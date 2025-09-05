#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试改进后的现实收益预估功能
"""

import sys
from pathlib import Path

# 添加路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "backtest"))

def test_realistic_projection():
    """测试现实收益预估"""
    print("测试现实收益预估功能")
    print("="*50)
    
    try:
        from backtest.core.backtest_manager import BacktestManager
        
        manager = BacktestManager()
        
        # 获取可用资源
        symbols = manager.get_available_symbols()
        strategies = manager.get_available_strategies()
        
        print(f"可用交易对: {symbols}")
        print(f"可用策略: {list(strategies.keys())}")
        
        if symbols and strategies:
            # 使用默认选项进行测试
            symbol = symbols[0]  # 第一个可用交易对
            strategy = "rsi_divergence_unified"  # 统一RSI策略
            
            print(f"\n使用 {symbol} 和 {strategy} 进行测试...")
            
            # 运行回测
            result = manager.run_backtest(
                symbol=symbol,
                strategy_name=strategy,
                initial_capital=10000.0
            )
            
            if result:
                print(f"\n回测成功，开始现实收益预估...")
                
                # 导入并运行现实收益预估
                from backtest.analysis.realistic_projection_dynamic import run_realistic_analysis
                run_realistic_analysis(result, symbol, strategy)
                
                print(f"\n✓ 现实收益预估测试完成")
                return True
            else:
                print("❌ 回测失败")
                return False
        else:
            print("❌ 没有可用的交易对或策略")
            return False
            
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_realistic_projection()
    if success:
        print("\n✅ 现实收益预估功能测试通过")
    else:
        print("\n❌ 现实收益预估功能测试失败")