# position_coordinator.py - 持仓协调器
"""
持仓协调器
负责协调多个策略的持仓，避免冲突和过度风险

主要功能:
1. 持仓冲突检测和解决
2. 风险分配和限制
3. 资金使用优化
4. 策略间协调
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import threading

from strategies.base_strategy import BaseStrategy, Signal

class ConflictType(Enum):
    """冲突类型枚举"""
    SAME_DIRECTION = "same_direction"      # 同方向重复
    OPPOSITE_DIRECTION = "opposite_direction"  # 相反方向
    OVER_POSITION_LIMIT = "over_position_limit"  # 超出持仓限制
    INSUFFICIENT_FUNDS = "insufficient_funds"    # 资金不足
    RISK_EXCEEDED = "risk_exceeded"        # 风险超限

@dataclass
class PositionConflict:
    """持仓冲突数据类"""
    symbol: str
    conflict_type: ConflictType
    existing_signals: List[Signal]
    new_signal: Signal
    severity: float  # 冲突严重程度 0-1
    suggested_action: str
    
class PositionCoordinator:
    """持仓协调器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化持仓协调器
        
        Args:
            config: 协调器配置
        """
        self.config = config
        self.logger = logging.getLogger("PositionCoordinator")
        
        # 协调规则配置
        self.max_positions_per_symbol = config.get('max_positions_per_symbol', 1)
        self.allow_opposite_positions = config.get('allow_opposite_positions', False)
        self.max_total_positions = config.get('max_total_positions', 3)
        self.min_signal_interval = config.get('min_signal_interval', 300)  # 5分钟
        
        # 风险分配配置
        self.max_risk_per_symbol = config.get('max_risk_per_symbol', 0.02)  # 2%
        self.risk_scaling_factor = config.get('risk_scaling_factor', 0.8)   # 多策略风险衰减
        
        # 策略优先级配置
        self.strategy_priorities = config.get('strategy_priorities', {})
        self.default_priority = config.get('default_priority', 50)
        
        # 当前状态
        self.active_signals: Dict[str, List[Signal]] = {}  # symbol -> signals
        self.last_signal_time: Dict[str, datetime] = {}    # symbol -> last_time
        self.position_usage: Dict[str, float] = {}         # symbol -> usage_ratio
        
        # 协调统计
        self.coordination_stats = {
            'total_conflicts': 0,
            'resolved_conflicts': 0,
            'rejected_signals': 0,
            'modified_signals': 0
        }
        
        # 线程锁
        self._lock = threading.RLock()
        
        self.logger.info("持仓协调器初始化完成")
    
    def coordinate_signals(self, new_signals: List[Signal]) -> Tuple[List[Signal], List[PositionConflict]]:
        """
        协调交易信号
        
        Args:
            new_signals: 新的信号列表
            
        Returns:
            (approved_signals, conflicts): 批准的信号和冲突列表
        """
        with self._lock:
            approved_signals = []
            conflicts = []
            
            for signal in new_signals:
                try:
                    # 检查信号冲突
                    conflict = self._detect_conflicts(signal)
                    
                    if conflict:
                        conflicts.append(conflict)
                        
                        # 尝试解决冲突
                        resolved_signal = self._resolve_conflict(conflict)
                        
                        if resolved_signal:
                            approved_signals.append(resolved_signal)
                            self.coordination_stats['resolved_conflicts'] += 1
                        else:
                            self.coordination_stats['rejected_signals'] += 1
                            self.logger.warning(f"信号被拒绝: {signal.symbol} - {conflict.conflict_type.value}")
                        
                        self.coordination_stats['total_conflicts'] += 1
                    
                    else:
                        # 无冲突，直接批准
                        approved_signals.append(signal)
                    
                    # 记录信号
                    self._record_signal(signal)
                    
                except Exception as e:
                    self.logger.error(f"协调信号失败 {signal.symbol}: {e}")
            
            # 更新活跃信号列表
            self._update_active_signals(approved_signals)
            
            self.logger.info(f"信号协调完成 - 输入: {len(new_signals)}, 批准: {len(approved_signals)}, 冲突: {len(conflicts)}")
            
            return approved_signals, conflicts
    
    def _detect_conflicts(self, signal: Signal) -> Optional[PositionConflict]:
        """检测信号冲突"""
        symbol = signal.symbol
        existing_signals = self.active_signals.get(symbol, [])
        
        # 1. 检查同方向重复
        same_direction_signals = [
            s for s in existing_signals 
            if s.signal_type == signal.signal_type and s.strategy_id != signal.strategy_id
        ]
        
        if same_direction_signals:
            return PositionConflict(
                symbol=symbol,
                conflict_type=ConflictType.SAME_DIRECTION,
                existing_signals=same_direction_signals,
                new_signal=signal,
                severity=0.3,
                suggested_action="合并或选择最强信号"
            )
        
        # 2. 检查相反方向
        if not self.allow_opposite_positions:
            opposite_signals = [
                s for s in existing_signals 
                if s.signal_type != signal.signal_type
            ]
            
            if opposite_signals:
                return PositionConflict(
                    symbol=symbol,
                    conflict_type=ConflictType.OPPOSITE_DIRECTION,
                    existing_signals=opposite_signals,
                    new_signal=signal,
                    severity=0.7,
                    suggested_action="等待现有持仓平仓或取消新信号"
                )
        
        # 3. 检查持仓数量限制
        if len(existing_signals) >= self.max_positions_per_symbol:
            return PositionConflict(
                symbol=symbol,
                conflict_type=ConflictType.OVER_POSITION_LIMIT,
                existing_signals=existing_signals,
                new_signal=signal,
                severity=0.5,
                suggested_action="等待现有持仓平仓"
            )
        
        # 4. 检查总持仓限制
        total_positions = sum(len(signals) for signals in self.active_signals.values())
        if total_positions >= self.max_total_positions:
            return PositionConflict(
                symbol=symbol,
                conflict_type=ConflictType.OVER_POSITION_LIMIT,
                existing_signals=[],
                new_signal=signal,
                severity=0.6,
                suggested_action="等待其他持仓平仓"
            )
        
        # 5. 检查信号时间间隔
        last_time = self.last_signal_time.get(symbol)
        if last_time:
            interval = (signal.timestamp - last_time).total_seconds()
            if interval < self.min_signal_interval:
                return PositionConflict(
                    symbol=symbol,
                    conflict_type=ConflictType.SAME_DIRECTION,
                    existing_signals=existing_signals,
                    new_signal=signal,
                    severity=0.2,
                    suggested_action=f"等待 {self.min_signal_interval - interval:.0f} 秒"
                )
        
        return None
    
    def _resolve_conflict(self, conflict: PositionConflict) -> Optional[Signal]:
        """解决信号冲突"""
        try:
            if conflict.conflict_type == ConflictType.SAME_DIRECTION:
                # 同方向信号：选择最强的或合并
                return self._resolve_same_direction_conflict(conflict)
            
            elif conflict.conflict_type == ConflictType.OPPOSITE_DIRECTION:
                # 相反方向：根据策略优先级决定
                return self._resolve_opposite_direction_conflict(conflict)
            
            elif conflict.conflict_type == ConflictType.OVER_POSITION_LIMIT:
                # 超出限制：选择最强信号替换最弱信号
                return self._resolve_position_limit_conflict(conflict)
            
            else:
                # 其他冲突类型暂时拒绝
                return None
                
        except Exception as e:
            self.logger.error(f"解决冲突失败: {e}")
            return None
    
    def _resolve_same_direction_conflict(self, conflict: PositionConflict) -> Optional[Signal]:
        """解决同方向冲突"""
        all_signals = conflict.existing_signals + [conflict.new_signal]
        
        # 按信号强度排序
        all_signals.sort(key=lambda s: s.strength, reverse=True)
        
        # 选择最强信号
        strongest_signal = all_signals[0]
        
        # 如果新信号不是最强的，考虑合并
        if strongest_signal != conflict.new_signal:
            # 可以实现信号合并逻辑，比如调整仓位大小
            return self._merge_signals(all_signals)
        
        return strongest_signal
    
    def _resolve_opposite_direction_conflict(self, conflict: PositionConflict) -> Optional[Signal]:
        """解决相反方向冲突"""
        # 获取策略优先级
        new_priority = self._get_strategy_priority(conflict.new_signal.strategy_id)
        
        for existing_signal in conflict.existing_signals:
            existing_priority = self._get_strategy_priority(existing_signal.strategy_id)
            
            # 如果新信号优先级更高，批准新信号（这将导致现有持仓被平仓）
            if new_priority > existing_priority:
                self.logger.info(f"高优先级策略信号批准: {conflict.new_signal.strategy_id} > {existing_signal.strategy_id}")
                return conflict.new_signal
        
        # 新信号优先级不够高，拒绝
        return None
    
    def _resolve_position_limit_conflict(self, conflict: PositionConflict) -> Optional[Signal]:
        """解决持仓限制冲突"""
        if not conflict.existing_signals:
            # 总持仓限制，暂时拒绝
            return None
        
        # 找到最弱的现有信号
        weakest_signal = min(conflict.existing_signals, key=lambda s: s.strength)
        
        # 如果新信号更强，替换最弱信号
        if conflict.new_signal.strength > weakest_signal.strength:
            self.logger.info(f"替换弱信号: {weakest_signal.strategy_id} -> {conflict.new_signal.strategy_id}")
            
            # 从活跃信号中移除最弱信号
            symbol_signals = self.active_signals.get(conflict.symbol, [])
            if weakest_signal in symbol_signals:
                symbol_signals.remove(weakest_signal)
            
            return conflict.new_signal
        
        return None
    
    def _merge_signals(self, signals: List[Signal]) -> Signal:
        """合并多个同方向信号"""
        if not signals:
            return None
        
        # 以最强信号为基础
        base_signal = max(signals, key=lambda s: s.strength)
        merged_signal = Signal(
            strategy_id=f"merged_{base_signal.strategy_id}",
            symbol=base_signal.symbol,
            signal_type=base_signal.signal_type,
            strength=min(1.0, sum(s.strength for s in signals) / len(signals) * 1.2),  # 合并强度加权
            timestamp=base_signal.timestamp,
            entry_price=sum(s.entry_price * s.strength for s in signals) / sum(s.strength for s in signals),
            stop_loss=base_signal.stop_loss,
            take_profit=base_signal.take_profit,
            metadata={
                'merged_from': [s.strategy_id for s in signals],
                'original_strengths': [s.strength for s in signals]
            }
        )
        
        self.coordination_stats['modified_signals'] += 1
        return merged_signal
    
    def _get_strategy_priority(self, strategy_id: str) -> int:
        """获取策略优先级"""
        return self.strategy_priorities.get(strategy_id, self.default_priority)
    
    def _record_signal(self, signal: Signal):
        """记录信号"""
        self.last_signal_time[signal.symbol] = signal.timestamp
    
    def _update_active_signals(self, approved_signals: List[Signal]):
        """更新活跃信号列表"""
        for signal in approved_signals:
            if signal.symbol not in self.active_signals:
                self.active_signals[signal.symbol] = []
            self.active_signals[signal.symbol].append(signal)
    
    def remove_signal(self, symbol: str, strategy_id: str = None):
        """移除信号（当持仓平仓时调用）"""
        with self._lock:
            if symbol in self.active_signals:
                if strategy_id:
                    # 移除特定策略的信号
                    self.active_signals[symbol] = [
                        s for s in self.active_signals[symbol] 
                        if s.strategy_id != strategy_id
                    ]
                else:
                    # 移除该品种的所有信号
                    del self.active_signals[symbol]
                
                # 清理空列表
                if symbol in self.active_signals and not self.active_signals[symbol]:
                    del self.active_signals[symbol]
    
    def calculate_adjusted_position_size(self, 
                                       signal: Signal, 
                                       original_size: float,
                                       total_balance: float) -> float:
        """
        计算调整后的仓位大小
        
        考虑多策略风险分配
        """
        symbol = signal.symbol
        
        # 检查该品种现有风险
        existing_risk = self._calculate_symbol_risk(symbol, total_balance)
        
        # 计算新信号的基础风险
        base_risk = original_size / total_balance
        
        # 多策略风险衰减
        adjusted_risk = base_risk * self.risk_scaling_factor
        
        # 检查品种风险限制
        total_symbol_risk = existing_risk + adjusted_risk
        if total_symbol_risk > self.max_risk_per_symbol:
            # 调整风险到允许范围内
            allowed_additional_risk = self.max_risk_per_symbol - existing_risk
            if allowed_additional_risk > 0:
                adjusted_risk = allowed_additional_risk
            else:
                adjusted_risk = 0  # 无法增加更多风险
        
        # 转换回仓位大小
        adjusted_size = adjusted_risk * total_balance
        
        self.logger.debug(f"仓位调整 {symbol}: {original_size:.2f} -> {adjusted_size:.2f}")
        
        return adjusted_size
    
    def _calculate_symbol_risk(self, symbol: str, total_balance: float) -> float:
        """计算品种当前风险"""
        existing_signals = self.active_signals.get(symbol, [])
        total_risk = 0.0
        
        for signal in existing_signals:
            if signal.position_size:
                risk = signal.position_size / total_balance
                total_risk += risk
        
        return total_risk
    
    def get_coordination_status(self) -> Dict[str, Any]:
        """获取协调状态"""
        with self._lock:
            return {
                'active_signals': {
                    symbol: len(signals) 
                    for symbol, signals in self.active_signals.items()
                },
                'total_active_positions': sum(len(signals) for signals in self.active_signals.values()),
                'position_limits': {
                    'per_symbol': self.max_positions_per_symbol,
                    'total': self.max_total_positions
                },
                'statistics': self.coordination_stats.copy(),
                'last_signal_times': {
                    symbol: time.isoformat() 
                    for symbol, time in self.last_signal_time.items()
                }
            }
    
    def reset_statistics(self):
        """重置统计信息"""
        with self._lock:
            self.coordination_stats = {
                'total_conflicts': 0,
                'resolved_conflicts': 0,
                'rejected_signals': 0,
                'modified_signals': 0
            }
            self.logger.info("协调统计已重置")
    
    def update_strategy_priority(self, strategy_id: str, priority: int):
        """更新策略优先级"""
        with self._lock:
            self.strategy_priorities[strategy_id] = priority
            self.logger.info(f"更新策略优先级: {strategy_id} = {priority}")
    
    def cleanup_expired_signals(self, expiry_hours: int = 24):
        """清理过期信号"""
        with self._lock:
            current_time = datetime.now()
            cleaned_count = 0
            
            for symbol in list(self.active_signals.keys()):
                signals_before = len(self.active_signals[symbol])
                
                self.active_signals[symbol] = [
                    s for s in self.active_signals[symbol]
                    if (current_time - s.timestamp).total_seconds() < expiry_hours * 3600
                ]
                
                signals_after = len(self.active_signals[symbol])
                cleaned_count += signals_before - signals_after
                
                # 清理空列表
                if not self.active_signals[symbol]:
                    del self.active_signals[symbol]
            
            if cleaned_count > 0:
                self.logger.info(f"清理过期信号: {cleaned_count} 个")
            
            return cleaned_count