# multi_config_manager.py - 多策略配置管理器
"""
多策略配置管理器
负责管理多策略系统的所有配置项

主要功能:
1. 配置文件加载和验证
2. 策略配置动态管理
3. 运行时配置修改
4. 配置热重载
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from datetime import datetime
import threading
from dataclasses import dataclass, field

@dataclass
class StrategyConfig:
    """策略配置数据类"""
    strategy_id: str
    class_name: str
    active: bool
    allocation_ratio: float
    config: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> bool:
        """验证策略配置"""
        if not self.strategy_id or not self.class_name:
            return False
        if not 0 <= self.allocation_ratio <= 1:
            return False
        return True

class MultiStrategyConfigManager:
    """多策略配置管理器"""
    
    def __init__(self, config_file: Union[str, Path] = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = Path(config_file) if config_file else Path("config/multi_strategy_config.json")
        self.logger = logging.getLogger("ConfigManager")
        
        # 配置数据
        self._config_data: Dict[str, Any] = {}
        self._strategies_config: Dict[str, StrategyConfig] = {}
        
        # 线程锁
        self._lock = threading.RLock()
        
        # 文件监控
        self._last_modified = None
        self._auto_reload = True
        
        # 加载配置
        self.load_config()
        
        self.logger.info(f"配置管理器初始化完成 - 配置文件: {self.config_file}")
    
    def load_config(self) -> bool:
        """
        加载配置文件
        
        Returns:
            bool: 加载是否成功
        """
        try:
            with self._lock:
                
                if not self.config_file.exists():
                    self.logger.error(f"配置文件不存在: {self.config_file}")
                    return False
                
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config_data = json.load(f)
                
                # 更新文件修改时间
                self._last_modified = self.config_file.stat().st_mtime
                
                # 解析策略配置
                self._parse_strategies_config()
                
                # 验证配置
                if not self._validate_config():
                    self.logger.error("配置验证失败")
                    return False
                
                self.logger.info("配置加载成功")
                return True
                
        except Exception as e:
            self.logger.error(f"配置加载失败: {e}")
            return False
    
    def _parse_strategies_config(self):
        """解析策略配置"""
        strategies_data = self._config_data.get('strategies', {})
        self._strategies_config.clear()
        
        for strategy_id, strategy_data in strategies_data.items():
            try:
                strategy_config = StrategyConfig(
                    strategy_id=strategy_id,
                    class_name=strategy_data.get('class', ''),
                    active=strategy_data.get('active', False),
                    allocation_ratio=strategy_data.get('allocation_ratio', 0.0),
                    config=strategy_data.get('config', {})
                )
                
                if strategy_config.validate():
                    self._strategies_config[strategy_id] = strategy_config
                else:
                    self.logger.warning(f"策略配置无效: {strategy_id}")
                    
            except Exception as e:
                self.logger.error(f"解析策略配置失败 {strategy_id}: {e}")
    
    def _validate_config(self) -> bool:
        """验证配置完整性"""
        try:
            # 检查必要的顶级配置
            required_sections = ['okx', 'trading_engine', 'strategy_manager', 'risk_manager']
            for section in required_sections:
                if section not in self._config_data:
                    self.logger.error(f"缺少必要配置节: {section}")
                    return False
            
            # 检查OKX API配置
            okx_config = self._config_data.get('okx', {})
            required_okx_keys = ['api_key', 'secret_key', 'passphrase']
            for key in required_okx_keys:
                if not okx_config.get(key):
                    self.logger.error(f"OKX配置缺少: {key}")
                    return False
            
            # 验证策略配置
            if not self._strategies_config:
                self.logger.warning("没有配置任何策略")
                return False
            
            # 检查资金分配总和
            total_allocation = sum(s.allocation_ratio for s in self._strategies_config.values() if s.active)
            if total_allocation > 1.1:  # 允许10%容差
                self.logger.warning(f"活跃策略资金分配总和超过100%: {total_allocation:.1%}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"配置验证异常: {e}")
            return False
    
    def save_config(self) -> bool:
        """
        保存配置到文件
        
        Returns:
            bool: 保存是否成功
        """
        try:
            with self._lock:
                # 更新策略配置到主配置数据
                strategies_data = {}
                for strategy_id, strategy_config in self._strategies_config.items():
                    strategies_data[strategy_id] = {
                        'class': strategy_config.class_name,
                        'active': strategy_config.active,
                        'allocation_ratio': strategy_config.allocation_ratio,
                        'config': strategy_config.config
                    }
                
                self._config_data['strategies'] = strategies_data
                
                # 备份原文件
                backup_file = self.config_file.with_suffix('.bak')
                if self.config_file.exists():
                    self.config_file.rename(backup_file)
                
                # 保存新配置
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self._config_data, f, indent=2, ensure_ascii=False)
                
                # 更新修改时间
                self._last_modified = self.config_file.stat().st_mtime
                
                self.logger.info("配置保存成功")
                return True
                
        except Exception as e:
            self.logger.error(f"配置保存失败: {e}")
            return False
    
    def reload_if_changed(self) -> bool:
        """如果文件有变化则重新加载"""
        if not self._auto_reload or not self.config_file.exists():
            return False
        
        try:
            current_mtime = self.config_file.stat().st_mtime
            if current_mtime > self._last_modified:
                self.logger.info("检测到配置文件变化，重新加载...")
                return self.load_config()
        except Exception as e:
            self.logger.error(f"检查文件变化失败: {e}")
        
        return False
    
    # ========== 通用配置访问方法 ==========
    
    def get(self, section: str, key: str = None, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            section: 配置节名称
            key: 配置键名称（可选）
            default: 默认值
            
        Returns:
            配置值
        """
        with self._lock:
            section_data = self._config_data.get(section, {})
            if key is None:
                return section_data
            return section_data.get(key, default)
    
    def set(self, section: str, key: str = None, value: Any = None) -> bool:
        """
        设置配置值
        
        Args:
            section: 配置节名称
            key: 配置键名称（如果为None，则value应为整个节的数据）
            value: 配置值
            
        Returns:
            bool: 设置是否成功
        """
        try:
            with self._lock:
                if section not in self._config_data:
                    self._config_data[section] = {}
                
                if key is None:
                    if isinstance(value, dict):
                        self._config_data[section] = value
                    else:
                        return False
                else:
                    self._config_data[section][key] = value
                
                return True
                
        except Exception as e:
            self.logger.error(f"设置配置失败: {e}")
            return False
    
    # ========== 策略配置管理方法 ==========
    
    def get_strategy_config(self, strategy_id: str) -> Optional[StrategyConfig]:
        """获取策略配置"""
        with self._lock:
            return self._strategies_config.get(strategy_id)
    
    def get_all_strategies_config(self) -> Dict[str, StrategyConfig]:
        """获取所有策略配置"""
        with self._lock:
            return self._strategies_config.copy()
    
    def get_active_strategies_config(self) -> Dict[str, StrategyConfig]:
        """获取活跃策略配置"""
        with self._lock:
            return {sid: config for sid, config in self._strategies_config.items() if config.active}
    
    def add_strategy_config(self, strategy_config: StrategyConfig) -> bool:
        """添加策略配置"""
        if not strategy_config.validate():
            self.logger.error(f"策略配置无效: {strategy_config.strategy_id}")
            return False
        
        with self._lock:
            if strategy_config.strategy_id in self._strategies_config:
                self.logger.warning(f"策略配置已存在，将被覆盖: {strategy_config.strategy_id}")
            
            self._strategies_config[strategy_config.strategy_id] = strategy_config
            self.logger.info(f"添加策略配置: {strategy_config.strategy_id}")
            return True
    
    def update_strategy_config(self, strategy_id: str, **kwargs) -> bool:
        """更新策略配置"""
        with self._lock:
            if strategy_id not in self._strategies_config:
                self.logger.error(f"策略配置不存在: {strategy_id}")
                return False
            
            strategy_config = self._strategies_config[strategy_id]
            
            # 更新配置项
            for key, value in kwargs.items():
                if hasattr(strategy_config, key):
                    setattr(strategy_config, key, value)
                elif key == 'config_update':
                    # 更新策略配置字典
                    if isinstance(value, dict):
                        strategy_config.config.update(value)
                else:
                    self.logger.warning(f"未知配置项: {key}")
            
            # 验证更新后的配置
            if not strategy_config.validate():
                self.logger.error(f"更新后的策略配置无效: {strategy_id}")
                return False
            
            self.logger.info(f"更新策略配置: {strategy_id}")
            return True
    
    def remove_strategy_config(self, strategy_id: str) -> bool:
        """移除策略配置"""
        with self._lock:
            if strategy_id in self._strategies_config:
                del self._strategies_config[strategy_id]
                self.logger.info(f"移除策略配置: {strategy_id}")
                return True
            else:
                self.logger.warning(f"策略配置不存在: {strategy_id}")
                return False
    
    def enable_strategy(self, strategy_id: str) -> bool:
        """启用策略"""
        return self.update_strategy_config(strategy_id, active=True)
    
    def disable_strategy(self, strategy_id: str) -> bool:
        """禁用策略"""
        return self.update_strategy_config(strategy_id, active=False)
    
    # ========== 特殊配置访问方法 ==========
    
    def get_okx_config(self) -> Dict[str, Any]:
        """获取OKX配置"""
        return self.get('okx', default={})
    
    def get_trading_engine_config(self) -> Dict[str, Any]:
        """获取交易引擎配置"""
        return self.get('trading_engine', default={})
    
    def get_strategy_manager_config(self) -> Dict[str, Any]:
        """获取策略管理器配置"""
        return self.get('strategy_manager', default={})
    
    def get_risk_manager_config(self) -> Dict[str, Any]:
        """获取风险管理器配置"""
        return self.get('risk_manager', default={})
    
    def get_symbol_settings(self, symbol: str = None) -> Dict[str, Any]:
        """获取交易对设置"""
        symbol_settings = self.get('symbol_settings', default={})
        if symbol:
            return symbol_settings.get(symbol, {})
        return symbol_settings
    
    def is_sandbox(self) -> bool:
        """是否为沙盒环境"""
        return self.get('okx', 'sandbox', True)
    
    def get_total_balance(self) -> float:
        """获取总资金"""
        return self.get('strategy_manager', 'total_balance', 10000.0)
    
    def get_max_leverage(self, symbol: str = None) -> int:
        """获取最大杠杆"""
        if symbol:
            symbol_config = self.get_symbol_settings(symbol)
            return symbol_config.get('max_leverage', 10)
        return self.get('position_management', 'max_leverage', 10)
    
    # ========== 配置状态和统计 ==========
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        with self._lock:
            active_strategies = len([s for s in self._strategies_config.values() if s.active])
            total_allocation = sum(s.allocation_ratio for s in self._strategies_config.values() if s.active)
            
            return {
                'config_file': str(self.config_file),
                'last_modified': datetime.fromtimestamp(self._last_modified).isoformat() if self._last_modified else None,
                'environment': 'sandbox' if self.is_sandbox() else 'production',
                'total_balance': self.get_total_balance(),
                'strategies': {
                    'total': len(self._strategies_config),
                    'active': active_strategies,
                    'total_allocation': round(total_allocation, 3)
                },
                'symbols_configured': len(self.get_symbol_settings()),
                'auto_reload': self._auto_reload
            }
    
    def validate_all(self) -> Dict[str, Any]:
        """验证所有配置"""
        results = {
            'overall': True,
            'errors': [],
            'warnings': [],
            'strategies': {}
        }
        
        try:
            # 验证基础配置
            if not self._validate_config():
                results['overall'] = False
                results['errors'].append("基础配置验证失败")
            
            # 验证每个策略配置
            for strategy_id, strategy_config in self._strategies_config.items():
                if not strategy_config.validate():
                    results['overall'] = False
                    results['strategies'][strategy_id] = False
                    results['errors'].append(f"策略配置无效: {strategy_id}")
                else:
                    results['strategies'][strategy_id] = True
            
            # 检查资金分配
            active_strategies = [s for s in self._strategies_config.values() if s.active]
            if active_strategies:
                total_allocation = sum(s.allocation_ratio for s in active_strategies)
                if total_allocation > 1.0:
                    results['warnings'].append(f"活跃策略资金分配总和超过100%: {total_allocation:.1%}")
                elif total_allocation < 0.8:
                    results['warnings'].append(f"活跃策略资金分配总和较低: {total_allocation:.1%}")
            
        except Exception as e:
            results['overall'] = False
            results['errors'].append(f"验证过程异常: {e}")
        
        return results
    
    def set_auto_reload(self, enabled: bool):
        """设置自动重载"""
        self._auto_reload = enabled
        self.logger.info(f"自动重载配置: {'启用' if enabled else '禁用'}")

# 全局配置管理器实例
multi_config = MultiStrategyConfigManager()