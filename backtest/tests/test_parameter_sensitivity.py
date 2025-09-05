# test_parameter_sensitivity.py - 参数敏感性测试脚本
from core.backtest import load_and_prepare_data
from parameter_sensitivity_test import parameter_sensitivity_test, analyze_parameter_sensitivity

def run_parameter_test():
    """运行参数敏感性测试"""
    print("开始参数敏感性测试...")
    
    # 1. 加载数据
    print("正在加载BTC-USDT数据...")
    df = load_and_prepare_data('BTC-USDT', '5m')
    
    if df is None:
        print("❌ 数据加载失败")
        return
    
    print(f"✅ 数据加载成功: {len(df)}条记录")
    
    # 2. 执行参数敏感性测试
    print("\n开始参数敏感性测试...")
    print("⚠️  注意: 这个测试会需要几分钟时间...")
    print("正在测试多种参数组合...")
    
    results = parameter_sensitivity_test(df, strategy_name='rsi_divergence')
    
    if not results:
        print("❌ 没有获得有效的测试结果")
        return
    
    # 3. 分析结果
    print("\n分析参数敏感性结果...")
    summary = analyze_parameter_sensitivity(results)
    
    # 4. 结论
    print(f"\n{'='*60}")
    print(f"参数敏感性分析结论")
    print(f"{'='*60}")
    
    profitable_ratio = summary['profitable_ratio']
    return_std = summary['return_std']
    
    if profitable_ratio < 0.3:
        print("🚨 结论: 策略严重过拟合!")
        print(f"   原因: 只有{profitable_ratio:.1%}的参数组合盈利")
        print("   建议: 策略可能只在特定参数下有效")
    elif return_std > 200:
        print("🚨 结论: 策略极不稳定!")
        print(f"   原因: 收益率标准差{return_std:.1f}%过高")
        print("   建议: 参数微调就可能导致巨大差异")
    elif profitable_ratio >= 0.7 and return_std <= 50:
        print("✅ 结论: 策略相对稳健")
        print(f"   {profitable_ratio:.1%}的参数组合盈利，收益率相对稳定")
        print("   建议: 可以考虑实盘测试")
    else:
        print("⚠️  结论: 策略稳健性中等")
        print("   建议: 需要进一步优化或更谨慎的参数选择")
    
    return summary

if __name__ == "__main__":
    run_parameter_test()