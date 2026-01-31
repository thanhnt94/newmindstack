from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from mindstack_app.models import User, AppSettings, db
from sqlalchemy.orm.attributes import flag_modified
from .. import blueprint
try:
    from fsrs_rs_python import DEFAULT_PARAMETERS
except ImportError:
    DEFAULT_PARAMETERS = [0.4, 0.6, 2.4, 5.8, 4.93, 0.94, 0.86, 0.01, 1.49, 0.14, 0.94, 2.18, 0.05, 0.34, 1.26, 0.29, 2.61, 0.25, 1.0]

class FSRSSettingsHelper:
    @staticmethod
    def get_parameters():
        return {
            'FSRS_DESIRED_RETENTION': AppSettings.get('FSRS_DESIRED_RETENTION'),
            'FSRS_MAX_INTERVAL': AppSettings.get('FSRS_MAX_INTERVAL'),
            'FSRS_ENABLE_FUZZ': AppSettings.get('FSRS_ENABLE_FUZZ'),
            'FSRS_GLOBAL_WEIGHTS': AppSettings.get('FSRS_GLOBAL_WEIGHTS'),
        }

    @staticmethod
    def get_defaults():
        return {
            'FSRS_DESIRED_RETENTION': 0.90,
            'FSRS_MAX_INTERVAL': 36500,
            'FSRS_ENABLE_FUZZ': False,
            'FSRS_GLOBAL_WEIGHTS': list(DEFAULT_PARAMETERS)
        }

    @staticmethod
    def save_parameters(data):
        for key, value in data.items():
            AppSettings.set(key, value, category='fsrs')
        db.session.commit()

@blueprint.route('/fsrs-config', methods=['GET'])
@login_required
def fsrs_config():
    """
    Page to configure FSRS parameters.
    """
    if current_user.user_role != User.ROLE_ADMIN:
        flash('Permission denied', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    # Load current FSRS settings or defaults
    current_settings = FSRSSettingsHelper.get_parameters()
    defaults = FSRSSettingsHelper.get_defaults()
    
    return render_template('admin/fsrs_config.html', 
                           settings=current_settings,
                           defaults=defaults,
                           active_page='fsrs_config')

@blueprint.route('/fsrs-config/save', methods=['POST'])
@login_required
def save_fsrs_config():
    """
    Save FSRS parameters.
    """
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
        
    try:
        FSRSSettingsHelper.save_parameters(data)
        return jsonify({'success': True, 'message': 'FSRS parameters saved successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error saving parameters: {str(e)}'}), 500
