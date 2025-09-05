#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一RSI背离策略的实盘交易系统适配器
实现标准化策略接口，集成统一策略逻辑
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from datetime import datetime
import logging

# 添加统一策略模块路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from strategies.base_strategy import BaseStrategy, Signal
from unified_strategies.rsi_divergence_unified import RSIDivergenceUnified

class RSIDivergenceUnifiedAdapter(BaseStrategy):
    """统一RSI背离策略的实盘交易适配器"""
    
    def __init__(self, strategy_id: str, config: Dict[str, Any]):
        """
        初始化统一RSI背离策略适配器
        
        Args:
            strategy_id: 策略唯一标识
            config: 策略配置
        """
        super().__init__(strategy_id, config)
        
        # 创建统一策略实例
        unified_config = config.copy()
        unified_config['debug'] = False  # 实盘不需要调试输出
        
        self.unified_strategy = RSIDivergenceUnified(strategy_id, unified_config)
        
        # 继承配置
        self.rsi_period = unified_config.get('rsi_period', 14)
        self.lookback_period = unified_config.get('lookback_period', 20)
        self.stop_loss_pct = unified_config.get('stop_loss_pct', 0.015)
        self.take_profit_ratio = unified_config.get('take_profit_ratio', 1.5)
        self.min_signal_strength = unified_config.get('min_signal_strength', 0.6)
        
        # 支持的交易对和时间框架
        self.supported_symbols = unified_config.get('supported_symbols', ['BTC-USDT-SWAP'])
        self.timeframes = unified_config.get('timeframes', ['5m'])
        
        self.logger.info(f"统一RSI背离策略适配器初始化完成: {strategy_id}")
    
    def get_supported_symbols(self) -> List[str]:
        """获取支持的交易对"""
        return self.supported_symbols
    
    def get_required_timeframes(self) -> List[str]:
        """获取需要的时间框架"""
        return self.timeframes
    
    def analyze_market(self, market_data: pd.DataFrame, symbol: str = None) -> List[Signal]:
        """
        分析市场数据并生成信号
        
        Args:
            market_data: 市场数据 (OHLCV格式)
            symbol: 交易对名称
            
        Returns:
            List[Signal]: 生成的信号列表
        """
        try:
            if symbol is None:
                symbol = self.supported_symbols[0] if self.supported_symbols else "BTC-USDT-SWAP"
            
            # 使用统一策略分析市场
            unified_signals = self.unified_strategy.analyze_market(market_data, symbol)
            
            # 转换为实盘交易系统的Signal格式
            live_signals = []
            for unified_signal in unified_signals:
                live_signal = Signal(
                    strategy_id=unified_signal.strategy_id,
                    symbol=unified_signal.symbol,
                    signal_type=unified_signal.signal_type,
                    strength=unified_signal.strength,
                    timestamp=unified_signal.timestamp,
                    entry_price=unified_signal.entry_price,
                    stop_loss=unified_signal.stop_loss,
                    take_profit=unified_signal.take_profit,
                    metadata=unified_signal.metadata or {}
                )
                live_signals.append(live_signal)
            
            if live_signals and self.logger:
                self.logger.info(f"生成 {len(live_signals)} 个信号 ({symbol})")
            
            return live_signals
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"市场分析失败 ({symbol}): {e}")
            return []
    
    def validate_signal(self, signal: Signal) -> bool:
        """验证信号有效性"""
        try:
            # 基本验证
            if not signal or not signal.symbol or not signal.signal_type:
                return False
            
            # 价格验证
            if signal.entry_price <= 0 or signal.stop_loss <= 0 or signal.take_profit <= 0:
                return False
            
            # 止损止盈逻辑验证
            if signal.signal_type == 'buy':
                if signal.stop_loss >= signal.entry_price or signal.take_profit <= signal.entry_price:
                    return False
            else:  # sell
                if signal.stop_loss <= signal.entry_price or signal.take_profit >= signal.entry_price:
                    return False
            
            # 信号强度验证
            if signal.strength < self.min_signal_strength:
                return False
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"信号验证失败: {e}")
            return False
    
    def calculate_position_size(self, signal: Signal, available_balance: float) -> float:
        """
        计算仓位大小
        
        Args:
            signal: 交易信号
            available_balance: 可用资金
            
        Returns:
            float: 计算的仓位大小
        """
        try:
            # 基于固定风险百分比计算仓位
            risk_amount = available_balance * self.config.get('risk_per_trade', 0.02)
            
            # 计算每单位的风险
            if signal.signal_type == 'buy':
                risk_per_unit = signal.entry_price - signal.stop_loss
            else:  # sell
                risk_per_unit = signal.stop_loss - signal.entry_price
            
            if risk_per_unit <= 0:
                return 0
            
            # 计算仓位大小
            position_size = risk_amount / risk_per_unit
            
            # 应用最大仓位限制
            max_position_value = available_balance * self.config.get('max_position_size', 0.8)
            max_position_size = max_position_value / signal.entry_price
            
            position_size = min(position_size, max_position_size)
            
            return max(0, position_size)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"仓位计算失败: {e}")
            return 0
    
    def get_risk_level(self) -> float:
        """
        获取策略当前风险等级
        
        Returns:
            float: 风险等级 (0.0-1.0, 越高风险越大)
        """
        # RSI背离策略的风险等级计算
        base_risk = 0.3  # 基础风险等级
        
        # 基于止损百分比调整风险
        stop_loss_risk = min(self.stop_loss_pct * 10, 0.3)  # 最多增加30%风险
        
        # 基于杠杆调整风险（如果有配置的话）
        leverage_risk = 0.0
        max_leverage = self.config.get('max_leverage', 1)
        if max_leverage > 1:
            leverage_risk = min((max_leverage - 1) * 0.05, 0.4)  # 杠杆风险
        
        total_risk = min(base_risk + stop_loss_risk + leverage_risk, 1.0)
        return total_risk
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取策略统计信息"""
        base_stats = super().get_statistics()
        
        # 添加统一策略特定的统计信息
        unified_stats = {
            'strategy_type': 'RSI Divergence Unified',
            'rsi_period': self.rsi_period,
            'lookback_period': self.lookback_period,
            'stop_loss_pct': self.stop_loss_pct,
            'take_profit_ratio': self.take_profit_ratio,
            'min_signal_strength': self.min_signal_strength,
            'risk_method': self.unified_strategy.risk_method,
            'supported_symbols': self.supported_symbols,
            'timeframes': self.timeframes
        }
        
        base_stats.update(unified_stats)
        return base_stats