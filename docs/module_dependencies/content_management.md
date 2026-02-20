# 📦 Module: `content_management`

This document outlines the dependencies and relationships of the `content_management` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- `quiz`
- `vocabulary`

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- Class: `ContentInterface` (Methods: get_items_content, get_container_metadata, verify_content_access, get_form_class, create_container, update_container, delete_container)
- Function: `create_container`
- Function: `delete_container`
- Function: `get_container_metadata`
- Function: `get_form_class`
- Function: `get_items_content`
- Function: `update_container`
- Function: `verify_content_access`

## 📡 Signals (Defines/Emits)
**Defined Signals:**
- `_signals`
- `container_structure_changed`
- `content_created`
- `content_deleted`
- `content_updated`

**Emitted Events:**
- `content_changed.send(...)` in `management_service.py`
- `content_created.send(...)` in `kernel_service.py`
- `content_deleted.send(...)` in `kernel_service.py`
- `content_updated.send(...)` in `kernel_service.py`

## 🎧 Event Listeners
- None.

## 💾 Database Models
- No dedicated models found.
