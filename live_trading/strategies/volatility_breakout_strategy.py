#!/usr/bin/env python3
"""
波动率收缩/扩张策略 (Volatility Breakout)
基于布林带的波动率收缩识别和突破入场
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
import logging

from .base_strategy import BaseStrategy, Signal


class VolatilityBreakoutStrategy(BaseStrategy):
    """波动率收缩/扩张策略"""
    
    def __init__(self, strategy_id: str = None, config: Dict[str, Any] = None):
        """
        初始化策略
        
        Args:
            strategy_id: 策略ID
            config: 策略配置
                - bb_period: 布林带周期 (默认20)
                - bb_std: 布林带标准差倍数 (默认2.0)
                - bb_threshold: 带宽收缩阈值 (默认0.04, 即4%)
                - atr_period: ATR周期 (默认14)
                - stop_loss_mult: 止损倍数 (默认1.5 * ATR)
                - trailing_mult: 移动止盈倍数 (默认2.0 * ATR)
                - volume_mult: 成交量放大倍数 (默认1.5)
                - enable_volume_filter: 是否启用成交量过滤 (默认False)
                - min_signal_strength: 最小信号强度 (默认0.6)
        """
        # 兼容性处理：如果第一个参数是字典，则视为config
        if isinstance(strategy_id, dict) and config is None:
            config = strategy_id
            strategy_id = config.get('strategy_id', 'volatility_breakout')
        elif config is None:
            config = {}
        elif strategy_id is None:
            strategy_id = config.get('strategy_id', 'volatility_breakout')
        
        super().__init__(strategy_id, config)
        
        # 布林带参数
        self.bb_period = config.get('bb_period', 20)
        self.bb_std = config.get('bb_std', 2.0)
        self.bb_threshold = config.get('bb_threshold', 0.04)  # 4%
        
        # ATR参数
        self.atr_period = config.get('atr_period', 14)
        self.stop_loss_mult = config.get('stop_loss_mult', 1.5)
        self.trailing_mult = config.get('trailing_mult', 2.0)
        
        # 成交量过滤参数
        self.volume_mult = config.get('volume_mult', 1.5)
        self.enable_volume_filter = config.get('enable_volume_filter', False)
        
        # 信号强度参数
        self.min_signal_strength = config.get('min_signal_strength', 0.6)
        
        # 调试模式
        self.debug = config.get('debug', False)
        
        # 内部状态
        self.last_signal_time = None
        self.position_side = None
        
        self.logger = logging.getLogger(__name__)
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        if len(data) < max(self.bb_period, self.atr_period) + 5:
            return data
        
        df = data.copy()
        
        # 计算布林带
        df['bb_middle'] = df['close'].rolling(window=self.bb_period).mean()
        df['bb_std'] = df['close'].rolling(window=self.bb_period).std()
        df['bb_upper'] = df['bb_middle'] + (self.bb_std * df['bb_std'])
        df['bb_lower'] = df['bb_middle'] - (self.bb_std * df['bb_std'])
        
        # 计算布林带宽度
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # 计算ATR
        df['hl'] = df['high'] - df['low']
        df['hc'] = abs(df['high'] - df['close'].shift(1))
        df['lc'] = abs(df['low'] - df['close'].shift(1))
        df['true_range'] = df[['hl', 'hc', 'lc']].max(axis=1)
        df['atr'] = df['true_range'].rolling(window=self.atr_period).mean()
        
        # 计算成交量均值（用于成交量过滤）
        if 'volume' in df.columns and self.enable_volume_filter:
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
        
        # 清理临时列
        df.drop(['hl', 'hc', 'lc', 'true_range'], axis=1, inplace=True)
        
        return df
    
    def identify_volatility_contraction(self, data: pd.DataFrame, index: int) -> bool:
        """识别波动率收缩"""
        if index < self.bb_period:
            return False
        
        current_width = data.iloc[index]['bb_width']
        
        # 检查布林带宽度是否低于阈值
        is_contracted = current_width < self.bb_threshold
        
        if self.debug and is_contracted:
            self.logger.debug(f"波动率收缩: 带宽={current_width:.4f} < 阈值={self.bb_threshold:.4f}")
        
        return is_contracted
    
    def check_breakout_conditions(self, data: pd.DataFrame, index: int) -> Tuple[bool, str, float]:
        """检查突破条件"""
        if index < max(self.bb_period, self.atr_period):
            return False, None, 0.0
        
        row = data.iloc[index]
        close_price = row['close']
        bb_upper = row['bb_upper']
        bb_lower = row['bb_lower']
        
        # 检查向上突破
        if close_price > bb_upper:
            signal_strength = (close_price - bb_upper) / bb_upper
            return True, 'buy', signal_strength
        
        # 检查向下突破
        elif close_price < bb_lower:
            signal_strength = (bb_lower - close_price) / bb_lower
            return True, 'sell', signal_strength
        
        return False, None, 0.0
    
    def check_volume_confirmation(self, data: pd.DataFrame, index: int) -> bool:
        """检查成交量确认"""
        if not self.enable_volume_filter or 'volume' not in data.columns:
            return True
        
        if index < 20:  # 需要足够的历史数据计算成交量均值
            return True
        
        row = data.iloc[index]
        current_volume = row['volume']
        avg_volume = row['volume_sma']
        
        if pd.isna(avg_volume) or avg_volume <= 0:
            return True
        
        volume_ratio = current_volume / avg_volume
        is_confirmed = volume_ratio >= self.volume_mult
        
        if self.debug:
            self.logger.debug(f"成交量确认: {current_volume:.0f} / {avg_volume:.0f} = {volume_ratio:.2f}, 确认={is_confirmed}")
        
        return is_confirmed
    
    def calculate_stop_loss_take_profit(self, data: pd.DataFrame, index: int, 
                                      entry_price: float, signal_type: str) -> Tuple[float, float]:
        """计算止损和止盈价格"""
        if index >= len(data):
            index = len(data) - 1
        
        row = data.iloc[index]
        atr = row['atr']
        
        if pd.isna(atr) or atr <= 0:
            # 如果ATR无效，使用固定百分比
            if signal_type == 'buy':
                stop_loss = entry_price * 0.97  # -3%
                take_profit = entry_price * 1.08  # +8%
            else:
                stop_loss = entry_price * 1.03  # +3%
                take_profit = entry_price * 0.92  # -8%
        else:
            # 使用ATR计算
            if signal_type == 'buy':
                stop_loss = entry_price - (self.stop_loss_mult * atr)
                take_profit = entry_price + (self.trailing_mult * atr)
            else:
                stop_loss = entry_price + (self.stop_loss_mult * atr)
                take_profit = entry_price - (self.trailing_mult * atr)
        
        return stop_loss, take_profit
    
    def analyze(self, data: pd.DataFrame, symbol: str, timeframe: str = '1h') -> List[Signal]:
        """主要分析方法"""
        if len(data) < max(self.bb_period, self.atr_period) + 5:
            if self.debug:
                self.logger.debug(f"数据不足，需要至少 {max(self.bb_period, self.atr_period) + 5} 根K线")
            return []
        
        # 计算技术指标
        df = self.calculate_indicators(data)
        signals = []
        
        # 分析最新的数据点
        current_index = len(df) - 1
        current_time = df.index[current_index]
        
        # 避免在同一时间生成重复信号
        if self.last_signal_time == current_time:
            return []
        
        # 检查最近是否有过波动率收缩
        recent_contracted = False
        lookback = min(10, current_index)  # 检查最近10根K线
        for i in range(max(0, current_index - lookback), current_index + 1):
            if self.identify_volatility_contraction(df, i):
                recent_contracted = True
                break
        
        if not recent_contracted:
            if self.debug:
                current_width = df.iloc[current_index]['bb_width']
                self.logger.debug(f"最近未出现波动率收缩: 当前带宽={current_width:.4f}, 阈值={self.bb_threshold:.4f}")
            return []
        
        # 检查突破条件
        has_breakout, signal_type, signal_strength = self.check_breakout_conditions(df, current_index)
        if not has_breakout:
            if self.debug:
                self.logger.debug("未检测到有效突破")
            return []
        
        # 检查信号强度
        if signal_strength < self.min_signal_strength:
            if self.debug:
                self.logger.debug(f"信号强度不足: {signal_strength:.4f} < {self.min_signal_strength}")
            return []
        
        # 检查成交量确认
        if not self.check_volume_confirmation(df, current_index):
            if self.debug:
                self.logger.debug("成交量确认失败")
            return []
        
        # 获取当前价格
        entry_price = df.iloc[current_index]['close']
        
        # 计算止损和止盈
        stop_loss, take_profit = self.calculate_stop_loss_take_profit(
            df, current_index, entry_price, signal_type
        )
        
        # 创建交易信号
        signal = Signal(
            strategy_id=self.config.get('strategy_id', 'volatility_breakout'),
            symbol=symbol,
            signal_type=signal_type,
            strength=signal_strength,  # 使用 strength 字段
            timestamp=current_time,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata={
                'bb_width': df.iloc[current_index]['bb_width'],
                'bb_upper': df.iloc[current_index]['bb_upper'],
                'bb_lower': df.iloc[current_index]['bb_lower'],
                'atr': df.iloc[current_index]['atr'],
                'breakout_type': 'upper' if signal_type == 'buy' else 'lower',
                'volume_confirmed': self.check_volume_confirmation(df, current_index),
                'timeframe': timeframe
            }
        )
        
        signals.append(signal)
        self.last_signal_time = current_time
        self.position_side = signal_type
        
        if self.debug:
            self.logger.info(f"生成{signal_type}信号: 价格={entry_price:.2f}, 止损={stop_loss:.2f}, "
                           f"止盈={take_profit:.2f}, 强度={signal_strength:.4f}")
        
        return signals
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        return {
            'name': 'Volatility Breakout',
            'description': '波动率收缩/扩张突破策略',
            'version': '1.0.0',
            'parameters': {
                'bb_period': self.bb_period,
                'bb_std': self.bb_std,
                'bb_threshold': self.bb_threshold,
                'atr_period': self.atr_period,
                'stop_loss_mult': self.stop_loss_mult,
                'trailing_mult': self.trailing_mult,
                'volume_mult': self.volume_mult,
                'enable_volume_filter': self.enable_volume_filter,
                'min_signal_strength': self.min_signal_strength
            },
            'supported_timeframes': ['5m', '15m', '1h', '4h', '1d'],
            'supported_symbols': ['BTC-USDT-SWAP', 'ETH-USDT-SWAP'],
            'risk_level': 'medium'
        }
    
    # 实现BaseStrategy的抽象方法
    def analyze_market(self, market_data: pd.DataFrame, **kwargs) -> List[Signal]:
        """分析市场数据并生成交易信号 - BaseStrategy抽象方法实现"""
        symbol = kwargs.get('symbol', 'BTC-USDT-SWAP')
        timeframe = kwargs.get('timeframe', '1h')
        return self.analyze(market_data, symbol, timeframe)
    
    def get_risk_level(self) -> float:
        """获取策略当前风险等级 - BaseStrategy抽象方法实现"""
        # 根据当前持仓情况返回风险等级
        if self.position_side:
            return 0.7  # 有持仓时风险较高
        else:
            return 0.3  # 无持仓时风险较低
    
    def validate_signal(self, signal: Signal) -> bool:
        """验证交易信号的有效性 - BaseStrategy抽象方法实现"""
        if not signal:
            return False
        
        # 检查必要字段
        if not all([signal.symbol, signal.signal_type, signal.entry_price, 
                   signal.stop_loss, signal.take_profit]):
            return False
        
        # 检查价格合理性
        if signal.entry_price <= 0 or signal.stop_loss <= 0 or signal.take_profit <= 0:
            return False
        
        # 检查止损止盈方向
        if signal.signal_type == 'buy':
            if signal.stop_loss >= signal.entry_price or signal.take_profit <= signal.entry_price:
                return False
        else:
            if signal.stop_loss <= signal.entry_price or signal.take_profit >= signal.entry_price:
                return False
        
        return True