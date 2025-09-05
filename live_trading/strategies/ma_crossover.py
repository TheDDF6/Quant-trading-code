# ma_crossover.py - 移动平均线交叉策略
"""
移动平均线交叉策略
经典的双均线交叉策略，适合趋势市场

信号逻辑:
- 快线上穿慢线：买入信号
- 快线下穿慢线：卖出信号
- 结合成交量和RSI过滤信号
"""

import pandas as pd
import numpy as np
import talib
from typing import List, Dict, Any
from datetime import datetime

from strategies.base_strategy import BaseStrategy, Signal

class MovingAverageCrossover(BaseStrategy):
    """移动平均线交叉策略"""
    
    def __init__(self, strategy_id: str, config: Dict[str, Any]):
        """
        初始化移动平均线策略
        
        Args:
            strategy_id: 策略唯一标识
            config: 策略配置
        """
        super().__init__(strategy_id, config)
        
        # 移动平均线参数
        self.fast_period = config.get('fast_period', 10)      # 快线周期
        self.slow_period = config.get('slow_period', 20)      # 慢线周期
        self.ma_type = config.get('ma_type', 'EMA')           # MA类型: SMA, EMA, WMA
        
        # 信号确认参数
        self.rsi_period = config.get('rsi_period', 14)
        self.rsi_neutral_min = config.get('rsi_neutral_min', 40)    # RSI中性区间
        self.rsi_neutral_max = config.get('rsi_neutral_max', 60)
        self.volume_multiplier = config.get('volume_multiplier', 1.2)  # 成交量确认倍数
        
        # 止损止盈参数
        self.stop_loss_pct = config.get('stop_loss_pct', 0.02)       # 2%止损
        self.take_profit_ratio = config.get('take_profit_ratio', 2.0) # 2倍止损的止盈
        self.trailing_stop_pct = config.get('trailing_stop_pct', 0.01) # 1%追踪止损
        
        # 趋势过滤
        self.trend_filter_period = config.get('trend_filter_period', 50)  # 趋势过滤周期
        self.min_trend_strength = config.get('min_trend_strength', 0.005) # 最小趋势强度
        
        # 最少数据要求
        self.min_data_points = max(100, self.trend_filter_period + 20)
        
        self.logger.info(f"移动平均线策略 {strategy_id} 初始化完成 - 快线:{self.fast_period}, 慢线:{self.slow_period}")
    
    def analyze_market(self, market_data: pd.DataFrame, **kwargs) -> List[Signal]:
        """
        分析市场数据生成交易信号
        
        Args:
            market_data: OHLCV数据
            **kwargs: 额外参数
            
        Returns:
            List[Signal]: 生成的信号列表
        """
        symbol = kwargs.get('symbol', 'Unknown')
        
        try:
            # 数据验证
            if len(market_data) < self.min_data_points:
                self.logger.debug(f"数据点不足: {len(market_data)} < {self.min_data_points}")
                return []
            
            # 提取价格数据
            close_prices = market_data['close'].values
            volumes = market_data['volume'].values
            
            # 计算移动平均线
            fast_ma = self._calculate_ma(close_prices, self.fast_period)
            slow_ma = self._calculate_ma(close_prices, self.slow_period)
            trend_ma = self._calculate_ma(close_prices, self.trend_filter_period)
            
            # 计算辅助指标
            rsi = talib.RSI(close_prices, timeperiod=self.rsi_period)
            
            # 检查交叉信号
            signals = self._check_crossover_signals(
                symbol, close_prices, fast_ma, slow_ma, trend_ma, rsi, volumes
            )
            
            return signals
            
        except Exception as e:
            self.logger.error(f"移动平均线策略分析失败 ({symbol}): {e}")
            return []
    
    def _calculate_ma(self, prices: np.ndarray, period: int) -> np.ndarray:
        """计算移动平均线"""
        if self.ma_type == 'SMA':
            return talib.SMA(prices, timeperiod=period)
        elif self.ma_type == 'EMA':
            return talib.EMA(prices, timeperiod=period)
        elif self.ma_type == 'WMA':
            return talib.WMA(prices, timeperiod=period)
        else:
            return talib.EMA(prices, timeperiod=period)  # 默认EMA
    
    def _check_crossover_signals(self, 
                               symbol: str,
                               close_prices: np.ndarray,
                               fast_ma: np.ndarray,
                               slow_ma: np.ndarray,
                               trend_ma: np.ndarray,
                               rsi: np.ndarray,
                               volumes: np.ndarray) -> List[Signal]:
        """检查均线交叉信号"""
        signals = []
        
        if len(fast_ma) < 3 or len(slow_ma) < 3:
            return signals
        
        current_time = datetime.now()
        current_price = close_prices[-1]
        current_fast_ma = fast_ma[-1]
        current_slow_ma = slow_ma[-1]
        current_trend_ma = trend_ma[-1]
        current_rsi = rsi[-1]
        
        # 前一周期的值
        prev_fast_ma = fast_ma[-2]
        prev_slow_ma = slow_ma[-2]
        
        # 检查金叉（看涨信号）
        golden_cross = (prev_fast_ma <= prev_slow_ma and current_fast_ma > current_slow_ma)
        
        # 检查死叉（看跌信号）
        death_cross = (prev_fast_ma >= prev_slow_ma and current_fast_ma < current_slow_ma)
        
        if golden_cross:
            # 金叉买入信号验证
            if self._validate_buy_signal(current_price, current_trend_ma, current_rsi, volumes):
                stop_loss = current_price * (1 - self.stop_loss_pct)
                take_profit = current_price + (current_price - stop_loss) * self.take_profit_ratio
                
                strength = self._calculate_signal_strength(
                    'buy', current_price, current_fast_ma, current_slow_ma, current_rsi, volumes
                )
                
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
                        'signal_reason': 'golden_cross',
                        'fast_ma': current_fast_ma,
                        'slow_ma': current_slow_ma,
                        'rsi': current_rsi,
                        'trend_direction': 'up' if current_price > current_trend_ma else 'down'
                    }
                )
                signals.append(signal)
        
        elif death_cross:
            # 死叉卖出信号验证
            if self._validate_sell_signal(current_price, current_trend_ma, current_rsi, volumes):
                stop_loss = current_price * (1 + self.stop_loss_pct)
                take_profit = current_price - (stop_loss - current_price) * self.take_profit_ratio
                
                strength = self._calculate_signal_strength(
                    'sell', current_price, current_fast_ma, current_slow_ma, current_rsi, volumes
                )
                
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
                        'signal_reason': 'death_cross',
                        'fast_ma': current_fast_ma,
                        'slow_ma': current_slow_ma,
                        'rsi': current_rsi,
                        'trend_direction': 'up' if current_price > current_trend_ma else 'down'
                    }
                )
                signals.append(signal)
        
        return signals
    
    def _validate_buy_signal(self, price: float, trend_ma: float, rsi: float, volumes: np.ndarray) -> bool:
        """验证买入信号"""
        # 趋势过滤：价格应该在长期趋势线之上或接近
        trend_ok = price >= trend_ma * (1 - self.min_trend_strength)
        
        # RSI过滤：避免超买区域买入
        rsi_ok = rsi <= 75  # 不在极度超买区
        
        # 成交量确认
        volume_ok = True
        if len(volumes) >= 20:
            avg_volume = np.mean(volumes[-20:])
            current_volume = volumes[-1]
            volume_ok = current_volume >= avg_volume * 0.8  # 成交量不能太低
        
        return trend_ok and rsi_ok and volume_ok
    
    def _validate_sell_signal(self, price: float, trend_ma: float, rsi: float, volumes: np.ndarray) -> bool:
        """验证卖出信号"""
        # 趋势过滤：价格应该在长期趋势线之下或接近
        trend_ok = price <= trend_ma * (1 + self.min_trend_strength)
        
        # RSI过滤：避免超卖区域卖出
        rsi_ok = rsi >= 25  # 不在极度超卖区
        
        # 成交量确认
        volume_ok = True
        if len(volumes) >= 20:
            avg_volume = np.mean(volumes[-20:])
            current_volume = volumes[-1]
            volume_ok = current_volume >= avg_volume * 0.8  # 成交量不能太低
        
        return trend_ok and rsi_ok and volume_ok
    
    def _calculate_signal_strength(self, 
                                 signal_type: str,
                                 price: float,
                                 fast_ma: float,
                                 slow_ma: float, 
                                 rsi: float,
                                 volumes: np.ndarray) -> float:
        """计算信号强度"""
        strength = 0.5  # 基础强度
        
        # 均线距离评分
        ma_distance = abs(fast_ma - slow_ma) / price
        if ma_distance > 0.01:  # 1%
            strength += 0.2
        elif ma_distance > 0.005:  # 0.5%
            strength += 0.1
        
        # RSI位置评分
        if signal_type == 'buy':
            if 30 <= rsi <= 50:  # 理想买入RSI区间
                strength += 0.2
            elif 50 < rsi <= 60:
                strength += 0.1
        else:  # sell
            if 50 <= rsi <= 70:  # 理想卖出RSI区间
                strength += 0.2
            elif 40 <= rsi < 50:
                strength += 0.1
        
        # 成交量评分
        if len(volumes) >= 10:
            recent_avg_volume = np.mean(volumes[-10:])
            current_volume = volumes[-1]
            volume_ratio = current_volume / recent_avg_volume
            
            if volume_ratio > 1.5:
                strength += 0.15
            elif volume_ratio > 1.2:
                strength += 0.1
            elif volume_ratio < 0.7:
                strength -= 0.1
        
        return max(0.1, min(1.0, strength))
    
    def get_risk_level(self) -> float:
        """获取策略风险等级"""
        base_risk = 0.4  # 均线策略基础风险
        
        # 根据持仓调整
        position_risk = len(self.current_positions) * 0.1
        
        # 根据胜率调整
        if self.total_trades > 10:
            win_rate = self.winning_trades / self.total_trades
            if win_rate > 0.7:
                base_risk -= 0.1
            elif win_rate < 0.3:
                base_risk += 0.2
        
        return max(0.2, min(0.7, base_risk + position_risk))
    
    def validate_signal(self, signal: Signal) -> bool:
        """验证信号有效性"""
        try:
            # 基础验证
            if not signal.symbol or signal.strength <= 0.3:  # 最低强度要求
                return False
            
            # 价格合理性
            if signal.entry_price <= 0:
                return False
            
            # 止损止盈合理性
            if signal.stop_loss:
                if signal.signal_type == 'buy':
                    if signal.stop_loss >= signal.entry_price:
                        return False
                elif signal.signal_type == 'sell':
                    if signal.stop_loss <= signal.entry_price:
                        return False
            
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
        return self.config.get('timeframes', ['15m', '1h'])