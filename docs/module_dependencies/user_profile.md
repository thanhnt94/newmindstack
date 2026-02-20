# 📦 Module: `user_profile`

This document outlines the dependencies and relationships of the `user_profile` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- `auth`
- `telegram_bot`

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- No public interface defined.

## 📡 Signals (Defines/Emits)

**Emitted Events:**
- `profile_updated.send(...)` in `profile_service.py`

## 🎧 Event Listeners
- None.

## 💾 Database Models
- No dedicated models found.
