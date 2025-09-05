# realistic_parameter_test.py - 现实的参数敏感性测试
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# 添加parent目录到路径以便导入
sys.path.append(str(Path(__file__).parent.parent))

from core.backtest import ideal_dynamic_backtest, load_and_prepare_data

def realistic_parameter_test(df):
    """
    测试真正重要的参数：
    - lookback: 背离识别的回看期
    - stop_loss_pct: 止损比例 
    - take_profit_ratio: 止盈比例
    - risk_per_trade: 单笔风险比例
    - max_leverage: 最大杠杆
    
    RSI周期固定为14（标准设置）
    """
    print(f"\n{'='*60}")
    print(f"现实参数敏感性测试")
    print(f"{'='*60}")
    
    # 定义参数范围 - 只测试真正会调整的参数
    lookbacks = [15, 20, 25, 30]                    # 回看期
    stop_loss_pcts = [0.01, 0.015, 0.02, 0.025]   # 止损比例
    take_profit_ratios = [1.2, 1.5, 2.0, 2.5]     # 止盈比例
    
    # 固定风险控制参数（符合交易所约束）
    fixed_risk = 0.015  # 固定1.5%风险
    fixed_max_leverage = 100  # 最大100倍杠杆（整数）
    
    results = []
    total_combinations = len(lookbacks) * len(stop_loss_pcts) * len(take_profit_ratios)
    current_combination = 0
    
    print(f"总参数组合数: {total_combinations}")
    print("RSI周期固定为14（标准技术分析设置）")
    print(f"单笔风险固定为{fixed_risk:.1%}（交易所约束）")
    print(f"最大杠杆固定为{fixed_max_leverage}倍（整数约束）")
    print("开始测试...\n")
    
    # 导入策略
    import importlib
    try:
        strategy_module = importlib.import_module("strategies.legacy.rsi_divergence")
    except ImportError as e:
        print(f"无法加载策略: {e}")
        return None
    
    for lookback in lookbacks:
        for stop_loss_pct in stop_loss_pcts:
            for take_profit_ratio in take_profit_ratios:
                current_combination += 1
                
                if current_combination % 5 == 0:
                    progress = (current_combination / total_combinations) * 100
                    print(f"进度: {progress:.1f}% ({current_combination}/{total_combinations})")
                
                try:
                    # 生成信号
                    signals = strategy_module.generate_signals(
                        df, 
                        stop_loss_pct=stop_loss_pct,
                        take_profit_ratio=take_profit_ratio,
                        lookback=lookback
                    )
                    
                    if len(signals) < 10:
                        continue
                    
                    # 回测（使用固定的风险和杠杆参数）
                    df_result, trades = ideal_dynamic_backtest(
                        df, signals,
                        initial_capital=10000,
                        risk_per_trade=fixed_risk,
                        max_leverage=fixed_max_leverage
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
                        
                        # 计算年化收益
                        days = (df.index[-1] - df.index[0]).days
                        years = days / 365.25
                        if years > 0 and final_capital > 0:
                            cagr = (pow(final_capital / 10000, 1/years) - 1) * 100
                        else:
                            cagr = 0
                        
                        # 检查杠杆使用情况
                        leverages_used = [t['leverage'] for t in trades]
                        avg_leverage = sum(leverages_used) / len(leverages_used)
                        max_leverage_used = max(leverages_used)
                        
                        results.append({
                            'lookback': lookback,
                            'stop_loss_pct': stop_loss_pct,
                            'take_profit_ratio': take_profit_ratio,
                            'signals': len(signals),
                            'trades': len(trades),
                            'total_return': total_return,
                            'cagr': cagr,
                            'win_rate': win_rate,
                            'max_drawdown': max_drawdown,
                            'avg_leverage': avg_leverage,
                            'max_leverage_used': max_leverage_used,
                            'final_capital': final_capital
                        })
                        
                except Exception as e:
                    continue
    
    return results

def analyze_realistic_results(results):
    """分析现实参数测试结果"""
    if not results:
        print("❌ 没有有效的测试结果")
        return
    
    print(f"\n{'='*60}")
    print(f"现实参数测试分析结果")
    print(f"{'='*60}")
    
    df_results = pd.DataFrame(results)
    
    print(f"有效参数组合数: {len(results)}")
    
    # 收益率分析
    returns = df_results['total_return']
    cagrs = df_results['cagr']
    
    print(f"\n总收益率分布:")
    print(f"最佳: {returns.max():.1f}%")
    print(f"最差: {returns.min():.1f}%")
    print(f"平均: {returns.mean():.1f}%")
    print(f"中位数: {returns.median():.1f}%")
    print(f"标准差: {returns.std():.1f}%")
    
    print(f"\n年化收益率(CAGR)分布:")
    print(f"最佳: {cagrs.max():.1f}%")
    print(f"最差: {cagrs.min():.1f}%")
    print(f"平均: {cagrs.mean():.1f}%")
    print(f"中位数: {cagrs.median():.1f}%")
    print(f"标准差: {cagrs.std():.1f}%")
    
    # 盈利组合分析
    profitable = df_results[df_results['total_return'] > 0]
    profitable_ratio = len(profitable) / len(results)
    
    print(f"\n盈利性分析:")
    print(f"盈利组合: {len(profitable)}/{len(results)} ({profitable_ratio:.1%})")
    
    # 现实性检查
    print(f"\n现实性检查:")
    extreme_returns = df_results[df_results['cagr'] > 500]  # CAGR > 500%
    if len(extreme_returns) > 0:
        print(f"⚠️  {len(extreme_returns)}个组合年化收益>500%，可能不现实")
    
    reasonable_returns = df_results[(df_results['cagr'] >= 10) & (df_results['cagr'] <= 200)]
    print(f"✅ {len(reasonable_returns)}个组合年化收益在10-200%区间（相对合理）")
    
    # 参数影响分析
    print(f"\n参数影响分析:")
    
    for param in ['lookback', 'stop_loss_pct', 'take_profit_ratio']:
        grouped = df_results.groupby(param)['cagr']
        print(f"\n{param}参数影响:")
        for value, group in grouped:
            if param == 'stop_loss_pct':
                print(f"  {param}={value:.1%}: 年化收益{group.mean():.1f}% (±{group.std():.1f}%)")
            else:
                print(f"  {param}={value}: 年化收益{group.mean():.1f}% (±{group.std():.1f}%)")
    
    # 杠杆使用分析
    if 'avg_leverage' in df_results.columns:
        print(f"\n杠杆使用情况:")
        print(f"平均杠杆: {df_results['avg_leverage'].mean():.1f}x")
        print(f"最大杠杆: {df_results['max_leverage_used'].max():.0f}x")
        print(f"杠杆标准差: {df_results['avg_leverage'].std():.1f}x")
    
    # 最佳组合（基于合理的年化收益）
    reasonable = df_results[(df_results['cagr'] >= 20) & (df_results['cagr'] <= 300)]
    if len(reasonable) > 0:
        best_reasonable_idx = reasonable['cagr'].idxmax()
        best_params = reasonable.loc[best_reasonable_idx]
        
        print(f"\n最佳合理参数组合 (CAGR 20-300%):")
        print(f"回看期: {best_params['lookback']}")
        print(f"止损比例: {best_params['stop_loss_pct']:.1%}")
        print(f"止盈比例: {best_params['take_profit_ratio']}")
        print(f"年化收益: {best_params['cagr']:.1f}%")
        print(f"胜率: {best_params['win_rate']:.1%}")
        print(f"最大回撤: {best_params['max_drawdown']:.1f}%")
        if 'avg_leverage' in best_params:
            print(f"平均杠杆: {best_params['avg_leverage']:.1f}x")
    
    # 稳健性评估
    print(f"\n{'='*40}")
    print(f"稳健性评估")
    print(f"{'='*40}")
    
    if profitable_ratio >= 0.7:
        print("✅ 盈利一致性: 良好")
    elif profitable_ratio >= 0.5:
        print("⚠️  盈利一致性: 中等")
    else:
        print("❌ 盈利一致性: 差")
    
    if cagrs.std() <= 100:
        print("✅ 年化收益稳定性: 良好")
    elif cagrs.std() <= 200:
        print("⚠️  年化收益稳定性: 中等")
    else:
        print("❌ 年化收益稳定性: 差")
    
    return {
        'total_combinations': len(results),
        'profitable_ratio': profitable_ratio,
        'avg_cagr': cagrs.mean(),
        'cagr_std': cagrs.std(),
        'reasonable_combinations': len(reasonable_returns)
    }

def main():
    """运行现实参数测试"""
    print("现实参数敏感性测试")
    print("只测试真正会调整的参数，RSI周期固定为14")
    
    # 加载数据
    df = load_and_prepare_data('BTC-USDT', '5m')
    if df is None:
        return
    
    # 执行测试
    results = realistic_parameter_test(df)
    
    if results:
        analyze_realistic_results(results)

def run_parameter_sensitivity_test():
    """包装函数，供main.py调用"""
    return main()

if __name__ == "__main__":
    main()