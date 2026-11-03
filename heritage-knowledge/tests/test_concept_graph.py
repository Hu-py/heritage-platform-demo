import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kg import DB,connect,normalized
from concept_graph import graph,evidence,endpoint_concept

class ConceptGraphTests(unittest.TestCase):
 def test_bilingual_center(self):
  self.assertEqual(graph(DB,'施工振动')['center'],graph(DB,'Construction Vibration')['center'])
  self.assertEqual(graph(DB,'施工振动')['center'],'concept:vibration')
 def test_depth_and_paths(self):
  a=graph(DB,center='concept:vibration',depth=1,kind='route');b=graph(DB,center='concept:vibration',depth=2,kind='route')
  self.assertGreater(len(b['nodes']),len(a['nodes']))
  ids={n['id'] for n in b['nodes']};self.assertTrue(all(e['source'] in ids and e['target'] in ids for e in b['edges']))
 def test_routes_are_not_evidence(self):
  g=graph(DB,center='concept:vibration',kind='route')
  for e in g['edges']:
   self.assertEqual(e['evidence_count'],0);self.assertEqual(evidence(DB,e['id'])['evidence'],[])
 def test_unknown_and_invalid(self):
  self.assertFalse(graph(DB,'nonsense_not_a_concept')['nodes'])
  with self.assertRaises(ValueError):evidence(DB,"' OR 1=1 --")
  with self.assertRaises(ValueError):graph(DB,center='fake')
 def test_exact_evidence_counts_and_original_quotes(self):
  g=graph(DB,'施工振动')
  for owner in [g['nodes'][0]]+g['edges'][:8]:
   r=evidence(DB,owner['id']);self.assertEqual(r['total'],owner['evidence_count'])
   self.assertEqual(len({(e['doc_id'],e['page']) for e in r['evidence']}),len(r['evidence']))
   with connect(DB) as db:
    for e in r['evidence']:
     page=db.execute('SELECT text FROM pages WHERE doc_id=? AND page=?',(e['doc_id'],e['page'])).fetchone()[0]
     for p in e['excerpts']:self.assertIn(p['text'],page)
     for c in e['claims']:self.assertIn(normalized(c['quote']),normalized(page))
 def test_ambiguous_entities_not_merged(self):
  self.assertEqual(endpoint_concept('振动和沉降','风险问题')[0],None)
  self.assertEqual(endpoint_concept('Monitoring','具体措施'),('concept:monitoring','exact_alias'))
 def test_candidate_provenance(self):
  g=graph(DB,kind='candidate');self.assertTrue(g['edges'])
  for e in g['edges']:
   for p in evidence(DB,e['id'])['evidence']:
    self.assertTrue(p['claims']);self.assertTrue(all(c['status']=='candidate_requires_review' for c in p['claims']))
 def test_pagination(self):
  a=evidence(DB,'concept:monitoring',limit=2);b=evidence(DB,'concept:monitoring',offset=2,limit=2)
  self.assertEqual(a['next_offset'],2);self.assertFalse({(e['doc_id'],e['page']) for e in a['evidence']}&{(e['doc_id'],e['page']) for e in b['evidence']})
if __name__=='__main__':unittest.main()
