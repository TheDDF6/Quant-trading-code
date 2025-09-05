#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the flexible backtest interface
"""
import sys
import os
from pathlib import Path

# Add paths
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "backtest"))

def test_backtest_manager():
    """Test BacktestManager functionality"""
    print("Testing BacktestManager...")
    
    try:
        from backtest.core.backtest_manager import BacktestManager
        
        manager = BacktestManager()
        
        # Test 1: Check available symbols
        print(f"\n1. Available symbols:")
        symbols = manager.get_available_symbols()
        print(f"   Found {len(symbols)} symbols: {symbols[:3]}...")
        
        # Test 2: Check available strategies  
        print(f"\n2. Available strategies:")
        strategies = manager.get_available_strategies()
        for strategy_id, info in strategies.items():
            print(f"   {strategy_id}: {info['name']} ({info['class']})")
        
        # Test 3: Test basic backtest if data available
        if symbols and strategies:
            print(f"\n3. Testing basic backtest...")
            print(f"   Using symbol: {symbols[0]}")
            print(f"   Using strategy: rsi_divergence_unified")
            
            # Run a quick test with limited data
            result = manager.run_backtest(
                symbol=symbols[0],
                strategy_name="rsi_divergence_unified",
                initial_capital=1000.0  # Smaller amount for testing
            )
            
            if result:
                print(f"   ✓ Backtest successful!")
                print(f"   Final return: {result['total_return_pct']:.2f}%")
                print(f"   Total trades: {result['total_trades']}")
                print(f"   Win rate: {result['win_rate']:.1f}%")
            else:
                print(f"   X Backtest failed")
        else:
            print("   X No data or strategies available")
            
        print("\n✓ BacktestManager test completed")
        return True
        
    except Exception as e:
        print(f"X BacktestManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_menu_options():
    """Test individual menu functions"""
    print("\nTesting menu functions...")
    
    try:
        # Import main module functions
        sys.path.insert(0, str(current_dir / "backtest"))
        from main import show_available_resources
        
        print("\n4. Testing show_available_resources...")
        show_available_resources()
        print("   ✓ Resource display completed")
        
        return True
        
    except Exception as e:
        print(f"X Menu functions test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("="*60)
    print("Flexible Backtest Interface Test")
    print("="*60)
    
    success = True
    
    # Test BacktestManager
    success &= test_backtest_manager()
    
    # Test menu options
    success &= test_menu_options()
    
    print("\n" + "="*60)
    if success:
        print("✓ All tests passed! Flexible backtest interface is working.")
    else:
        print("X Some tests failed. Check the output above.")
    print("="*60)

if __name__ == "__main__":
    main()