.PHONY: help backtest backtest-bybit

_now_seconds_for_d := $(shell date '+%s')
d ?= $(shell date -r $$(( $(_now_seconds_for_d) - 86400 )) '+%Y%m%d')

# Default exchange specific parameters
BYBIT_CONFIG_PATH := bybit/config.json
BYBIT_MODELS_PATH := bybit/models

# Generic backtest target - currently defaults to bybit
backtest: backtest-bybit

backtest-bybit:
	@echo "Ensuring backtest script is executable..."
	chmod +x ./backtest.sh
	@echo "Running backtest script for Bybit..."
	./backtest.sh "$(d)" "$(BYBIT_CONFIG_PATH)" "$(BYBIT_MODELS_PATH)"

help:
	@echo "Available commands:"
	@echo "  make backtest              - Run backtest for the default exchange (currently Bybit)."
	@echo "  make backtest-bybit [d=YYYYMMDD] - Run backtest specifically for Bybit."
	@echo "                             Config is read from $(BYBIT_CONFIG_PATH)."
	@echo "                             Defaults to d=yesterday."
	@echo "  make help                  - Show this help message."
	@echo "Exchange-specific targets (e.g., backtest-bybit) can be added for other exchanges." 