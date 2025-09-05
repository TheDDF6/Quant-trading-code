# strategy_registry.py - 策略注册表
"""
策略注册表
管理所有可用的策略类型和创建策略实例

主要功能:
1. 策略类型注册
2. 动态创建策略实例
3. 策略参数模板管理
4. 策略信息查询
"""

import logging
import os
import importlib
import inspect
from typing import Dict, List, Type, Any, Optional, Tuple
from abc import ABC

from strategies.base_strategy import BaseStrategy

class StrategyRegistry:
    """策略注册表"""
    
    def __init__(self):
        """初始化策略注册表"""
        self.logger = logging.getLogger("StrategyRegistry")
        
        # 策略类注册表
        self._strategy_classes: Dict[str, Type[BaseStrategy]] = {}
        
        # 策略默认配置模板
        self._default_configs: Dict[str, Dict[str, Any]] = {}
        
        # 策略描述信息
        self._strategy_info: Dict[str, Dict[str, str]] = {}
        
        # 注册内置策略
        self._register_builtin_strategies()
        
        self.logger.info("策略注册表初始化完成")
    
    def _register_builtin_strategies(self):
        """自动发现并注册strategies目录中的策略"""
        strategies_dir = "strategies"

        if not os.path.exists(strategies_dir):
            self.logger.warning(f"策略目录不存在: {strategies_dir}")
            return

        # 递归扫描strategies目录及子目录
        for root, _, files in os.walk(strategies_dir):
            rel_path = os.path.relpath(root, strategies_dir)
            package = "strategies" if rel_path == "." else f"strategies.{rel_path.replace(os.sep, '.')}"

            for filename in files:
                if filename.endswith('.py') and filename not in ('__init__.py', 'base_strategy.py'):
                    module_base = filename[:-3]
                    full_module = f"{package}.{module_base}" if package != "strategies" else f"strategies.{module_base}"

                    try:
                        module = importlib.import_module(full_module)

                        # 查找BaseStrategy的子类
                        for name, obj in inspect.getmembers(module):
                            if (
                                inspect.isclass(obj)
                                and issubclass(obj, BaseStrategy)
                                and obj != BaseStrategy
                            ):
                                self._register_discovered_strategy(name, obj, module_base)

                    except Exception as e:
                        self.logger.error(f"导入策略模块失败 {full_module}: {e}")
                        continue

        self.logger.info(f"已自动发现并注册 {len(self._strategy_classes)} 个策略")
    
    def _register_discovered_strategy(self, class_name: str, strategy_class: Type[BaseStrategy], module_name: str):
        """注册自动发现的策略"""
        # 根据策略类型设置默认配置
        default_config = {
            "supported_symbols": ["BTC-USDT-SWAP"],
            "timeframes": ["5m"],
            "max_position_size": 0.5,
            "risk_per_trade": 0.02
        }
        
        description = "自动发现的交易策略"
        category = "自定义"
        risk_level = "中等"
        
        # 根据模块名设置特定配置
        if 'rsi' in module_name.lower():
            default_config.update({
                "rsi_period": 14,
                "rsi_oversold": 30,
                "rsi_overbought": 70,
                "stop_loss_pct": 0.015,
                "take_profit_ratio": 1.5
            })
            description = "基于RSI的交易策略"
            category = "技术指标"
            
        elif 'ma' in module_name.lower() or 'average' in module_name.lower():
            default_config.update({
                "fast_period": 10,
                "slow_period": 20,
                "stop_loss_pct": 0.02,
                "take_profit_ratio": 2.0
            })
            description = "基于移动平均的交易策略"
            category = "趋势跟踪"
            
        elif 'volatility' in module_name.lower() or 'breakout' in module_name.lower():
            default_config.update({
                "bb_period": 20,
                "bb_std": 2.0,
                "bb_threshold": 0.04,
                "atr_period": 14,
                "stop_loss_mult": 1.5,
                "trailing_mult": 2.0,
                "volume_mult": 1.5,
                "enable_volume_filter": False,
                "min_signal_strength": 0.6
            })
            description = "基于布林带的波动率突破策略"
            category = "突破策略"
            risk_level = "中等"
        
        self.register_strategy(
            class_name,
            strategy_class, 
            default_config,
            description,
            category,
            risk_level
        )
    
    def register_strategy(self, 
                         strategy_name: str,
                         strategy_class: Type[BaseStrategy],
                         default_config: Dict[str, Any],
                         description: str = "",
                         category: str = "其他",
                         risk_level: str = "未知"):
        """
        注册策略
        
        Args:
            strategy_name: 策略名称
            strategy_class: 策略类
            default_config: 默认配置
            description: 策略描述
            category: 策略分类
            risk_level: 风险等级
        """
        if not issubclass(strategy_class, BaseStrategy):
            raise ValueError(f"策略类必须继承自BaseStrategy: {strategy_class}")
        
        self._strategy_classes[strategy_name] = strategy_class
        self._default_configs[strategy_name] = default_config.copy()
        self._strategy_info[strategy_name] = {
            "description": description,
            "category": category,
            "risk_level": risk_level,
            "class_name": strategy_class.__name__
        }
        
        self.logger.info(f"策略已注册: {strategy_name}")
    
    def unregister_strategy(self, strategy_name: str):
        """注销策略"""
        if strategy_name in self._strategy_classes:
            del self._strategy_classes[strategy_name]
            del self._default_configs[strategy_name]
            del self._strategy_info[strategy_name]
            self.logger.info(f"策略已注销: {strategy_name}")
        else:
            self.logger.warning(f"策略不存在: {strategy_name}")
    
    def create_strategy(self, 
                       strategy_type: str, 
                       strategy_id: str, 
                       config: Dict[str, Any] = None) -> Optional[BaseStrategy]:
        """
        创建策略实例
        
        Args:
            strategy_type: 策略类型
            strategy_id: 策略实例ID
            config: 策略配置（如果为None则使用默认配置）
            
        Returns:
            策略实例或None
        """
        if strategy_type not in self._strategy_classes:
            self.logger.error(f"未知策略类型: {strategy_type}")
            return None
        
        try:
            # 合并默认配置和用户配置
            final_config = self._default_configs[strategy_type].copy()
            if config:
                final_config.update(config)
            
            # 创建策略实例
            strategy_class = self._strategy_classes[strategy_type]
            strategy = strategy_class(strategy_id, final_config)
            
            self.logger.info(f"策略实例已创建: {strategy_id} ({strategy_type})")
            return strategy
            
        except Exception as e:
            self.logger.error(f"创建策略失败 {strategy_id}: {e}")
            return None
    
    def get_available_strategies(self) -> List[str]:
        """获取所有可用策略类型"""
        return list(self._strategy_classes.keys())
    
    def get_strategy_info(self, strategy_type: str = None) -> Dict[str, Any]:
        """
        获取策略信息
        
        Args:
            strategy_type: 策略类型（如果为None则返回所有策略信息）
            
        Returns:
            策略信息字典
        """
        if strategy_type:
            if strategy_type in self._strategy_info:
                return self._strategy_info[strategy_type].copy()
            else:
                return {}
        else:
            return self._strategy_info.copy()
    
    def get_default_config(self, strategy_type: str) -> Dict[str, Any]:
        """获取策略默认配置"""
        return self._default_configs.get(strategy_type, {}).copy()
    
    def get_strategy_categories(self) -> Dict[str, List[str]]:
        """获取策略分类"""
        categories = {}
        for strategy_type, info in self._strategy_info.items():
            category = info.get("category", "其他")
            if category not in categories:
                categories[category] = []
            categories[category].append(strategy_type)
        
        return categories
    
    def validate_strategy_config(self, strategy_type: str, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证策略配置
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        if strategy_type not in self._strategy_classes:
            errors.append(f"未知策略类型: {strategy_type}")
            return False, errors
        
        default_config = self._default_configs[strategy_type]
        
        # 检查必要参数
        required_fields = ["supported_symbols", "timeframes"]
        for field in required_fields:
            if field not in config and field not in default_config:
                errors.append(f"缺少必要参数: {field}")
        
        # 检查数值参数范围
        numeric_checks = {
            "risk_per_trade": (0.001, 0.1),  # 0.1% - 10%
            "max_position_size": (0.1, 1.0),  # 10% - 100%
            "stop_loss_pct": (0.005, 0.1),   # 0.5% - 10%
        }
        
        for param, (min_val, max_val) in numeric_checks.items():
            if param in config:
                value = config[param]
                if not isinstance(value, (int, float)) or not (min_val <= value <= max_val):
                    errors.append(f"{param} 应该在 {min_val}-{max_val} 范围内")
        
        return len(errors) == 0, errors

# 全局策略注册表实例
strategy_registry = StrategyRegistry()