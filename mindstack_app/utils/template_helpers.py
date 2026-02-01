"""
Utility function for dynamic template rendering.
All routes should use this instead of direct render_template with hardcoded versions.
"""
from flask import render_template
from mindstack_app.services.template_service import TemplateService


def render_dynamic_template(relative_path: str, **context):
    """
    Render a template with dynamic version prefix from TemplateService.
    
    Args:
        relative_path: Template path relative to version folder, e.g. 'modules/dashboard/index.html'
        **context: Template context variables
        
    Returns:
        Rendered template string
        
    Example:
        # Instead of: render_template('v3/pages/dashboard/index.html', ...)
        # Use: render_dynamic_template('modules/dashboard/index.html', ...)
    """
    version = TemplateService.get_active_version()
    full_path = f'{version}/{relative_path}'
    
    # Add template_version to context for templates that need it
    context['template_version'] = version
    
    return render_template(full_path, **context)
