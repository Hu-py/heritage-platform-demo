"""Page-preserving PDF extraction, SHA deduplication and selective local OCR."""
import argparse, concurrent.futures, csv, hashlib, json, os, re, shutil, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; WORKSPACE=ROOT.parent
PDFTOTEXT=shutil.which('pdftotext') or '/opt/anaconda3/bin/pdftotext'
PDFTOPPM=shutil.which('pdftoppm') or '/opt/anaconda3/bin/pdftoppm'
TESSERACT=shutil.which('tesseract') or '/opt/homebrew/bin/tesseract'
def meaningful(text):return len(re.sub(r'\s','',text))
def ocr_page(path,page):
 with tempfile.TemporaryDirectory(prefix='herisk-ocr-') as temp:
  target=Path(temp)/'page'
  subprocess.run([PDFTOPPM,'-f',str(page),'-l',str(page),'-r','180','-png','-singlefile',str(path),str(target)],capture_output=True,check=True,timeout=90)
  env=dict(os.environ,OMP_THREAD_LIMIT='1')
  r=subprocess.run([TESSERACT,str(target)+'.png','stdout','-l','chi_sim+eng','--psm','3'],capture_output=True,check=True,timeout=150,env=env)
  return r.stdout.decode('utf-8','replace')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=WORKSPACE/'规划数据库');parser.add_argument('--workers',type=int,default=3);args=parser.parse_args()
 dest=ROOT/'data/extracted';dest.mkdir(parents=True,exist_ok=True)
 metadata={}
 for path in args.source.rglob('PDF来源清单.csv'):
  with path.open(encoding='utf-8-sig',newline='') as f:
   for row in csv.DictReader(f):metadata[row['filename']]=row
 seen={};manifest=[];pending=[]
 for path in sorted(args.source.rglob('*.pdf')):
  if path.name.startswith('._') or not ('已下载PDF' in str(path) or 'RAG_datasource' in str(path)):continue
  digest=hashlib.sha256(path.read_bytes()).hexdigest();doc_id='doc:'+digest[:20]
  if digest in seen:seen[digest]['duplicates'].append(str(path.relative_to(WORKSPACE)));continue
  meta=metadata.get(path.name,{})
  record={'id':doc_id,'sha256':digest,'path':str(path.relative_to(WORKSPACE)),'filename':path.name,'title':meta.get('title',path.stem),'category':meta.get('category',path.parent.name),'publisher':meta.get('source','未登记'),'year':meta.get('year',''),'url':meta.get('url',''),'source_note':meta.get('note',''),'access':meta.get('access','未登记'),'duplicates':[],'validity':'not_verified','licence':'source_terms_apply_not_for_redistribution'}
  if '批准实施通知' in path.name:record['document_scope']='approval_notice_not_standard_fulltext'
  elif 'GB55035' in path.name:record['document_scope']='excludes_cultural_relic_buildings_and_protected_sites_article_1_0_2'
  else:record['document_scope']='applicability_requires_review'
  seen[digest]=record;manifest.append(record);cache=dest/(digest+'.json')
  if cache.exists():
   record['cache']=cache.name;continue
  old_caches=list((WORKSPACE/'规划数据库/rag_workbench/human_activity_output/page_cache').glob('*-'+digest+'.json'))
  if old_caches:
   old=json.loads(old_caches[0].read_text());texts=old.get('texts',[])
   if texts:
    record['cache']=cache.name
    record['_pages']=[{'page':i+1,'text':t,'method':'hash_verified_imported_cache','quality':'imported_ocr_requires_review','characters':meaningful(t)} for i,t in enumerate(texts)]
    record['source_note']+=' Imported page cache matched SHA256; OCR and semantic accuracy unreviewed.'
    record['category']='既有专题知识库'
    continue
  process=subprocess.run([PDFTOTEXT,str(path),'-'],capture_output=True,timeout=90,check=True)
  pages=process.stdout.decode('utf-8','replace').split('\f')
  if not pages[-1].strip():pages.pop()
  page_records=[]
  for i,text in enumerate(pages,1):
   # Low-content scans, including PDFs whose only text layer is a watermark.
   low=meaningful(text)<100
   pg={'page':i,'text':text,'method':'pdf_text','quality':'unreviewed','characters':meaningful(text)};page_records.append(pg)
   if low:pending.append((path,i,pg))
  record['cache']=cache.name;record['_pages']=page_records
 print('Documents',len(manifest),'OCR pages',len(pending),flush=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
  futures={pool.submit(ocr_page,path,page):(path,page,pg) for path,page,pg in pending}
  for future in concurrent.futures.as_completed(futures):
   path,page,pg=futures[future]
   try:
    value=future.result();pg.update(text=value,method='tesseract_chi_sim_eng',characters=meaningful(value),quality='ocr_requires_review' if meaningful(value)>=100 else 'low_text')
   except Exception as e:pg.update(quality='ocr_failed',error=type(e).__name__)
   print('OCR',path.name,page,pg['characters'],pg['quality'],flush=True)
 for record in manifest:
  pages=record.pop('_pages',None)
  if pages is not None:(dest/record['cache']).write_text(json.dumps(pages,ensure_ascii=False),encoding='utf-8')
  else:pages=json.loads((dest/record['cache']).read_text())
  record.update(page_count=len(pages),text_characters=sum(x['characters'] for x in pages),ocr_pages=sum(x['method'].startswith('tesseract') for x in pages),low_text_pages=[x['page'] for x in pages if x['characters']<100])
 (ROOT/'data/documents.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Extraction complete:',len(manifest),'documents',sum(x['page_count'] for x in manifest),'pages',flush=True)
if __name__=='__main__':main()
