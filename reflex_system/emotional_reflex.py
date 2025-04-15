
from abc import ABC, abstractmethod
from datetime import datetime
import random

class BaseReflexManager(ABC):

    @abstractmethod
    def _start(self):
        pass

    @abstractmethod
    def _stop(self):
        pass

class EmotionalReflexManager(BaseReflexManager):
    def __init__(self):
        self.active = False
        self.mood = "neutral"
        self.history = []

    def _start(self):
        self.active = True
        self._update_mood("initiating")
        print(f"[EMOTION REFLEX] Started at {datetime.now()} with mood: {self.mood}")

    def _stop(self):
        self._update_mood("dormant")
        self.active = False
        print(f"[EMOTION REFLEX] Stopped at {datetime.now()} with mood: {self.mood}")

    def _update_mood(self, new_mood=None):
        if not new_mood:
            new_mood = random.choice(["focused", "calm", "alert", "neutral", "curious"])
        self.mood = new_mood
        self.history.append((datetime.now(), self.mood))
        print(f"[EMOTION REFLEX] Mood changed to: {self.mood}")

    def get_current_mood(self):
        return self.mood

    def get_mood_history(self):
        return self.history

# Global instance
emotional_reflex_manager = EmotionalReflexManager()
