import logging
from functools import reduce

import talib.abstract as ta
from pandas import DataFrame
from technical import qtpylib

from freqtrade.strategy import IStrategy


logger = logging.getLogger(__name__)


class MainStrategy(IStrategy):
    """
    Example strategy showing how the user connects their own
    IFreqaiModel to the strategy.

    Warning! This is a showcase of functionality,
    which means that it is designed to show various functions of FreqAI
    and it runs on all computers. We use this showcase to help users
    understand how to build a strategy, and we use it as a benchmark
    to help debug possible problems.

    This means this is *not* meant to be run live in production.
    """

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
        """
        Keep the original feature engineering to maintain compatibility with existing model
        """
        dataframe["%-rsi-period"] = ta.RSI(dataframe, timeperiod=period)
        dataframe["%-mfi-period"] = ta.MFI(dataframe, timeperiod=period)
        dataframe["%-adx-period"] = ta.ADX(dataframe, timeperiod=period)
        dataframe["%-sma-period"] = ta.SMA(dataframe, timeperiod=period)
        dataframe["%-ema-period"] = ta.EMA(dataframe, timeperiod=period)

        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), window=period, stds=2.2
        )
        dataframe["bb_lowerband-period"] = bollinger["lower"]
        dataframe["bb_middleband-period"] = bollinger["mid"]
        dataframe["bb_upperband-period"] = bollinger["upper"]

        dataframe["%-bb_width-period"] = (
            dataframe["bb_upperband-period"] - dataframe["bb_lowerband-period"]
        ) / dataframe["bb_middleband-period"]
        dataframe["%-close-bb_lower-period"] = dataframe["close"] / dataframe["bb_lowerband-period"]

        dataframe["%-roc-period"] = ta.ROC(dataframe, timeperiod=period)

        dataframe["%-relative_volume-period"] = (
            dataframe["volume"] / dataframe["volume"].rolling(period).mean()
        )

        return dataframe

    def feature_engineering_expand_basic(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        Keep the original basic features
        """
        dataframe["%-pct-change"] = dataframe["close"].pct_change()
        dataframe["%-raw_volume"] = dataframe["volume"]
        dataframe["%-raw_price"] = dataframe["close"]
        return dataframe

    def feature_engineering_standard(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        Keep the original standard features
        """
        dataframe["%-day_of_week"] = dataframe["date"].dt.dayofweek
        dataframe["%-hour_of_day"] = dataframe["date"].dt.hour
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        """
        *Only functional with FreqAI enabled strategies*
        Required function to set the targets for the model.
        All targets must be prepended with `&` to be recognized by the FreqAI internals.

        Access metadata such as the current pair with:

        `metadata["pair"]`

        More details about feature engineering available:

        https://www.freqtrade.io/en/latest/freqai-feature-engineering

        :param dataframe: strategy dataframe which will receive the targets
        :param metadata: metadata of current pair
        usage example: dataframe["&-target"] = dataframe["close"].shift(-1) / dataframe["close"]
        """
        dataframe["&-s_close"] = (
            dataframe["close"]
            .shift(-self.freqai_info["feature_parameters"]["label_period_candles"])
            .rolling(self.freqai_info["feature_parameters"]["label_period_candles"])
            .mean()
            / dataframe["close"]
            - 1
        )

        # Classifiers are typically set up with strings as targets:
        # df['&s-up_or_down'] = np.where( df["close"].shift(-100) >
        #                                 df["close"], 'up', 'down')

        # If user wishes to use multiple targets, they can add more by
        # appending more columns with '&'. User should keep in mind that multi targets
        # requires a multioutput prediction model such as
        # freqai/prediction_models/CatboostRegressorMultiTarget.py,
        # freqtrade trade --freqaimodel CatboostRegressorMultiTarget

        # df["&-s_range"] = (
        #     df["close"]
        #     .shift(-self.freqai_info["feature_parameters"]["label_period_candles"])
        #     .rolling(self.freqai_info["feature_parameters"]["label_period_candles"])
        #     .max()
        #     -
        #     df["close"]
        #     .shift(-self.freqai_info["feature_parameters"]["label_period_candles"])
        #     .rolling(self.freqai_info["feature_parameters"]["label_period_candles"])
        #     .min()
        # )

        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # All indicators must be populated by feature_engineering_*() functions

        # the model will return all labels created by user in `set_freqai_targets()`
        # (& appended targets), an indication of whether or not the prediction should be accepted,
        # the target mean/std values for each of the labels created by user in
        # `set_freqai_targets()` for each training period.

        dataframe = self.freqai.start(dataframe, metadata, self)

        # Re-calculate indicators needed for strategy logic after FreqAI processing,
        # in case FreqAI drops them from its output dataframe.
        # The period should match the one used in feature_engineering_expand_all,
        # which is derived from config's `indicator_periods_candles`.
        # For this Example strategy and its config, period is 14.
        period = 14

        dataframe["%-adx-period"] = ta.ADX(dataframe, timeperiod=period)
        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), window=period, stds=2.2
        )
        dataframe["bb_lowerband-period"] = bollinger["lower"]
        # dataframe["bb_middleband-period"] = bollinger["mid"] # Not used in entry/exit
        dataframe["bb_upperband-period"] = bollinger["upper"]
        dataframe["%-rsi-period"] = ta.RSI(dataframe, timeperiod=period)
        dataframe["%-relative_volume-period"] = (
            dataframe["volume"] / dataframe["volume"].rolling(period).mean()
        )

        return dataframe

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        # Strong trend confirmation using ADX
        df['trend_strength'] = df['%-adx-period'] > 25  # ADX > 25 indicates strong trend

        # Volume confirmation
        df['volume_confirm'] = df['%-relative_volume-period'] > 1.5  # 50% above average volume

        # RSI confirmation
        df['rsi_confirm'] = (df['%-rsi-period'] < 30) | (df['%-rsi-period'] > 70)

        # Bollinger Band confirmation
        df['bb_confirm'] = (df['close'] < df['bb_lowerband-period']) | (df['close'] > df['bb_upperband-period'])

        # Long entry conditions
        enter_long_conditions = [
            df["do_predict"] == 1,
            df["&-s_close"] > 0.02,  # Increased threshold to 2%
            df['trend_strength'],     # Strong trend
            df['volume_confirm'],     # High volume
            df['%-rsi-period'] < 30,  # Oversold
            df['close'] < df['bb_lowerband-period'],  # Price below lower BB
        ]

        if enter_long_conditions:
            df.loc[
                reduce(lambda x, y: x & y, enter_long_conditions), ["enter_long", "enter_tag"]
            ] = (1, "long")

        # Short entry conditions
        enter_short_conditions = [
            df["do_predict"] == 1,
            df["&-s_close"] < -0.02,  # Increased threshold to -2%
            df['trend_strength'],      # Strong trend
            df['volume_confirm'],      # High volume
            df['%-rsi-period'] > 70,  # Overbought
            df['close'] > df['bb_upperband-period'],  # Price above upper BB
        ]

        if enter_short_conditions:
            df.loc[
                reduce(lambda x, y: x & y, enter_short_conditions), ["enter_short", "enter_tag"]
            ] = (1, "short")

        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        # Exit long positions
        exit_long_conditions = [
            df["do_predict"] == 1,
            df["&-s_close"] < 0.01,  # Exit if prediction turns negative
            df['%-rsi-period'] > 70,  # Exit on overbought
            df['close'] > df['bb_upperband-period'],  # Exit above upper BB
        ]

        if exit_long_conditions:
            df.loc[
                reduce(lambda x, y: x & y, exit_long_conditions), ["exit_long", "exit_tag"]
            ] = (1, "exit_long")

        # Exit short positions
        exit_short_conditions = [
            df["do_predict"] == 1,
            df["&-s_close"] > -0.01,  # Exit if prediction turns positive
            df['%-rsi-period'] < 30,  # Exit on oversold
            df['close'] < df['bb_lowerband-period'],  # Exit below lower BB
        ]

        if exit_short_conditions:
            df.loc[
                reduce(lambda x, y: x & y, exit_short_conditions), ["exit_short", "exit_tag"]
            ] = (1, "exit_short")

        return df

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
        """
        Additional confirmation before entering a trade
        """
        # Get the dataframe
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = df.iloc[-1].squeeze()

        # Additional confirmation for long entries
        if side == "long":
            # Check if we have enough volume
            if last_candle['%-relative_volume-period'] < 1.5:
                return False
            
            # Check if trend is strong enough
            if last_candle['%-adx-period'] < 25:
                return False

        # Additional confirmation for short entries
        if side == "short":
            # Check if we have enough volume
            if last_candle['%-relative_volume-period'] < 1.5:
                return False
            
            # Check if trend is strong enough
            if last_candle['%-adx-period'] < 25:
                return False

        return True