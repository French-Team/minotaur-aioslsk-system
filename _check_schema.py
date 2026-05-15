import sys
sys.stdout.reconfigure(encoding='utf-8')

lines = open('src/services/event_bus.py', 'r', encoding='utf-8').readlines()

# Find the schema creation
for i, line in enumerate(lines):
    if 'CREATE TABLE' in line or 'CHECK' in line or 'category' in line:
        for j in range(max(0,i-1), min(i+5, len(lines))):
            print(f'{j+1}: {lines[j]}', end='')
        print('---')
