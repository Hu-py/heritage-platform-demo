import sys,unittest,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kg import KnowledgeBase,connect,normalized,validate_claim,CONCEPTS,WORKSPACE
from llm import validate_plan
class KnowledgeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.kb=KnowledgeBase()
 def test_integrity(self):
  with connect() as db:
   self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
   self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
  self.assertEqual(self.kb.status()['documents'],48);self.assertEqual(self.kb.status()['sites'],763)
 def test_source_hashes(self):
  for d in self.kb.documents():self.assertEqual(hashlib.sha256((WORKSPACE/d['path']).read_bytes()).hexdigest(),d['sha256'])
 def test_bilingual_retrieval(self):
  a=self.kb.search('施工振动 监测',12);b=self.kb.search('vibration monitoring',12)
  self.assertIn('concept:vibration',[x['id'] for x in a['concepts']]);self.assertIn('concept:vibration',[x['id'] for x in b['concepts']])
  self.assertTrue(any(x['language']=='en' for x in a['results']))
  self.assertTrue(any(x['language']=='zh' for x in self.kb.search('authenticity minimum intervention',12)['results']))
 def test_source_citations(self):
  for r in self.kb.search('游客承载量',10)['results']:
   with connect() as db:p=db.execute('SELECT text FROM pages WHERE doc_id=? AND page=?',(r['doc_id'],r['page'])).fetchone()[0]
   self.assertIn(r['text'],p);self.assertEqual(r['page'],r['citation']['pdf_page'])
 def test_imported_claims(self):
  with connect() as db:
   rows=db.execute('SELECT c.*,p.text FROM claims c JOIN pages p ON c.doc_id=p.doc_id AND c.page=p.page').fetchall()
   self.assertEqual(len(rows),79)
   for row in rows:
    self.assertIsNone(validate_claim(dict(row),row['text']));self.assertEqual(row['status'],'candidate_requires_review')
 def test_no_evidence_for_unknown_query(self):self.assertEqual(self.kb.search('zxqnevermatchingword')["results"],[])
 def test_source_path_guard(self):
  with self.assertRaises(ValueError):self.kb.document_path('../../etc/passwd')
 def test_inapplicable_standard_filtered(self):
  r=self.kb.search('历史建筑 完整性 规范',30,'G-1')
  self.assertTrue(all('GB55035' not in x['filename'] for x in r['results']))
 def test_diagnosis_does_not_become_generated_strategy(self):
  b=self.kb.planning_bundle('G-1');self.assertEqual(b['status'],'evidence_ready_generation_not_run');self.assertEqual(b['planning_response']['strategy_candidates'],[]);self.assertFalse(b['evidence_check']['semantic_support_verified'])
 def test_fabricated_quote_rejected(self):
  evidence=[{'id':'x','text':'Historic masonry should be monitored before intervention.','citation':{'pdf_page':1}}]
  item={'title':'Monitor','measures':['Inspect'],'conditions':[],'citations':[{'chunk_id':'x','quote':'A fabricated statement about concrete and demolition.'}]}
  accepted,rejected=validate_plan({'strategy_candidates':[item]},evidence);self.assertFalse(accepted);self.assertEqual(rejected[0]['reason'],'unverifiable_quote')
  item['citations']=[{'chunk_id':'x','quote':evidence[0]['text']}];accepted,rejected=validate_plan({'strategy_candidates':[item]},evidence);self.assertEqual(len(accepted),1);self.assertEqual(accepted[0]['status'],'draft_requires_expert_review')
 def test_empty_claim_fails(self):self.assertEqual(validate_claim({},''),'missing_fields')
 def test_graph_paths_reach_sources(self):
  r=self.kb.search('游客承载量');ids={n['id'] for n in r['graph']['nodes']}
  for edge in r['graph']['edges']:self.assertIn(edge['source'],ids);self.assertIn(edge['target'],ids)
  self.assertTrue(any(e['relation']=='PART_OF' for e in r['graph']['edges']))
if __name__=='__main__':unittest.main()
