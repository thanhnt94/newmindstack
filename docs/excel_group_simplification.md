# Simplified Excel structure for grouped quiz items

This proposal trims the Excel schema so each question (item) stays the smallest editable unit while groups are recognized through just three fields. It also removes per-item passage fields to avoid duplicate context data.

## Minimal columns in the `Data` sheet

| Category | Columns | Notes |
| --- | --- | --- |
| Identification | `item_id`, `order_in_container`, `action` | Same behavior as today for locating and ordering items. |
| Core content | `question`, `pre_question_text`, `guidance`, `ai_prompt` | Main text fields; unchanged. |
| Choices & answers | `option_a` – `option_d`, `correct_answer_text` | Choice-based items or free-text answers. |
| Item-specific media | `question_image_file`, `question_audio_file` | Media that belongs only to this item. |
| Group linkage (proposed) | `group_id`, `group_shared_components`, `group_item_order` | See details below. |

Removed fields: `passage_text` and `passage_order` (context will be carried by the group), and all other `group_*` content fields that repeated across rows. Bạn có thể tải file Excel mẫu theo cấu trúc này từ trang quản lý Excel của quiz (`/quizzes/<set_id>/manage-excel`) qua nút **Tải template trống**.

## The three group fields

| Field | Purpose | Expected values |
| --- | --- | --- |
| `group_id` | Numeric identifier used to tie multiple rows to the same group. Leave blank for standalone items. | Existing group ID or a new integer when bulk-creating groups. |
| `group_shared_components` | Declares which parts are shared across items in the same `group_id`. | Comma-separated tokens, e.g. `image`, `audio`, `explanation`, `prompt`. Importer uses this to know which fields to copy from the first row of the group. |
| `group_item_order` | The order of this question inside its group (e.g., multi-step questions). | Integer; independent from `order_in_container`. |

### How import/export would work
- **Import:** Rows with the same `group_id` are bundled. The first row containing a given shared component provides the canonical value; subsequent rows can leave those component cells empty. Items without `group_id` remain independent. 
- **Export:** Each grouped row repeats only the three group columns. Shared component columns are populated on the first row of each group for readability, left blank on others to keep the sheet concise.

### Benefits
- Editors think in terms of a single `group_id` instead of six different group-related columns.
- No `passage_*` duplication—context lives with the group rather than every item.
- Orders are clear: `order_in_container` for the quiz flow, `group_item_order` for steps within a grouped context.
