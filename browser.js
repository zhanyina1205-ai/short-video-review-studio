/* GitHub Pages adapter. Records live in the current browser, one key per snapshot. */
window.browserStudio = (() => {
  const prefix = 'short-video-review-studio/v1/';
  const assets = new URL('./vendor/', document.baseURI).href;
  const platformTime = () => new Intl.DateTimeFormat('sv-SE', {
    timeZone:'Asia/Shanghai', dateStyle:'short', timeStyle:'short'
  }).format(new Date()).replace(' ', 'T');
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
  })[c]);
  let template, fields, runtime, ocrWorker;
  async function file(path, json=false) {
    const r = await fetch(new URL(path, document.baseURI));
    if (!r.ok) throw Error('资源加载失败，请刷新重试');
    return json ? r.json() : r.text();
  }
  function script(name) {
    return new Promise((resolve,reject)=>{
      const s=document.createElement('script'); s.src=assets+name;
      s.onload=resolve; s.onerror=()=>reject(Error('识别或分析组件加载失败，请重试'));document.head.append(s);
    });
  }
  async function engine() {
    if (!runtime) runtime=(async()=>{
      await script('pyodide.js');
      const py=await loadPyodide({indexURL:assets});
      await py.runPythonAsync(await file('./analysis.py'));
      py.runPython('import json');
      return py;
    })().catch(e=>{runtime=null;throw e});
    return runtime;
  }
  async function analyze(fn,input) {
    const py=await engine();
    py.globals.set('payload_text',JSON.stringify(input));
    try { return JSON.parse(py.runPython('json.dumps('+fn+'(json.loads(payload_text)))')) }
    catch(e){throw Error(String(e.message).split('ValueError: ').pop().trim())}
  }
  function records() {
    return Object.keys(localStorage).filter(k=>k.startsWith(prefix))
      .map(k=>JSON.parse(localStorage.getItem(k))).sort((a,b)=>b.observed.localeCompare(a.observed));
  }
  function path(d) { return prefix+d.id+'/'+d.observed }
  function works() {
    const latest=new Map();
    for(const d of records()){
      if(!latest.has(d.id)) latest.set(d.id,{...d,history:[]});
      latest.get(d.id).history.push({time:d.observed,url:path(d)});
    }
    return [...latest.values()];
  }
  function monday(day){
    const d=new Date(day+'T12:00:00Z');
    d.setUTCDate(d.getUTCDate()-(d.getUTCDay()+6)%7);
    return d.toISOString().slice(0,10);
  }
  function weekGroups(items,today){
    const thisWeek=monday(today.slice(0,10)), groups=new Map();
    for(const d of items.filter(x=>x.published)){
      const start=monday(d.published.slice(0,10));
      const ready=new Date(start+'T10:00:00+08:00').getTime()+7*86400000;
      if(start>=thisWeek || Date.now()<ready) continue;
      if(!groups.has(start)) groups.set(start,[]);
      groups.get(start).push(d);
    }
    return groups;
  }
  async function recognize(image){
    if(!ocrWorker)ocrWorker=(async()=>{
      await script('tesseract.min.js');
      return Tesseract.createWorker('chi_sim+eng',1,{
        workerPath:assets+'worker.min.js',corePath:assets,langPath:assets
      });
    })().catch(e=>{ocrWorker=null;throw e});
    const worker=await ocrWorker;
    const bitmap=await createImageBitmap(image);
    const width=bitmap.width,height=bitmap.height;bitmap.close();
    const {data}=await worker.recognize(image);
    const blocks=[];
    for(const line of data.lines || []){
      let group;
      for(const word of line.words || []){
        const box=word.bbox;
        if(!group || box.x0-group.right>width*.032){
          group={t:'',x:box.x0/width,y:box.y0/height,right:box.x1};blocks.push(group);
        }
        group.t+=word.text;group.right=box.x1;
      }
    }
    const lines=data.text.split(/\r?\n/).map(s=>s.trim()).filter(Boolean);
    const result={lines,fields:await analyze('extract',blocks)};
    const index=lines.findIndex(s=>/20\d\d-\d\d-\d\d\s+\d\d:\d\d.*发\s*布/.test(s));
    if(index>=0){result.published=lines[index].match(/20\d\d-\d\d-\d\d\s+\d\d:\d\d/)[0].replace(/\s+/,'T');result.title=lines[index-1]||''}
    return result;
  }
  async function save(d){
    const byTitle=works().find(x=>x.platform===d.platform&&x.title===d.title&&x.published===d.published);
    d.id=d.id || byTitle?.id || crypto.randomUUID();
    if(!d.title.trim() || !d.observed)throw Error('请填写标题和观察时间');
    if(d.published && d.published>d.observed)throw Error('观察时间应在发布之后');
    if(localStorage.getItem(path(d)))throw Error('同一作品的这个观察时间已归档');
    const doc=await analyze('make_report',d);
    if(d.context?.trim())doc.sections.unshift(['补充观察',d.context.trim()]);
    localStorage.setItem(path(doc),JSON.stringify(doc));return {url:path(doc)};
  }
  function weekly(start){
    const list=weekGroups(works(),platformTime()).get(start)||[];
    const stats=new Map();
    for(const d of list){
      if(!stats.has(d.platform))stats.set(d.platform,{});
      const group=stats.get(d.platform);
      for(const [key,n] of Object.entries(d.counts)){group[key]??={total:0,samples:0};group[key].total+=n;group[key].samples++}
    }
    const names={plays:'播放量',views:'观看量',likes:'点赞',comments:'评论',saves:'收藏',shares:'分享',gained:'吸粉',lost:'脱粉'};
    const metrics=[];
    for(const [platform,group] of stats)for(const [key,s] of Object.entries(group)){
      metrics.push([platform,names[key]||key,s.total.toLocaleString(),s.samples+' 条有记录','按作品最新观察时间累计']);
    }
    const sections=list.map(d=>[d.title+' · '+d.platform,d.summary+'\n观察时间 '+d.observed+'\n'+(d.sections.find(s=>s[0].includes('实验'))?.[1]||'')]);
    return {title:start+' 发布周运营周报',note:'按北京自然周归档；同一作品只计一次。',summary:'本周归档 '+list.length+' 条作品。以下为各作品截至最新截图时的累计数据。',highlights:[['作品数',list.length]],metrics,sections};
  }
  function report(url){
    const w=url.startsWith('/reports/周报/');
    const d=w?weekly(url.split('/').pop().slice(0,10)):JSON.parse(localStorage.getItem(url));
    if(!d)throw Error('未找到这份报告');
    const cols=w?['平台','指标','结果','样本','口径']:['维度','指标','读数','比较口径','解读'];
    const values={title:escape(d.title),kind:w?'运营周报':escape(d.platform)+' · 单条复盘',summary:escape(d.summary),note:escape(d.note),
      cards:d.highlights.map(([k,v])=>'<div><small>'+escape(k)+'</small><b>'+escape(v)+'</b></div>').join(''),
      table:'<div class="scroll"><table><thead><tr>'+cols.map(s=>'<th>'+s+'</th>').join('')+'</tr></thead><tbody>'+d.metrics.map(r=>'<tr>'+r.map(c=>'<td>'+escape(c)+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>',
      sections:d.sections.map(([k,v])=>'<article><h2>'+escape(k)+'</h2><p>'+escape(v)+'</p></article>').join('')};
    return template.replace(/\$(title|kind|summary|note|cards|table|sections)\b/g,(_,k)=>values[k]);
  }
  async function request(url,opts){
    if(url==='/api/ocr')return recognize(opts.body);
    if(url==='/api/save')return save(JSON.parse(opts.body));
    if(url!=='/api/state')throw Error('未知操作');
    if(!template || !fields)[template,fields]=await Promise.all([file('./report.html'),file('./fields.json',true)]);
    const items=works(),today=platformTime();
    return {works:items,today,fields,weeks:[...weekGroups(items,today).keys()].sort().reverse()};
  }
  return {request,report};
})();
