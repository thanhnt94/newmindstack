# 📦 Module: `media`

This document outlines the dependencies and relationships of the `media` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- None (Independent Module)

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- Class: `MediaInterface` (Methods: search_and_cache_image, clean_orphan_cache, convert_to_relative_path)
- Function: `batch_generate_images`
- Function: `clean_orphan_cache`
- Function: `convert_to_relative_path`
- Function: `search_and_cache_image`

## 📡 Signals (Defines/Emits)
- None.

## 🎧 Event Listeners
- None.

## 💾 Database Models
- No dedicated models found.
