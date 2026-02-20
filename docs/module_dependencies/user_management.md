# 📦 Module: `user_management`

This document outlines the dependencies and relationships of the `user_management` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- `auth`

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- Class: `UserManagementInterface` (Methods: get_user_info, check_user_exists, get_user_role)
- Function: `check_user_exists`
- Function: `get_user_info`
- Function: `get_user_role`

## 📡 Signals (Defines/Emits)
- None.

## 🎧 Event Listeners
- None.

## 💾 Database Models
- No dedicated models found.
