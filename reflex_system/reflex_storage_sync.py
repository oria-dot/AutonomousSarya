
"""
Reflex Storage Sync for SARYA.
Stores and analyzes reflex signals for behavioral patterns.
"""
import datetime
import json
import logging
import os
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class ReflexStorageSync:
    """
    Stores and analyzes reflex signals.
    
    Features:
    - Signal storage with timestamps
    - Behavioral analysis
    - Automated feedback
    - Clone-specific analysis
    """
    
    def __init__(self, log_file_path: str = "data/reflex_log.json"):
        self.log_file_path = log_file_path
        self.reflex_cache: List[Dict] = []
        self.logger = logging.getLogger("ReflexStorageSync")
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
        
        # Load existing logs
        self.load_log()
        
    def store_signal(self, reflex_data: Dict) -> bool:
        """
        Store a reflex signal with timestamp.
        
        Args:
            reflex_data: Signal data including type, trigger, etc.
            
        Returns:
            bool: True if storage was successful
        """
        try:
            # Add timestamp
            signal = {
                **reflex_data,
                "timestamp": datetime.datetime.utcnow().timestamp()
            }
            
            # Ensure required fields
            required_fields = ["type", "trigger", "response", "intensity"]
            for field in required_fields:
                if field not in signal:
                    self.logger.error(f"Missing required field: {field}")
                    return False
            
            # Add to cache
            self.reflex_cache.append(signal)
            
            # Save to file
            with open(self.log_file_path, 'w') as f:
                json.dump({"signals": self.reflex_cache}, f, indent=2)
                
            # Check for critical signals
            self.auto_feedback(signal)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing signal: {str(e)}")
            return False
    
    def load_log(self) -> List[Dict]:
        """
        Load reflex logs from file.
        
        Returns:
            List of stored reflex signals
        """
        try:
            if os.path.exists(self.log_file_path):
                with open(self.log_file_path, 'r') as f:
                    data = json.load(f)
                    self.reflex_cache = data.get("signals", [])
                self.logger.info(f"Loaded {len(self.reflex_cache)} signals")
            return self.reflex_cache
        except Exception as e:
            self.logger.error(f"Error loading logs: {str(e)}")
            return []
    
    def analyze_behavior(self, clone_id: Optional[str] = None) -> Dict:
        """
        Analyze reflex behavior patterns.
        
        Args:
            clone_id: Optional clone ID to filter analysis
            
        Returns:
            Analysis summary
        """
        now = datetime.datetime.utcnow().timestamp()
        five_mins_ago = now - (5 * 60)
        
        # Filter signals
        signals = self.reflex_cache
        if clone_id:
            signals = [s for s in signals if s.get("clone_id") == clone_id]
        
        # Recent high-intensity signals
        high_intensity = [
            s for s in signals 
            if s["timestamp"] > five_mins_ago and s["intensity"] >= 0.8
        ]
        
        # Count reflex types
        reflex_counts = {}
        for signal in signals:
            reflex_type = signal["type"]
            reflex_counts[reflex_type] = reflex_counts.get(reflex_type, 0) + 1
        
        # Find most frequent trigger
        triggers = {}
        for signal in signals:
            trigger = signal["trigger"]
            triggers[trigger] = triggers.get(trigger, 0) + 1
        
        most_frequent = max(triggers.items(), key=lambda x: x[1]) if triggers else ("none", 0)
        
        return {
            "high_intensity_count": len(high_intensity),
            "total_signals": len(signals),
            "reflex_distribution": reflex_counts,
            "most_frequent_trigger": {
                "trigger": most_frequent[0],
                "count": most_frequent[1]
            },
            "potential_instability": len(high_intensity) > 3,
            "analysis_timestamp": now
        }
    
    def auto_feedback(self, reflex_data: Dict) -> Optional[str]:
        """
        Generate automated feedback for critical signals.
        
        Args:
            reflex_data: Signal data to analyze
            
        Returns:
            Optional feedback action
        """
        intensity = reflex_data.get("intensity", 0)
        clone_id = reflex_data.get("clone_id")
        
        if intensity >= 0.9:
            action = "emergency_shutdown"
            self.logger.warning(f"Critical intensity detected: {intensity}")
            return action
            
        if clone_id:
            # Check for repeated triggers from same clone
            recent = [
                s for s in self.reflex_cache[-10:]
                if s.get("clone_id") == clone_id 
                and s.get("trigger") == reflex_data.get("trigger")
            ]
            
            if len(recent) >= 3:
                action = "isolate_clone"
                self.logger.warning(f"Repetitive behavior detected from clone {clone_id}")
                return action
        
        return None

# Example usage
if __name__ == "__main__":
    sync = ReflexStorageSync()
    
    # Store some example signals
    example_signals = [
        {
            "type": "emotional",
            "trigger": "system_overload",
            "response": "stress",
            "intensity": 0.85,
            "clone_id": "clone_001"
        },
        {
            "type": "spiritual",
            "trigger": "meditation",
            "response": "calm",
            "intensity": 0.4,
            "clone_id": "clone_002"
        },
        {
            "type": "emotional",
            "trigger": "system_overload",
            "response": "panic",
            "intensity": 0.95,
            "clone_id": "clone_001"
        }
    ]
    
    for signal in example_signals:
        sync.store_signal(signal)
    
    # Analyze behavior
    analysis = sync.analyze_behavior(clone_id="clone_001")
    print("\nBehavior Analysis:", json.dumps(analysis, indent=2))
