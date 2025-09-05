#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
回测管理器 - 支持多币对和多策略的灵活回测系统
"""

import sys
import os
from pathlib import Path
import importlib
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json

# 添加统一策略模块路径
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from backtest.core.backtest import load_and_prepare_data, ideal_dynamic_backtest, plot_ideal_results, analyze_strategy_reasonableness

class BacktestManager:
    """回测管理器 - 支持多币对和多策略"""
    
    def __init__(self):
        self.data_dir = Path(r"D:\VSC\crypto_data")
        self.available_symbols = self._discover_available_symbols()
        self.available_strategies = self._discover_available_strategies()
        
    def _discover_available_symbols(self) -> List[str]:
        """发现可用的交易对数据"""
        symbols = []
        if not self.data_dir.exists():
            print(f"数据目录不存在: {self.data_dir}")
            return symbols
        
        for file in self.data_dir.glob("*_5m.parquet"):
            symbol_name = file.stem.replace("_5m", "").replace("-", "-")
            symbols.append(symbol_name)
        
        return sorted(symbols)
    
    def _discover_available_strategies(self) -> Dict[str, Dict]:
        """发现可用的策略"""
        strategies = {}
        
        # 统一策略
        strategies['rsi_divergence_unified'] = {
            'name': 'RSI背离策略(统一)',
            'class': 'unified',
            'risk_methods': ['fixed_percentage', 'recent_extreme'],
            'default_params': {
                'rsi_period': 14,
                'lookback_period': 20,
                'stop_loss_pct': 0.015,
                'take_profit_ratio': 1.5,
                'risk_method': 'fixed_percentage'
            }
        }
        
        # 添加波动率突破策略
        strategies['volatility_breakout_unified'] = {
            'name': '波动率突破策略',
            'class': 'unified',
            'risk_methods': ['fixed_percentage', 'recent_extreme'],
            'default_params': {
                'bb_period': 24,        # 针对5分钟数据优化
                'bb_std': 1.8,          # 稍微降低标准差
                'bb_threshold': 0.08,   # 放宽到8%，更现实
                'atr_period': 12,       # 1小时ATR
                'stop_loss_mult': 1.5,
                'trailing_mult': 2.0,
                'volume_mult': 1.5,
                'enable_volume_filter': False,
                'min_signal_strength': 0.0005,  # 降低到0.05%
                'risk_method': 'fixed_percentage'
            }
        }
        
        # 传统策略
        strategy_dir = Path(__file__).parent.parent / "strategies"
        if strategy_dir.exists():
            for file in strategy_dir.glob("*.py"):
                if file.stem.startswith("_") or file.stem in ['__init__']:
                    continue
                
                strategy_name = file.stem
                if strategy_name not in strategies:
                    strategies[strategy_name] = {
                        'name': strategy_name.replace('_', ' ').title(),
                        'class': 'traditional',
                        'risk_methods': ['traditional'],
                        'default_params': {}
                    }
        
        return strategies
    
    def get_available_symbols(self) -> List[str]:
        """获取可用的交易对列表"""
        return self.available_symbols
    
    def get_available_strategies(self) -> Dict[str, Dict]:
        """获取可用的策略字典"""
        return self.available_strategies
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """获取交易对信息"""
        data_file = self.data_dir / f"{symbol}_5m.parquet"
        if not data_file.exists():
            return None
        
        try:
            df = pd.read_parquet(data_file)
            return {
                'symbol': symbol,
                'data_points': len(df),
                'start_date': df.index[0],
                'end_date': df.index[-1],
                'file_size': data_file.stat().st_size / (1024*1024),  # MB
                'timeframes': ['5m', '15m', '1h', '4h', '1d']  # 支持重采样
            }
        except Exception as e:
            print(f"读取{symbol}数据失败: {e}")
            return None
    
    def run_backtest(self, 
                     symbol: str,
                     strategy_name: str,
                     timeframe: str = '5m',
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     initial_capital: float = 10000.0,
                     risk_per_trade: float = 0.015,
                     max_leverage: float = 100,
                     strategy_params: Optional[Dict] = None) -> Optional[Dict]:
        """
        运行单个回测
        
        Args:
            symbol: 交易对
            strategy_name: 策略名称
            timeframe: 时间框架
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金
            risk_per_trade: 单笔风险
            max_leverage: 最大杠杆
            strategy_params: 策略参数
            
        Returns:
            Dict: 回测结果
        """
        print(f"\n{'='*60}")
        print(f"开始回测: {symbol} - {strategy_name}")
        print(f"时间框架: {timeframe}, 初始资金: ${initial_capital:,.2f}")
        print(f"{'='*60}")
        
        # 加载数据
        df = load_and_prepare_data(symbol, timeframe, start_date, end_date)
        if df is None:
            print(f"无法加载{symbol}的数据")
            return None
        
        # 获取策略信息
        strategy_info = self.available_strategies.get(strategy_name)
        if not strategy_info:
            print(f"未知策略: {strategy_name}")
            return None
        
        # 合并参数
        params = strategy_info['default_params'].copy()
        if strategy_params:
            params.update(strategy_params)
        
        # 确保时间框架参数被传递
        params['timeframe'] = timeframe
        
        # 生成信号
        try:
            signals = self._generate_signals(strategy_name, strategy_info, df, params)
            if not signals:
                print("策略未生成任何信号")
                return None
        except Exception as e:
            print(f"信号生成失败: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        # 运行回测
        try:
            df_result, trades = ideal_dynamic_backtest(
                df, signals,
                initial_capital=initial_capital,
                risk_per_trade=risk_per_trade,
                max_leverage=max_leverage
            )
            
            # 分析结果
            plot_ideal_results(df_result, trades, symbol)
            analyze_strategy_reasonableness(df_result, trades, signals, symbol)
            
            # 返回结果摘要
            if trades:
                total_pnl = sum(trade['pnl'] for trade in trades)
                win_trades = [t for t in trades if t['pnl'] > 0]
                win_rate = len(win_trades) / len(trades) * 100
                
                result = {
                    'symbol': symbol,
                    'strategy': strategy_name,
                    'timeframe': timeframe,
                    'initial_capital': initial_capital,
                    'final_capital': initial_capital + total_pnl,
                    'total_return_pct': (total_pnl / initial_capital) * 100,
                    'total_trades': len(trades),
                    'win_trades': len(win_trades),
                    'win_rate': win_rate,
                    'total_signals': len(signals),
                    'signal_execution_rate': len(trades) / len(signals) * 100,
                    'params': params,
                    'trades': trades,
                    'df_result': df_result
                }
                
                return result
            else:
                return None
                
        except Exception as e:
            print(f"回测执行失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_signals(self, strategy_name: str, strategy_info: Dict, df: pd.DataFrame, params: Dict) -> List:
        """生成交易信号"""
        
        if strategy_info['class'] == 'unified':
            # 统一策略
            if strategy_name == 'rsi_divergence_unified':
                # RSI策略需要作为包导入以支持相对导入
                import sys
                from pathlib import Path
                project_root = Path(__file__).parent.parent.parent
                
                # 将项目根目录添加到路径
                if str(project_root) not in sys.path:
                    sys.path.insert(0, str(project_root))
                
                # 强制重新导入模块
                import importlib
                if 'unified_strategies.rsi_divergence_unified' in sys.modules:
                    importlib.reload(sys.modules['unified_strategies.rsi_divergence_unified'])
                if 'unified_strategies' in sys.modules:
                    importlib.reload(sys.modules['unified_strategies'])
                
                # 尝试导入
                try:
                    from unified_strategies.rsi_divergence_unified import generate_signals
                except ImportError:
                    # 备选方案：使用本地简化版本
                    print("使用本地RSI简化策略...")
                    try:
                        from strategies.experimental.rsi_simple import generate_signals
                    except ImportError as e:
                        print(f"本地简化策略导入失败: {e}")
                        return []
                return generate_signals(
                    df=df,
                    stop_loss_pct=params.get('stop_loss_pct', 0.015),
                    take_profit_ratio=params.get('take_profit_ratio', 1.5),
                    lookback=params.get('lookback_period', 20),
                    risk_method=params.get('risk_method', 'fixed_percentage'),
                    timeframe=params.get('timeframe', '5m'),  # 传递时间框架参数
                    rsi_period=params.get('rsi_period', 14),
                    min_divergence_distance=params.get('min_divergence_distance', 5),
                    peak_window=params.get('peak_window', 3)
                )
            elif strategy_name == 'volatility_breakout_unified':
                # 直接导入波动率突破策略模块
                import sys
                import importlib.util
                from pathlib import Path
                
                # 定位策略文件的绝对路径
                strategy_file = Path(__file__).parent.parent / "unified_strategies" / "volatility_breakout_unified.py"
                
                # 使用importlib直接加载模块
                spec = importlib.util.spec_from_file_location("volatility_breakout_unified", strategy_file)
                volatility_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(volatility_module)
                
                generate_signals = volatility_module.generate_signals
                return generate_signals(
                    df=df,
                    risk_pct=params.get('risk_pct', 0.02),
                    take_profit_ratio=params.get('take_profit_ratio', 2.0),
                    lookback_period=params.get('lookback_period', 20),
                    risk_method=params.get('risk_method', 'fixed_percentage'),
                    timeframe=params.get('timeframe', '5m'),  # 传递时间框架参数
                    bb_period=params.get('bb_period', 24),
                    bb_std=params.get('bb_std', 1.8),
                    bb_threshold=params.get('bb_threshold', 0.08),
                    atr_period=params.get('atr_period', 12),
                    stop_loss_mult=params.get('stop_loss_mult', 1.5),
                    trailing_mult=params.get('trailing_mult', 2.0),
                    volume_mult=params.get('volume_mult', 1.5),
                    enable_volume_filter=params.get('enable_volume_filter', False),
                    min_signal_strength=params.get('min_signal_strength', 0.0005)
                )
        else:
            # 传统策略
            try:
                strategy = importlib.import_module(f"strategies.{strategy_name}")
                if hasattr(strategy, 'generate_signals'):
                    return strategy.generate_signals(df, **params)
            except ImportError as e:
                print(f"无法加载策略 {strategy_name}: {e}")
        
        return []
    
    def run_multi_symbol_backtest(self,
                                  symbols: List[str],
                                  strategy_name: str,
                                  **kwargs) -> Dict[str, Any]:
        """
        运行多币对回测
        
        Args:
            symbols: 交易对列表
            strategy_name: 策略名称
            **kwargs: 其他回测参数
            
        Returns:
            Dict: 汇总结果
        """
        print(f"\n{'='*80}")
        print(f"多币对回测: {len(symbols)}个交易对 - {strategy_name}")
        print(f"{'='*80}")
        
        results = {}
        summary = {
            'total_symbols': len(symbols),
            'successful_backtests': 0,
            'failed_backtests': 0,
            'total_return_pct': 0,
            'avg_return_pct': 0,
            'total_trades': 0,
            'avg_win_rate': 0,
            'best_performer': None,
            'worst_performer': None
        }
        
        for symbol in symbols:
            print(f"\n处理 {symbol}...")
            result = self.run_backtest(symbol=symbol, strategy_name=strategy_name, **kwargs)
            
            if result:
                results[symbol] = result
                summary['successful_backtests'] += 1
                summary['total_return_pct'] += result['total_return_pct']
                summary['total_trades'] += result['total_trades']
                
                # 更新最佳和最差表现
                if (summary['best_performer'] is None or 
                    result['total_return_pct'] > results[summary['best_performer']]['total_return_pct']):
                    summary['best_performer'] = symbol
                    
                if (summary['worst_performer'] is None or 
                    result['total_return_pct'] < results[summary['worst_performer']]['total_return_pct']):
                    summary['worst_performer'] = symbol
            else:
                summary['failed_backtests'] += 1
                print(f"X {symbol} 回测失败")
        
        # 计算平均值
        if summary['successful_backtests'] > 0:
            summary['avg_return_pct'] = summary['total_return_pct'] / summary['successful_backtests']
            win_rates = [r['win_rate'] for r in results.values()]
            summary['avg_win_rate'] = sum(win_rates) / len(win_rates)
        
        # 打印汇总
        self._print_multi_symbol_summary(summary, results)
        
        return {
            'summary': summary,
            'results': results
        }
    
    def _print_multi_symbol_summary(self, summary: Dict, results: Dict):
        """打印多币对回测汇总"""
        print(f"\n{'='*80}")
        print(f"多币对回测汇总")
        print(f"{'='*80}")
        print(f"总交易对数: {summary['total_symbols']}")
        print(f"成功回测: {summary['successful_backtests']}")
        print(f"失败回测: {summary['failed_backtests']}")
        print(f"平均收益率: {summary['avg_return_pct']:.2f}%")
        print(f"平均胜率: {summary['avg_win_rate']:.1f}%")
        print(f"总交易数: {summary['total_trades']}")
        
        if summary['best_performer']:
            best = results[summary['best_performer']]
            print(f"\n最佳表现: {summary['best_performer']}")
            print(f"   收益率: {best['total_return_pct']:.2f}%")
            print(f"   胜率: {best['win_rate']:.1f}%")
            print(f"   交易数: {best['total_trades']}")
        
        if summary['worst_performer']:
            worst = results[summary['worst_performer']]
            print(f"\n最差表现: {summary['worst_performer']}")
            print(f"   收益率: {worst['total_return_pct']:.2f}%")
            print(f"   胜率: {worst['win_rate']:.1f}%")
            print(f"   交易数: {worst['total_trades']}")
        
        print(f"\n详细结果:")
        for symbol, result in results.items():
            print(f"  {symbol:15} | 收益: {result['total_return_pct']:8.2f}% | "
                  f"胜率: {result['win_rate']:5.1f}% | 交易: {result['total_trades']:4d}")
    
    def save_results(self, results: Dict, filename: str):
        """保存回测结果到文件"""
        output_dir = Path(__file__).parent.parent / "results"
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / f"{filename}.json"
        
        # 转换不能序列化的对象
        serializable_results = {}
        for key, value in results.items():
            if key == 'results':
                serializable_results[key] = {}
                for symbol, result in value.items():
                    # 移除不能序列化的DataFrame和复杂对象
                    clean_result = {k: v for k, v in result.items() 
                                   if k not in ['df_result', 'trades']}
                    clean_result['trade_count'] = len(result.get('trades', []))
                    serializable_results[key][symbol] = clean_result
            else:
                serializable_results[key] = value
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_results, f, indent=2, ensure_ascii=False)
            print(f"结果已保存到: {output_file}")
        except Exception as e:
            print(f"保存结果失败: {e}")

    def compare_strategies(self,
                          symbol: str,
                          strategy_names: List[str],
                          **kwargs) -> Dict:
        """
        策略对比
        
        Args:
            symbol: 交易对
            strategy_names: 策略列表
            **kwargs: 其他回测参数
            
        Returns:
            Dict: 对比结果
        """
        print(f"\n{'='*80}")
        print(f"策略对比: {symbol} - {len(strategy_names)}个策略")
        print(f"{'='*80}")
        
        results = {}
        for strategy_name in strategy_names:
            print(f"\n测试策略: {strategy_name}")
            result = self.run_backtest(symbol=symbol, strategy_name=strategy_name, **kwargs)
            if result:
                results[strategy_name] = result
            else:
                print(f"X {strategy_name} 策略测试失败")
        
        # 打印对比结果
        if len(results) > 1:
            self._print_strategy_comparison(results)
        
        return results
    
    def _print_strategy_comparison(self, results: Dict):
        """打印策略对比结果"""
        print(f"\n{'='*80}")
        print(f"策略对比汇总")
        print(f"{'='*80}")
        
        print(f"{'策略名称':20} | {'收益率':>8} | {'胜率':>6} | {'交易数':>6} | {'信号数':>6}")
        print(f"{'-'*60}")
        
        for strategy_name, result in results.items():
            print(f"{strategy_name:20} | {result['total_return_pct']:7.2f}% | "
                  f"{result['win_rate']:5.1f}% | {result['total_trades']:6d} | "
                  f"{result['total_signals']:6d}")
        
        # 找出最佳策略
        best_strategy = max(results.keys(), 
                           key=lambda x: results[x]['total_return_pct'])
        print(f"\n最佳策略: {best_strategy} "
              f"(收益率: {results[best_strategy]['total_return_pct']:.2f}%)")

# 便捷函数
def quick_backtest(symbol: str = "BTC-USDT", 
                   strategy: str = "rsi_divergence_unified",
                   **kwargs):
    """快速回测函数"""
    manager = BacktestManager()
    return manager.run_backtest(symbol=symbol, strategy_name=strategy, **kwargs)