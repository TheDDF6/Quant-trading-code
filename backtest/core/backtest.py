# ideal_backtest.py - 理想化动态风险回测系统
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import importlib
import sys
import os

# 设置输出编码
sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
sys.stderr.reconfigure(encoding='utf-8', errors='ignore')

# 添加统一策略模块路径
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent  # 回到项目根目录
sys.path.insert(0, str(project_root))

# 配置
DATA_DIR = Path(r"D:\VSC\crypto_data")
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def load_and_prepare_data(symbol, timeframe, start_date=None, end_date=None):
    """加载并准备数据"""
    file_path = DATA_DIR / f"{symbol}_5m.parquet"
    if not file_path.exists():
        print(f"文件不存在: {file_path}")
        return None
        
    df = pd.read_parquet(file_path)
    df.index = pd.to_datetime(df.index)
    df.sort_index(inplace=True)
    
    if start_date:
        df = df[df.index >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df.index <= pd.to_datetime(end_date)]
    
    if timeframe != '5m':
        rule_map = {'15m': '15min', '1h': '1h', '4h': '4h', '1d': '1D'}
        if timeframe in rule_map:
            rule = rule_map[timeframe]
            df_resampled = pd.DataFrame()
            df_resampled['open'] = df['open'].resample(rule).first()
            df_resampled['high'] = df['high'].resample(rule).max()
            df_resampled['low'] = df['low'].resample(rule).min()
            df_resampled['close'] = df['close'].resample(rule).last()
            df_resampled['volume'] = df['volume'].resample(rule).sum()
            df_resampled.dropna(inplace=True)
            df = df_resampled
    
    print(f"数据加载完成: {len(df)} 条记录")
    print(f"时间范围: {df.index[0]} 至 {df.index[-1]}")
    return df

def ideal_dynamic_backtest(df, signals, initial_capital=10000, 
                          risk_per_trade=0.015,  # 1.5%动态风险
                          max_leverage=100):      # 允许高杠杆
    """
    理想化动态风险回测
    - 无手续费
    - 无滑点
    - 动态风险（基于当前资金）
    - 允许高杠杆
    """
    # 初始化
    capital = initial_capital
    trades = []
    equity_curve = []
    position = None
    
    # 信号匹配
    signal_dict = {}
    for sig in signals:
        sig_time = sig[0]
        if len(df.index) > 0:
            time_diffs = abs(df.index - sig_time)
            min_diff = time_diffs.min()
            if min_diff <= pd.Timedelta(minutes=5):
                closest_time = df.index[time_diffs.argmin()]
                if closest_time not in signal_dict:
                    signal_dict[closest_time] = sig
    
    print(f"\n理想化回测参数:")
    print(f"初始资金: ${initial_capital:,.2f}")
    print(f"动态风险: {risk_per_trade*100:.1f}%")
    print(f"最大杠杆: {max_leverage}x")
    print(f"匹配信号: {len(signal_dict)}/{len(signals)}")
    
    # 主循环
    for timestamp, bar in df.iterrows():
        # 1. 检查平仓
        if position is not None:
            should_close = False
            exit_price = bar['close']
            exit_reason = ""
            
            if position['direction'] == 'long':
                if bar['low'] <= position['stop_loss']:
                    should_close = True
                    exit_price = position['stop_loss']
                    exit_reason = "止损"
                elif bar['high'] >= position['take_profit']:
                    should_close = True
                    exit_price = position['take_profit']
                    exit_reason = "止盈"
            else:  # short
                if bar['high'] >= position['stop_loss']:
                    should_close = True
                    exit_price = position['stop_loss']
                    exit_reason = "止损"
                elif bar['low'] <= position['take_profit']:
                    should_close = True
                    exit_price = position['take_profit']
                    exit_reason = "止盈"
            
            if should_close:
                # 计算盈亏
                if position['direction'] == 'long':
                    pnl = position['size'] * (exit_price - position['entry_price'])
                else:
                    pnl = position['size'] * (position['entry_price'] - exit_price)
                
                # 更新资金
                capital = capital + position['margin'] + pnl
                
                # 记录交易
                trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': timestamp,
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'direction': position['direction'],
                    'size': position['size'],
                    'leverage': position['leverage'],
                    'pnl': pnl,
                    'return_pct': (pnl / position['risk_amount']) * 100,
                    'reason': exit_reason,
                    'capital_after': capital
                })
                
                position = None
        
        # 2. 检查开仓信号
        if position is None and timestamp in signal_dict:
            sig = signal_dict[timestamp]
            _, entry_price, action, stop_loss, take_profit, _ = sig
            
            if action == 'buy':
                direction = 'long' if take_profit > entry_price else 'short'
                stop_distance = abs(entry_price - stop_loss)
                
                if stop_distance > 0 and capital > 0:
                    # 动态风险：基于当前资金
                    risk_amount = capital * risk_per_trade
                    
                    # 计算所需仓位价值
                    position_value = risk_amount / (stop_distance / entry_price)
                    
                    # 计算杠杆
                    required_leverage = position_value / capital
                    
                    # 使用实际需要的杠杆（必须是整数，1-100）
                    required_leverage_int = max(1, min(100, int(round(required_leverage))))
                    actual_leverage = min(required_leverage_int, max_leverage)
                    
                    # 重新计算仓位价值以控制风险在1.5%
                    # 优先保证风险控制，杠杆为整数
                    actual_position_value = risk_amount / (stop_distance / entry_price)
                    max_position_value = capital * actual_leverage
                    actual_position_value = min(actual_position_value, max_position_value)
                    
                    # 计算保证金
                    margin = actual_position_value / actual_leverage
                    
                    # 开仓
                    if margin <= capital:
                        capital = capital - margin
                        
                        position = {
                            'entry_time': timestamp,
                            'entry_price': entry_price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'direction': direction,
                            'size': actual_position_value / entry_price,
                            'margin': margin,
                            'leverage': actual_leverage,
                            'risk_amount': risk_amount
                        }
        
        # 3. 计算权益
        if position is not None:
            if position['direction'] == 'long':
                unrealized_pnl = position['size'] * (bar['close'] - position['entry_price'])
            else:
                unrealized_pnl = position['size'] * (position['entry_price'] - bar['close'])
            current_equity = capital + position['margin'] + unrealized_pnl
        else:
            current_equity = capital
        
        equity_curve.append(current_equity)
    
    # 强制平仓
    if position is not None:
        final_price = df['close'].iloc[-1]
        if position['direction'] == 'long':
            pnl = position['size'] * (final_price - position['entry_price'])
        else:
            pnl = position['size'] * (position['entry_price'] - final_price)
        
        capital = capital + position['margin'] + pnl
        
        trades.append({
            'entry_time': position['entry_time'],
            'exit_time': df.index[-1],
            'entry_price': position['entry_price'],
            'exit_price': final_price,
            'direction': position['direction'],
            'size': position['size'],
            'leverage': position['leverage'],
            'pnl': pnl,
            'return_pct': (pnl / position['risk_amount']) * 100,
            'reason': '强制平仓',
            'capital_after': capital
        })
        
        equity_curve[-1] = capital
    
    # 结果统计
    df_result = df.copy()
    df_result['equity'] = equity_curve
    
    final_equity = equity_curve[-1]
    total_return = (final_equity - initial_capital) / initial_capital * 100
    
    # 计算复合年化收益率
    days = (df.index[-1] - df.index[0]).days
    years = days / 365.25
    if years > 0 and final_equity > 0:
        cagr = (pow(final_equity / initial_capital, 1/years) - 1) * 100
    else:
        cagr = 0
    
    print(f"\n{'='*50}")
    print(f"理想化回测结果:")
    print(f"{'='*50}")
    print(f"初始资金: ${initial_capital:,.2f}")
    print(f"最终权益: ${final_equity:,.2f}")
    print(f"总收益率: {total_return:.2f}%")
    print(f"年化收益率(CAGR): {cagr:.2f}%")
    print(f"总交易数: {len(trades)}")
    
    if trades:
        win_trades = [t for t in trades if t['pnl'] > 0]
        lose_trades = [t for t in trades if t['pnl'] <= 0]
        
        print(f"盈利交易: {len(win_trades)} ({len(win_trades)/len(trades)*100:.1f}%)")
        print(f"亏损交易: {len(lose_trades)} ({len(lose_trades)/len(trades)*100:.1f}%)")
        
        # 止盈止损统计
        tp_trades = [t for t in trades if t['reason'] == '止盈']
        sl_trades = [t for t in trades if t['reason'] == '止损']
        print(f"止盈退出: {len(tp_trades)} ({len(tp_trades)/len(trades)*100:.1f}%)")
        print(f"止损退出: {len(sl_trades)} ({len(sl_trades)/len(trades)*100:.1f}%)")
        
        # 最大回撤
        equity_series = pd.Series(equity_curve)
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max * 100
        max_drawdown = drawdown.min()
        print(f"最大回撤: {max_drawdown:.2f}%")
        
        # 平均盈亏
        if win_trades:
            avg_win = np.mean([t['pnl'] for t in win_trades])
            avg_win_pct = np.mean([t['return_pct'] for t in win_trades])
            max_win = max([t['pnl'] for t in win_trades])
            print(f"平均盈利: ${avg_win:.2f} ({avg_win_pct:.1f}%)")
            print(f"最大盈利: ${max_win:.2f}")
        
        if lose_trades:
            avg_loss = np.mean([t['pnl'] for t in lose_trades])
            avg_loss_pct = np.mean([t['return_pct'] for t in lose_trades])
            max_loss = min([t['pnl'] for t in lose_trades])
            print(f"平均亏损: ${avg_loss:.2f} ({avg_loss_pct:.1f}%)")
            print(f"最大亏损: ${max_loss:.2f}")
            
        # 盈亏比
        if win_trades and lose_trades:
            profit_factor = abs(sum([t['pnl'] for t in win_trades]) / sum([t['pnl'] for t in lose_trades]))
            print(f"盈亏比: {profit_factor:.2f}")
        
        # 平均杠杆
        avg_leverage = np.mean([t['leverage'] for t in trades])
        max_used_leverage = max([t['leverage'] for t in trades])
        print(f"平均杠杆: {avg_leverage:.1f}x")
        print(f"最大使用杠杆: {max_used_leverage:.1f}x")
    
    return df_result, trades

def plot_ideal_results(df, trades, symbol):
    """绘制理想化回测结果"""
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    
    # 1. 权益曲线（线性坐标）
    axes[0].plot(df.index, df['equity'], color='purple', linewidth=2)
    axes[0].axhline(y=df['equity'].iloc[0], color='gray', linestyle='--', alpha=0.5)
    axes[0].set_title(f'{symbol} - 权益曲线')
    axes[0].set_ylabel('权益 ($)')
    axes[0].grid(True, alpha=0.3)
    
    # 2. 回撤曲线
    equity_series = pd.Series(df['equity'].values)
    rolling_max = equity_series.expanding().max()
    drawdown = (equity_series - rolling_max) / rolling_max * 100
    axes[1].fill_between(df.index, 0, drawdown, alpha=0.5, color='red')
    axes[1].set_title('回撤曲线')
    axes[1].set_ylabel('回撤 (%)')
    axes[1].grid(True, alpha=0.3)
    axes[1].invert_yaxis()
    
    # 3. 价格走势与交易信号
    axes[2].plot(df.index, df['close'], color='blue', alpha=0.7, linewidth=1, label='价格')
    
    # 添加交易信号标记
    if trades and len(trades) > 0:
        # 分离盈利和亏损交易
        profitable_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]
        
        # 标记盈利交易
        if profitable_trades:
            entry_times_profit = [pd.to_datetime(t['entry_time']) for t in profitable_trades]
            entry_prices_profit = [t['entry_price'] for t in profitable_trades]
            exit_times_profit = [pd.to_datetime(t['exit_time']) for t in profitable_trades]
            exit_prices_profit = [t['exit_price'] for t in profitable_trades]
            
            axes[2].scatter(entry_times_profit, entry_prices_profit, 
                          color='green', marker='^', s=60, label='盈利开仓', zorder=5)
            axes[2].scatter(exit_times_profit, exit_prices_profit, 
                          color='darkgreen', marker='v', s=60, label='盈利平仓', zorder=5)
        
        # 标记亏损交易
        if losing_trades:
            entry_times_loss = [pd.to_datetime(t['entry_time']) for t in losing_trades]
            entry_prices_loss = [t['entry_price'] for t in losing_trades]
            exit_times_loss = [pd.to_datetime(t['exit_time']) for t in losing_trades]
            exit_prices_loss = [t['exit_price'] for t in losing_trades]
            
            axes[2].scatter(entry_times_loss, entry_prices_loss, 
                          color='red', marker='^', s=60, label='亏损开仓', zorder=5)
            axes[2].scatter(exit_times_loss, exit_prices_loss, 
                          color='darkred', marker='v', s=60, label='亏损平仓', zorder=5)
        
        # 绘制交易连线
        for trade in trades[:20]:  # 限制连线数量避免图表过于复杂
            entry_time = pd.to_datetime(trade['entry_time'])
            exit_time = pd.to_datetime(trade['exit_time'])
            entry_price = trade['entry_price']
            exit_price = trade['exit_price']
            
            color = 'green' if trade['pnl'] > 0 else 'red'
            alpha = 0.6 if trade['pnl'] > 0 else 0.4
            
            axes[2].plot([entry_time, exit_time], [entry_price, exit_price], 
                        color=color, alpha=alpha, linewidth=1, linestyle='--')
    
    axes[2].set_title('价格走势与交易信号')
    axes[2].set_ylabel('价格 ($)')
    axes[2].set_xlabel('时间')
    axes[2].legend(loc='upper left')
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

def analyze_strategy_reasonableness(df, trades, signals, symbol):
    """分析策略合理性"""
    print(f"\n{'='*60}")
    print(f"策略合理性分析 - {symbol}")
    print(f"{'='*60}")
    
    # 时间分析
    total_days = (df.index[-1] - df.index[0]).days
    total_hours = total_days * 24
    
    print(f"数据时间跨度: {total_days}天 ({total_days/365.25:.1f}年)")
    print(f"总信号数: {len(signals)}")
    print(f"执行交易数: {len(trades)}")
    print(f"平均每天交易: {len(trades)/max(total_days, 1):.2f}笔")
    print(f"平均每小时交易: {len(trades)/max(total_hours, 1):.3f}笔")
    
    if len(trades)/max(total_days, 1) > 2:
        print("警告: 交易频率过高，可能存在过度交易")
    
    # 收益率分析
    if trades:
        returns = [t['return_pct'] for t in trades]
        win_rate = len([t for t in trades if t['pnl'] > 0]) / len(trades)
        
        print(f"\n胜率: {win_rate*100:.1f}%")
        print(f"平均单笔收益率: {np.mean(returns):.1f}%")
        print(f"收益率标准差: {np.std(returns):.1f}%")
        
        # 检查极端收益
        extreme_returns = [r for r in returns if abs(r) > 200]
        if extreme_returns:
            print(f"警告: 发现{len(extreme_returns)}笔极端收益交易 (>200%)")
    
    # 杠杆分析
    if trades:
        leverages = [t['leverage'] for t in trades]
        print(f"\n平均杠杆: {np.mean(leverages):.1f}x")
        print(f"最大杠杆: {max(leverages):.1f}x")
        
        high_leverage_trades = [t for t in trades if t['leverage'] > 5]
        if high_leverage_trades:
            print(f"警告: {len(high_leverage_trades)}笔交易使用了>5x杠杆")
    else:
        print(f"\n无交易数据可供杠杆分析")
    
    # 资金增长分析
    initial_capital = trades[0]['capital_after'] - trades[0]['pnl'] if trades else 10000
    final_capital = trades[-1]['capital_after'] if trades else 10000
    
    capital_growth = []
    for trade in trades:
        capital_growth.append(trade['capital_after'])
    
    # 检查资金增长的平滑性
    if len(capital_growth) > 10:
        growth_rates = []
        for i in range(1, len(capital_growth)):
            growth_rate = (capital_growth[i] - capital_growth[i-1]) / capital_growth[i-1]
            growth_rates.append(abs(growth_rate))
        
        avg_growth_rate = np.mean(growth_rates)
        max_growth_rate = max(growth_rates)
        
        print(f"\n平均单笔资金变化率: {avg_growth_rate*100:.2f}%")
        print(f"最大单笔资金变化率: {max_growth_rate*100:.2f}%")
        
        if max_growth_rate > 0.5:
            print("警告: 存在极端的单笔资金变化")
    
    print(f"\n建议:")
    if len(trades)/max(total_days, 1) > 2:
        print("- 考虑增加信号过滤条件，降低交易频率")
    if trades and np.mean([t['leverage'] for t in trades]) > 3:
        print("- 考虑降低最大杠杆限制")
    print("- 在实际交易中加入手续费和滑点成本")
    print("- 考虑分段测试避免过拟合")

def main():
    # 用户输入
    symbol = input("币种交易对（如BTC-USDT）: ").strip()
    start_date = input("开始日期（YYYY-MM-DD，可空）: ").strip() or None
    end_date = input("结束日期（YYYY-MM-DD，可空）: ").strip() or None
    strategy_name = input("策略名（如rsi_divergence）: ").strip()
    timeframe = input("K线周期（5m/15m/1h/4h/1d）: ").strip()
    
    leverage_input = input("最大杠杆（默认100）: ").strip()
    max_leverage = int(leverage_input) if leverage_input.isdigit() else 100
    
    risk_input = input("单笔风险百分比（默认1.5）: ").strip()
    risk_pct = float(risk_input) / 100 if risk_input else 0.015
    
    # 加载策略
    try:
        strategy = importlib.import_module(f"strategies.{strategy_name}")
    except ImportError as e:
        print(f"无法加载策略: {e}")
        return
    
    # 加载数据
    df = load_and_prepare_data(symbol, timeframe, start_date, end_date)
    if df is None:
        return
    
    # 生成信号
    signals = strategy.generate_signals(df)
    if not signals:
        print("策略未生成任何信号")
        return
    
    # 运行理想化回测
    df_result, trades = ideal_dynamic_backtest(
        df, signals,
        initial_capital=10000,
        risk_per_trade=risk_pct,
        max_leverage=max_leverage
    )
    
    # 绘制结果
    plot_ideal_results(df_result, trades, symbol)
    
    # 策略合理性分析
    analyze_strategy_reasonableness(df_result, trades, signals, symbol)
    
    # 显示最后几笔交易
    if trades:
        print(f"\n最近5笔交易:")
        for i, trade in enumerate(trades[-5:], 1):
            print(f"{i}. {trade['direction'].upper()} {trade['entry_price']:.0f} -> {trade['exit_price']:.0f}")
            print(f"   盈亏: ${trade['pnl']:.2f} ({trade['return_pct']:.1f}%), {trade['reason']}")
            print(f"   杠杆: {trade['leverage']:.1f}x, 资金: ${trade['capital_after']:.2f}")

def run_strategy_backtest(symbol="BTC-USDT", start_date=None, end_date=None,
                          strategy_name="rsi_divergence_unified", timeframe="5m",
                          max_leverage=100, risk_pct=0.015, risk_method="fixed_percentage"):
    """
    运行策略回测的包装函数，可以从其他模块调用
    """
    print(f"运行回测: {symbol}, 策略: {strategy_name}, 时间框架: {timeframe}, 风险方法: {risk_method}")
    
    # 确保路径正确
    import sys
    from pathlib import Path
    backtest_dir = Path(__file__).parent.parent  # backtest目录
    if str(backtest_dir) not in sys.path:
        sys.path.insert(0, str(backtest_dir))
    
    # 加载策略
    try:
        if strategy_name == "rsi_divergence_unified":
            # 使用RSI统一策略
            from unified_strategies.rsi_divergence_unified import generate_signals
            strategy_func = lambda df: generate_signals(df, risk_pct, 1.5, 20, risk_method, timeframe=timeframe)
        elif strategy_name == "volatility_breakout_unified":
            # 使用波动率突破统一策略
            try:
                from unified_strategies.volatility_breakout_unified import generate_signals
                strategy_func = lambda df: generate_signals(df, risk_pct, 2.0, 20, risk_method, timeframe=timeframe)
            except ImportError:
                # 备用导入路径
                import sys
                from pathlib import Path
                backtest_dir = Path(__file__).parent.parent
                sys.path.insert(0, str(backtest_dir))
                from unified_strategies.volatility_breakout_unified import generate_signals
                strategy_func = lambda df: generate_signals(df, risk_pct, 2.0, 20, risk_method, timeframe=timeframe)
        else:
            # 传统策略加载方式
            strategy = importlib.import_module(f"strategies.{strategy_name}")
            strategy_func = strategy.generate_signals
    except ImportError as e:
        print(f"无法加载策略: {e}")
        return
    
    # 加载数据
    df = load_and_prepare_data(symbol, timeframe, start_date, end_date)
    if df is None:
        return
    
    # 生成信号
    signals = strategy_func(df)
    if not signals:
        print("策略未生成任何信号")
        return
    
    # 运行理想化回测
    df_result, trades = ideal_dynamic_backtest(
        df, signals,
        initial_capital=10000,
        risk_per_trade=risk_pct,
        max_leverage=max_leverage
    )
    
    # 绘制结果
    plot_ideal_results(df_result, trades, symbol)
    
    # 策略合理性分析
    analyze_strategy_reasonableness(df_result, trades, signals, symbol)
    
    # 显示最后几笔交易
    if trades:
        print(f"\n最近5笔交易:")
        for i, trade in enumerate(trades[-5:], 1):
            print(f"{i}. {trade['direction'].upper()} {trade['entry_price']:.0f} -> {trade['exit_price']:.0f}")
            print(f"   盈亏: ${trade['pnl']:.2f} ({trade['return_pct']:.1f}%), {trade['reason']}")
            print(f"   杠杆: {trade['leverage']:.1f}x, 资金: ${trade['capital_after']:.2f}")
    
    return df_result, trades

if __name__ == "__main__":
    main()