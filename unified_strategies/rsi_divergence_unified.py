#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一RSI背离策略
兼容回测系统和实盘交易系统的统一实现
"""

import pandas as pd
import numpy as np
import talib
from typing import List, Dict, Any, Tuple
from datetime import datetime
import logging

from .base_unified_strategy import UnifiedStrategy, UnifiedSignal

class RSIDivergenceUnified(UnifiedStrategy):
    """统一RSI背离策略"""
    
    def __init__(self, strategy_id: str, config: Dict[str, Any]):
        super().__init__(strategy_id, config)
        
        # RSI参数 - 与实盘交易一致
        self.rsi_period = config.get('rsi_period', 12)  # 与实盘一致
        self.rsi_oversold = config.get('rsi_oversold', 30)
        self.rsi_overbought = config.get('rsi_overbought', 70)
        
        # 背离检测参数
        self.lookback_period = config.get('lookback_period', 20)
        self.min_divergence_distance = config.get('min_divergence_distance', 5)
        self.peak_window = config.get('peak_window', 3)
        
        # 风险管理参数 - 统一设置
        self.stop_loss_pct = config.get('stop_loss_pct', 0.015)  # 1.5%
        self.take_profit_ratio = config.get('take_profit_ratio', 1.5)  # 1.5倍止损
        self.risk_method = config.get('risk_method', 'fixed_percentage')  # 'fixed_percentage' or 'recent_extreme'
        
        # 信号过滤参数 - 与实盘一致
        self.min_signal_strength = config.get('min_signal_strength', 0.6)  # 与实盘一致
        self.volume_confirmation = config.get('volume_confirmation', True)
        
        # 调试选项
        self.debug = config.get('debug', False)
        
    def get_strategy_name(self) -> str:
        return "RSI Divergence Unified"
    
    def analyze_market(self, df: pd.DataFrame, symbol: str = "BTC-USDT") -> List[UnifiedSignal]:
        """分析市场数据并生成统一信号"""
        
        if not self.validate_data(df):
            if self.debug:
                print(f"数据验证失败 - 长度: {len(df) if df is not None else 0}")
            return []
        
        try:
            # 计算技术指标
            df = df.copy()
            df['rsi'] = talib.RSI(df['close'], timeperiod=self.rsi_period)
            
            # 等待足够的数据
            valid_data_start = self.rsi_period + self.lookback_period
            if len(df) < valid_data_start:
                return []
            
            # 提取数据数组
            close_prices = df['close'].values
            high_prices = df['high'].values
            low_prices = df['low'].values
            rsi_values = df['rsi'].values
            volumes = df['volume'].values if 'volume' in df.columns else np.ones(len(df))
            
            # 去除NaN值
            valid_mask = ~np.isnan(rsi_values)
            start_idx = np.where(valid_mask)[0][0] + self.lookback_period
            
            if start_idx >= len(df) - 1:
                return []
            
            # 识别背离信号
            signals = self._identify_all_divergences(
                df, symbol, close_prices, high_prices, low_prices, 
                rsi_values, volumes, start_idx
            )
            
            if self.debug:
                print(f"识别到 {len(signals)} 个信号")
            
            return signals
            
        except Exception as e:
            if self.debug:
                print(f"市场分析失败: {e}")
            return []
    
    def _identify_all_divergences(self, 
                                df: pd.DataFrame,
                                symbol: str,
                                close_prices: np.ndarray,
                                high_prices: np.ndarray,
                                low_prices: np.ndarray,
                                rsi_values: np.ndarray,
                                volumes: np.ndarray,
                                start_idx: int) -> List[UnifiedSignal]:
        """识别所有背离信号"""
        
        signals = []
        
        # 使用滑动窗口识别背离
        for i in range(start_idx, len(close_prices)):
            current_signals = self._check_divergence_at_point(
                df, symbol, close_prices, high_prices, low_prices,
                rsi_values, volumes, i
            )
            signals.extend(current_signals)
        
        return signals
    
    def _check_divergence_at_point(self,
                                 df: pd.DataFrame,
                                 symbol: str,
                                 close_prices: np.ndarray,
                                 high_prices: np.ndarray,
                                 low_prices: np.ndarray,
                                 rsi_values: np.ndarray,
                                 volumes: np.ndarray,
                                 current_idx: int) -> List[UnifiedSignal]:
        """在指定点检查背离"""
        
        signals = []
        
        # 获取用于分析的数据窗口
        window_start = max(0, current_idx - self.lookback_period)
        window_close = close_prices[window_start:current_idx + 1]
        window_high = high_prices[window_start:current_idx + 1]
        window_low = low_prices[window_start:current_idx + 1]
        window_rsi = rsi_values[window_start:current_idx + 1]
        
        if len(window_close) < self.min_divergence_distance + self.peak_window:
            return signals
        
        # 寻找峰谷
        price_peaks, price_troughs = self._find_peaks_and_troughs(window_close, self.peak_window)
        rsi_peaks, rsi_troughs = self._find_peaks_and_troughs(window_rsi, self.peak_window)
        
        current_price = close_prices[current_idx]
        current_rsi = rsi_values[current_idx]
        timestamp = df.index[current_idx] if hasattr(df.index[current_idx], 'to_pydatetime') else df.index[current_idx]
        
        # 检查底背离 (看涨)
        bull_signal = self._check_bullish_divergence(
            window_close, window_low, window_rsi,
            price_troughs, rsi_troughs, len(window_close) - 1
        )
        
        if bull_signal:
            stop_loss, take_profit = self._calculate_risk_levels(
                current_price, 'buy', current_idx, low_prices, high_prices
            )
            
            strength = self._calculate_signal_strength('buy', current_rsi, volumes[current_idx])
            
            if strength >= self.min_signal_strength:
                signal = UnifiedSignal(
                    symbol=symbol,
                    signal_type='buy',
                    timestamp=timestamp,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    strategy_id=self.strategy_id,
                    strength=strength,
                    metadata={
                        'signal_reason': 'bullish_divergence',
                        'rsi_value': current_rsi,
                        'risk_method': self.risk_method
                    }
                )
                signals.append(signal)
        
        # 检查顶背离 (看跌)
        bear_signal = self._check_bearish_divergence(
            window_close, window_high, window_rsi,
            price_peaks, rsi_peaks, len(window_close) - 1
        )
        
        if bear_signal:
            stop_loss, take_profit = self._calculate_risk_levels(
                current_price, 'sell', current_idx, low_prices, high_prices
            )
            
            strength = self._calculate_signal_strength('sell', current_rsi, volumes[current_idx])
            
            if strength >= self.min_signal_strength:
                signal = UnifiedSignal(
                    symbol=symbol,
                    signal_type='sell',
                    timestamp=timestamp,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    strategy_id=self.strategy_id,
                    strength=strength,
                    metadata={
                        'signal_reason': 'bearish_divergence',
                        'rsi_value': current_rsi,
                        'risk_method': self.risk_method
                    }
                )
                signals.append(signal)
        
        return signals
    
    def _check_bullish_divergence(self,
                                price_series: np.ndarray,
                                low_series: np.ndarray,
                                rsi_series: np.ndarray,
                                price_troughs: List[int],
                                rsi_troughs: List[int],
                                current_idx: int) -> bool:
        """检查底背离"""
        
        if len(price_troughs) < 2:
            return False
        
        # 获取最近的两个价格低点
        recent_troughs = [t for t in price_troughs if t < current_idx - self.peak_window]
        if len(recent_troughs) < 2:
            return False
        
        trough1_idx = recent_troughs[-2]
        trough2_idx = recent_troughs[-1]
        
        # 检查距离是否合适
        if trough2_idx - trough1_idx < self.min_divergence_distance:
            return False
        
        # 价格创新低
        price1_low = low_series[trough1_idx]
        price2_low = low_series[trough2_idx]
        
        if price2_low >= price1_low:
            return False
        
        # 找到对应的RSI低点
        rsi1_idx = self._find_nearest_trough(rsi_troughs, trough1_idx)
        rsi2_idx = self._find_nearest_trough(rsi_troughs, trough2_idx)
        
        if rsi1_idx is None or rsi2_idx is None:
            return False
        
        # RSI未创新低 (背离)
        rsi1_low = rsi_series[rsi1_idx]
        rsi2_low = rsi_series[rsi2_idx]
        
        # 底背离：价格新低，RSI不创新低
        return rsi2_low > rsi1_low
    
    def _check_bearish_divergence(self,
                                price_series: np.ndarray,
                                high_series: np.ndarray,
                                rsi_series: np.ndarray,
                                price_peaks: List[int],
                                rsi_peaks: List[int],
                                current_idx: int) -> bool:
        """检查顶背离"""
        
        if len(price_peaks) < 2:
            return False
        
        # 获取最近的两个价格高点
        recent_peaks = [p for p in price_peaks if p < current_idx - self.peak_window]
        if len(recent_peaks) < 2:
            return False
        
        peak1_idx = recent_peaks[-2]
        peak2_idx = recent_peaks[-1]
        
        # 检查距离是否合适
        if peak2_idx - peak1_idx < self.min_divergence_distance:
            return False
        
        # 价格创新高
        price1_high = high_series[peak1_idx]
        price2_high = high_series[peak2_idx]
        
        if price2_high <= price1_high:
            return False
        
        # 找到对应的RSI高点
        rsi1_idx = self._find_nearest_peak(rsi_peaks, peak1_idx)
        rsi2_idx = self._find_nearest_peak(rsi_peaks, peak2_idx)
        
        if rsi1_idx is None or rsi2_idx is None:
            return False
        
        # RSI未创新高 (背离)
        rsi1_high = rsi_series[rsi1_idx]
        rsi2_high = rsi_series[rsi2_idx]
        
        # 顶背离：价格新高，RSI不创新高
        return rsi2_high < rsi1_high
    
    def _find_nearest_trough(self, rsi_troughs: List[int], price_trough_idx: int) -> int:
        """找到最接近价格低点的RSI低点"""
        if not rsi_troughs:
            return None
        
        min_distance = float('inf')
        nearest_idx = None
        
        for rsi_idx in rsi_troughs:
            distance = abs(rsi_idx - price_trough_idx)
            if distance < min_distance and distance <= self.peak_window:
                min_distance = distance
                nearest_idx = rsi_idx
        
        return nearest_idx
    
    def _find_nearest_peak(self, rsi_peaks: List[int], price_peak_idx: int) -> int:
        """找到最接近价格高点的RSI高点"""
        if not rsi_peaks:
            return None
        
        min_distance = float('inf')
        nearest_idx = None
        
        for rsi_idx in rsi_peaks:
            distance = abs(rsi_idx - price_peak_idx)
            if distance < min_distance and distance <= self.peak_window:
                min_distance = distance
                nearest_idx = rsi_idx
        
        return nearest_idx
    
    def _calculate_risk_levels(self,
                             entry_price: float,
                             signal_type: str,
                             current_idx: int,
                             low_prices: np.ndarray,
                             high_prices: np.ndarray) -> Tuple[float, float]:
        """统一的风险级别计算"""
        
        if self.risk_method == 'recent_extreme':
            # 使用历史极值方法 (回测系统原方法)
            return self._calculate_extreme_based_risk(
                entry_price, signal_type, current_idx, low_prices, high_prices
            )
        else:
            # 使用固定百分比方法 (实盘系统方法)
            return self._calculate_percentage_based_risk(entry_price, signal_type)
    
    def _calculate_percentage_based_risk(self, entry_price: float, signal_type: str) -> Tuple[float, float]:
        """基于百分比的风险计算"""
        if signal_type == 'buy':
            stop_loss = entry_price * (1 - self.stop_loss_pct)
            take_profit = entry_price + (entry_price - stop_loss) * self.take_profit_ratio
        else:  # sell
            stop_loss = entry_price * (1 + self.stop_loss_pct)
            take_profit = entry_price - (stop_loss - entry_price) * self.take_profit_ratio
        
        return stop_loss, take_profit
    
    def _calculate_extreme_based_risk(self,
                                    entry_price: float,
                                    signal_type: str,
                                    current_idx: int,
                                    low_prices: np.ndarray,
                                    high_prices: np.ndarray) -> Tuple[float, float]:
        """基于历史极值的风险计算"""
        lookback_start = max(0, current_idx - self.lookback_period)
        
        if signal_type == 'buy':
            recent_low = np.min(low_prices[lookback_start:current_idx + 1])
            stop_loss = recent_low * 0.998  # 0.2%缓冲
            stop_loss_distance = entry_price - stop_loss
            if stop_loss_distance <= 0:
                stop_loss = entry_price * (1 - self.stop_loss_pct)
                stop_loss_distance = entry_price - stop_loss
            take_profit = entry_price + stop_loss_distance * self.take_profit_ratio
        else:  # sell
            recent_high = np.max(high_prices[lookback_start:current_idx + 1])
            stop_loss = recent_high * 1.002  # 0.2%缓冲
            stop_loss_distance = stop_loss - entry_price
            if stop_loss_distance <= 0:
                stop_loss = entry_price * (1 + self.stop_loss_pct)
                stop_loss_distance = stop_loss - entry_price
            take_profit = entry_price - stop_loss_distance * self.take_profit_ratio
        
        return stop_loss, take_profit
    
    def _calculate_signal_strength(self, signal_type: str, rsi_value: float, volume: float) -> float:
        """计算信号强度"""
        strength = 0.5  # 基础强度
        
        # RSI强度贡献
        if signal_type == 'buy':
            if rsi_value <= self.rsi_oversold:
                strength += 0.3
            elif rsi_value <= 40:
                strength += 0.2
        else:  # sell
            if rsi_value >= self.rsi_overbought:
                strength += 0.3
            elif rsi_value >= 60:
                strength += 0.2
        
        # 成交量确认
        if self.volume_confirmation and volume > 0:
            # 这里可以加入更复杂的成交量分析
            strength += 0.1
        
        return min(strength, 1.0)

# 兼容性函数 - 供回测系统调用
def generate_signals(df: pd.DataFrame, 
                    stop_loss_pct: float = 0.015,
                    take_profit_ratio: float = 1.5,
                    lookback: int = 20,
                    risk_method: str = 'recent_extreme',
                    timeframe: str = '5m',
                    **kwargs) -> List[Tuple]:
    """
    兼容回测系统的信号生成函数
    使用统一策略实现
    """
    
    # 根据时间框架调整RSI参数
    timeframe_configs = {
        '5m': {
            'rsi_period': 12,           # 与实盘一致
            'lookback_period': 20,      # 100分钟回看
            'min_divergence_distance': 5,
            'peak_window': 3,
        },
        '15m': {
            'rsi_period': 12,           # 与实盘一致
            'lookback_period': 16,      # 4小时回看
            'min_divergence_distance': 4,
            'peak_window': 2,
        },
        '1h': {
            'rsi_period': 12,           # 与实盘一致
            'lookback_period': 24,      # 24小时回看
            'min_divergence_distance': 6,
            'peak_window': 3,
        },
        '4h': {
            'rsi_period': 14,           # 标准周期
            'lookback_period': 20,      # 80小时=3.3天回看
            'min_divergence_distance': 5,
            'peak_window': 2,
        },
        '1d': {
            'rsi_period': 16,           # 稍长周期更稳定
            'lookback_period': 30,      # 30天回看
            'min_divergence_distance': 7,
            'peak_window': 3,
        }
    }
    
    # 获取时间框架特定配置，如果没有则使用传入参数或5m配置
    tf_config = timeframe_configs.get(timeframe, timeframe_configs['5m'])
    
    config = {
        'rsi_period': kwargs.get('rsi_period', tf_config['rsi_period']),
        'lookback_period': kwargs.get('lookback_period', lookback if lookback != 20 else tf_config['lookback_period']),
        'min_divergence_distance': kwargs.get('min_divergence_distance', tf_config['min_divergence_distance']),
        'peak_window': kwargs.get('peak_window', tf_config['peak_window']),
        'stop_loss_pct': stop_loss_pct,
        'take_profit_ratio': take_profit_ratio,
        'risk_method': risk_method,
        'min_signal_strength': 0.6,  # 与实盘一致的信号强度过滤
        'debug': True
    }
    
    print(f"使用时间框架 {timeframe} 的RSI策略优化参数:")
    print(f"  RSI周期: {config['rsi_period']}, 回看周期: {config['lookback_period']}")
    print(f"  背离距离: {config['min_divergence_distance']}, 峰值窗口: {config['peak_window']}")
    
    strategy = RSIDivergenceUnified("rsi_divergence_backtest", config)
    unified_signals = strategy.analyze_market(df, "BTC-USDT")
    
    # 转换为回测系统格式
    backtest_signals = [signal.to_backtest_format() for signal in unified_signals]
    
    print(f"=== 统一RSI背离策略 ===")
    print(f"参数: 回看期={lookback}, 止损={stop_loss_pct:.1%}, 止盈比例={take_profit_ratio}, 风险方法={risk_method}")
    print(f"生成信号总数: {len(backtest_signals)}")
    
    # 显示前5个信号
    for i, signal in enumerate(unified_signals[:5], 1):
        print(f"{signal.metadata.get('signal_reason', '未知')}信号 {i}: {signal.timestamp}")
        print(f"  入场: {signal.entry_price:.4f}, 止损: {signal.stop_loss:.4f}, 止盈: {signal.take_profit:.4f}")
    
    return backtest_signals