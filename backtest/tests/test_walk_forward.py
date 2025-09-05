# test_walk_forward.py - 走向前分析测试脚本
from core.backtest import load_and_prepare_data
from core.time_series_validation import (
    walk_forward_analysis,
    analyze_walk_forward_results,
)

def run_walk_forward_test():
    """运行走向前分析测试"""
    print("开始走向前分析测试...")
    
    # 1. 加载数据
    print("正在加载BTC-USDT数据...")
    df = load_and_prepare_data('BTC-USDT', '5m')
    
    if df is None:
        print("❌ 数据加载失败")
        return
    
    print(f"✅ 数据加载成功: {len(df)}条记录")
    print(f"时间范围: {df.index[0]} 至 {df.index[-1]}")
    
    # 2. 执行走向前分析
    print("\n开始走向前分析...")
    print("设置: 训练期6个月，测试期1个月")
    
    results = walk_forward_analysis(
        df=df, 
        strategy_name='rsi_divergence',
        initial_capital=10000,
        train_months=6,  # 训练期6个月
        test_months=1,   # 测试期1个月
        min_trades=5     # 最少交易数
    )
    
    if not results:
        print("❌ 没有获得有效的测试结果")
        return
    
    # 3. 分析结果
    print("\n分析走向前测试结果...")
    summary = analyze_walk_forward_results(results)
    
    # 4. 结论
    print(f"\n{'='*60}")
    print(f"走向前分析结论")
    print(f"{'='*60}")
    
    if summary['overfitting_risk'] == 'high':
        print("🚨 结论: 策略存在严重过拟合风险!")
        print("   原因: 在未见过的数据上表现不稳定")
        print("   建议: 重新设计策略或调整参数")
    else:
        print("✅ 结论: 策略相对稳健")
        print("   但仍建议进一步测试参数敏感性")
    
    return summary

if __name__ == "__main__":
    run_walk_forward_test()
