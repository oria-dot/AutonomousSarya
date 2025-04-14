"""
Reflex Processor for SARYA.
Coordinates between emotional and spiritual reflexes.
"""
import logging
from typing import Dict, Optional

from core.base_module import BaseModule
from core.event_bus import Event, event_bus
from reflex_system.emotional_reflex import emotional_reflex_manager
from reflex_system.spiritual_reflex import spiritual_reflex_manager

class ReflexProcessor(BaseModule):
    def __init__(self):
        super().__init__("ReflexProcessor")

    def _initialize(self) -> bool:
        event_bus.subscribe("reflex.process", self._on_process_request)
        return True

    def process_reflex(self, data: Dict) -> Dict:
        emotional_state = emotional_reflex_manager.process_emotional_state(data)
        spiritual_insight = spiritual_reflex_manager.interpret_pattern(data)

        return {
            "emotional": emotional_state,
            "spiritual": spiritual_insight,
            "integrated_response": self._integrate_responses(
                emotional_state,
                spiritual_insight
            )
        }

    def _integrate_responses(self, emotional: Dict, spiritual: Dict) -> Dict:
        return {
            "primary_response": emotional.get("emotional_response"),
            "symbolic_guidance": spiritual.get("guidance"),
            "recommended_action": self._determine_action(emotional, spiritual)
        }

    def _determine_action(self, emotional: Dict, spiritual: Dict) -> str:
        if emotional.get("intensity", 0) > 0.8:
            return "immediate_attention"
        return "normal_processing"

    def _on_process_request(self, event: Event) -> None:
        result = self.process_reflex(event.data)
        event_bus.publish(Event(
            "reflex.processed",
            source=self.name,
            data=result
        ))

reflex_processor = ReflexProcessor()