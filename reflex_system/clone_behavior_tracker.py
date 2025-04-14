
"""
Clone Behavior Tracker for SARYA.
Monitors clone actions and detects suspicious behavior patterns.
"""
import datetime
import logging
import time
from collections import defaultdict
from typing import Dict, List, Optional

from core.base_module import BaseModule
from reflex_system.reflex_signal_router import reflex_signal_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class CloneBehaviorTracker(BaseModule):
    """
    Tracks and analyzes clone behavior patterns.
    
    Features:
    - Action logging with timestamps
    - Pattern detection
    - Risk analysis
    - Reflex signal integration
    """
    
    HIGH_RISK_ACTIONS = {
        'override_safety',
        'loop_trade',
        'modify_core',
        'bypass_validation',
        'recursive_clone',
        'memory_override'
    }
    
    def __init__(self):
        super().__init__("CloneBehaviorTracker")
        self.clone_log: Dict[str, List[Dict]] = defaultdict(list)
        self.risk_thresholds = {
            'action_frequency': 10,  # actions per minute
            'high_risk_count': 3,    # high risk actions in 5 minutes
            'pattern_repeat': 4      # same action repeated
        }
    
    def log_action(
        self, 
        clone_id: str, 
        action_type: str, 
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Log a clone action.
        
        Args:
            clone_id: ID of the clone
            action_type: Type of action performed
            metadata: Optional additional data
        """
        action = {
            'timestamp': time.time(),
            'type': action_type,
            'metadata': metadata or {},
            'risk_level': 'high' if action_type in self.HIGH_RISK_ACTIONS else 'normal'
        }
        
        self.clone_log[clone_id].append(action)
        self.logger.info(f"Logged {action_type} action for clone {clone_id}")
        
        # Analyze after each high-risk action
        if action['risk_level'] == 'high':
            self.analyze_clone_behavior(clone_id)
    
    def analyze_clone_behavior(self, clone_id: str) -> Dict:
        """
        Analyze clone behavior patterns.
        
        Args:
            clone_id: ID of the clone to analyze
            
        Returns:
            Analysis results
        """
        if not self.clone_log[clone_id]:
            return {'status': 'no_data'}
            
        now = time.time()
        five_mins_ago = now - (5 * 60)
        
        # Get recent actions
        recent_actions = [
            action for action in self.clone_log[clone_id]
            if action['timestamp'] > five_mins_ago
        ]
        
        # Calculate metrics
        action_count = len(recent_actions)
        high_risk_count = sum(1 for a in recent_actions if a['risk_level'] == 'high')
        
        # Check action frequency
        actions_per_minute = action_count / 5.0
        
        # Check for repeated actions
        action_sequence = [a['type'] for a in recent_actions[-4:]]
        has_repeating_pattern = len(set(action_sequence)) == 1 and len(action_sequence) >= 3
        
        # Determine if behavior is suspicious
        is_suspicious = (
            actions_per_minute > self.risk_thresholds['action_frequency'] or
            high_risk_count >= self.risk_thresholds['high_risk_count'] or
            has_repeating_pattern
        )
        
        if is_suspicious:
            intensity = min(0.5 + (high_risk_count * 0.1), 0.9)
            
            reflex_signal_router.route_signal(
                "alert",
                {
                    "clone_id": clone_id,
                    "trigger": "clone_behavior_tracker",
                    "intensity": intensity,
                    "response": "monitor",
                    "data": {
                        "actions_per_minute": actions_per_minute,
                        "high_risk_count": high_risk_count,
                        "has_repeating_pattern": has_repeating_pattern
                    }
                }
            )
            
            self.logger.warning(
                f"Suspicious behavior detected for clone {clone_id}: "
                f"APM={actions_per_minute:.1f}, "
                f"high_risk={high_risk_count}"
            )
        
        return {
            'status': 'suspicious' if is_suspicious else 'normal',
            'metrics': {
                'actions_per_minute': actions_per_minute,
                'high_risk_count': high_risk_count,
                'has_repeating_pattern': has_repeating_pattern
            }
        }
    
    def get_clone_history(
        self, 
        clone_id: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get action history for a clone.
        
        Args:
            clone_id: ID of the clone
            limit: Maximum number of actions to return
            
        Returns:
            List of actions with timestamps
        """
        return list(reversed(self.clone_log[clone_id][-limit:]))
    
    def report_summary(self, clone_id: str) -> Dict:
        """
        Generate a behavior summary report.
        
        Args:
            clone_id: ID of the clone
            
        Returns:
            Summary report
        """
        if not self.clone_log[clone_id]:
            return {'status': 'no_data'}
            
        actions = self.clone_log[clone_id]
        
        # Count action types
        action_counts = defaultdict(int)
        for action in actions:
            action_counts[action['type']] += 1
        
        # Calculate risk score
        high_risk_ratio = sum(
            1 for a in actions 
            if a['risk_level'] == 'high'
        ) / len(actions)
        
        risk_score = min(high_risk_ratio * 100, 100)
        
        # Get last triggered reflex
        last_reflex = None
        for action in reversed(actions):
            if action['type'].startswith('reflex_'):
                last_reflex = action
                break
        
        return {
            'action_counts': dict(action_counts),
            'risk_score': risk_score,
            'last_reflex': last_reflex,
            'total_actions': len(actions),
            'high_risk_actions': sum(1 for a in actions if a['risk_level'] == 'high'),
            'first_action_time': datetime.datetime.fromtimestamp(actions[0]['timestamp']),
            'last_action_time': datetime.datetime.fromtimestamp(actions[-1]['timestamp'])
        }

# Create singleton instance
clone_behavior_tracker = CloneBehaviorTracker()

# Example usage
if __name__ == "__main__":
    tracker = CloneBehaviorTracker()
    
    # Log some test actions
    test_clone_id = "test_clone_001"
    
    tracker.log_action(test_clone_id, "start_process")
    time.sleep(0.1)
    
    tracker.log_action(
        test_clone_id, 
        "override_safety",
        {"target": "trade_limits"}
    )
    time.sleep(0.1)
    
    tracker.log_action(
        test_clone_id,
        "loop_trade",
        {"amount": 1000}
    )
    time.sleep(0.1)
    
    # Log repeated actions
    for _ in range(4):
        tracker.log_action(
            test_clone_id,
            "memory_override",
            {"section": "core_rules"}
        )
        time.sleep(0.1)
    
    # Get analysis
    analysis = tracker.analyze_clone_behavior(test_clone_id)
    print("\nBehavior Analysis:", analysis)
    
    # Get summary report
    summary = tracker.report_summary(test_clone_id)
    print("\nBehavior Summary:", summary)
