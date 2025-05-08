from pandas import DataFrame
# import numpy as np # Not strictly needed for the current uncommented code

def set_freqai_targets(dataframe: DataFrame, metadata: dict, freqai_info: dict, **kwargs) -> DataFrame:
    dataframe["&-s_close"] = (
        dataframe["close"]
        .shift(-freqai_info["feature_parameters"]["label_period_candles"])
        .rolling(freqai_info["feature_parameters"]["label_period_candles"])
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
    #     .shift(-freqai_info["feature_parameters"]["label_period_candles"])
    #     .rolling(freqai_info["feature_parameters"]["label_period_candles"])
    #     .max()
    #     -
    #     df["close"]
    #     .shift(-freqai_info["feature_parameters"]["label_period_candles"])
    #     .rolling(freqai_info["feature_parameters"]["label_period_candles"])
    #     .min()
    # )
    return dataframe 