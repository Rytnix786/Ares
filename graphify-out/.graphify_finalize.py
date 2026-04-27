import json
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import re

from graphify.build import build_from_json
from graphify.cluster import cluster, score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.report import generate
from graphify.export import to_json, to_html
from graphify.detect import save_manifest
from graphify.benchmark import run_benchmark

base = Path('graphify-out')

def read_json_any(path: Path):
    b = path.read_bytes()
    if b.startswith(b'\xff\xfe'):
        return json.loads(b.decode('utf-16'))
    return json.loads(b.decode('utf-8'))

ast = read_json_any(base / '.graphify_ast.json')
sem_path = base / '.graphify_semantic.json'
if sem_path.exists():
    sem = read_json_any(sem_path)
else:
    sem = {'nodes': [], 'edges': [], 'hyperedges': [], 'input_tokens': 0, 'output_tokens': 0}

seen = {n['id'] for n in ast.get('nodes', [])}
merged_nodes = list(ast.get('nodes', []))
for n in sem.get('nodes', []):
    if n['id'] not in seen:
        merged_nodes.append(n)
        seen.add(n['id'])

extraction = {
    'nodes': merged_nodes,
    'edges': ast.get('edges', []) + sem.get('edges', []),
    'hyperedges': sem.get('hyperedges', []),
    'input_tokens': sem.get('input_tokens', 0),
    'output_tokens': sem.get('output_tokens', 0),
}
(base / '.graphify_extract.json').write_text(json.dumps(extraction, indent=2), encoding='utf-8')

G = build_from_json(extraction)
if G.number_of_nodes() == 0:
    raise SystemExit('ERROR: Graph is empty - extraction produced no nodes.')

communities = cluster(G)
cohesion = score_all(G, communities)
gods = god_nodes(G)
surprises = surprising_connections(G, communities)

# Initial labels
labels = {cid: f'Community {cid}' for cid in communities}
questions = suggest_questions(G, communities, labels)

detect = read_json_any(base / '.graphify_detect.json')
tokens = {'input': extraction.get('input_tokens', 0), 'output': extraction.get('output_tokens', 0)}

report = generate(G, communities, cohesion, labels, gods, surprises, detect, tokens, '.', suggested_questions=questions)
(base / 'GRAPH_REPORT.md').write_text(report, encoding='utf-8')
to_json(G, communities, str(base / 'graph.json'))

analysis = {
    'communities': {str(k): v for k, v in communities.items()},
    'cohesion': {str(k): v for k, v in cohesion.items()},
    'gods': gods,
    'surprises': surprises,
    'questions': questions,
}
(base / '.graphify_analysis.json').write_text(json.dumps(analysis, indent=2), encoding='utf-8')

# Heuristic community naming from node labels
stop = {'the','and','for','with','from','into','that','this','none','true','false','class','function','module','file','test'}
smart_labels = {}
for cid, members in communities.items():
    c = Counter()
    for nid in members[:120]:
        label = str(G.nodes[nid].get('label', nid)).lower()
        for t in re.findall(r'[a-z][a-z0-9_]+', label):
            if len(t) >= 4 and t not in stop:
                c[t] += 1
    top = [w for w, _ in c.most_common(2)]
    if top:
        name = ' '.join(w.capitalize() for w in top)
    else:
        name = f'Community {cid}'
    smart_labels[cid] = name[:48]

questions = suggest_questions(G, communities, smart_labels)
report = generate(G, communities, cohesion, smart_labels, gods, surprises, detect, tokens, '.', suggested_questions=questions)
(base / 'GRAPH_REPORT.md').write_text(report, encoding='utf-8')
(base / '.graphify_labels.json').write_text(json.dumps({str(k): v for k, v in smart_labels.items()}, indent=2), encoding='utf-8')

NODE_LIMIT = 5000
if G.number_of_nodes() > NODE_LIMIT:
    import networkx as nx
    node_to_community = {nid: cid for cid, m in communities.items() for nid in m}
    meta = nx.Graph()
    for cid in communities:
        meta.add_node(str(cid), label=smart_labels.get(cid, f'Community {cid}'))
    edge_counts = Counter()
    for u, v in G.edges():
        cu, cv = node_to_community.get(u), node_to_community.get(v)
        if cu is not None and cv is not None and cu != cv:
            edge_counts[(min(cu, cv), max(cu, cv))] += 1
    for (cu, cv), w in edge_counts.items():
        meta.add_edge(str(cu), str(cv), weight=w, relation=f'{w} cross-community edges', confidence='AGGREGATED')
    if meta.number_of_nodes() > 1:
        meta_communities = {cid: [str(cid)] for cid in communities}
        member_counts = {cid: len(m) for cid, m in communities.items()}
        to_html(meta, meta_communities, str(base / 'graph.html'), community_labels=smart_labels or None, member_counts=member_counts)
else:
    to_html(G, communities, str(base / 'graph.html'), community_labels=smart_labels or None)

bench_summary = None
if detect.get('total_words', 0) > 5000:
    bench = run_benchmark(str(base / 'graph.json'), corpus_words=detect['total_words'])
    bench_summary = bench

save_manifest(detect.get('files', {}))

cost_path = base / 'cost.json'
if cost_path.exists():
    cost = json.loads(cost_path.read_text(encoding='utf-8'))
else:
    cost = {'runs': [], 'total_input_tokens': 0, 'total_output_tokens': 0}
cost['runs'].append({'date': datetime.now(timezone.utc).isoformat(), 'input_tokens': tokens['input'], 'output_tokens': tokens['output'], 'files': detect.get('total_files', 0)})
cost['total_input_tokens'] += tokens['input']
cost['total_output_tokens'] += tokens['output']
cost_path.write_text(json.dumps(cost, indent=2), encoding='utf-8')

print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, {len(communities)} communities")
print(f"This run tokens: in={tokens['input']}, out={tokens['output']}")
if bench_summary:
    print('Benchmark:')
    for k in ('naive_tokens','graph_tokens','reduction_pct'):
        if k in bench_summary:
            print(f"  {k}: {bench_summary[k]}")
print('Outputs ready in graphify-out/')
