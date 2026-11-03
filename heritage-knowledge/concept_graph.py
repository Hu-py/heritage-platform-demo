"""Rebuildable concept projection. Source tables and PDF evidence stay intact."""
import json
from collections import defaultdict
from contextlib import closing
from itertools import combinations
from threading import RLock
from kg import connect, CONCEPTS, ONTOLOGY, concept_matches, normalized, digest

LOCK = RLock()
VERSION = 'concept-projection-1'
KINDS = {'保护原则':'principle','风险问题':'risk','规划策略':'strategy','具体措施':'measure',
         '法规条款':'regulation','保护案例':'case','材料结构':'material','文物对象':'building_type'}

def endpoint_concept(text, kind):
    allowed = KINDS.get(kind)
    candidates = [c for c in CONCEPTS.values() if not allowed or c['kind'] == allowed]
    exact = [c['id'] for c in candidates if any(normalized(text) == normalized(a) for a in c['aliases'])]
    if len(exact) == 1:
        return exact[0], 'exact_alias'
    matched = set(concept_matches(text)) & {c['id'] for c in candidates}
    return (next(iter(matched)), 'lexical_candidate') if len(matched) == 1 else (None, 'unmapped')

def ensure_projection(path):
    with LOCK, closing(connect(path)) as db, db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS cg_meta(key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE IF NOT EXISTS cg_links(id TEXT PRIMARY KEY,source TEXT,target TEXT,relation TEXT,kind TEXT,evidence_count INTEGER);
        CREATE INDEX IF NOT EXISTS cg_source ON cg_links(source);
        CREATE INDEX IF NOT EXISTS cg_target ON cg_links(target);
        CREATE TABLE IF NOT EXISTS cg_evidence(owner TEXT,doc_id TEXT,page INTEGER,chunk_id TEXT,claim_id TEXT,PRIMARY KEY(owner,doc_id,page,chunk_id,claim_id));
        CREATE INDEX IF NOT EXISTS cg_evidence_owner ON cg_evidence(owner,doc_id,page);
        ''')
        signature = digest([VERSION, ONTOLOGY,
            list(db.execute('SELECT count(*),max(id) FROM claims').fetchone()),
            list(db.execute('SELECT count(*),max(chunk_id) FROM mentions').fetchone()),
            db.execute("SELECT value FROM meta WHERE key='build'").fetchone()[0]])
        old = db.execute("SELECT value FROM cg_meta WHERE key='signature'").fetchone()
        if old and old[0] == signature:
            return json.loads(db.execute("SELECT value FROM cg_meta WHERE key='summary'").fetchone()[0])
        db.execute('DELETE FROM cg_links'); db.execute('DELETE FROM cg_evidence')
        refs = defaultdict(set); links = {}; chunks = defaultdict(list); mapped = 0
        def link(a,b,relation,kind):
            key='cg:'+digest([a,b,relation,kind])[:24]
            links[key]=(a,b,relation,kind)
            return key
        for r in db.execute('SELECT m.concept_id,c.id,c.doc_id,c.page FROM mentions m JOIN chunks c ON c.id=m.chunk_id ORDER BY c.id'):
            cid,chunk,doc,page=r
            if cid not in CONCEPTS: continue
            ref=(doc,page,chunk,''); refs[cid].add(ref); chunks[chunk].append((cid,ref))
        for entries in chunks.values():
            for (a,ref),(b,_) in combinations(sorted(entries),2):
                refs[link(a,b,'同段共现','cooccurrence')].add(ref)
        for e in ONTOLOGY['retrieval_routes']:
            link(e['source'],e['target'],'检索扩展','route')
        for r in db.execute('SELECT * FROM claims'):
            a,am=endpoint_concept(r['source'],r['source_type']); b,bm=endpoint_concept(r['target'],r['target_type'])
            if not a or not b or a==b: continue
            key=link(a,b,r['relation'],'candidate'); refs[key].add((r['doc_id'],r['page'],'',r['id']));mapped+=1
        for key,(a,b,relation,kind) in links.items():
            count=len({(x[0],x[1]) for x in refs[key]})
            db.execute('INSERT INTO cg_links VALUES(?,?,?,?,?,?)',(key,a,b,relation,kind,count))
        db.executemany('INSERT INTO cg_evidence VALUES(?,?,?,?,?)',((owner,*r) for owner,rows in refs.items() for r in sorted(rows)))
        summary={'concepts':len(CONCEPTS),'relations':len(links),'mapped_claims':mapped,
                 'unmapped_claims':db.execute('SELECT count(*) FROM claims').fetchone()[0]-mapped,
                 'count_unit':'distinct_document_pdf_page','version':VERSION}
        for key,value in [('signature',signature),('summary',json.dumps(summary))]:
            db.execute('INSERT OR REPLACE INTO cg_meta VALUES(?,?)',(key,value))
        return summary

def graph(path,query='',center='',depth=1,kind='all',limit=32):
    summary=ensure_projection(path); depth=max(1,min(int(depth),2));limit=max(5,min(int(limit),60))
    if kind not in {'all','candidate','cooccurrence','route'}:raise ValueError('Unknown relation type')
    if center and center not in CONCEPTS:raise ValueError('Unknown concept')
    matches=concept_matches(query[:1000]) if query else []
    roots=[center] if center else matches[:1]
    with closing(connect(path)) as db:
        counts={r['owner']:r['n'] for r in db.execute('SELECT owner,count(*) n FROM (SELECT DISTINCT owner,doc_id,page FROM cg_evidence) GROUP BY owner')}
        rows=[dict(r) for r in db.execute('SELECT * FROM cg_links') if kind=='all' or r['kind']==kind]
    priority={'candidate':0,'route':1,'cooccurrence':2}
    rows.sort(key=lambda e:(priority[e['kind']],-e['evidence_count'],e['id']))
    selected=set(roots);distance={x:0 for x in roots}
    if roots:
        frontier=set(roots)
        for hop in range(1,depth+1):
            new=set()
            for e in rows:
                if e['source'] in frontier or e['target'] in frontier:
                    for cid in [e['source'],e['target']]:
                        if cid not in selected and len(selected)<limit:
                            selected.add(cid);new.add(cid);distance[cid]=hop
            frontier=new
    elif not query:
        selected=set(CONCEPTS)
    # An unknown query must not silently return an unrelated overview.
    all_edges=[e for e in rows if e['source'] in selected and e['target'] in selected]
    # Bound density while preserving each selected node's path to the center.
    keep=[]; seen=set(roots)
    for hop in range(1,depth+1):
        for cid in sorted(selected):
            if distance.get(cid)!=hop: continue
            edge=next((e for e in all_edges if (e['source']==cid and e['target'] in seen) or (e['target']==cid and e['source'] in seen)),None)
            if edge and edge not in keep:keep.append(edge)
            seen.add(cid)
    for e in sorted(all_edges,key=lambda e:(not (e['source'] in roots or e['target'] in roots),priority[e['kind']],-e['evidence_count'])):
        if len(keep)>=min(90,max(24,len(selected)*2)):break
        if e not in keep:keep.append(e)
    nodes=[{**CONCEPTS[c], 'label':CONCEPTS[c]['zh'],'evidence_count':counts.get(c,0),
            'distance':distance.get(c),'central':c in roots} for c in sorted(selected)]
    return {'nodes':nodes,'edges':keep,'center':roots[0] if roots else None,
            'matches':[CONCEPTS[c] for c in matches],'depth':depth,'summary':summary,
            'omitted_edges':len(all_edges)-len(keep),'node_limit':limit,
            'catalog':list(CONCEPTS.values())}

def evidence(path,owner,offset=0,limit=12):
    ensure_projection(path);offset=max(0,int(offset));limit=max(1,min(20,int(limit)))
    with closing(connect(path)) as db:
        edge=db.execute('SELECT * FROM cg_links WHERE id=?',(owner,)).fetchone()
        if owner not in CONCEPTS and not edge:raise ValueError('Unknown graph item')
        pages=db.execute('SELECT DISTINCT doc_id,page FROM cg_evidence WHERE owner=? ORDER BY doc_id,page',(owner,)).fetchall()
        out=[]
        for doc,page in pages[offset:offset+limit]:
            d=db.execute('SELECT title,metadata FROM documents WHERE id=?',(doc,)).fetchone();meta=json.loads(d['metadata'])
            refs=db.execute('SELECT chunk_id,claim_id FROM cg_evidence WHERE owner=? AND doc_id=? AND page=?',(owner,doc,page)).fetchall()
            excerpts=[];claims=[]
            for chunk,claim in refs:
                if chunk:
                    r=db.execute('SELECT text,language,quality FROM chunks WHERE id=?',(chunk,)).fetchone()
                    excerpts.append({'id':chunk,**dict(r)})
                if claim:
                    r=dict(db.execute('SELECT * FROM claims WHERE id=?',(claim,)).fetchone())
                    r['mapping']={x:endpoint_concept(r[x],r[x+'_type'])[1] for x in ['source','target']}
                    claims.append(r)
            out.append({'doc_id':doc,'title':d['title'],'page':page,'url':'/api/knowledge/document?id='+doc+'#page='+str(page),
                        'scope':meta.get('document_scope'),'validity':meta.get('validity'),
                        'excerpts':excerpts,'claims':claims})
    return {'owner':owner,'edge':dict(edge) if edge else None,'total':len(pages),'offset':offset,
            'next_offset':offset+limit if offset+limit<len(pages) else None,'evidence':out}
