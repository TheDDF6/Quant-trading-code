#!/usr/bin/env python3
"""
波动率突破统一策略 - 用于回测系统
基于布林带的波动率收缩识别和突破入场
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple

# 添加live_trading路径以便导入策略
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "live_trading"))

from strategies.volatility_breakout_unified_adapter import VolatilityBreakoutUnifiedAdapter

def generate_signals(df: pd.DataFrame, 
                    risk_pct: float = 0.02, 
                    take_profit_ratio: float = 2.0,
                    lookback_period: int = 20, 
                    risk_method: str = "fixed_percentage",
                    **kwargs) -> List[Tuple]:
    """
    生成波动率突破交易信号
    
    Args:
        df: OHLCV数据
        risk_pct: 风险百分比
        take_profit_ratio: 止盈比例
        lookback_period: 回看周期
        risk_method: 风险管理方法
        **kwargs: 其他参数
        
    Returns:
        List[Tuple]: 信号列表，格式为 (时间, 价格, 动作, 止损, 止盈, 强度)
    """
    
    # 根据时间框架调整参数
    timeframe = kwargs.get('timeframe', '5m')
    
    # 不同时间框架的参数映射 - 与实盘交易一致
    timeframe_configs = {
        '5m': {
            'bb_period': 20,      # 与实盘一致
            'bb_std': 2.0,        # 与实盘一致
            'bb_threshold': 0.04, # 与实盘一致
            'atr_period': 14,     # 与实盘一致
            'min_signal_strength': 0.005,  # 回测适当放宽，保持逻辑一致
        },
        '15m': {
            'bb_period': 20,      # 与实盘一致
            'bb_std': 2.0,        # 与实盘一致
            'bb_threshold': 0.04, # 与实盘一致
            'atr_period': 14,     # 与实盘一致
            'min_signal_strength': 0.005,  # 回测适当放宽，保持逻辑一致
        },
        '1h': {
            'bb_period': 20,      # 与实盘一致
            'bb_std': 2.0,        # 与实盘一致
            'bb_threshold': 0.04, # 与实盘一致
            'atr_period': 14,     # 与实盘一致
            'min_signal_strength': 0.005,  # 回测适当放宽，保持逻辑一致
        },
        '4h': {
            'bb_period': 20,      # 与实盘一致
            'bb_std': 2.0,        # 与实盘一致
            'bb_threshold': 0.04, # 与实盘一致
            'atr_period': 14,     # 与实盘一致
            'min_signal_strength': 0.005,  # 回测适当放宽，保持逻辑一致
        },
        '1d': {
            'bb_period': 20,      # 与实盘一致
            'bb_std': 2.0,        # 与实盘一致
            'bb_threshold': 0.04, # 与实盘一致
            'atr_period': 14,     # 与实盘一致
            'min_signal_strength': 0.005,  # 回测适当放宽，保持逻辑一致
        }
    }
    
    # 获取时间框架特定配置
    tf_config = timeframe_configs.get(timeframe, timeframe_configs['5m'])
    
    # 创建策略配置
    config = {
        'bb_period': kwargs.get('bb_period', tf_config['bb_period']),
        'bb_std': kwargs.get('bb_std', tf_config['bb_std']),
        'bb_threshold': kwargs.get('bb_threshold', tf_config['bb_threshold']),
        'atr_period': kwargs.get('atr_period', tf_config['atr_period']),
        'stop_loss_mult': kwargs.get('stop_loss_mult', 1.5),
        'trailing_mult': kwargs.get('trailing_mult', 2.0),
        'volume_mult': kwargs.get('volume_mult', 1.5),
        'enable_volume_filter': kwargs.get('enable_volume_filter', False),
        'min_signal_strength': kwargs.get('min_signal_strength', tf_config['min_signal_strength']),
        'supported_symbols': ['BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'BTC-USDT', 'ETH-USDT'],
        'timeframes': ['5m', '15m', '1h', '4h', '1d'],
        'debug': True  # 开启调试以便观察
    }
    
    print(f"使用时间框架 {timeframe} 的优化参数:")
    print(f"  BB周期: {config['bb_period']}, 标准差: {config['bb_std']}, 收缩阈值: {config['bb_threshold']}")
    print(f"  ATR周期: {config['atr_period']}, 最小信号强度: {config['min_signal_strength']}")
    
    # 创建策略实例
    strategy = VolatilityBreakoutUnifiedAdapter(config)
    
    signals = []
    
    # 确保数据有足够的历史
    min_required = max(config['bb_period'], config['atr_period']) + 10
    if len(df) < min_required:
        return signals
    
    try:
        # 添加调试计数器
        analysis_count = 0
        contraction_count = 0
        breakout_count = 0
        signal_count = 0
        
        # 逐步分析数据，模拟实时环境
        step_size = max(1, len(df) // 1000)  # 减少分析频率以提高性能
        
        for i in range(min_required, len(df), step_size):
            analysis_count += 1
            
            # 获取到当前时间点的数据
            current_data = df.iloc[:i+1].copy()
            
            # 调用策略分析
            strategy_signals = strategy.analyze(
                current_data, 
                'BTC-USDT',  # 回测中使用通用符号
                '5m'
            )
            
            # 转换为回测系统需要的格式
            for signal in strategy_signals:
                signal_count += 1
                # 回测系统格式：(时间, 价格, 动作, 止损, 止盈, 强度)
                action = 'buy' if signal.signal_type == 'buy' else 'sell'
                
                signals.append((
                    signal.timestamp,
                    signal.entry_price,
                    action,
                    signal.stop_loss,
                    signal.take_profit,
                    signal.strength
                ))
                
                print(f"+ 生成{action}信号: 时间={signal.timestamp}, 价格={signal.entry_price:.2f}, 强度={signal.strength:.4f}")
        
        # 额外分析：检查最后一段数据的波动率情况
        if len(df) >= 100:
            recent_data = df.iloc[-100:].copy()
            df_with_indicators = strategy.strategy.calculate_indicators(recent_data)
            
            if 'bb_width' in df_with_indicators.columns:
                bb_widths = df_with_indicators['bb_width'].dropna()
                if len(bb_widths) > 0:
                    min_width = bb_widths.min()
                    avg_width = bb_widths.mean()
                    max_width = bb_widths.max()
                    
                    print(f"BB分析 - 最近100根K线布林带宽度:")
                    print(f"   最小宽度: {min_width:.6f} (阈值: {config['bb_threshold']:.6f})")
                    print(f"   平均宽度: {avg_width:.6f}")
                    print(f"   最大宽度: {max_width:.6f}")
                    print(f"   收缩次数: {sum(bb_widths < config['bb_threshold'])} / {len(bb_widths)}")
                
    except Exception as e:
        print(f"生成波动率突破信号失败: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"波动率突破策略分析完成:")
    print(f"   分析次数: {analysis_count}")
    print(f"   生成信号: {len(signals)} 个")
    return signals

def get_strategy_info() -> Dict[str, Any]:
    """获取策略信息"""
    return {
        'name': '波动率突破策略',
        'description': '基于布林带的波动率收缩识别和突破入场策略',
        'version': '1.0.0',
        'risk_methods': ['fixed_percentage', 'recent_extreme'],
        'default_params': {
            'bb_period': 20,
            'bb_std': 2.0,
            'bb_threshold': 0.04,
            'atr_period': 14,
            'stop_loss_mult': 1.5,
            'trailing_mult': 2.0,
            'min_signal_strength': 0.001
        },
        'supported_symbols': ['BTC-USDT', 'ETH-USDT'],
        'timeframes': ['5m', '15m', '1h', '4h', '1d']
    }