let language=localStorage.getItem('heritage-language')==='en'?'en':'zh';
const translations={
'建筑集合填充不透明度':'Building-set fill opacity','全市风险范围（按韧性着色）':'Citywide extents by resilience','当前文物精细风险范围':'Selected site risk extent',
'隐藏文物点':'Hide sites','显示文物点':'Show sites',
'范围与等级':'Extent & grade','边界线':'Boundaries','建筑集合':'Building sets','基本范围':'Basic extent','风险范围':'Risk extent','同级韧性':'Same resilience','较低韧性':'Lower resilience','韧性等级':'Resilience','全部等级':'All levels','高韧性':'High resilience','中韧性':'Medium resilience','低韧性':'Low resilience','等级重叠':'Overlapping levels','范围重叠取较低韧性':'Overlaps show lower resilience',
'红：高韧性；黄：中韧性；蓝：低韧性。左下角切换范围':'Red: high; yellow: medium; blue: low resilience. Switch extents at bottom-left.',
'风险范围按中心文物韧性着色：红高、黄中、蓝低。模型范围不等于法定保护范围。':'Extents use the central site’s resilience: red high, yellow medium, blue low. Not statutory boundaries.',

'规划知识库':'Knowledge',
'文物遗产韧性与规划响应平台':'Heritage Resilience & Intervention Spatial Knowledge platform',
'建筑遗产韧性与干预':'Heritage Resilience & Intervention','空间知识平台':'Spatial Knowledge platform','HERISK – 文物遗产韧性与规划响应平台':'HERISK – Heritage Resilience & Intervention Spatial Knowledge platform',
"HERISK 是一个由大语言模型驱动的空间平台，面向人为扰动下的建筑遗产韧性评估。平台从开放文本中提取遗产记录，推断建筑属性，融合专家与地方知识库开展脆弱性评价，模拟五类危害在建筑之间的传播，并自动划定干预分区与全市风险区域。":"HERISK is an LLM-powered spatial platform for built heritage resilience assessment under anthropogenic disturbance. It extracts heritage records from open texts, infers building attributes, evaluates vulnerability via integrated expert and local knowledge bases, simulates cross-building propagation of five hazard types, and automatically delineates intervention zones and city-wide risk areas.",
'关于 HERISK':'About HERISK','迹察风险，城铸韧性':'Mapping heritage risk contagion for urban resilience',
'上海文物资源':'Shanghai Heritage','图层与显示设置':'Layers & appearance',
'◈ 上海文物资源':'◈ Shanghai Heritage','文物资源风险评估与规划反馈响应平台':'Heritage Risk Assessment & Planning','文物保护规划辅助决策':'Conservation planning support','文物资源空间总览':'HERITAGE OVERVIEW','文物风险总览':'Heritage risk overview','数据加载中…':'Loading data…','文物资源检索':'Find heritage sites','搜索文物名称、地址或编号':'Search name, address or ID','全部行政区':'All districts','跨区文物可在其涉及的任一区中查到。':'Cross-district sites appear in each relevant district.','空间图层管理':'Map layers','基础空间信息':'Base layers','文物点位与建筑轮廓':'Heritage sites & footprints','上海市行政边界':'Shanghai boundary','坐标系待核验':'CRS unverified','建筑轮廓':'Building footprints','放大后加载':'Zoom in to load','图层显示设置':'Layer appearance','底图不透明度':'Basemap opacity','全市风险底板不透明度':'Citywide risk opacity','选中文物范围不透明度':'Selected extent opacity','文物点位与建筑':'Heritage sites & buildings','当前选中文物':'Selected heritage site','全市开发建设风险底板':'Citywide development risk','当前文物关联风险范围':'Selected associated risk extent','其他建筑':'Other buildings','建筑轮廓放大后显示。颜色区分对象，不代表风险等级；模型范围不等同于法定保护范围。':'Zoom in for footprints. Colors identify layers, not risk levels. Model extents are not statutory boundaries.','全域与单体风险模式':'Map view','全域风险分布':'Citywide risk','浏览全市文物点位与全域风险底图':'Explore heritage sites and citywide risk','文物点位叠加所选风险底板；点击文物查看关联范围':'Select a heritage site to see its associated extent.','当前文物关联风险':'Selected-site risk','紫色：当前文物关联范围；朱红：全市风险底板':'Purple: selected extent; red: citywide risk','返回全市视图':'Citywide view','文物资源目录':'Heritage directory','全市风险底板':'Citywide risk layer','正在准备…':'Preparing…','地图加载中…':'Loading map…','文物本体与建筑群联动诊断':'SITE & BUILDING-GROUP ASSESSMENT','选择文物查看诊断结果':'Select a heritage site','本体风险':'Intrinsic risk','建筑群风险':'Building-group risk','规划反馈响应':'Planning response','通过地图点选或目录检索，查看文物本体特征、脆弱性评价与关联建筑群空间风险。':'Select a site on the map or in the directory to explore its assessment.','仅文物点':'Heritage only','综合风险':'Combined risk','本底塑造':'Historical setting','开发建设':'Development','活动利用':'Use & activities','污染安全':'Pollution','舆论引导':'Public attention','待接入':'Coming soon','切换底板':'Switch risk layer','切换到此风险，显示待接入状态':'Switch to this category; data pending','数据尚未接入，当前仅显示文物与基础地图':'Data unavailable; showing heritage sites and basemap','仅显示文物与基础空间信息':'Showing heritage sites and base layers','加载中…':'Loading…','朱红色为渗流影响范围（非风险等级）':'Red shows percolation extent, not risk levels','底板图像加载失败，点击重试':'Image failed to load; click to retry','底板加载失败，点击当前风险按钮重试':'Layer failed to load; click to retry','全市：朱红色为渗流影响范围，青绿色为文物点；选中后紫色显示关联范围。边界坐标系待核验。':'Red: citywide percolation; green: heritage sites; purple: selected extent. Boundary CRS unverified.',
'黄浦区':'Huangpu','徐汇区':'Xuhui','长宁区':'Changning','静安区':'Jing’an','普陀区':'Putuo','虹口区':'Hongkou','杨浦区':'Yangpu','闵行区':'Minhang','宝山区':'Baoshan','嘉定区':'Jiading','浦东新区':'Pudong','金山区':'Jinshan','松江区':'Songjiang','青浦区':'Qingpu','奉贤区':'Fengxian','崇明区':'Chongming'
};
const originals=new WeakMap();
function translated(text){let trimmed=text.trim();if(translations[trimmed])return text.replace(trimmed,translations[trimmed]);if(trimmed.includes(' · '))return text.split(' · ').map(x=>translations[x]||x).join(' · ');return text}
function translateUI(){
 updateThemeButton();
 const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let node;
 while(node=walker.nextNode()){
  if(node.parentElement.closest('script,style,#headerCopyright,#riskTooltip,#theme,.brand-slogan,#detail,#headlineScores,#stats,#title,#meta,#list,.leaflet-pane'))continue;
  let record=originals.get(node);if(!record||node.nodeValue!==record.output)record={source:node.nodeValue};
  const output=language==='en'?translated(record.source):record.source;record.output=output;originals.set(node,record);if(node.nodeValue!==output)node.nodeValue=output;
 }
 document.documentElement.lang=language==='en'?'en':'zh-CN';
 const copyright=document.getElementById('headerCopyright');
 if(copyright){const text=language==='en'?'Copyright@Centre for URBAN SCIENCE & PLANNING TONGJI X UCL Sino-UK Joint Lab for Urban AI':'copyright@同济大学城市科学与规划中心 ｜ 中英城市人工智能实验室';if(copyright.textContent!==text)copyright.textContent=text;}
 document.title=language==='en'?'HERISK – Heritage Resilience & Intervention Spatial Knowledge platform':'HERISK – 文物遗产韧性与规划响应平台';
 document.getElementById('search').placeholder=language==='en'?translations['搜索文物名称、地址或编号']:'搜索文物名称、地址或编号';
 document.getElementById('language').textContent=language==='en'?'中文':'English';
 document.querySelectorAll('#riskButtons button').forEach(b=>b.removeAttribute('title'));
 if(typeof updateRiskTooltip==='function')updateRiskTooltip();
}
const languageObserver=new MutationObserver(()=>{languageObserver.disconnect();translateUI();languageObserver.observe(document.body,{childList:true,subtree:true,characterData:true})});
document.getElementById('language').onclick=()=>{language=language==='en'?'zh':'en';localStorage.setItem('heritage-language',language);filter();render();if(typeof refreshRiskView==='function')refreshRiskView();translateUI()};
languageObserver.observe(document.body,{childList:true,subtree:true,characterData:true});
translateUI();
