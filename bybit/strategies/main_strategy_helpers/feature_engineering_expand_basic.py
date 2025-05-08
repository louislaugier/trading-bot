from pandas import DataFrame

def feature_engineering_expand_basic(dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
    dataframe["%-pct-change"] = dataframe["close"].pct_change()
    dataframe["%-raw_volume"] = dataframe["volume"]
    dataframe["%-raw_price"] = dataframe["close"]
    return dataframe 