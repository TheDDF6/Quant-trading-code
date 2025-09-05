#!/usr/bin/env python3
"""
RSI背离策略的包装器 - 用于backtest目录
解决相对导入问题
"""

import sys
from pathlib import Path
import importlib.util

def generate_signals(df, stop_loss_pct=0.015, take_profit_ratio=1.5, lookback=20, risk_method='fixed_percentage', **kwargs):
    """
    RSI背离策略信号生成的包装器函数
    """
    try:
        # 直接从文件加载RSI策略
        rsi_file = Path(__file__).parent.parent.parent / "unified_strategies" / "rsi_divergence_unified.py"
        
        if not rsi_file.exists():
            print(f"RSI策略文件不存在: {rsi_file}")
            return []
        
        # 临时添加路径
        old_path = sys.path.copy()
        parent_dir = rsi_file.parent.parent
        sys.path.insert(0, str(parent_dir))
        
        try:
            # 导入RSI策略模块
            spec = importlib.util.spec_from_file_location("rsi_divergence_unified", rsi_file)
            rsi_module = importlib.util.module_from_spec(spec)
            
            # 设置模块的__package__属性避免相对导入问题
            rsi_module.__package__ = "unified_strategies"
            
            # 执行模块
            spec.loader.exec_module(rsi_module)
            
            # 调用原始函数
            return rsi_module.generate_signals(
                df=df,
                stop_loss_pct=stop_loss_pct,
                take_profit_ratio=take_profit_ratio,
                lookback=lookback,
                risk_method=risk_method,
                **kwargs
            )
            
        finally:
            # 恢复路径
            sys.path = old_path
            
    except Exception as e:
        print(f"RSI策略包装器执行失败: {e}")
        import traceback
        traceback.print_exc()
        return []