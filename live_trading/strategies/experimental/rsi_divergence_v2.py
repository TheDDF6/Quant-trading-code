# rsi_divergence_v2.py - RSI背离策略v2 (标准化接口)
"""
RSI背离策略 v2.0
实现标准化策略接口，支持多策略框架

主要功能:
1. RSI背离信号识别
2. 动态止损止盈计算
3. 多时间周期支持
4. 风险控制集成
"""

import pandas as pd
import numpy as np
import talib
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
import logging

from strategies.base_strategy import BaseStrategy, Signal

class RSIDivergenceV2(BaseStrategy):
    """RSI背离策略 v2.0"""
    
    def __init__(self, strategy_id: str, config: Dict[str, Any]):
        """
        初始化RSI背离策略
        
        Args:
            strategy_id: 策略唯一标识
            config: 策略配置
        """
        super().__init__(strategy_id, config)
        
        # RSI参数
        self.rsi_period = config.get('rsi_period', 14)
        self.rsi_oversold = config.get('rsi_oversold', 30)
        self.rsi_overbought = config.get('rsi_overbought', 70)
        
        # 背离检测参数
        self.lookback_period = config.get('lookback', 20)
        self.min_divergence_distance = config.get('min_divergence_distance', 5)
        self.peak_window = config.get('peak_window', 3)
        
        # 止损止盈参数
        self.stop_loss_pct = config.get('stop_loss_pct', 0.015)  # 1.5%
        self.take_profit_ratio = config.get('take_profit_ratio', 1.5)  # 1.5倍止损
        self.trailing_stop_pct = config.get('trailing_stop_pct', 0.008)  # 0.8%追踪止损
        
        # 信号过滤参数
        self.min_signal_strength = config.get('min_signal_strength', 0.6)
        self.volume_confirmation = config.get('volume_confirmation', True)
        
        # 数据缓存
        self.price_cache = {}
        self.rsi_cache = {}
        self.signal_cache = {}
        
        # 最少数据点要求
        self.min_data_points = max(50, self.lookback_period + 30)
        
        self.logger.info(f"RSI背离策略 {strategy_id} 初始化完成 - RSI周期:{self.rsi_period}, 回看期:{self.lookback_period}")
    
    def analyze_market(self, market_data: pd.DataFrame, **kwargs) -> List[Signal]:
        """
        分析市场数据生成交易信号
        
        Args:
            market_data: OHLCV数据
            **kwargs: symbol等额外参数
            
        Returns:
            List[Signal]: 生成的信号列表
        """
        symbol = kwargs.get('symbol', 'Unknown')
        
        try:
            # 数据验证
            if len(market_data) < self.min_data_points:
                self.logger.debug(f"数据点不足: {len(market_data)} < {self.min_data_points}")
                return []
            
            # 确保数据完整性
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in market_data.columns for col in required_columns):
                self.logger.error(f"数据缺少必要列: {market_data.columns.tolist()}")
                return []
            
            # 计算技术指标
            close_prices = market_data['close'].values
            high_prices = market_data['high'].values
            low_prices = market_data['low'].values
            volumes = market_data['volume'].values
            
            # 计算RSI
            rsi = talib.RSI(close_prices, timeperiod=self.rsi_period)
            
            # 缓存数据
            self.price_cache[symbol] = close_prices
            self.rsi_cache[symbol] = rsi
            
            # 识别背离信号
            signals = self._identify_divergence_signals(
                symbol, close_prices, high_prices, low_prices, rsi, volumes
            )
            
            return signals
            
        except Exception as e:
            self.logger.error(f"市场分析失败 ({symbol}): {e}")
            return []
    
    def _identify_divergence_signals(self, 
                                   symbol: str,
                                   close_prices: np.ndarray,
                                   high_prices: np.ndarray, 
                                   low_prices: np.ndarray,
                                   rsi: np.ndarray,
                                   volumes: np.ndarray) -> List[Signal]:
        """识别背离信号"""
        signals = []
        
        if len(close_prices) < self.lookback_period + 10:
            return signals
        
        # 寻找价格和RSI的峰谷
        price_peaks, price_troughs = self._find_peaks_and_troughs(close_prices, self.peak_window)
        rsi_peaks, rsi_troughs = self._find_peaks_and_troughs(rsi, self.peak_window)
        
        current_time = datetime.now()
        current_price = close_prices[-1]
        current_rsi = rsi[-1]
        
        # 检查底背离 (看涨信号)
        bull_signal = self._check_bullish_divergence(
            close_prices, low_prices, rsi, 
            price_troughs, rsi_troughs,
            current_price, current_rsi
        )
        
        if bull_signal:
            # 计算止损止盈
            stop_loss = current_price * (1 - self.stop_loss_pct)
            take_profit = current_price + (current_price - stop_loss) * self.take_profit_ratio
            
            # 计算信号强度
            strength = self._calculate_signal_strength('buy', current_rsi, volumes)
            
            if strength >= self.min_signal_strength:
                signal = Signal(
                    strategy_id=self.strategy_id,
                    symbol=symbol,
                    signal_type='buy',
                    strength=strength,
                    timestamp=current_time,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    metadata={
                        'signal_reason': 'bullish_divergence',
                        'rsi_value': current_rsi,
                        'lookback_confirmed': True
                    }
                )
                signals.append(signal)
        
        # 检查顶背离 (看跌信号)
        bear_signal = self._check_bearish_divergence(
            close_prices, high_prices, rsi,
            price_peaks, rsi_peaks,
            current_price, current_rsi
        )
        
        if bear_signal:
            # 计算止损止盈
            stop_loss = current_price * (1 + self.stop_loss_pct)
            take_profit = current_price - (stop_loss - current_price) * self.take_profit_ratio
            
            # 计算信号强度
            strength = self._calculate_signal_strength('sell', current_rsi, volumes)
            
            if strength >= self.min_signal_strength:
                signal = Signal(
                    strategy_id=self.strategy_id,
                    symbol=symbol,
                    signal_type='sell',
                    strength=strength,
                    timestamp=current_time,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    metadata={
                        'signal_reason': 'bearish_divergence',
                        'rsi_value': current_rsi,
                        'lookback_confirmed': True
                    }
                )
                signals.append(signal)
        
        return signals
    
    def _find_peaks_and_troughs(self, series: np.ndarray, window: int) -> Tuple[List[int], List[int]]:
        """寻找序列中的峰值和谷值"""
        peaks = []
        troughs = []
        
        for i in range(window, len(series) - window):
            # 检查是否为峰值
            is_peak = all(series[i] >= series[i + j] for j in range(-window, window + 1) if j != 0)
            if is_peak and any(series[i] > series[i + j] for j in range(-window, window + 1) if j != 0):
                peaks.append(i)
            
            # 检查是否为谷值
            is_trough = all(series[i] <= series[i + j] for j in range(-window, window + 1) if j != 0)
            if is_trough and any(series[i] < series[i + j] for j in range(-window, window + 1) if j != 0):
                troughs.append(i)
        
        return peaks, troughs
    
    def _check_bullish_divergence(self, 
                                close_prices: np.ndarray,
                                low_prices: np.ndarray,
                                rsi: np.ndarray,
                                price_troughs: List[int],
                                rsi_troughs: List[int],
                                current_price: float,
                                current_rsi: float) -> bool:
        """检查底背离（看涨信号）"""
        if len(price_troughs) < 2 or current_rsi > self.rsi_oversold:
            return False
        
        # 寻找最近的两个价格谷值
        recent_troughs = [idx for idx in price_troughs if len(close_prices) - idx <= self.lookback_period]
        
        if len(recent_troughs) < 2:
            return False
        
        # 取最近两个谷值
        trough1_idx = recent_troughs[-2]  # 较早的谷值
        trough2_idx = recent_troughs[-1]  # 较晚的谷值
        
        # 谷值间距检查
        if trough2_idx - trough1_idx < self.min_divergence_distance:
            return False
        
        # 价格谷值比较
        price_low1 = low_prices[trough1_idx]
        price_low2 = low_prices[trough2_idx]
        
        # 寻找对应的RSI谷值
        rsi_low1 = self._find_nearest_rsi_extreme(rsi_troughs, trough1_idx, rsi)
        rsi_low2 = self._find_nearest_rsi_extreme(rsi_troughs, trough2_idx, rsi)
        
        if rsi_low1 is None or rsi_low2 is None:
            return False
        
        # 底背离条件：价格创新低，但RSI没有创新低
        price_makes_lower_low = price_low2 < price_low1 * 0.998  # 0.2%容差
        rsi_makes_higher_low = rsi_low2 > rsi_low1 * 1.02       # 2%容差
        
        return price_makes_lower_low and rsi_makes_higher_low
    
    def _check_bearish_divergence(self,
                                close_prices: np.ndarray,
                                high_prices: np.ndarray, 
                                rsi: np.ndarray,
                                price_peaks: List[int],
                                rsi_peaks: List[int],
                                current_price: float,
                                current_rsi: float) -> bool:
        """检查顶背离（看跌信号）"""
        if len(price_peaks) < 2 or current_rsi < self.rsi_overbought:
            return False
        
        # 寻找最近的两个价格峰值
        recent_peaks = [idx for idx in price_peaks if len(close_prices) - idx <= self.lookback_period]
        
        if len(recent_peaks) < 2:
            return False
        
        # 取最近两个峰值
        peak1_idx = recent_peaks[-2]  # 较早的峰值
        peak2_idx = recent_peaks[-1]  # 较晚的峰值
        
        # 峰值间距检查
        if peak2_idx - peak1_idx < self.min_divergence_distance:
            return False
        
        # 价格峰值比较
        price_high1 = high_prices[peak1_idx]
        price_high2 = high_prices[peak2_idx]
        
        # 寻找对应的RSI峰值
        rsi_high1 = self._find_nearest_rsi_extreme(rsi_peaks, peak1_idx, rsi)
        rsi_high2 = self._find_nearest_rsi_extreme(rsi_peaks, peak2_idx, rsi)
        
        if rsi_high1 is None or rsi_high2 is None:
            return False
        
        # 顶背离条件：价格创新高，但RSI没有创新高
        price_makes_higher_high = price_high2 > price_high1 * 1.002  # 0.2%容差
        rsi_makes_lower_high = rsi_high2 < rsi_high1 * 0.98         # 2%容差
        
        return price_makes_higher_high and rsi_makes_lower_high
    
    def _find_nearest_rsi_extreme(self, rsi_extremes: List[int], price_extreme_idx: int, rsi: np.ndarray) -> Optional[float]:
        """寻找最接近价格极值的RSI极值"""
        min_distance = float('inf')
        nearest_rsi_value = None
        
        for rsi_idx in rsi_extremes:
            distance = abs(rsi_idx - price_extreme_idx)
            if distance < min_distance and distance <= 3:  # 最多3个周期的误差
                min_distance = distance
                nearest_rsi_value = rsi[rsi_idx]
        
        return nearest_rsi_value
    
    def _calculate_signal_strength(self, signal_type: str, current_rsi: float, volumes: np.ndarray) -> float:
        """计算信号强度 (0.0-1.0)"""
        strength = 0.5  # 基础强度
        
        # RSI位置评分
        if signal_type == 'buy':
            # 买入信号：RSI越低（超卖）越好
            if current_rsi <= 20:
                strength += 0.3
            elif current_rsi <= 30:
                strength += 0.2
            elif current_rsi <= 40:
                strength += 0.1
        
        elif signal_type == 'sell':
            # 卖出信号：RSI越高（超买）越好
            if current_rsi >= 80:
                strength += 0.3
            elif current_rsi >= 70:
                strength += 0.2
            elif current_rsi >= 60:
                strength += 0.1
        
        # 成交量确认
        if self.volume_confirmation and len(volumes) >= 20:
            recent_avg_volume = np.mean(volumes[-20:])
            current_volume = volumes[-1]
            
            if current_volume > recent_avg_volume * 1.2:  # 成交量放大20%
                strength += 0.15
            elif current_volume < recent_avg_volume * 0.8:  # 成交量萎缩20%
                strength -= 0.1
        
        # 限制在0-1范围内
        return max(0.0, min(1.0, strength))
    
    def get_risk_level(self) -> float:
        """获取策略当前风险等级"""
        base_risk = 0.3  # 基础风险等级
        
        # 根据当前持仓数量调整风险
        position_count = len(self.current_positions)
        risk_adjustment = position_count * 0.1
        
        # 根据最近表现调整风险
        if self.total_trades > 5:
            win_rate = self.winning_trades / self.total_trades
            if win_rate > 0.6:
                risk_adjustment -= 0.1  # 表现好，降低风险
            elif win_rate < 0.4:
                risk_adjustment += 0.2  # 表现差，提高风险
        
        return max(0.1, min(0.8, base_risk + risk_adjustment))
    
    def validate_signal(self, signal: Signal) -> bool:
        """验证信号有效性"""
        try:
            # 基础验证
            if not signal.symbol or signal.strength <= 0:
                return False
            
            # 价格有效性验证
            if signal.entry_price <= 0:
                return False
            
            # 止损止盈合理性验证
            if signal.stop_loss:
                if signal.signal_type == 'buy' and signal.stop_loss >= signal.entry_price:
                    return False
                elif signal.signal_type == 'sell' and signal.stop_loss <= signal.entry_price:
                    return False
            
            # 检查重复信号
            current_time = datetime.now()
            cache_key = f"{signal.symbol}_{signal.signal_type}"
            
            if cache_key in self.signal_cache:
                last_signal_time = self.signal_cache[cache_key]
                if (current_time - last_signal_time).total_seconds() < 300:  # 5分钟内不重复
                    return False
            
            # 更新信号缓存
            self.signal_cache[cache_key] = current_time
            
            return True
            
        except Exception as e:
            self.logger.error(f"信号验证失败: {e}")
            return False
    
    def get_supported_symbols(self) -> List[str]:
        """获取支持的交易对"""
        return self.config.get('supported_symbols', [
            'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'BNB-USDT-SWAP'
        ])
    
    def get_timeframes(self) -> List[str]:
        """获取需要的时间周期"""
        return self.config.get('timeframes', ['5m', '15m'])