# test_monthly_walk_forward.py - 月度走向前分析
import sys
from pathlib import Path

# 添加parent目录到路径以便导入
sys.path.append(str(Path(__file__).parent.parent))

from core.backtest import load_and_prepare_data
from core.time_series_validation import walk_forward_analysis, analyze_walk_forward_results

def run_monthly_walk_forward():
    """运行月度走向前分析 - 更多轮数的测试"""
    print("开始月度走向前分析...")
    
    df = load_and_prepare_data('BTC-USDT', '5m')
    if df is None:
        return
    
    print(f"数据时间范围: {df.index[0]} 至 {df.index[-1]}")
    
    # 使用更短的训练期和测试期以获得更多轮测试
    results = walk_forward_analysis(
        df=df,
        strategy_name='rsi_divergence', 
        initial_capital=10000,
        train_months=3,  # 训练期3个月
        test_months=1,   # 测试期1个月
        min_trades=5
    )
    
    if results:
        summary = analyze_walk_forward_results(results)
        
        print(f"\n{'='*60}")
        print(f"月度走向前分析总结")
        print(f"{'='*60}")
        
        avg_monthly_return = summary['avg_return']
        consistency = summary['profit_consistency']
        
        # 计算更现实的年化收益预估
        if avg_monthly_return > 0:
            # 使用更保守的复利计算
            conservative_monthly = min(avg_monthly_return, 20)  # 限制月收益不超过20%
            conservative_annual = (1 + conservative_monthly/100)**12 - 1
            print(f"保守年化收益预估: {conservative_annual*100:.1f}%")
        
        if consistency >= 0.7:
            print("策略在多个时间段表现一致")
        else:
            print("警告: 策略表现不够一致，存在时间偏差")
        
        return summary
    else:
        print("错误: 无法获得足够的测试轮数")

def run_walk_forward_analysis():
    """包装函数，供main.py调用"""
    return run_monthly_walk_forward()

if __name__ == "__main__":
    run_monthly_walk_forward()