# config.py - 配置管理
import os
from typing import Dict, Any
import json
from pathlib import Path

class Config:
    """交易系统配置"""
    
    def __init__(self):
        self.config_file = Path(__file__).parent / "trading_config.json"
        self.load_config()
        
    def load_config(self):
        """加载配置文件"""
        default_config = {
            "okx": {
                "api_key": "",
                "secret_key": "", 
                "passphrase": "",
                "sandbox": True  # 默认使用沙盒环境
            },
            "trading": {
                "symbol": "BTC-USDT-SWAP",  # 交易对
                "initial_balance": 1000.0,  # 初始资金
                "risk_per_trade": 0.015,    # 单笔风险1.5%
                "max_leverage": 10,         # 最大杠杆（保守起步）
                "min_trade_amount": 10.0,   # 最小交易金额
                "max_positions": 1          # 最大持仓数量
            },
            "strategy": {
                "name": "rsi_divergence",
                "rsi_period": 14,
                "lookback": 20,
                "stop_loss_pct": 0.015,
                "take_profit_ratio": 1.5
            },
            "risk_management": {
                "max_daily_loss": 0.05,     # 最大日亏损5%
                "max_consecutive_losses": 3, # 最大连续亏损次数
                "stop_trading_on_loss": True, # 达到亏损限制时停止交易
                "emergency_stop": False      # 紧急停止开关
            },
            "monitoring": {
                "log_level": "INFO",
                "save_trades": True,
                "alert_on_error": True,
                "heartbeat_interval": 60    # 心跳间隔（秒）
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 合并配置，新的配置项会被添加
                    self._deep_update(default_config, loaded_config)
            except Exception as e:
                print(f"加载配置文件失败: {e}，使用默认配置")
        
        self.config = default_config
        self.save_config()  # 保存配置以确保所有默认值都存在
        
    def _deep_update(self, base_dict: Dict, update_dict: Dict):
        """深度更新字典"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
                
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            
    def get(self, section: str, key: str = None, default: Any = None) -> Any:
        """获取配置项"""
        if key is None:
            return self.config.get(section, default)
        return self.config.get(section, {}).get(key, default)
        
    def set(self, section: str, key: str, value: Any):
        """设置配置项"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        self.save_config()
        
    def is_sandbox(self) -> bool:
        """是否为沙盒环境"""
        return self.get('okx', 'sandbox', True)
        
    def get_symbol(self) -> str:
        """获取交易对"""
        return self.get('trading', 'symbol', 'BTC-USDT-SWAP')
        
    def get_risk_per_trade(self) -> float:
        """获取单笔风险比例"""
        return self.get('trading', 'risk_per_trade', 0.015)
        
    def is_emergency_stop(self) -> bool:
        """是否紧急停止"""
        return self.get('risk_management', 'emergency_stop', False)
        
    def set_emergency_stop(self, stop: bool):
        """设置紧急停止"""
        self.set('risk_management', 'emergency_stop', stop)
    
    def get_maker_fee(self) -> float:
        """获取挂单手续费率"""
        return self.get('fees', 'maker_fee', 0.0002)
        
    def get_taker_fee(self) -> float:
        """获取吃单手续费率"""
        return self.get('fees', 'taker_fee', 0.0005)
        
    def get_slippage_rate(self) -> float:
        """获取预估滑点率"""
        return self.get('fees', 'estimated_slippage', 0.0001)
        
    def is_using_market_orders(self) -> bool:
        """是否主要使用市价单"""
        order_type = self.get('fees', 'primary_order_type', 'market')
        return order_type.lower() == 'market'
        
    def get_user_level(self) -> str:
        """获取用户等级"""
        return self.get('fees', 'user_level', 'normal')
        
    def validate_api_config(self) -> bool:
        """验证API配置是否完整"""
        api_key = self.get('okx', 'api_key', '')
        secret_key = self.get('okx', 'secret_key', '')
        passphrase = self.get('okx', 'passphrase', '')
        
        return all([api_key, secret_key, passphrase])
        
    def validate_fees_config(self) -> bool:
        """验证手续费配置是否合理"""
        maker_fee = self.get_maker_fee()
        taker_fee = self.get_taker_fee()
        slippage = self.get_slippage_rate()
        
        # 基本合理性检查
        if not (0 <= maker_fee <= 0.01):  # 0-1%
            return False
        if not (0 <= taker_fee <= 0.01):  # 0-1%
            return False
        if not (0 <= slippage <= 0.001):  # 0-0.1%
            return False
        if maker_fee > taker_fee:  # Maker费率通常不应高于Taker
            return False
            
        return True

# 全局配置实例
config = Config()