#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
动态参数敏感性测试 - 支持用户选择币对和策略的参数稳健性验证
"""

import pandas as pd
import numpy as np
import itertools
from pathlib import Path
import sys

# 添加路径
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

def run_parameter_sensitivity_test(symbol, strategy_name):
    """
    运行动态参数敏感性测试
    
    Args:
        symbol: 交易对
        strategy_name: 策略名称
    """
    print(f"\n{'='*70}")
    print(f"参数敏感性测试 - {symbol} - {strategy_name}")
    print(f"{'='*70}")
    
    print("参数敏感性测试的重要意义:")
    print("- 避免过拟合: 验证策略是否过度依赖特定参数")
    print("- 评估稳健性: 测试参数变化时策略表现的稳定性")
    print("- 优化边界: 找出有效参数范围，指导实际使用")
    print("- 风险控制: 了解参数调整的潜在风险")
    
    try:
        from core.backtest_manager import BacktestManager
        from core.backtest import load_and_prepare_data
        
        manager = BacktestManager()
        
        # 加载数据
        print(f"\n正在加载数据...")
        df = load_and_prepare_data(symbol, '5m')
        if df is None:
            print(f"无法加载 {symbol} 的数据")
            return None
            
        print(f"数据加载完成: {len(df)} 条记录")
        
        # 获取策略信息
        strategies = manager.get_available_strategies()
        strategy_info = strategies.get(strategy_name)
        if not strategy_info:
            print(f"未找到策略: {strategy_name}")
            return None
            
        # 根据策略类型进行不同的参数测试
        if strategy_info['class'] == 'unified':
            results = test_unified_strategy_parameters(symbol, strategy_name, strategy_info, manager)
        else:
            results = test_traditional_strategy_parameters(symbol, strategy_name, strategy_info, manager)
            
        if results:
            # 分析结果
            analyze_parameter_sensitivity(results, symbol, strategy_name)
            return results
        else:
            print("参数敏感性测试未产生有效结果")
            return None
            
    except Exception as e:
        print(f"参数敏感性测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_unified_strategy_parameters(symbol, strategy_name, strategy_info, manager):
    """测试统一策略的参数敏感性"""
    print(f"\n开始测试统一策略参数敏感性...")
    
    # 定义参数网格 - 基于RSI背离策略（简化版，减少测试时间）
    param_grids = {
        'rsi_period': [12, 14, 16],           # RSI周期
        'lookback_period': [15, 20],          # 回看期
        'stop_loss_pct': [0.01, 0.015],       # 止损比例
        'take_profit_ratio': [1.2, 1.5]      # 止盈比例
    }
    
    print("参数测试范围:")
    for param, values in param_grids.items():
        print(f"  {param}: {values}")
    
    # 生成所有参数组合
    param_combinations = list(itertools.product(*param_grids.values()))
    total_combinations = len(param_combinations)
    
    print(f"\n总测试组合数: {total_combinations}")
    print("开始批量测试... (可能需要几分钟)")
    
    results = []
    successful_tests = 0
    
    for i, combination in enumerate(param_combinations, 1):
        params = dict(zip(param_grids.keys(), combination))
        
        if i % 5 == 0 or i == 1:
            print(f"进度: {i}/{total_combinations} ({i/total_combinations*100:.1f}%)")
        
        try:
            # 运行静默回测（不显示图表）
            result = run_silent_backtest(
                manager, symbol, strategy_name, params
            )
            
            if result and result['total_trades'] >= 5:
                test_result = {
                    'params': params.copy(),
                    'return_pct': result['total_return_pct'],
                    'total_trades': result['total_trades'],
                    'win_rate': result['win_rate'],
                    'sharpe_ratio': calculate_simple_sharpe(result['total_return_pct'])
                }
                results.append(test_result)
                successful_tests += 1
        except:
            continue  # 跳过失败的测试
    
    print(f"\n测试完成! 成功测试: {successful_tests}/{total_combinations}")
    return results

def test_traditional_strategy_parameters(symbol, strategy_name, strategy_info, manager):
    """测试传统策略的参数敏感性"""
    print(f"\n暂不支持传统策略的参数敏感性测试")
    print(f"建议使用统一策略进行测试")
    return None

def run_silent_backtest(manager, symbol, strategy_name, params):
    """运行静默回测（不显示图表和详细输出）"""
    # 暂时保存原始的plot函数
    import matplotlib.pyplot as plt
    original_show = plt.show
    original_plot = plt.plot
    original_figure = plt.figure
    
    try:
        # 禁用所有图表显示
        plt.show = lambda: None
        plt.plot = lambda *args, **kwargs: None
        plt.figure = lambda *args, **kwargs: None
        
        # 运行回测，但不输出详细信息
        result = manager.run_backtest(
            symbol=symbol,
            strategy_name=strategy_name,
            initial_capital=10000.0,
            strategy_params=params
        )
        
        return result
        
    finally:
        # 恢复原始函数
        plt.show = original_show
        plt.plot = original_plot
        plt.figure = original_figure

def calculate_simple_sharpe(return_pct, risk_free_rate=2.0):
    """简化的夏普比率计算"""
    excess_return = return_pct - risk_free_rate
    # 简化假设风险为收益的一半
    risk = abs(return_pct) * 0.5 if return_pct != 0 else 1
    return excess_return / risk

def analyze_parameter_sensitivity(results, symbol, strategy_name):
    """分析参数敏感性结果"""
    print(f"\n{'='*70}")
    print(f"参数敏感性分析结果")
    print(f"{'='*70}")
    
    if not results:
        print("X 没有有效的测试结果")
        return
    
    # 基础统计
    returns = [r['return_pct'] for r in results]
    profitable_tests = len([r for r in returns if r > 0])
    total_tests = len(results)
    
    print(f"有效测试数: {total_tests}")
    print(f"盈利组合数: {profitable_tests} ({profitable_tests/total_tests*100:.1f}%)")
    
    # 收益统计
    print(f"\n收益率分布:")
    print(f"  平均收益率: {np.mean(returns):.2f}%")
    print(f"  收益率标准差: {np.std(returns):.2f}%")
    print(f"  最佳收益率: {max(returns):.2f}%")
    print(f"  最差收益率: {min(returns):.2f}%")
    print(f"  中位数收益率: {np.median(returns):.2f}%")
    
    # 寻找最佳参数组合
    best_result = max(results, key=lambda x: x['return_pct'])
    worst_result = min(results, key=lambda x: x['return_pct'])
    
    print(f"\n最佳参数组合:")
    print(f"  收益率: {best_result['return_pct']:.2f}%")
    print(f"  参数: {best_result['params']}")
    
    print(f"\n最差参数组合:")
    print(f"  收益率: {worst_result['return_pct']:.2f}%")
    print(f"  参数: {worst_result['params']}")
    
    # 参数影响分析
    analyze_parameter_impact(results)
    
    # 稳健性评估
    stability_assessment = assess_parameter_stability(results)
    
    # 最终建议
    provide_parameter_recommendations(stability_assessment, best_result, symbol, strategy_name)

def analyze_parameter_impact(results):
    """分析各参数的影响"""
    print(f"\n{'='*50}")
    print("参数影响分析")
    print(f"{'='*50}")
    
    if not results:
        return
    
    # 提取所有参数名
    param_names = list(results[0]['params'].keys())
    
    for param_name in param_names:
        print(f"\n{param_name} 的影响:")
        
        # 按参数值分组
        param_groups = {}
        for result in results:
            param_value = result['params'][param_name]
            if param_value not in param_groups:
                param_groups[param_value] = []
            param_groups[param_value].append(result['return_pct'])
        
        # 计算每个参数值的平均收益
        for param_value, returns in param_groups.items():
            avg_return = np.mean(returns)
            print(f"  {param_value}: 平均收益 {avg_return:.2f}% (样本数: {len(returns)})")

def assess_parameter_stability(results):
    """评估参数稳定性"""
    print(f"\n{'='*50}")
    print("参数稳定性评估")
    print(f"{'='*50}")
    
    returns = [r['return_pct'] for r in results]
    profitable_ratio = len([r for r in returns if r > 0]) / len(returns)
    return_std = np.std(returns)
    return_mean = np.mean(returns)
    
    # 稳定性评分
    stability_score = 0
    
    # 1. 盈利比例评估
    if profitable_ratio >= 0.7:
        print("+ 盈利稳定性: 优秀 (≥70%组合盈利)")
        stability_score += 3
    elif profitable_ratio >= 0.5:
        print("! 盈利稳定性: 一般 (50-70%组合盈利)")
        stability_score += 2
    elif profitable_ratio >= 0.3:
        print("X 盈利稳定性: 差 (30-50%组合盈利)")
        stability_score += 1
    else:
        print("X 高过拟合风险: 30-50%参数组合盈利")
        stability_score += 0
    
    # 2. 收益波动性评估
    volatility_ratio = return_std / abs(return_mean) if return_mean != 0 else float('inf')
    if volatility_ratio <= 0.5:
        print("+ 收益稳定性: 优秀 (变异系数≤50%)")
        stability_score += 3
    elif volatility_ratio <= 1.0:
        print("! 收益稳定性: 一般 (变异系数50-100%)")
        stability_score += 2
    else:
        print("X 参数不稳定: 收益率标准差>100%")
        stability_score += 1
    
    # 3. 综合评估
    if stability_score >= 5:
        overall_stability = "优秀"
        recommendation = "策略参数稳健，适合实盘使用"
    elif stability_score >= 4:
        overall_stability = "良好"
        recommendation = "策略相对稳定，建议小资金测试"
    elif stability_score >= 2:
        overall_stability = "一般"
        recommendation = "策略稳定性有限，需要谨慎使用"
    else:
        overall_stability = "差"
        recommendation = "策略可能过拟合，不建议实盘使用"
    
    print(f"\n综合稳定性评级: {overall_stability}")
    print(f"建议: {recommendation}")
    
    return {
        'profitable_ratio': profitable_ratio,
        'volatility_ratio': volatility_ratio,
        'stability_score': stability_score,
        'overall_stability': overall_stability,
        'recommendation': recommendation
    }

def provide_parameter_recommendations(stability_assessment, best_result, symbol, strategy_name):
    """提供参数使用建议"""
    print(f"\n{'='*70}")
    print("参数使用建议")
    print(f"{'='*70}")
    
    print(f"策略: {strategy_name}")
    print(f"交易对: {symbol}")
    
    if stability_assessment['stability_score'] >= 4:
        print(f"\n+ 推荐参数配置:")
        for param, value in best_result['params'].items():
            print(f"  {param}: {value}")
        print(f"  预期收益率: {best_result['return_pct']:.2f}%")
        
        print(f"\n使用建议:")
        print(f"  - 可以使用推荐参数进行实盘测试")
        print(f"  - 建议定期重新测试参数有效性")
        print(f"  - 市场环境变化时考虑微调参数")
        
    else:
        print(f"\n! 参数稳定性不足，建议:")
        print(f"  - 进一步优化策略逻辑")
        print(f"  - 扩大参数测试范围")
        print(f"  - 考虑添加额外过滤条件")
        print(f"  - 在不同市场环境下分别测试")
    
    print(f"\n重要提醒:")
    print(f"  - 参数敏感性测试基于历史数据")
    print(f"  - 未来市场可能需要不同参数")
    print(f"  - 建议结合走向前分析验证")
    print(f"  - 实盘使用前先进行模拟测试")