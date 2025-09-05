# strategy_configurator.py - 策略配置器
"""
策略配置器
提供交互式策略管理功能

主要功能:
1. 添加新策略实例
2. 删除现有策略
3. 修改策略配置
4. 策略模板管理
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from core.strategy_registry import strategy_registry
from config.multi_config_manager import MultiStrategyConfigManager, StrategyConfig

class StrategyConfigurator:
    """策略配置器"""
    
    def __init__(self, config_manager: MultiStrategyConfigManager):
        """
        初始化策略配置器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger("StrategyConfigurator")
    
    def show_available_strategies(self) -> Dict[str, Any]:
        """显示可用的策略类型"""
        available = strategy_registry.get_available_strategies()
        categories = strategy_registry.get_strategy_categories()
        
        print("\n📋 可用策略类型:")
        print("=" * 50)
        
        strategy_list = {}
        index = 1
        
        for category, strategies in categories.items():
            print(f"\n📂 {category}:")
            for strategy_type in strategies:
                info = strategy_registry.get_strategy_info(strategy_type)
                print(f"  {index}. {strategy_type}")
                print(f"     描述: {info.get('description', '无描述')}")
                print(f"     风险: {info.get('risk_level', '未知')}")
                strategy_list[str(index)] = strategy_type
                index += 1
        
        return strategy_list
    
    def show_current_strategies(self):
        """显示当前配置的策略"""
        strategies = self.config_manager.get_all_strategies_config()
        
        print("\n💼 当前配置的策略:")
        print("=" * 60)
        
        if not strategies:
            print("❌ 暂无配置的策略")
            return
        
        total_allocation = 0
        for i, (strategy_id, config) in enumerate(strategies.items(), 1):
            status = "🟢 启用" if config.active else "⚪ 禁用"
            allocation = config.allocation_ratio * 100
            total_allocation += allocation if config.active else 0
            
            print(f"{i}. {strategy_id} ({config.class_name})")
            print(f"   状态: {status}")
            print(f"   资金分配: {allocation:.1f}%")
            print(f"   支持品种: {config.config.get('supported_symbols', ['未设置'])}")
            print()
        
        print(f"总活跃资金分配: {total_allocation:.1f}%")
        remaining = 100 - total_allocation
        if remaining > 0:
            print(f"剩余可分配: {remaining:.1f}%")
        elif remaining < 0:
            print(f"⚠️  超额分配: {-remaining:.1f}%")
    
    def add_strategy_interactive(self) -> bool:
        """交互式添加策略"""
        print("\n🔧 添加新策略")
        print("=" * 30)
        
        # 1. 选择策略类型
        strategy_list = self.show_available_strategies()
        
        try:
            choice = input("\n请选择策略类型编号 (回车取消): ").strip()
            if not choice:
                print("❌ 操作已取消")
                return False
            
            if choice not in strategy_list:
                print("❌ 无效选择")
                return False
            
            strategy_type = strategy_list[choice]
            print(f"✅ 已选择: {strategy_type}")
            
        except KeyboardInterrupt:
            print("\n❌ 操作已取消")
            return False
        
        # 2. 输入策略ID
        while True:
            strategy_id = input("\n请输入策略实例ID (例如: rsi_btc_1): ").strip()
            if not strategy_id:
                print("❌ 策略ID不能为空")
                continue
            
            # 检查是否已存在
            if self.config_manager.get_strategy_config(strategy_id):
                print("❌ 策略ID已存在，请选择其他名称")
                continue
            
            break
        
        # 3. 配置基本参数
        print(f"\n⚙️  配置策略参数 ({strategy_type}):")
        
        # 获取默认配置
        default_config = strategy_registry.get_default_config(strategy_type)
        strategy_config = default_config.copy()
        
        # 资金分配
        while True:
            try:
                current_allocation = sum(
                    config.allocation_ratio 
                    for config in self.config_manager.get_active_strategies_config().values()
                )
                remaining = 1.0 - current_allocation
                
                print(f"当前剩余可分配资金: {remaining * 100:.1f}%")
                allocation_input = input(f"请输入资金分配比例 (0-{remaining * 100:.1f}%, 默认 20%): ").strip()
                
                if not allocation_input:
                    allocation_ratio = min(0.2, remaining)
                else:
                    allocation_pct = float(allocation_input.rstrip('%'))
                    allocation_ratio = allocation_pct / 100
                    
                    if allocation_ratio <= 0 or allocation_ratio > remaining:
                        print(f"❌ 分配比例应该在 0-{remaining * 100:.1f}% 范围内")
                        continue
                
                break
                
            except ValueError:
                print("❌ 请输入有效的数值")
        
        # 支持的交易对
        symbols_input = input(f"请输入支持的交易对 (用逗号分隔，默认: {default_config.get('supported_symbols', [])}): ").strip()
        if symbols_input:
            symbols = [s.strip().upper() for s in symbols_input.split(',')]
            strategy_config['supported_symbols'] = symbols
        
        # 4. 高级参数配置 (可选)
        advanced = input("\n是否配置高级参数? (y/N): ").lower() == 'y'
        
        if advanced:
            strategy_config = self._configure_advanced_parameters(strategy_type, strategy_config)
        
        # 5. 验证配置
        is_valid, errors = strategy_registry.validate_strategy_config(strategy_type, strategy_config)
        if not is_valid:
            print("\n❌ 配置验证失败:")
            for error in errors:
                print(f"  - {error}")
            
            retry = input("\n是否重新配置? (y/N): ").lower() == 'y'
            if retry:
                return self.add_strategy_interactive()
            else:
                return False
        
        # 6. 创建策略配置
        new_strategy_config = StrategyConfig(
            strategy_id=strategy_id,
            class_name=strategy_type,
            active=True,
            allocation_ratio=allocation_ratio,
            config=strategy_config
        )
        
        # 7. 预览配置
        print("\n📋 策略配置预览:")
        print("=" * 30)
        print(f"策略ID: {strategy_id}")
        print(f"策略类型: {strategy_type}")
        print(f"资金分配: {allocation_ratio * 100:.1f}%")
        print(f"支持品种: {strategy_config.get('supported_symbols', [])}")
        print(f"时间周期: {strategy_config.get('timeframes', [])}")
        print(f"风险比例: {strategy_config.get('risk_per_trade', 0) * 100:.1f}%")
        
        # 8. 确认添加
        confirm = input("\n确认添加此策略? (Y/n): ").lower()
        if confirm == 'n':
            print("❌ 操作已取消")
            return False
        
        # 9. 保存配置
        try:
            self.config_manager.add_strategy_config(new_strategy_config)
            self.config_manager.save_config()
            
            print(f"✅ 策略 '{strategy_id}' 已成功添加并保存")
            return True
            
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
            return False
    
    def _configure_advanced_parameters(self, strategy_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """配置高级参数"""
        print(f"\n🔧 高级参数配置 ({strategy_type}):")
        
        # 通用参数配置
        common_params = {
            'risk_per_trade': {
                'prompt': '单笔风险比例 (0.5-5.0%, 默认 {default}%)',
                'type': float,
                'range': (0.005, 0.05),
                'format': lambda x: f"{x * 100:.1f}%"
            },
            'stop_loss_pct': {
                'prompt': '止损比例 (0.5-10.0%, 默认 {default}%)',
                'type': float,
                'range': (0.005, 0.1),
                'format': lambda x: f"{x * 100:.1f}%"
            },
            'take_profit_ratio': {
                'prompt': '止盈倍数 (1.0-5.0倍, 默认 {default}倍)',
                'type': float,
                'range': (1.0, 5.0),
                'format': lambda x: f"{x:.1f}倍"
            }
        }
        
        # 策略特定参数
        if strategy_type == "RSIDivergenceV2":
            specific_params = {
                'rsi_period': {
                    'prompt': 'RSI周期 (5-50, 默认 {default})',
                    'type': int,
                    'range': (5, 50),
                    'format': lambda x: str(x)
                },
                'lookback': {
                    'prompt': '背离检测回看期 (10-50, 默认 {default})',
                    'type': int,
                    'range': (10, 50),
                    'format': lambda x: str(x)
                }
            }
        elif strategy_type == "MovingAverageCrossover":
            specific_params = {
                'fast_period': {
                    'prompt': '快线周期 (3-20, 默认 {default})',
                    'type': int,
                    'range': (3, 20),
                    'format': lambda x: str(x)
                },
                'slow_period': {
                    'prompt': '慢线周期 (10-100, 默认 {default})',
                    'type': int,
                    'range': (10, 100),
                    'format': lambda x: str(x)
                }
            }
        else:
            specific_params = {}
        
        # 合并参数
        all_params = {**common_params, **specific_params}
        
        for param_name, param_config in all_params.items():
            if param_name in config:
                current_value = config[param_name]
                formatted_value = param_config['format'](current_value)
                prompt = param_config['prompt'].format(default=formatted_value)
                
                try:
                    user_input = input(f"{prompt}: ").strip()
                    if user_input:
                        new_value = param_config['type'](user_input.rstrip('%倍'))
                        min_val, max_val = param_config['range']
                        
                        if min_val <= new_value <= max_val:
                            config[param_name] = new_value
                        else:
                            print(f"⚠️  参数超出范围，保持默认值")
                except ValueError:
                    print(f"⚠️  输入无效，保持默认值")
        
        return config
    
    def remove_strategy_interactive(self) -> bool:
        """交互式删除策略"""
        print("\n🗑️  删除策略")
        print("=" * 20)
        
        strategies = self.config_manager.get_all_strategies_config()
        if not strategies:
            print("❌ 暂无可删除的策略")
            return False
        
        # 显示策略列表
        strategy_list = {}
        print("\n当前策略:")
        for i, (strategy_id, config) in enumerate(strategies.items(), 1):
            status = "🟢 启用" if config.active else "⚪ 禁用"
            allocation = config.allocation_ratio * 100
            print(f"{i}. {strategy_id} ({config.class_name}) - {status} - {allocation:.1f}%")
            strategy_list[str(i)] = strategy_id
        
        try:
            choice = input("\n请选择要删除的策略编号 (回车取消): ").strip()
            if not choice:
                print("❌ 操作已取消")
                return False
            
            if choice not in strategy_list:
                print("❌ 无效选择")
                return False
            
            strategy_id = strategy_list[choice]
            strategy_config = strategies[strategy_id]
            
            # 确认删除
            print(f"\n⚠️  即将删除策略: {strategy_id}")
            print(f"类型: {strategy_config.class_name}")
            print(f"资金分配: {strategy_config.allocation_ratio * 100:.1f}%")
            
            confirm = input("\n确认删除? 此操作不可撤销! (输入 'DELETE' 确认): ")
            if confirm != 'DELETE':
                print("❌ 操作已取消")
                return False
            
            # 执行删除
            self.config_manager.remove_strategy_config(strategy_id)
            self.config_manager.save_config()
            
            print(f"✅ 策略 '{strategy_id}' 已成功删除")
            return True
            
        except KeyboardInterrupt:
            print("\n❌ 操作已取消")
            return False
    
    def modify_strategy_interactive(self) -> bool:
        """交互式修改策略"""
        print("\n🔧 修改策略配置")
        print("=" * 25)
        
        strategies = self.config_manager.get_all_strategies_config()
        if not strategies:
            print("❌ 暂无可修改的策略")
            return False
        
        # 显示策略列表
        strategy_list = {}
        print("\n当前策略:")
        for i, (strategy_id, config) in enumerate(strategies.items(), 1):
            status = "🟢 启用" if config.active else "⚪ 禁用"
            allocation = config.allocation_ratio * 100
            print(f"{i}. {strategy_id} ({config.class_name}) - {status} - {allocation:.1f}%")
            strategy_list[str(i)] = strategy_id
        
        try:
            choice = input("\n请选择要修改的策略编号 (回车取消): ").strip()
            if not choice:
                print("❌ 操作已取消")
                return False
            
            if choice not in strategy_list:
                print("❌ 无效选择")
                return False
            
            strategy_id = strategy_list[choice]
            return self._modify_strategy_details(strategy_id)
            
        except KeyboardInterrupt:
            print("\n❌ 操作已取消")
            return False
    
    def _modify_strategy_details(self, strategy_id: str) -> bool:
        """修改策略详细配置"""
        strategy_config = self.config_manager.get_strategy_config(strategy_id)
        if not strategy_config:
            print(f"❌ 策略不存在: {strategy_id}")
            return False
        
        print(f"\n🔧 修改策略: {strategy_id}")
        print("=" * 40)
        print("1. 启用/禁用策略")
        print("2. 修改资金分配")
        print("3. 修改支持的交易对")
        print("4. 修改策略参数")
        print("0. 返回上级菜单")
        
        choice = input("\n请选择操作 (0-4): ").strip()
        
        if choice == '1':
            return self._toggle_strategy_status(strategy_id, strategy_config)
        elif choice == '2':
            return self._modify_allocation(strategy_id, strategy_config)
        elif choice == '3':
            return self._modify_symbols(strategy_id, strategy_config)
        elif choice == '4':
            return self._modify_parameters(strategy_id, strategy_config)
        elif choice == '0':
            return False
        else:
            print("❌ 无效选择")
            return False
    
    def _toggle_strategy_status(self, strategy_id: str, strategy_config: StrategyConfig) -> bool:
        """切换策略启用状态"""
        current_status = "启用" if strategy_config.active else "禁用"
        new_status = "禁用" if strategy_config.active else "启用"
        
        confirm = input(f"\n确认{new_status}策略 '{strategy_id}'? 当前状态: {current_status} (y/N): ").lower()
        if confirm != 'y':
            print("❌ 操作已取消")
            return False
        
        success = self.config_manager.update_strategy_config(strategy_id, active=not strategy_config.active)
        if success:
            self.config_manager.save_config()
            print(f"✅ 策略 '{strategy_id}' 已{new_status}")
            return True
        else:
            print("❌ 操作失败")
            return False
    
    def _modify_allocation(self, strategy_id: str, strategy_config: StrategyConfig) -> bool:
        """修改资金分配"""
        current_allocation = strategy_config.allocation_ratio * 100
        
        # 计算可用分配
        other_active_allocation = sum(
            config.allocation_ratio 
            for sid, config in self.config_manager.get_active_strategies_config().items()
            if sid != strategy_id
        )
        max_available = 100 - other_active_allocation * 100
        
        print(f"\n当前分配: {current_allocation:.1f}%")
        print(f"最大可分配: {max_available:.1f}%")
        
        try:
            new_allocation_input = input(f"请输入新的分配比例 (0-{max_available:.1f}%, 回车取消): ").strip()
            if not new_allocation_input:
                print("❌ 操作已取消")
                return False
            
            new_allocation_pct = float(new_allocation_input.rstrip('%'))
            if new_allocation_pct < 0 or new_allocation_pct > max_available:
                print(f"❌ 分配比例应该在 0-{max_available:.1f}% 范围内")
                return False
            
            new_allocation_ratio = new_allocation_pct / 100
            
            success = self.config_manager.update_strategy_config(strategy_id, allocation_ratio=new_allocation_ratio)
            if success:
                self.config_manager.save_config()
                print(f"✅ 策略 '{strategy_id}' 资金分配已更新为 {new_allocation_pct:.1f}%")
                return True
            else:
                print("❌ 操作失败")
                return False
                
        except ValueError:
            print("❌ 请输入有效的数值")
            return False
    
    def _modify_symbols(self, strategy_id: str, strategy_config: StrategyConfig) -> bool:
        """修改支持的交易对"""
        current_symbols = strategy_config.config.get('supported_symbols', [])
        print(f"\n当前支持的交易对: {current_symbols}")
        
        new_symbols_input = input("请输入新的交易对列表 (用逗号分隔, 回车取消): ").strip()
        if not new_symbols_input:
            print("❌ 操作已取消")
            return False
        
        new_symbols = [s.strip().upper() for s in new_symbols_input.split(',')]
        
        success = self.config_manager.update_strategy_config(
            strategy_id, 
            config_update={'supported_symbols': new_symbols}
        )
        
        if success:
            self.config_manager.save_config()
            print(f"✅ 策略 '{strategy_id}' 支持的交易对已更新为: {new_symbols}")
            return True
        else:
            print("❌ 操作失败")
            return False
    
    def _modify_parameters(self, strategy_id: str, strategy_config: StrategyConfig) -> bool:
        """修改策略参数"""
        print(f"\n⚙️  修改策略参数: {strategy_id}")
        print("=" * 30)
        
        current_config = strategy_config.config.copy()
        
        # 显示当前主要参数
        key_params = ['risk_per_trade', 'stop_loss_pct', 'take_profit_ratio']
        
        print("主要参数:")
        for param in key_params:
            if param in current_config:
                value = current_config[param]
                if param.endswith('_pct') or param == 'risk_per_trade':
                    print(f"  {param}: {value * 100:.2f}%")
                else:
                    print(f"  {param}: {value}")
        
        print("\n策略特定参数:")
        strategy_type = strategy_config.class_name
        if strategy_type == "RSIDivergenceV2":
            specific_params = ['rsi_period', 'lookback', 'min_signal_strength']
        elif strategy_type == "MovingAverageCrossover":
            specific_params = ['fast_period', 'slow_period', 'ma_type']
        else:
            specific_params = []
        
        for param in specific_params:
            if param in current_config:
                print(f"  {param}: {current_config[param]}")
        
        # 选择要修改的参数
        all_params = key_params + specific_params
        print(f"\n可修改的参数: {', '.join(all_params)}")
        
        param_to_modify = input("请输入要修改的参数名 (回车取消): ").strip()
        if not param_to_modify:
            print("❌ 操作已取消")
            return False
        
        if param_to_modify not in all_params or param_to_modify not in current_config:
            print("❌ 无效参数名")
            return False
        
        # 修改参数值
        current_value = current_config[param_to_modify]
        print(f"当前值: {current_value}")
        
        try:
            new_value_input = input(f"请输入新值 (回车取消): ").strip()
            if not new_value_input:
                print("❌ 操作已取消")
                return False
            
            # 根据参数类型转换值
            if isinstance(current_value, int):
                new_value = int(new_value_input)
            elif isinstance(current_value, float):
                new_value = float(new_value_input.rstrip('%')) / (100 if new_value_input.endswith('%') else 1)
            elif isinstance(current_value, str):
                new_value = new_value_input
            else:
                new_value = new_value_input
            
            # 更新配置
            update_config = {param_to_modify: new_value}
            success = self.config_manager.update_strategy_config(
                strategy_id,
                config_update=update_config
            )
            
            if success:
                self.config_manager.save_config()
                print(f"✅ 参数 '{param_to_modify}' 已更新为: {new_value}")
                return True
            else:
                print("❌ 操作失败")
                return False
                
        except ValueError:
            print("❌ 输入值类型错误")
            return False
    
    def clone_strategy_interactive(self) -> bool:
        """交互式克隆策略"""
        print("\n📋 克隆策略")
        print("=" * 15)
        
        strategies = self.config_manager.get_all_strategies_config()
        if not strategies:
            print("❌ 暂无可克隆的策略")
            return False
        
        # 选择要克隆的策略
        strategy_list = {}
        print("\n可克隆的策略:")
        for i, (strategy_id, config) in enumerate(strategies.items(), 1):
            status = "🟢 启用" if config.active else "⚪ 禁用"
            print(f"{i}. {strategy_id} ({config.class_name}) - {status}")
            strategy_list[str(i)] = strategy_id
        
        try:
            choice = input("\n请选择要克隆的策略编号 (回车取消): ").strip()
            if not choice:
                print("❌ 操作已取消")
                return False
            
            if choice not in strategy_list:
                print("❌ 无效选择")
                return False
            
            source_strategy_id = strategy_list[choice]
            source_config = strategies[source_strategy_id]
            
            # 输入新的策略ID
            while True:
                new_strategy_id = input(f"\n请输入新策略ID (基于 {source_strategy_id}): ").strip()
                if not new_strategy_id:
                    print("❌ 策略ID不能为空")
                    continue
                
                if self.config_manager.get_strategy_config(new_strategy_id):
                    print("❌ 策略ID已存在，请选择其他名称")
                    continue
                
                break
            
            # 创建新策略配置
            new_config = StrategyConfig(
                strategy_id=new_strategy_id,
                class_name=source_config.class_name,
                active=False,  # 新克隆的策略默认禁用
                allocation_ratio=0.0,  # 需要手动设置
                config=source_config.config.copy()
            )
            
            # 添加并保存
            self.config_manager.add_strategy_config(new_config)
            self.config_manager.save_config()
            
            print(f"✅ 策略已成功克隆: {new_strategy_id}")
            print("ℹ️  新策略默认为禁用状态，请手动配置资金分配并启用")
            
            return True
            
        except KeyboardInterrupt:
            print("\n❌ 操作已取消")
            return False