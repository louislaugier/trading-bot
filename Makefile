.PHONY: help backtest-v

_now_seconds_for_d := $(shell date '+%s')
d ?= $(shell date -r $$(( $(_now_seconds_for_d) - 86400 )) '+%Y%m%d')

V_CFG_TRAIN_DAYS := 30
V_CFG_BACKTEST_DAYS := 365
V_BUFFER_DAYS := 90

_V_EFFECTIVE_END_DATE := $(d)

_V_END_DATE_SECONDS_CMD := date -j -f '%Y%m%d' '$(_V_EFFECTIVE_END_DATE)' '+%s'
_V_END_DATE_SECONDS := $(shell $(_V_END_DATE_SECONDS_CMD))

_V_BT_EXEC_START_DATE_CMD := date -j -r $$(( $(_V_END_DATE_SECONDS) - $(V_CFG_BACKTEST_DAYS) * 86400 )) '+%Y%m%d'
_V_BACKTEST_EXECUTION_START_DATE := $(shell $(_V_BT_EXEC_START_DATE_CMD))
_V_BACKTEST_EXECUTION_TIMERANGE := $(_V_BACKTEST_EXECUTION_START_DATE)-$(_V_EFFECTIVE_END_DATE)

_V_BT_START_SECONDS_CMD := date -j -f '%Y%m%d' '$(_V_BACKTEST_EXECUTION_START_DATE)' '+%s'
_V_BT_START_SECONDS := $(shell $(_V_BT_START_SECONDS_CMD))
_V_DL_START_DATE_CMD := date -j -r $$(( $(_V_BT_START_SECONDS) - $(V_CFG_TRAIN_DAYS) * 86400 - $(V_BUFFER_DAYS) * 86400 )) '+%Y%m%d'
_V_DOWNLOAD_START_DATE := $(shell $(_V_DL_START_DATE_CMD))
_V_DOWNLOAD_TIMERANGE := $(_V_DOWNLOAD_START_DATE)-$(_V_EFFECTIVE_END_DATE)

backtest-v:
	@echo "--------------------------------------------------------------------"
	@echo "Running backtest-v for end date: $(_V_EFFECTIVE_END_DATE)"
	@echo "(Assumes config.json: freqai.backtest_period_days=$(V_CFG_BACKTEST_DAYS), freqai.train_period_days=$(V_CFG_TRAIN_DAYS))"
	@echo "Using FreqAI Training Days: $(V_CFG_TRAIN_DAYS)"
	@echo "Using FreqAI Backtest Days: $(V_CFG_BACKTEST_DAYS)"
	@echo "Using Startup Candle Buffer: $(V_BUFFER_DAYS) days"
	@echo "==> Calculated Download Period:   $(_V_DOWNLOAD_START_DATE) to $(_V_EFFECTIVE_END_DATE) ($(_V_DOWNLOAD_TIMERANGE))"
	@echo "==> Calculated Backtest Execution Period: $(_V_BACKTEST_EXECUTION_START_DATE) to $(_V_EFFECTIVE_END_DATE) ($(_V_BACKTEST_EXECUTION_TIMERANGE))"
	@echo "--------------------------------------------------------------------"

	@echo "\n>>> Downloading data for backtest-v..."
	docker compose run --rm freqtrade download-data \
		--timerange $(_V_DOWNLOAD_TIMERANGE) \
		--exchange bybit \
		--pairs BTC/USDT:USDT \
		--timeframe 5m 15m 1h 4h \
		--erase \
		--config /freqtrade/user_data/config.json

	@echo "\n>>> Running backtest for backtest-v..."
	docker compose run --rm freqtrade backtesting \
		--timerange $(_V_BACKTEST_EXECUTION_TIMERANGE) \
		--strategy MainStrategy \
		--freqaimodel XGBoostRegressor \
		--config /freqtrade/user_data/config.json

help:
	@echo "Available commands:"
	@echo "  make backtest-v [d=YYYYMMDD] - Download data and run backtest. Defaults to d=yesterday."
	@echo "                             (Assumes freqai.backtest_period_days=$(V_CFG_BACKTEST_DAYS) and freqai.train_period_days=$(V_CFG_TRAIN_DAYS) in config.json)"
	@echo "  make help                   - Show this help message" 