import json
from graphify.detect import detect
from pathlib import Path

result = detect(Path('.'))
top_dirs = sorted(result.get('subdirectories', {}).items(), key=lambda x: x[1], reverse=True)[:5]
print('Top 5 subdirectories by file count:')
for d, c in top_dirs:
    print(f'  {d}: {c} files')
