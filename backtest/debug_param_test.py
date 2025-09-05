#!/usr/bin/env python3
"""
调试参数敏感性测试问题
"""

import sys
import os
from pathlib import Path

# 设置正确的工作目录
script_dir = Path(__file__).parent
os.chdir(script_dir)
sys.path.insert(0, str(script_dir))

print(f"当前工作目录: {os.getcwd()}")
print(f"Python路径: {sys.path[:3]}")

def debug_single_backtest():
    """调试单个回测"""
    try:
        from core.backtest_manager import BacktestManager
        
        manager = BacktestManager()
        params = {'rsi_period': 12, 'lookback_period': 15, 'stop_loss_pct': 0.015, 'take_profit_ratio': 1.2}
        
        print(f"\n测试参数: {params}")
        result = manager.run_backtest('BTC-USDT', 'rsi_divergence_unified', 
                                    timeframe='5m', strategy_params=params)
        
        print(f"回测结果类型: {type(result)}")
        if result:
            print(f"结果键: {result.keys() if isinstance(result, dict) else '不是字典'}")
            print(f"交易数: {result.get('total_trades', '无此键') if isinstance(result, dict) else '无法获取'}")
            print(f"收益率: {result.get('total_return_pct', '无此键') if isinstance(result, dict) else '无法获取'}")
            return result
        else:
            print("回测返回None")
            return None
            
    except Exception as e:
        print(f"调试回测失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def debug_silent_backtest():
    """调试静默回测"""
    try:
        from core.backtest_manager import BacktestManager
        from analysis.parameter_sensitivity_optimized import run_completely_silent_backtest
        
        manager = BacktestManager()
        params = {'rsi_period': 12, 'lookback_period': 15, 'stop_loss_pct': 0.015, 'take_profit_ratio': 1.2}
        
        print(f"\n测试静默回测，参数: {params}")
        result = run_completely_silent_backtest(manager, 'BTC-USDT', 'rsi_divergence_unified', params, '5m')
        
        print(f"静默回测结果类型: {type(result)}")
        if result:
            print(f"结果键: {result.keys() if isinstance(result, dict) else '不是字典'}")
            print(f"交易数: {result.get('total_trades', '无此键') if isinstance(result, dict) else '无法获取'}")
            print(f"收益率: {result.get('total_return_pct', '无此键') if isinstance(result, dict) else '无法获取'}")
            return result
        else:
            print("静默回测返回None")
            return None
            
    except Exception as e:
        print(f"调试静默回测失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def debug_param_sensitivity():
    """调试参数敏感性测试"""
    try:
        from analysis.parameter_sensitivity_optimized import run_parameter_sensitivity_test_optimized
        
        print("\n运行完整参数敏感性测试:")
        result = run_parameter_sensitivity_test_optimized('BTC-USDT', 'rsi_divergence_unified', timeframe='5m')
        print(f"参数敏感性测试结果: {result}")
        return result
        
    except Exception as e:
        print(f"调试参数敏感性测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("调试参数敏感性测试问题")
    print("=" * 60)
    
    # 1. 测试单个回测
    print("\n1. 测试单个回测（非静默）:")
    result1 = debug_single_backtest()
    
    # 2. 测试静默回测
    print("\n2. 测试静默回测:")
    result2 = debug_silent_backtest()
    
    # 3. 测试完整参数敏感性
    print("\n3. 测试完整参数敏感性:")
    result3 = debug_param_sensitivity()
    
    print("\n调试完成")