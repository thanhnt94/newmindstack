# File: mindstack_app/modules/ops/services/system_service.py
import subprocess
import threading
import os
import time
import json
from datetime import datetime

class SystemService:
    """
    Service to handle system-level operations like code deployment and upgrades.
    """
    
    # Persistent state file path
    # We put it in the database directory as it's usually persistent
    _STATE_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'database', 'system_upgrade_state.json'))
    
    _execution_state = {
        'is_running': False,
        'logs': [],
        'start_time': None,
        'end_time': None,
        'exit_code': None,
        'current_line': ""
    }
    
    _log_lock = threading.Lock()
    _monitor_thread = None  # Track the actual thread instance

    @classmethod
    def _save_state(cls):
        """Persist current state to disk."""
        try:
            os.makedirs(os.path.dirname(cls._STATE_FILE), exist_ok=True)
            with open(cls._STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cls._execution_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[SystemService] Error saving state: {e}")

    @classmethod
    def _load_state(cls):
        """Load state from disk if it exists."""
        if os.path.exists(cls._STATE_FILE):
            try:
                with open(cls._STATE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Merge with existing default in case schema changed
                    cls._execution_state.update(data)
                    
                    # Orphaned state recovery: 
                    # If state says running but we have no local thread, it crashed/restarted
                    if cls._execution_state.get('is_running') and cls._monitor_thread is None:
                        print("[SystemService] Detecting orphaned running state (Service Restarted). Cleaning up...")
                        cls._execution_state['is_running'] = False
                        # Use code 0 (Success) because a restart during upgrade is usually intended
                        if cls._execution_state.get('exit_code') is None:
                             cls._execution_state['exit_code'] = 0
                        
                        cls._execution_state['logs'].append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Hệ thống đã khởi động lại (Service Restarted).")
                        cls._save_state()
            except Exception as e:
                print(f"[SystemService] Error loading state: {e}")

    @classmethod
    def run_upgrade(cls, command="sudo ms-deploy"):
        """
        Executes the upgrade command in a background thread.
        """
        # Load latest state before checking
        cls._load_state()
        
        if cls._execution_state['is_running']:
            return False, "Một tiến trình nâng cấp đang chạy."

        # Reset state
        cls._execution_state = {
            'is_running': True,
            'logs': [f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Bắt đầu tiến trình nâng cấp..."],
            'start_time': time.time(),
            'end_time': None,
            'exit_code': None,
            'current_line': ""
        }
        cls._save_state()

        # Run in background thread to not block Flask
        cls._monitor_thread = threading.Thread(target=cls._execute_command, args=(command,))
        cls._monitor_thread.daemon = True
        cls._monitor_thread.start()
        
        return True, "Tiến trình nâng cấp đã được bắt đầu."

    @classmethod
    def _execute_command(cls, command):
        """Internal method to run the command and capture output."""
        try:
            # Use shell=True for ms-deploy if it's an alias or script
            # Log the exact command being executed for transparency
            with cls._log_lock:
                cls._execution_state['logs'].append(f"[INFO] Executing: {command}")
                cls._save_state()

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=True,
                bufsize=1,
                universal_newlines=True
            )

            # Use readline loop with poll() for higher fidelity capturing
            # especially important before system restarts
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                
                if line:
                    with cls._log_lock:
                        stripped_line = line.strip()
                        cls._execution_state['logs'].append(stripped_line)
                        cls._execution_state['current_line'] = stripped_line
                        # Limit log size to last 1000 lines
                        if len(cls._execution_state['logs']) > 1000:
                            cls._execution_state['logs'].pop(0)
                        cls._save_state()

            process.wait()
            
            with cls._log_lock:
                cls._execution_state['exit_code'] = process.returncode
                cls._execution_state['is_running'] = False
                cls._execution_state['end_time'] = time.time()
                status = "thành công" if process.returncode == 0 else "thất bại"
                cls._execution_state['logs'].append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Tiến trình kết thúc với trạng thái: {status} (Mã: {process.returncode})")
                cls._save_state()

        except Exception as e:
            with cls._log_lock:
                cls._execution_state['is_running'] = False
                cls._execution_state['exit_code'] = 1
                cls._execution_state['logs'].append(f"[ERROR] {str(e)}")
                cls._save_state()

    @classmethod
    def get_status(cls):
        """Returns the current execution state."""
        # Always reload from disk to get latest state (especially after restart)
        cls._load_state()
        with cls._log_lock:
            return {
                'is_running': cls._execution_state['is_running'],
                'logs': cls._execution_state['logs'],
                'start_time': cls._execution_state['start_time'],
                'end_time': cls._execution_state['end_time'],
                'exit_code': cls._execution_state['exit_code']
            }
