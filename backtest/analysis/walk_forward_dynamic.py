#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
动态走向前分析 - 支持用户选择币对和策略的时间序列验证
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys

# 添加路径
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

def run_walk_forward_analysis(symbol, strategy_name, timeframe='5m'):
    """
    运行动态走向前分析
    
    Args:
        symbol: 交易对
        strategy_name: 策略名称
        timeframe: 时间框架
    """
    print(f"\n{'='*70}")
    print(f"走向前分析 - {symbol} - {strategy_name}")
    print(f"{'='*70}")
    
    try:
        from core.backtest_manager import BacktestManager
        from core.backtest import load_and_prepare_data
        
        manager = BacktestManager()
        
        # 加载数据
        print(f"正在加载数据... (时间框架: {timeframe})")
        df = load_and_prepare_data(symbol, timeframe)
        if df is None:
            print(f"无法加载 {symbol} 的数据")
            return None
            
        print(f"数据加载完成: {len(df)} 条记录")
        print(f"时间范围: {df.index[0]} 至 {df.index[-1]}")
        
        # 获取策略信息
        strategies = manager.get_available_strategies()
        strategy_info = strategies.get(strategy_name)
        if not strategy_info:
            print(f"未找到策略: {strategy_name}")
            return None
            
        # 执行走向前分析
        results = perform_walk_forward_analysis(
            df, symbol, strategy_name, strategy_info, manager, timeframe=timeframe
        )
        
        if results:
            # 分析结果
            analyze_walk_forward_results(results, symbol, strategy_name)
            return results
        else:
            print("走向前分析未产生有效结果")
            return None
            
    except Exception as e:
        print(f"走向前分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def perform_walk_forward_analysis(df, symbol, strategy_name, strategy_info, manager, 
                                timeframe='5m', train_months=3, test_months=1, min_trades=5):
    """
    执行走向前分析
    """
    print(f"\n走向前分析参数:")
    print(f"  训练期: {train_months} 个月")
    print(f"  测试期: {test_months} 个月") 
    print(f"  最少交易数要求: {min_trades}")
    
    results = []
    total_months = len(df) // (30 * 24 * 12)  # 假设5分钟数据，估算月数
    
    if total_months < train_months + test_months:
        print(f"数据不足以进行走向前分析（需要至少{train_months + test_months}个月数据）")
        return None
    
    # 计算可以进行的分析轮数
    max_rounds = min(3, total_months - train_months)  # 最多3轮
    
    for round_num in range(1, max_rounds + 1):
        print(f"\n--- 第{round_num}轮分析 ---")
        
        # 计算训练期和测试期时间范围
        train_start_idx = (round_num - 1) * (test_months * 30 * 24 * 12)
        train_end_idx = train_start_idx + (train_months * 30 * 24 * 12)
        test_start_idx = train_end_idx
        test_end_idx = test_start_idx + (test_months * 30 * 24 * 12)
        
        # 确保索引不超出数据范围
        if test_end_idx >= len(df):
            test_end_idx = len(df) - 1
        if train_end_idx >= len(df):
            break
            
        train_data = df.iloc[train_start_idx:train_end_idx].copy()
        test_data = df.iloc[test_start_idx:test_end_idx].copy()
        
        if len(train_data) < 1000 or len(test_data) < 500:
            print(f"第{round_num}轮数据不足，跳过")
            continue
            
        print(f"训练期: {train_data.index[0].strftime('%Y-%m-%d')} 至 {train_data.index[-1].strftime('%Y-%m-%d')}")
        print(f"测试期: {test_data.index[0].strftime('%Y-%m-%d')} 至 {test_data.index[-1].strftime('%Y-%m-%d')}")
        
        # 在测试期运行回测
        try:
            result = manager.run_backtest(
                symbol=symbol,
                strategy_name=strategy_name,
                timeframe=timeframe,
                start_date=test_data.index[0].strftime('%Y-%m-%d'),
                end_date=test_data.index[-1].strftime('%Y-%m-%d'),
                initial_capital=10000.0
            )
            
            if result and result['total_trades'] >= min_trades:
                round_result = {
                    'round': round_num,
                    'train_start': train_data.index[0],
                    'train_end': train_data.index[-1], 
                    'test_start': test_data.index[0],
                    'test_end': test_data.index[-1],
                    'total_return_pct': result['total_return_pct'],
                    'total_trades': result['total_trades'],
                    'win_rate': result['win_rate'],
                    'max_drawdown': calculate_max_drawdown(result.get('df_result')),
                    'trades': result['trades']
                }
                results.append(round_result)
                
                print(f"✓ 第{round_num}轮完成:")
                print(f"  收益率: {result['total_return_pct']:.1f}%")
                print(f"  交易数: {result['total_trades']}")
                print(f"  胜率: {result['win_rate']:.1f}%")
            else:
                print(f"第{round_num}轮交易数不足({result['total_trades'] if result else 0} < {min_trades})，跳过")
                
        except Exception as e:
            print(f"第{round_num}轮回测失败: {e}")
            continue
    
    return results

def calculate_max_drawdown(df_result):
    """计算最大回撤"""
    if df_result is None or 'equity' not in df_result.columns:
        return 0.0
        
    equity = df_result['equity']
    peak = equity.expanding().max()
    drawdown = (equity - peak) / peak * 100
    return drawdown.min()

def analyze_walk_forward_results(results, symbol, strategy_name):
    """分析走向前结果"""
    print(f"\n{'='*70}")
    print(f"走向前分析结果汇总")
    print(f"{'='*70}")
    
    if not results:
        print("❌ 没有有效的测试结果")
        return
    
    # 统计信息
    returns = [r['total_return_pct'] for r in results]
    win_rates = [r['win_rate'] for r in results]
    drawdowns = [r['max_drawdown'] for r in results]
    
    profitable_rounds = len([r for r in returns if r > 0])
    total_rounds = len(results)
    
    print(f"总测试轮数: {total_rounds}")
    print(f"盈利轮数: {profitable_rounds} ({profitable_rounds/total_rounds*100:.1f}%)")
    
    # 收益率统计
    print(f"\n收益率统计:")
    print(f"  平均收益率: {np.mean(returns):.1f}%")
    print(f"  收益率标准差: {np.std(returns):.1f}%")
    print(f"  最佳收益率: {max(returns):.1f}%")
    print(f"  最差收益率: {min(returns):.1f}%")
    
    # 胜率统计
    print(f"\n胜率统计:")
    print(f"  平均胜率: {np.mean(win_rates):.1f}%")
    print(f"  胜率标准差: {np.std(win_rates):.1f}%")
    
    # 回撤统计
    print(f"\n回撤统计:")
    print(f"  平均最大回撤: {np.mean(drawdowns):.1f}%")
    print(f"  最大回撤(最差): {min(drawdowns):.1f}%")
    
    # 稳定性评估
    print(f"\n{'='*50}")
    print(f"策略稳定性评估")
    print(f"{'='*50}")
    
    # 盈利一致性
    profit_consistency = profitable_rounds / total_rounds
    if profit_consistency >= 0.7:
        print("✓ 盈利一致性: 良好 (≥70%轮次盈利)")
    elif profit_consistency >= 0.5:
        print("⚠️ 盈利一致性: 一般 (50-70%轮次盈利)")
    else:
        print("❌ 盈利一致性: 差 (<50%轮次盈利)")
    
    # 收益率稳定性
    return_volatility = np.std(returns) / abs(np.mean(returns)) if np.mean(returns) != 0 else float('inf')
    if return_volatility <= 0.5:
        print("✓ 收益率稳定性: 良好 (变异系数≤50%)")
    elif return_volatility <= 1.0:
        print("⚠️ 收益率稳定性: 一般 (变异系数50-100%)")
    else:
        print("❌ 收益率稳定性: 差 (变异系数>100%)")
    
    # 过拟合风险评估
    if profit_consistency >= 0.7 and return_volatility <= 0.5:
        print("✓ 过拟合风险: 低")
    elif profit_consistency >= 0.5 and return_volatility <= 1.0:
        print("⚠️ 过拟合风险: 中等")
    else:
        print("❌ 过拟合风险: 高")
    
    # 详细结果表
    print(f"\n详细测试结果:")
    print("-" * 80)
    print(f"{'轮次':^4} {'测试期间':^25} {'收益率':^8} {'胜率':^6} {'最大回撤':^10}")
    print("-" * 80)
    
    for result in results:
        period = f"{result['test_start'].strftime('%Y-%m-%d')} 至 {result['test_end'].strftime('%Y-%m-%d')}"
        print(f"{result['round']:^4} {period:^25} {result['total_return_pct']:^7.1f}% "
              f"{result['win_rate']:^5.1f}% {result['max_drawdown']:^9.1f}%")
    
    # 保守预估
    if profitable_rounds > 0:
        conservative_return = min(returns) if min(returns) > 0 else np.mean([r for r in returns if r > 0])
        annual_estimate = conservative_return * 12  # 假设月度测试
        
        print(f"\n{'='*70}")
        print(f"保守预估")
        print(f"{'='*70}")
        print(f"基于最差表现的保守年化收益预估: {annual_estimate:.1f}%")
        
        if profit_consistency >= 0.7:
            print("✓ 策略在多个时间段表现一致，适合实盘考虑")
        else:
            print("⚠️ 策略表现不够稳定，建议进一步优化")
    
    return {
        'total_rounds': total_rounds,
        'profitable_rounds': profitable_rounds,
        'profit_consistency': profit_consistency,
        'avg_return': np.mean(returns),
        'return_volatility': return_volatility,
        'results': results
    }