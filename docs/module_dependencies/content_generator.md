# 📦 Module: `content_generator`

This document outlines the dependencies and relationships of the `content_generator` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- `AI`
- `audio`

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- Function: `generate_audio`
- Function: `generate_bulk_from_container`
- Function: `generate_image`
- Function: `generate_text`
- Function: `get_generation_status`
- Function: `get_log_model`

## 📡 Signals (Defines/Emits)
**Defined Signals:**
- `_signals`
- `generation_completed`
- `generation_failed`
- `generation_queued`

## 🎧 Event Listeners
- None.

## 💾 Database Models
- `GenerationLog`
