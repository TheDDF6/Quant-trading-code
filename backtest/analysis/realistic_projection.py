# realistic_projection.py - 现实收益预估
import pandas as pd
import numpy as np

def realistic_returns_analysis():
    """基于走向前分析结果的现实收益预估"""
    
    print("现实收益预估分析")
    print("="*50)
    
    # 走向前分析的实际结果
    monthly_returns = [50.6, 44.1, 24.4]  # 月收益率%
    win_rates = [51.6, 52.3, 46.4]        # 胜率%
    max_drawdowns = [-8.0, -9.7, -9.8]    # 最大回撤%
    
    print("原始回测结果:")
    for i, ret in enumerate(monthly_returns, 1):
        print(f"第{i}轮: {ret:.1f}%月收益, 胜率{win_rates[i-1]:.1f}%, 回撤{max_drawdowns[i-1]:.1f}%")
    
    print(f"\n平均月收益: {np.mean(monthly_returns):.1f}%")
    print(f"收益递减趋势: 从{max(monthly_returns):.1f}%降至{min(monthly_returns):.1f}%")
    
    # 现实因素调整
    print("\n" + "="*50)
    print("现实因素调整:")
    print("="*50)
    
    # 1. 交易成本
    trading_cost = 0.2  # 双向手续费约0.2%
    slippage = 0.1      # 滑点约0.1%
    total_cost = trading_cost + slippage
    
    print(f"交易成本: {trading_cost:.1f}%")
    print(f"滑点成本: {slippage:.1f}%")
    print(f"总交易成本: {total_cost:.1f}%")
    
    # 2. 调整后收益（假设平均每月20笔交易）
    avg_trades_per_month = 90  # 基于回测结果
    monthly_cost = avg_trades_per_month * total_cost / 100
    
    print(f"\n平均每月交易次数: {avg_trades_per_month}")
    print(f"每月交易成本: {monthly_cost:.1f}%")
    
    # 3. 调整各轮收益
    adjusted_returns = []
    for ret in monthly_returns:
        adjusted = ret - monthly_cost
        adjusted_returns.append(max(0, adjusted))  # 不允许负收益
    
    print(f"\n调整后月收益:")
    for i, adj_ret in enumerate(adjusted_returns, 1):
        original = monthly_returns[i-1]
        print(f"第{i}轮: {original:.1f}% → {adj_ret:.1f}% (扣除成本)")
    
    # 4. 保守预估
    print("\n" + "="*50)
    print("保守预估分析:")
    print("="*50)
    
    avg_adjusted = np.mean(adjusted_returns)
    print(f"平均调整后月收益: {avg_adjusted:.1f}%")
    
    # 考虑效果递减趋势
    declining_factor = 0.7  # 假设效果逐步递减30%
    conservative_monthly = avg_adjusted * declining_factor
    
    print(f"考虑递减趋势后: {conservative_monthly:.1f}%")
    
    # 进一步保守化
    final_conservative = min(conservative_monthly, 15)  # 限制最高15%月收益
    print(f"最终保守预估: {final_conservative:.1f}%月收益")
    
    # 年化收益计算
    if final_conservative > 0:
        annual_return = (1 + final_conservative/100)**12 - 1
        print(f"对应年化收益: {annual_return*100:.0f}%")
    
    # 风险评估
    print("\n" + "="*50) 
    print("风险评估:")
    print("="*50)
    
    avg_drawdown = np.mean([abs(dd) for dd in max_drawdowns])
    print(f"平均最大回撤: {avg_drawdown:.1f}%")
    
    if final_conservative > 0:
        risk_reward = final_conservative / avg_drawdown
        print(f"风险收益比: {risk_reward:.1f}")
    
    # 实际建议
    print("\n" + "="*50)
    print("实际交易建议:")
    print("="*50)
    
    if final_conservative >= 10:
        print("✅ 策略显示正向预期，但需谨慎:")
        print("   - 建议小仓位测试")
        print("   - 严格执行止损")
        print("   - 监控策略衰减")
    elif final_conservative >= 5:
        print("⚠️ 策略有一定潜力，但风险较高:")
        print("   - 建议极小仓位测试")
        print("   - 随时准备停止")
    else:
        print("❌ 扣除现实成本后收益不足:")
        print("   - 不建议实盘交易")
        print("   - 需要进一步优化策略")
    
    return {
        'original_avg': np.mean(monthly_returns),
        'adjusted_avg': avg_adjusted,
        'final_conservative': final_conservative,
        'annual_estimate': annual_return*100 if final_conservative > 0 else 0,
        'avg_drawdown': avg_drawdown
    }

def run_realistic_projection():
    """包装函数，供main.py调用"""
    return realistic_returns_analysis()

if __name__ == "__main__":
    realistic_returns_analysis()