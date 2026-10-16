'use strict';
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeURL=value=>{try{const u=new URL(value);return ['http:','https:'].includes(u.protocol)&&!u.username&&!u.password?u.href:''}catch{return ''}};
const regexLiteral=value=>value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
const DATA_URL=new URL('./data/articles.json',document.baseURI);
const WORKFLOW_URL='https://github.com/Cocoachennie/reading/actions/workflows/pages.yml';
let state={articles:[],statuses:{}}, exam='考研英语',view='all', busy=false;
let legacyStorageError=false;
let personal={version:1,saved:{},history:{},imports:{}};
try { const stored=JSON.parse(localStorage.getItem('leaf-personal')||'null');if(stored&&stored.version===1&&stored.saved&&stored.history)personal={...stored,imports:stored.imports||{}};else if(stored)legacyStorageError=true; }catch { legacyStorageError=true;toast('本地记录读取失败，请使用备份恢复。'); }
function toast(message){$('#toast').textContent=message;$('#toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('#toast').hidden=true,4200)}
function persist(){if(legacyStorageError){toast('旧版收藏无法读取，未覆盖。请先导出原始存储。');return false}try{localStorage.setItem('leaf-personal',JSON.stringify(personal));return true}catch{toast('浏览器存储不可用。当前记录仅在本次会话中保留，请导出备份。');return false}}
function date(v){if(!v)return '日期未知';const d=new Date(v);return Number.isNaN(d.getTime())?'日期未知':d.toLocaleDateString('zh-CN')}
function stamp(v){return v?new Date(v).toLocaleString('zh-CN'):'尚无成功更新'}
function metadata(a){const {body,analysis,...rest}=a;return rest}
const analysisCache=new WeakMap();
function adjusted(a){
 if(a.analysis?.status==='failed')return {...a,topics:a.topics||[],exam_scores:a.exam_scores||{},recommendations:a.recommendations||[]};
 const minCues=Number($('#cue-min').value)||2;
 let cache=analysisCache.get(a);if(!cache||cache.minCues!==minCues){
  try{cache={minCues,article:LeafAnalysis.enrich(a,{minCues})}}catch(e){cache={minCues,article:{...a,topics:[],recommendations:[],exam_scores:{},analysis:{available:false,status:'failed',words:null,cefr:null,basis:'分析失败：'+e.message}}}}
  analysisCache.set(a,cache);
 }return cache.article;
}
function articles(){const all=new Map(state.articles.map(a=>[a.id,a]));for(const a of Object.values(personal.imports))all.set(a.id,a);for(const a of Object.values(personal.saved))if(!all.has(a.id))all.set(a.id,a);return [...all.values()].map(adjusted)}
function syncOptions(){for(const [id,values]of [['topic',Object.keys(LeafAnalysis.TOPICS)],['source',[...new Set(articles().map(a=>a.source))].sort()]]){const select=$('#'+id),current=select.value;select.innerHTML=`<option value="">全部${id==='topic'?'主题':'来源'}</option>`+values.map(v=>`<option>${esc(v)}</option>`).join('');select.value=values.includes(current)?current:''}}
function render(){
 $('#saved-count').textContent=Object.keys(personal.saved).length;
 $('#list-title').textContent=view==='saved'?'我的收藏':view==='history'?'阅读记录':'为你挑选的阅读';
 $('#last-update').textContent=state.last_success?'上次成功 '+stamp(state.last_success):'尚无成功更新';
 $('#statuses').innerHTML=Object.values(state.statuses).map(s=>`<div class="source-status"><div><strong>${esc(s.name)}</strong><br><small>上次成功：${esc(stamp(s.last_success))}${s.checked_at?' · 最近尝试：'+esc(stamp(s.checked_at)):''}</small></div><div><span>${esc(s.state)}${s.count?' · '+s.count+' 条':''}</span>${s.error?`<div class="status-error">${esc(s.error)}</div>`:''}</div></div>`).join('')+`<p>The Economist：仅支持手动链接导入，未接通自动接口。</p><p>已配置定时采集：计划每天北京时间 08:23 / 20:23，需仓库启用 Actions 和 Pages；运行可能延迟，实际以上次成功记录为准。刷新只读取已发布 JSON，不会立刻抓取来源。<a href="${WORKFLOW_URL}" target="_blank" rel="noopener noreferrer">前往 GitHub Actions 查看或手动采集 ↗</a></p><p>本数据生成于：${esc(stamp(state.generated_at))}；最近一次定时触发：${esc(state.scheduler?.last_scheduled_run?stamp(state.scheduler.last_scheduled_run):'尚无定时运行记录')}。</p>`;
 const all=articles();let filtered=all.filter(a=>{
  if(view==='saved'&&!personal.saved[a.id]||view==='history'&&!personal.history[a.id])return false;
  if(!$('#demo-toggle').checked&&a.demo)return false;
  // Show unclassified entries for review, rather than silently losing new RSS titles.
  if(view==='all'&&!$('#all-articles').checked){const fit=a.exam_scores[exam];if(!fit||!fit.eligible||(!fit.provisional&&fit.score<Number($('#match-threshold').value))||(fit.provisional&&!$('#candidate-toggle').checked))return false;}
  if($('#topic').value&&!a.topics.includes($('#topic').value))return false;
  if($('#source').value&&a.source!==$('#source').value)return false;
  const d=$('#date').value;if(d==='unknown'&&a.published_at)return false;
  if(d&&d!=='unknown'){const age=Date.now()-new Date(a.published_at).getTime();if(!a.published_at||age<0||age>Number(d)*86400000)return false}
  const level=$('#difficulty').value;if(level==='unknown'&&a.analysis.cefr)return false;if(level&&level!=='unknown'&&a.analysis.cefr!==level)return false;
  const length=$('#length').value,w=a.analysis.words;if(length==='unknown'&&w!==null)return false;
  if(length==='short'&&(w===null||w>Number($('#short-max').value)))return false;
  if(length==='medium'&&(w===null||w<=Number($('#short-max').value)||w>Number($('#medium-max').value)))return false;
  if(length==='long'&&(w===null||w<=Number($('#medium-max').value)))return false;
  return [a.title,a.summary_zh,a.summary_en,a.source,...a.topics,a.body||''].join(' ').toLowerCase().includes($('#search').value.toLowerCase().trim());
 });
 if(view==='history')filtered.sort((a,b)=>personal.history[b.id].localeCompare(personal.history[a.id]));
 else filtered.sort((a,b)=>Number(a.demo)-Number(b.demo)||((b.exam_scores[exam]?.score??(b.exam_scores[exam]?.topic_score||0)*.7)-(a.exam_scores[exam]?.score??(a.exam_scores[exam]?.topic_score||0)*.7))||(b.published_at||'').localeCompare(a.published_at||''));
 const live=filtered.filter(a=>!a.demo).length;
 $('#result-count').textContent=`${filtered.length} 篇文章 · ${live} 篇非演示${view==='all'?' · '+exam:''}`;
 $('#notice').textContent='V2.0 · 默认仅显示真实来源或你的本地导入。三个考试独立评分；仅元数据候选不计算全文难度。数量不足时如实显示，可勾选全部文章查看待分析条目。';
 $('#empty').hidden=filtered.length>0;
 $('#articles').innerHTML=filtered.map(a=>{const r=a.recommendations.find(r=>r.exam===exam)||a.recommendations[0];return `<article class="article-card" data-article="${esc(a.id)}"><div class="card-top"><span class="source-name">${esc(a.source)}</span>${a.demo?'<span class="demo-label">虚构演示</span>':`<time>${esc(date(a.published_at))}</time>`}</div><h3><button class="title-button" data-open="${esc(a.id)}">${esc(a.title)}</button></h3><p class="intro">${esc(a.summary_zh)}</p><div class="tags">${a.topics.map(t=>`<span class="tag">${esc(t)}</span>`).join('')}${a.recommendations.map(r=>`<span class="tag exam">${esc(r.exam)}</span>`).join('')}${!a.topics.length?'<span class="tag">主题待复核</span>':''}</div><div class="metrics">${a.analysis.status==='failed'?'<span class="analysis-failure">自动分析失败</span>':''}<span>${a.analysis.words!==null?a.analysis.words+' words':'词数 · 暂无法分析'}</span><span>${a.analysis.cefr?'CEFR 参考 · '+a.analysis.cefr:'难度 · 暂无法分析'}</span><span>${a.analysis.reading_minutes?'约 '+a.analysis.reading_minutes+' 分钟':''}</span></div><p class="recommendation">${a.exam_scores[exam]?.score!=null?'适配 '+a.exam_scores[exam].score+'/100':a.exam_scores[exam]?.eligible?'仅主题预评分 '+a.exam_scores[exam].topic_score+'/50':'暂无该考试推荐'} · ${esc(a.topics.join(' / ')||'主题待复核')}${view==='history'?'<br>打开原文：'+esc(stamp(personal.history[a.id])):''}</p><button class="reason" data-reason="${esc(a.id)}">筛选理由与分析依据 ↗</button><div class="card-actions"><button class="original text-button" data-open="${esc(a.id)}">${a.body?'开始精读 ↗':'查看详情 ↗'}</button>${safeURL(a.url)&&!a.demo?`<a class="original" href="${esc(safeURL(a.url))}" target="_blank" rel="noopener noreferrer" data-read="${esc(a.id)}">Read Original 阅读原文 ↗</a>`:'<span class="original disabled">演示文章 · 无原文链接</span>'}<button class="save ${personal.saved[a.id]?'selected':''}" data-save="${esc(a.id)}" aria-pressed="${!!personal.saved[a.id]}">${personal.saved[a.id]?'◆ 已收藏':'◇ Save 收藏'}</button></div></article>`}).join('');
}
function validateCatalog(data){
 if(!data||data.schema_version!==1||!Array.isArray(data.articles)||!data.statuses||!data.topic_rules||!data.exam_rules)throw Error('文章数据格式不正确');
 const dictionary=v=>v&&typeof v==='object'&&!Array.isArray(v);
 if(!dictionary(data.statuses)||!Object.values(data.statuses).every(s=>dictionary(s)&&typeof s.name==='string'&&typeof s.state==='string'))throw Error('来源状态格式不正确');
 for(const rules of [data.topic_rules,data.exam_rules])if(!dictionary(rules)||!Object.values(rules).every(terms=>Array.isArray(terms)&&terms.every(t=>typeof t==='string'&&t.length>0)))throw Error('分类规则格式不正确');
 if(!data.articles.every(a=>a&&typeof a.id==='string'&&typeof a.title==='string'&&typeof a.source==='string'&&typeof a.summary_zh==='string'&&(!a.body||(a.license?.url==='https://creativecommons.org/licenses/by-nc-sa/4.0/'&&a.url.startsWith('https://github.com/openstax/')))&&(a.demo||(safeURL(a.url)&&a.id===a.url))))throw Error('文章条目格式不正确或包含不应公开的正文');
 return data;
}
async function refresh(){
 try{
  const url=new URL(DATA_URL);url.searchParams.set('v',Date.now());
  const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw Error('HTTP '+response.status);
  const next=validateCatalog(await response.json());state=next;syncOptions();render();document.dispatchEvent(new Event('catalog-ready'));
  try{localStorage.setItem('leaf-catalog',JSON.stringify(next))}catch{/* Personal reading data takes priority over the optional public catalog cache. */}
  return true;
 }catch(e){syncOptions();render();$('#notice').textContent='无法读取最新文章数据：'+e.message+'。已有文章、本地导入和收藏已保留；稍后可重试刷新。';return false}
}
$$('[data-exam]').forEach(b=>b.onclick=()=>{exam=b.dataset.exam;$$('[data-exam]').forEach(x=>x.classList.toggle('active',x===b));render()});
for(const id of ['all','saved','history'])$('#'+id+'-nav').onclick=()=>{view=id;$$('nav button').forEach(b=>b.classList.toggle('nav-active',b.id===id+'-nav'));render()};
$$('.filters input,.filters select,#demo-toggle,#candidate-toggle,#all-articles').forEach(e=>e.addEventListener('input',render));
$$('#settings input').forEach(e=>e.addEventListener('change',()=>{if(!e.checkValidity()||Number($('#medium-max').value)<=Number($('#short-max').value)){toast('请保持阈值有效，且中篇上限及较难句长大于前一档。');e.value=e.defaultValue;return}render()}));
for(const [button,panel]of [['status-toggle','statuses'],['settings-toggle','settings']])$('#'+button).onclick=()=>$('#'+panel).hidden=!$('#'+panel).hidden;
for(const [button,dialog]of [['import-open','import-dialog'],['backup-open','backup-dialog']])$('#'+button).onclick=()=>$('#'+dialog).showModal();
$$('[data-close]').forEach(b=>b.onclick=()=>$('#'+b.dataset.close).close());
$('#reset').onclick=()=>{$$('.filters input,.filters select').forEach(e=>e.value='');$('#demo-toggle').checked=false;render()};
$('#articles').addEventListener('click',e=>{
 const b=e.target.closest('[data-save],[data-reason],[data-read],[data-open]');if(!b){const card=e.target.closest('[data-article]');if(card&&!window.getSelection()?.toString())LeafReader.openArticle(card.dataset.article);return;}const id=b.dataset.save||b.dataset.reason||b.dataset.read||b.dataset.open;const a=articles().find(a=>a.id===id);if(!a)return;
 if(b.dataset.save){if(personal.saved[id])delete personal.saved[id];else personal.saved[id]=metadata(a);persist();render()}
 if(b.dataset.read){personal.history[id]=new Date().toISOString();persist();if(view==='history')render()}
 if(b.dataset.reason)showAnalysis(a);
 if(b.dataset.open)LeafReader.openArticle(a.id);

});
function showAnalysis(a){
 $('#detail-content').innerHTML=`<h3 class="detail-title">${esc(a.title)}</h3><p>${esc(a.source)} · ${esc(date(a.published_at))} · 推荐阅读来源，未核实真题采用</p><div class="detail-section"><strong>独立考试适配</strong>${Object.entries(a.exam_scores).map(([name,fit])=>`<p><strong>${esc(name)}：${fit.score===null?'完整评分暂无法计算':fit.score+'/100'}</strong><br>${esc(fit.reason)}</p>`).join('')}</div><div class="detail-section"><strong>自动分析 · ${esc(a.analysis.status)}</strong><p>主题线索：${esc(Object.entries(a.analysis.topic_hits||{}).map(([t,terms])=>t+'（'+terms.join(' / ')+'）').join('；')||'尚无充分线索')}</p><p>${esc(a.analysis.basis)}</p><p>实际展示词数：${a.analysis.words??'暂无法分析'}；长难句：${a.analysis.long_sentences??'暂无法分析'}；CEFR 参考：${a.analysis.cefr||'暂无法分析'}</p><p>核心词：${esc((a.analysis.core_vocabulary||[]).map(v=>v.word+' ×'+v.count).join('、')||'暂无法分析')}</p><p>编辑学术词：${esc((a.analysis.academic_vocabulary||[]).map(v=>v.word+' ×'+v.count+' '+v.meaning).join('、')||'暂无或无法分析')}；并非完整 AWL。</p><p>考研高频词覆盖率：暂无法分析。没有真实授权语料、年份范围或统计分母。</p></div><p>${esc(a.content_scope||'未获可站内展示的正文，仅元数据。')}<br>${esc(a.rights)}<br>收集于 ${esc(stamp(a.collected_at))}</p>`;
 $('#detail-dialog').showModal();
}
$('#update').onclick=async()=>{if(busy)return;busy=true;$('#update').disabled=true;$('#update').textContent='正在刷新…';try{if(await refresh())toast('已读取最近发布的数据；立即采集请前往来源状态中的 GitHub Actions。')}finally{busy=false;$('#update').disabled=false;$('#update').textContent='↻ 刷新文章'}};
$('#import-form').onsubmit=e=>{e.preventDefault();const form=e.target;$('#import-error').textContent='';const data=Object.fromEntries(new FormData(form));try{
 const title=data.title.trim(),url=safeURL(data.url),body=data.body.trim();
 if(!title||!url)throw Error('请提供标题和有效的 HTTP(S) 原文链接');
 if(body&&!form.elements.authorized.checked)throw Error('只有确认有权使用完整正文后才能导入');
 if(new TextEncoder().encode(body).length>500000)throw Error('正文超过 500KB 限制');
 const article={id:url,title,url,source:data.source.trim()||'手动导入',published_at:data.published_at||null,collected_at:new Date().toISOString(),summary_zh:data.summary_zh.trim()||'手动导入，尚未添加中文简介。',summary_en:data.summary_en.trim(),body,demo:false,browser_only:true,rights:body?'用户声明合法取得完整正文；仅保存在本浏览器，不发送到服务器。':'本地链接与元数据；未获取全文。'};
 personal.imports[url]=article;const saved=persist();syncOptions();render();form.reset();$('#import-dialog').close();if(saved)toast('已导入到本浏览器；正文不会上传或公开。');if(window.LeafReader)LeafReader.openArticle(url);
 }catch(e){$('#import-error').textContent=e.message}};

try{const cached=localStorage.getItem('leaf-catalog');if(cached){state=validateCatalog(JSON.parse(cached));syncOptions();render()}}catch{/* A corrupt cache must not prevent fetching the published catalog. */}
refresh();
