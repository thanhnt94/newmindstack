# 📦 Module: `notification`

This document outlines the dependencies and relationships of the `notification` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- None (Independent Module)

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- Function: `get_unread_count`
- Function: `mark_notification_read`
- Function: `notify_achievement_unlock`
- Function: `send_notification`

## 📡 Signals (Defines/Emits)
- None.

## 🎧 Event Listeners
- None.

## 💾 Database Models
- `NotificationPreference`
- `Notification`
- `PushSubscription`
