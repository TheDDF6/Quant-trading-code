# base_strategy.py - 策略基础类
"""
策略基础抽象类
定义所有交易策略必须实现的接口

所有策略必须继承此类并实现required方法
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import logging

@dataclass
class Signal:
    """交易信号数据类"""
    strategy_id: str          # 策略ID
    symbol: str               # 交易对
    signal_type: str          # 信号类型: 'buy', 'sell', 'close'
    strength: float           # 信号强度 (0-1)
    timestamp: datetime       # 信号时间
    entry_price: float        # 预期入场价格
    stop_loss: Optional[float] = None    # 止损价格
    take_profit: Optional[float] = None  # 止盈价格
    position_size: Optional[float] = None # 建议仓位大小
    metadata: Optional[Dict] = None       # 额外信息

class BaseStrategy(ABC):
    """
    策略基础类 - 所有交易策略的抽象基类
    
    必须实现的方法:
    - analyze_market: 分析市场并生成信号
    - get_risk_level: 获取策略风险等级
    - validate_signal: 验证信号有效性
    """
    
    def __init__(self, strategy_id: str, config: Dict[str, Any]):
        """
        初始化策略
        
        Args:
            strategy_id: 唯一策略标识符
            config: 策略配置参数
        """
        self.strategy_id = strategy_id
        self.config = config
        self.logger = logging.getLogger(f"Strategy.{strategy_id}")
        
        # 策略状态
        self.is_active = config.get('active', True)
        self.balance = config.get('initial_balance', 0.0)
        self.allocated_balance = config.get('allocated_balance', 0.0)
        
        # 策略统计
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.current_positions = {}
        
        # 风险参数
        self.max_position_size = config.get('max_position_size', 0.1)  # 最大仓位比例
        self.risk_per_trade = config.get('risk_per_trade', 0.02)       # 单笔风险比例
        self.max_drawdown = config.get('max_drawdown', 0.1)            # 最大回撤
        
        self.logger.info(f"策略 {strategy_id} 初始化完成")
    
    @abstractmethod
    def analyze_market(self, market_data: pd.DataFrame, **kwargs) -> List[Signal]:
        """
        分析市场数据并生成交易信号
        
        Args:
            market_data: 市场数据 (包含OHLCV)
            **kwargs: 其他参数
            
        Returns:
            List[Signal]: 交易信号列表
        """
        pass
    
    @abstractmethod
    def get_risk_level(self) -> float:
        """
        获取策略当前风险等级
        
        Returns:
            float: 风险等级 (0.0-1.0, 越高风险越大)
        """
        pass
    
    @abstractmethod  
    def validate_signal(self, signal: Signal) -> bool:
        """
        验证交易信号的有效性
        
        Args:
            signal: 待验证的信号
            
        Returns:
            bool: 信号是否有效
        """
        pass
    
    def get_supported_symbols(self) -> List[str]:
        """获取策略支持的交易对列表"""
        return self.config.get('supported_symbols', ['BTC-USDT-SWAP'])
    
    def get_timeframes(self) -> List[str]:
        """获取策略需要的时间周期"""
        return self.config.get('timeframes', ['5m'])
    
    def calculate_position_size(self, signal: Signal, available_balance: float) -> float:
        """
        计算建议仓位大小
        
        Args:
            signal: 交易信号
            available_balance: 可用余额
            
        Returns:
            float: 建议仓位大小(USDT)
        """
        if signal.stop_loss and signal.entry_price:
            # 基于风险计算仓位大小
            risk_amount = available_balance * self.risk_per_trade
            price_diff = abs(signal.entry_price - signal.stop_loss)
            if price_diff > 0:
                position_size = risk_amount / (price_diff / signal.entry_price)
                max_position = available_balance * self.max_position_size
                return min(position_size, max_position)
        
        # 默认使用固定比例
        return available_balance * self.max_position_size
    
    def update_statistics(self, trade_result: Dict[str, Any]):
        """
        更新策略统计信息
        
        Args:
            trade_result: 交易结果
        """
        self.total_trades += 1
        pnl = trade_result.get('pnl', 0.0)
        self.total_pnl += pnl
        
        if pnl > 0:
            self.winning_trades += 1
            
        self.logger.info(f"交易统计更新 - 总交易: {self.total_trades}, "
                        f"胜率: {self.winning_trades/self.total_trades*100:.1f}%, "
                        f"总盈亏: {self.total_pnl:.2f}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取策略统计信息"""
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        return {
            'strategy_id': self.strategy_id,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'win_rate': round(win_rate, 2),
            'total_pnl': round(self.total_pnl, 2),
            'balance': round(self.balance, 2),
            'allocated_balance': round(self.allocated_balance, 2),
            'active_positions': len(self.current_positions),
            'risk_level': self.get_risk_level()
        }
    
    def set_active(self, active: bool):
        """设置策略激活状态"""
        self.is_active = active
        status = "激活" if active else "停用"
        self.logger.info(f"策略 {self.strategy_id} 已{status}")
    
    def emergency_stop(self):
        """紧急停止策略"""
        self.is_active = False
        self.logger.warning(f"策略 {self.strategy_id} 紧急停止")
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.strategy_id}, active={self.is_active})>"