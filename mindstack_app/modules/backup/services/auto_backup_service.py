# File: mindstack_app/modules/backup/services/auto_backup_service.py
import os
import json
import zipfile
import logging
import shutil
from datetime import datetime, timedelta
from flask import current_app
from mindstack_app.core.extensions import scheduler, db
from mindstack_app.services.config_service import get_runtime_config
from .backup_service import (
    get_backup_folder,
    resolve_database_path,
    DATASET_CATALOG,
    collect_dataset_payload,
    write_dataset_to_zip
)

logger = logging.getLogger(__name__)

class AutoBackupService:
    """
    Service for handling automated daily backups and retention.
    """

    @staticmethod
    def run_daily_backup():
        """
        Job to be executed by scheduler.
        Creates a Universal Full Backup and cleans up old ones.
        """
        with scheduler.app.app_context():
            enabled = get_runtime_config('AUTO_BACKUP_ENABLED', 'false').lower() == 'true'
            if not enabled:
                logger.info("Auto Backup is disabled in settings.")
                return

            try:
                logger.info("Starting automated daily backup...")
                AutoBackupService._create_universal_backup()
                AutoBackupService._cleanup_old_backups()
                logger.info("Automated daily backup completed successfully.")
            except Exception as e:
                logger.error(f"Automated daily backup failed: {e}")

    @staticmethod
    def _create_universal_backup():
        backup_folder = get_backup_folder()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'mindstack_auto_backup_{timestamp}.zip'
        backup_path = os.path.join(backup_folder, backup_filename)

        db_path = resolve_database_path()
        if not os.path.exists(db_path):
            raise FileNotFoundError('Database file not found.')

        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 1. Database
            zipf.write(db_path, os.path.basename(db_path))
            
            # 2. Uploads
            uploads_folder = os.path.join(current_app.root_path, 'static', 'uploads')
            if os.path.exists(uploads_folder):
                for root, dirs, files in os.walk(uploads_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join('uploads', os.path.relpath(file_path, uploads_folder))
                        zipf.write(file_path, arcname)

            # 3. Datasets (Universal Format)
            for dataset_key in DATASET_CATALOG.keys():
                try:
                    payload = collect_dataset_payload(dataset_key)
                    write_dataset_to_zip(zipf, dataset_key, payload, folder_prefix='datasets')
                except Exception as e:
                    logger.error(f"Failed to include dataset {dataset_key} in auto backup: {e}")

            # 4. Manifest
            manifest = {
                'type': 'full',
                'is_auto': True,
                'is_universal': True,
                'generated_at': datetime.utcnow().isoformat() + 'Z',
                'database_file': os.path.basename(db_path),
                'includes_uploads': True
            }
            zipf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))

    @staticmethod
    def _cleanup_old_backups():
        retention_days = int(get_runtime_config('AUTO_BACKUP_RETENTION_DAYS', 7))
        backup_folder = get_backup_folder()
        
        now = datetime.now()
        threshold = now - timedelta(days=retention_days)

        for filename in os.listdir(backup_folder):
            if not filename.startswith('mindstack_auto_backup_') or not filename.endswith('.zip'):
                continue
            
            file_path = os.path.join(backup_folder, filename)
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            if file_time < threshold:
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted old auto backup: {filename}")
                except Exception as e:
                    logger.error(f"Failed to delete old backup {filename}: {e}")

    @staticmethod
    def init_scheduler(app):
        """
        Register the backup job with APScheduler.
        Recommended time: 02:00 AM daily.
        """
        # Job ID for tracking/replacing
        job_id = 'daily_auto_backup'
        
        # Add job if it doesn't exist
        if not scheduler.get_job(job_id):
            scheduler.add_job(
                id=job_id,
                func=AutoBackupService.run_daily_backup,
                trigger='cron',
                hour=2,
                minute=0,
                replace_existing=True
            )
            logger.info("Automated daily backup job registered at 02:00 AM.")
