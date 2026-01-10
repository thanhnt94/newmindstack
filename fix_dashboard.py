
import os

start_dir = os.getcwd()
target_file = os.path.join(start_dir, 'mindstack_app', 'templates', 'v4', 'pages', 'learning', 'vocabulary', 'dashboard', 'index.html')

content = """{# Vocabulary Learning Hub - Main Dashboard v1.0 #}

{% set _v = template_version|default('v4') %}
{% extends _v ~ '/base.html' %}

{% block title %}Học từ vựng - MindStack{% endblock %}

{% block head %}

{{ super() }}

{% include _v ~ '/includes/assets/_markdown_assets.html' %}

<link rel="stylesheet" href="{{ url_for('learning.vocabulary.serve_dashboard_asset', filename='css/dashboard.css') }}">
<link rel="stylesheet"
    href="{{ url_for('learning.vocabulary.serve_dashboard_asset', filename='css/dashboard-mobile.css') }}">
<link rel="stylesheet"
    href="{{ url_for('learning.vocabulary.serve_dashboard_asset', filename='css/dashboard-desktop.css') }}">


<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">



{% endblock %}



{% block content %}

{# Include Desktop View - Hidden on mobile, visible on lg+ #}
{% set _v = template_version|default('v4') %}
{% include _v ~ '/pages/learning/vocabulary/dashboard/_desktop.html' %}

{# Mobile View - Step Browser only - Hidden on lg+ #}
{% include _v ~ '/pages/learning/vocabulary/dashboard/_mobile.html' %}

<!-- STEP 2: Set Detail -->
{% include _v ~ '/pages/learning/vocabulary/dashboard/components/steps/_detail.html' %}



<!-- STEP 3: Mode Selector - Select Then Submit -->
{% include _v ~ '/pages/learning/vocabulary/dashboard/components/steps/_modes.html' %}



<!-- STEP 4: Flashcard Options (Sub-selection) - Inline rendering -->
{% include _v ~ '/pages/learning/vocabulary/dashboard/components/steps/_flashcard_options.html' %}



{# Step 5: MCQ Options - Header in loaded content #}
{% include _v ~ '/pages/learning/vocabulary/dashboard/components/steps/_mcq_options.html' %}



{# Modal Options Flashcard #}



{% include _v ~ '/pages/learning/vocabulary/stats/_modal_stats.html' %}





<!-- Flashcard Settings Modal (Redesigned) -->
{% include _v ~ '/pages/learning/vocabulary/dashboard/components/modals/_settings_modal.html' %}
{% endblock %}



{% block scripts %}

{{ super() }}

<script>
    window.ComponentConfig = {
        activeSetId: {{ active_set_id|default(None)|tojson }},
        activeStep: '{{ active_step|default("browser") }}',
        capabilities: {{ container_capabilities|default([])|tojson|safe }},
        apiUrls: {
            // Add any dynamic URLs if needed
        },
        userButtonCount: {{ user_button_count|default(4) }}
    };
</script>
<script src="{{ url_for('learning.vocabulary.serve_dashboard_asset', filename='js/dashboard.js') }}"></script>






{# Include Stats Components #}
{% include _v ~ '/pages/learning/vocabulary/dashboard/components/modals/_container_stats_modal.html' %}
{% include _v ~ '/pages/learning/vocabulary/dashboard/components/stats/_item_stats_charts.html' %}
{% include _v ~ '/pages/learning/vocabulary/dashboard/components/stats/_stats_enhancement.html' %}
{% include _v ~ '/pages/learning/vocabulary/dashboard/components/stats/_inject_stats_button.html' %}

<!-- Edit Set Modal - Beautiful App-like Design -->
{% include _v ~ '/pages/learning/vocabulary/dashboard/components/modals/_edit_set_modal.html' %}





{% endblock %}"""

with open(target_file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Successfully wrote to {target_file}")
