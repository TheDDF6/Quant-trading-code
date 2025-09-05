# time_series_validation.py - 时间序列分段验证工具
import pandas as pd
import numpy as np
from pathlib import Path
import importlib

def walk_forward_analysis(df, strategy_name, initial_capital=10000, 
                         train_months=6, test_months=1, min_trades=10):
    """
    走向前分析 - 金融时间序列的正确验证方法
    
    参数:
    - train_months: 训练期长度(月)
    - test_months: 测试期长度(月) 
    - min_trades: 最少交易数要求
    """
    from core.backtest import ideal_dynamic_backtest
    
    print(f"\n{'='*60}")
    print(f"走向前分析 - {strategy_name}")
    print(f"{'='*60}")
    print(f"训练期: {train_months}个月")
    print(f"测试期: {test_months}个月")
    
    # 加载策略
    try:
        strategy = importlib.import_module(f"strategies.{strategy_name}")
    except ImportError as e:
        print(f"无法加载策略: {e}")
        return None
    
    results = []
    start_date = df.index[0]
    end_date = df.index[-1]
    
    current_date = start_date
    fold_num = 1
    
    while current_date < end_date:
        # 计算训练期和测试期
        train_end = current_date + pd.DateOffset(months=train_months)
        test_start = train_end
        test_end = test_start + pd.DateOffset(months=test_months)
        
        if test_end > end_date:
            break
            
        print(f"\n--- 第{fold_num}轮分析 ---")
        print(f"训练期: {current_date.strftime('%Y-%m-%d')} 至 {train_end.strftime('%Y-%m-%d')}")
        print(f"测试期: {test_start.strftime('%Y-%m-%d')} 至 {test_end.strftime('%Y-%m-%d')}")
        
        # 1. 训练期数据 - 用于参数优化(这里简化，直接用默认参数)
        train_data = df[(df.index >= current_date) & (df.index < train_end)].copy()
        
        if len(train_data) < 1000:  # 训练数据太少
            print("❌ 训练数据不足，跳过")
            current_date = test_start
            fold_num += 1
            continue
            
        # 2. 测试期数据 - 用于验证策略效果
        test_data = df[(df.index >= test_start) & (df.index < test_end)].copy()
        
        if len(test_data) < 100:  # 测试数据太少
            print("❌ 测试数据不足，跳过")
            current_date = test_start
            fold_num += 1
            continue
        
        try:
            # 在训练期生成信号(实际应该用训练期优化参数，这里简化)
            train_signals = strategy.generate_signals(train_data)
            
            # 在测试期生成信号并回测
            test_signals = strategy.generate_signals(test_data)
            
            if len(test_signals) < min_trades:
                print(f"❌ 测试期信号不足({len(test_signals)}<{min_trades})，跳过")
                current_date = test_start
                fold_num += 1
                continue
            
            # 在测试期执行回测
            test_result, test_trades = ideal_dynamic_backtest(
                test_data, test_signals, 
                initial_capital=initial_capital,
                risk_per_trade=0.015,
                max_leverage=100
            )
            
            if test_trades:
                # 计算测试期表现
                final_capital = test_trades[-1]['capital_after']
                total_return = (final_capital - initial_capital) / initial_capital * 100
                
                win_trades = [t for t in test_trades if t['pnl'] > 0]
                win_rate = len(win_trades) / len(test_trades)
                
                # 计算最大回撤
                equity_curve = test_result['equity'].values
                equity_series = pd.Series(equity_curve)
                rolling_max = equity_series.expanding().max()
                drawdown = (equity_series - rolling_max) / rolling_max * 100
                max_drawdown = drawdown.min()
                
                results.append({
                    'fold': fold_num,
                    'train_start': current_date,
                    'train_end': train_end,
                    'test_start': test_start,
                    'test_end': test_end,
                    'train_signals': len(train_signals),
                    'test_signals': len(test_signals),
                    'test_trades': len(test_trades),
                    'total_return': total_return,
                    'win_rate': win_rate,
                    'max_drawdown': max_drawdown,
                    'final_capital': final_capital
                })
                
                print(f"✓ 训练信号: {len(train_signals)}, 测试信号: {len(test_signals)}")
                print(f"✓ 测试交易: {len(test_trades)}, 胜率: {win_rate:.1%}")
                print(f"✓ 测试收益: {total_return:.1f}%, 最大回撤: {max_drawdown:.1f}%")
                
            else:
                print("❌ 测试期无有效交易")
                
        except Exception as e:
            print(f"❌ 回测出错: {str(e)}")
        
        # 移动到下一个测试期
        current_date = test_start
        fold_num += 1
    
    return results

def analyze_walk_forward_results(results):
    """分析走向前测试结果"""
    if not results:
        print("❌ 没有有效的测试结果")
        return
    
    print(f"\n{'='*60}")
    print(f"走向前分析结果汇总")
    print(f"{'='*60}")
    
    # 基本统计
    total_folds = len(results)
    profitable_folds = len([r for r in results if r['total_return'] > 0])
    
    returns = [r['total_return'] for r in results]
    win_rates = [r['win_rate'] for r in results]
    max_drawdowns = [r['max_drawdown'] for r in results]
    
    print(f"总测试轮数: {total_folds}")
    print(f"盈利轮数: {profitable_folds} ({profitable_folds/total_folds:.1%})")
    
    print(f"\n收益率统计:")
    print(f"平均收益率: {np.mean(returns):.1f}%")
    print(f"收益率标准差: {np.std(returns):.1f}%")
    print(f"最佳收益率: {max(returns):.1f}%")
    print(f"最差收益率: {min(returns):.1f}%")
    
    print(f"\n胜率统计:")
    print(f"平均胜率: {np.mean(win_rates):.1%}")
    print(f"胜率标准差: {np.std(win_rates):.1%}")
    
    print(f"\n回撤统计:")
    print(f"平均最大回撤: {np.mean(max_drawdowns):.1f}%")
    print(f"最大回撤(最差): {min(max_drawdowns):.1f}%")
    
    # 稳定性评估
    print(f"\n{'='*40}")
    print(f"策略稳定性评估")
    print(f"{'='*40}")
    
    # 1. 盈利一致性
    if profitable_folds / total_folds >= 0.7:
        print("✓ 盈利一致性: 良好 (≥70%轮次盈利)")
    elif profitable_folds / total_folds >= 0.5:
        print("⚠️ 盈利一致性: 中等 (50-70%轮次盈利)")
    else:
        print("❌ 盈利一致性: 差 (<50%轮次盈利)")
    
    # 2. 收益率稳定性
    if np.std(returns) <= 20:
        print("✓ 收益率稳定性: 良好 (标准差≤20%)")
    elif np.std(returns) <= 50:
        print("⚠️ 收益率稳定性: 中等 (标准差20-50%)")
    else:
        print("❌ 收益率稳定性: 差 (标准差>50%)")
    
    # 3. 过拟合风险评估
    if np.std(returns) <= 30 and profitable_folds / total_folds >= 0.6:
        print("✓ 过拟合风险: 低")
    elif np.std(returns) <= 60 and profitable_folds / total_folds >= 0.4:
        print("⚠️ 过拟合风险: 中等")
    else:
        print("❌ 过拟合风险: 高，可能存在严重过拟合")
    
    # 详细结果表
    print(f"\n详细测试结果:")
    print("-" * 80)
    print("轮次  测试期间                收益率    胜率     最大回撤")
    print("-" * 80)
    
    for r in results:
        print(f"{r['fold']:2d}   {r['test_start'].strftime('%Y-%m-%d')} 至 "
              f"{r['test_end'].strftime('%Y-%m-%d')}  {r['total_return']:6.1f}%  "
              f"{r['win_rate']:5.1%}   {r['max_drawdown']:6.1f}%")
    
    return {
        'avg_return': np.mean(returns),
        'return_std': np.std(returns),
        'avg_win_rate': np.mean(win_rates),
        'profit_consistency': profitable_folds / total_folds,
        'overfitting_risk': 'high' if (np.std(returns) > 60 or profitable_folds / total_folds < 0.4) else 'low'
    }

def main():
    """演示走向前分析"""
    print("时间序列分段验证工具")
    print("用法示例:")
    print("from time_series_validation import walk_forward_analysis, analyze_walk_forward_results")
    print("from backtest import load_and_prepare_data")
    print("")
    print("# 加载数据")  
    print("df = load_and_prepare_data('BTC-USDT', '5m')")
    print("")
    print("# 执行走向前分析")
    print("results = walk_forward_analysis(df, 'rsi_divergence')")
    print("")
    print("# 分析结果")
    print("analyze_walk_forward_results(results)")

if __name__ == "__main__":
    main()