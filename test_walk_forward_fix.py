#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试修复后的走向前分析功能
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
        from backtest.tests.test_monthly_walk_forward import run_walk_forward_analysis
        
        print("开始运行走向前分析...")
        result = run_walk_forward_analysis()
        
        if result:
            print("✓ 走向前分析测试成功")
            return True
        else:
            print("❌ 走向前分析返回空结果")
            return False
            
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_walk_forward()
    if success:
        print("\n✅ 走向前分析功能修复成功")
    else:
        print("\n❌ 走向前分析功能仍有问题")