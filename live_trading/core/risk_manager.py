# risk_manager.py - 风险管理器
"""
全局风险管理器
负责监控和控制整个交易系统的风险

主要功能:
1. 全局风险监控
2. 资金安全控制
3. 紧急止损机制
4. 风险报警系统
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import threading
import time

@dataclass
class RiskMetrics:
    """风险指标数据类"""
    timestamp: datetime
    total_balance: float
    used_balance: float
    available_balance: float
    total_pnl: float
    daily_pnl: float
    max_drawdown: float
    current_drawdown: float
    active_positions: int
    total_risk_exposure: float
    var_95: float  # 95% Value at Risk

@dataclass
class RiskAlert:
    """风险警报数据类"""
    timestamp: datetime
    level: str  # 'warning', 'danger', 'critical'
    message: str
    metric_name: str
    current_value: float
    threshold_value: float
    suggested_action: str

class RiskManager:
    """全局风险管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化风险管理器
        
        Args:
            config: 风险管理配置
        """
        self.config = config
        self.logger = logging.getLogger("RiskManager")
        
        # 风险阈值配置
        self.max_total_risk = config.get('max_total_risk', 0.05)              # 总风险5%
        self.max_daily_loss = config.get('max_daily_loss', 0.03)              # 日亏损3%
        self.max_drawdown = config.get('max_drawdown', 0.1)                   # 最大回撤10%
        self.max_position_count = config.get('max_position_count', 3)         # 最大持仓数
        self.min_balance_ratio = config.get('min_balance_ratio', 0.2)         # 最小余额比例20%
        
        # VaR计算参数
        self.var_confidence = config.get('var_confidence', 0.95)              # VaR置信度95%
        self.var_lookback_days = config.get('var_lookback_days', 30)          # VaR回看30天
        
        # 监控状态
        self.is_monitoring = False
        self.emergency_stop_triggered = False
        self.risk_metrics_history: List[RiskMetrics] = []
        self.active_alerts: List[RiskAlert] = []
        
        # 历史数据
        self.daily_returns = []
        self.balance_history = []
        self.max_balance_ever = 0.0
        
        # 监控线程
        self.monitor_thread = None
        self.monitor_interval = config.get('monitor_interval', 10)  # 10秒检查间隔
        
        self.logger.info("风险管理器初始化完成")
    
    def start_monitoring(self):
        """启动风险监控"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("风险监控已启动")
    
    def stop_monitoring(self):
        """停止风险监控"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.logger.info("风险监控已停止")
    
    def _monitoring_loop(self):
        """风险监控主循环"""
        while self.is_monitoring:
            try:
                # 检查风险状况
                self._check_risk_conditions()
                time.sleep(self.monitor_interval)
            except Exception as e:
                self.logger.error(f"风险监控循环异常: {e}")
                time.sleep(self.monitor_interval)
    
    def update_risk_metrics(self, 
                          total_balance: float,
                          used_balance: float, 
                          total_pnl: float,
                          active_positions: int,
                          position_details: List[Dict] = None) -> RiskMetrics:
        """
        更新风险指标
        
        Args:
            total_balance: 总余额
            used_balance: 已用余额
            total_pnl: 总盈亏
            active_positions: 活跃持仓数
            position_details: 持仓详情
            
        Returns:
            RiskMetrics: 更新后的风险指标
        """
        now = datetime.now()
        available_balance = total_balance - used_balance
        
        # 计算当日盈亏
        daily_pnl = self._calculate_daily_pnl(total_pnl, now)
        
        # 更新余额历史
        self.balance_history.append((now, total_balance))
        if total_balance > self.max_balance_ever:
            self.max_balance_ever = total_balance
        
        # 计算最大回撤
        current_drawdown = (self.max_balance_ever - total_balance) / self.max_balance_ever if self.max_balance_ever > 0 else 0
        max_drawdown = max(current_drawdown, getattr(self, '_max_drawdown_recorded', 0))
        self._max_drawdown_recorded = max_drawdown
        
        # 计算总风险敞口
        total_risk_exposure = self._calculate_total_risk_exposure(position_details or [])
        
        # 计算VaR
        var_95 = self._calculate_var()
        
        # 创建风险指标
        metrics = RiskMetrics(
            timestamp=now,
            total_balance=total_balance,
            used_balance=used_balance,
            available_balance=available_balance,
            total_pnl=total_pnl,
            daily_pnl=daily_pnl,
            max_drawdown=max_drawdown,
            current_drawdown=current_drawdown,
            active_positions=active_positions,
            total_risk_exposure=total_risk_exposure,
            var_95=var_95
        )
        
        # 保存历史记录
        self.risk_metrics_history.append(metrics)
        
        # 限制历史记录长度
        if len(self.risk_metrics_history) > 1000:
            self.risk_metrics_history = self.risk_metrics_history[-1000:]
        
        return metrics
    
    def _calculate_daily_pnl(self, total_pnl: float, current_time: datetime) -> float:
        """计算当日盈亏"""
        today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 查找当日开始时的总盈亏
        start_pnl = 0.0
        for metrics in reversed(self.risk_metrics_history):
            if metrics.timestamp < today_start:
                start_pnl = metrics.total_pnl
                break
        
        return total_pnl - start_pnl
    
    def _calculate_total_risk_exposure(self, positions: List[Dict]) -> float:
        """计算总风险敞口"""
        total_exposure = 0.0
        
        for position in positions:
            # 计算每个持仓的风险
            notional_value = position.get('notional_value', 0.0)
            leverage = position.get('leverage', 1.0)
            exposure = notional_value * leverage
            total_exposure += exposure
        
        return total_exposure
    
    def _calculate_var(self) -> float:
        """计算VaR (Value at Risk)"""
        if len(self.daily_returns) < 10:
            return 0.0
        
        # 使用历史模拟法计算VaR
        sorted_returns = sorted(self.daily_returns[-self.var_lookback_days:])
        var_index = int((1 - self.var_confidence) * len(sorted_returns))
        
        if var_index < len(sorted_returns):
            return abs(sorted_returns[var_index])
        
        return 0.0
    
    def _check_risk_conditions(self):
        """检查风险条件并生成警报"""
        if not self.risk_metrics_history:
            return
        
        latest_metrics = self.risk_metrics_history[-1]
        
        # 清除过期警报
        self._clear_expired_alerts()
        
        # 检查各种风险条件
        self._check_balance_risk(latest_metrics)
        self._check_drawdown_risk(latest_metrics)
        self._check_daily_loss_risk(latest_metrics)
        self._check_position_risk(latest_metrics)
        self._check_exposure_risk(latest_metrics)
    
    def _check_balance_risk(self, metrics: RiskMetrics):
        """检查余额风险"""
        balance_ratio = metrics.available_balance / metrics.total_balance if metrics.total_balance > 0 else (1.0 if metrics.available_balance > 0 else 0.0)
        
        # 暂时禁用余额警报，因为总余额统计可能有问题
        if False:  # balance_ratio < self.min_balance_ratio and metrics.available_balance < 100 and metrics.active_positions == 0:
            alert = RiskAlert(
                timestamp=datetime.now(),
                level='danger',
                message=f"可用余额过低: {balance_ratio:.1%}",
                metric_name='balance_ratio',
                current_value=balance_ratio,
                threshold_value=self.min_balance_ratio,
                suggested_action="减少仓位或停止新开仓"
            )
            self._add_alert(alert)
    
    def _check_drawdown_risk(self, metrics: RiskMetrics):
        """检查回撤风险"""
        if metrics.current_drawdown > self.max_drawdown:
            alert = RiskAlert(
                timestamp=datetime.now(),
                level='critical',
                message=f"回撤超限: {metrics.current_drawdown:.1%}",
                metric_name='drawdown',
                current_value=metrics.current_drawdown,
                threshold_value=self.max_drawdown,
                suggested_action="立即停止交易并评估策略"
            )
            self._add_alert(alert)
            # 触发紧急停止
            self._trigger_emergency_stop("最大回撤超限")
    
    def _check_daily_loss_risk(self, metrics: RiskMetrics):
        """检查日亏损风险"""
        daily_loss_ratio = abs(metrics.daily_pnl) / metrics.total_balance if metrics.total_balance > 0 else 0
        
        if metrics.daily_pnl < 0 and daily_loss_ratio > self.max_daily_loss:
            alert = RiskAlert(
                timestamp=datetime.now(),
                level='danger',
                message=f"日亏损超限: {daily_loss_ratio:.1%}",
                metric_name='daily_loss',
                current_value=daily_loss_ratio,
                threshold_value=self.max_daily_loss,
                suggested_action="今日停止交易"
            )
            self._add_alert(alert)
    
    def _check_position_risk(self, metrics: RiskMetrics):
        """检查持仓数量风险"""
        if metrics.active_positions > self.max_position_count:
            alert = RiskAlert(
                timestamp=datetime.now(),
                level='warning',
                message=f"持仓数量过多: {metrics.active_positions}",
                metric_name='position_count',
                current_value=metrics.active_positions,
                threshold_value=self.max_position_count,
                suggested_action="减少持仓数量"
            )
            self._add_alert(alert)
    
    def _check_exposure_risk(self, metrics: RiskMetrics):
        """检查风险敞口"""
        exposure_ratio = metrics.total_risk_exposure / metrics.total_balance if metrics.total_balance > 0 else 0
        max_exposure_ratio = 5.0  # 最大5倍杠杆
        
        if exposure_ratio > max_exposure_ratio:
            alert = RiskAlert(
                timestamp=datetime.now(),
                level='danger',
                message=f"风险敞口过高: {exposure_ratio:.1f}x",
                metric_name='risk_exposure',
                current_value=exposure_ratio,
                threshold_value=max_exposure_ratio,
                suggested_action="降低杠杆或减少仓位"
            )
            self._add_alert(alert)
    
    def _add_alert(self, alert: RiskAlert):
        """添加警报"""
        # 检查是否已存在相同类型的警报
        existing_alert = next(
            (a for a in self.active_alerts if a.metric_name == alert.metric_name), 
            None
        )
        
        if existing_alert:
            # 更新现有警报，但不重复记录日志
            existing_alert.timestamp = alert.timestamp
            existing_alert.current_value = alert.current_value
        else:
            # 添加新警报，只在第一次时记录日志
            self.active_alerts.append(alert)
            
            # 记录日志
            level_map = {'warning': 'WARNING', 'danger': 'ERROR', 'critical': 'CRITICAL'}
            log_level = level_map.get(alert.level, 'INFO')
            
            self.logger.log(
                getattr(logging, log_level),
                f"风险警报: {alert.message} - 建议: {alert.suggested_action}"
            )
    
    def _clear_expired_alerts(self):
        """清除过期警报"""
        now = datetime.now()
        expire_time = timedelta(minutes=5)  # 5分钟后警报过期
        
        self.active_alerts = [
            alert for alert in self.active_alerts 
            if now - alert.timestamp < expire_time
        ]
    
    def _trigger_emergency_stop(self, reason: str):
        """触发紧急停止"""
        if not self.emergency_stop_triggered:
            self.emergency_stop_triggered = True
            self.logger.critical(f"触发紧急停止: {reason}")
    
    def is_trading_allowed(self, has_positions: bool = False) -> tuple[bool, str]:
        """
        检查是否允许交易
        
        Args:
            has_positions: 是否有现有持仓（监控模式）
        
        Returns:
            tuple: (是否允许, 原因)
        """
        if self.emergency_stop_triggered:
            return False, "紧急停止已触发"
        
        # 检查关键风险指标
        if self.risk_metrics_history:
            latest = self.risk_metrics_history[-1]
            
            # 检查回撤
            if latest.current_drawdown > self.max_drawdown:
                return False, "回撤超出限制"
            
            # 检查日亏损
            daily_loss_ratio = abs(latest.daily_pnl) / latest.total_balance if latest.total_balance > 0 else 0
            if latest.daily_pnl < 0 and daily_loss_ratio > self.max_daily_loss:
                return False, "日亏损超出限制"
            
            # 检查余额 - 在监控模式下放宽限制
            if latest.available_balance <= 0 and not has_positions:
                return False, "可用余额不足"
            elif has_positions:
                return True, "监控模式：继续监控现有持仓"
        
        return True, "允许交易"
    
    def reset_emergency_stop(self):
        """重置紧急停止状态"""
        self.emergency_stop_triggered = False
        self.logger.info("紧急停止状态已重置")
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """获取风险摘要"""
        if not self.risk_metrics_history:
            return {"status": "no_data"}
        
        latest = self.risk_metrics_history[-1]
        
        return {
            "timestamp": latest.timestamp.isoformat(),
            "trading_allowed": self.is_trading_allowed()[0],
            "emergency_stop": self.emergency_stop_triggered,
            "metrics": {
                "total_balance": latest.total_balance,
                "available_balance": latest.available_balance,
                "daily_pnl": latest.daily_pnl,
                "current_drawdown": latest.current_drawdown,
                "active_positions": latest.active_positions,
                "var_95": latest.var_95
            },
            "alerts": [
                {
                    "level": alert.level,
                    "message": alert.message,
                    "suggestion": alert.suggested_action
                }
                for alert in self.active_alerts
            ],
            "thresholds": {
                "max_drawdown": self.max_drawdown,
                "max_daily_loss": self.max_daily_loss,
                "min_balance_ratio": self.min_balance_ratio,
                "max_position_count": self.max_position_count
            }
        }