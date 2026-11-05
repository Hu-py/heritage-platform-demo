// Evidence retrieval is automatic; paid generation requires an explicit click.
let planRequest=0;
const scatterRiskLabels={background:['本底塑造','Historical setting'],development:['开发建设','Development'],activity:['活动利用','Use & activities'],pollution:['污染安全','Pollution & safety'],opinion:['舆论引导','Public attention']};
const scatterVulnerabilityLabels=[['历史价值敏感性','Historical-value vulnerability'],['开发建设敏感性','Development vulnerability'],['活动利用敏感性','Use vulnerability'],['环境污染敏感性','Pollution vulnerability'],['舆论传播敏感性','Public-attention vulnerability']];

function scatterControls(risk){
 const defaultDim=Math.max(0,riskDims[risk]??1),defaultRisk=scatterRiskLabels[risk]?risk:'development';
 return `<section class="cross-risk-panel"><div class="cross-risk-heading"><div><small>${tx('全市文物资源交叉定位 · 五类一一对应','CITY-WIDE POSITION · FIVE PAIRED CATEGORIES')}</small><h2>${tx('本体脆弱性 × 规模化风险','Intrinsic vulnerability × scaled risk')}</h2></div><div class="scatter-selectors"><label>${tx('本体脆弱性一级指标','Intrinsic dimension')}<select id="scatterIntrinsic">${scatterVulnerabilityLabels.map((label,i)=>`<option value="${i}" ${i===defaultDim?'selected':''}>${tx(...label)}</option>`).join('')}</select></label><span>×</span><label>${tx('对应规模化风险类别','Paired scaled-risk category')}<select id="scatterSpatial">${Object.entries(scatterRiskLabels).map(([id,label])=>`<option value="${id}" ${id===defaultRisk?'selected':''}>${tx(...label)}</option>`).join('')}</select></label></div></div><div id="crossRiskChart"></div></section>`;
}

function renderCrossRiskScatter(site){
 const target=$('crossRiskChart');if(!target)return;
 const dim=+$('scatterIntrinsic').value,risk=pairedRiskIds[dim],settings={dim,risk,direction:'desc'},bounds=metricPopulation(settings);$('scatterSpatial').value=risk;
 const data=sites.map(s=>({site:s,...crossMetric(s,settings,bounds)})).filter(d=>Number.isFinite(d.intrinsic)&&Number.isFinite(d.scaleRisk)&&Number.isFinite(d.value)).map(d=>({...d,x:d.intrinsic,y:d.scaleRisk}));
 if(!data.length){target.innerHTML=`<p class="notice">${tx('当前组合暂无可比较数据。','No comparable data for this combination.')}</p>`;return}
 const W=620,H=310,p={l:52,r:18,t:18,b:48},yMin=Math.min(...data.map(d=>d.y)),yMax=Math.max(...data.map(d=>d.y)),span=yMax-yMin||1;
 const sx=v=>p.l+(v-1)/4*(W-p.l-p.r),sy=v=>H-p.b-(v-yMin)/span*(H-p.t-p.b),selectedPoint=data.find(d=>d.site.id===site.id);
 const xTicks=[1,2,3,4,5].map(v=>`<line x1="${sx(v)}" y1="${p.t}" x2="${sx(v)}" y2="${H-p.b}"/><text x="${sx(v)}" y="${H-p.b+18}" text-anchor="middle">${v}</text>`).join('');
 const yTicks=[0,.25,.5,.75,1].map(t=>{const v=yMin+span*t,y=sy(v);return `<line x1="${p.l}" y1="${y}" x2="${W-p.r}" y2="${y}"/><text x="${p.l-8}" y="${y+3}" text-anchor="end">${number(v)}</text>`}).join('');
 const points=data.filter(d=>d.site.id!==site.id).map(d=>`<circle cx="${sx(d.x)}" cy="${sy(d.y)}" r="2.7"><title>${esc(siteName(d.site))} · ${number(d.x)} × ${number(d.y)} = ${number(d.value)}</title></circle>`).join('');
 const selectedSvg=selectedPoint?`<line class="selected-guide" x1="${sx(selectedPoint.x)}" y1="${p.t}" x2="${sx(selectedPoint.x)}" y2="${H-p.b}"/><line class="selected-guide" x1="${p.l}" y1="${sy(selectedPoint.y)}" x2="${W-p.r}" y2="${sy(selectedPoint.y)}"/><circle class="selected-scatter-point" cx="${sx(selectedPoint.x)}" cy="${sy(selectedPoint.y)}" r="7"><title>${esc(siteName(site))}</title></circle>`:'';
 const crossRanks=[...data].sort((a,b)=>b.value-a.value),rank=crossRanks.findIndex(d=>d.site.id===site.id)+1;
 target.innerHTML=`<svg class="cross-risk-scatter" viewBox="0 0 ${W} ${H}" role="img" aria-label="${tx('全市文物本体脆弱性与规模化风险交叉散点图','City-wide intrinsic vulnerability and scaled-risk scatter plot')}"><g class="scatter-grid">${xTicks}${yTicks}</g><g class="scatter-points">${points}</g>${selectedSvg}<text class="scatter-axis-label" x="${(p.l+W-p.r)/2}" y="${H-7}" text-anchor="middle">${esc(tx(...scatterVulnerabilityLabels[dim]))} · 1–5</text><text class="scatter-axis-label" transform="translate(13 ${(p.t+H-p.b)/2}) rotate(-90)" text-anchor="middle">${esc(tx(...scatterRiskLabels[risk]))} · ${risk==='opinion'?'risk_value*':'R_value'}</text></svg><div class="scatter-position"><span>${selectedPoint?tx('当前文物综合风险','Selected composite risk'):tx('当前文物缺少该组合数据','Selected site has no data for this pair')}</span>${selectedPoint?`<strong>${number(selectedPoint.value)}</strong><small>${tx('标准化计算','Normalized')}: ${number(selectedPoint.intrinsicNorm)} × ${number(selectedPoint.scaleRiskNorm)}<br>${tx('原始值','Raw')}: ${number(selectedPoint.x)} × ${number(selectedPoint.y)} · ${tx('综合排序','Composite rank')} ${rank} / ${data.length}${selectedPoint.scaleFallback?`<br>* ${tx('舆论类使用 risk_value 回退','Opinion uses risk_value fallback')}`:''}</small>`:`<small>${tx('图中仍显示其他可比较文物','Other comparable sites remain visible')}</small>`}</div>`;
}

function planningAction(configured){
 return `<section class="planning-action-panel comprehensive-action"><h3>${tx('生成或更新综合响应','Generate or update comprehensive response')}</h3><button id="generateComprehensive" ${configured?'':'disabled'}>${configured?tx('生成综合规划响应','Generate comprehensive response'):tx('DeepSeek 待配置 · 本地检索已可用','DeepSeek not configured · local search ready')}</button><p class="muted">${tx('综合报告覆盖全部五类风险；评分、页码与原文由本地程序回填。','Covers all five risks; scores, pages and quotations are filled locally.')}</p></section>`;
}

async function fetchComprehensive(siteId){
 return fetch('/api/knowledge/latest-report?'+new URLSearchParams({site_id:siteId,risk:'any',scope:'comprehensive'})).then(r=>r.ok?r.json():null).then(x=>x?.report||null).catch(()=>null);
}

function bindGeneration(site,risk,token){
 const button=$('generateComprehensive'),output=$('comprehensivePlan');if(!button)return;
 button.onclick=async()=>{
  button.disabled=true;output.textContent=tx('正在生成并核对引用…','Generating and checking citations…');
  try{
   const generated=await fetch('/api/knowledge/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({site_id:site.id,risk,report_scope:'comprehensive'})});
   const data=await generated.json();if(!generated.ok)throw Error(data.error);
   if(token!==planRequest||tab!=='plan'||selected?.id!==site.id)return;
   renderStructuredReport(data,output);button.textContent=tx('更新综合响应','Update comprehensive response');
  }catch(error){output.innerHTML=`<p class="notice">${esc(error.message)}</p>`}finally{button.disabled=false}
 };
}

async function renderPlanning(site,risk){
 const token=++planRequest,target=$('detail');
 target.innerHTML=`<p class="muted">${tx('正在加载综合规划响应…','Loading comprehensive planning response…')}</p>`;
 try{
  const [capability,saved]=await Promise.all([
   fetch('/api/knowledge/status').then(r=>r.json()),
   fetchComprehensive(site.id),
   riskReady.catch(()=>null)
  ]);
  if(token!==planRequest||selected?.id!==site.id||tab!=='plan')return;
  target.innerHTML=`${scatterControls(risk)}<section class="planning-level comprehensive-level"><div class="planning-level-heading"><div><small>${tx('五类风险综合决策','INTEGRATED FIVE-RISK RESPONSE')}</small><h2>${tx('综合规划响应','Comprehensive planning response')}</h2><p>${tx('整合全部文物资源本体脆弱性与空间风险，统一提出保护目标、策略与措施','Integrates all intrinsic vulnerabilities and spatial risks into unified objectives, strategies and measures')}</p></div></div><div id="comprehensivePlan"></div>${planningAction(capability.llm?.configured)}<a class="knowledge-link" target="_blank" rel="noopener" href="knowledge.html?site_id=${encodeURIComponent(site.id)}&risk=${encodeURIComponent(risk)}">${tx('打开知识库与关系图 ↗','Open library & graph ↗')}</a></section>`;
  $('scatterIntrinsic').onchange=()=>{$('scatterSpatial').value=pairedRiskIds[+$('scatterIntrinsic').value];renderCrossRiskScatter(site)};$('scatterSpatial').onchange=()=>{$('scatterIntrinsic').value=String(Math.max(0,pairedRiskIds.indexOf($('scatterSpatial').value)));renderCrossRiskScatter(site)};renderCrossRiskScatter(site);
  bindGeneration(site,risk,token);
  if(saved){renderStructuredReport(saved,$('comprehensivePlan'));$('generateComprehensive').textContent=tx('更新综合响应','Update comprehensive response')}
  else $('comprehensivePlan').innerHTML=`<p class="focused-empty">${tx('尚未生成综合报告。点击下方按钮，系统将结合五类文物资源本体脆弱性与空间风险生成统一规划响应。','No comprehensive report yet. Use the button below to generate a unified response from all intrinsic vulnerabilities and spatial risks.')}</p>`;
 }catch(error){
  if(token===planRequest&&tab==='plan')target.innerHTML=`<p class="notice">${tx('知识服务未接入：证据检索与策略生成需在本地运行知识库后端（在线版为纯静态托管）。','Knowledge service offline: evidence retrieval and generation require the local backend (online hosting is static-only).')}</p><a class="knowledge-link" href="knowledge.html">${tx('打开知识库','Open knowledge library')}</a>`;
 }
}
