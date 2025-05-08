# Freqtrade Backtesting Project

This project provides a Docker-based environment for running Freqtrade backtests with FreqAI integration. It includes automated data downloading, model management, and backtesting capabilities, structured to support multiple exchanges.

## Prerequisites

- Docker and Docker Compose installed
- `jq` command-line tool installed (for JSON processing)
  - macOS: `brew install jq`
  - Ubuntu/Debian: `apt-get install jq`
  - Other systems: Check your package manager

Each exchange typically has its own directory (e.g., `bybit/`) containing its specific `config.json` and `models/` subdirectory.

## Configuration

### Exchange Configuration (e.g., `bybit/config.json`)

The primary configuration for Freqtrade, FreqAI, and backtesting parameters is done within an exchange-specific `config.json` file (e.g., `bybit/config.json` for Bybit).
The `backtest.sh` script is parameterized to use the correct configuration file based on the Makefile target.

Key settings within an exchange's `config.json` that you'll often adjust for backtesting include:

- **Backtesting Period & Pair (found under `backtest_config` and `freqai` objects):**
  - `backtest_config.pair`: The trading pair to backtest (e.g., "DOGE/USDT:USDT", "BTC/USDT:USDT").
  - `freqai.backtest_period_days`: The number of days for the actual backtesting evaluation period (e.g., 7, 30, 365).

- **Data Lookback for FreqAI & Indicators (influences total data downloaded):**
  - `freqai.train_period_days`: Number of days of data the FreqAI model trains on *before* the `backtest_period_days` start (e.g., 15, 30, 90). Larger values mean more training data but higher memory use and longer download/setup.
  - `backtest_config.buffer_days`: Additional days of data downloaded *before* the `train_period_days` start. This is primarily for indicator warm-up periods to ensure they are stable when FreqAI training begins (e.g., 30).

- **FreqAI Model Complexity & Features (impacts memory and training time):**
  - `freqai.identifier`: A unique name for your FreqAI model setup. The script cleans model files related to this identifier before a new run.
  - `freqai.model_training_parameters` (e.g., `n_estimators`, `max_depth` for XGBoost): Controls the complexity and training time of the ML model.
  - `freqai.feature_parameters` (e.g., `include_corr_pairlist`, `include_shifted_candles`, `label_period_candles`, `indicator_periods_candles`): Defines what features are generated for the ML model. More features or more complex features can increase memory and time requirements.

- **General Backtest Behavior:**
  - `timeframe`: The main analysis timeframe for your strategy (e.g., "5m", "1h"). This is also usually the primary timeframe for FreqAI.
  - `backtest_config.timeframes_all_download`: Space-separated list of all timeframes to download (e.g., "5m 15m 1h 4h"). Ensure your main `timeframe` is included here.
  - `dry_run` (top-level): Set to `true` if you want the backtest to simulate trades without running the full strategy logic for trade execution details (often faster, but less detailed results). For full backtesting results, set to `false`. Note that the `backtest.sh` script passes `--config` to `freqtrade backtesting`, so this `dry_run` setting in the config is what Freqtrade itself will use; the script previously had its own DRY_RUN variable for its docker command, but that is now superseded by the config's `dry_run` for the actual backtest run.
  - `exchange.name`: Ensure this is correctly set for the specific exchange (e.g., "bybit").

Ensure the relevant `config.json` (e.g., `bybit/config.json`) is correctly populated with these settings before running a backtest for that exchange.

## Running Backtests

The `Makefile` provides targets for running backtests.

### Generic Backtest (Defaults to Bybit for now)

To run a backtest for the current default exchange (Bybit):

```bash
make backtest
```
This will invoke the `backtest-bybit` target.

### Exchange-Specific Backtest

To run a backtest for a specific exchange, use its dedicated target. For Bybit:

```bash
make backtest-bybit
```

**Custom End Date for an Exchange-Specific Backtest:**

To run a backtest for Bybit ending on a specific date (all other parameters are read from `bybit/config.json`):

```bash
make backtest-bybit d=YYYYMMDD
# Example: make backtest-bybit d=20240301
```

This will:
1. Ensure `backtest.sh` is executable.
2. Invoke `backtest.sh` with the target end date, and paths to Bybit's config (`bybit/config.json`) and models directory (`bybit/models`).
3. The script then reads parameters from `bybit/config.json`.
4. It handles data downloading, cleans the previous FreqAI model data for the `freqai.identifier` found in `bybit/config.json` (within `bybit/models/`), and runs the Freqtrade backtest.

Changes to backtest duration, training days, pair, dry run mode, etc., should be made directly in the respective exchange's `config.json` file.

Future exchange support can be added by:
1. Creating a directory for the new exchange (e.g., `newexchange/`) with its own `config.json` and `models/` subdirectory.
2. Adding a corresponding target in the `Makefile` (e.g., `backtest-newexchange`) that calls `backtest.sh` with the paths for that new exchange.

## Docker Environment

The project runs entirely within Docker containers. The main components are:

- `freqtrade`: The main Freqtrade container
- Data persistence through Docker volumes
- Model storage in the `bybit/models` directory

## Troubleshooting

1. **Data Download Issues**
   - Ensure you have sufficient disk space
   - Check your internet connection
   - Verify the exchange API is accessible

2. **Model Issues**
   - Check if the FreqAI identifier is correctly set in `config.json`
   - Ensure the model directory has proper permissions
   - Verify sufficient memory for model training

3. **Docker Issues**
   - Ensure Docker daemon is running
   - Check Docker Compose version compatibility
   - Verify container logs for detailed error messages

## Help

For available commands and options:

```bash
make help
```

## Notes

- The `backtest.sh` script automatically handles data availability and adjusts the backtest period accordingly based on the actual downloaded data and configured lookback periods from the specified `config.json`.
- Previous model data (within the specified exchange's model directory) is automatically cleaned before each run based on the `freqai.identifier`.
- All operations are performed within Docker containers for consistency.
- The script uses macOS/BSD date syntax; for Linux systems, modifications to date commands within `backtest.sh` may be required if not already compatible. 