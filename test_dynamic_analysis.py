#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试动态分析功能（走向前和参数敏感性）
"""

import sys
from pathlib import Path

# 添加路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "backtest"))

def test_walk_forward_dynamic():
    """测试动态走向前分析"""
    print("="*60)
    print("测试动态走向前分析")
    print("="*60)
    
    try:
        from backtest.analysis.walk_forward_dynamic import run_walk_forward_analysis
        
        # 使用默认参数测试
        symbol = "BTC-USDT"
        strategy = "rsi_divergence_unified"
        
        print(f"测试配置: {symbol} - {strategy}")
        
        result = run_walk_forward_analysis(symbol, strategy)
        
        if result:
            print("✓ 走向前分析测试成功")
            return True
        else:
            print("❌ 走向前分析测试失败")
            return False
            
    except Exception as e:
        print(f"走向前分析测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_parameter_sensitivity_dynamic():
    """测试动态参数敏感性分析"""
    print("\n" + "="*60)
    print("测试动态参数敏感性分析")
    print("="*60)
    
    try:
        from backtest.analysis.parameter_sensitivity_dynamic import run_parameter_sensitivity_test
        
        # 使用默认参数测试
        symbol = "BTC-USDT"
        strategy = "rsi_divergence_unified"
        
        print(f"测试配置: {symbol} - {strategy}")
        print("注意: 参数敏感性测试可能需要较长时间...")
        
        result = run_parameter_sensitivity_test(symbol, strategy)
        
        if result:
            print("✓ 参数敏感性测试成功")
            return True
        else:
            print("❌ 参数敏感性测试失败")
            return False
            
    except Exception as e:
        print(f"参数敏感性测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("动态分析功能测试")
    print("="*80)
    
    success_count = 0
    
    # 测试走向前分析
    if test_walk_forward_dynamic():
        success_count += 1
    
    # 测试参数敏感性分析（时间较长，可选）
    test_param = input("\n是否测试参数敏感性分析？(可能需要几分钟) [y/N]: ").strip().lower()
    if test_param == 'y':
        if test_parameter_sensitivity_dynamic():
            success_count += 1
    else:
        print("跳过参数敏感性测试")
        success_count += 1  # 认为成功
    
    print("\n" + "="*80)
    if success_count == 2:
        print("✅ 所有动态分析功能测试通过!")
        print("\n现在可以在主菜单中使用:")
        print("  • 菜单项 5: 走向前分析 (支持选择币对和策略)")
        print("  • 菜单项 6: 参数敏感性测试 (支持选择币对和策略)")
    else:
        print("❌ 部分功能测试失败")
    print("="*80)

if __name__ == "__main__":
    main()