# fee_calculator_demo.py - 基于用户实际费率的手续费计算演示
"""
基于用户实际费率的OKX合约手续费计算演示
用户费率: 挂单 0.020%, 吃单 0.050%
"""

def demonstrate_okx_fee_calculation():
    """演示OKX官方手续费计算公式"""
    print("="*60)
    print("OKX合约手续费计算演示")
    print("="*60)
    print("用户费率等级: VIP 1")
    print("挂单费率 (Maker): 0.020%")
    print("吃单费率 (Taker): 0.050%")
    print()
    
    # 用户实际费率
    maker_rate = 0.0002  # 0.020%
    taker_rate = 0.0005  # 0.050%
    
    # 合约信息
    ct_val = 0.01  # BTC-USDT-SWAP 面值: 0.01 BTC
    
    # 测试场景
    scenarios = [
        {"price": 100000, "position_value": 500, "desc": "小额测试"},
        {"price": 100000, "position_value": 2000, "desc": "中等仓位"},
        {"price": 100000, "position_value": 10000, "desc": "大额仓位"},
        {"price": 50000, "position_value": 1000, "desc": "低价位测试"},
    ]
    
    print("🧮 USDT永续合约手续费计算 (BTC-USDT-SWAP)")
    print("公式: 面值 × 张数 × 价格 × 费率")
    print("-" * 80)
    print(f"{'场景':<12} {'BTC价格':<10} {'目标价值':<10} {'张数':<8} {'实际价值':<12} {'挂单费':<10} {'吃单费'}")
    print("-" * 80)
    
    for scenario in scenarios:
        price = scenario["price"]
        target_value = scenario["position_value"]
        desc = scenario["desc"]
        
        # 计算合约张数
        contract_size = target_value / (ct_val * price)
        contract_size = round(contract_size)  # 取整到最小单位
        
        # 实际仓位价值
        actual_value = ct_val * contract_size * price
        
        # OKX官方公式计算手续费
        maker_fee = ct_val * contract_size * price * maker_rate
        taker_fee = ct_val * contract_size * price * taker_rate
        
        print(f"{desc:<12} ${price:<9,} ${target_value:<9} {contract_size:<8} ${actual_value:<11,.2f} ${maker_fee:<9.2f} ${taker_fee:.2f}")
    
    print()
    print("📊 手续费成本分析")
    print("-" * 50)
    
    # 分析不同仓位大小的手续费占比
    test_values = [500, 1000, 2000, 5000, 10000]
    price = 100000
    
    print(f"{'仓位价值':<12} {'开平成本':<12} {'占仓位比例':<12} {'占风险比例'}")
    print("-" * 50)
    
    for value in test_values:
        # 计算开仓+平仓的双向手续费成本
        contract_size = round(value / (ct_val * price))
        actual_value = ct_val * contract_size * price
        
        # 双向手续费（开仓+平仓，都使用吃单费率）
        total_fee = (ct_val * contract_size * price * taker_rate) * 2
        
        # 手续费占仓位价值的比例
        fee_pct = (total_fee / actual_value) * 100
        
        # 假设1.5%风险预算，手续费占风险预算的比例
        risk_budget = actual_value * 0.015
        fee_risk_pct = (total_fee / risk_budget) * 100
        
        print(f"${value:<11} ${total_fee:<11.2f} {fee_pct:<11.2f}% {fee_risk_pct:<11.1f}%")
    
    print()
    print("💡 重要发现")
    print("-" * 30)
    print("• 手续费按实际仓位价值计算，与保证金无关")
    print("• 杠杆越高，仓位价值越大，手续费越高")
    print("• 手续费是双向成本：开仓 + 平仓")
    print("• 使用限价单（挂单）可以显著降低成本")
    print(f"• 挂单vs吃单节省: {((taker_rate - maker_rate) / taker_rate) * 100:.0f}%")
    
    print()
    print("🎯 交易成本优化建议")
    print("-" * 30)
    print("1. 尽可能使用限价单（挂单）而非市价单")
    print("2. 合理控制杠杆倍数，避免过高的仓位价值")
    print("3. 考虑手续费成本制定止盈止损策略")
    print("4. 频繁交易会显著增加累计成本")
    
def calculate_breakeven_analysis():
    """盈亏平衡点分析"""
    print("\n" + "="*60)
    print("盈亏平衡点分析")
    print("="*60)
    
    taker_rate = 0.0005  # 0.050%
    slippage = 0.0001   # 0.01% 滑点
    
    # 总交易成本率（开仓+平仓+滑点）
    total_cost_rate = (taker_rate + slippage) * 2
    
    print(f"单向交易成本: {(taker_rate + slippage)*100:.3f}%")
    print(f"双向交易成本: {total_cost_rate*100:.3f}%")
    print(f"盈亏平衡点: 价格需要变动 {total_cost_rate*100:.3f}% 才能覆盖交易成本")
    
    print(f"\n📈 不同止损距离的成本占比:")
    stop_distances = [0.005, 0.010, 0.015, 0.020, 0.030]  # 0.5% - 3%
    
    for stop_dist in stop_distances:
        cost_ratio = (total_cost_rate / stop_dist) * 100
        print(f"   止损距离 {stop_dist*100:.1f}%: 手续费占风险的 {cost_ratio:.1f}%")
        
    print(f"\n结论: 对于{1.5:.1f}%的止损策略，手续费约占总风险的 {(total_cost_rate / 0.015)*100:.0f}%")

def main():
    """主函数"""
    demonstrate_okx_fee_calculation()
    calculate_breakeven_analysis()
    
    print(f"\n" + "="*60)
    print("说明")
    print("="*60)
    print("• 以上计算基于OKX官方手续费公式")
    print("• 实际交易中请以API返回的费率为准")
    print("• 沙盒环境使用相同费率进行模拟")
    print("• 强平和交割有特殊费率规则")

if __name__ == "__main__":
    main()