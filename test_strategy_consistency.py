#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试回测系统和实盘交易系统中策略的一致性
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
import pytest

# 设置编码
sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
sys.stderr.reconfigure(encoding='utf-8', errors='ignore')

# 添加路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "backtest"))
sys.path.insert(0, str(current_dir / "live_trading"))

def load_test_data():
    """加载测试数据"""
    data_path = current_dir / "crypto_data" / "BTC-USDT_5m.parquet"
    
    if not data_path.exists():
        print(f"测试数据不存在: {data_path}")
        return None
    
    df = pd.read_parquet(data_path)
    
    # 确保索引是时间格式
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    # 取最近1000个数据点进行测试
    df = df.tail(1000).copy()
    df.sort_index(inplace=True)
    
    print(f"测试数据加载完成: {len(df)} 条记录")
    print(f"数据时间范围: {df.index[0]} 至 {df.index[-1]}")
    
    return df


@pytest.fixture
def df():
    """Fixture providing test market data"""
    return load_test_data()

def test_unified_strategy_backtest(df):
    """测试统一策略在回测系统中的表现"""
    print("\n" + "="*60)
    print("测试统一策略 - 回测系统")
    print("="*60)
    
    try:
        from unified_strategies.rsi_divergence_unified import generate_signals
        
        # 测试两种风险管理方法
        risk_methods = ['fixed_percentage', 'recent_extreme']
        results = {}
        
        for risk_method in risk_methods:
            print(f"\n--- 风险方法: {risk_method} ---")
            
            signals = generate_signals(
                df=df,
                stop_loss_pct=0.015,
                take_profit_ratio=1.5,
                lookback=20,
                risk_method=risk_method
            )
            
            results[risk_method] = {
                'signal_count': len(signals),
                'signals': signals[:3]  # 保存前3个信号用于对比
            }
            
            print(f"生成信号数量: {len(signals)}")
            
            # 显示前3个信号的详细信息
            for i, signal in enumerate(signals[:3], 1):
                timestamp, entry_price, signal_type, stop_loss, take_profit, _ = signal
                print(f"信号 {i}: {signal_type} @ {entry_price:.2f}")
                print(f"  止损: {stop_loss:.2f}, 止盈: {take_profit:.2f}")
                if signal_type == 'buy':
                    risk_pct = (entry_price - stop_loss) / entry_price * 100
                    reward_pct = (take_profit - entry_price) / entry_price * 100
                else:
                    risk_pct = (stop_loss - entry_price) / entry_price * 100
                    reward_pct = (entry_price - take_profit) / entry_price * 100
                print(f"  风险: {risk_pct:.2f}%, 收益: {reward_pct:.2f}%, R:R = 1:{reward_pct/risk_pct:.1f}")
        
        return results
        
    except Exception as e:
        print(f"回测系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_unified_strategy_live_trading(df):
    """测试统一策略在实盘交易系统中的表现"""
    print("\n" + "="*60)
    print("测试统一策略 - 实盘交易系统")
    print("="*60)
    
    try:
        from live_trading.strategies.rsi_divergence_unified_adapter import RSIDivergenceUnifiedAdapter
        
        # 测试两种风险管理方法
        risk_methods = ['fixed_percentage', 'recent_extreme']
        results = {}
        
        for risk_method in risk_methods:
            print(f"\n--- 风险方法: {risk_method} ---")
            
            config = {
                'rsi_period': 14,
                'lookback_period': 20,
                'stop_loss_pct': 0.015,
                'take_profit_ratio': 1.5,
                'risk_method': risk_method,
                'min_signal_strength': 0.0,  # 设为0以便对比
                'supported_symbols': ['BTC-USDT-SWAP'],
                'timeframes': ['5m']
            }
            
            strategy = RSIDivergenceUnifiedAdapter(f"rsi_unified_{risk_method}", config)
            signals = strategy.analyze_market(df, "BTC-USDT-SWAP")
            
            results[risk_method] = {
                'signal_count': len(signals),
                'signals': signals[:3]  # 保存前3个信号用于对比
            }
            
            print(f"生成信号数量: {len(signals)}")
            
            # 显示前3个信号的详细信息
            for i, signal in enumerate(signals[:3], 1):
                print(f"信号 {i}: {signal.signal_type} @ {signal.entry_price:.2f}")
                print(f"  止损: {signal.stop_loss:.2f}, 止盈: {signal.take_profit:.2f}")
                if signal.signal_type == 'buy':
                    risk_pct = (signal.entry_price - signal.stop_loss) / signal.entry_price * 100
                    reward_pct = (signal.take_profit - signal.entry_price) / signal.entry_price * 100
                else:
                    risk_pct = (signal.stop_loss - signal.entry_price) / signal.entry_price * 100
                    reward_pct = (signal.entry_price - signal.take_profit) / signal.entry_price * 100
                print(f"  风险: {risk_pct:.2f}%, 收益: {reward_pct:.2f}%, R:R = 1:{reward_pct/risk_pct:.1f}")
                print(f"  强度: {signal.strength:.2f}, 原因: {signal.metadata.get('signal_reason', 'unknown')}")
        
        return results
        
    except Exception as e:
        print(f"实盘系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def compare_results(backtest_results, live_results):
    """对比两个系统的结果"""
    print("\n" + "="*60)
    print("系统一致性对比分析")
    print("="*60)
    
    if not backtest_results or not live_results:
        print("❌ 无法进行对比 - 某个系统测试失败")
        return
    
    for risk_method in ['fixed_percentage', 'recent_extreme']:
        print(f"\n--- 风险方法: {risk_method} ---")
        
        bt_result = backtest_results.get(risk_method, {})
        live_result = live_results.get(risk_method, {})
        
        bt_count = bt_result.get('signal_count', 0)
        live_count = live_result.get('signal_count', 0)
        
        print(f"信号数量对比:")
        print(f"  回测系统: {bt_count}")
        print(f"  实盘系统: {live_count}")
        
        if bt_count == live_count:
            print("  ✅ 信号数量一致")
        else:
            print("  ❌ 信号数量不一致")
        
        # 对比前3个信号的价格
        bt_signals = bt_result.get('signals', [])
        live_signals = live_result.get('signals', [])
        
        min_signals = min(len(bt_signals), len(live_signals), 3)
        price_match = True
        
        for i in range(min_signals):
            bt_signal = bt_signals[i]
            live_signal = live_signals[i]
            
            # 回测信号格式: (timestamp, entry_price, signal_type, stop_loss, take_profit, _)
            # 实盘信号格式: Signal对象
            bt_entry = bt_signal[1]
            bt_stop = bt_signal[3]
            bt_take = bt_signal[4]
            
            live_entry = live_signal.entry_price
            live_stop = live_signal.stop_loss
            live_take = live_signal.take_profit
            
            entry_diff = abs(bt_entry - live_entry) / bt_entry * 100
            stop_diff = abs(bt_stop - live_stop) / bt_stop * 100
            take_diff = abs(bt_take - live_take) / bt_take * 100
            
            print(f"\n信号 {i+1} 价格对比:")
            print(f"  入场价格: BT={bt_entry:.2f}, Live={live_entry:.2f}, 差异={entry_diff:.3f}%")
            print(f"  止损价格: BT={bt_stop:.2f}, Live={live_stop:.2f}, 差异={stop_diff:.3f}%")
            print(f"  止盈价格: BT={bt_take:.2f}, Live={live_take:.2f}, 差异={take_diff:.3f}%")
            
            if entry_diff > 0.001 or stop_diff > 0.1 or take_diff > 0.1:
                price_match = False
                print("  ❌ 价格存在差异")
            else:
                print("  ✅ 价格基本一致")
        
        if price_match and bt_count == live_count:
            print(f"\n✅ {risk_method} 方法：两系统完全一致")
        else:
            print(f"\n❌ {risk_method} 方法：两系统存在差异")

def main():
    """主函数"""
    print("策略一致性测试")
    print("="*60)
    print("测试统一RSI背离策略在回测和实盘系统中的一致性")
    
    # 加载测试数据
    df = load_test_data()
    if df is None:
        return
    
    # 测试回测系统
    backtest_results = test_unified_strategy_backtest(df)
    
    # 测试实盘交易系统
    live_results = test_unified_strategy_live_trading(df)
    
    # 对比结果
    compare_results(backtest_results, live_results)
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)

if __name__ == "__main__":
    main()