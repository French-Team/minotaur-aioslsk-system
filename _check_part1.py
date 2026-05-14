
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open('src/gui/theme_part1.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Verify
print(f'Part 1: {len(content)} chars')
print(f'Has COLORS: {"COLORS" in content}')
