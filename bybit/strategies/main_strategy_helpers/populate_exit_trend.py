from pandas import DataFrame
from functools import reduce

def populate_exit_trend(df: DataFrame, metadata: dict) -> DataFrame:
    exit_long_conditions = [
        df["do_predict"] == 1,
        df["&-s_close"] < 0.01,
        df['%-rsi-period'] > 70,
        df['close'] > df['bb_upperband-period'],
    ]

    # The list will not be empty here, so direct reduce is fine.
    # Original code had `if exit_long_conditions:`, which is true for non-empty lists.
    # Assuming conditions are always valid Series for bitwise operations.
    if exit_long_conditions: 
        df.loc[
            reduce(lambda x, y: x & y, exit_long_conditions), ["exit_long", "exit_tag"]
        ] = (1, "exit_long")

    exit_short_conditions = [
        df["do_predict"] == 1,
        df["&-s_close"] > -0.01,
        df['%-rsi-period'] < 30,
        df['close'] < df['bb_lowerband-period'],
    ]

    if exit_short_conditions:
        df.loc[
            reduce(lambda x, y: x & y, exit_short_conditions), ["exit_short", "exit_tag"]
        ] = (1, "exit_short")
    return df 