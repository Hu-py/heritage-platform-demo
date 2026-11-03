"""Local-only knowledge API. PDFs and the database stay outside public/."""
from pathlib import Path
import sys,json,shutil
from urllib.parse import parse_qs,urlparse,quote
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'heritage-knowledge'))
from kg import KnowledgeBase
from llm import capabilities,generate
KB=KnowledgeBase()
def reply(handler,data,status=200):
 body=json.dumps(data,ensure_ascii=False).encode();handler.send_response(status);handler.send_header('Content-Type','application/json; charset=utf-8');handler.send_header('Content-Length',str(len(body)));handler.send_header('Cache-Control','no-store');handler.send_header('X-Content-Type-Options','nosniff');handler.end_headers();handler.wfile.write(body)
def handle(handler):
 u=urlparse(handler.path)
 if not u.path.startswith('/api/knowledge/'):return False
 try:
  q=parse_qs(u.query);get=lambda key,default='':q.get(key,[default])[0];action=u.path.rsplit('/',1)[-1]
  if handler.command=='POST':
   origin=handler.headers.get('Origin')
   if origin and urlparse(origin).netloc!=handler.headers.get('Host'):reply(handler,{'error':'Cross-origin request rejected'},403);return True
   if action!='generate':reply(handler,{'error':'Unknown action'},404);return True
   size=int(handler.headers.get('Content-Length','0'))
   if not 0<size<=16000:raise ValueError('Invalid request size')
   data=json.loads(handler.rfile.read(size));bundle=KB.planning_bundle(str(data.get('site_id','')),str(data.get('risk','development')),str(data.get('query',''))[:1000]);reply(handler,generate(bundle));return True
  if action=='status':reply(handler,{'build':KB.status(),'llm':capabilities()})
  elif action=='search':reply(handler,KB.search(get('q'),int(get('limit','8')),get('site_id') or None))
  elif action=='documents':reply(handler,{'documents':KB.documents()})
  elif action=='plan':reply(handler,KB.planning_bundle(get('site_id'),get('risk','development'),get('q')))
  elif action=='document':
   path=KB.document_path(get('id'));handler.send_response(200);handler.send_header('Content-Type','application/pdf');handler.send_header('Content-Length',str(path.stat().st_size));handler.send_header('Content-Disposition',"inline; filename*=UTF-8''"+quote(path.name));handler.send_header('X-Content-Type-Options','nosniff');handler.end_headers()
   with path.open('rb') as stream:shutil.copyfileobj(stream,handler.wfile)
  else:reply(handler,{'error':'Unknown knowledge endpoint'},404)
 except (ValueError,KeyError,json.JSONDecodeError) as e:reply(handler,{'error':str(e)},400)
 except FileNotFoundError:reply(handler,{'error':'知识库尚未构建，请运行 heritage-knowledge/cli.py build'},503)
 except Exception as e:
  # No tracebacks, credentials or provider response bodies to the browser.
  reply(handler,{'error':str(e) if isinstance(e,RuntimeError) else '知识服务暂不可用：'+type(e).__name__},503)
 return True
