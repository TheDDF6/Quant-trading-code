#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""测试回测菜单功能"""

import sys
from pathlib import Path

# 添加路径
sys.path.append(str(Path(__file__).parent))

def test_backtest_functions():
    """测试各个回测功能"""
    
    print("测试回测系统各个功能...")
    
    # 测试1: 基础回测
    try:
        print("\n1. 测试基础回测功能...")
        from core.backtest import run_strategy_backtest
        print("✅ 基础回测导入成功")
        
    except Exception as e:
        print(f"❌ 基础回测导入失败: {e}")
    
    # 测试2: 走向前分析
    try:
        print("\n2. 测试走向前分析...")
        from tests.test_monthly_walk_forward import run_walk_forward_analysis
        print("✅ 走向前分析导入成功")
        
    except Exception as e:
        print(f"❌ 走向前分析导入失败: {e}")
    
    # 测试3: 参数敏感性测试
    try:
        print("\n3. 测试参数敏感性...")
        from tests.realistic_parameter_test import run_parameter_sensitivity_test
        print("✅ 参数敏感性测试导入成功")
        
    except Exception as e:
        print(f"❌ 参数敏感性测试导入失败: {e}")
    
    # 测试4: 现实收益预估
    try:
        print("\n4. 测试现实收益预估...")
        from analysis.realistic_projection import run_realistic_projection
        result = run_realistic_projection()
        print("✅ 现实收益预估运行成功")
        
    except Exception as e:
        print(f"❌ 现实收益预估失败: {e}")
    
    # 测试5: 实施计划
    try:
        print("\n5. 测试实施计划...")
        from analysis.implementation_plan import show_implementation_plan
        show_implementation_plan()
        print("✅ 实施计划显示成功")
        
    except Exception as e:
        print(f"❌ 实施计划失败: {e}")
    
    print("\n测试完成！")

if __name__ == "__main__":
    test_backtest_functions()