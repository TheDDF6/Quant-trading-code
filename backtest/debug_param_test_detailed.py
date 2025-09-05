#!/usr/bin/env python3
"""
详细调试参数敏感性测试问题
"""

import sys
import os
from pathlib import Path
import itertools

# 设置正确的工作目录
script_dir = Path(__file__).parent
os.chdir(script_dir)
sys.path.insert(0, str(script_dir))

def debug_param_sensitivity_step_by_step():
    """逐步调试参数敏感性测试"""
    try:
        from core.backtest_manager import BacktestManager
        from analysis.parameter_sensitivity_optimized import run_completely_silent_backtest
        
        manager = BacktestManager()
        
        # 参数网格
        param_grids = {
            'rsi_period': [12, 14],
            'lookback_period': [15, 20],
            'stop_loss_pct': [0.015],
            'take_profit_ratio': [1.2, 1.5]
        }
        
        param_combinations = list(itertools.product(*param_grids.values()))
        print(f"参数组合总数: {len(param_combinations)}")
        
        results = []
        successful_tests = 0
        
        for i, combination in enumerate(param_combinations, 1):
            params = dict(zip(param_grids.keys(), combination))
            
            print(f"\n=== 测试组合 {i}/8 ===")
            print(f"参数: {params}")
            
            try:
                # 静默运行回测
                result = run_completely_silent_backtest(manager, 'BTC-USDT', 'rsi_divergence_unified', params, '5m')
                
                print(f"回测结果类型: {type(result)}")
                if result is None:
                    print("❌ result为None")
                    continue
                elif not isinstance(result, dict):
                    print(f"❌ result不是字典，是{type(result)}")
                    continue
                else:
                    print(f"✅ result是字典，键: {list(result.keys())}")
                    
                    if 'total_trades' not in result:
                        print("❌ result缺少total_trades字段")
                        continue
                    
                    total_trades = result['total_trades']
                    print(f"交易数: {total_trades}")
                    
                    if total_trades < 2:
                        print(f"❌ 交易数{total_trades}不足2")
                        continue
                    
                    print("✅ 满足条件，添加到结果中")
                    
                    test_result = {
                        'params': params.copy(),
                        'return_pct': result['total_return_pct'],
                        'total_trades': result['total_trades'],
                        'win_rate': result['win_rate'],
                        'max_drawdown': -20.0
                    }
                    results.append(test_result)
                    successful_tests += 1
                    
            except Exception as e:
                print(f"❌ 异常: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"\n最终统计: 成功 {successful_tests}/{len(param_combinations)}")
        print(f"结果列表长度: {len(results)}")
        
        return results
        
    except Exception as e:
        print(f"调试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("详细调试参数敏感性测试")
    print("=" * 60)
    
    results = debug_param_sensitivity_step_by_step()
    
    if results:
        print(f"\n成功结果: {len(results)}个")
        for i, result in enumerate(results, 1):
            print(f"  {i}. 收益率: {result['return_pct']:.2f}%, 交易数: {result['total_trades']}")
    else:
        print("\n没有成功结果")
    
    print("\n调试完成")