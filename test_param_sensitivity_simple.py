#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简单测试参数敏感性分析功能
"""

import sys
from pathlib import Path

# 添加路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "backtest"))

def test_parameter_sensitivity():
    """测试参数敏感性分析"""
    print("测试参数敏感性分析功能")
    print("="*50)
    print("注意：这是简化测试，会自动减少参数组合数量")
    
    try:
        # 先修改参数范围，减少测试时间
        from backtest.analysis.parameter_sensitivity_dynamic import run_parameter_sensitivity_test
        
        # 使用默认参数测试
        symbol = "BTC-USDT"
        strategy = "rsi_divergence_unified"
        
        print(f"测试配置: {symbol} - {strategy}")
        
        result = run_parameter_sensitivity_test(symbol, strategy)
        
        if result:
            print("\n参数敏感性分析测试成功!")
            return True
        else:
            print("\n参数敏感性分析测试失败")
            return False
            
    except Exception as e:
        print(f"\n参数敏感性分析测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_parameter_sensitivity()
    if success:
        print("\n参数敏感性分析功能已准备就绪，可以在主菜单中使用")
    else:
        print("\n参数敏感性分析功能需要进一步修复")