# 📦 Module: `access_control`

This document outlines the dependencies and relationships of the `access_control` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- None (Independent Module)

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- Class: `AccessControlInterface` (Methods: check, get_limit, enforce_quota, assign_role)
- Function: `assign_role`
- Function: `check`
- Function: `enforce_quota`
- Function: `get_limit`

## 📡 Signals (Defines/Emits)
**Defined Signals:**
- `_signals`
- `access_denied`
- `role_changed`

**Emitted Events:**
- `access_denied.send(...)` in `permission_service.py`
- `role_changed.send(...)` in `permission_service.py`

## 🎧 Event Listeners
- None.

## 💾 Database Models
- No dedicated models found.
