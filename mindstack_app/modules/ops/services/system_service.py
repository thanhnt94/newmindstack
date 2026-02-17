# File: mindstack_app/modules/ops/services/system_service.py
import subprocess
import threading
import os
import time
from datetime import datetime

class SystemService:
    """
    Service to handle system-level operations like code deployment and upgrades.
    """
    
    # Store the latest command execution state
    _execution_state = {
        'is_running': False,
        'logs': [],
        'start_time': None,
        'end_time': None,
        'exit_code': None,
        'current_line': ""
    }
    
    _log_lock = threading.Lock()

    @classmethod
    def run_upgrade(cls, command="ms-deploy"):
        """
        Executes the upgrade command in a background thread.
        """
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

        # Run in background thread to not block Flask
        thread = threading.Thread(target=cls._execute_command, args=(command,))
        thread.daemon = True
        thread.start()
        
        return True, "Tiến trình nâng cấp đã được bắt đầu."

    @classmethod
    def _execute_command(cls, command):
        """Internal method to run the command and capture output."""
        try:
            # Use shell=True for ms-deploy if it's an alias or script in PATH
            # On Windows, this might need a different handling if it's a .bat/.ps1
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=True,
                bufsize=1,
                universal_newlines=True
            )

            for line in process.stdout:
                with cls._log_lock:
                    cls._execution_state['logs'].append(line.strip())
                    cls._execution_state['current_line'] = line.strip()
                    # Limit log size to last 1000 lines
                    if len(cls._execution_state['logs']) > 1000:
                        cls._execution_state['logs'].pop(0)

            process.wait()
            
            with cls._log_lock:
                cls._execution_state['exit_code'] = process.returncode
                cls._execution_state['is_running'] = False
                cls._execution_state['end_time'] = time.time()
                status = "thành công" if process.returncode == 0 else "thất bại"
                cls._execution_state['logs'].append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Tiến trình kết thúc với trạng thái: {status} (Mã: {process.returncode})")

        except Exception as e:
            with cls._log_lock:
                cls._execution_state['is_running'] = False
                cls._execution_state['exit_code'] = 1
                cls._execution_state['logs'].append(f"[ERROR] {str(e)}")

    @classmethod
    def get_status(cls):
        """Returns the current execution state."""
        with cls._log_lock:
            return {
                'is_running': cls._execution_state['is_running'],
                'logs': cls._execution_state['logs'],
                'start_time': cls._execution_state['start_time'],
                'end_time': cls._execution_state['end_time'],
                'exit_code': cls._execution_state['exit_code']
            }
