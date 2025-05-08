from pandas import DataFrame

def feature_engineering_standard(dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
    dataframe["%-day_of_week"] = dataframe["date"].dt.dayofweek
    dataframe["%-hour_of_day"] = dataframe["date"].dt.hour
    return dataframe 