import argparse,json
from pathlib import Path
from kg import KnowledgeBase, build, connect

def main():
 p=argparse.ArgumentParser(description='HERISK evidence graph');sub=p.add_subparsers(dest='command',required=True)
 sub.add_parser('build');sub.add_parser('status')
 s=sub.add_parser('search');s.add_argument('query');s.add_argument('--limit',type=int,default=8)
 g=sub.add_parser('plan');g.add_argument('site_id');g.add_argument('--risk',default='development');g.add_argument('--generate',action='store_true')
 e=sub.add_parser('enrich');e.add_argument('query');e.add_argument('--limit',type=int,default=8)
 x=sub.add_parser('export');x.add_argument('output',type=Path)
 args=p.parse_args();kb=KnowledgeBase()
 if args.command=='build':result=build()
 elif args.command=='status':result=kb.status()
 elif args.command=='search':result=kb.search(args.query,args.limit)
 elif args.command=='plan':
  result=kb.planning_bundle(args.site_id,args.risk)
  if args.generate:
   from llm import generate
   result=generate(result)
 elif args.command=='enrich':
  from llm import enrich
  result=enrich(kb,args.query,min(args.limit,30))
 elif args.command=='export':
  with connect(kb.path) as db:result={t:[dict(r) for r in db.execute('SELECT * FROM '+t)] for t in ['nodes','edges','claims']}
  args.output.write_text(json.dumps(result,ensure_ascii=False));print(str(args.output));return
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
