import json
from pathlib import Path
from datetime import datetime, timezone
from graphify.detect import save_manifest
from graphify.benchmark import run_benchmark, print_benchmark

base=Path('graphify-out')

def read_json_any(path: Path):
    b=path.read_bytes()
    if b.startswith(b'\xff\xfe'):
        return json.loads(b.decode('utf-16'))
    return json.loads(b.decode('utf-8'))

detect=read_json_any(base/'.graphify_detect.json')
extract=read_json_any(base/'.graphify_extract.json')

save_manifest(detect.get('files', {}))

if detect.get('total_words',0) > 5000 and (base/'graph.json').exists():
    try:
        result = run_benchmark(str(base/'graph.json'), corpus_words=detect['total_words'])
        print_benchmark(result)
    except Exception as e:
        print(f'Benchmark skipped: {e}')

cost_path=base/'cost.json'
if cost_path.exists():
    cost=json.loads(cost_path.read_text(encoding='utf-8'))
else:
    cost={'runs': [], 'total_input_tokens': 0, 'total_output_tokens': 0}
input_tok=extract.get('input_tokens',0)
output_tok=extract.get('output_tokens',0)
cost['runs'].append({'date': datetime.now(timezone.utc).isoformat(), 'input_tokens': input_tok, 'output_tokens': output_tok, 'files': detect.get('total_files',0)})
cost['total_input_tokens'] += input_tok
cost['total_output_tokens'] += output_tok
cost_path.write_text(json.dumps(cost, indent=2), encoding='utf-8')
print(f'This run: {input_tok:,} input tokens, {output_tok:,} output tokens')
print(f'All time: {cost["total_input_tokens"]:,} input, {cost["total_output_tokens"]:,} output ({len(cost["runs"])} runs)')
