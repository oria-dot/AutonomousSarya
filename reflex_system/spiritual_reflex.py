from abc import ABC, abstractmethod
from datetime import datetime

class BaseReflex(ABC):

    @abstractmethod
    def _start(self):
        pass

class SpiritualReflex(BaseReflex):
    def __init__(self):
        self.state = "inactive"
        self.insight_log = []

    def _start(self):
        self.state = "seeking"
        self.insight_log.append((datetime.now(), "Spiritual core awakened"))
        print(f"[SPIRITUAL REFLEX] Activated at {datetime.now()}")

    def meditate(self):
        self.state = "reflective"
        self.insight_log.append((datetime.now(), "Entered meditation mode"))
        print(f"[SPIRITUAL REFLEX] Meditation sequence running...")

    def get_state(self):
        return self.state

    def get_insights(self):
        return self.insight_log

# Global instance
spiritual_reflex = SpiritualReflex()
