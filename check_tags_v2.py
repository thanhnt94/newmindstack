import sys
import re

def check_balance(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove comments
    content = re.sub(r'\{#.*?#\}', '', content, flags=re.DOTALL)
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    
    # Simple regex to find open and close tags
    div_opens = len(re.findall(r'<div[\s>]', content, re.IGNORECASE))
    div_closes = len(re.findall(r'</div>', content, re.IGNORECASE))
    
    sec_opens = len(re.findall(r'<section[\s>]', content, re.IGNORECASE))
    sec_closes = len(re.findall(r'</section>', content, re.IGNORECASE))
    
    header_opens = len(re.findall(r'<header[\s>]', content, re.IGNORECASE))
    header_closes = len(re.findall(r'</header>', content, re.IGNORECASE))
    
    main_opens = len(re.findall(r'<main[\s>]', content, re.IGNORECASE))
    main_closes = len(re.findall(r'</main>', content, re.IGNORECASE))

    print(f"File: {filename}")
    print(f"  DIV: {div_opens} / {div_closes} (Bal: {div_opens - div_closes})")
    print(f"  SECTION: {sec_opens} / {sec_closes} (Bal: {sec_opens - sec_closes})")
    print(f"  HEADER: {header_opens} / {header_closes} (Bal: {header_opens - header_closes})")
    print(f"  MAIN: {main_opens} / {main_closes} (Bal: {main_opens - main_closes})")

check_balance(sys.argv[1])
