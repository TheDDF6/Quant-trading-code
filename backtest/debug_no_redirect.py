#!/usr/bin/env python3
"""
测试不重定向输出的回测
"""

import sys
import os
from pathlib import Path
import itertools

# 设置正确的工作目录
script_dir = Path(__file__).parent
os.chdir(script_dir)
sys.path.insert(0, str(script_dir))

def test_backtest_without_redirect():
    """测试不重定向输出的回测"""
    try:
        from core.backtest_manager import BacktestManager
        
        manager = BacktestManager()
        
        # 测试一个参数组合
        params = {'rsi_period': 12, 'lookback_period': 15, 'stop_loss_pct': 0.015, 'take_profit_ratio': 1.2}
        
        print(f"测试参数: {params}")
        print("开始运行回测...")
        
        result = manager.run_backtest(
            symbol='BTC-USDT',
            strategy_name='rsi_divergence_unified',
            timeframe='5m',
            initial_capital=10000.0,
            strategy_params=params
        )
        
        print(f"回测结果类型: {type(result)}")
        if result:
            print(f"结果键: {list(result.keys())}")
            print(f"交易数: {result.get('total_trades', '无此键')}")
            print(f"收益率: {result.get('total_return_pct', '无此键')}")
            return result
        else:
            print("回测返回None")
            return None
            
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_backtest_with_simple_redirect():
    """测试简单重定向的回测"""
    try:
        from core.backtest_manager import BacktestManager
        
        manager = BacktestManager()
        
        # 测试一个参数组合
        params = {'rsi_period': 12, 'lookback_period': 15, 'stop_loss_pct': 0.015, 'take_profit_ratio': 1.2}
        
        print(f"\\n测试简单重定向版本...")
        print(f"测试参数: {params}")
        
        # 简单的输出重定向
        import io
        from contextlib import redirect_stdout
        
        # 捕获输出但不完全静默
        output_buffer = io.StringIO()
        
        with redirect_stdout(output_buffer):
            result = manager.run_backtest(
                symbol='BTC-USDT',
                strategy_name='rsi_divergence_unified',
                timeframe='5m',
                initial_capital=10000.0,
                strategy_params=params
            )
        
        print(f"回测结果类型: {type(result)}")
        if result:
            print(f"结果键: {list(result.keys())}")
            print(f"交易数: {result.get('total_trades', '无此键')}")
            print(f"收益率: {result.get('total_return_pct', '无此键')}")
            print(f"输出长度: {len(output_buffer.getvalue())}字符")
            return result
        else:
            print("回测返回None")
            print(f"捕获的输出: {output_buffer.getvalue()[:200]}...")
            return None
            
    except Exception as e:
        print(f"简单重定向测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("测试不重定向输出的回测")
    print("=" * 60)
    
    # 测试1：不重定向输出
    print("\\n1. 测试不重定向输出:")
    result1 = test_backtest_without_redirect()
    
    # 测试2：简单重定向
    print("\\n2. 测试简单重定向:")
    result2 = test_backtest_with_simple_redirect()
    
    print("\\n调试完成")