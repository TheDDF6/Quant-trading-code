# rsi_divergence.py - RSI背离策略 (旧版)

import pandas as pd
import talib
import numpy as np

def find_peaks_and_troughs(series, window=5):
    """寻找局部高点和低点"""
    peaks = []
    troughs = []
    
    for i in range(window, len(series) - window):
        is_peak = True
        is_trough = True
        
        for j in range(-window, window + 1):
            if j == 0:
                continue
            if series[i] <= series[i + j]:
                is_peak = False
            if series[i] >= series[i + j]:
                is_trough = False
        
        if is_peak:
            peaks.append(i)
        if is_trough:
            troughs.append(i)
    
    return peaks, troughs

def identify_divergence(price_series, rsi_series, lookback_bars=20):
    """识别RSI背离"""
    bull_divs = []
    bear_divs = []
    
    price_peaks, price_troughs = find_peaks_and_troughs(price_series, window=3)
    rsi_peaks, rsi_troughs = find_peaks_and_troughs(rsi_series, window=3)
    
    # 检查底背离
    for i, price_trough_idx in enumerate(price_troughs[1:], 1):
        prev_price_trough_idx = price_troughs[i-1]
        
        if price_trough_idx - prev_price_trough_idx < 5 or price_trough_idx - prev_price_trough_idx > lookback_bars:
            continue
            
        current_price_low = price_series[price_trough_idx]
        prev_price_low = price_series[prev_price_trough_idx]
        
        rsi_trough_near_current = None
        rsi_trough_near_prev = None
        
        for rsi_idx in rsi_troughs:
            if abs(rsi_idx - price_trough_idx) <= 3:
                rsi_trough_near_current = rsi_idx
            if abs(rsi_idx - prev_price_trough_idx) <= 3:
                rsi_trough_near_prev = rsi_idx
        
        if rsi_trough_near_current is not None and rsi_trough_near_prev is not None:
            current_rsi_low = rsi_series[rsi_trough_near_current]
            prev_rsi_low = rsi_series[rsi_trough_near_prev]
            
            # 底背离：价格创新低，RSI未创新低
            if current_price_low < prev_price_low and current_rsi_low > prev_rsi_low:
                bull_divs.append((price_trough_idx, 'bottom_divergence'))
    
    # 检查顶背离
    for i, price_peak_idx in enumerate(price_peaks[1:], 1):
        prev_price_peak_idx = price_peaks[i-1]
        
        if price_peak_idx - prev_price_peak_idx < 5 or price_peak_idx - prev_price_peak_idx > lookback_bars:
            continue
            
        current_price_high = price_series[price_peak_idx]
        prev_price_high = price_series[prev_price_peak_idx]
        
        rsi_peak_near_current = None
        rsi_peak_near_prev = None
        
        for rsi_idx in rsi_peaks:
            if abs(rsi_idx - price_peak_idx) <= 3:
                rsi_peak_near_current = rsi_idx
            if abs(rsi_idx - prev_price_peak_idx) <= 3:
                rsi_peak_near_prev = rsi_idx
        
        if rsi_peak_near_current is not None and rsi_peak_near_prev is not None:
            current_rsi_high = rsi_series[rsi_peak_near_current]
            prev_rsi_high = rsi_series[rsi_peak_near_prev]
            
            # 顶背离：价格创新高，RSI未创新高
            if current_price_high > prev_price_high and current_rsi_high < prev_rsi_high:
                bear_divs.append((price_peak_idx, 'top_divergence'))
    
    return bull_divs, bear_divs

def generate_signals(df, stop_loss_pct=0.015, take_profit_ratio=1.5, lookback=20):
    """RSI背离策略"""
    print(f"=== RSI背离策略 (改进版) ===")
    print(f"参数: 回看期={lookback}, 止损={stop_loss_pct:.1%}, 止盈比例={take_profit_ratio}")
    
    df = df.copy()
    df['rsi'] = talib.RSI(df['close'], timeperiod=14)  # 固定使用14，这是标准设置
    signals = []

    min_data_points = max(50, lookback + 20)
    if len(df) < min_data_points:
        print(f"❌ 数据不足，需要至少 {min_data_points} 个数据点")
        return signals

    close_values = df['close'].values
    rsi_values = df['rsi'].values
    
    valid_mask = ~np.isnan(rsi_values)
    if not valid_mask.any():
        print("❌ RSI数据全部为NaN")
        return signals
    
    start_idx = np.where(valid_mask)[0][0] + 20
    
    bull_divs, bear_divs = identify_divergence(
        close_values[start_idx:], 
        rsi_values[start_idx:], 
        lookback_bars=lookback
    )
    
    bull_divs = [(idx + start_idx, div_type) for idx, div_type in bull_divs]
    bear_divs = [(idx + start_idx, div_type) for idx, div_type in bear_divs]
    
    print(f"识别到底背离: {len(bull_divs)} 个")
    print(f"识别到顶背离: {len(bear_divs)} 个")
    
    signal_count = 0
    
    # 底背离信号
    for idx, div_type in bull_divs:
        if idx >= len(df) - 1:
            continue
            
        entry_price = df['close'].iloc[idx + 1]
        lookback_start = max(0, idx - lookback)
        recent_low = df['low'].iloc[lookback_start:idx + 1].min()
        stop_loss = recent_low * 0.998
        
        stop_loss_distance = entry_price - stop_loss
        if stop_loss_distance <= 0:
            continue
            
        take_profit = entry_price + stop_loss_distance * take_profit_ratio
        
        signals.append((
            df.index[idx + 1],
            entry_price,
            'buy',
            stop_loss,
            take_profit,
            0
        ))
        
        signal_count += 1
        if signal_count <= 5:
            print(f"底背离信号 {signal_count}: {df.index[idx + 1].strftime('%Y-%m-%d %H:%M')}")
            print(f"  入场: {entry_price:.4f}, 止损: {stop_loss:.4f}, 止盈: {take_profit:.4f}")
    
    # 顶背离信号（反弹做多）
    for idx, div_type in bear_divs:
        if idx >= len(df) - 1:
            continue
            
        entry_price = df['close'].iloc[idx + 1]
        lookback_start = max(0, idx - lookback)
        recent_high = df['high'].iloc[lookback_start:idx + 1].max()
        stop_loss = recent_high * 1.002
        
        stop_loss_distance = stop_loss - entry_price
        if stop_loss_distance <= 0:
            continue
            
        take_profit = entry_price - stop_loss_distance * take_profit_ratio
        
        signals.append((
            df.index[idx + 1],
            entry_price,
            'buy',
            stop_loss,
            take_profit,
            0
        ))
        
        signal_count += 1
    
    print(f"生成信号总数: {len(signals)}")
    return signals