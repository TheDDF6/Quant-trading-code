#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能参数敏感性测试 - 平衡效率和全面性
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
os.environ['MPLBACKEND'] = 'Agg'
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def run_parameter_sensitivity_test_smart(symbol, strategy_name, mode="balanced", timeframe='5m'):
    """
    智能参数敏感性测试
    
    Args:
        mode: 'fast' (8组合), 'balanced' (16组合), 'comprehensive' (36组合)
    """
    print(f"\n{'='*70}")
    print(f"智能参数敏感性测试 - {symbol} - {strategy_name}")
    print(f"模式: {mode}")
    print(f"{'='*70}")
    
    # 根据模式选择参数网格
    if mode == "fast":
        param_grids = {
            'rsi_period': [14],                   # 1个值（默认最优）
            'lookback_period': [15, 20],          # 2个值（关键参数）
            'stop_loss_pct': [0.015],             # 1个值（最优固定）
            'take_profit_ratio': [1.2, 1.5, 2.0] # 3个值（重要参数）
        }
        expected_combinations = 6
        description = "快速模式 - 测试最关键参数"
        
    elif mode == "balanced":
        param_grids = {
            'rsi_period': [12, 14],               # 2个值，包含实盘参数12
            'lookback_period': [15, 20, 25],      # 3个值（最重要）
            'stop_loss_pct': [0.01, 0.015],       # 2个值（重要）
            'take_profit_ratio': [1.2, 1.5]       # 2个值
        }
        expected_combinations = 12  # 2*3*2*2 = 12
        description = "平衡模式 - 全面测试主要参数"
        
    else:  # comprehensive
        param_grids = {
            'rsi_period': [10, 12, 14, 16, 18],   # 5个值
            'lookback_period': [15, 20, 25, 30],  # 4个值
            'stop_loss_pct': [0.01, 0.015, 0.02], # 3个值
            'take_profit_ratio': [1.0, 1.2, 1.5, 2.0] # 4个值
        }
        expected_combinations = 240
        description = "全面模式 - 详尽测试所有参数范围"
    
    print(f"\n{description}")
    print("参数测试范围:")
    for param, values in param_grids.items():
        print(f"  {param}: {values}")
    
    # 生成参数组合
    param_combinations = list(itertools.product(*param_grids.values()))
    total_combinations = len(param_combinations)
    
    print(f"\n总组合数: {total_combinations}")
    
    # 时间估算
    estimated_time = total_combinations * 3  # 假设每个组合3秒
    if estimated_time > 300:  # 超过5分钟
        print(f"⏰ 预估时间: {estimated_time//60}分{estimated_time%60}秒")
        confirm = input("时间较长，是否继续？(y/N): ").strip().lower()
        if confirm != 'y':
            print("已取消测试")
            return None
    
    print("="*50)
    
    results = []
    successful_tests = 0
    
    for i, combination in enumerate(param_combinations, 1):
        params = dict(zip(param_grids.keys(), combination))
        
        # 动态进度条 (使用ASCII字符)
        progress = i / total_combinations * 100
        bar_length = 30
        filled_length = int(bar_length * progress / 100)
        bar = '#' * filled_length + '-' * (bar_length - filled_length)
        
        # 估算剩余时间
        if i > 1:
            avg_time_per_test = (i - 1) * 3  # 简化估算
            remaining_tests = total_combinations - i
            remaining_time = remaining_tests * 3
            time_str = f" | 剩余:{remaining_time//60}:{remaining_time%60:02d}"
        else:
            time_str = ""
        
        print(f"\r[{bar}] {progress:5.1f}% ({i}/{total_combinations}){time_str}", end='', flush=True)
        
        try:
            # 运行静默回测
            result = run_silent_backtest_optimized(symbol, strategy_name, params, timeframe)
            
            if result and result['total_trades'] >= 5:
                test_result = {
                    'params': params.copy(),
                    'return_pct': result['total_return_pct'],
                    'total_trades': result['total_trades'],
                    'win_rate': result['win_rate'],
                    'sharpe_ratio': calculate_simple_sharpe(result['total_return_pct']),
                    'risk_score': calculate_risk_score(result)
                }
                results.append(test_result)
                successful_tests += 1
        except:
            continue
    
    print(f"\n\n✅ 测试完成! 成功: {successful_tests}/{total_combinations}")
    
    if results:
        analysis = analyze_results_smart(results, symbol, strategy_name, mode)
        return results, analysis
    else:
        print("❌ 没有有效结果")
        return None, None

def run_silent_backtest_optimized(symbol, strategy_name, params, timeframe='5m'):
    """高度优化的静默回测"""
    from core.backtest_manager import BacktestManager
    
    # 重定向所有输出到空设备
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    try:
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        
        plt.ioff()  # 关闭matplotlib交互
        
        manager = BacktestManager()
        result = manager.run_backtest(
            symbol=symbol,
            strategy_name=strategy_name,
            timeframe=timeframe,
            initial_capital=10000.0,
            strategy_params=params
        )
        
        return result
        
    finally:
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = original_stdout
        sys.stderr = original_stderr

def calculate_simple_sharpe(return_pct, risk_free_rate=2.0):
    """简化夏普比率"""
    if return_pct <= 0:
        return -1.0
    excess_return = return_pct - risk_free_rate
    risk = abs(return_pct) * 0.3  # 简化风险估算
    return excess_return / risk if risk > 0 else 0

def calculate_risk_score(result):
    """计算风险评分（越低越好）"""
    win_rate = result['win_rate']
    total_trades = result['total_trades']
    
    # 风险因子
    low_win_rate_penalty = max(0, 50 - win_rate) * 0.02  # 胜率低于50%的惩罚
    low_trade_count_penalty = max(0, 20 - total_trades) * 0.1  # 交易数少的惩罚
    
    return low_win_rate_penalty + low_trade_count_penalty

def analyze_results_smart(results, symbol, strategy_name, mode):
    """智能结果分析"""
    print(f"\n{'='*70}")
    print(f"参数敏感性分析结果 ({mode}模式)")
    print(f"{'='*70}")
    
    # 基础统计
    returns = [r['return_pct'] for r in results]
    win_rates = [r['win_rate'] for r in results]
    trade_counts = [r['total_trades'] for r in results]
    
    profitable_count = len([r for r in returns if r > 0])
    
    print(f"有效测试: {len(results)}")
    print(f"盈利组合: {profitable_count} ({profitable_count/len(results)*100:.1f}%)")
    
    # 收益分布分析
    print(f"\n📊 收益率分布:")
    print(f"  平均: {np.mean(returns):6.2f}% ± {np.std(returns):5.2f}%")
    print(f"  中位数: {np.median(returns):6.2f}%")
    print(f"  最佳: {max(returns):6.2f}%")
    print(f"  最差: {min(returns):6.2f}%")
    print(f"  变异系数: {np.std(returns)/abs(np.mean(returns)):.2f}")
    
    # 找出最优组合（综合考虑收益和风险）
    for result in results:
        result['composite_score'] = result['return_pct'] * 0.7 + (100 - result['risk_score']) * 0.3
    
    best_result = max(results, key=lambda x: x['composite_score'])
    highest_return = max(results, key=lambda x: x['return_pct'])
    most_stable = min(results, key=lambda x: x['risk_score'])
    
    # 显示top3结果
    print(f"\n🏆 TOP 3 参数组合:")
    sorted_results = sorted(results, key=lambda x: x['composite_score'], reverse=True)
    
    for i, result in enumerate(sorted_results[:3], 1):
        print(f"\n{i}. 收益率: {result['return_pct']:6.2f}% | 胜率: {result['win_rate']:5.1f}% | 综合评分: {result['composite_score']:.1f}")
        print(f"   参数: {result['params']}")
    
    # 参数重要性分析
    print(f"\n📈 参数影响力排序:")
    param_importance = analyze_parameter_importance(results)
    
    for i, (param, impact) in enumerate(param_importance, 1):
        print(f"  {i}. {param:15} 影响力: {impact:5.1f}%")
    
    # 稳健性评估
    profitability = profitable_count / len(results)
    volatility = np.std(returns) / abs(np.mean(returns)) if np.mean(returns) != 0 else float('inf')
    
    print(f"\n🎯 策略稳健性评估:")
    
    # 综合评级
    if profitability >= 0.8 and volatility <= 0.4:
        rating = "优秀"
        color = "🟢"
    elif profitability >= 0.6 and volatility <= 0.8:
        rating = "良好"
        color = "🟡"
    elif profitability >= 0.4:
        rating = "一般"
        color = "🟠"
    else:
        rating = "较差"
        color = "🔴"
    
    print(f"  {color} 综合评级: {rating}")
    print(f"  盈利稳定性: {profitability*100:.1f}%")
    print(f"  收益波动性: {volatility:.2f}")
    print(f"  平均胜率: {np.mean(win_rates):.1f}%")
    print(f"  平均交易数: {np.mean(trade_counts):.0f}")
    
    # 使用建议
    print(f"\n💡 使用建议:")
    if rating == "优秀":
        print(f"  ✅ 强烈推荐实盘使用")
        print(f"  ✅ 推荐参数: {best_result['params']}")
        print(f"  ✅ 预期年化收益: {best_result['return_pct']:.1f}%")
    elif rating == "良好":
        print(f"  ⚠️  建议小资金测试")
        print(f"  ⚠️  推荐参数: {best_result['params']}")
        print(f"  ⚠️  保守预期收益: {best_result['return_pct']*0.7:.1f}%")
    else:
        print(f"  ❌ 不建议直接实盘使用")
        print(f"  ❌ 建议进一步优化策略")
    
    # 识别优质参数空间
    optimal_space = identify_optimal_parameter_space(results)
    
    print(f"\n🎯 优质参数空间识别:")
    print(f"{'='*50}")
    
    for param_name, space_info in optimal_space.items():
        print(f"\n📌 {param_name}:")
        print(f"   最优值: {space_info['best_value']}")
        print(f"   优质范围: {space_info['good_range']}")
        print(f"   避免使用: {space_info['poor_range']}")
        print(f"   推荐策略: {space_info['recommendation']}")
    
    # 生成详细的参数使用指南
    param_configs = generate_parameter_recommendations(optimal_space)
    
    return {
        'rating': rating,
        'profitability': profitability,
        'volatility': volatility,
        'best_params': best_result['params'],
        'best_return': best_result['return_pct'],
        'param_importance': param_importance,
        'optimal_space': optimal_space,
        'parameter_configs': param_configs
    }

def analyze_parameter_importance(results):
    """分析参数重要性"""
    param_names = list(results[0]['params'].keys())
    param_impacts = []
    
    for param_name in param_names:
        # 计算该参数不同取值的收益率差异
        param_groups = {}
        for result in results:
            param_value = result['params'][param_name]
            if param_value not in param_groups:
                param_groups[param_value] = []
            param_groups[param_value].append(result['return_pct'])
        
        # 计算收益率的标准差作为重要性指标
        group_means = [np.mean(returns) for returns in param_groups.values()]
        if len(group_means) > 1:
            impact = np.std(group_means)
        else:
            impact = 0
        
        param_impacts.append((param_name, impact))
    
    # 按重要性排序
    param_impacts.sort(key=lambda x: x[1], reverse=True)
    
    return param_impacts

def identify_optimal_parameter_space(results):
    """识别优质参数空间"""
    param_names = list(results[0]['params'].keys())
    optimal_space = {}
    
    for param_name in param_names:
        # 按参数值分组计算收益
        param_groups = {}
        for result in results:
            param_value = result['params'][param_name]
            if param_value not in param_groups:
                param_groups[param_value] = []
            param_groups[param_value].append(result['return_pct'])
        
        # 计算每个参数值的平均收益和稳定性
        param_analysis = {}
        for value, returns in param_groups.items():
            param_analysis[value] = {
                'avg_return': np.mean(returns),
                'std_return': np.std(returns),
                'min_return': min(returns),
                'max_return': max(returns),
                'sample_count': len(returns)
            }
        
        # 找出最优值
        best_value = max(param_analysis.keys(), 
                        key=lambda x: param_analysis[x]['avg_return'])
        best_avg_return = param_analysis[best_value]['avg_return']
        
        # 识别优质范围（收益率在最优值80%以上的参数）
        good_threshold = best_avg_return * 0.8
        good_values = [v for v, stats in param_analysis.items() 
                      if stats['avg_return'] >= good_threshold]
        
        # 识别差劲范围（收益率在最优值50%以下的参数）
        poor_threshold = best_avg_return * 0.5
        poor_values = [v for v, stats in param_analysis.items() 
                      if stats['avg_return'] <= poor_threshold]
        
        # 生成推荐策略
        if len(good_values) == 1:
            recommendation = f"参数敏感，必须使用 {best_value}"
        elif len(good_values) >= len(param_analysis) * 0.7:
            recommendation = f"参数稳健，{min(good_values)}-{max(good_values)} 范围内都可接受"
        else:
            recommendation = f"中等敏感，推荐使用 {good_values} 中的值"
        
        optimal_space[param_name] = {
            'best_value': best_value,
            'best_return': best_avg_return,
            'good_range': good_values,
            'poor_range': poor_values,
            'recommendation': recommendation,
            'sensitivity': calculate_parameter_sensitivity(param_analysis),
            'detailed_stats': param_analysis
        }
    
    return optimal_space

def calculate_parameter_sensitivity(param_analysis):
    """计算参数敏感性"""
    returns = [stats['avg_return'] for stats in param_analysis.values()]
    if len(returns) <= 1:
        return 0.0
    
    # 收益率的变异系数作为敏感性指标
    sensitivity = np.std(returns) / abs(np.mean(returns)) if np.mean(returns) != 0 else 0
    
    if sensitivity > 0.5:
        return "高敏感"
    elif sensitivity > 0.2:
        return "中敏感"
    else:
        return "低敏感"

def generate_parameter_recommendations(optimal_space):
    """生成具体的参数使用建议"""
    print(f"\n📋 参数使用指南:")
    print(f"{'='*50}")
    
    # 按敏感性分类参数
    high_sensitivity = []
    medium_sensitivity = []
    low_sensitivity = []
    
    for param_name, space_info in optimal_space.items():
        sensitivity = space_info['sensitivity']
        if sensitivity == "高敏感":
            high_sensitivity.append((param_name, space_info))
        elif sensitivity == "中敏感":
            medium_sensitivity.append((param_name, space_info))
        else:
            low_sensitivity.append((param_name, space_info))
    
    # 高敏感参数 - 必须精确设置
    if high_sensitivity:
        print(f"\n🔴 高敏感参数 (必须精确设置):")
        for param_name, space_info in high_sensitivity:
            print(f"   {param_name}: 必须使用 {space_info['best_value']}")
            print(f"   ⚠️  偏离最优值会显著影响收益")
    
    # 中敏感参数 - 有一定范围
    if medium_sensitivity:
        print(f"\n🟡 中敏感参数 (有可接受范围):")
        for param_name, space_info in medium_sensitivity:
            print(f"   {param_name}: 推荐范围 {space_info['good_range']}")
            print(f"   💡 最优: {space_info['best_value']}, 可接受: {len(space_info['good_range'])} 个选择")
    
    # 低敏感参数 - 相对灵活
    if low_sensitivity:
        print(f"\n🟢 低敏感参数 (设置灵活):")
        for param_name, space_info in low_sensitivity:
            print(f"   {param_name}: 任选 {space_info['good_range']}")
            print(f"   ✅ 对收益影响较小，可根据个人偏好调整")
    
    # 生成最终建议配置
    print(f"\n⭐ 推荐配置组合:")
    print(f"{'='*30}")
    
    config_conservative = {}  # 保守配置
    config_aggressive = {}   # 激进配置
    config_balanced = {}     # 平衡配置
    
    for param_name, space_info in optimal_space.items():
        good_values = sorted(space_info['good_range'])
        
        if len(good_values) >= 3:
            config_conservative[param_name] = good_values[0]      # 最保守
            config_balanced[param_name] = good_values[len(good_values)//2]  # 中间值
            config_aggressive[param_name] = good_values[-1]      # 最激进
        elif len(good_values) == 2:
            config_conservative[param_name] = good_values[0]
            config_balanced[param_name] = good_values[0]
            config_aggressive[param_name] = good_values[1]
        else:
            # 只有一个好选择
            config_conservative[param_name] = good_values[0]
            config_balanced[param_name] = good_values[0] 
            config_aggressive[param_name] = good_values[0]
    
    print(f"🛡️  保守配置: {config_conservative}")
    print(f"⚖️   平衡配置: {config_balanced}")
    print(f"🚀 激进配置: {config_aggressive}")
    
    return {
        'conservative': config_conservative,
        'balanced': config_balanced,
        'aggressive': config_aggressive
    }

if __name__ == "__main__":
    # 测试不同模式
    print("选择测试模式:")
    print("1. 快速 (6组合, ~30秒)")
    print("2. 平衡 (36组合, ~3分钟)") 
    print("3. 全面 (240组合, ~12分钟)")
    
    mode_choice = input("选择模式 (1-3): ").strip()
    mode_map = {'1': 'fast', '2': 'balanced', '3': 'comprehensive'}
    mode = mode_map.get(mode_choice, 'balanced')
    
    run_parameter_sensitivity_test_smart("BTC-USDT", "rsi_divergence_unified", mode)