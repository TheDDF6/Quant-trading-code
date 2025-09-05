#!/usr/bin/env python3
"""
简化的RSI背离策略 - 用于参数敏感性测试
"""

import pandas as pd
import numpy as np

def calculate_rsi(prices, period=14):
    """计算RSI指标"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def find_divergences(prices, rsi, lookback_period=20, min_distance=5):
    """寻找价格与RSI背离"""
    signals = []
    
    for i in range(lookback_period, len(prices) - 5):
        # 寻找价格新高和RSI背离
        price_window = prices[i-lookback_period:i]
        rsi_window = rsi[i-lookback_period:i]
        
        if pd.isna(price_window).any() or pd.isna(rsi_window).any():
            continue
            
        current_price = prices.iloc[i]
        current_rsi = rsi.iloc[i]
        
        # 寻找价格新高但RSI未创新高的背离
        if current_price == price_window.max():
            if current_rsi < rsi_window.max() * 0.95:  # RSI背离
                signals.append({
                    'timestamp': prices.index[i],
                    'price': current_price,
                    'action': 'bearish_divergence',
                    'strength': 0.7
                })
        
        # 寻找价格新低但RSI未创新低的背离
        elif current_price == price_window.min():
            if current_rsi > rsi_window.min() * 1.05:  # RSI背离
                signals.append({
                    'timestamp': prices.index[i],
                    'price': current_price,
                    'action': 'bullish_divergence', 
                    'strength': 0.7
                })
    
    return signals

def generate_signals(df, stop_loss_pct=0.015, take_profit_ratio=1.5, lookback=20, risk_method='fixed_percentage', **kwargs):
    """
    生成RSI背离交易信号
    
    Args:
        df: OHLCV数据
        stop_loss_pct: 止损百分比
        take_profit_ratio: 止盈比例
        lookback: 回看周期
        risk_method: 风险管理方法
        **kwargs: 其他参数
        
    Returns:
        List[Tuple]: 信号列表，格式为 (时间, 价格, 动作, 止损, 止盈, 强度)
    """
    
    if df is None or len(df) < 50:
        return []
    
    # 获取参数
    rsi_period = kwargs.get('rsi_period', 14)
    min_signal_strength = kwargs.get('min_signal_strength', 0.6)
    
    try:
        # 计算RSI
        rsi = calculate_rsi(df['close'], rsi_period)
        
        # 寻找背离
        divergences = find_divergences(df['close'], rsi, lookback, 5)
        
        # 转换为交易信号格式
        signals = []
        for div in divergences:
            if div['strength'] >= min_signal_strength:
                timestamp = div['timestamp']
                price = div['price']
                action = div['action']
                
                if action == 'bearish_divergence':
                    # 做空信号
                    stop_loss = price * (1 + stop_loss_pct)
                    take_profit = price * (1 - stop_loss_pct * take_profit_ratio)
                elif action == 'bullish_divergence':
                    # 做多信号
                    stop_loss = price * (1 - stop_loss_pct)
                    take_profit = price * (1 + stop_loss_pct * take_profit_ratio)
                else:
                    continue
                
                signals.append((timestamp, price, action, stop_loss, take_profit, div['strength']))
        
        print(f"RSI简化策略生成 {len(signals)} 个信号")
        return signals
        
    except Exception as e:
        print(f"RSI简化策略执行失败: {e}")
        return []