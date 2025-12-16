"""
Alert Manager
Manages user-defined alerts and triggers
"""

import uuid
import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class AlertManager:
    def __init__(self):
        self.alerts = {}
        self.triggered_history = []
        
    def add_alert(self, symbol: str, metric: str, condition: str, threshold: float, message: str = '') -> str:
        """
        Add a new alert
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            metric: Metric to monitor (e.g., 'price', 'zscore', 'volume')
            condition: Condition ('>', '<', '>=', '<=', '==')
            threshold: Threshold value
            message: Custom alert message
        """
        alert_id = str(uuid.uuid4())
        
        alert = {
            'id': alert_id,
            'symbol': symbol,
            'metric': metric,
            'condition': condition,
            'threshold': threshold,
            'message': message or f"{symbol} {metric} {condition} {threshold}",
            'created_at': datetime.now().isoformat(),
            'active': True,
            'trigger_count': 0
        }
        
        self.alerts[alert_id] = alert
        logger.info(f"Alert created: {alert_id} - {alert['message']}")
        
        return alert_id
    
    def remove_alert(self, alert_id: str):
        """Remove an alert"""
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            logger.info(f"Alert removed: {alert_id}")
    
    def get_all_alerts(self) -> List[Dict]:
        """Get all active alerts"""
        return list(self.alerts.values())
    
    def check_tick(self, tick: Dict) -> List[Dict]:
        """
        Check if any alerts are triggered by this tick
        
        Args:
            tick: Tick data with timestamp, symbol, price, quantity
        
        Returns:
            List of triggered alerts
        """
        triggered = []
        
        for alert_id, alert in self.alerts.items():
            if not alert['active']:
                continue
                
            if alert['symbol'] != tick['symbol']:
                continue
            
            # Get the metric value from tick
            if alert['metric'] == 'price':
                value = tick['price']
            elif alert['metric'] == 'volume' or alert['metric'] == 'quantity':
                value = tick['quantity']
            else:
                continue  # Metric not available in tick data
            
            # Check condition
            if self._evaluate_condition(value, alert['condition'], alert['threshold']):
                alert['trigger_count'] += 1
                alert['last_triggered'] = datetime.now().isoformat()
                
                triggered_alert = {
                    'alert_id': alert_id,
                    'message': alert['message'],
                    'symbol': alert['symbol'],
                    'metric': alert['metric'],
                    'value': value,
                    'threshold': alert['threshold'],
                    'timestamp': tick['timestamp'].isoformat() if hasattr(tick['timestamp'], 'isoformat') else str(tick['timestamp'])
                }
                
                triggered.append(triggered_alert)
                self.triggered_history.append(triggered_alert)
                
                # Keep history limited
                if len(self.triggered_history) > 100:
                    self.triggered_history = self.triggered_history[-100:]
        
        return triggered
    
    def check_analytics(self, analytics: Dict) -> List[Dict]:
        """
        Check if any alerts are triggered by analytics data
        
        Args:
            analytics: Analytics data dictionary
        
        Returns:
            List of triggered alerts
        """
        triggered = []
        
        for alert_id, alert in self.alerts.items():
            if not alert['active']:
                continue
            
            symbol = analytics.get('symbol')
            if alert['symbol'] != symbol:
                continue
            
            # Extract metric value from analytics
            value = None
            if alert['metric'] == 'zscore':
                value = analytics.get('statistics', {}).get('zscore')
            elif alert['metric'] == 'rsi':
                value = analytics.get('statistics', {}).get('rsi')
            elif alert['metric'] == 'volatility':
                value = analytics.get('statistics', {}).get('volatility')
            elif alert['metric'] == 'price':
                value = analytics.get('price', {}).get('current')
            
            if value is None:
                continue
            
            # Check condition
            if self._evaluate_condition(value, alert['condition'], alert['threshold']):
                alert['trigger_count'] += 1
                alert['last_triggered'] = datetime.now().isoformat()
                
                triggered_alert = {
                    'alert_id': alert_id,
                    'message': alert['message'],
                    'symbol': alert['symbol'],
                    'metric': alert['metric'],
                    'value': value,
                    'threshold': alert['threshold'],
                    'timestamp': datetime.now().isoformat()
                }
                
                triggered.append(triggered_alert)
                self.triggered_history.append(triggered_alert)
                
                if len(self.triggered_history) > 100:
                    self.triggered_history = self.triggered_history[-100:]
        
        return triggered
    
    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Evaluate if a condition is met"""
        try:
            if condition == '>':
                return value > threshold
            elif condition == '<':
                return value < threshold
            elif condition == '>=':
                return value >= threshold
            elif condition == '<=':
                return value <= threshold
            elif condition == '==':
                return abs(value - threshold) < 0.0001  # Float comparison
            else:
                return False
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False
    
    def get_triggered_history(self, limit: int = 50) -> List[Dict]:
        """Get recent triggered alerts"""
        return self.triggered_history[-limit:]
    
    def clear_history(self):
        """Clear triggered alert history"""
        self.triggered_history = []
        logger.info("Alert history cleared")