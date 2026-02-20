# 📦 Module: `AI`

This document outlines the dependencies and relationships of the `AI` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- None (Independent Module)

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- Class: `AIInterface` (Methods: generate_content, generate_item_explanation, get_formatted_prompt, get_default_request_interval, generate_ai_explanations, get_item_ai_contents, get_primary_explanation, set_primary_explanation)
- Function: `generate_ai_explanations`
- Function: `generate_content`
- Function: `generate_content`
- Function: `generate_item_explanation`
- Function: `get_default_request_interval`
- Function: `get_formatted_prompt`
- Function: `get_item_ai_contents`
- Function: `get_primary_explanation`
- Function: `set_primary_explanation`

## 📡 Signals (Defines/Emits)

**Emitted Events:**
- `ai_response_ready.send(...)` in `ai_service.py`
- `ai_token_used.send(...)` in `ai_gateway.py`

## 🎧 Event Listeners
- None.

## 💾 Database Models
- `AiCache`
- `AiContent`
- `AiTokenLog`
- `ApiKey`
