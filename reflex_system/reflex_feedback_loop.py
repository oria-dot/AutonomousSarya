
"""
Reflex Feedback Loop Engine for SARYA.
Analyzes reflex patterns and provides reinforcement or suppression commands.
"""
import logging
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from core.base_module import BaseModule
from reflex_system.reflex_signal_router import reflex_signal_router
from reflex_system.reflex_storage_sync import ReflexStorageSync

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class ReflexFeedbackLoop(BaseModule):
    """
    Processes reflex signals to identify patterns and manage feedback responses.
    
    Features:
    - Pattern detection in recent signals
    - Loop and instability detection
    - Reinforcement and suppression signals
    - Automated feedback response
    """
    
    def __init__(self):
        super().__init__("ReflexFeedbackLoop")
        self.storage_sync = ReflexStorageSync()
        self.pattern_memory: Dict[str, List[Dict]] = defaultdict(list)
        self.last_scan = time.time()
        self.scan_interval = 30  # seconds
        
        # Thresholds for pattern detection
        self.thresholds = {
            'signal_frequency': 10,    # signals per minute
            'repeat_threshold': 3,     # identical signals to detect loop
            'intensity_spike': 0.7,    # sudden intensity increase
            'cooldown_period': 300     # seconds between reinforcements
        }
    
    def process_recent_signals(self, time_window: int = 300) -> List[Dict]:
        """
        Analyze signals from recent time window.
        
        Args:
            time_window: Time window in seconds (default 5 minutes)
            
        Returns:
            List of detected patterns
        """
        now = time.time()
        if now - self.last_scan < self.scan_interval:
            return []
            
        self.last_scan = now
        window_start = now - time_window
        
        # Get recent signals
        recent_signals = [
            signal for signal in self.storage_sync.load_log()
            if signal['timestamp'] > window_start
        ]
        
        patterns = []
        
        # Group by clone
        clone_signals = defaultdict(list)
        for signal in recent_signals:
            clone_id = signal.get('clone_id')
            if clone_id:
                clone_signals[clone_id].append(signal)
        
        # Analyze each clone's signals
        for clone_id, signals in clone_signals.items():
            loop_detected = self.detect_loop_or_instability(signals)
            if loop_detected:
                patterns.append({
                    'type': 'loop',
                    'clone_id': clone_id,
                    'signals': signals,
                    'detected_at': now
                })
                
            # Check signal frequency
            signals_per_minute = len(signals) / (time_window / 60)
            if signals_per_minute > self.thresholds['signal_frequency']:
                patterns.append({
                    'type': 'high_frequency',
                    'clone_id': clone_id,
                    'frequency': signals_per_minute,
                    'detected_at': now
                })
                
        return patterns
    
    def detect_loop_or_instability(
        self, 
        signals: List[Dict]
    ) -> Tuple[bool, Optional[str]]:
        """
        Look for repeated reflexes or unstable patterns.
        
        Args:
            signals: List of reflex signals to analyze
            
        Returns:
            Tuple of (is_unstable, reason)
        """
        if not signals:
            return False, None
            
        # Check for repeated signal types
        signal_types = [s['type'] for s in signals[-3:]]
        if len(signal_types) >= 3:
            if len(set(signal_types)) == 1:
                return True, 'repeated_signals'
        
        # Check for intensity spikes
        intensities = [s.get('intensity', 0) for s in signals[-3:]]
        if len(intensities) >= 2:
            if any(
                b - a > self.thresholds['intensity_spike']
                for a, b in zip(intensities, intensities[1:])
            ):
                return True, 'intensity_spike'
        
        # Check for rapid alternating patterns
        if len(signals) >= 4:
            last_four = signals[-4:]
            types = [s['type'] for s in last_four]
            if types[0] == types[2] and types[1] == types[3]:
                return True, 'alternating_pattern'
                
        return False, None
    
    def trigger_response(
        self, 
        pattern_type: str,
        clone_id: str,
        data: Optional[Dict] = None
    ) -> bool:
        """
        Send appropriate response signal based on pattern type.
        
        Args:
            pattern_type: Type of pattern detected
            clone_id: ID of the clone involved
            data: Optional additional data
            
        Returns:
            bool: True if response was triggered
        """
        response_map = {
            'loop': ('cooldown', 0.8),
            'high_frequency': ('alert', 0.6),
            'intensity_spike': ('suppress', 0.7),
            'alternating_pattern': ('stabilize', 0.5)
        }
        
        if pattern_type not in response_map:
            return False
            
        reflex_type, intensity = response_map[pattern_type]
        
        signal_data = {
            'clone_id': clone_id,
            'trigger': 'feedback_loop',
            'pattern_type': pattern_type,
            'intensity': intensity,
            'data': data or {}
        }
        
        # Route response signal
        return reflex_signal_router.route_signal(reflex_type, signal_data)
    
    def run_feedback_cycle(self) -> None:
        """Run a complete feedback analysis cycle."""
        try:
            patterns = self.process_recent_signals()
            
            for pattern in patterns:
                clone_id = pattern['clone_id']
                pattern_type = pattern['type']
                
                # Trigger appropriate response
                success = self.trigger_response(
                    pattern_type,
                    clone_id,
                    {'detected_at': pattern['detected_at']}
                )
                
                if success:
                    self.logger.info(
                        f"Triggered {pattern_type} response for clone {clone_id}"
                    )
                else:
                    self.logger.warning(
                        f"Failed to trigger response for pattern {pattern_type}"
                    )
                    
        except Exception as e:
            self.logger.error(f"Error in feedback cycle: {str(e)}")

# Create singleton instance
reflex_feedback_loop = ReflexFeedbackLoop()

# Example usage
if __name__ == "__main__":
    feedback_loop = ReflexFeedbackLoop()
    
    # Simulate some reflex signals
    test_signals = [
        {
            'type': 'emotional',
            'clone_id': 'test_clone_001',
            'intensity': 0.5,
            'timestamp': time.time() - 240
        },
        {
            'type': 'emotional',
            'clone_id': 'test_clone_001', 
            'intensity': 0.6,
            'timestamp': time.time() - 180
        },
        {
            'type': 'emotional',
            'clone_id': 'test_clone_001',
            'intensity': 0.8,
            'timestamp': time.time() - 120
        }
    ]
    
    # Process signals
    patterns = feedback_loop.process_recent_signals()
    print("\nDetected patterns:", patterns)
    
    # Test loop detection
    is_unstable, reason = feedback_loop.detect_loop_or_instability(test_signals)
    print("\nInstability check:", is_unstable, reason)
    
    # Trigger test response
    success = feedback_loop.trigger_response(
        'loop',
        'test_clone_001',
        {'test': True}
    )
    print("\nResponse triggered:", success)
