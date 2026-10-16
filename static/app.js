'use strict';
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeURL=value=>{try{const u=new URL(value);return ['http:','https:'].includes(u.protocol)&&!u.username&&!u.password?u.href:''}catch{return ''}};
const regexLiteral=value=>value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
const DATA_URL=new URL('./data/articles.json',document.baseURI);
const WORKFLOW_URL='https://github.com/Cocoachennie/reading/actions/workflows/pages.yml';
let state={articles:[],statuses:{}}, exam='考研英语',view='all', busy=false;
let personal={version:1,saved:{},history:{},imports:{}};
try { const stored=JSON.parse(localStorage.getItem('leaf-personal')||'null');if(stored&&stored.version===1&&stored.saved&&stored.history)personal={...stored,imports:stored.imports||{}}; }catch { toast('本地记录读取失败，请使用备份恢复。'); }
function toast(message){$('#toast').textContent=message;$('#toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('#toast').hidden=true,4200)}
function persist(){try{localStorage.setItem('leaf-personal',JSON.stringify(personal));return true}catch{toast('浏览器存储不可用。当前记录仅在本次会话中保留，请导出备份。');return false}}
function date(v){if(!v)return '日期未知';const d=new Date(v);return Number.isNaN(d.getTime())?'日期未知':d.toLocaleDateString('zh-CN')}
function stamp(v){return v?new Date(v).toLocaleString('zh-CN'):'尚无成功更新'}
function metadata(a){const {body,analysis,...rest}=a;return rest}
function localAnalysis(body){
 if(!body.trim())return {available:false,words:null,difficulty:null,coverage:null,basis:'暂无法分析：未获得获授权的完整正文。'};
 const words=body.match(/[A-Za-z]+(?:['’-][A-Za-z]+)*/g)||[];
 const sentences=body.split(/[.!?]+/).filter(s=>/[A-Za-z]/.test(s));
 if(words.length<80||sentences.length<3)return {available:false,words:words.length,difficulty:null,coverage:null,basis:'正文不足 80 个英文词或 3 句；样本过短，不估计难度。'};
 const avg=words.length/sentences.length,long=100*words.filter(w=>w.length>=8).length/words.length;
 return {available:true,words:words.length,difficulty:null,coverage:null,average_sentence:Math.round(avg*10)/10,long_word_ratio:Math.round(long*10)/10,basis:`启发式估计：平均句长 ${avg.toFixed(1)} 词，≥8 字母词占比 ${long.toFixed(1)}%。长词仅为复杂度代理；非官方分级，未分析语法或 CEFR。正文仅在当前浏览器计算与保存。`};
}
function adjusted(a){
 const text=[a.title,a.summary_en,a.body].filter(Boolean).join(' ').toLowerCase();
 const cues=Number($('#cue-min').value)||2;
 const hits={};for(const [topic,terms]of Object.entries(state.topic_rules||{})){hits[topic]=terms.filter(t=>new RegExp('\\b'+regexLiteral(t)+'\\b','i').test(text))}
 const words=text.split(/\s+/);const windows=[];for(let i=0;i<Math.max(1,words.length);i+=30)windows.push(words.slice(i,i+60).join(' '));
 const topics=Object.keys(hits).filter(t=>windows.some(w=>hits[t].filter(term=>new RegExp('\\b'+regexLiteral(term)+'\\b','i').test(w)).length>=cues));
 const recommendations=Object.entries(state.exam_rules||{}).flatMap(([name,allowed])=>{const ts=topics.filter(t=>allowed.includes(t));return ts.length?[{exam:name,reason:`主题初筛：${ts.join('、')}；多个线索在 60 词局部语境共同出现（${ts.flatMap(t=>hits[t]).slice(0,5).join(' / ')}）。需人工核对语境；不代表考试采用或全文难度适配。`}]:[]});
 const analysis={...(a.browser_only?localAnalysis(a.body||''):a.analysis||{available:false,words:null,difficulty:null,coverage:null,basis:'暂无法分析：备份不含完整正文。'})};
 if(analysis.available){analysis.difficulty=analysis.average_sentence>=Number($('#hard-sentence').value)||analysis.long_word_ratio>=27?'较难':analysis.average_sentence>=Number($('#medium-sentence').value)||analysis.long_word_ratio>=17?'中等':'较易';}
 return {...a,topics,recommendations,analysis};
}
function articles(){const all=new Map(state.articles.map(a=>[a.id,a]));for(const a of Object.values(personal.imports))all.set(a.id,a);for(const a of Object.values(personal.saved))if(!all.has(a.id))all.set(a.id,a);return [...all.values()].map(adjusted)}
function syncOptions(){for(const [id,values]of [['topic',Object.keys(state.topic_rules||{})],['source',[...new Set(articles().map(a=>a.source))].sort()]]){const select=$('#'+id),current=select.value;select.innerHTML=`<option value="">全部${id==='topic'?'主题':'来源'}</option>`+values.map(v=>`<option>${esc(v)}</option>`).join('');select.value=values.includes(current)?current:''}}
function render(){
 $('#saved-count').textContent=Object.keys(personal.saved).length;
 $('#list-title').textContent=view==='saved'?'我的收藏':view==='history'?'阅读记录':'为你挑选的阅读';
 $('#last-update').textContent=state.last_success?'上次成功 '+stamp(state.last_success):'尚无成功更新';
 $('#statuses').innerHTML=Object.values(state.statuses).map(s=>`<div class="source-status"><div><strong>${esc(s.name)}</strong><br><small>上次成功：${esc(stamp(s.last_success))}${s.checked_at?' · 最近尝试：'+esc(stamp(s.checked_at)):''}</small></div><div><span>${esc(s.state)}${s.count?' · '+s.count+' 条':''}</span>${s.error?`<div class="status-error">${esc(s.error)}</div>`:''}</div></div>`).join('')+`<p>The Economist：仅支持手动链接导入，未接通自动接口。</p><p>已配置定时采集：计划每天北京时间 08:23 / 20:23，需仓库启用 Actions 和 Pages；运行可能延迟，实际以上次成功记录为准。刷新只读取已发布 JSON，不会立刻抓取来源。<a href="${WORKFLOW_URL}" target="_blank" rel="noopener noreferrer">前往 GitHub Actions 查看或手动采集 ↗</a></p><p>本数据生成于：${esc(stamp(state.generated_at))}；最近一次定时触发：${esc(state.scheduler?.last_scheduled_run?stamp(state.scheduler.last_scheduled_run):'尚无定时运行记录')}。</p>`;
 const all=articles();let filtered=all.filter(a=>{
  if(view==='saved'&&!personal.saved[a.id]||view==='history'&&!personal.history[a.id])return false;
  if(!$('#demo-toggle').checked&&a.demo)return false;
  // Show unclassified entries for review, rather than silently losing new RSS titles.
  if(view==='all'&&a.recommendations.length&&!a.recommendations.some(r=>r.exam===exam))return false;
  if($('#topic').value&&!a.topics.includes($('#topic').value))return false;
  if($('#source').value&&a.source!==$('#source').value)return false;
  const d=$('#date').value;if(d==='unknown'&&a.published_at)return false;
  if(d&&d!=='unknown'){const age=Date.now()-new Date(a.published_at).getTime();if(!a.published_at||age<0||age>Number(d)*86400000)return false}
  const level=$('#difficulty').value;if(level==='unknown'&&a.analysis.difficulty)return false;if(level&&level!=='unknown'&&a.analysis.difficulty!==level)return false;
  const length=$('#length').value,w=a.analysis.words;if(length==='unknown'&&w!==null)return false;
  if(length==='short'&&(w===null||w>Number($('#short-max').value)))return false;
  if(length==='medium'&&(w===null||w<=Number($('#short-max').value)||w>Number($('#medium-max').value)))return false;
  if(length==='long'&&(w===null||w<=Number($('#medium-max').value)))return false;
  return [a.title,a.summary_zh,a.summary_en,a.source,...a.topics,a.body||''].join(' ').toLowerCase().includes($('#search').value.toLowerCase().trim());
 });
 if(view==='history')filtered.sort((a,b)=>personal.history[b.id].localeCompare(personal.history[a.id]));
 else filtered.sort((a,b)=>Number(a.demo)-Number(b.demo)||(b.published_at||'').localeCompare(a.published_at||''));
 const live=filtered.filter(a=>!a.demo).length;
 $('#result-count').textContent=`${filtered.length} 篇文章 · ${live} 篇非演示${view==='all'?' · '+exam:''}`;
 $('#notice').textContent=state.articles.some(a=>a.demo)?'演示数据已明确标注：示例标题、简介与主题线索为虚构内容，并非对应来源实际发布文章。未分类的真实条目保留展示，等待人工复核。':'仅展示收集条目。推荐标签是主题初筛，不是官方评分或已核实真题来源。';
 $('#empty').hidden=filtered.length>0;
 $('#articles').innerHTML=filtered.map(a=>{const r=a.recommendations.find(r=>r.exam===exam)||a.recommendations[0];return `<article class="article-card"><div class="card-top"><span class="source-name">${esc(a.source)}</span>${a.demo?'<span class="demo-label">虚构演示</span>':`<time>${esc(date(a.published_at))}</time>`}</div><h3>${esc(a.title)}</h3><p class="intro">${esc(a.summary_zh)}</p><div class="tags">${a.topics.map(t=>`<span class="tag">${esc(t)}</span>`).join('')}${a.recommendations.map(r=>`<span class="tag exam">${esc(r.exam)}</span>`).join('')}${!a.topics.length?'<span class="tag">主题待复核</span>':''}</div><div class="metrics"><span>${a.analysis.words!==null?a.analysis.words+' words':'词数 · 暂无法分析'}</span><span>${a.analysis.difficulty?'估计 · '+a.analysis.difficulty:'难度 · 暂无法分析'}</span></div><p class="recommendation">${r?'推荐阅读 · '+esc(a.topics.join(' / ')):'暂无考试推荐 · 等待语境复核'}${view==='history'?'<br>打开原文：'+esc(stamp(personal.history[a.id])):''}</p><button class="reason" data-reason="${esc(a.id)}">筛选理由与分析依据 ↗</button><div class="card-actions">${safeURL(a.url)&&!a.demo?`<a class="original" href="${esc(safeURL(a.url))}" target="_blank" rel="noopener noreferrer" data-read="${esc(a.id)}">Read Original 阅读原文 ↗</a>`:'<span class="original disabled">演示文章 · 无原文链接</span>'}<button class="save ${personal.saved[a.id]?'selected':''}" data-save="${esc(a.id)}" aria-pressed="${!!personal.saved[a.id]}">${personal.saved[a.id]?'◆ 已收藏':'◇ Save 收藏'}</button></div></article>`}).join('');
}
function validateCatalog(data){
 if(!data||data.schema_version!==1||!Array.isArray(data.articles)||!data.statuses||!data.topic_rules||!data.exam_rules)throw Error('文章数据格式不正确');
 const dictionary=v=>v&&typeof v==='object'&&!Array.isArray(v);
 if(!dictionary(data.statuses)||!Object.values(data.statuses).every(s=>dictionary(s)&&typeof s.name==='string'&&typeof s.state==='string'))throw Error('来源状态格式不正确');
 for(const rules of [data.topic_rules,data.exam_rules])if(!dictionary(rules)||!Object.values(rules).every(terms=>Array.isArray(terms)&&terms.every(t=>typeof t==='string'&&t.length>0)))throw Error('分类规则格式不正确');
 if(!data.articles.every(a=>a&&typeof a.id==='string'&&typeof a.title==='string'&&typeof a.source==='string'&&typeof a.summary_zh==='string'&&!a.body&&(a.demo||safeURL(a.url))))throw Error('文章条目格式不正确或包含不应公开的正文');
 return data;
}
async function refresh(){
 try{
  const url=new URL(DATA_URL);url.searchParams.set('v',Date.now());
  const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw Error('HTTP '+response.status);
  const next=validateCatalog(await response.json());state=next;syncOptions();render();
  try{localStorage.setItem('leaf-catalog',JSON.stringify(next))}catch{/* Personal reading data takes priority over the optional public catalog cache. */}
  return true;
 }catch(e){syncOptions();render();$('#notice').textContent='无法读取最新文章数据：'+e.message+'。已有文章、本地导入和收藏已保留；稍后可重试刷新。';return false}
}
$$('[data-exam]').forEach(b=>b.onclick=()=>{exam=b.dataset.exam;$$('[data-exam]').forEach(x=>x.classList.toggle('active',x===b));render()});
for(const id of ['all','saved','history'])$('#'+id+'-nav').onclick=()=>{view=id;$$('nav button').forEach(b=>b.classList.toggle('nav-active',b.id===id+'-nav'));render()};
$$('.filters input,.filters select,#demo-toggle').forEach(e=>e.addEventListener('input',render));
$$('#settings input').forEach(e=>e.addEventListener('change',()=>{if(!e.checkValidity()||Number($('#medium-max').value)<=Number($('#short-max').value)||Number($('#hard-sentence').value)<=Number($('#medium-sentence').value)){toast('请保持阈值有效，且中篇上限及较难句长大于前一档。');e.value=e.defaultValue;return}render()}));
for(const [button,panel]of [['status-toggle','statuses'],['settings-toggle','settings']])$('#'+button).onclick=()=>$('#'+panel).hidden=!$('#'+panel).hidden;
for(const [button,dialog]of [['import-open','import-dialog'],['backup-open','backup-dialog']])$('#'+button).onclick=()=>$('#'+dialog).showModal();
$$('[data-close]').forEach(b=>b.onclick=()=>$('#'+b.dataset.close).close());
$('#reset').onclick=()=>{$$('.filters input,.filters select').forEach(e=>e.value='');$('#demo-toggle').checked=true;render()};
$('#articles').addEventListener('click',e=>{
 const b=e.target.closest('[data-save],[data-reason],[data-read]');if(!b)return;const id=b.dataset.save||b.dataset.reason||b.dataset.read;const a=articles().find(a=>a.id===id);if(!a)return;
 if(b.dataset.save){if(personal.saved[id])delete personal.saved[id];else personal.saved[id]=metadata(a);persist();render()}
 if(b.dataset.read){personal.history[id]=new Date().toISOString();persist();if(view==='history')render()}
 if(b.dataset.reason){const analysis=a.analysis;$('#detail-content').innerHTML=`<h3 class="detail-title">${esc(a.title)}</h3><p>${a.demo?'虚构演示内容 · ':''}推荐阅读来源 · 未核实真题采用</p><div class="detail-section"><strong>第一阶段 · 主题初筛</strong>${a.recommendations.length?a.recommendations.map(r=>`<p><strong>${esc(r.exam)}</strong>：${esc(r.reason)}</p>`).join(''):'<p>未达到多个线索匹配阈值，暂不推荐。单个关键词不构成相关性证据。</p>'}<p>线索范围：${a.body?'用户确认授权的全文、标题与简介':'仅标题与用户提供的英文简介（元数据初筛）'}。编辑主题库不是历年真题语料库，需要至少多个独立线索在 60 词局部窗口共同出现，防止全文远距离偶然命中；尚未实现语义模型或人工审核流程。</p></div><div class="detail-section"><strong>第二阶段 · 阅读适配</strong><p>${esc(analysis.basis)}</p>${analysis.available?`<p>当前阈值估计：${esc(analysis.difficulty)}；中等句长 ≥${esc($('#medium-sentence').value)}，较难句长 ≥${esc($('#hard-sentence').value)}；长词比例阈值 17% / 27%。词数按英文词及内部撇号/连字符统计。</p>`:''}<p>考研高频词覆盖率：暂无法分析。没有真实、合法可用的真题语料，未设置年份、语料范围或频次表。</p><p>IELTS / TOEFL：分别按其编辑主题分类初筛；尚无考试专用全文适配评分。</p></div><div class="detail-section"><strong>来源与权限</strong><p>${esc(a.rights)}<br>发布日期：${esc(date(a.published_at))}<br>收集日期：${esc(stamp(a.collected_at))}<br>真题采用证据：无；不可标记为真题来源。</p></div>`;$('#detail-dialog').showModal()}
});
$('#update').onclick=async()=>{if(busy)return;busy=true;$('#update').disabled=true;$('#update').textContent='正在刷新…';try{if(await refresh())toast('已读取最近发布的数据；立即采集请前往来源状态中的 GitHub Actions。')}finally{busy=false;$('#update').disabled=false;$('#update').textContent='↻ 刷新文章'}};
$('#import-form').onsubmit=e=>{e.preventDefault();const form=e.target;$('#import-error').textContent='';const data=Object.fromEntries(new FormData(form));try{
 const title=data.title.trim(),url=safeURL(data.url),body=data.body.trim();
 if(!title||!url)throw Error('请提供标题和有效的 HTTP(S) 原文链接');
 if(body&&!form.elements.authorized.checked)throw Error('只有确认有权使用完整正文后才能导入');
 if(new TextEncoder().encode(body).length>500000)throw Error('正文超过 500KB 限制');
 const article={id:url,title,url,source:data.source.trim()||'手动导入',published_at:data.published_at||null,collected_at:new Date().toISOString(),summary_zh:data.summary_zh.trim()||'手动导入，尚未添加中文简介。',summary_en:data.summary_en.trim(),body,demo:false,browser_only:true,rights:body?'用户声明合法取得完整正文；仅保存在本浏览器，不发送到服务器。':'本地链接与元数据；未获取全文。'};
 personal.imports[url]=article;const saved=persist();syncOptions();render();form.reset();$('#import-dialog').close();if(saved)toast('已导入到本浏览器；正文不会上传或公开。');
 }catch(e){$('#import-error').textContent=e.message}};

$('#export').onclick=()=>{const data={version:1,saved:personal.saved,history:personal.history,imports:Object.fromEntries(Object.entries(personal.imports).map(([id,a])=>[id,metadata(a)])),exported_at:new Date().toISOString()};const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='leaf-reading-backup.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
$('#backup-file').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>2000000)throw Error('备份超过 2MB 限制');const data=JSON.parse(await file.text());if(data.version!==1||!data.saved||typeof data.saved!=='object'||Array.isArray(data.saved)||!data.history||typeof data.history!=='object'||Array.isArray(data.history))throw Error('备份格式不正确');const saved={...personal.saved},history={...personal.history};for(const [id,a]of Object.entries(data.saved)){if(!a||typeof a.title!=='string'||a.id!==id||typeof a.source!=='string'||typeof a.summary_zh!=='string'||(!a.demo&&!safeURL(a.url)))throw Error('文章记录格式不正确');if(['__proto__','constructor','prototype'].includes(id))throw Error('无效记录 ID');saved[id]=metadata(a)}for(const[id,t]of Object.entries(data.history)){if(!safeURL(id)||typeof t!=='string'||Number.isNaN(Date.parse(t)))throw Error('阅读记录格式不正确');history[id]=t}const imports={...personal.imports};if(data.imports!==undefined){if(!data.imports||typeof data.imports!=='object'||Array.isArray(data.imports))throw Error('导入文章备份格式不正确');for(const[id,a]of Object.entries(data.imports)){if(!a||a.id!==id||!safeURL(id)||typeof a.title!=='string'||typeof a.source!=='string'||typeof a.summary_zh!=='string')throw Error('导入文章格式不正确');if(!imports[id])imports[id]={...metadata(a),browser_only:true,body:''}}}personal={version:1,saved,history,imports};const ok=persist();syncOptions();render();$('#backup-message').textContent=ok?'恢复成功，已与现有记录合并。':'已恢复到当前会话，但浏览器存储不可用，请导出备份。'}catch(e){$('#backup-message').textContent='恢复失败：'+e.message}finally{e.target.value=''}};
try{const cached=localStorage.getItem('leaf-catalog');if(cached){state=validateCatalog(JSON.parse(cached));syncOptions();render()}}catch{/* A corrupt cache must not prevent fetching the published catalog. */}
refresh();
