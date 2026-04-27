import json
from pathlib import Path
from graphify.extract import collect_files, extract

detect_path = Path('graphify-out/.graphify_detect.json')
b = detect_path.read_bytes()
txt = b.decode('utf-16') if b.startswith(b'\xff\xfe') else b.decode('utf-8')
detect = json.loads(txt)

code_files = []
for f in detect.get('files', {}).get('code', []):
    p = Path(f)
    code_files.extend(collect_files(p) if p.is_dir() else [p])

if code_files:
    result = extract(code_files, cache_root=Path('.'))
else:
    result = {'nodes': [], 'edges': [], 'input_tokens': 0, 'output_tokens': 0}

Path('graphify-out/.graphify_ast.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(f"AST: {len(result['nodes'])} nodes, {len(result['edges'])} edges")
