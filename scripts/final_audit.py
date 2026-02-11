import os
import re
import sys
from collections import defaultdict

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULES_DIR = os.path.join(BASE_DIR, 'mindstack_app', 'modules')

# 1. Danh sách các module CŨ (Phải bị xóa)
LEGACY_MODULES = [
    'vocab_flashcard', 'vocab_mcq', 'vocab_typing', 
    'vocab_speed', 'vocab_listening', 'vocab_matching'
]

# 2. Danh sách các Mode bắt buộc phải có trong Vocabulary mới
REQUIRED_VOCAB_MODES = [
    'flashcard_mode.py', 'mcq_mode.py', 'typing_mode.py',
    'speed_mode.py', 'listening_mode.py', 'matching_mode.py'
]

# 3. Chuẩn cấu trúc của 1 Module hiện đại
REQUIRED_FILES = ['__init__.py', 'interface.py', 'services', 'routes']

def print_header(title):
    print(f"\n{'='*60}")
    print(f"🕵️  {title.upper()}")
    print(f"{'='*60}")

def check_zombies():
    print_header("1. CHECKING FOR ZOMBIE MODULES (Legacy)")
    found_zombies = []
    for mod in LEGACY_MODULES:
        path = os.path.join(MODULES_DIR, mod)
        if os.path.exists(path):
            found_zombies.append(mod)
    
    if found_zombies:
        print("❌ WARNING: Vẫn còn các module cũ chưa xóa sạch:")
        for z in found_zombies:
            print(f"   - {z}")
        print("👉 Khuyến nghị: Hãy xóa hoặc backup chúng ra khỏi folder 'modules/'.")
    else:
        print("✅ SẠCH SẼ: Không tìm thấy module cũ nào.")

def check_structure():
    print_header("2. CHECKING MODULE STRUCTURE (Standardization)")
    
    # Lấy danh sách module hiện tại (trừ __pycache__)
    modules = [d for d in os.listdir(MODULES_DIR) 
               if os.path.isdir(os.path.join(MODULES_DIR, d)) and not d.startswith('__')]
    
    issues = 0
    for mod in modules:
        mod_path = os.path.join(MODULES_DIR, mod)
        missing = []
        for req in REQUIRED_FILES:
            if not os.path.exists(os.path.join(mod_path, req)):
                missing.append(req)
        
        if missing:
            print(f"⚠️  Module '{mod}' thiếu thành phần chuẩn: {', '.join(missing)}")
            issues += 1
    
    if issues == 0:
        print("✅ CHUẨN MỰC: Tất cả module đều có đủ Interface, Services, Routes.")

def check_driver_modes():
    print_header("3. CHECKING VOCABULARY DRIVER MODES")
    modes_dir = os.path.join(MODULES_DIR, 'vocabulary', 'modes')
    
    if not os.path.exists(modes_dir):
        print("❌ LỖI: Không tìm thấy thư mục 'vocabulary/modes'!")
        return

    files = os.listdir(modes_dir)
    missing_modes = [m for m in REQUIRED_VOCAB_MODES if m not in files]
    
    if missing_modes:
        print(f"❌ THIẾU MODE: Chưa thấy các file logic sau: {', '.join(missing_modes)}")
    else:
        print("✅ ĐẦY ĐỦ: Module Vocabulary đã tích hợp đủ 6 chế độ học.")

def check_illegal_imports():
    print_header("4. CHECKING ILLEGAL IMPORTS (Coupling)")
    print("(Quy tắc: Module A chỉ được import 'module_b.interface')\n")
    
    violations = []
    
    # Regex tìm import chéo
    # Pattern bắt: from mindstack_app.modules.MODULE_NAME...
    import_pattern = re.compile(r'from\s+mindstack_app\.modules\.(\w+)')
    
    for root, dirs, files in os.walk(MODULES_DIR):
        # Xác định module hiện tại đang scan
        rel_path = os.path.relpath(root, MODULES_DIR)
        current_module = rel_path.split(os.sep)[0]
        
        if current_module in ['.', '..'] or current_module.startswith('__'):
            continue

        for file in files:
            if not file.endswith('.py'): continue
            
            file_path = os.path.join(root, file)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines):
                match = import_pattern.search(line)
                if match:
                    target_module = match.group(1)
                    
                    # Bỏ qua import chính mình
                    if target_module == current_module: continue
                    
                    # Bỏ qua import từ core/utils (hợp lệ)
                    if target_module in ['core', 'utils']: continue

                    # QUAN TRỌNG: Kiểm tra xem có import qua interface không
                    # Hợp lệ: ...modules.auth.interface
                    # Hợp lệ: ...modules.auth import interface
                    is_interface_import = 'interface' in line
                    
                    if not is_interface_import:
                        # Đây là LỖI: Import trực tiếp ruột gan module khác
                        violations.append({
                            'source': f"{current_module}/{os.path.basename(file)}:{i+1}",
                            'target': target_module,
                            'code': line.strip()
                        })

    if violations:
        print(f"🔴 TÌM THẤY {len(violations)} VI PHẠM NGUY HIỂM:")
        for v in violations:
            print(f"   ► Tại {v['source']}")
            print(f"     Gọi lén module '{v['target']}': \"{v['code']}\"")
            print("     👉 Sửa thành: Gọi qua interface.py\n")
    else:
        print("✅ KIẾN TRÚC SẠCH: Không phát hiện import 'đi cửa sau'.")

if __name__ == "__main__":
    check_zombies()
    check_structure()
    check_driver_modes()
    check_illegal_imports()
    print("\n" + "="*60)
    print("🏁 AUDIT COMPLETE")