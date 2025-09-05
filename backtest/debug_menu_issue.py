#!/usr/bin/env python3
"""
调试菜单系统参数敏感性测试问题
"""

import sys
import os
from pathlib import Path

# 设置工作目录
script_dir = Path(__file__).parent
os.chdir(script_dir)
sys.path.insert(0, str(script_dir))

print(f"当前工作目录: {os.getcwd()}")

def debug_backtest_manager():
    """调试回测管理器"""
    try:
        from core.backtest_manager import BacktestManager
        
        manager = BacktestManager()
        
        # 测试基本功能
        strategies = manager.get_available_strategies()
        print(f"可用策略数: {len(strategies)}")
        
        symbols = manager.get_available_symbols()
        print(f"可用交易对: {symbols}")
        
        # 测试单个回测
        params = {'rsi_period': 12, 'lookback_period': 15, 'stop_loss_pct': 0.015, 'take_profit_ratio': 1.2}
        print(f"\\n测试单个回测...")
        
        result = manager.run_backtest(
            symbol='BTC-USDT',
            strategy_name='rsi_divergence_unified',
            timeframe='5m',
            initial_capital=10000.0,
            strategy_params=params
        )
        
        print(f"回测结果: {type(result)}")
        if result:
            print(f"交易数: {result.get('total_trades', '无')}")
            print(f"收益率: {result.get('total_return_pct', '无')}")
        
        return result
        
    except Exception as e:
        print(f"回测管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def debug_silent_function():
    """调试静默回测函数"""
    try:
        from core.backtest_manager import BacktestManager
        from analysis.parameter_sensitivity_optimized import run_completely_silent_backtest
        
        manager = BacktestManager()
        params = {'rsi_period': 12, 'lookback_period': 15, 'stop_loss_pct': 0.015, 'take_profit_ratio': 1.2}
        
        print(f"\\n测试静默回测函数...")
        result = run_completely_silent_backtest(manager, 'BTC-USDT', 'rsi_divergence_unified', params, '5m')
        
        print(f"静默回测结果: {type(result)}")
        if result:
            print(f"交易数: {result.get('total_trades', '无')}")
            print(f"收益率: {result.get('total_return_pct', '无')}")
        else:
            print("静默回测返回None!")
        
        return result
        
    except Exception as e:
        print(f"静默回测测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def debug_import_paths():
    """调试导入路径"""
    print(f"\\n调试导入路径:")
    print(f"sys.path前5个: {sys.path[:5]}")
    
    # 检查关键模块的位置
    try:
        import core.backtest_manager
        print(f"backtest_manager位置: {core.backtest_manager.__file__}")
    except:
        print("无法导入backtest_manager")
    
    try:
        import analysis.parameter_sensitivity_optimized
        print(f"parameter_sensitivity位置: {analysis.parameter_sensitivity_optimized.__file__}")
    except:
        print("无法导入parameter_sensitivity_optimized")

if __name__ == "__main__":
    print("=" * 60)
    print("调试菜单系统参数敏感性测试问题")
    print("=" * 60)
    
    # 1. 调试导入路径
    debug_import_paths()
    
    # 2. 调试回测管理器
    result1 = debug_backtest_manager()
    
    # 3. 调试静默回测函数
    result2 = debug_silent_function()
    
    print(f"\\n总结:")
    print(f"- 回测管理器结果: {'正常' if result1 else '异常'}")
    print(f"- 静默回测结果: {'正常' if result2 else '异常'}")
    
    print("\\n调试完成")