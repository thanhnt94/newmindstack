import re

file_path = r'c:\Code\MindStack\newmindstack\mindstack_app\modules\learning\sub_modules\stats\templates\stats\components\_item_charts.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the openItemStatsModal wrapper to add fallback
old_pattern = r'''// Override with chart-enhanced version
    window\.openItemStatsModal = function \(itemId\) \{
        // Call original function first
        if \(originalOpenItemStats\) \{
            originalOpenItemStats\(itemId\);
        \}

        // Fetch item stats with chart data'''

new_code = '''// Override with chart-enhanced version
    window.openItemStatsModal = function (itemId) {
        // Call original function first (if exists)
        if (originalOpenItemStats) {
            originalOpenItemStats(itemId);
        } else if (typeof window.openModal === 'function') {
            // FALLBACK: Open modal directly using URL
            window.openModal(`/learn/vocabulary/item/${itemId}/stats`);
        }

        // Fetch item stats with chart data'''

content = re.sub(old_pattern, new_code, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Added fallback to _item_charts.html!")
