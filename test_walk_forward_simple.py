#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简单测试走向前分析功能
"""

import sys
from pathlib import Path

# 添加路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "backtest"))

def test_walk_forward():
    """测试走向前分析"""
    print("测试走向前分析功能")
    print("="*50)
    
    try:
        from backtest.analysis.walk_forward_dynamic import run_walk_forward_analysis
        
        # 使用默认参数测试
        symbol = "BTC-USDT"
        strategy = "rsi_divergence_unified"
        
        print(f"测试配置: {symbol} - {strategy}")
        
        result = run_walk_forward_analysis(symbol, strategy)
        
        if result:
            print("\n✅ 走向前分析测试成功!")
            return True
        else:
            print("\n❌ 走向前分析测试失败")
            return False
            
    except Exception as e:
        print(f"\n❌ 走向前分析测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_walk_forward()
    if success:
        print("\n走向前分析功能已准备就绪，可以在主菜单中使用")
    else:
        print("\n走向前分析功能需要进一步修复")