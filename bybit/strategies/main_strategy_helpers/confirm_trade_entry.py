# from freqtrade.data.dataprovider import DataProvider # Potential import for type hinting

def confirm_trade_entry(
    dp, # DataProvider instance
    timeframe: str,
    pair: str,
    order_type: str,
    amount: float,
    rate: float,
    time_in_force: str,
    current_time, # Type could be datetime
    entry_tag: str,
    side: str,
    **kwargs,
) -> bool:
    df, _ = dp.get_analyzed_dataframe(pair, timeframe)
    last_candle = df.iloc[-1].squeeze()

    if side == "long":
        if last_candle['%-relative_volume-period'] < 1.5:
            return False
        if last_candle['%-adx-period'] < 25:
            return False
    elif side == "short":
        if last_candle['%-relative_volume-period'] < 1.5:
            return False
        if last_candle['%-adx-period'] < 25:
            return False
    return True 