# MindStack AI Integration (v2.0)

## Overview

MindStack uses AI to provide intelligent explanations for learning items. The system features a unified interface supporting multiple providers with automatic failover and key rotation.

---

## 🏗️ Architecture

```
modules/AI/
├── interface.py          # Unified entry point (generate_content)
├── engines/              # LLM Clients (Gemini, HuggingFace)
├── services/             # Business Logic (Key Rotation, Logs)
├── logics/               # Pure logic (Prompt formatting)
└── routes/               # API Endpoints
```

### Flow
1. **Request**: Call `generate_content()` from `interface.py`.
2. **Provider**: `ServiceManager` selects the active provider.
3. **Key**: `ApiKeyManager` provides a valid, non-exhausted key.
4. **Execution**: `GeminiEngine` (or other) executes the call.
5. **Logging**: Success/Failure is logged to `AIUsageLog`.

---

## 🔧 Providers

### 1. Google Gemini (Primary)
- **Model**: `gemini-2.0-flash-lite-001` (Configurable via Admin)
- **Features**: Highly responsive, excellent Vietnamese support.

### 2. HuggingFace (Secondary/Fallback)
- **Models**: Llama-3, etc.
- **Role**: Used as a fallback if all Gemini keys are exhausted (429) or if the service is down.

---

## 🔑 Key Management & Rotation

MindStack supports multiple API keys per provider to overcome rate limits.

**Rotation Logic:**
- Keys are sorted by `last_used_timestamp`.
- If a key fails with a **429 (Quota Exhausted)** error, it is marked as `is_exhausted` and the system automatically retries with the next key.
- Exhausted keys are periodically reset or can be manually reset via Admin.

---

## 📝 Prompt System

MindStack uses a hierarchical prompt system:
1. **Item Prompt**: Specific prompt stored in `item.content['ai_prompt']`.
2. **Container Prompt**: Custom prompt defined for the entire set.
3. **Default Prompt**: Standardized prompts for Flashcards or Quizzes.

---

## 🚀 Implementation Examples

### Python (Preferred)
```python
from mindstack_app.modules.AI.interface import generate_content

response = generate_content(
    prompt="Explain Quantum Physics to a 5-year-old",
    feature="explanation",
    context_ref="item_id=123"
)

if response.success:
    print(response.content)
else:
    print(f"Error: {response.error}")
```

### API Endpoint
```http
POST /learn/ai/get-ai-response
Content-Type: application/json

{
    "prompt": "...",
    "feature": "explanation"
}
```

---

## 📊 Monitoring

AI usage is tracked in the `ai_usage_logs` table, capturing:
- Processing time
- Token/Character counts
- Provider & Model used
- Errors & Rate limit occurrences