import talib.abstract as ta
from pandas import DataFrame
from technical import qtpylib

def feature_engineering_expand_all(dataframe: DataFrame, period: int, metadata: dict, **kwargs) -> DataFrame:
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