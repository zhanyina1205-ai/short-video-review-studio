'use strict';
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
let state, page='home', filter='全部', uploads=[], importing=false, session=0;
const pageNames={home:['内容工作台','WORKSPACE OVERVIEW'],archive:['作品档案','CONTENT ARCHIVE'],weekly:['运营周报','WEEKLY REVIEW']};
async function request(url,opts){if(window.browserStudio)return browserStudio.request(url,opts);const r=await fetch(url,opts);const d=await r.json();if(!r.ok)throw Error(d.error||'读取失败，请重试');return d}
async function refresh(){state=await request('/api/state');render()}
function openReport(url,title){$('viewtitle').textContent=title;if(window.browserStudio){$('frame').srcdoc=browserStudio.report(url)}else{$('frame').src=url}$('viewer').showModal()}
function weekEnd(w){let d=new Date(w+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+6);return d.toISOString().slice(0,10)}
function weekCard(w){return '<div class="week"><strong>▦</strong><div><small class="meta">按发布周归档</small><h3>'+esc(w)+' — '+weekEnd(w).slice(5)+'</h3></div><button class="link right" data-week="'+w+'">查看周报 ↗</button></div>'}
function render(){
 const [title,kicker]=pageNames[page];$('heading').textContent=$('crumb').textContent=title;$('kicker').textContent=kicker;
 $('today').textContent=state.today.slice(0,10).replaceAll('-',' / ');document.querySelectorAll('[data-page]').forEach(b=>b.classList.toggle('active',b.dataset.page===page));
 const all=state.works;let html='';
 if(page==='home'){
  const start=new Date(state.today.slice(0,10)+'T12:00:00Z');start.setUTCDate(start.getUTCDate()-(start.getUTCDay()+6)%7);
  const monday=start.toISOString().slice(0,10);
  html+=`<section class="hero" aria-labelledby="review-intro">
    <div><small class="eyebrow">抖音　/　小红书</small>
    <h2 id="review-intro">短视频内容复盘</h2>
    <p>导入后台截图，梳理每条作品的观看、互动和涨粉表现。<br>在每周的运营周报里，确定下一条视频值得尝试的改动。</p>
    <button type="button" data-page="archive">打开作品档案　↗</button></div>
    <div class="graphic" aria-hidden="true"><span class="sheet-back"></span><span class="sheet-front"><i></i></span></div>
   </section>`;
  html+='<div class="tiles">'+[['已归档作品',all.length,'条'],['本周发布并归档',all.filter(d=>d.published&&d.published.slice(0,10)>=monday&&d.published.slice(0,10)<=state.today.slice(0,10)).length,'条'],['已生成周报',state.weeks.length,'份']].map(([s,n,u])=>'<div class="tile"><small>'+s+'</small><strong>'+n+'<em>'+u+'</em></strong></div>').join('')+'</div>';
 }
 if(page!=='weekly'){
  const works=all.filter(d=>filter==='全部'||d.platform===filter);
  html+='<div class="sectionhead"><h2>'+(page==='home'?'最近作品':'全部作品')+'</h2><div class="filters">'+['全部','抖音','小红书'].map(f=>'<button class="'+(filter===f?'on':'')+'" data-filter="'+f+'">'+f+'</button>').join('')+'</div></div><div class="cards">';
  html+=(page==='home'?works.slice(0,4):works).map(d=>{const i=all.indexOf(d);return '<article class="item"><div class="stamp"><small>'+esc(d.published.slice(5,7)||'—')+' 月</small>'+esc(d.published.slice(8,10)||'—')+'</div><div><div class="meta">'+esc(d.platform)+' · '+esc(d.goal)+'</div><h3>'+esc(d.title)+'</h3><div class="meta">观察于 '+esc(d.observed.replace('T',' '))+' · '+d.history.length+' 次记录</div>'+(page==='archive'?'<div class="reportbuttons">'+d.history.map((h,j)=>'<button data-work="'+i+'" data-snap="'+j+'">'+esc(h.time.replace('T',' '))+'</button>').join('')+'</div>':'')+'</div><div class="right"><button class="link" data-update="'+i+'">补录</button><button data-work="'+i+'">查看复盘 ↗</button></div></article>'}).join('')||'<div class="empty">当前筛选下还没有作品。导入第一组截图后会显示在这里。</div>';
  html+='</div>';
 }
 if(page!=='archive'){html+='<div class="sectionhead"><h2>'+(page==='weekly'?'已生成的周报':'最近周报')+'</h2><small class="meta">'+(window.browserStudio?'周一 10:00 后打开汇总 · 北京时间':'每周一 10:00 · 北京时间')+'</small></div><div class="cards">'+(state.weeks.slice(0,page==='home'?1:undefined).map(weekCard).join('')||'<div class="empty">首份周报生成后会显示在这里。</div>')+'</div>'}
 $('surface').innerHTML=html;
}
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;const d=b.dataset;
 if(d.page){page=d.page;render();window.scrollTo(0,0)}
 if(d.filter){filter=d.filter;render()}
 if(d.close){$(d.close).close()}
 if(d.week)openReport('/reports/周报/'+d.week+'.html','运营周报');
 if(d.work!==undefined){let w=state.works[+d.work];openReport(w.history[Number(d.snap||0)].url,w.title)}
 if(d.update!==undefined)editor(state.works[+d.update]);
});
function row(name='',value='',compare='',owner=''){
 const el=document.createElement('div');el.className='metricrow';el.dataset.owner=owner;
 el.innerHTML='<input aria-label="指标名称" list="names" placeholder="指标名称"><input aria-label="读数" placeholder="读数及单位"><input aria-label="比较口径" placeholder="往期变化（可选）"><button type="button" aria-label="移除指标">×</button>';
 const inputs=el.querySelectorAll('input');[name,value,compare].forEach((v,i)=>inputs[i].value=v);el.querySelector('button').onclick=()=>el.remove();$('metrics').append(el);return el
}
function bindWork(w){if(w){$('title').value=w.title;$('platform').value=w.platform;$('published').value=w.published;$('goal').value=['观看','涨粉','互动','咨询'].includes(w.goal)?w.goal:'观看'}$('platform').disabled=!!w}
function editor(w){
 if(!state)return;session++;uploads.forEach(u=>URL.revokeObjectURL(u.url));uploads=[];importing=false;$('entry').reset();
 $('match').innerHTML='<option value="">新作品</option>'+state.works.map((d,i)=>'<option value="'+i+'">'+esc(d.platform+' · '+d.title)+'</option>').join('');
 $('match').value=w?String(state.works.indexOf(w)):'';bindWork(w);$('metrics').innerHTML='';$('previews').innerHTML='';$('rawtext').textContent='';$('raw').hidden=true;$('err').textContent='';$('ocrstatus').textContent='';$('save').disabled=false;
 $('observed').value=new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Shanghai',dateStyle:'short',timeStyle:'short'}).format(new Date()).replace(' ','T');
 $('names').innerHTML=state.fields.map(k=>'<option value="'+esc(k)+'">').join('');row();$('editor').showModal()
}
$('new').onclick=()=>editor();$('add').onclick=()=>row();$('match').onchange=()=>bindWork($('match').value===''?null:state.works[+$('match').value]);
function drawPreviews(){const box=$('previews');box.innerHTML='';uploads.forEach(u=>{let v=document.createElement('div');v.className='preview';let img=document.createElement('img');img.src=u.url;img.alt=u.file.name;let b=document.createElement('button');b.type='button';b.textContent='移除';b.disabled=importing;b.onclick=()=>{uploads=uploads.filter(x=>x!==u);URL.revokeObjectURL(u.url);$('metrics').querySelectorAll('.metricrow').forEach(r=>{if(r.dataset.owner===u.key)r.remove()});mergeImages();drawPreviews()};v.append(img,b);box.append(v)});$('raw').hidden=!uploads.some(u=>u.data);$('rawtext').textContent=uploads.filter(u=>u.data).map(u=>u.file.name+'\n'+u.data.lines.join(' · ')).join('\n\n')}
function mergeImages(){let existing=new Map();for(const el of $('metrics').children){const [a,b,c]=el.querySelectorAll('input');if(a.value)existing.set(a.value,[el,b,c]);else if(!b.value)el.remove()}
 let conflicts=new Set();for(const u of uploads){if(!u.data)continue;for(const [name,[v,c]] of Object.entries(u.data.fields)){const prev=existing.get(name);if(prev){if(prev[1].value!==v)conflicts.add(name);else if(!prev[2].value)prev[2].value=c;continue}const el=row(name,v,c,u.key);existing.set(name,[el,...Array.from(el.querySelectorAll('input')).slice(1)])}}
 return [...conflicts]}
async function addFiles(files){if(importing)return;const run=session;const list=Array.from(files);if(!list.length)return;importing=true;$('save').disabled=true;$('err').textContent='';let failed=[];
 for(const file of list){if(run!==session)return;if(!/image\/(png|jpeg)/.test(file.type)||file.size>18*1024*1024){failed.push(file.name+'（仅支持 18 MB 内 PNG/JPEG）');continue}
  const u={file,url:URL.createObjectURL(file),key:crypto.randomUUID()};uploads.push(u);drawPreviews();$('ocrstatus').textContent='正在本机识别 '+file.name+'…';
  try{u.data=await request('/api/ocr',{method:'POST',body:file});if(run!==session)return;if(!$('title').value&&u.data.title)$('title').value=u.data.title;if(!$('published').value&&u.data.published)$('published').value=u.data.published}
  catch(e){failed.push(file.name+'：'+e.message)}
 }
 if(run!==session)return;const conflicts=mergeImages();importing=false;drawPreviews();$('save').disabled=false;$('ocrstatus').textContent='识别完成，请核对指标名称、单位与时间。'+(conflicts.length?'多张截图的数值有差异，请核对 '+conflicts.join('、')+'。':'');if(failed.length)$('err').textContent=failed.join('；')+'。可以重新选择截图或手动添加指标。';
}
$('files').onchange=e=>{addFiles(e.target.files);e.target.value=''};$('drop').ondragover=e=>e.preventDefault();$('drop').ondrop=e=>{e.preventDefault();addFiles(e.dataTransfer.files)};
$('entry').onsubmit=async e=>{e.preventDefault();if(importing)return;$('save').disabled=true;$('err').textContent='';
 const fields=Array.from($('metrics').children,r=>Array.from(r.querySelectorAll('input'),i=>i.value.trim())).filter(f=>f.some(Boolean));
 if(fields.some(f=>!f[0]||!f[1])){$('err').textContent='请补全指标名称和读数，或移除该行。';$('save').disabled=false;return}
 const payload=Object.fromEntries(['title','platform','goal','published','observed','context'].map(k=>[k,$(k).value]));payload.fields=fields;if($('match').value!=='')payload.id=state.works[+$('match').value].id;
 try{const r=await request('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});$('editor').close();await refresh();openReport(r.url,payload.title)}catch(err){$('err').textContent=err.message}finally{$('save').disabled=false}
};
refresh().catch(e=>{$('surface').textContent='档案读取失败，请重新启动本地工具后刷新。 '+e.message});

