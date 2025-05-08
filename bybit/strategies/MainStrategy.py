import logging
from functools import reduce

import talib.abstract as ta
from pandas import DataFrame
from technical import qtpylib

from freqtrade.strategy import IStrategy
from main_strategy_helpers.feature_engineering_expand_all import feature_engineering_expand_all
from main_strategy_helpers.feature_engineering_expand_basic import feature_engineering_expand_basic
from main_strategy_helpers.feature_engineering_standard import feature_engineering_standard
from main_strategy_helpers.set_freqai_targets import set_freqai_targets
from main_strategy_helpers.populate_indicators import populate_indicators
from main_strategy_helpers.populate_entry_trend import populate_entry_trend
from main_strategy_helpers.populate_exit_trend import populate_exit_trend
from main_strategy_helpers.confirm_trade_entry import confirm_trade_entry


logger = logging.getLogger(__name__)


class MainStrategy(IStrategy):
    minimal_roi = {
        "0": 0.05,    # 5% profit target
        "60": 0.025,  # 2.5% profit target after 60 minutes
        "120": 0.01,  # 1% profit target after 120 minutes
        "240": -1     # Hold until stoploss after 240 minutes
    }

    plot_config = {
        "main_plot": {},
        "subplots": {
            "&-s_close": {"&-s_close": {"color": "blue"}},
            "do_predict": {
                "do_predict": {"color": "brown"},
            },
        },
    }

    process_only_new_candles = True
    stoploss = -0.02  # 2% stoploss
    use_exit_signal = True
    # this is the maximum period fed to talib (timeframe independent)
    startup_candle_count: int = 40
    can_short = True

    def feature_engineering_expand_all(
        self, dataframe: DataFrame, period: int, metadata: dict, **kwargs
    ) -> DataFrame:
        return feature_engineering_expand_all(dataframe, period, metadata, **kwargs)

    def feature_engineering_expand_basic(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        return feature_engineering_expand_basic(dataframe, metadata, **kwargs)

    def feature_engineering_standard(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        return feature_engineering_standard(dataframe, metadata, **kwargs)

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        return set_freqai_targets(dataframe, metadata, self.freqai_info, **kwargs)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return populate_indicators(self, dataframe, metadata)

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        return populate_entry_trend(df, metadata)

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        return populate_exit_trend(df, metadata)

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time,
        entry_tag,
        side: str,
        **kwargs,
    ) -> bool:
        return confirm_trade_entry(
            self.dp,
            self.timeframe,
            pair,
            order_type,
            amount,
            rate,
            time_in_force,
            current_time,
            entry_tag,
            side,
            **kwargs,
        )