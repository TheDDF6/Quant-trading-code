"""rsi_trend_divergence.py - RSI趋势背离策略"""

import pandas as pd
import talib

def generate_signals(df, stop_loss_pct=0.015, take_profit_ratio=3.0, lookback=10):
    """
    RSI趋势背离策略（改写版：使用MA200过滤趋势 + N根K线局部极值判断）
    """
    print(f"=== RSI趋势背离策略 ===")
    df = df.copy()
    df['rsi'] = talib.RSI(df['close'], timeperiod=14)
    df['ma200'] = df['close'].rolling(200).mean()
    signals = []

    equity = 10000  # 初始资金

    for i in range(max(200, lookback), len(df)):
        current_close = df['close'].iloc[i]
        current_rsi = df['rsi'].iloc[i]
        ma200 = df['ma200'].iloc[i]
        if pd.isna(current_rsi) or pd.isna(ma200):
            continue

        # 趋势向上：多头背离
        if current_close > ma200:
            recent_low = df['low'].iloc[i-lookback:i].min()
            recent_rsi_low = df['rsi'].iloc[i-lookback:i].min()
            if current_close <= recent_low and current_rsi > recent_rsi_low:
                entry_price = current_close
                stop_loss = recent_low * 0.998
                stop_loss_distance = entry_price - stop_loss
                if stop_loss_distance <= 0:
                    continue
                take_profit = entry_price + stop_loss_distance * take_profit_ratio
                size = equity * stop_loss_pct / stop_loss_distance
                max_position_value = equity * 0.3
                if size * entry_price > max_position_value:
                    size = max_position_value / entry_price

                signals.append((df.index[i], entry_price, 'buy', stop_loss, take_profit, size))
                if len(signals) <= 3:
                    print(f"信号{len(signals)}: {df.index[i]} (多头) 买入 {entry_price:.4f} | 止损 {stop_loss:.4f} | 止盈 {take_profit:.4f} | 仓位 {size:.6f}")

        # 趋势向下：空头背离（做多反弹）
        elif current_close < ma200:
            recent_high = df['high'].iloc[i-lookback:i].max()
            recent_rsi_high = df['rsi'].iloc[i-lookback:i].max()
            if current_close >= recent_high and current_rsi < recent_rsi_high:
                entry_price = current_close
                stop_loss = recent_high * 1.002
                stop_loss_distance = stop_loss - entry_price
                if stop_loss_distance <= 0:
                    continue
                take_profit = entry_price - stop_loss_distance * take_profit_ratio
                size = equity * stop_loss_pct / stop_loss_distance
                max_position_value = equity * 0.3
                if size * entry_price > max_position_value:
                    size = max_position_value / entry_price

                signals.append((df.index[i], entry_price, 'buy', stop_loss, take_profit, size))
                if len(signals) <= 3:
                    print(f"信号{len(signals)}: {df.index[i]} (空头) 反弹买入 {entry_price:.4f} | 止损 {stop_loss:.4f} | 止盈 {take_profit:.4f} | 仓位 {size:.6f}")

    print(f"生成信号总数: {len(signals)}")
    return signals
