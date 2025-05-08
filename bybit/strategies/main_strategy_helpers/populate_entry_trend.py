from pandas import DataFrame
from functools import reduce

def populate_entry_trend(df: DataFrame, metadata: dict) -> DataFrame:
    df['trend_strength'] = df['%-adx-period'] > 25
    df['volume_confirm'] = df['%-relative_volume-period'] > 1.5
    df['rsi_confirm'] = (df['%-rsi-period'] < 30) | (df['%-rsi-period'] > 70)
    df['bb_confirm'] = (df['close'] < df['bb_lowerband-period']) | (df['close'] > df['bb_upperband-period'])

    enter_long_conditions = [
        df["do_predict"] == 1,
        df["&-s_close"] > 0.02,
        df['trend_strength'],
        df['volume_confirm'],
        df['%-rsi-period'] < 30,
        df['close'] < df['bb_lowerband-period'],
    ]

    # The list will not be empty here, so direct reduce is fine.
    # Original code had `if enter_long_conditions:`, which is true for non-empty lists.
    # Assuming conditions are always valid Series for bitwise operations.
    if enter_long_conditions: 
         df.loc[
            reduce(lambda x, y: x & y, enter_long_conditions), ["enter_long", "enter_tag"]
        ] = (1, "long")

    enter_short_conditions = [
        df["do_predict"] == 1,
        df["&-s_close"] < -0.02,
        df['trend_strength'],
        df['volume_confirm'],
        df['%-rsi-period'] > 70,
        df['close'] > df['bb_upperband-period'],
    ]

    if enter_short_conditions:
        df.loc[
            reduce(lambda x, y: x & y, enter_short_conditions), ["enter_short", "enter_tag"]
        ] = (1, "short")
    return df 