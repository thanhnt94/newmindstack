# 📦 Module: `audio`

This document outlines the dependencies and relationships of the `audio` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- `quiz`
- `vocabulary`

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- Class: `AudioInterface` (Methods: speech_to_text)
- Function: `generate_audio`
- Function: `speech_to_text`

## 📡 Signals (Defines/Emits)
- None.

## 🎧 Event Listeners
- None.

## 💾 Database Models
- No dedicated models found.
