#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
动态现实收益预估 - 基于具体回测结果的现实收益分析
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def run_realistic_analysis(backtest_result, symbol, strategy):
    """
    基于回测结果进行现实收益预估
    
    Args:
        backtest_result: 回测结果字典
        symbol: 交易对
        strategy: 策略名称
    """
    print("\n" + "="*70)
    print(f"现实收益预估分析 - {symbol} - {strategy}")
    print("="*70)
    
    # 提取回测基础数据
    total_return_pct = backtest_result['total_return_pct']
    total_trades = backtest_result['total_trades']
    win_rate = backtest_result['win_rate']
    trades = backtest_result['trades']
    initial_capital = backtest_result['initial_capital']
    final_capital = backtest_result['final_capital']
    
    print(f"回测基础数据:")
    print(f"  交易对: {symbol}")
    print(f"  策略: {strategy}")
    print(f"  总收益率: {total_return_pct:.2f}%")
    print(f"  总交易数: {total_trades}")
    print(f"  胜率: {win_rate:.1f}%")
    print(f"  初始资金: ${initial_capital:,.2f}")
    print(f"  最终资金: ${final_capital:,.2f}")
    
    if not trades or len(trades) == 0:
        print("\n❌ 没有交易记录，无法进行现实收益预估")
        return
    
    # 分析交易频率
    analyze_trading_frequency(trades, backtest_result)
    
    # 计算现实交易成本
    realistic_costs = calculate_realistic_costs(trades, total_trades)
    
    # 调整收益预估
    adjusted_results = adjust_returns_for_reality(
        backtest_result, realistic_costs
    )
    
    # 保守预估
    conservative_projection = generate_conservative_projection(
        adjusted_results, win_rate, total_return_pct
    )
    
    # 风险评估
    risk_assessment = assess_trading_risks(trades, adjusted_results)
    
    # 最终建议
    generate_trading_recommendations(
        conservative_projection, risk_assessment, symbol, strategy
    )

def analyze_trading_frequency(trades, backtest_result):
    """分析交易频率"""
    print(f"\n" + "-"*50)
    print("交易频率分析:")
    print("-"*50)
    
    total_trades = len(trades)
    if total_trades > 0:
        # 计算平均持仓时间（假设基于5分钟K线）
        avg_hold_time_bars = np.mean([trade.get('hold_time', 10) for trade in trades])
        avg_hold_hours = avg_hold_time_bars * 5 / 60
        
        # 估算交易密度
        trades_per_day = total_trades / 365  # 假设一年数据
        trades_per_week = trades_per_day * 7
        trades_per_month = trades_per_day * 30
        
        print(f"总交易数: {total_trades}")
        print(f"平均持仓时间: {avg_hold_hours:.1f}小时")
        print(f"交易密度:")
        print(f"  日均: {trades_per_day:.1f}笔")
        print(f"  周均: {trades_per_week:.1f}笔") 
        print(f"  月均: {trades_per_month:.1f}笔")
        
        return trades_per_month
    
    return 0

def calculate_realistic_costs(trades, total_trades):
    """计算现实交易成本"""
    print(f"\n" + "-"*50)
    print("现实交易成本分析:")
    print("-"*50)
    
    # OKX期货交易成本（参考实际费率）
    maker_fee = 0.0002  # 0.02% Maker费用
    taker_fee = 0.0005  # 0.05% Taker费用
    funding_cost = 0.0001  # 资金费率（每8小时）
    slippage = 0.001    # 滑点损失约0.1%
    
    # 假设50%是Maker订单，50%是Taker订单
    avg_trading_fee = (maker_fee + taker_fee) / 2
    
    # 每笔交易的总成本（开仓+平仓）
    cost_per_trade_pct = (avg_trading_fee * 2 + slippage) * 100
    
    print(f"交易费用:")
    print(f"  Maker费用: {maker_fee*100:.3f}%")
    print(f"  Taker费用: {taker_fee*100:.3f}%")
    print(f"  平均交易费: {avg_trading_fee*100:.3f}%")
    print(f"  滑点成本: {slippage*100:.2f}%")
    print(f"  资金费用: {funding_cost*100:.3f}%/8h")
    
    print(f"\n每笔交易总成本: {cost_per_trade_pct:.2f}%")
    print(f"总交易次数: {total_trades}")
    
    total_cost_pct = cost_per_trade_pct * total_trades
    print(f"累计交易成本: {total_cost_pct:.2f}%")
    
    return {
        'cost_per_trade_pct': cost_per_trade_pct,
        'total_cost_pct': total_cost_pct,
        'maker_fee': maker_fee,
        'taker_fee': taker_fee,
        'slippage': slippage,
        'funding_cost': funding_cost
    }

def adjust_returns_for_reality(backtest_result, costs):
    """调整收益以反映现实因素"""
    print(f"\n" + "-"*50)
    print("现实因素调整:")
    print("-"*50)
    
    original_return = backtest_result['total_return_pct']
    total_cost = costs['total_cost_pct']
    
    # 基础调整：扣除交易成本
    basic_adjusted = original_return - total_cost
    
    print(f"原始收益率: {original_return:.2f}%")
    print(f"交易成本: {total_cost:.2f}%")
    print(f"扣除成本后: {basic_adjusted:.2f}%")
    
    # 心理因素调整（实际执行中的纪律性）
    discipline_factor = 0.85  # 假设85%的执行纪律
    psychology_adjusted = basic_adjusted * discipline_factor
    
    print(f"考虑执行纪律(85%): {psychology_adjusted:.2f}%")
    
    # 市场环境变化调整
    market_adaptation_factor = 0.8  # 策略可能逐步失效
    market_adjusted = psychology_adjusted * market_adaptation_factor
    
    print(f"考虑策略适应性(80%): {market_adjusted:.2f}%")
    
    return {
        'original': original_return,
        'cost_adjusted': basic_adjusted,
        'psychology_adjusted': psychology_adjusted,
        'final_adjusted': market_adjusted
    }

def generate_conservative_projection(adjusted_results, win_rate, original_return):
    """生成保守预估"""
    print(f"\n" + "-"*50)
    print("保守预估计算:")
    print("-"*50)
    
    final_return = adjusted_results['final_adjusted']
    
    # 进一步保守化处理
    if final_return > 50:
        # 如果收益过高，进一步降低
        conservative_return = min(final_return * 0.6, 30)
        print(f"高收益保守化: {final_return:.2f}% → {conservative_return:.2f}%")
    elif final_return > 20:
        conservative_return = final_return * 0.7
        print(f"中等收益保守化: {final_return:.2f}% → {conservative_return:.2f}%")
    else:
        conservative_return = final_return * 0.9
        print(f"低收益轻度保守化: {final_return:.2f}% → {conservative_return:.2f}%")
    
    # 年化收益计算（假设数据是1年）
    annual_return = conservative_return
    monthly_return = (1 + conservative_return/100)**(1/12) - 1
    
    print(f"\n最终保守预估:")
    print(f"  年化收益率: {annual_return:.2f}%")
    print(f"  月均收益率: {monthly_return*100:.2f}%")
    
    return {
        'annual_return': annual_return,
        'monthly_return': monthly_return * 100,
        'conservative_factor': conservative_return / original_return if original_return != 0 else 0
    }

def assess_trading_risks(trades, adjusted_results):
    """评估交易风险"""
    print(f"\n" + "-"*50)
    print("风险评估:")
    print("-"*50)
    
    if not trades:
        return {'risk_level': 'unknown'}
    
    # 计算最大亏损
    losses = [trade['pnl'] for trade in trades if trade['pnl'] < 0]
    max_loss = min(losses) if losses else 0
    
    # 计算连续亏损
    consecutive_losses = 0
    max_consecutive_losses = 0
    for trade in trades:
        if trade['pnl'] < 0:
            consecutive_losses += 1
            max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
        else:
            consecutive_losses = 0
    
    # 收益波动性
    returns = [trade['pnl'] for trade in trades]
    return_volatility = np.std(returns) if len(returns) > 1 else 0
    
    print(f"风险指标:")
    print(f"  最大单笔亏损: ${max_loss:.2f}")
    print(f"  最大连续亏损: {max_consecutive_losses}笔")
    print(f"  收益波动性: ${return_volatility:.2f}")
    
    # 风险等级评估
    risk_score = 0
    if abs(max_loss) > 500:  # 单笔亏损超过$500
        risk_score += 2
    if max_consecutive_losses > 5:
        risk_score += 2
    if return_volatility > 100:
        risk_score += 1
    
    if risk_score >= 4:
        risk_level = "高"
    elif risk_score >= 2:
        risk_level = "中"
    else:
        risk_level = "低"
    
    print(f"  综合风险等级: {risk_level}")
    
    return {
        'risk_level': risk_level,
        'max_loss': max_loss,
        'max_consecutive_losses': max_consecutive_losses,
        'volatility': return_volatility,
        'risk_score': risk_score
    }

def generate_trading_recommendations(projection, risk_assessment, symbol, strategy):
    """生成交易建议"""
    print(f"\n" + "="*70)
    print("实盘交易建议:")
    print("="*70)
    
    annual_return = projection['annual_return']
    risk_level = risk_assessment['risk_level']
    
    print(f"策略: {strategy}")
    print(f"交易对: {symbol}")
    print(f"预估年化收益: {annual_return:.2f}%")
    print(f"风险等级: {risk_level}")
    
    print(f"\n建议:")
    
    if annual_return >= 20 and risk_level in ["低", "中"]:
        print("✅ 策略显示良好潜力，建议:")
        print("   • 从小资金开始测试（建议1000-5000 USDT）")
        print("   • 严格按照回测参数执行")
        print("   • 设置总资金最大回撤限制（如-10%）")
        print("   • 每月评估策略表现")
        
    elif annual_return >= 10 and risk_level != "高":
        print("⚠️ 策略有一定价值，但需谨慎:")
        print("   • 建议极小资金测试（500-2000 USDT）")
        print("   • 密切监控策略衰减情况")
        print("   • 准备随时调整或停止")
        
    elif annual_return >= 5:
        print("🔸 策略收益有限，建议:")
        print("   • 仅用于学习和验证（少于500 USDT）")
        print("   • 观察策略在不同市场环境下的表现")
        print("   • 考虑参数优化")
        
    else:
        print("❌ 不建议实盘交易:")
        print("   • 扣除现实成本后收益不足")
        print("   • 建议继续优化策略")
        print("   • 或寻找其他交易机会")
    
    print(f"\n⚠️ 重要提醒:")
    print(f"   • 历史表现不代表未来收益")
    print(f"   • 加密货币交易存在高风险")
    print(f"   • 请仅用可承受损失的资金")
    print(f"   • 建议设置止损并严格执行")