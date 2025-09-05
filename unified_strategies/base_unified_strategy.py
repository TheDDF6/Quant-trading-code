#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一策略基类
支持回测系统和实盘交易系统的通用策略接口
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class UnifiedSignal:
    """统一信号类 - 兼容回测和实盘系统"""
    # 基础信息
    symbol: str
    signal_type: str  # 'buy' or 'sell'
    timestamp: Union[datetime, pd.Timestamp]
    entry_price: float
    
    # 风险管理
    stop_loss: float
    take_profit: float
    
    # 策略信息
    strategy_id: str
    strength: float = 1.0
    confidence: float = 1.0
    
    # 额外信息
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_backtest_format(self) -> Tuple:
        """转换为回测系统格式"""
        return (
            self.timestamp,
            self.entry_price,
            self.signal_type,
            self.stop_loss,
            self.take_profit,
            0  # 回测系统需要的额外参数
        )
    
    def to_live_trading_signal(self):
        """转换为实盘交易系统Signal格式"""
        # 这里需要导入实盘系统的Signal类，暂时返回字典格式
        return {
            'strategy_id': self.strategy_id,
            'symbol': self.symbol,
            'signal_type': self.signal_type,
            'strength': self.strength,
            'timestamp': self.timestamp,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'metadata': self.metadata
        }

class UnifiedStrategy(ABC):
    """统一策略基类"""
    
    def __init__(self, strategy_id: str, config: Dict[str, Any]):
        self.strategy_id = strategy_id
        self.config = config
        
        # 通用参数
        self.lookback_period = config.get('lookback_period', 20)
        self.min_data_points = config.get('min_data_points', 50)
        
    @abstractmethod
    def analyze_market(self, df: pd.DataFrame, symbol: str = "BTC-USDT") -> List[UnifiedSignal]:
        """
        分析市场数据并生成信号
        
        Args:
            df: 市场数据 (OHLCV格式)
            symbol: 交易对名称
            
        Returns:
            List[UnifiedSignal]: 生成的信号列表
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """返回策略名称"""
        pass
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """验证数据质量"""
        if df is None or len(df) < self.min_data_points:
            return False
        
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
            return False
        
        return True
    
    def _find_peaks_and_troughs(self, series: np.ndarray, window: int = 3) -> Tuple[List[int], List[int]]:
        """寻找局部高点和低点 - 统一实现"""
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