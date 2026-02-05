from flask import Blueprint

blueprint = Blueprint('backup', __name__, url_prefix='/admin/backup')

module_metadata = {
    'name': 'Backup & Restore',
    'icon': 'database',
    'category': 'System',
    'url_prefix': '/admin/backup',
    'enabled': True
}

def setup_module(app):
    from . import routes
    
    # Initialize Automated Backup Scheduler
    from .services.auto_backup_service import AutoBackupService
    AutoBackupService.init_scheduler(app)
