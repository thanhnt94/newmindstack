from flask import render_template as flask_render_template

def render_template(template_name_or_list, **context):
    """
    Simple wrapper for flask.render_template.
    
    The application is now configured to look directly into the 'templates/default' folder,
    so no path manipulation is needed here.
    """
    return flask_render_template(template_name_or_list, **context)
