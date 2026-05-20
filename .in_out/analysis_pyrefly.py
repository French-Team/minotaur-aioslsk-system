import json
from collections import Counter
from pathlib import Path

report_path = Path("q:/minautor-aioslsk-system/.in_out/pyrefly_report.json")
content = report_path.read_text(encoding="utf-8")

# Strip non-JSON parts if any
json_start = content.find("{")
json_end = content.rfind("}")
if json_start != -1 and json_end != -1:
    json_content = content[json_start:json_end+1]
else:
    json_content = content

data = json.loads(json_content)
errors = data.get("errors", [])

lines = []
lines.append(f"Total parsed errors: {len(errors)}\n")

# Group by file
files = {}
# Group by error name
names = Counter()

for err in errors:
    path = err.get("path", "unknown")
    name = err.get("name", "unknown")
    desc = err.get("description", "")
    line = err.get("line", 0)
    
    names[name] += 1
    files.setdefault(path, []).append((line, name, desc))

lines.append("--- Errors by type ---")
for name, count in names.most_common():
    lines.append(f"{name}: {count}")

lines.append("\n--- Errors by file ---")
for file_path, file_errors in sorted(files.items(), key=lambda x: len(x[1]), reverse=True):
    lines.append(f"{file_path}: {len(file_errors)} errors")
    for line, name, desc in file_errors:
        lines.append(f"  Line {line} [{name}]: {desc.replace('\n', ' ')}")

Path("q:/minautor-aioslsk-system/.in_out/pyrefly_analysis.txt").write_text("\n".join(lines), encoding="utf-8")
print("Analysis written to .in_out/pyrefly_analysis.txt")
