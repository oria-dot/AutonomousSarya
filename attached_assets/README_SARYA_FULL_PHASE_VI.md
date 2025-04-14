# SARYA Phase VI System Overview

This system is a fully integrated AI intelligence infrastructure featuring clone automation, reflex memory, strategy evolution, and emotional/spiritual awareness.

## System Architecture
- **Engine Core**: Handles system boot, command routing, interlinking
- **Clone Intelligence**: Autonomous clone launchers, feedback, scaling, warfare
- **Dashboard/API**: FastAPI interface with OpenAPI docs and JWT security
- **Metrics Layer**: Prometheus metrics for reflex, clone, and risk
- **Plugin System**: Dynamically load plugins from `/plugins/` directory
- **Emotional Reflex Layer**: Detects emotional context from system events
- **Spiritual Feedback Core**: Adds symbolic meaning to reflex logs

## Key Modules Used

### Active Core Components
- `systems/clone_intelligence_system/sarya_engine.py`
- `systems/clone_intelligence_system/aria_dispatcher.py`
- `systems/clone_intelligence_system/aria_interlink_engine.py`
- `systems/clone_intelligence_system/aria_boot_kernel.py`
- `systems/clone_intelligence_system/clone_command_engine.py`
- `systems/clone_intelligence_system/clone_worker.py`
- `plugin_loader.py`
- `sarya_dashboard_fastapi.py`
- `emotional_reflex_engine.py`
- `spiritual_guidance_core.py`

## Phase VI Components
- `emotional_reflex_engine.py` - Maps reflex logs to emotional tags
- `spiritual_guidance_core.py` - Symbolic insight generator from events
- `deep_reflex_emotion_log.json` - Emotion memory storage (created at runtime)

## What is Unused (Currently)
- Many experimental modules in `/experimental_tools/`, `/legacy_unused/`, and `/uncategorized/` are not yet integrated or loaded dynamically
- These are reserved for future expansions (e.g. voice dashboards, reinforcement learning, AI trading, compliance systems)

## Suggested Flow
1. Start `sarya_engine.py`
2. Launch the FastAPI dashboard (`/v1/...`)
3. Trigger a clone via webhook or API
4. Emotional reflex is logged automatically
5. Use `spiritual_guidance_core.py` for deeper symbolic analysis if needed

_SARYA is now reflex-aware, emotionally reactive, spiritually symbolic, and modularly expandable._