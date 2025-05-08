#!/bin/bash

# Exit on error
set -e

# --- Parameters ---
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <target_end_date_YMD> <host_config_file_path> <host_model_dir_base_path>"
    echo "Example: $0 20240101 bybit/config.json bybit/models"
    exit 1
fi

TARGET_END_DATE_YMD=$1
HOST_CONFIG_FILE=$2
HOST_MODEL_DIR_BASE=$3

# Ensure jq is installed
if ! command -v jq &> /dev/null
then
    echo "jq could not be found. Please install jq (e.g., brew install jq or apt-get install jq)."
    exit 1
fi

if [ ! -f "${HOST_CONFIG_FILE}" ]; then
    echo "Configuration file ${HOST_CONFIG_FILE} not found."
    exit 1
fi

# Function to safely get config value using jq
get_config_value() {
    local key="$1"
    local default_value="$2"
    # Use the HOST_CONFIG_FILE variable passed as an argument
    local value=$(jq -r "${key}" "${HOST_CONFIG_FILE}")

    if [ "$value" == "null" ] || [ -z "$value" ]; then
        if [ -n "$default_value" ]; then
            echo "$default_value"
            return
        fi
        echo "Error: Key '${key}' not found or is null in ${HOST_CONFIG_FILE}, and no default value provided." >&2
        exit 1
    fi
    echo "$value"
}

# Read parameters from config file using the provided HOST_CONFIG_FILE
CFG_BACKTEST_DAYS=$(get_config_value '.freqai.backtest_period_days' "7")
FREQAI_IDENTIFIER=$(get_config_value '.freqai.identifier' "") # No default, should fail if not present
CFG_TRAIN_DAYS=$(get_config_value '.freqai.train_period_days' "30")
BUFFER_DAYS=$(get_config_value '.backtest_config.buffer_days' "70") # Default matches last update
PAIR=$(get_config_value '.backtest_config.pair' "BTC/USDT:USDT")
TIMEFRAME_MAIN=$(get_config_value '.timeframe' "5m")
TIMEFRAMES_ALL=$(get_config_value '.backtest_config.timeframes_all_download' "5m 15m 1h 4h")
DRY_RUN=$(get_config_value '.dry_run' "false")

# Fixed parameters (path inside docker, not parameterized from Makefile)
CONFIG_FILE_DOCKER="/freqtrade/user_data/config.json" 
# MODEL_DIR_BASE_DOCKER="/freqtrade/user_data/models" # Path inside docker, not changed by this param

# --- Helper Function (macOS/BSD date syntax) ---
date_to_seconds() {
  local format="$1"
  local date_str="$2"
  date -j -f "$format" "$date_str" '+%s' 2>/dev/null || { echo "ERROR: Invalid date format '$format' for value '$date_str'" >&2; return 1; }
  return 0
}

seconds_to_date() {
  local seconds="$1"
  local format="${2:-%Y%m%d}" # Default YYYYMMDD
  date -j -r "$seconds" "+$format" 2>/dev/null || { echo "ERROR: Invalid seconds value '$seconds'" >&2; return 1; }
  return 0
}

# --- Calculations ---
echo "--------------------------------------------------------------------"
echo "Running backtest script for end date: ${TARGET_END_DATE_YMD}"
echo "Using config file: ${HOST_CONFIG_FILE}"
echo "Using host model base directory: ${HOST_MODEL_DIR_BASE}"
echo "(Configured backtest days: ${CFG_BACKTEST_DAYS}, train days: ${CFG_TRAIN_DAYS}, buffer: ${BUFFER_DAYS})"
echo "(Pair: ${PAIR}, Main Timeframe: ${TIMEFRAME_MAIN}, All Timeframes: ${TIMEFRAMES_ALL})"
echo "(Dry Run: ${DRY_RUN})"

# Calculate DESIRED ranges
END_DATE_SECONDS=$(date_to_seconds '%Y%m%d' "${TARGET_END_DATE_YMD}") || exit 1
LOOKBACK_BT_DAYS_SECONDS=$(( CFG_BACKTEST_DAYS * 86400 ))
DESIRED_BT_START_SECONDS=$(( END_DATE_SECONDS - LOOKBACK_BT_DAYS_SECONDS ))
DESIRED_BT_START_DATE=$(seconds_to_date "$DESIRED_BT_START_SECONDS") || exit 1
DESIRED_BT_TIMERANGE="${DESIRED_BT_START_DATE}-${TARGET_END_DATE_YMD}"

LOOKBACK_TOTAL_DAYS_SECONDS=$(( (CFG_TRAIN_DAYS + BUFFER_DAYS) * 86400 ))
DESIRED_DL_START_SECONDS=$(( DESIRED_BT_START_SECONDS - LOOKBACK_TOTAL_DAYS_SECONDS ))
DESIRED_DL_START_DATE=$(seconds_to_date "$DESIRED_DL_START_SECONDS") || exit 1
DESIRED_DL_TIMERANGE="${DESIRED_DL_START_DATE}-${TARGET_END_DATE_YMD}"

echo "Desired Download Period:    ${DESIRED_DL_TIMERANGE}"
echo "Desired Backtest Period:  ${DESIRED_BT_TIMERANGE}"
echo "--------------------------------------------------------------------"

# --- Download Data ---
echo -e "\\n>>> Downloading data..."
docker compose run --rm freqtrade download-data \
  --timerange "${DESIRED_DL_TIMERANGE}" \
  --exchange bybit \
  --pairs "${PAIR}" \
  --timeframe ${TIMEFRAMES_ALL} \
  --config "${CONFIG_FILE_DOCKER}"

# --- Determine Actual Data Start ---
echo -e "\\n>>> Determining actual data start date for ${PAIR} ${TIMEFRAME_MAIN}..."
# Run list-data with --show-timerange
LIST_DATA_OUTPUT=$(docker compose run --rm freqtrade list-data --pair "${PAIR}" --show-timerange --config "${CONFIG_FILE_DOCKER}" 2>/dev/null || echo "LIST_DATA_FAILED")

if [ "$LIST_DATA_OUTPUT" == "LIST_DATA_FAILED" ]; then
  echo "ERROR: 'freqtrade list-data' command failed." >&2
  exit 1
fi

# Define the new awk script to extract Pair, Timeframe, and FromDate
AWK_SCRIPT=$'
  # Rule 1: Skip headers/separators or lines with less than 7 fields
  NF < 7 || $0 ~ /━━━━━━━━━/ || $0 ~ /Pair symbol/ {
    next
  }

  # Rule 2 (default action for lines not skipped by \'next\'): Process and print
  # $2 is Pair symbol, $3 is Timeframe, $5 is "FROM_DATE FROM_TIME"
  {
    split($5, datetime_parts, " ");
    print $2 " " $3 " " datetime_parts[1]; # Output: Pair Timeframe FromDate
  }
'

# Process list-data output using the new awk script
PROCESSED_LIST_DATA=$(printf "%s\n" "${LIST_DATA_OUTPUT}" | awk -F'[ \t]*│[ \t]*' "${AWK_SCRIPT}")

# Check if the initial awk processing produced any output
if [ -z "${PROCESSED_LIST_DATA}" ]; then
  echo "ERROR: Initial awk processing of list-data yielded no results for ${PAIR} ${TIMEFRAME_MAIN}." >&2
  echo "Original list-data output:" >&2
  echo "${LIST_DATA_OUTPUT}" >&2
  exit 1
fi

# Grep for the target pair and timeframe from the processed data
# The pattern matches the PAIR at the start, followed by a space, then TIMEFRAME_MAIN, followed by a space.
TARGET_LINE=$(echo "${PROCESSED_LIST_DATA}" | grep "^${PAIR} ${TIMEFRAME_MAIN} ")

# Check if the target line was found by grep
if [ -z "${TARGET_LINE}" ]; then
  echo "ERROR: Could not find data start date for ${PAIR} ${TIMEFRAME_MAIN} in processed list-data." >&2
  echo "Processed list-data (before grep):" >&2
  echo "${PROCESSED_LIST_DATA}" >&2
  echo "Original list-data output:" >&2
  echo "${LIST_DATA_OUTPUT}" >&2
  exit 1
fi

# Extract the date (the 3rd field) from the successfully grepped line
ACTUAL_DATA_START_DATE_STR=$(echo "${TARGET_LINE}" | awk '{print $3}')

# Final check on the extracted date string
if [ -z "${ACTUAL_DATA_START_DATE_STR}" ]; then
  echo "ERROR: Extracted data start date is unexpectedly empty for ${PAIR} ${TIMEFRAME_MAIN} after grep and final awk." >&2
  echo "Target line processed by final awk was: ${TARGET_LINE}" >&2
  exit 1
fi

echo "Actual data start date found: ${ACTUAL_DATA_START_DATE_STR}" # Should be YYYY-MM-DD

# --- Calculate Effective Backtest Start ---
echo -e "\\n>>> Calculating effective backtest period..."
ACTUAL_DATA_START_SECONDS=$(date_to_seconds '%Y-%m-%d' "${ACTUAL_DATA_START_DATE_STR}") || exit 1
ACTUAL_DATA_START_DATE_FRIENDLY=$(seconds_to_date "$ACTUAL_DATA_START_SECONDS" '%Y-%m-%d')
echo "Debug: ACTUAL_DATA_START_DATE_STR = ${ACTUAL_DATA_START_DATE_STR}, ACTUAL_DATA_START_DATE_FRIENDLY = ${ACTUAL_DATA_START_DATE_FRIENDLY}"

MIN_EXEC_START_SECONDS=$(( ACTUAL_DATA_START_SECONDS + LOOKBACK_TOTAL_DAYS_SECONDS ))
MIN_EXEC_START_DATE_FRIENDLY=$(seconds_to_date "$MIN_EXEC_START_SECONDS" '%Y-%m-%d')
echo "Debug: MIN_EXEC_START_DATE_FRIENDLY = ${MIN_EXEC_START_DATE_FRIENDLY}"

REQUESTED_EXEC_START_SECONDS=$(( END_DATE_SECONDS - LOOKBACK_BT_DAYS_SECONDS ))
REQUESTED_EXEC_START_DATE_FRIENDLY=$(seconds_to_date "$REQUESTED_EXEC_START_SECONDS" '%Y-%m-%d')
echo "Debug: REQUESTED_EXEC_START_DATE_FRIENDLY = ${REQUESTED_EXEC_START_DATE_FRIENDLY}"

if [ "$REQUESTED_EXEC_START_SECONDS" -gt "$MIN_EXEC_START_SECONDS" ]; then
  EFFECTIVE_EXEC_START_SECONDS="$REQUESTED_EXEC_START_SECONDS"
else
  EFFECTIVE_EXEC_START_SECONDS="$MIN_EXEC_START_SECONDS"
fi
EFFECTIVE_EXEC_START_DATE_CALC_FRIENDLY=$(seconds_to_date "$EFFECTIVE_EXEC_START_SECONDS" '%Y-%m-%d')
echo "Debug: EFFECTIVE_EXEC_START_DATE_CALC_FRIENDLY (chosen) = ${EFFECTIVE_EXEC_START_DATE_CALC_FRIENDLY}"

EFFECTIVE_EXEC_START_DATE=$(seconds_to_date "$EFFECTIVE_EXEC_START_SECONDS") || exit 1
EFFECTIVE_BACKTEST_TIMERANGE="${EFFECTIVE_EXEC_START_DATE}-${TARGET_END_DATE_YMD}"

# --- Final Check ---
if [ "$EFFECTIVE_EXEC_START_SECONDS" -ge "$END_DATE_SECONDS" ]; then
  EFFECTIVE_START_DATE_FRIENDLY=$(seconds_to_date "$EFFECTIVE_EXEC_START_SECONDS" '%Y-%m-%d') || EFFECTIVE_START_DATE_FRIENDLY="INVALID"
  END_DATE_FRIENDLY=$(seconds_to_date "$END_DATE_SECONDS" '%Y-%m-%d') || END_DATE_FRIENDLY="INVALID"
  echo "ERROR: Effective backtest start date (${EFFECTIVE_START_DATE_FRIENDLY}) is on or after end date (${END_DATE_FRIENDLY}). Insufficient data available for pair ${PAIR} after accounting for lookback." >&2
  exit 1
fi
echo "Using Effective Backtest Execution Period: ${EFFECTIVE_BACKTEST_TIMERANGE}"

# --- Clean FreqAI Model ---
if [ -z "$FREQAI_IDENTIFIER" ] || [ "$FREQAI_IDENTIFIER" == "null" ]; then
    echo "ERROR: FREQAI_IDENTIFIER not provided or could not be read from ${HOST_CONFIG_FILE}." >&2
    exit 1
fi
# Use the HOST_MODEL_DIR_BASE variable passed as an argument
HOST_MODEL_PATH="${HOST_MODEL_DIR_BASE}/${FREQAI_IDENTIFIER}"
echo -e "\\n>>> Cleaning previous FreqAI model data for identifier: ${FREQAI_IDENTIFIER} at ${HOST_MODEL_PATH}..."
rm -rf "${HOST_MODEL_PATH}"

# --- Run Backtest ---
echo -e "\\n>>> Running backtest (Effective Range: ${EFFECTIVE_BACKTEST_TIMERANGE})..."
if [ "${DRY_RUN}" = "true" ]; then
    echo "Running in DRY RUN mode - no actual trades will be executed"
    docker compose run --rm freqtrade backtesting \
        --timerange "${EFFECTIVE_BACKTEST_TIMERANGE}" \
        --strategy MainStrategy \
        --freqaimodel XGBoostRegressor \
        --config "${CONFIG_FILE_DOCKER}" \
        --dry-run
else
    docker compose run --rm freqtrade backtesting \
        --timerange "${EFFECTIVE_BACKTEST_TIMERANGE}" \
        --strategy MainStrategy \
        --freqaimodel XGBoostRegressor \
        --config "${CONFIG_FILE_DOCKER}"
fi

echo -e "\\nBacktest finished." 