# strategy_validator_fixed.py - 修复后的策略验证工具
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import importlib

# 解决中文显示问题
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def validate_strategy(df, signals, symbol):
    """
    验证策略的合理性
    """
    print(f"\n{'='*50}")
    print(f"策略验证报告 - {symbol}")
    print(f"{'='*50}")
    
    # 1. 基础信息
    print(f"\n【基础信息】")
    print(f"数据周期: {df.index[0]} 到 {df.index[-1]}")
    print(f"数据点数: {len(df)}")
    print(f"交易信号数: {len(signals)}")
    
    if not signals:
        print("❌ 没有交易信号，无法验证")
        return
    
    # 2. 信号频率分析
    print(f"\n【信号频率分析】")
    signal_times = [sig[0] for sig in signals]
    total_days = (df.index[-1] - df.index[0]).days
    signals_per_day = len(signals) / max(total_days, 1)
    
    print(f"总交易天数: {total_days}天")
    print(f"平均每天信号数: {signals_per_day:.2f}")
    
    if signals_per_day > 5:
        print("⚠️ 警告: 信号过于频繁，可能存在过拟合")
    elif signals_per_day < 0.1:
        print("⚠️ 警告: 信号过少，策略可能不够活跃")
    else:
        print("✓ 信号频率合理")
    
    # 计算信号间隔
    if len(signal_times) > 1:
        intervals = [(signal_times[i] - signal_times[i-1]).total_seconds()/3600 
                    for i in range(1, len(signal_times))]
        intervals = [abs(x) for x in intervals if abs(x) > 0]
        
        if intervals:
            avg_interval = np.mean(intervals)
            min_interval = min(intervals)
            
            print(f"平均信号间隔: {avg_interval:.1f}小时")
            print(f"最短信号间隔: {min_interval:.1f}小时")
            
            if min_interval < 1:
                print("⚠️ 警告: 信号间隔过短，可能存在噪音交易")
    
    # 3. 风险收益比分析
    print(f"\n【风险收益比分析】")
    risk_rewards = []
    risk_pcts = []
    
    for i, sig in enumerate(signals[:10]):
        ts, price, action, stop_loss, take_profit, _ = sig
        
        if action == 'buy':
            stop_distance = abs(price - stop_loss)
            profit_distance = abs(take_profit - price)
            
            if stop_distance > 0:
                risk_reward = profit_distance / stop_distance
                stop_pct = stop_distance / price * 100
                profit_pct = profit_distance / price * 100
                
                risk_rewards.append(risk_reward)
                risk_pcts.append(stop_pct)
                
                if i < 5:
                    print(f"信号{i+1}: 风险{stop_pct:.2f}% vs 收益{profit_pct:.2f}% (比例{risk_reward:.2f})")
    
    if risk_rewards:
        avg_rr = np.mean(risk_rewards)
        avg_risk = np.mean(risk_pcts)
        print(f"平均风险收益比: {avg_rr:.2f}")
        print(f"平均单笔风险: {avg_risk:.2f}%")
        
        if avg_rr < 1.5:
            print("⚠️ 平均风险收益比偏低")
        if avg_risk > 3:
            print("⚠️ 单笔风险偏高")
    
    # 4. 价格匹配验证
    print(f"\n【价格匹配验证】")
    price_issues = check_price_matching(df, signals)
    if price_issues:
        print("⚠️ 价格匹配问题:")
        for issue in price_issues[:3]:
            print(f"  - {issue}")
    else:
        print("✓ 价格匹配合理")

def check_price_matching(df, signals):
    """检查价格匹配合理性"""
    issues = []
    
    for i, sig in enumerate(signals[:20]):
        ts, price, action, stop_loss, take_profit, _ = sig
        
        try:
            # 找到最接近的时间点
            closest_time = min(df.index, key=lambda x: abs((x - ts).total_seconds()))
            closest_idx = df.index.get_loc(closest_time)
            
            # 获取当时的OHLC数据
            ohlc = df.iloc[closest_idx]
            
            # 检查信号价格是否在合理范围内
            if not (ohlc['low'] * 0.999 <= price <= ohlc['high'] * 1.001):
                issues.append(f"信号{i+1}价格{price:.2f}不在K线范围[{ohlc['low']:.2f}, {ohlc['high']:.2f}]")
            
        except Exception as e:
            issues.append(f"信号{i+1}时间匹配错误: {str(e)}")
    
    return issues

def create_validation_report(df, signals, trades, symbol):
    """创建完整的验证报告 - 适配新的交易格式"""
    
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    fig, axes = plt.subplots(4, 1, figsize=(15, 16))
    
    # 检查必要的列是否存在
    required_columns = ['equity', 'cash']
    for col in required_columns:
        if col not in df.columns:
            print(f"❌ 错误: DataFrame中缺少 '{col}' 列")
            return
    
    # 1. 权益曲线
    axes[0].plot(df.index, df['equity'], label='总权益', color='purple', linewidth=2)
    axes[0].set_title(f'{symbol} - 权益曲线', fontsize=14, fontweight='bold')
    axes[0].set_ylabel('权益 ($)')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # 计算回撤
    equity_series = pd.Series(df['equity'].values, index=df.index)
    rolling_max = equity_series.expanding().max()
    drawdown = (equity_series - rolling_max) / rolling_max * 100
    
    if not drawdown.empty and not drawdown.isna().all():
        max_dd_idx = drawdown.idxmin()
        max_dd_value = drawdown.min()
        
        axes[0].axhline(y=rolling_max.loc[max_dd_idx], color='red', linestyle='--', alpha=0.5)
        axes[0].annotate(f'最大回撤: {max_dd_value:.1f}%', 
                        xy=(max_dd_idx, equity_series.loc[max_dd_idx]),
                        xytext=(10, 10), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.3', fc='yellow', alpha=0.7))
    else:
        max_dd_value = 0
    
    # 2. 现金和保证金使用（如果有的话）
    axes[1].plot(df.index, df['cash'], label='现金', color='green')
    if 'margin_used' in df.columns:
        axes[1].plot(df.index, df['margin_used'], label='已用保证金', color='red')
    if 'position_value' in df.columns:
        axes[1].plot(df.index, df['position_value'], label='仓位价值', color='orange')
    
    axes[1].set_title('资金分布', fontsize=14)
    axes[1].set_ylabel('金额 ($)')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    # 3. 回撤曲线
    if not drawdown.empty and not drawdown.isna().all():
        axes[2].fill_between(df.index, 0, drawdown, alpha=0.3, color='red', label='回撤')
        axes[2].set_title('回撤曲线', fontsize=14)
        axes[2].set_ylabel('回撤 (%)')
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)
        axes[2].invert_yaxis()
    else:
        axes[2].text(0.5, 0.5, '无回撤数据', ha='center', va='center', transform=axes[2].transAxes)
        axes[2].set_title('回撤曲线', fontsize=14)
    
    # 4. 价格和交易点
    axes[3].plot(df.index, df['close'], label='价格', color='blue', alpha=0.7)
    
    # 标记交易点 - 适配新格式
    if trades and len(trades) > 0:
        # 处理字典格式的交易记录
        if isinstance(trades[0], dict):
            entry_times = [pd.to_datetime(t['entry_time']) for t in trades]
            close_times = [pd.to_datetime(t['close_time']) for t in trades]
            entry_prices = [t['entry_price'] for t in trades]
            close_prices = [t['close_price'] for t in trades]
            
            # 用不同颜色区分盈亏交易
            profitable_trades = [t for t in trades if t['pnl'] > 0]
            losing_trades = [t for t in trades if t['pnl'] <= 0]
            
            if profitable_trades:
                profit_entry_times = [pd.to_datetime(t['entry_time']) for t in profitable_trades]
                profit_entry_prices = [t['entry_price'] for t in profitable_trades]
                profit_close_times = [pd.to_datetime(t['close_time']) for t in profitable_trades]
                profit_close_prices = [t['close_price'] for t in profitable_trades]
                
                axes[3].scatter(profit_entry_times, profit_entry_prices, color='green', 
                              marker='^', s=40, label='盈利开仓', zorder=5)
                axes[3].scatter(profit_close_times, profit_close_prices, color='darkgreen', 
                              marker='v', s=40, label='盈利平仓', zorder=5)
            
            if losing_trades:
                loss_entry_times = [pd.to_datetime(t['entry_time']) for t in losing_trades]
                loss_entry_prices = [t['entry_price'] for t in losing_trades]
                loss_close_times = [pd.to_datetime(t['close_time']) for t in losing_trades]
                loss_close_prices = [t['close_price'] for t in losing_trades]
                
                axes[3].scatter(loss_entry_times, loss_entry_prices, color='red', 
                              marker='^', s=40, label='亏损开仓', zorder=5)
                axes[3].scatter(loss_close_times, loss_close_prices, color='darkred', 
                              marker='v', s=40, label='亏损平仓', zorder=5)
        
        # 处理旧格式的交易记录（元组格式）
        else:
            entry_times = []
            entry_prices = []
            
            for trade in trades:
                if len(trade) >= 3 and trade[2] == 'buy':
                    entry_times.append(trade[0])
                    entry_prices.append(trade[1])
            
            if entry_times:
                axes[3].scatter(entry_times, entry_prices, color='green', 
                              marker='^', s=40, label='开仓', zorder=5)
    
    axes[3].set_title('价格走势与交易点', fontsize=14)
    axes[3].set_ylabel('价格')
    axes[3].set_xlabel('时间')
    axes[3].legend()
    axes[3].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    
    # 生成文字报告
    final_equity = df['equity'].iloc[-1]
    initial_equity = df['equity'].iloc[0]
    total_return = (final_equity - initial_equity) / initial_equity * 100
    
    print(f"\n{'='*60}")
    print(f"最终验证报告 - {symbol}")
    print(f"{'='*60}")
    print(f"初始资金: ${initial_equity:,.2f}")
    print(f"最终资金: ${final_equity:,.2f}")
    print(f"总收益率: {total_return:.2f}%")
    print(f"最大回撤: {max_dd_value:.2f}%")
    
    # 交易统计
    if trades and isinstance(trades[0], dict):
        profitable_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]
        
        print(f"总交易数: {len(trades)}")
        print(f"盈利交易: {len(profitable_trades)} ({len(profitable_trades)/max(len(trades),1)*100:.1f}%)")
        print(f"亏损交易: {len(losing_trades)} ({len(losing_trades)/max(len(trades),1)*100:.1f}%)")
        
        if profitable_trades:
            avg_profit = np.mean([t['pnl'] for t in profitable_trades])
            max_profit = max([t['pnl'] for t in profitable_trades])
            print(f"平均盈利: ${avg_profit:.2f}")
            print(f"最大盈利: ${max_profit:.2f}")
            
        if losing_trades:
            avg_loss = np.mean([t['pnl'] for t in losing_trades])
            max_loss = min([t['pnl'] for t in losing_trades])
            print(f"平均亏损: ${avg_loss:.2f}")
            print(f"最大亏损: ${max_loss:.2f}")
            
        # 风险收益比
        if profitable_trades and losing_trades:
            profit_factor = sum([t['pnl'] for t in profitable_trades]) / abs(sum([t['pnl'] for t in losing_trades]))
            print(f"盈亏比: {profit_factor:.2f}")
    else:
        print(f"信号数量: {len(signals)}")
        print(f"执行交易数: {len([t for t in trades if len(t) >= 3 and t[2] == 'buy'])}")
    
    print(f"\n【策略评估】")
    
    # 性能评估
    if total_return > 100:
        print("⚠️ 收益率过高，可能存在过拟合风险")
    elif total_return < -20:
        print("⚠️ 收益率过低，策略可能需要优化")
    else:
        print("✓ 收益率在合理范围内")
    
    if abs(max_dd_value) > 30:
        print("⚠️ 最大回撤过大，风险控制需要加强")
    elif abs(max_dd_value) < 5:
        print("✓ 回撤控制良好")
    else:
        print("✓ 回撤在可接受范围内")
    
    # 交易频率评估
    if trades and isinstance(trades[0], dict):
        total_days = (df.index[-1] - df.index[0]).days
        trades_per_month = len(trades) / max(total_days/30, 1)
        
        if trades_per_month > 30:
            print("⚠️ 交易过于频繁，可能存在过度交易")
        elif trades_per_month < 2:
            print("⚠️ 交易频率过低，策略可能不够活跃")
        else:
            print("✓ 交易频率合理")

def analyze_trade_performance(trades):
    """详细分析交易表现"""
    if not trades or not isinstance(trades[0], dict):
        return
        
    print(f"\n【交易表现分析】")
    
    # 计算各种指标
    returns = [t['return'] for t in trades]
    pnls = [t['pnl'] for t in trades]
    leverages = [t['leverage'] for t in trades]
    
    # 按平仓原因分类
    stop_loss_trades = [t for t in trades if t['reason'] == '止损']
    take_profit_trades = [t for t in trades if t['reason'] == '止盈']
    
    print(f"止损交易: {len(stop_loss_trades)} ({len(stop_loss_trades)/len(trades)*100:.1f}%)")
    print(f"止盈交易: {len(take_profit_trades)} ({len(take_profit_trades)/len(trades)*100:.1f}%)")
    
    if returns:
        print(f"平均收益率: {np.mean(returns)*100:.2f}%")
        print(f"收益率标准差: {np.std(returns)*100:.2f}%")
        print(f"最佳交易: {max(returns)*100:.2f}%")
        print(f"最差交易: {min(returns)*100:.2f}%")
    
    if leverages:
        print(f"平均杠杆: {np.mean(leverages):.1f}x")
        print(f"最大杠杆: {max(leverages):.1f}x")

def main():
    print("策略验证工具 v2.0")
    print("支持新的回测系统和交易记录格式")
    print("\n使用方法:")
    print("1. 运行修复后的回测系统")
    print("2. validate_strategy(df, signals, symbol)")
    print("3. create_validation_report(df_backtest, signals, trades, symbol)")
    print("4. analyze_trade_performance(trades)")

if __name__ == "__main__":
    main()