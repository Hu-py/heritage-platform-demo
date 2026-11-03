// Evidence retrieval is automatic; paid generation requires an explicit click.
let planRequest=0;

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
   fetchComprehensive(site.id)
  ]);
  if(token!==planRequest||selected?.id!==site.id||tab!=='plan')return;
  target.innerHTML=`<section class="planning-level comprehensive-level"><div class="planning-level-heading"><div><small>${tx('五类风险综合决策','INTEGRATED FIVE-RISK RESPONSE')}</small><h2>${tx('综合规划响应','Comprehensive planning response')}</h2><p>${tx('整合全部本体风险与建筑群风险，统一提出保护目标、策略与措施','Integrates all intrinsic and group risks into unified objectives, strategies and measures')}</p></div></div><div id="comprehensivePlan"></div>${planningAction(capability.llm?.configured)}<a class="knowledge-link" target="_blank" rel="noopener" href="knowledge.html?site_id=${encodeURIComponent(site.id)}&risk=${encodeURIComponent(risk)}">${tx('打开知识库与关系图 ↗','Open library & graph ↗')}</a></section>`;
  bindGeneration(site,risk,token);
  if(saved){renderStructuredReport(saved,$('comprehensivePlan'));$('generateComprehensive').textContent=tx('更新综合响应','Update comprehensive response')}
  else $('comprehensivePlan').innerHTML=`<p class="focused-empty">${tx('尚未生成综合报告。点击下方按钮，系统将结合五类本体与建筑群风险生成统一规划响应。','No comprehensive report yet. Use the button below to generate a unified response from all intrinsic and group risks.')}</p>`;
 }catch(error){
  if(token===planRequest&&tab==='plan')target.innerHTML=`<p class="notice">${tx('知识服务未接入：证据检索与策略生成需在本地运行知识库后端（在线版为纯静态托管）。','Knowledge service offline: evidence retrieval and generation require the local backend (online hosting is static-only).')}</p><a class="knowledge-link" href="knowledge.html">${tx('打开知识库','Open knowledge library')}</a>`;
 }
}
