# 📦 Module: `auth`

This document outlines the dependencies and relationships of the `auth` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- None (Independent Module)

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- Class: `AuthInterface` (Methods: authenticate, register, get_user_by_id, get_user_form_class, get_profile_edit_form_class, get_change_password_form_class)
- Function: `authenticate`
- Function: `get_change_password_form_class`
- Function: `get_profile_edit_form_class`
- Function: `get_user_by_id`
- Function: `get_user_form_class`
- Function: `register`

## 📡 Signals (Defines/Emits)

**Emitted Events:**
- `user_logged_in.send(...)` in `views.py`
- `user_registered.send(...)` in `auth_service.py`

## 🎧 Event Listeners
- None.

## 💾 Database Models
- `UserSession`
- `User`
