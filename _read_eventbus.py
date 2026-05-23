import logging
import sys

logger = logging.getLogger("[READ-EVENTBUS]")
sys.stdout.reconfigure(encoding='utf-8')

lines = open('src/services/event_bus.py', 'r', encoding='utf-8').readlines()

# Show SurveillanceEvent class
print("=== SurveillanceEvent class (lines 79-107) ===")
for i in range(78, 108):
    if i < len(lines):
        print(f'{i+1}: {lines[i]}', end='')

# Show emit_event method
print("\n=== emit_event method (lines 197-220) ===")
for i, line in enumerate(lines):
    if 'def emit_event' in line:
        for j in range(i, min(i+30, len(lines))):
            print(f'{j+1}: {lines[j]}', end='')
        break

# Show signal definition
print("\n=== Signals ===")
for i, line in enumerate(lines):
    if 'Signal(' in line:
        print(f'{i+1}: {line.rstrip()}')
