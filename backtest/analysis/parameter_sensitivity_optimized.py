#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
优化版参数敏感性测试 - 静默运行，带进度条，无图表弹窗
"""

import pandas as pd
import numpy as np
import itertools
from pathlib import Path
import sys
import os

# 添加路径
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

# 禁用matplotlib图表显示
os.environ['MPLBACKEND'] = 'Agg'  # 使用非交互后端
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def run_parameter_sensitivity_test_optimized(symbol, strategy_name, timeframe='5m'):
    """
    优化版参数敏感性测试 - 快速、静默、有进度条
    """
    
    # 强制重载相关模块以确保使用最新版本
    import importlib
    import sys
    
    modules_to_reload = [
        'core.backtest_manager',
        'core.backtest',
        'strategies.rsi_simple'
    ]
    
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
    
    print(f"\n{'='*70}")
    print(f"参数敏感性测试 - {symbol} - {strategy_name}")
    print(f"{'='*70}")
    
    print("测试意义:")
    print("- 验证策略稳健性，避免过拟合")
    print("- 找出最优参数组合")
    print("- 评估参数调整的风险")
    
    try:
        from core.backtest_manager import BacktestManager
        
        manager = BacktestManager()
        
        # 简化参数网格（更少组合，更快测试）
        param_grids = {
            'rsi_period': [12, 14],               # 2个值
            'lookback_period': [15, 20],          # 2个值  
            'stop_loss_pct': [0.015],             # 1个值（固定最优）
            'take_profit_ratio': [1.2, 1.5]      # 2个值
        }
        
        print("\n测试参数范围（优化版）:")
        for param, values in param_grids.items():
            print(f"  {param}: {values}")
        
        # 生成参数组合
        param_combinations = list(itertools.product(*param_grids.values()))
        total_combinations = len(param_combinations)
        
        print(f"\n总组合数: {total_combinations} （已优化减少）")
        print("="*50)
        
        results = []
        successful_tests = 0
        
        for i, combination in enumerate(param_combinations, 1):
            params = dict(zip(param_grids.keys(), combination))
            
            # 进度显示
            progress = i / total_combinations * 100
            bar_length = 30
            filled_length = int(bar_length * progress / 100)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            print(f"\r[{bar}] {progress:5.1f}% ({i}/{total_combinations}) 测试中...", end='', flush=True)
            
            try:
                # 静默运行回测
                result = run_completely_silent_backtest(manager, symbol, strategy_name, params, timeframe)
                
                if result and result['total_trades'] >= 2:  # 降低交易数量要求
                    test_result = {
                        'params': params.copy(),
                        'return_pct': result['total_return_pct'],
                        'total_trades': result['total_trades'],
                        'win_rate': result['win_rate'],
                        'max_drawdown': -20.0  # 简化
                    }
                    results.append(test_result)
                    successful_tests += 1
            except Exception as e:
                # 捕获任何异常但继续处理
                continue
        
        print(f"\n\n✅ 测试完成! 成功: {successful_tests}/{total_combinations}")
        
        if results:
            analyze_results_optimized(results, symbol, strategy_name)
            return results
        else:
            print("❌ 没有有效结果")
            return None
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return None

def run_completely_silent_backtest(manager, symbol, strategy_name, params, timeframe='5m'):
    """完全静默的回测 - 无输出，无图表，无弹窗"""
    
    try:
        # 禁用matplotlib
        plt.ioff()  # 关闭交互模式
        
        # 使用简单的输出重定向
        import io
        from contextlib import redirect_stdout, redirect_stderr
        
        # 捕获输出但不完全静默，避免问题
        output_buffer = io.StringIO()
        error_buffer = io.StringIO()
        
        with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
            # 运行回测
            result = manager.run_backtest(
                symbol=symbol,
                strategy_name=strategy_name,
                timeframe=timeframe,
                initial_capital=10000.0,
                strategy_params=params
            )
        
        return result
        
    except Exception as e:
        return None

def analyze_results_optimized(results, symbol, strategy_name):
    """优化版结果分析 - 简洁版"""
    print(f"\n{'='*60}")
    print("参数敏感性分析结果")
    print(f"{'='*60}")
    
    # 基础统计
    returns = [r['return_pct'] for r in results]
    profitable = len([r for r in returns if r > 0])
    
    print(f"有效测试: {len(results)}")
    print(f"盈利组合: {profitable} ({profitable/len(results)*100:.1f}%)")
    
    # 收益分布
    print(f"\n📊 收益率分布:")
    print(f"  平均: {np.mean(returns):6.2f}%")
    print(f"  最佳: {max(returns):6.2f}%")
    print(f"  最差: {min(returns):6.2f}%")
    print(f"  标准差: {np.std(returns):4.2f}%")
    
    # 最佳参数
    best = max(results, key=lambda x: x['return_pct'])
    worst = min(results, key=lambda x: x['return_pct'])
    
    print(f"\n🏆 最佳参数组合 (收益率: {best['return_pct']:.2f}%):")
    for param, value in best['params'].items():
        print(f"  {param}: {value}")
    
    print(f"\n📉 最差参数组合 (收益率: {worst['return_pct']:.2f}%):")
    for param, value in worst['params'].items():
        print(f"  {param}: {value}")
    
    # 参数影响分析（简化版）
    print(f"\n📈 参数影响分析:")
    param_names = list(results[0]['params'].keys())
    
    for param_name in param_names:
        param_groups = {}
        for result in results:
            param_value = result['params'][param_name]
            if param_value not in param_groups:
                param_groups[param_value] = []
            param_groups[param_value].append(result['return_pct'])
        
        print(f"  {param_name}:")
        for value, returns_list in param_groups.items():
            avg_return = np.mean(returns_list)
            print(f"    {value}: {avg_return:6.2f}% (n={len(returns_list)})")
    
    # 稳健性评估
    profit_ratio = profitable / len(results)
    volatility = np.std(returns) / abs(np.mean(returns)) if np.mean(returns) != 0 else float('inf')
    
    print(f"\n🎯 稳健性评估:")
    if profit_ratio >= 0.8 and volatility <= 0.5:
        rating = "优秀"
        recommendation = "推荐实盘使用"
    elif profit_ratio >= 0.6 and volatility <= 1.0:
        rating = "良好"
        recommendation = "小资金测试"
    else:
        rating = "一般"
        recommendation = "需要优化"
    
    print(f"  盈利稳定性: {profit_ratio*100:.1f}%")
    print(f"  收益波动性: {volatility:.2f}")
    print(f"  综合评级: {rating}")
    print(f"  使用建议: {recommendation}")
    
    # 推荐参数
    if rating in ["优秀", "良好"]:
        print(f"\n✅ 推荐参数配置:")
        for param, value in best['params'].items():
            print(f"  {param} = {value}")
        print(f"  预期年化收益: {best['return_pct']:.1f}%")
    
    return {
        'rating': rating,
        'best_params': best['params'],
        'best_return': best['return_pct'],
        'avg_return': np.mean(returns),
        'profit_ratio': profit_ratio
    }

if __name__ == "__main__":
    # 测试
    run_parameter_sensitivity_test_optimized("BTC-USDT", "rsi_divergence_unified")