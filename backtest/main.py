# main.py - RSI背离策略回测系统主入口
"""
RSI背离策略回测系统
===================

基于技术分析的RSI背离策略回测和验证系统

主要功能：
1. 策略回测 - 理想化动态风险回测
2. 走向前分析 - 时间序列验证，避免过拟合
3. 参数敏感性测试 - 验证策略稳健性
4. 现实收益预估 - 考虑交易成本的实际收益
5. 实施计划 - 策略部署指导

使用方法：
python main.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 添加路径以便导入模块
sys.path.append(str(Path(__file__).parent))

def show_menu():
    """显示主菜单"""
    print("\n" + "="*80)
    print("多币对多策略回测系统")
    print("="*80)
    print("回测分析:")
    print("  1. 灵活回测 - 自选币对和策略")
    print("  2. 多币对回测 - 批量测试多个交易对")
    print("  3. 策略对比 - 同币对不同策略对比")
    print("  4. 查看可用资源 - 显示支持的币对和策略")
    print("")
    print("高级分析:")
    print("  5. 走向前分析 - 验证策略时间稳定性")
    print("  6. 参数敏感性测试 - 测试参数稳健性")
    print("  7. 现实收益预估 - 考虑交易成本的真实预期")
    print("")
    print("其他:")
    print("  8. 查看实施计划 - 策略部署指导")
    print("  9. 查看系统文档")
    print("  0. 退出")
    print("="*80)


def run_walk_forward():
    """运行走向前分析"""
    print("\n走向前分析 - 验证策略时间稳定性")
    print("="*60)
    print("用途：验证策略在不同时间段的表现，避免过拟合")
    
    try:
        from core.backtest_manager import BacktestManager
        
        manager = BacktestManager()
        
        # 选择交易对
        symbols = manager.get_available_symbols()
        print("可用交易对:")
        for i, symbol in enumerate(symbols, 1):
            print(f"  {i}. {symbol}")
        
        try:
            symbol_choice = input(f"\n选择交易对 (1-{len(symbols)}, 默认1): ").strip() or "1"
            symbol_idx = int(symbol_choice) - 1
            if 0 <= symbol_idx < len(symbols):
                selected_symbol = symbols[symbol_idx]
            else:
                selected_symbol = symbols[0] if symbols else "BTC-USDT"
        except ValueError:
            selected_symbol = symbols[0] if symbols else "BTC-USDT"
        
        # 选择策略
        strategies = manager.get_available_strategies()
        print(f"\n可用策略:")
        for i, (strategy_id, strategy_info) in enumerate(strategies.items(), 1):
            print(f"  {i}. {strategy_info['name']} ({strategy_id})")
        
        try:
            strategy_choice = input(f"选择策略 (1-{len(strategies)}, 默认1): ").strip() or "1"
            strategy_keys = list(strategies.keys())
            strategy_idx = int(strategy_choice) - 1
            if 0 <= strategy_idx < len(strategy_keys):
                selected_strategy = strategy_keys[strategy_idx]
            else:
                selected_strategy = strategy_keys[0]
        except ValueError:
            selected_strategy = list(strategies.keys())[0]
        
        # 选择时间框架
        print("\n可用时间框架:")
        timeframes = ['5m', '15m', '1h', '4h', '1d']
        timeframe_names = {
            '5m': '5分钟',
            '15m': '15分钟', 
            '1h': '1小时',
            '4h': '4小时',
            '1d': '1日'
        }
        for i, tf in enumerate(timeframes, 1):
            print(f"  {i}. {timeframe_names[tf]} ({tf})")
        
        try:
            timeframe_choice = input(f"选择时间框架 (1-{len(timeframes)}, 默认1-5分钟): ").strip() or "1"
            timeframe_idx = int(timeframe_choice) - 1
            if 0 <= timeframe_idx < len(timeframes):
                selected_timeframe = timeframes[timeframe_idx]
            else:
                selected_timeframe = "5m"
        except ValueError:
            selected_timeframe = "5m"
        
        print(f"\n运行走向前分析: {selected_symbol} - {strategies[selected_strategy]['name']} ({timeframe_names[selected_timeframe]})")
        
        # 运行走向前分析
        from analysis.walk_forward_dynamic import run_walk_forward_analysis
        run_walk_forward_analysis(selected_symbol, selected_strategy, timeframe=selected_timeframe)
            
    except Exception as e:
        print(f"走向前分析失败: {e}")
        import traceback
        traceback.print_exc()

def run_parameter_test():
    """运行参数敏感性测试"""
    print("\n参数敏感性测试 - 验证策略稳健性")
    print("="*60)
    print("用途：测试参数变化对策略表现的影响，评估策略稳健性")
    print("意义：避免过拟合，确保策略不会因参数微调而大幅失效")
    
    try:
        from core.backtest_manager import BacktestManager
        
        manager = BacktestManager()
        
        # 选择交易对
        symbols = manager.get_available_symbols()
        print("\n可用交易对:")
        for i, symbol in enumerate(symbols, 1):
            print(f"  {i}. {symbol}")
        
        try:
            symbol_choice = input(f"\n选择交易对 (1-{len(symbols)}, 默认1): ").strip() or "1"
            symbol_idx = int(symbol_choice) - 1
            if 0 <= symbol_idx < len(symbols):
                selected_symbol = symbols[symbol_idx]
            else:
                selected_symbol = symbols[0] if symbols else "BTC-USDT"
        except ValueError:
            selected_symbol = symbols[0] if symbols else "BTC-USDT"
        
        # 选择策略
        strategies = manager.get_available_strategies()
        print(f"\n可用策略:")
        for i, (strategy_id, strategy_info) in enumerate(strategies.items(), 1):
            print(f"  {i}. {strategy_info['name']} ({strategy_id})")
        
        try:
            strategy_choice = input(f"选择策略 (1-{len(strategies)}, 默认1): ").strip() or "1"
            strategy_keys = list(strategies.keys())
            strategy_idx = int(strategy_choice) - 1
            if 0 <= strategy_idx < len(strategy_keys):
                selected_strategy = strategy_keys[strategy_idx]
            else:
                selected_strategy = strategy_keys[0]
        except ValueError:
            selected_strategy = list(strategies.keys())[0]
        
        # 选择时间框架
        print("\n可用时间框架:")
        timeframes = ['5m', '15m', '1h', '4h', '1d']
        timeframe_names = {
            '5m': '5分钟',
            '15m': '15分钟', 
            '1h': '1小时',
            '4h': '4小时',
            '1d': '1日'
        }
        for i, tf in enumerate(timeframes, 1):
            print(f"  {i}. {timeframe_names[tf]} ({tf})")
        
        try:
            timeframe_choice = input(f"选择时间框架 (1-{len(timeframes)}, 默认1-5分钟): ").strip() or "1"
            timeframe_idx = int(timeframe_choice) - 1
            if 0 <= timeframe_idx < len(timeframes):
                selected_timeframe = timeframes[timeframe_idx]
            else:
                selected_timeframe = "5m"
        except ValueError:
            selected_timeframe = "5m"
        
        # 选择测试模式
        print("\n选择参数敏感性测试模式:")
        print("  1. 快速模式 (6组合) - 测试最关键参数")
        print("  2. 平衡模式 (18组合) - 平衡效率和全面性") 
        print("  3. 优化模式 (8组合) - 无图表弹窗，有进度条")
        print("  4. 全面模式 (36组合) - 完整参数空间测试")
        
        try:
            mode_choice = input("请选择测试模式 (1-4, 默认3): ").strip() or "3"
            mode_idx = int(mode_choice)
            
            print(f"\n运行参数敏感性测试: {selected_symbol} - {strategies[selected_strategy]['name']} ({timeframe_names[selected_timeframe]})")
            
            if mode_idx == 1:
                # 快速模式
                from analysis.parameter_sensitivity_smart import run_parameter_sensitivity_test_smart
                run_parameter_sensitivity_test_smart(selected_symbol, selected_strategy, "fast", selected_timeframe)
            elif mode_idx == 2:
                # 平衡模式
                from analysis.parameter_sensitivity_smart import run_parameter_sensitivity_test_smart
                run_parameter_sensitivity_test_smart(selected_symbol, selected_strategy, "balanced", selected_timeframe)
            elif mode_idx == 4:
                # 全面模式
                from analysis.parameter_sensitivity_smart import run_parameter_sensitivity_test_smart
                run_parameter_sensitivity_test_smart(selected_symbol, selected_strategy, "comprehensive", selected_timeframe)
            else:
                # 默认优化模式（模式3）
                # 强制重新导入以确保使用最新版本
                import importlib
                import analysis.parameter_sensitivity_optimized
                import core.backtest_manager
                import core.backtest
                importlib.reload(core.backtest_manager)
                importlib.reload(core.backtest)
                importlib.reload(analysis.parameter_sensitivity_optimized)
                from analysis.parameter_sensitivity_optimized import run_parameter_sensitivity_test_optimized
                run_parameter_sensitivity_test_optimized(selected_symbol, selected_strategy, timeframe=selected_timeframe)
        except ValueError:
            # 默认优化模式
            # 强制重新导入以确保使用最新版本
            import importlib
            import analysis.parameter_sensitivity_optimized
            import core.backtest_manager
            import core.backtest
            importlib.reload(core.backtest_manager)
            importlib.reload(core.backtest)
            importlib.reload(analysis.parameter_sensitivity_optimized)
            from analysis.parameter_sensitivity_optimized import run_parameter_sensitivity_test_optimized
            run_parameter_sensitivity_test_optimized(selected_symbol, selected_strategy, timeframe=selected_timeframe)
            
    except Exception as e:
        print(f"参数敏感性测试失败: {e}")
        import traceback
        traceback.print_exc()

def run_projection():
    """运行现实收益预估"""
    print("\n现实收益预估 - 基于实际交易成本的保守预估")
    print("="*60)
    
    try:
        from core.backtest_manager import BacktestManager
        
        manager = BacktestManager()
        
        # 选择交易对
        symbols = manager.get_available_symbols()
        print("可用交易对:")
        for i, symbol in enumerate(symbols, 1):
            print(f"  {i}. {symbol}")
        
        try:
            symbol_choice = input(f"\n选择交易对 (1-{len(symbols)}, 默认1): ").strip() or "1"
            symbol_idx = int(symbol_choice) - 1
            if 0 <= symbol_idx < len(symbols):
                selected_symbol = symbols[symbol_idx]
            else:
                selected_symbol = symbols[0] if symbols else "BTC-USDT"
        except ValueError:
            selected_symbol = symbols[0] if symbols else "BTC-USDT"
        
        # 选择策略
        strategies = manager.get_available_strategies()
        print(f"\n可用策略:")
        for i, (strategy_id, strategy_info) in enumerate(strategies.items(), 1):
            print(f"  {i}. {strategy_info['name']} ({strategy_id})")
        
        try:
            strategy_choice = input(f"选择策略 (1-{len(strategies)}, 默认1): ").strip() or "1"
            strategy_keys = list(strategies.keys())
            strategy_idx = int(strategy_choice) - 1
            if 0 <= strategy_idx < len(strategy_keys):
                selected_strategy = strategy_keys[strategy_idx]
            else:
                selected_strategy = strategy_keys[0]
        except ValueError:
            selected_strategy = list(strategies.keys())[0]
        
        print(f"\n运行现实收益预估: {selected_symbol} - {strategies[selected_strategy]['name']}")
        
        # 运行回测获取基础数据
        result = manager.run_backtest(
            symbol=selected_symbol,
            strategy_name=selected_strategy,
            initial_capital=10000.0
        )
        
        if result:
            # 调用现实收益预估分析
            from analysis.realistic_projection_dynamic import run_realistic_analysis
            run_realistic_analysis(result, selected_symbol, selected_strategy)
        else:
            print("回测失败，无法进行现实收益预估")
            
    except Exception as e:
        print(f"现实收益预估失败: {e}")
        import traceback
        traceback.print_exc()

def show_implementation_plan():
    """显示实施计划"""
    print("\n显示策略实施计划...")
    
    try:
        from analysis.implementation_plan import show_implementation_plan as show_plan
        show_plan()
    except Exception as e:
        print(f"运行出错: {e}")
        import traceback
        traceback.print_exc()

def run_flexible_backtest():
    """运行灵活回测"""
    print("\n灵活回测 - 自选币对和策略")
    print("="*50)
    
    try:
        from core.backtest_manager import BacktestManager
        
        manager = BacktestManager()
        
        # 显示可用选项
        print("\n可用交易对:")
        symbols = manager.get_available_symbols()
        for i, symbol in enumerate(symbols, 1):
            print(f"  {i}. {symbol}")
        
        print("\n可用策略:")
        strategies = manager.get_available_strategies()
        for i, (strategy_id, strategy_info) in enumerate(strategies.items(), 1):
            print(f"  {i}. {strategy_info['name']} ({strategy_id})")
        
        print("\n可用时间框架:")
        timeframes = ['5m', '15m', '1h', '4h', '1d']
        timeframe_names = {
            '5m': '5分钟',
            '15m': '15分钟', 
            '1h': '1小时',
            '4h': '4小时',
            '1d': '1日'
        }
        for i, tf in enumerate(timeframes, 1):
            print(f"  {i}. {timeframe_names[tf]} ({tf})")
        
        # 用户输入
        try:
            symbol_choice = input(f"\n选择交易对 (1-{len(symbols)}): ").strip()
            symbol_idx = int(symbol_choice) - 1
            if 0 <= symbol_idx < len(symbols):
                selected_symbol = symbols[symbol_idx]
            else:
                print("无效选择，使用默认: BTC-USDT")
                selected_symbol = "BTC-USDT"
            
            strategy_choice = input(f"选择策略 (1-{len(strategies)}): ").strip()
            strategy_keys = list(strategies.keys())
            strategy_idx = int(strategy_choice) - 1
            if 0 <= strategy_idx < len(strategy_keys):
                selected_strategy = strategy_keys[strategy_idx]
            else:
                print("无效选择，使用默认: rsi_divergence_unified")
                selected_strategy = "rsi_divergence_unified"
            
            timeframe_choice = input(f"选择时间框架 (1-{len(timeframes)}, 默认1-5分钟): ").strip() or "1"
            timeframe_idx = int(timeframe_choice) - 1
            if 0 <= timeframe_idx < len(timeframes):
                selected_timeframe = timeframes[timeframe_idx]
            else:
                selected_timeframe = "5m"
            
            print(f"\n开始回测: {selected_symbol} | {strategies[selected_strategy]['name']} | {timeframe_names[selected_timeframe]}")
            
            # 运行回测
            result = manager.run_backtest(
                symbol=selected_symbol,
                strategy_name=selected_strategy,
                timeframe=selected_timeframe
            )
            
            if result:
                print(f"\n回测完成! 最终收益率: {result['total_return_pct']:.2f}%")
            
        except ValueError:
            print("输入无效，使用默认参数运行...")
            result = manager.run_backtest("BTC-USDT", "rsi_divergence_unified")
            
    except Exception as e:
        print(f"灵活回测失败: {e}")
        import traceback
        traceback.print_exc()

def run_multi_symbol_backtest():
    """运行多币对回测"""
    print("\n多币对回测 - 批量测试")
    print("="*50)
    
    try:
        from core.backtest_manager import BacktestManager
        
        manager = BacktestManager()
        symbols = manager.get_available_symbols()
        
        print(f"发现 {len(symbols)} 个交易对:")
        for symbol in symbols:
            print(f"  - {symbol}")
        
        # 选择策略
        strategies = manager.get_available_strategies()
        print("\n可用策略:")
        for i, (strategy_id, strategy_info) in enumerate(strategies.items(), 1):
            print(f"  {i}. {strategy_info['name']} ({strategy_id})")
        
        print("\n可用时间框架:")
        timeframes = ['5m', '15m', '1h', '4h', '1d']
        timeframe_names = {
            '5m': '5分钟',
            '15m': '15分钟', 
            '1h': '1小时',
            '4h': '4小时',
            '1d': '1日'
        }
        for i, tf in enumerate(timeframes, 1):
            print(f"  {i}. {timeframe_names[tf]} ({tf})")
        
        try:
            strategy_choice = input(f"\n选择策略 (1-{len(strategies)}, 默认1): ").strip() or "1"
            strategy_idx = int(strategy_choice) - 1
            strategy_keys = list(strategies.keys())
            if 0 <= strategy_idx < len(strategy_keys):
                selected_strategy = strategy_keys[strategy_idx]
            else:
                selected_strategy = strategy_keys[0]
            
            timeframe_choice = input(f"选择时间框架 (1-{len(timeframes)}, 默认1-5分钟): ").strip() or "1"
            timeframe_idx = int(timeframe_choice) - 1
            if 0 <= timeframe_idx < len(timeframes):
                selected_timeframe = timeframes[timeframe_idx]
            else:
                selected_timeframe = "5m"
            
            print(f"使用策略: {strategies[selected_strategy]['name']}")
            print(f"时间框架: {timeframe_names[selected_timeframe]}")
            
            # 运行多币对回测
            results = manager.run_multi_symbol_backtest(
                symbols=symbols,
                strategy_name=selected_strategy,
                timeframe=selected_timeframe
            )
            
            # 保存结果
            filename = f"multi_symbol_{selected_strategy}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            manager.save_results(results, filename)
            
        except ValueError:
            print("输入无效，使用默认策略")
            
    except Exception as e:
        print(f"多币对回测失败: {e}")
        import traceback
        traceback.print_exc()

def run_strategy_comparison():
    """运行策略对比"""
    print("\n策略对比 - 同币对不同策略")
    print("="*50)
    
    try:
        from core.backtest_manager import BacktestManager
        
        manager = BacktestManager()
        
        # 选择交易对
        symbols = manager.get_available_symbols()
        print("可用交易对:")
        for i, symbol in enumerate(symbols, 1):
            print(f"  {i}. {symbol}")
        
        try:
            symbol_choice = input(f"\n选择交易对 (1-{len(symbols)}, 默认1): ").strip() or "1"
            symbol_idx = int(symbol_choice) - 1
            if 0 <= symbol_idx < len(symbols):
                selected_symbol = symbols[symbol_idx]
            else:
                selected_symbol = symbols[0] if symbols else "BTC-USDT"
            
            # 选择时间框架
            print("\n可用时间框架:")
            timeframes = ['5m', '15m', '1h', '4h', '1d']
            timeframe_names = {
                '5m': '5分钟',
                '15m': '15分钟', 
                '1h': '1小时',
                '4h': '4小时',
                '1d': '1日'
            }
            for i, tf in enumerate(timeframes, 1):
                print(f"  {i}. {timeframe_names[tf]} ({tf})")
            
            timeframe_choice = input(f"选择时间框架 (1-{len(timeframes)}, 默认1-5分钟): ").strip() or "1"
            timeframe_idx = int(timeframe_choice) - 1
            if 0 <= timeframe_idx < len(timeframes):
                selected_timeframe = timeframes[timeframe_idx]
            else:
                selected_timeframe = "5m"
            
            # 选择策略
            strategies = manager.get_available_strategies()
            strategy_keys = list(strategies.keys())
            print(f"\n将使用所有可用策略对比 {selected_symbol} ({timeframe_names[selected_timeframe]}):")
            for strategy_id, strategy_info in strategies.items():
                print(f"  - {strategy_info['name']}")
            
            # 运行对比
            results = manager.compare_strategies(
                symbol=selected_symbol,
                strategy_names=strategy_keys,
                timeframe=selected_timeframe
            )
            
            # 保存结果
            filename = f"strategy_comparison_{selected_symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            manager.save_results({'results': results}, filename)
            
        except ValueError:
            print("输入无效，使用默认参数")
            
    except Exception as e:
        print(f"策略对比失败: {e}")
        import traceback
        traceback.print_exc()

def show_available_resources():
    """显示可用资源"""
    print("\n可用资源 - 支持的币对和策略")
    print("="*60)
    
    try:
        from core.backtest_manager import BacktestManager
        
        manager = BacktestManager()
        
        # 显示交易对
        symbols = manager.get_available_symbols()
        print(f"\n可用交易对 ({len(symbols)}个):")
        print("="*40)
        
        for symbol in symbols:
            info = manager.get_symbol_info(symbol)
            if info:
                print(f"  {symbol:15} | {info['data_points']:6,} 数据点 | "
                      f"{info['start_date'].strftime('%Y-%m-%d')} 至 "
                      f"{info['end_date'].strftime('%Y-%m-%d')} | "
                      f"{info['file_size']:.1f}MB")
            else:
                print(f"  {symbol:15} | 数据读取失败")
        
        # 显示策略
        strategies = manager.get_available_strategies()
        print(f"\n可用策略 ({len(strategies)}个):")
        print("="*40)
        
        for strategy_id, strategy_info in strategies.items():
            risk_methods = ", ".join(strategy_info['risk_methods'])
            print(f"  {strategy_info['name']:25} | 类型: {strategy_info['class']:12} | "
                  f"风险方法: {risk_methods}")
            
            # 显示默认参数
            if strategy_info['default_params']:
                params_str = ", ".join([f"{k}={v}" for k, v in strategy_info['default_params'].items()][:3])
                print(f"    {'':27}   默认参数: {params_str}")
        
        print(f"\n使用提示:")
        print(f"  - 选择菜单项 1 进行灵活回测")
        print(f"  - 选择菜单项 2 进行多币对批量测试")
        print(f"  - 选择菜单项 3 进行策略对比")
        
    except Exception as e:
        print(f"显示资源信息失败: {e}")
        import traceback
        traceback.print_exc()

def show_documentation():
    """显示系统文档"""
    print("\n" + "="*60)
    print("系统文档")
    print("="*60)
    
    print("\n目录结构:")
    print("├── main.py                    # 主入口文件")
    print("├── core/                      # 核心模块")
    print("│   ├── backtest.py           # 主回测引擎")
    print("│   └── time_series_validation.py # 走向前分析")
    print("├── strategies/                # 交易策略")
    print("│   ├── ma_crossover.py       # 移动平均策略")
    print("│   ├── rsi_divergence_unified_adapter.py # RSI背离适配器")
    print("│   ├── experimental/")
    print("│   │   ├── rsi_simple.py            # 简化RSI背离策略")
    print("│   │   └── rsi_trend_divergence.py # RSI趋势背离策略")
    print("│   └── legacy/")
    print("│       └── rsi_divergence.py       # RSI背离策略(旧版)")
    print("├── tests/                     # 测试模块")
    print("│   ├── test_monthly_walk_forward.py # 月度走向前测试")
    print("│   ├── realistic_parameter_test.py  # 现实参数测试")
    print("│   └── test_parameter_sensitivity.py # 参数敏感性测试")
    print("├── analysis/                  # 分析工具")
    print("│   ├── realistic_projection.py # 现实收益预估")
    print("│   └── implementation_plan.py # 实施计划")
    print("├── utils/                     # 工具模块")
    print("│   └── strategy_validator.py # 策略验证工具")
    print("└── archive/                   # 归档文件")
    
    print("\n推荐使用流程:")
    print("1. 先运行'走向前分析'了解策略真实表现")
    print("2. 运行'现实收益预估'获得保守预期")
    print("3. 查看'实施计划'了解部署指导")
    print("4. 可选：运行'参数敏感性测试'验证稳健性")
    
    print("\n重要说明:")
    print("- 所有回测结果都是基于历史数据的理想化测试")
    print("- 实际交易中会有手续费、滑点等额外成本")
    print("- 策略存在失效风险，需要持续监控和调整")
    print("- 建议从模拟交易开始验证策略有效性")

def main():
    """主函数"""
    
    # 确保工作目录正确设置
    import os
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    print(f"设置工作目录为: {script_dir}")
    
    while True:
        show_menu()
        
        try:
            choice = input("\n请选择操作 (0-9): ").strip()
            
            if choice == '0':
                print("感谢使用！记住：谨慎交易，风险自负。")
                break
            elif choice == '1':
                run_flexible_backtest()
            elif choice == '2':
                run_multi_symbol_backtest()
            elif choice == '3':
                run_strategy_comparison()
            elif choice == '4':
                show_available_resources()
            elif choice == '5':
                run_walk_forward()
            elif choice == '6':
                run_parameter_test()
            elif choice == '7':
                run_projection()
            elif choice == '8':
                show_implementation_plan()
            elif choice == '9':
                show_documentation()
            else:
                print("无效选择，请输入0-9之间的数字。")
                
        except KeyboardInterrupt:
            print("\n\n操作已取消。")
            break
        except Exception as e:
            print(f"发生错误: {e}")
        
        input("\n按Enter继续...")

if __name__ == "__main__":
    main()