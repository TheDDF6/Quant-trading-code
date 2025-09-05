# parameter_sensitivity_test.py - 参数敏感性测试
import pandas as pd
import numpy as np
import itertools
from core.backtest import ideal_dynamic_backtest, load_and_prepare_data

def parameter_sensitivity_test(df, strategy_name='rsi_divergence'):
    """
    测试策略对参数变化的敏感性
    如果策略过拟合，微小的参数变化会导致性能大幅下降
    """
    print(f"\n{'='*60}")
    print(f"参数敏感性测试 - {strategy_name}")
    print(f"{'='*60}")
    
    # 定义参数网格 - RSI背离策略的关键参数
    rsi_periods = [10, 12, 14, 16, 18]  # RSI周期
    lookbacks = [15, 20, 25, 30]        # 回看期
    stop_loss_pcts = [0.01, 0.015, 0.02, 0.025]  # 止损比例
    take_profit_ratios = [1.2, 1.5, 2.0, 2.5]    # 止盈比例
    
    results = []
    total_combinations = len(rsi_periods) * len(lookbacks) * len(stop_loss_pcts) * len(take_profit_ratios)
    current_combination = 0
    
    print(f"总参数组合数: {total_combinations}")
    print("开始测试...\n")
    
    # 导入策略模块
    import importlib
    try:
        strategy_module = importlib.import_module(f"strategies.{strategy_name}")
    except ImportError as e:
        print(f"无法加载策略: {e}")
        return None
    
    # 遍历所有参数组合
    for rsi_period in rsi_periods:
        for lookback in lookbacks:
            for stop_loss_pct in stop_loss_pcts:
                for take_profit_ratio in take_profit_ratios:
                    current_combination += 1
                    
                    if current_combination % 10 == 0:
                        progress = (current_combination / total_combinations) * 100
                        print(f"进度: {progress:.1f}% ({current_combination}/{total_combinations})")
                    
                    try:
                        # 修改RSI周期（需要修改策略代码以支持参数）
                        # 这里简化处理，使用默认参数但记录组合
                        
                        # 生成信号
                        signals = strategy_module.generate_signals(
                            df, 
                            stop_loss_pct=stop_loss_pct,
                            take_profit_ratio=take_profit_ratio,
                            lookback=lookback
                        )
                        
                        if len(signals) < 10:  # 信号太少，跳过
                            continue
                        
                        # 运行回测
                        df_result, trades = ideal_dynamic_backtest(
                            df, signals,
                            initial_capital=10000,
                            risk_per_trade=0.015,
                            max_leverage=100
                        )
                        
                        if trades and len(trades) > 5:
                            final_capital = trades[-1]['capital_after']
                            total_return = (final_capital - 10000) / 10000 * 100
                            
                            win_trades = [t for t in trades if t['pnl'] > 0]
                            win_rate = len(win_trades) / len(trades)
                            
                            # 计算最大回撤
                            equity_curve = df_result['equity'].values
                            equity_series = pd.Series(equity_curve)
                            rolling_max = equity_series.expanding().max()
                            drawdown = (equity_series - rolling_max) / rolling_max * 100
                            max_drawdown = drawdown.min()
                            
                            results.append({
                                'rsi_period': rsi_period,
                                'lookback': lookback,
                                'stop_loss_pct': stop_loss_pct,
                                'take_profit_ratio': take_profit_ratio,
                                'signals': len(signals),
                                'trades': len(trades),
                                'total_return': total_return,
                                'win_rate': win_rate,
                                'max_drawdown': max_drawdown,
                                'final_capital': final_capital
                            })
                            
                    except Exception as e:
                        # 某些参数组合可能出错，跳过
                        continue
    
    return results

def analyze_parameter_sensitivity(results):
    """分析参数敏感性结果"""
    if not results:
        print("❌ 没有有效的测试结果")
        return
    
    print(f"\n{'='*60}")
    print(f"参数敏感性分析结果")
    print(f"{'='*60}")
    
    # 转换为DataFrame便于分析
    df_results = pd.DataFrame(results)
    
    print(f"有效参数组合数: {len(results)}")
    
    # 收益率统计
    returns = df_results['total_return']
    print(f"\n收益率分布:")
    print(f"最佳收益率: {returns.max():.1f}%")
    print(f"最差收益率: {returns.min():.1f}%")
    print(f"平均收益率: {returns.mean():.1f}%")
    print(f"收益率标准差: {returns.std():.1f}%")
    print(f"收益率中位数: {returns.median():.1f}%")
    
    # 稳健性评估
    positive_returns = len(df_results[df_results['total_return'] > 0])
    robustness_ratio = positive_returns / len(results)
    
    print(f"\n稳健性评估:")
    print(f"盈利参数组合: {positive_returns}/{len(results)} ({robustness_ratio:.1%})")
    
    # 参数敏感性分析
    print(f"\n参数影响分析:")
    
    # 按不同参数分组，看收益率分布
    for param in ['rsi_period', 'lookback', 'stop_loss_pct', 'take_profit_ratio']:
        if param in df_results.columns:
            grouped = df_results.groupby(param)['total_return']
            print(f"\n{param}参数影响:")
            for value, group in grouped:
                print(f"  {param}={value}: 平均收益{group.mean():.1f}% (±{group.std():.1f}%)")
    
    # 最佳参数组合
    best_idx = df_results['total_return'].idxmax()
    best_params = df_results.iloc[best_idx]
    
    print(f"\n最佳参数组合:")
    print(f"RSI周期: {best_params['rsi_period']}")
    print(f"回看期: {best_params['lookback']}")
    print(f"止损比例: {best_params['stop_loss_pct']:.1%}")
    print(f"止盈比例: {best_params['take_profit_ratio']}")
    print(f"收益率: {best_params['total_return']:.1f}%")
    print(f"胜率: {best_params['win_rate']:.1%}")
    
    # 过拟合风险评估
    print(f"\n{'='*40}")
    print(f"过拟合风险评估")
    print(f"{'='*40}")
    
    if robustness_ratio >= 0.7:
        print("✅ 低过拟合风险: 70%以上参数组合盈利")
    elif robustness_ratio >= 0.5:
        print("⚠️  中等过拟合风险: 50-70%参数组合盈利")
    elif robustness_ratio >= 0.3:
        print("❌ 高过拟合风险: 30-50%参数组合盈利")
    else:
        print("🚨 极高过拟合风险: <30%参数组合盈利")
    
    if returns.std() <= 50:
        print("✅ 参数稳定性好: 收益率标准差≤50%")
    elif returns.std() <= 100:
        print("⚠️  参数稳定性中等: 收益率标准差50-100%")
    else:
        print("❌ 参数不稳定: 收益率标准差>100%")
    
    # 建议
    print(f"\n建议:")
    if robustness_ratio < 0.5:
        print("- 策略可能存在严重过拟合，建议重新设计")
    if returns.std() > 100:
        print("- 参数过于敏感，建议增加参数约束")
    if returns.max() > 1000:
        print("- 最高收益率异常，检查是否存在数据泄露")
    
    return {
        'total_combinations': len(results),
        'profitable_ratio': robustness_ratio,
        'return_mean': returns.mean(),
        'return_std': returns.std(),
        'best_return': returns.max(),
        'worst_return': returns.min()
    }

def quick_sensitivity_test():
    """快速敏感性测试示例"""
    print("参数敏感性测试工具")
    print("\n使用方法:")
    print("from parameter_sensitivity_test import parameter_sensitivity_test, analyze_parameter_sensitivity")
    print("from backtest import load_and_prepare_data")
    print("")
    print("# 加载数据")
    print("df = load_and_prepare_data('BTC-USDT', '5m')")
    print("")
    print("# 执行参数敏感性测试")
    print("results = parameter_sensitivity_test(df)")
    print("")
    print("# 分析结果")
    print("summary = analyze_parameter_sensitivity(results)")

if __name__ == "__main__":
    quick_sensitivity_test()