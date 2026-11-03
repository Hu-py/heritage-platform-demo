/* Concept-only projection; PDFs and verbatim evidence are loaded on selection. */
window.conceptExplorer=(()=>{
 const el=id=>document.getElementById(id),escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const kinds={risk:['风险问题','#cc7a83'],principle:['保护原则','#c5ad78'],strategy:['规划策略','#78b39c'],measure:['具体措施','#74a9c9'],material:['材料结构','#b39aca'],building_type:['建筑类型','#c89365'],regulation:['法规规范','#93a7d1'],case:['保护案例','#a7b979'],legal_status:['保护身份','#b5a38b'],place:['地域','#8e9999']};
 const relationNames={candidate:'专业候选关系 · 待复核',route:'检索扩展 · 非证据',cooccurrence:'同段共现 · 非因果'};
 let data,simulation,zoom,svg,layer,request=0,detailRequest=0,query='',center='',paused=false,selected=null;
 async function get(path){const r=await fetch('/api/knowledge/'+path);const d=await r.json();if(!r.ok)throw Error(d.error||'图谱加载失败');return d}
 const color=n=>(kinds[n.kind]||['其他','#99a6a0'])[1];
 function fit(){if(!layer||!data?.nodes.length)return;const b=layer.node().getBBox();if(!b.width||!b.height)return;const scale=Math.min(1.5,840/(b.width+100),490/(b.height+100));svg.call(zoom.transform,d3.zoomIdentity.translate(460-(b.x+b.width/2)*scale,285-(b.y+b.height/2)*scale).scale(scale))}
 function highlight(id){if(!layer)return;layer.selectAll('.concept-node').classed('chosen',n=>n.id===id);layer.selectAll('.concept-edge').classed('chosen',e=>e.id===id)}
 async function showEvidence(item,isEdge=false,offset=0){
  const token=++detailRequest;selected=item;highlight(item.id);
  if(!offset){el('conceptDetail').innerHTML=`<div class="detail-head"><span class="eyebrow">${isEdge?'RELATION':'CONCEPT'}</span><h2>${escape(isEdge?item.relation:item.zh)}</h2>${isEdge?`<p>${escape(data.nodes.find(n=>n.id===item.source)?.zh||item.source)} → ${escape(data.nodes.find(n=>n.id===item.target)?.zh||item.target)}</p><span class="tag">${relationNames[item.kind]}</span>`:`<p>${escape(item.en)}</p><span class="tag">${escape(kinds[item.kind]?.[0]||item.kind)}</span><p class="muted">别名：${escape(item.aliases.join(' / '))}</p><button id="useConcept">以此为中心展开</button>`}<p>${item.evidence_count} 个原文证据页</p></div><div id="detailEvidence">正在读取证据…</div>`;if(!isEdge)el('useConcept').onclick=()=>{center=item.id;query=item.zh;load()}}
  try{const d=await get('graph-evidence?id='+encodeURIComponent(item.id)+'&offset='+offset);if(token!==detailRequest)return;
   const html=d.evidence.map(e=>`<div class="graph-evidence"><h3>${escape(e.title)}</h3><a href="${escape(e.url)}" target="_blank" rel="noopener">PDF 第 ${e.page} 页 ↗</a><p class="muted">适用范围：${escape(e.scope||'待核验')} · 时效：${escape(e.validity||'待核验')}</p>${e.claims.map(c=>`<p><b>${escape(c.source)} → ${escape(c.relation)} → ${escape(c.target)}</b></p><p class="quote">${escape(c.quote)}</p><p class="muted">候选关系，未通过语义核验 · ${escape(c.kind)}<br>条件：${escape(c.condition||'未明确摘录')}<br>概念映射：${Object.values(c.mapping).includes('lexical_candidate')?'词面匹配候选，需复核':'精确别名匹配'}</p>`).join('')}${e.excerpts.map(x=>`<p class="quote">${escape(x.text)}</p><span class="muted">${escape(x.language)} · ${escape(x.quality)}</span>`).join('')}</div>`).join('');
   if(!offset)el('detailEvidence').innerHTML=html||(isEdge&&item.kind==='route'?'<p class="notice">这是 ontology 中的检索扩展规则，没有直接原文证据；不能作为保护措施的依据。</p>':'<p class="notice">暂无关联原文。</p>');else{el('moreEvidence')?.remove();el('detailEvidence').insertAdjacentHTML('beforeend',html)}
   if(d.next_offset!==null){el('detailEvidence').insertAdjacentHTML('beforeend',`<button id="moreEvidence">更多证据（共 ${d.total} 页）</button>`);el('moreEvidence').onclick=()=>showEvidence(item,isEdge,d.next_offset)}
  }catch(e){if(token===detailRequest)el('detailEvidence').textContent=e.message}
 }
 function draw(){
  if(!window.d3){el('graphSummary').textContent='D3 本地资源加载失败，请刷新页面。';return}
  simulation?.stop();svg=d3.select('#conceptSvg');svg.selectAll('*').remove();svg.attr('viewBox','0 0 920 590');layer=svg.append('g');
  zoom=d3.zoom().scaleExtent([.18,5]).on('zoom',e=>{layer.attr('transform',e.transform);layer.selectAll('.node-label').style('font-size',`${11/e.transform.k}px`);layer.selectAll('.node-count').style('font-size',`${8/e.transform.k}px`);layer.selectAll('.edge-caption').style('font-size',`${10/e.transform.k}px`)});svg.call(zoom).on('dblclick.zoom',null);
  const nodes=data.nodes.map(n=>({...n})),edges=data.edges.map(e=>({...e}));
  const paths=layer.append('g').selectAll('g').data(edges).join('g').attr('class',e=>'concept-edge '+e.kind).attr('role','button').attr('tabindex',0).attr('aria-label',e=>e.relation+'，'+e.evidence_count+'个证据页').on('click',(event,e)=>{event.stopPropagation();showEvidence(data.edges.find(x=>x.id===e.id),true)}).on('keydown',(event,e)=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();showEvidence(data.edges.find(x=>x.id===e.id),true)}});
  paths.append('line').attr('class','edge-hit');paths.append('line').attr('class','edge-visible');paths.append('title').text(e=>relationNames[e.kind]+' · '+e.relation+' · '+e.evidence_count+' 个证据页');
  paths.filter(e=>e.kind==='candidate').append('text').attr('class','edge-caption').text(e=>e.relation+' · '+e.evidence_count);
  const groups=layer.append('g').selectAll('g').data(nodes).join('g').attr('class',n=>'concept-node'+(n.central?' central':'')).attr('role','button').attr('tabindex',0).attr('aria-label',n=>n.zh+' '+n.en+'，'+n.evidence_count+'个证据页').on('click',(event,n)=>{event.stopPropagation();showEvidence(n)}).on('keydown',(event,n)=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();showEvidence(n)}});
  groups.append('circle').attr('r',n=>n.central?25:12+Math.min(8,Math.sqrt(n.evidence_count))).attr('fill',color);
  groups.append('text').attr('class','node-label').attr('y',n=>n.central?43:35).attr('text-anchor','middle').text(n=>n.zh.length>10?n.zh.slice(0,9)+'…':n.zh);
  groups.append('text').attr('class','node-count').attr('text-anchor','middle').attr('y',4).text(n=>n.evidence_count);
  groups.append('title').text(n=>n.zh+' / '+n.en);
  simulation=d3.forceSimulation(nodes).force('link',d3.forceLink(edges).id(n=>n.id).distance(130).strength(.2)).force('charge',d3.forceManyBody().strength(-500)).force('collision',d3.forceCollide(60)).force('center',d3.forceCenter(460,270)).force('x',d3.forceX(460).strength(.035)).force('y',d3.forceY(270).strength(.035));
  groups.call(d3.drag().on('start',(e,n)=>{if(!paused&&!e.active)simulation.alphaTarget(.15).restart();n.fx=n.x;n.fy=n.y}).on('drag',(e,n)=>{n.fx=e.x;n.fy=e.y;n.x=e.x;n.y=e.y;if(paused)tick()}).on('end',(e,n)=>{simulation.alphaTarget(0);n.fx=null;n.fy=null}));
  function tick(){paths.selectAll('line').attr('x1',e=>e.source.x).attr('y1',e=>e.source.y).attr('x2',e=>e.target.x).attr('y2',e=>e.target.y);paths.select('text').attr('x',e=>(e.source.x+e.target.x)/2).attr('y',e=>(e.source.y+e.target.y)/2);groups.attr('transform',n=>`translate(${n.x},${n.y})`)}
  simulation.stop();for(let i=0;i<180;i++)simulation.tick();tick();fit();simulation.on('tick',tick);if(!paused)simulation.alpha(.12).restart();
  el('graphLegend').innerHTML=Object.entries(kinds).filter(([k])=>nodes.some(n=>n.kind===k)).map(([,v])=>`<span><i style="background:${v[1]}"></i>${v[0]}</span>`).join('');
 }
 async function load(){const token=++request;el('graphSummary').textContent='正在聚合概念与证据…';try{const d=await get('concept-graph?'+new URLSearchParams({q:query,center,depth:el('graphDepth').value,kind:el('graphKind').value}));if(token!==request)return;data=d;detailRequest++;selected=null;
  el('graphCenter').innerHTML='<option value="">选择中心概念</option>'+d.catalog.map(c=>`<option value="${escape(c.id)}">${escape(c.zh)} / ${escape(c.en)}</option>`).join('');el('graphCenter').value=d.center||'';
  el('graphSummary').innerHTML=`<strong>${d.nodes.length}</strong> 个概念 <strong>${d.edges.length}</strong> 条关联 <span>${d.center?'中心：'+escape(d.nodes.find(n=>n.id===d.center).zh):query?'未匹配到概念，请使用专业术语或选择中心概念':'全库概览'}${d.omitted_edges?' · 已收起 '+d.omitted_edges+' 条次要连线':''}</span>`;
  el('graphCoverage').textContent=`现有 ${d.summary.concepts} 个标准概念，${d.summary.mapped_claims} 条候选关系可映射到概念两端；${d.summary.unmapped_claims} 条尚未映射或不能形成独立概念边，仍可在候选专业关系中检索。`;
  el('conceptDetail').innerHTML='<div class="detail-intro"><span class="eyebrow">EVIDENCE PANEL</span><h2>追溯概念背后的原文。</h2><p>点击节点查看概念证据；点击连线查看关系性质、文献和页码。</p><p>实线：专业候选关系<br>虚线：检索扩展规则<br>细线：同段共现</p></div>';draw();
 }catch(e){if(token===request)el('graphSummary').textContent=e.message}}
 el('graphCenter').onchange=()=>{center=el('graphCenter').value;query='';load()};el('graphDepth').onchange=load;el('graphKind').onchange=load;el('graphOverview').onclick=()=>{query='';center='';load()};el('graphFit').onclick=fit;
 el('graphPause').onclick=()=>{paused=!paused;el('graphPause').textContent=paused?'继续布局':'暂停布局';if(simulation){if(paused)simulation.stop();else simulation.alpha(.3).restart()}};
 el('graphZoomIn').onclick=()=>svg?.call(zoom.scaleBy,1.3);el('graphZoomOut').onclick=()=>svg?.call(zoom.scaleBy,1/1.3);
 el('graphEnrich').onclick=async()=>{const concept=data?.nodes.find(n=>n.id===data.center);if(!concept){el('enrichStatus').textContent='请先选择一个中心概念。';return}el('graphEnrich').disabled=true;el('enrichStatus').textContent='正在根据最多 3 条原文提取候选关系…';try{const r=await fetch('/api/knowledge/enrich',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:concept.zh+' '+concept.en})});const d=await r.json();if(!r.ok)throw Error(d.error||'补充失败');el('enrichStatus').textContent=`已入库 ${d.results.reduce((n,x)=>n+x.accepted.length,0)} 条候选记录，需复核。`;await load()}catch(e){el('enrichStatus').textContent=e.message}finally{el('graphEnrich').disabled=false}};
 return {search(q){query=q;center='';load()},configure(llm){el('graphEnrich').disabled=!llm.configured;el('enrichStatus').textContent=llm.configured?'仅在点击后发送检索片段':'DeepSeek 尚未配置；本地图谱与证据检索可正常使用。'}};
})();
