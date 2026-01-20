
import sys
try:
    content = open('card_debug.txt', encoding='utf-16').readlines()
except:
    content = open('card_debug.txt', encoding='utf-8').readlines()

for i, line in enumerate(content):
    print(f"{i}: {line.strip()}")
