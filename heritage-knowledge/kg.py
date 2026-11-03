"""HERISK evidence graph and bilingual local retrieval. No network calls on import/search."""
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
import hashlib, json, math, os, re, sqlite3, unicodedata
ROOT=Path(__file__).resolve().parent; WORKSPACE=ROOT.parent; DB=ROOT/'data/knowledge.sqlite'
ONTOLOGY=json.loads((ROOT/'ontology.json').read_text(encoding='utf-8'))
CONCEPTS={c['id']:c for c in ONTOLOGY['concepts']}
def dumps(v):return json.dumps(v,ensure_ascii=False)
def digest(v):return hashlib.sha256((v if isinstance(v,str) else dumps(v)).encode()).hexdigest()
def normalized(text):return re.sub(r'\s+','',unicodedata.normalize('NFKC',str(text))).casefold()
def tokens(text):
 text=unicodedata.normalize('NFKC',text).lower();out=re.findall(r'[a-z][a-z0-9_-]{1,}',text)
 stop={'the','and','for','with','that','this','from','are','was','were','has','have','been','will','shall','should','can','not','its','into','than','such','their','these','which','also','may','all','but','more','other','they','how','what','under'}
 out=[w for w in out if w not in stop]
 for run in re.findall(r'[\u3400-\u9fff]+',text):
  out.extend(run[i:i+2] for i in range(len(run)-1))
 return out
PATTERNS={cid:[re.compile(re.escape(a),re.I) if re.search(r'[\u3400-\u9fff]',a) else re.compile(r'\b'+re.escape(a)+r'\b',re.I) for a in c['aliases']] for cid,c in CONCEPTS.items()}
def concept_matches(text):
 text=re.sub(r'(?<=[a-z])-\n(?=[a-z])','',text,flags=re.I)
 text=re.sub(r'\s+',' ',text)
 for _ in range(2):text=re.sub(r'(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])','',text)
 return [cid for cid,patterns in PATTERNS.items() if any(p.search(text) for p in patterns)]
def language_of(text):
 c=len(re.findall(r'[\u3400-\u9fff]',text)); latin=len(re.findall(r'[a-zA-Z]',text))
 return 'zh' if c>max(20,latin*.15) else ('en' if len(re.findall(r'\b(the|and|of|for|with|heritage|conservation)\b',text,re.I))>3 else 'other')
def connect(path=DB):
 db=sqlite3.connect(path,timeout=30);db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON');return db
SCHEMA='''
CREATE TABLE documents(id TEXT PRIMARY KEY, title TEXT, filename TEXT, path TEXT, sha256 TEXT, category TEXT, metadata TEXT);
CREATE TABLE pages(doc_id TEXT,page INTEGER,text TEXT,method TEXT,quality TEXT,PRIMARY KEY(doc_id,page),FOREIGN KEY(doc_id) REFERENCES documents(id));
CREATE TABLE chunks(id TEXT PRIMARY KEY,doc_id TEXT,page INTEGER,sequence INTEGER,text TEXT,language TEXT,quality TEXT,section_hint TEXT,FOREIGN KEY(doc_id,page) REFERENCES pages(doc_id,page));
CREATE VIRTUAL TABLE search_fts USING fts5(chunk_id UNINDEXED,body,tokenize='unicode61');
CREATE TABLE concepts(id TEXT PRIMARY KEY,kind TEXT,zh TEXT,en TEXT,aliases TEXT);
CREATE TABLE mentions(chunk_id TEXT,concept_id TEXT,PRIMARY KEY(chunk_id,concept_id),FOREIGN KEY(chunk_id) REFERENCES chunks(id),FOREIGN KEY(concept_id) REFERENCES concepts(id));
CREATE INDEX mention_concept ON mentions(concept_id);
CREATE TABLE nodes(id TEXT PRIMARY KEY,kind TEXT,label TEXT,data TEXT);
CREATE TABLE edges(id TEXT PRIMARY KEY,source TEXT,target TEXT,relation TEXT,evidence_id TEXT,status TEXT,FOREIGN KEY(source) REFERENCES nodes(id),FOREIGN KEY(target) REFERENCES nodes(id));
CREATE INDEX edge_source ON edges(source);CREATE INDEX edge_target ON edges(target);
CREATE TABLE sites(id TEXT PRIMARY KEY,name TEXT,data TEXT);
CREATE TABLE claims(id TEXT PRIMARY KEY,doc_id TEXT,page INTEGER,source TEXT,source_type TEXT,relation TEXT,target TEXT,target_type TEXT,quote TEXT,kind TEXT,condition TEXT,status TEXT,provenance TEXT,FOREIGN KEY(doc_id,page) REFERENCES pages(doc_id,page));
CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT);
'''
def add_node(db,id,kind,label,data=None):db.execute('INSERT OR IGNORE INTO nodes VALUES(?,?,?,?)',(id,kind,label,dumps(data or {})))
def add_edge(db,source,target,relation,evidence=None,status='source_record'):
 db.execute('INSERT OR IGNORE INTO edges VALUES(?,?,?,?,?,?)',(digest([source,target,relation,evidence])[:32],source,target,relation,evidence,status))
def chunks_of(text,size=1400,overlap=180):
 # Page-local windows, ending at a sentence/newline where possible. No lost intervals.
 start=0
 while start<len(text):
  end=min(start+size,len(text))
  if end<len(text):
   points=[text.rfind(mark,start+size//2,end) for mark in ['\n','。','. ']];cut=max(points)
   if cut>start:end=cut+1
  value=text[start:end].strip()
  if len(value)>=70:yield value
  if end>=len(text):break
  start=max(start+1,end-overlap)
def validate_claim(c,text):
 required=['source','target','source_type','target_type','relation','quote','kind']
 if not isinstance(c,dict) or any(not isinstance(c.get(k),str) or not c[k].strip() for k in required):return 'missing_fields'
 q=normalized(c['quote'])
 if len(q)<10 or q not in normalized(text):return 'quote_not_in_page'
 if any(normalized(c[k]) not in q for k in ['source','target']):return 'entity_not_in_quote'
 condition=c.get('condition')
 if condition is not None and (not isinstance(condition,str) or normalized(condition) not in q):return 'condition_not_in_quote'
 if c['source']==c['target']:return 'identical_endpoints'
 if c['kind'] not in ['实测','实验','模拟','规范要求','作者论述','建议','observed','experimental','simulation','normative','author_statement','recommendation']:return 'unknown_evidence_kind'
 return None
def insert_claim(db,c,doc_id,page,provenance):
 pid='claim:'+digest([doc_id,page,c])[:24]
 db.execute('INSERT OR IGNORE INTO claims VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(pid,doc_id,page,c['source'],c['source_type'],c['relation'],c['target'],c['target_type'],c['quote'],c['kind'],c.get('condition'),'candidate_requires_review',dumps(provenance)))
 endpoints=[]
 for end in ['source','target']:
  nid='entity:'+digest([c[end+'_type'],normalized(c[end])])[:24];endpoints.append(nid);add_node(db,nid,c[end+'_type'],c[end])
  # Strict exact alias mapping, never merge approximate names or entity types.
  for cid,concept in CONCEPTS.items():
   if any(normalized(c[end])==normalized(a) for a in concept['aliases']):add_edge(db,nid,cid,'ALIAS_CANDIDATE',pid,'mapping_requires_review')
 add_node(db,pid,'claim',c['relation'],dict(c,status='candidate_requires_review',doc_id=doc_id,page=page))
 add_edge(db,endpoints[0],endpoints[1],c['relation'],pid,'candidate_requires_review');add_edge(db,pid,doc_id,'EVIDENCED_BY',pid,'quote_matched_not_semantically_verified')
 return pid

def current_risk_manifest():
 path=WORKSPACE/'heritage-platform/public/data/risk-v2/manifest.json'
 return json.loads(path.read_text()) if path.exists() else None

def update_site_risks(site,manifest):
 if manifest is None:return site
 site=dict(site);site['risksByCategory']={category:info['records'].get(site['id']) for category,info in manifest['categories'].items()}
 site['risks']=[dict(value,category=category,source_file=manifest['categories'][category]['filename']) for category,value in site['risksByCategory'].items() if value]
 site['risk_semantics']={'risk_value':'风险值','R_value':'韧性值，越高越好','R_degree':'0高、1中、2低韧性；用于地图赋色'}
 return site

def build():
 ROOT.joinpath('data').mkdir(exist_ok=True);temporary=DB.with_suffix('.building.sqlite')
 if temporary.exists():temporary.unlink()
 db=connect(temporary);db.executescript(SCHEMA)
 manifest=json.loads((ROOT/'data/documents.json').read_text())
 for c in CONCEPTS.values():
  db.execute('INSERT INTO concepts VALUES(?,?,?,?,?)',(c['id'],c['kind'],c['zh'],c['en'],dumps(c['aliases'])));add_node(db,c['id'],c['kind'],c['zh'],c)
 for e in ONTOLOGY['retrieval_routes']:add_edge(db,e['source'],e['target'],e['relation'],status=e['status'])
 for doc in manifest:
  db.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?)',(doc['id'],doc['title'],doc['filename'],doc['path'],doc['sha256'],doc['category'],dumps(doc)));add_node(db,doc['id'],'document',doc['title'],doc)
  pages=json.loads((ROOT/'data/extracted'/doc['cache']).read_text())
  bibliography=False
  for page in pages:
   db.execute('INSERT INTO pages VALUES(?,?,?,?,?)',(doc['id'],page['page'],page['text'],page['method'],page['quality']))
   if page['characters']<100:continue
   search_text=page['text']
   if doc['category']=='学术论文':
    ref=re.search(r'(?im)^\s*(references|bibliography|参考文献)\s*:?\s*$',search_text)
    if ref and page['page']>len(pages)*.4:
     search_text=search_text[:ref.start()];bibliography=True
    elif bibliography:continue
   for sequence,text in enumerate(chunks_of(search_text)):
    cid='chunk:'+digest([doc['sha256'],page['page'],sequence,text])[:24];lang=language_of(text);section=''
    m=re.search(r'(第[一二三四五六七八九十百零\d]+条|\bArticle\s+\d+|\b\d+\.\d+\.\d+)',text)
    if m:section=m.group()
    db.execute('INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?)',(cid,doc['id'],page['page'],sequence,text,lang,page['quality'],section))
    matched=concept_matches(text)
    body=' '.join(tokens(text))+' '+' '.join(x.replace('concept:','c_') for x in matched)
    db.execute('INSERT INTO search_fts VALUES(?,?)',(cid,body))
    add_node(db,cid,'passage',doc['title']+' · p.'+str(page['page']),{'doc_id':doc['id'],'page':page['page'],'quality':page['quality'],'language':lang})
    add_edge(db,cid,doc['id'],'PART_OF',cid)
    for concept in matched:db.execute('INSERT INTO mentions VALUES(?,?)',(cid,concept));add_edge(db,cid,concept,'MENTIONS',cid,'lexical_mention_not_causal_claim')
 # A: keep scores scoped to the individual site; do not turn inferred sensitivity into observed damage.
 source_path=WORKSPACE/'heritage-platform/public/data/sites.json';site_data=json.loads(source_path.read_text());source_id='source:heritage-sites-json'
 add_node(db,source_id,'source','HERISK sites.json',{'path':str(source_path.relative_to(WORKSPACE)),'sha256':hashlib.sha256(source_path.read_bytes()).hexdigest(),'provenance_limit':'Prepared data; not original spreadsheet row provenance.'})
 risk_manifest=current_risk_manifest()
 if risk_manifest:add_node(db,'source:risk-v2','source','建筑群风险-1 GeoJSON',{'files':{k:{'filename':v['filename'],'sha256':v['sha256']} for k,v in risk_manifest['categories'].items()}})
 for site in site_data:
  site=update_site_risks(site,risk_manifest)
  sid='site:'+site['id'];db.execute('INSERT INTO sites VALUES(?,?,?)',(site['id'],site['name'],dumps(site)));add_node(db,sid,'site',site['name'],{k:v for k,v in site.items() if k not in ['scores','indicators']});add_edge(db,sid,source_id,'RECORDED_IN')
  for key,value in site['profile'].items():
   aid=sid+':attribute:'+key;add_node(db,aid,'attribute',key+' · '+str(value),{'value':value});add_edge(db,sid,aid,'HAS_ATTRIBUTE',source_id)
  for layer in ['scores','indicators']:
   for i,row in enumerate(site[layer]):
    aid=sid+':'+layer+':'+str(i);value=row.get('敏感性评分');label=row.get('三级评价指标',row.get('评价维度',''))
    add_node(db,aid,'assessment',label,dict(row,source_pointer=site['id']+'/'+layer+'/'+str(i),score=value));add_edge(db,sid,aid,'HAS_ASSESSMENT',source_id)
    for concept in concept_matches(label):add_edge(db,aid,concept,'RETRIEVAL_HINT',source_id,'query_mapping_not_observed_damage')
  for i,risk in enumerate(site.get('risks',[])):
   rid=sid+':external:'+str(i);add_node(db,rid,'external_risk',{'background':'本底塑造','development':'开发建设','activity':'活动利用','pollution':'污染安全'}.get(risk.get('category'),'开发建设')+'外部风险',risk);add_edge(db,sid,rid,'HAS_EXTERNAL_RISK','source:risk-v2' if risk_manifest else source_id)
 # Import existing workbench claims only after matching original file hashes and page quotes.
 old=WORKSPACE/'规划数据库/rag_workbench/human_activity_output';rejected=[];accepted=0
 if (old/'claims.json').exists():
  original_docs=json.loads((old/'ingestion_report.json').read_text())['documents'];hashes={d['filename']:d['file_hash'] for d in original_docs};by_name={d['filename']:d for d in manifest}
  for claim in json.loads((old/'claims.json').read_text()):
   doc=by_name.get(claim.get('source_name'));reason=None
   if not doc or doc['sha256']!=hashes.get(claim.get('source_name')):reason='source_hash_mismatch'
   else:
    pg=db.execute('SELECT text FROM pages WHERE doc_id=? AND page=?',(doc['id'],claim['page'])).fetchone();reason=validate_claim(claim,pg['text']) if pg else 'page_missing'
   if reason:rejected.append({'claim_id':claim.get('id'),'reason':reason});continue
   insert_claim(db,claim,doc['id'],claim['page'],{'import':'rag_workbench','original_id':claim.get('id'),'source_sha256':doc['sha256'],'cache':'hash_verified_imported_cache'});accepted+=1
 # Rebuild is reproducible: preserve validated local LLM extraction caches.
 for path in sorted((ROOT/'data/llm-extractions').glob('*.json')):
  record=json.loads(path.read_text());chunk=db.execute('SELECT * FROM chunks WHERE id=?',(record.get('chunk_id'),)).fetchone()
  if not chunk or digest(chunk['text'])!=record.get('text_hash'):continue
  from llm import ALLOWED_TYPES, ALLOWED_RELATIONS
  for claim in record.get('payload',{}).get('claims',[])[:8]:
   if validate_claim(claim,chunk['text']) is None and claim['source_type'] in ALLOWED_TYPES and claim['target_type'] in ALLOWED_TYPES and claim['relation'] in ALLOWED_RELATIONS:
    insert_claim(db,claim,chunk['doc_id'],chunk['page'],{'extractor':'DeepSeek','cache':path.name,**record.get('model_info',{})})
 stats={table:db.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in ['documents','pages','chunks','concepts','mentions','sites','claims','nodes','edges']}
 stats.update(built_at=datetime.now(timezone.utc).isoformat(),workbench_claims_imported=accepted,workbench_claims_rejected=len(rejected),retrieval='SQLite FTS5 BM25 + bilingual controlled vocabulary + 1-hop graph expansion',graph_claim_policy='Claims are candidates; mentions and routing rules are not treatment evidence.')
 db.execute('INSERT INTO meta VALUES(?,?)',('build',dumps(stats)));db.commit();assert not db.execute('PRAGMA foreign_key_check').fetchall();db.close();temporary.replace(DB)
 (ROOT/'reports/build.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2));(ROOT/'reports/import-rejections.json').write_text(json.dumps(rejected,ensure_ascii=False,indent=2))
 print(dumps(stats));return stats

class KnowledgeBase:
 def __init__(self,path=DB):self.path=Path(path)
 def status(self):
  with connect(self.path) as db:
   result=json.loads(db.execute("SELECT value FROM meta WHERE key='build'").fetchone()[0])
   for table in ['claims','nodes','edges']:result[table]=db.execute('SELECT count(*) FROM '+table).fetchone()[0]
   return result
 def documents(self):
  with connect(self.path) as db:return [json.loads(r[0]) for r in db.execute('SELECT metadata FROM documents ORDER BY category,title')]
 def site(self,id):
  with connect(self.path) as db:r=db.execute('SELECT data FROM sites WHERE id=?',(id,)).fetchone()
  if not r:raise ValueError('Unknown heritage site')
  return update_site_risks(json.loads(r[0]),current_risk_manifest())
 def document_path(self,id):
  with connect(self.path) as db:r=db.execute('SELECT path FROM documents WHERE id=?',(id,)).fetchone()
  if not r:raise ValueError('Unknown document')
  path=(WORKSPACE/r['path']).resolve()
  if not path.is_relative_to((WORKSPACE/'规划数据库').resolve()):raise ValueError('Source path outside library')
  return path
 def search(self,query,limit=8,site_id=None):
  query=str(query).strip()[:1000];limit=min(max(int(limit),1),30)
  if not query:return {'query':query,'results':[],'concepts':[],'expanded_concepts':[],'claims':[],'graph':{'nodes':[],'edges':[]}}
  direct=concept_matches(query);expanded=list(dict.fromkeys(e['target'] for e in ONTOLOGY['retrieval_routes'] if e['source'] in direct and e['target'] not in direct))
  words=list(dict.fromkeys(tokens(query)))[:60];words+=['c_'+c.split(':',1)[1] for c in direct+expanded]
  match=' OR '.join('"'+w.replace('"','""')+'"' for w in words)
  if not match:return {'query':query,'results':[],'concepts':[],'expanded_concepts':[],'claims':[],'graph':{'nodes':[],'edges':[]}}
  with connect(self.path) as db:
   rows=db.execute('''SELECT c.*,d.title,d.filename,d.category,d.metadata,bm25(search_fts) rank FROM search_fts JOIN chunks c ON c.id=search_fts.chunk_id JOIN documents d ON d.id=c.doc_id WHERE search_fts MATCH ? ORDER BY rank LIMIT 300''',(match,)).fetchall()
   candidates=[]
   for row in rows:
    r=dict(row);meta=json.loads(r.pop('metadata'));matched=[v[0] for v in db.execute('SELECT concept_id FROM mentions WHERE chunk_id=?',(r['id'],))]
    direct_hits=list(set(matched)&set(direct));exp_hits=list(set(matched)&set(expanded))
    r['retrieval_score']=round(math.log1p(abs(r.pop('rank')))*.7+len(direct_hits)*3+len(exp_hits)*.5,4)
    if r['language']=='other':r['retrieval_score']*=.55
    r['matched_concepts']=direct_hits;r['expanded_concepts']=exp_hits;r['source_url']=meta['url'];r['scope']=meta['document_scope'];r['validity']=meta['validity']
    r['applicability']='not_verified';r['review_status']='source_and_applicability_require_review'
    if 'excludes_cultural_relic' in r['scope']:
     r['applicability']='excludes_cultural_relic_buildings';r['scope_note']='GB 55035 第1.0.2条注明文物建筑和文物保护单位除外；不得作为这些对象的直接适用规范。'
     if site_id:continue
    if r['scope']=='approval_notice_not_standard_fulltext':r['scope_note']='批准实施通知，不是标准条文全文。';r['retrieval_score']*=.4
    r['citation']={'id':r['id'],'document_id':r['doc_id'],'title':r['title'],'pdf_page':r['page'],'section_hint':r['section_hint'],'original_language':r['language'],'text_method':db.execute('SELECT method FROM pages WHERE doc_id=? AND page=?',(r['doc_id'],r['page'])).fetchone()[0],'url':'/api/knowledge/document?id='+r['doc_id']+'#page='+str(r['page'])}
    candidates.append(r)
   candidates.sort(key=lambda r:r['retrieval_score'],reverse=True);results=[];per_doc=defaultdict(int);seen=set()
   for r in candidates:
    key=(r['doc_id'],r['page'])
    if key in seen or per_doc[r['doc_id']]>=2:continue
    results.append(r);seen.add(key);per_doc[r['doc_id']]+=1
    if len(results)>=limit:break
   claims=[]
   for row in db.execute('SELECT * FROM claims'):
    c=dict(row);hits=set(concept_matches(c['quote']))&set(direct)
    literal=any(w in normalized(c['quote']) for w in words if not w.startswith('c_') and len(w)>2)
    if hits or literal:
     c['matched_concepts']=list(hits);c['citation_url']='/api/knowledge/document?id='+c['doc_id']+'#page='+str(c['page']);claims.append(c)
   claims.sort(key=lambda c:len(c['matched_concepts']),reverse=True);claims=claims[:8]
  graph=self.retrieval_graph(results,direct,expanded,claims,site_id)
  return {'query':query,'concepts':[CONCEPTS[c] for c in direct],'expanded_concepts':[CONCEPTS[c] for c in expanded],'results':results,'claims':claims,'graph':graph,'method':'BM25 + controlled bilingual aliases + graph expansion; not neural embedding retrieval','warnings':['匹配表示相关材料，不等于适用性或因果关系已核验。','PDF页码为物理页码；OCR文字需对照原件。']}
 def retrieval_graph(self,results,direct,expanded,claims,site_id):
  nodes={};edges=[]
  def n(id,label,kind,**kw):nodes[id]={'id':id,'label':label,'kind':kind,**kw}
  for c in direct+expanded:n(c,CONCEPTS[c]['zh'],CONCEPTS[c]['kind'])
  for e in ONTOLOGY['retrieval_routes']:
   if e['source'] in nodes and e['target'] in nodes:edges.append(e)
  if site_id:
   site=self.site(site_id);n('site:'+site_id,site['name'],'site')
   for c in direct:edges.append({'source':'site:'+site_id,'target':c,'relation':'RETRIEVAL_HINT','status':'query_mapping_not_damage'})
  for r in results:
   n(r['doc_id'],r['title'],'document');n(r['id'],'p.'+str(r['page']),'passage',citation=r['citation'])
   edges.append({'source':r['id'],'target':r['doc_id'],'relation':'PART_OF'})
   for c in r['matched_concepts']+r['expanded_concepts']:edges.append({'source':r['id'],'target':c,'relation':'MENTIONS'})
  doc_titles={d['id']:d['title'] for d in self.documents()}
  for c in claims:
   ids=[]
   for end in ['source','target']:
    id='entity:'+digest([c[end+'_type'],normalized(c[end])])[:24];n(id,c[end],c[end+'_type']);ids.append(id)
   edges.append({'source':ids[0],'target':ids[1],'relation':c['relation'],'status':c['status'],'claim_id':c['id'],'quote':c['quote']})
   n(c['doc_id'],doc_titles.get(c['doc_id'],c['doc_id']),'document')
   edges.append({'source':ids[0],'target':c['doc_id'],'relation':'EVIDENCED_BY','status':c['status'],'claim_id':c['id'],'quote':c['quote'],'citation_url':c['citation_url']})
  return {'nodes':list(nodes.values()),'edges':edges}
 def planning_bundle(self,site_id,risk='development',query=''):
  site=self.site(site_id);terms={'development':'施工振动 沉降 开发建设 结构病害','background':'真实性 完整性 历史环境','activity':'活动利用 游客压力 适应性再利用','pollution':'污染 水湿病害 材料修复','opinion':'舆论 公众参与 遗产阐释','composite':'真实性 完整性 风险评估','none':'保护原则'}
  q=query or terms.get(risk,terms['development'])+' '+site.get('profile',{}).get('建造材','')
  found=self.search(q,8,site_id)
  missing=sorted({str(r['缺失信息']) for r in site['indicators'] if r.get('缺失信息') and r['缺失信息']!='无'})
  return {'status':'evidence_ready_generation_not_run','site_id':site_id,'site_name':site['name'],'risk_category':risk,'diagnosis':{'profile':site['profile'],'scores':[{k:r.get(k) for k in ['评价维度','敏感性评分','证据','推理依据']} for r in site['scores']],'external_risk':[x for x in site.get('risks',[]) if x.get('category',risk)==risk],'risk_semantics':site.get('risk_semantics',{}),'note':'Sensitivity scores are not verified observed damage. risk_value is risk; R_value is resilience (higher is better). No cross-category normalization is assumed.'},'retrieval':found,'evidence_check':{'citation_locations_verified':True,'semantic_support_verified':False,'legal_applicability_verified':False,'current_validity_verified':False},'planning_response':{'protection_objectives':[],'strategy_candidates':[],'measures':[],'monitoring':[],'evidence_gaps':missing,'review_required':True},'message':'已检索专业依据；未调用模型生成策略。候选关系不等于经过核验的处置建议。'}
