# strategy_manager.py - 策略管理器
"""
多策略管理器
负责管理多个交易策略的运行、协调和监控

主要功能:
1. 策略注册和生命周期管理
2. 信号收集和去重
3. 资金分配和风险控制
4. 策略性能监控
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Type
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

from strategies.base_strategy import BaseStrategy, Signal

class StrategyManager:
    """多策略管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化策略管理器
        
        Args:
            config: 管理器配置
        """
        self.config = config
        self.logger = logging.getLogger("StrategyManager")
        
        # 策略注册表
        self.strategies: Dict[str, BaseStrategy] = {}
        self.strategy_configs: Dict[str, Dict] = {}
        
        # 资金管理
        self.total_balance = config.get('total_balance', 10000.0)
        self.reserved_balance = config.get('reserved_balance', 0.1)  # 保留10%资金
        self.available_balance = self.total_balance * (1 - self.reserved_balance)
        
        # 信号管理
        self.active_signals: List[Signal] = []
        self.signal_history: List[Signal] = []
        self.max_signal_history = config.get('max_signal_history', 1000)
        
        # 运行控制
        self.is_running = False
        self.update_interval = config.get('update_interval', 30)  # 30秒更新间隔
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # 全局风险控制
        self.max_total_risk = config.get('max_total_risk', 0.05)  # 总风险不超过5%
        self.max_concurrent_positions = config.get('max_concurrent_positions', 3)
        
        # 资金分配模式：'individual' 或 'shared_pool'
        self.fund_allocation_mode = config.get('fund_allocation_mode', 'shared_pool')
        
        # 共享资金池管理
        self.shared_pool_balance = self.available_balance
        self.pool_lock = False  # 资金池锁定状态（有持仓时锁定）
        
        self.logger.info("策略管理器初始化完成")
    
    def register_strategy(self, strategy: BaseStrategy, allocation_ratio: float = 0.0):
        """
        注册策略
        
        Args:
            strategy: 策略实例
            allocation_ratio: 资金分配比例 (0.0表示平均分配)
        """
        strategy_id = strategy.strategy_id
        
        if strategy_id in self.strategies:
            self.logger.warning(f"策略 {strategy_id} 已存在，将被覆盖")
        
        self.strategies[strategy_id] = strategy
        
        if self.fund_allocation_mode == 'shared_pool':
            # 共享资金池模式：策略不分配独立资金
            strategy.allocated_balance = 0.0  # 标记为共享模式
            strategy.balance = 0.0
            self.logger.info(f"策略 {strategy_id} 注册成功，使用共享资金池模式")
        else:
            # 独立分配模式
            if allocation_ratio <= 0:
                # 平均分配
                allocation_ratio = 1.0 / max(len(self.strategies), 1)
            
            allocated_amount = self.available_balance * allocation_ratio
            strategy.allocated_balance = allocated_amount
            strategy.balance = allocated_amount
            self.logger.info(f"策略 {strategy_id} 注册成功，分配资金: ${allocated_amount:.2f}")
    
    def unregister_strategy(self, strategy_id: str):
        """注销策略"""
        if strategy_id in self.strategies:
            strategy = self.strategies[strategy_id]
            # 回收资金
            self.available_balance += strategy.balance
            del self.strategies[strategy_id]
            self.logger.info(f"策略 {strategy_id} 已注销")
        else:
            self.logger.warning(f"策略 {strategy_id} 不存在")
    
    def start_all_strategies(self):
        """启动所有策略"""
        self.is_running = True
        self.logger.info("启动所有策略运行")
        
        for strategy_id, strategy in self.strategies.items():
            if strategy.is_active:
                self.logger.info(f"策略 {strategy_id} 已激活")
    
    def stop_all_strategies(self):
        """停止所有策略"""
        self.is_running = False
        self.logger.info("停止所有策略运行")
        
        for strategy in self.strategies.values():
            strategy.emergency_stop()
    
    def collect_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[Signal]:
        """
        收集所有策略的交易信号
        
        Args:
            market_data: 各交易对的市场数据
            
        Returns:
            List[Signal]: 收集到的所有信号
        """
        all_signals = []
        
        for strategy_id, strategy in self.strategies.items():
            if not strategy.is_active:
                continue
                
            try:
                # 获取策略支持的交易对数据
                strategy_data = {}
                for symbol in strategy.get_supported_symbols():
                    if symbol in market_data:
                        strategy_data[symbol] = market_data[symbol]
                
                if strategy_data:
                    # 并行执行策略分析
                    future = self.executor.submit(
                        self._run_strategy_analysis, 
                        strategy, 
                        strategy_data
                    )
                    signals = future.result(timeout=10)  # 10秒超时
                    all_signals.extend(signals)
                    
            except Exception as e:
                self.logger.error(f"策略 {strategy_id} 信号收集失败: {e}")
        
        # 信号去重和优先级处理
        filtered_signals = self._filter_and_prioritize_signals(all_signals)
        
        # 更新信号历史
        self.active_signals = filtered_signals
        self.signal_history.extend(filtered_signals)
        
        # 限制历史记录长度
        if len(self.signal_history) > self.max_signal_history:
            self.signal_history = self.signal_history[-self.max_signal_history:]
        
        return filtered_signals
    
    def _run_strategy_analysis(self, strategy: BaseStrategy, market_data: Dict[str, pd.DataFrame]) -> List[Signal]:
        """运行单个策略分析"""
        signals = []
        
        for symbol, data in market_data.items():
            try:
                strategy_signals = strategy.analyze_market(data, symbol=symbol)
                
                # 验证信号
                for signal in strategy_signals:
                    if strategy.validate_signal(signal):
                        # 计算仓位大小
                        if signal.position_size is None:
                            signal.position_size = strategy.calculate_position_size(
                                signal, strategy.balance
                            )
                        signals.append(signal)
                        
            except Exception as e:
                self.logger.error(f"策略 {strategy.strategy_id} 分析 {symbol} 失败: {e}")
        
        return signals
    
    def _filter_and_prioritize_signals(self, signals: List[Signal]) -> List[Signal]:
        """
        信号过滤和优先级处理
        
        规则:
        1. 同一交易对只保留最强信号
        2. 总风险不超过限制
        3. 并发持仓不超过限制
        4. 共享资金池模式：只允许一个持仓（先到先得）
        """
        if not signals:
            return []
        
        # 共享资金池模式下的特殊处理
        if self.fund_allocation_mode == 'shared_pool':
            return self._filter_signals_shared_pool_mode(signals)
        
        # 独立分配模式的原有逻辑
        return self._filter_signals_individual_mode(signals)
    
    def _filter_signals_shared_pool_mode(self, signals: List[Signal]) -> List[Signal]:
        """共享资金池模式的信号过滤"""
        if not signals:
            return []
        
        # 检查当前是否已有持仓（资金池是否被占用）
        if self.pool_lock:
            self.logger.info("共享资金池已被占用，暂不接受新信号")
            return []
        
        # 按时间排序（先到先得），然后按信号强度排序
        signals.sort(key=lambda x: (x.timestamp, -x.strength))
        
        # 按交易对分组，每个交易对只保留最强信号
        signal_by_symbol = {}
        for signal in signals:
            symbol = signal.symbol
            if symbol not in signal_by_symbol:
                signal_by_symbol[symbol] = signal
            elif signal.strength > signal_by_symbol[symbol].strength:
                signal_by_symbol[symbol] = signal
        
        # 选择最强信号（如果有多个交易对的话）
        if signal_by_symbol:
            best_signal = max(signal_by_symbol.values(), key=lambda x: x.strength)
            
            # 调整仓位大小为全部可用资金
            best_signal.position_size = self.shared_pool_balance
            
            self.logger.info(f"共享资金池模式：选择信号 {best_signal.symbol}，分配全部资金 ${self.shared_pool_balance:.2f}")
            return [best_signal]
        
        return []
    
    def _filter_signals_individual_mode(self, signals: List[Signal]) -> List[Signal]:
        """独立分配模式的信号过滤（原有逻辑）"""
        # 按交易对分组
        signal_by_symbol = {}
        for signal in signals:
            symbol = signal.symbol
            if symbol not in signal_by_symbol:
                signal_by_symbol[symbol] = []
            signal_by_symbol[symbol].append(signal)
        
        # 每个交易对选择最强信号
        filtered_signals = []
        for symbol, symbol_signals in signal_by_symbol.items():
            # 按信号强度排序
            symbol_signals.sort(key=lambda x: x.strength, reverse=True)
            best_signal = symbol_signals[0]
            
            # 检查风险限制
            if self._check_risk_limits(best_signal):
                filtered_signals.append(best_signal)
            else:
                self.logger.warning(f"信号 {best_signal.symbol} 超出风险限制，已过滤")
        
        # 按信号强度排序，优先执行强信号
        filtered_signals.sort(key=lambda x: x.strength, reverse=True)
        
        # 限制并发持仓数量
        if len(filtered_signals) > self.max_concurrent_positions:
            filtered_signals = filtered_signals[:self.max_concurrent_positions]
        
        return filtered_signals
    
    def _check_risk_limits(self, signal: Signal) -> bool:
        """检查信号是否符合风险限制"""
        # 获取策略
        strategy = self.strategies.get(signal.strategy_id)
        if not strategy:
            return False
        
        # 检查策略余额
        if signal.position_size > strategy.balance:
            return False
        
        # 检查总风险
        current_risk = self._calculate_current_risk()
        signal_risk = self._calculate_signal_risk(signal)
        
        if current_risk + signal_risk > self.max_total_risk:
            return False
        
        return True
    
    def _calculate_current_risk(self) -> float:
        """计算当前总风险"""
        total_risk = 0.0
        
        for strategy in self.strategies.values():
            strategy_risk = strategy.get_risk_level()
            risk_weight = strategy.allocated_balance / self.total_balance
            total_risk += strategy_risk * risk_weight
        
        return total_risk
    
    def _calculate_signal_risk(self, signal: Signal) -> float:
        """计算信号风险"""
        if signal.stop_loss and signal.entry_price and signal.position_size:
            risk_per_unit = abs(signal.entry_price - signal.stop_loss) / signal.entry_price
            total_risk = risk_per_unit * (signal.position_size / self.total_balance)
            return total_risk
        
        # 默认风险估算
        return 0.02  # 2%
    
    def get_strategies_status(self) -> Dict[str, Any]:
        """获取所有策略状态"""
        status = {
            'manager_status': {
                'is_running': self.is_running,
                'total_balance': self.total_balance,
                'available_balance': self.available_balance,
                'active_strategies': len([s for s in self.strategies.values() if s.is_active]),
                'total_strategies': len(self.strategies),
                'current_risk': self._calculate_current_risk(),
                'active_signals': len(self.active_signals),
                'fund_allocation_mode': self.fund_allocation_mode,
                'shared_pool_balance': self.shared_pool_balance if self.fund_allocation_mode == 'shared_pool' else None,
                'pool_locked': self.pool_lock if self.fund_allocation_mode == 'shared_pool' else None
            },
            'strategies': {}
        }
        
        for strategy_id, strategy in self.strategies.items():
            status['strategies'][strategy_id] = strategy.get_statistics()
        
        return status
    
    def rebalance_funds(self):
        """重新平衡资金分配"""
        active_strategies = [s for s in self.strategies.values() if s.is_active]
        
        if not active_strategies:
            return
        
        # 回收所有资金
        total_recovered = sum(s.balance for s in active_strategies)
        
        # 重新平均分配
        allocation_per_strategy = total_recovered / len(active_strategies)
        
        for strategy in active_strategies:
            strategy.balance = allocation_per_strategy
            strategy.allocated_balance = allocation_per_strategy
        
        self.logger.info(f"资金重新平衡完成，每策略分配: ${allocation_per_strategy:.2f}")
    
    def lock_shared_pool(self, reason: str = ""):
        """锁定共享资金池"""
        if self.fund_allocation_mode == 'shared_pool':
            self.pool_lock = True
            self.logger.info(f"共享资金池已锁定 - {reason}")
    
    def unlock_shared_pool(self, reason: str = ""):
        """解锁共享资金池"""
        if self.fund_allocation_mode == 'shared_pool':
            self.pool_lock = False
            self.logger.info(f"共享资金池已解锁 - {reason}")
    
    def update_shared_pool_balance(self, new_balance: float):
        """更新共享资金池余额"""
        if self.fund_allocation_mode == 'shared_pool':
            self.shared_pool_balance = new_balance
            self.logger.info(f"共享资金池余额更新为: ${new_balance:.2f}")
    
    def get_available_capital(self) -> float:
        """获取当前可用资金"""
        if self.fund_allocation_mode == 'shared_pool':
            return self.shared_pool_balance if not self.pool_lock else 0.0
        else:
            # 独立模式下返回所有策略的余额总和
            return sum(s.balance for s in self.strategies.values())
    
    def shutdown(self):
        """关闭管理器"""
        self.stop_all_strategies()
        self.executor.shutdown(wait=True)
        self.logger.info("策略管理器已关闭")