#!/usr/bin/env python3
"""
波动率突破策略统一适配器
兼容现有的回测和交易系统
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import logging

from .volatility_breakout_strategy import VolatilityBreakoutStrategy
from .base_strategy import Signal


class VolatilityBreakoutUnifiedAdapter:
    """波动率突破策略统一适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化适配器
        
        Args:
            config: 策略配置参数
        """
        self.config = config
        self.strategy = VolatilityBreakoutStrategy(config)
        
        # 从配置中提取参数
        self.supported_symbols = config.get('supported_symbols', ['BTC-USDT-SWAP'])
        self.timeframes = config.get('timeframes', ['1h'])
        self.risk_method = config.get('risk_method', 'fixed_percentage')
        self.debug = config.get('debug', False)
        
        self.logger = logging.getLogger(__name__)
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
    
    def generate_signals(self, symbol: str, timeframe: str, data: pd.DataFrame) -> List[Signal]:
        """
        生成交易信号 - 回测系统接口
        
        Args:
            symbol: 交易对
            timeframe: 时间周期
            data: OHLCV数据
            
        Returns:
            信号列表
        """
        if symbol not in self.supported_symbols:
            return []
        
        if timeframe not in self.timeframes:
            return []
        
        try:
            signals = self.strategy.analyze(data, symbol, timeframe)
            return signals
        except Exception as e:
            self.logger.error(f"生成信号失败: {e}")
            return []
    
    def analyze(self, data: pd.DataFrame, symbol: str, timeframe: str = '1h') -> List[Signal]:
        """
        分析数据生成信号 - 交易系统接口
        
        Args:
            data: OHLCV数据
            symbol: 交易对
            timeframe: 时间周期
            
        Returns:
            信号列表
        """
        return self.generate_signals(symbol, timeframe, data)
    
    def calculate_position_size(self, signal: Signal, balance: float, 
                              risk_per_trade: float = 0.02) -> float:
        """
        计算仓位大小
        
        Args:
            signal: 交易信号
            balance: 账户余额
            risk_per_trade: 每笔交易风险比例
            
        Returns:
            仓位大小
        """
        if signal.stop_loss <= 0 or signal.entry_price <= 0:
            return 0.0
        
        # 计算价格风险
        if signal.signal_type == 'buy':
            price_risk = signal.entry_price - signal.stop_loss
        else:
            price_risk = signal.stop_loss - signal.entry_price
        
        if price_risk <= 0:
            return 0.0
        
        # 计算风险比例
        risk_ratio = price_risk / signal.entry_price
        
        if risk_ratio <= 0:
            return 0.0
        
        # 计算仓位大小
        risk_amount = balance * risk_per_trade
        position_value = risk_amount / risk_ratio
        position_size = position_value / signal.entry_price
        
        return position_size
    
    def get_strategy_params(self) -> Dict[str, Any]:
        """获取策略参数 - 兼容接口"""
        return self.strategy.get_strategy_info()['parameters']
    
    def get_supported_symbols(self) -> List[str]:
        """获取支持的交易对"""
        return self.supported_symbols
    
    def get_supported_timeframes(self) -> List[str]:
        """获取支持的时间周期"""
        return self.timeframes
    
    def validate_signal(self, signal: Signal) -> bool:
        """验证信号有效性"""
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
    
    def get_strategy_name(self) -> str:
        """获取策略名称"""
        return "volatility_breakout_unified"
    
    def get_strategy_description(self) -> str:
        """获取策略描述"""
        return "波动率收缩/扩张突破策略 - 基于布林带的波动率识别和突破入场"
    
    def should_update_stop_loss(self, current_price: float, entry_price: float, 
                               current_stop: float, signal_type: str) -> Optional[float]:
        """
        移动止损逻辑
        
        Args:
            current_price: 当前价格
            entry_price: 入场价格
            current_stop: 当前止损价格
            signal_type: 信号类型
            
        Returns:
            新的止损价格，None表示不更新
        """
        # 简单的移动止损逻辑
        trailing_mult = self.config.get('trailing_mult', 2.0)
        
        # 这里可以根据ATR动态调整，暂时使用固定比例
        trailing_distance = entry_price * 0.02  # 2%的移动距离
        
        if signal_type == 'buy':
            # 多头位置：价格上涨时上调止损
            if current_price > entry_price * 1.05:  # 盈利5%以上才启动移动止损
                new_stop = current_price - trailing_distance
                if new_stop > current_stop:
                    return new_stop
        else:
            # 空头位置：价格下跌时下调止损
            if current_price < entry_price * 0.95:  # 盈利5%以上才启动移动止损
                new_stop = current_price + trailing_distance
                if new_stop < current_stop:
                    return new_stop
        
        return None