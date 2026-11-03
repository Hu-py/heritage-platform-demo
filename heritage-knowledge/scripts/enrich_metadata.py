from pathlib import Path
import json,re,subprocess
ROOT=Path(__file__).resolve().parents[1];path=ROOT/'data/documents.json';docs=json.loads(path.read_text())
for doc in docs:
 out=subprocess.run(['/opt/anaconda3/bin/pdfinfo',str(ROOT.parent/doc['path'])],capture_output=True,text=True).stdout
 fields={m.group(1).lower():m.group(2).strip() for m in re.finditer(r'^(Title|Author|Subject):\s*(.+)$',out,re.M)}
 title=fields.get('title','')
 if doc['title']==Path(doc['filename']).stem and len(title)>15 and not any(x in title.lower() for x in ['microsoft word','untitled','adobe','untitled']):doc['title']=title;doc['title_origin']='embedded_pdf_metadata_unreviewed'
 doc['pdf_metadata']=fields
 doi=re.search(r'(10\.\d{4,9}/[^\s]+)',fields.get('subject',''))
 if doi and not doc['url']:doc['url']='https://doi.org/'+doi.group(1).rstrip('.,;')
path.write_text(json.dumps(docs,ensure_ascii=False,indent=2));print('Metadata enriched:',len(docs))
