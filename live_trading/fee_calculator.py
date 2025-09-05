# fee_calculator.py - 手续费计算演示工具
from config.config import config

def demonstrate_fee_impact():
    """演示手续费对交易的影响"""
    print("\n" + "="*60)
    print("手续费影响演示")
    print("="*60)
    
    # 获取配置
    maker_fee = config.get_maker_fee()
    taker_fee = config.get_taker_fee()
    slippage = config.get_slippage_rate()
    risk_per_trade = config.get_risk_per_trade()
    
    print(f"用户等级: 普通用户")
    print(f"挂单手续费: {maker_fee*100:.3f}%")
    print(f"吃单手续费: {taker_fee*100:.3f}%")
    print(f"预估滑点: {slippage*100:.3f}%")
    print(f"单笔风险: {risk_per_trade*100:.1f}%")
    
    # 示例计算
    examples = [
        {"balance": 1000, "btc_price": 50000, "description": "小额测试"},
        {"balance": 5000, "btc_price": 50000, "description": "中等资金"},
        {"balance": 10000, "btc_price": 50000, "description": "较大资金"}
    ]
    
    print(f"\n交易成本示例 (BTC价格: $50,000):")
    print("-" * 60)
    print(f"{'场景':<10} {'资金':<10} {'风险金额':<10} {'仓位价值':<12} {'总手续费':<10} {'手续费占比'}")
    print("-" * 60)
    
    for example in examples:
        balance = example["balance"]
        btc_price = example["btc_price"]
        desc = example["description"]
        
        # 计算风险金额
        risk_amount = balance * risk_per_trade
        
        # 假设止损距离为1%的价格变动
        risk_distance_pct = 0.01  # 1%
        position_value = risk_amount / risk_distance_pct
        
        # 计算手续费 (开仓 + 平仓，使用吃单费率)
        open_fee = position_value * taker_fee
        close_fee = position_value * taker_fee
        slippage_cost = position_value * slippage * 2  # 开仓和平仓
        total_cost = open_fee + close_fee + slippage_cost
        
        # 手续费占风险金额的比例
        cost_ratio = (total_cost / risk_amount) * 100
        
        print(f"{desc:<10} ${balance:<9} ${risk_amount:<9.0f} ${position_value:<11.0f} ${total_cost:<9.2f} {cost_ratio:<.2f}%")
    
    print("\n" + "="*60)
    print("重要提醒:")
    print("="*60)
    print("• 手续费按仓位价值计算，杠杆越高，仓位价值越大，手续费越高")
    print("• 上述计算基于市价单(吃单)，实际可能有所不同")
    print("• 滑点成本在市场波动大时可能更高")
    print("• 频繁交易会显著增加累计手续费成本")
    print("• 建议在沙盒环境测试，观察实际手续费情况")
    
    print(f"\n策略盈亏平衡点分析:")
    print("-" * 40)
    
    # 计算不同仓位价值下的盈亏平衡点
    position_values = [1000, 5000, 10000, 50000]
    
    for pv in position_values:
        total_cost = pv * (taker_fee * 2 + slippage * 2)  # 双向成本
        breakeven_pct = (total_cost / pv) * 100
        
        print(f"仓位价值 ${pv:>6}: 需要价格变动 {breakeven_pct:.3f}% 才能覆盖成本")
    
    print(f"\n结论:")
    print(f"• 对于1%止损的策略，手续费约占风险金额的{((taker_fee * 2 + slippage * 2) / 0.01) * 100:.1f}%")
    print(f"• 这意味着策略胜率需要额外提升{((taker_fee * 2 + slippage * 2) / 0.01) * 100:.1f}%来覆盖成本")
    print(f"• 回测中的{config.get_risk_per_trade()*100:.1f}%月收益需要扣除约{((taker_fee * 2 + slippage * 2) / 0.015) * 100:.1f}%的交易成本")

def calculate_realistic_returns():
    """基于手续费计算更现实的收益预期"""
    print("\n" + "="*60)
    print("现实收益预期修正")
    print("="*60)
    
    # 基于回测结果的数据
    backtest_monthly_returns = [50.6, 44.1, 24.4]  # 走向前分析结果
    avg_monthly_return = sum(backtest_monthly_returns) / len(backtest_monthly_returns)
    
    # 假设每月交易次数 (基于回测中的交易频率)
    estimated_trades_per_month = 90
    
    # 计算月交易成本
    risk_per_trade = config.get_risk_per_trade()
    avg_position_value_per_trade = 1000  # 假设平均仓位价值
    
    # 每笔交易的总成本率
    cost_per_trade_rate = config.get_taker_fee() * 2 + config.get_slippage_rate() * 2
    
    # 月交易成本 (基于仓位价值)
    monthly_cost_rate = cost_per_trade_rate * estimated_trades_per_month / 30  # 平均到每日
    
    print(f"回测月平均收益: {avg_monthly_return:.1f}%")
    print(f"估计月交易次数: {estimated_trades_per_month}")
    print(f"单笔交易成本率: {cost_per_trade_rate*100:.3f}%")
    
    # 修正后的收益
    # 这里简化处理，实际应该根据具体的仓位大小和交易频率计算
    cost_impact = estimated_trades_per_month * cost_per_trade_rate * 0.1  # 简化估算
    adjusted_monthly_return = avg_monthly_return - cost_impact * 100
    
    print(f"交易成本影响: -{cost_impact*100:.2f}%")
    print(f"修正后月收益: {adjusted_monthly_return:.1f}%")
    
    if adjusted_monthly_return > 0:
        adjusted_annual_return = ((1 + adjusted_monthly_return/100)**12 - 1) * 100
        print(f"修正后年化收益: {adjusted_annual_return:.0f}%")
    
    print(f"\n建议:")
    print(f"• 实际交易中严密监控手续费成本")
    print(f"• 考虑降低交易频率以减少成本")
    print(f"• 在可能的情况下使用限价单(挂单)降低费率")

def main():
    """主函数"""
    demonstrate_fee_impact()
    calculate_realistic_returns()
    
    print(f"\n" + "="*60)
    print("使用建议")
    print("="*60)
    print("1. 在开始实盘交易前，先了解预期的交易成本")
    print("2. 设置合理的预期，考虑手续费对收益的影响")
    print("3. 在沙盒环境中验证实际的交易成本")
    print("4. 根据实际成本调整策略参数")

if __name__ == "__main__":
    main()