/* Leaf analysis v2: shared by the browser and the offline build. No external AI. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.LeafAnalysis=api})(globalThis,function(){
'use strict';
const VERSION='2.0.0';
const TOPICS={
 '社会':['society','social','community','inequality','employment','workers'],
 '经济':['economy','economic','market','trade','inflation','scarcity','consumers','production'],
 '政策':['policy','government','politics','democracy','regulation','election'],
 '文化':['culture','cultural','literature','language','tradition','identity'],
 '科技':['technology','artificial intelligence','digital','algorithm','automation','software'],
 '教育':['education','learning','school','students','teaching','university'],
 '心理学':['psychology','psychological','cognitive','memory','behavior','behaviour','perception'],
 '环境':['climate','environment','carbon','conservation','biodiversity','ecosystem'],
 '科学':['scientific','science','research','experiment','hypothesis','evidence'],
 '生命科学':['biology','cells','cell','organism','organisms','evolution','species','genetic'],
 '地质':['geology','geological','rocks','minerals','tectonic','sediment','earthquake'],
 '天文':['astronomy','universe','planet','planets','galaxy','galaxies','stars','orbit'],
 '历史':['history','historical','ancient','civilization','century','medieval'],
 '考古':['archaeology','archaeological','excavation','artifacts','fossil','prehistoric'],
 '艺术史':['art','painting','sculpture','renaissance','artists','architecture']
};
const PROFILES={
 '考研英语':{weights:{社会:5,经济:5,政策:5,文化:4,科技:4,教育:4,心理学:2,环境:3,科学:1,历史:3},length:[450,900],levels:{B1:10,B2:28,C1:30,C2:23},focus:'社会、经济、政策与论证表达；编辑参考方向，尚未用真题语料校准'},
 IELTS:{weights:{科学:4,环境:5,教育:4,社会:3,历史:3,心理学:5,科技:3,生命科学:3,地质:3,天文:2,艺术史:2,经济:1,文化:3},length:[700,1400],levels:{B1:12,B2:30,C1:29,C2:20},focus:'科学与半学术说明、环境、心理和教育'},
 TOEFL:{weights:{生命科学:5,地质:5,天文:5,历史:4,考古:5,艺术史:5,科学:4,环境:3,心理学:2,教育:1,科技:1,文化:1},length:[550,1000],levels:{B1:10,B2:29,C1:30,C2:24},focus:'自然科学与人文学科的学术说明'}
};
const STOP=new Set('a an the and or but of to in on at for from by with as is are was were be been being this that these those it its they their them we our you your he she his her not no can could would should will may might must have has had do does did also than then into about such which who what when where how more most other some any each all both only one two first new there here so if while through between over under after before during very many much us up out use used using'.split(' '));
// Small editorial academic seed list, not an exam corpus or the complete AWL.
const GLOSSARY={analysis:['分析','n.'],approach:['方法；接近','n./v.'],assume:['假定','v.'],benefit:['益处；受益','n./v.'],concept:['概念','n.'],context:['语境；背景','n.'],create:['创造','v.'],data:['数据','n.'],define:['定义','v.'],derive:['源自；推导','v.'],distribute:['分配；分布','v.'],economy:['经济','n.'],environment:['环境','n.'],establish:['建立；确立','v.'],estimate:['估计','n./v.'],evidence:['证据','n.'],factor:['因素','n.'],function:['功能；起作用','n./v.'],identify:['识别','v.'],individual:['个人；个体的','n./adj.'],interpret:['解释','v.'],involve:['涉及','v.'],issue:['议题','n.'],method:['方法','n.'],occur:['发生','v.'],percent:['百分之','n.'],period:['时期','n.'],policy:['政策','n.'],principle:['原则','n.'],process:['过程；处理','n./v.'],require:['需要','v.'],research:['研究','n./v.'],respond:['回应','v.'],role:['作用；角色','n.'],section:['部分','n.'],significant:['显著的；重要的','adj.'],similar:['相似的','adj.'],source:['来源','n.'],specific:['特定的','adj.'],structure:['结构','n.'],theory:['理论','n.'],variable:['变量；可变的','n./adj.'],hypothesis:['假设','n.'],scientific:['科学的','adj.'],behavior:['行为','n.'],memory:['记忆','n.'],community:['社区；群体','n.'],climate:['气候','n.'],species:['物种','n.'],evolution:['演化','n.'],universe:['宇宙','n.'],scarcity:['稀缺','n.']};
const tokens=s=>String(s||'').match(/[A-Za-z]+(?:['’-][A-Za-z]+)*/g)||[];
const sentences=s=>String(s||'').match(/[^.!?]+(?:[.!?]+|$)/g)?.filter(x=>/[A-Za-z]/.test(x)).map(x=>x.trim())||[];
const escape=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
function lemma(raw){const word=String(raw).toLowerCase().replace(/^[^a-z]+|[^a-z]+$/g,'');const irregular={children:'child',people:'person',men:'man',women:'woman',studies:'study',theories:'theory',data:'data'};if(irregular[word])return irregular[word];if(GLOSSARY[word])return word;for(const suffix of ['s','es','ed','ing']){const stem=word.slice(0,-suffix.length);if(word.endsWith(suffix)&&GLOSSARY[stem])return stem;if(word.endsWith(suffix)&&GLOSSARY[stem+'e'])return stem+'e'}return word}
function topicMatch(text,min=2){const words=String(text).toLowerCase().split(/\s+/),windows=[];for(let i=0;i<Math.max(1,words.length);i+=30)windows.push(words.slice(i,i+60).join(' '));const hits={};for(const [topic,terms]of Object.entries(TOPICS)){let best=[];for(const w of windows){const found=terms.filter(t=>new RegExp('\\b'+escape(t)+'\\b','i').test(w));if(found.length>best.length)best=found}if(best.length>=min)hits[topic]=best}return hits}
function analyze(article,settings={}){
 const body=typeof article.body==='string'?article.body.trim():'';
 const hits=topicMatch([article.title,article.summary_en,body].join(' '),settings.minCues||2),topics=Object.keys(hits);
 const result={version:VERSION,status:body?'insufficient_text':'metadata_only',available:false,words:body?tokens(body).length:null,cefr:null,difficulty:null,reading_minutes:null,long_sentences:null,keywords:[],core_vocabulary:[],academic_vocabulary:[],coverage:null,topic_hits:hits,topics,basis:'未取得允许站内使用的正文；不使用标题或摘要计算全文指标。'};
 if(!body)return result;
 const ws=tokens(body),ss=sentences(body),freq=new Map();for(const w of ws){const key=lemma(w);if(key.length>2&&!STOP.has(key))freq.set(key,(freq.get(key)||0)+1)}
 const ranked=[...freq].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]));
 result.keywords=ranked.slice(0,12).map(([word,count])=>({word,count}));
 result.core_vocabulary=ranked.slice(0,16).map(([word,count])=>({word,count,meaning:GLOSSARY[word]?.[0]||'',pos:GLOSSARY[word]?.[1]||''}));
 result.academic_vocabulary=ranked.filter(([word])=>GLOSSARY[word]).slice(0,20).map(([word,count])=>({word,count,meaning:GLOSSARY[word][0],pos:GLOSSARY[word][1]}));
 result.reading_minutes=Math.max(1,Math.ceil(ws.length/(settings.wpm||180)));
 result.long_sentences=ss.filter(s=>tokens(s).length>=30||(tokens(s).length>=22&&/\b(although|whereas|because|which|whose|unless|despite|whether)\b/i.test(s))).length;
 if(ws.length<80||ss.length<3){result.basis='所展示正文不足 80 个英文词或 3 句，不估计 CEFR。';return result}
 const avg=ws.length/ss.length,long=ws.filter(w=>w.length>=8).length/ws.length,complex=result.long_sentences/ss.length;
 const abstraction=Math.min(1,topics.filter(t=>['经济','政策','社会','心理学','文化','科学'].includes(t)).length/3);
 const components={vocabulary:Math.min(1,long/.38),syntax:Math.min(1,avg/38)*.55+Math.min(1,complex/.5)*.45,length:Math.min(1,ws.length/2500),abstraction};
 const index=.4*components.vocabulary+.35*components.syntax+.1*components.length+.15*components.abstraction;
 result.cefr=index<.33?'B1':index<.5?'B2':index<.7?'C1':'C2';result.difficulty=result.cefr;
 Object.assign(result,{available:true,status:'available',average_sentence:+avg.toFixed(1),long_word_ratio:+(long*100).toFixed(1),complex_sentence_ratio:+(complex*100).toFixed(1),components,complexity_index:+index.toFixed(3)});
 result.basis=`CEFR 启发式参考，未经标准化测评校准：词汇形态复杂度 40%、句长/从属线索 35%、篇幅 10%、主题抽象度 15%。平均句长 ${avg.toFixed(1)} 词，≥8 字母词 ${(long*100).toFixed(1)}%，长难句 ${result.long_sentences}（规则估计）。分数阈值 .33/.50/.70。词数基于所展示正文；阅读时间按 ${settings.wpm||180} 词/分钟估计。学术词为编辑小词表，不是完整 AWL 或考研词频。`;
 return result;
}
function recommend(analysis){const all={};for(const [exam,p]of Object.entries(PROFILES)){const matched=analysis.topics.filter(t=>p.weights[t]);const max=Math.max(0,...matched.map(t=>p.weights[t]));const theme=Math.min(50,Math.round(max/5*40+Math.min(matched.length,3)*3));const w=analysis.words;const length=w===null?null:w>=p.length[0]&&w<=p.length[1]?20:Math.round(20*Math.max(0,1-Math.min(Math.abs(w-p.length[0]),Math.abs(w-p.length[1]))/(p.length[1]*1.5)));const language=analysis.cefr?p.levels[analysis.cefr]:null;const complete=analysis.available;const score=complete?theme+language+length:null;
 all[exam]={score,topic_score:theme,language_score:complete?language:null,length_score:complete?length:null,provisional:!complete,eligible:complete?theme>=25&&score>=55:theme>=25,matched_topics:matched,reason:`${exam}：${p.focus}。主题 ${theme}/50（${matched.join('、')||'尚无充分主题线索'}）；建议篇幅 ${p.length.join('–')} 词。`+(complete?`语言 ${language}/30（估计 ${analysis.cefr}），篇幅 ${length}/20；总分 ${score}/100。${w>p.length[1]?'篇幅较长，建议分段精读。':''}`:'未取得可分析正文，只有主题预评分，完整适配分暂不可计算。')+'不是官方评分，也不证明被真题采用。'};
 }return all}
function enrich(article,settings){const analysis=analyze(article,settings),exam_scores=recommend(analysis);return {...article,analysis,topics:analysis.topics,exam_scores,recommendations:Object.entries(exam_scores).filter(([,s])=>s.eligible).map(([exam,s])=>({exam,reason:s.reason}))}}
return {VERSION,TOPICS,PROFILES,GLOSSARY,tokens,sentences,lemma,topicMatch,analyze,recommend,enrich};
});
