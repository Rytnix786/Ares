import json
from pathlib import Path
from collections import Counter
import re
from graphify.build import build_from_json
from graphify.cluster import cluster, score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.report import generate
from graphify.export import to_json, to_html

base=Path('graphify-out')

def read_json_any(path: Path):
    b = path.read_bytes()
    if b.startswith(b'\xff\xfe'):
        return json.loads(b.decode('utf-16'))
    return json.loads(b.decode('utf-8'))

extraction=read_json_any(base/'.graphify_extract.json')
detect=read_json_any(base/'.graphify_detect.json')
G=build_from_json(extraction)
communities=cluster(G)
cohesion=score_all(G, communities)
gods=god_nodes(G)
surprises=surprising_connections(G, communities)

stop={'the','and','for','with','from','into','that','this','none','true','false','class','function','module','file','test'}
labels={}
for cid,members in communities.items():
    c=Counter()
    for nid in members[:120]:
        label=str(G.nodes[nid].get('label',nid)).lower()
        for t in re.findall(r'[a-z][a-z0-9_]+',label):
            if len(t)>=4 and t not in stop:
                c[t]+=1
    top=[w for w,_ in c.most_common(2)]
    labels[cid]=' '.join(w.capitalize() for w in top) if top else f'Community {cid}'

questions=suggest_questions(G, communities, labels)
report=generate(G, communities, cohesion, labels, gods, surprises, detect, {'input': extraction.get('input_tokens',0), 'output': extraction.get('output_tokens',0)}, '.', suggested_questions=questions)
(base/'GRAPH_REPORT.md').write_text(report, encoding='utf-8')

analysis={'communities': {str(k): v for k,v in communities.items()}, 'cohesion': {str(k): v for k,v in cohesion.items()}, 'gods': gods, 'surprises': surprises, 'questions': questions}
(base/'.graphify_analysis.json').write_text(json.dumps(analysis, indent=2), encoding='utf-8')
(base/'.graphify_labels.json').write_text(json.dumps({str(k): v for k,v in labels.items()}, indent=2), encoding='utf-8')

to_json(G, communities, str(base/'graph.json'))
NODE_LIMIT=5000
if G.number_of_nodes()>NODE_LIMIT:
    import networkx as nx
    node_to_community={nid: cid for cid,m in communities.items() for nid in m}
    meta=nx.Graph()
    for cid in communities: meta.add_node(str(cid), label=labels.get(cid, f'Community {cid}'))
    edge_counts=Counter()
    for u,v in G.edges():
        cu,cv=node_to_community.get(u), node_to_community.get(v)
        if cu is not None and cv is not None and cu!=cv:
            edge_counts[(min(cu,cv), max(cu,cv))]+=1
    for (cu,cv),w in edge_counts.items():
        meta.add_edge(str(cu), str(cv), weight=w, relation=f'{w} cross-community edges', confidence='AGGREGATED')
    meta_communities={cid:[str(cid)] for cid in communities}
    member_counts={cid:len(m) for cid,m in communities.items()}
    to_html(meta, meta_communities, str(base/'graph.html'), community_labels=labels or None)
else:
    to_html(G, communities, str(base/'graph.html'), community_labels=labels or None)

print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, {len(communities)} communities")
print('finalize-done')

