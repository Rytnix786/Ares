import json
from pathlib import Path

d = json.loads(Path('graphify-out/.graphify_detect.json').read_text())
print(f"Corpus: {d['total_files']} files · ~{d['total_words']:,} words")
print(f"  code:     {len(d['files'].get('code', []))} files")
print(f"  docs:     {len(d['files'].get('document', []))} files")
print(f"  papers:   {len(d['files'].get('paper', []))} files")
print(f"  images:   {len(d['files'].get('image', []))} files")
print(f"  video:    {len(d['files'].get('video', []))} files")
