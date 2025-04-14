"""
Emotional Reflex Manager for SARYA.
Handles emotional state mapping and triggers.
"""
import json
import logging
import time
from typing import Dict, Optional

from core.base_module import BaseModule
from core.event_bus import Event, event_bus
from core.memory import memory_system

class EmotionalReflexManager(BaseModule):
    def __init__(self):
        super().__init__("EmotionalReflexManager")
        self.emotional_states = {}
        self.state_history = []

    def _initialize(self) -> bool:
        event_bus.subscribe("reflex.signal", self._on_reflex_signal)
        return True

    def process_emotional_state(self, data: Dict) -> Dict:
        intensity = data.get("intensity", 0.0)
        context = data.get("context", {})

        state = {
            "timestamp": time.time(),
            "intensity": intensity,
            "context": context,
            "emotional_response": self._calculate_response(intensity, context)
        }

        self.state_history.append(state)
        return state

    def _calculate_response(self, intensity: float, context: Dict) -> str:
        if intensity > 0.8:
            return "highly_reactive"
        elif intensity > 0.5:
            return "moderately_reactive"
        return "stable"

    def _on_reflex_signal(self, event: Event) -> None:
        if event.data.get("type") == "emotional":
            self.process_emotional_state(event.data)

emotional_reflex_manager = EmotionalReflexManager()