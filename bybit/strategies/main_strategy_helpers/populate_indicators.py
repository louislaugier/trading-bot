from pandas import DataFrame
import talib.abstract as ta
from technical import qtpylib
from freqtrade.strategy import IStrategy # For type hinting

def populate_indicators(strategy: IStrategy, dataframe: DataFrame, metadata: dict) -> DataFrame:
    dataframe = strategy.freqai.start(dataframe, metadata, strategy)

    # Re-calculate indicators needed for strategy logic after FreqAI processing
    period = 14 # This was hardcoded in the original, ensure it's what's desired
                # or pass as an argument if it needs to be dynamic from strategy config.

    dataframe["%-adx-period"] = ta.ADX(dataframe, timeperiod=period)
    bollinger = qtpylib.bollinger_bands(
        qtpylib.typical_price(dataframe), window=period, stds=2.2
    )
    dataframe["bb_lowerband-period"] = bollinger["lower"]
    dataframe["bb_upperband-period"] = bollinger["upper"]
    dataframe["%-rsi-period"] = ta.RSI(dataframe, timeperiod=period)
    dataframe["%-relative_volume-period"] = (
        dataframe["volume"] / dataframe["volume"].rolling(period).mean()
    )
    return dataframe 