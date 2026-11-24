const KEY='lib_read_v1';
function getRead(){try{return JSON.parse(localStorage.getItem(KEY))||[]}catch(e){return[]}}
function setRead(a){localStorage.setItem(KEY,JSON.stringify(a))}
function markRead(id){const r=getRead();if(!r.includes(id)){r.push(id);setRead(r)}}
function unmarkRead(id){setRead(getRead().filter(x=>x!==id))}
const PREF_KEY='lib_pref_v1';
function getPref(){try{const p=JSON.parse(localStorage.getItem(PREF_KEY));if(p&&Array.isArray(p.later)&&Array.isArray(p.skip))return p;}catch(e){}return{later:[],skip:[]}}
function setPref(p){localStorage.setItem(PREF_KEY,JSON.stringify(p))}
function getLater(){return getPref().later}
function getSkip(){return getPref().skip}
function toggleIn(a,id){return a.includes(id)?a.filter(function(x){return x!==id}):a.concat([id])}
function toggleLater(id){const p=getPref();p.later=toggleIn(p.later,id);setPref(p);refreshPrefUI()}
function toggleSkip(id){const p=getPref();p.skip=toggleIn(p.skip,id);setPref(p);refreshPrefUI()}
const MEMO_KEY='lib_memo_v1';
function normalizeMemos(raw){
  const out={};
  if(!raw||typeof raw!=='object'||Array.isArray(raw))return out;
  Object.keys(raw).forEach(function(id){
    const v=raw[id];
    if(Array.isArray(v)){
      const arr=v.filter(function(e){return e&&typeof e.text==='string'&&e.text}).map(function(e){return{text:e.text,at:e.at||''}});
      if(arr.length)out[id]=arr;
    }else if(v&&typeof v.text==='string'&&v.text){
      out[id]=[{text:v.text,at:v.updated_at||''}];
    }
  });
  return out;
}
function getMemos(){
  try{
    const raw=JSON.parse(localStorage.getItem(MEMO_KEY));
    const norm=normalizeMemos(raw);
    if(JSON.stringify(raw||{})!==JSON.stringify(norm))setMemos(norm);
    return norm;
  }catch(e){return{}}
}
function setMemos(m){localStorage.setItem(MEMO_KEY,JSON.stringify(m))}
function splitMemoLines(text){
  const LF=String.fromCharCode(10),CR=String.fromCharCode(13);
  return String(text||'').split(CR).join(LF).split(LF).map(function(s){return s.trim()}).filter(function(s){return s.length>0});
}
function addMemos(id,text){
  const lines=splitMemoLines(text);
  if(!lines.length)return 0;
  const m=getMemos();const arr=(m[id]||[]).slice();const now=new Date().toISOString();
  lines.forEach(function(s){arr.push({text:s,at:now})});
  m[id]=arr;setMemos(m);return lines.length;
}
function updateMemoText(id,idx,text){
  const m=getMemos();const arr=(m[id]||[]).slice();
  if(idx<0||idx>=arr.length)return;
  if(String(text||'').trim()){arr[idx]={text:String(text),at:new Date().toISOString()};m[id]=arr;}
  else{arr.splice(idx,1);if(arr.length)m[id]=arr;else delete m[id];}
  setMemos(m);
}
function deleteMemoAt(id,idx){
  const m=getMemos();const arr=(m[id]||[]).slice();
  if(idx<0||idx>=arr.length)return;
  arr.splice(idx,1);if(arr.length)m[id]=arr;else delete m[id];setMemos(m);
}
function refreshMemoCounts(){
  const memos=getMemos();
  document.querySelectorAll('[data-memo-count]').forEach(function(el){
    const n=(memos[el.getAttribute('data-memo-count')]||[]).length;
    el.textContent=n?('（'+n+'）'):'';
  });
}
function renderMemoPanel(panel){
  const id=panel.getAttribute('data-memo-panel');
  const list=panel.querySelector('[data-memo-list]');
  const arr=getMemos()[id]||[];
  list.innerHTML='';
  if(!arr.length){list.innerHTML='<p class="meta">まだメモがありません。</p>';return;}
  arr.forEach(function(mm,i){
    const row=document.createElement('div');row.className='memo-row';
    const tx=document.createElement('div');tx.className='memo-row-text';tx.textContent=mm.text;
    const meta=document.createElement('div');meta.className='memo-row-meta';
    const dt=document.createElement('span');dt.className='meta';dt.textContent=fmtDate(mm.at);
    const del=document.createElement('button');del.type='button';del.className='mini skipb';del.textContent='削除';
    del.addEventListener('click',function(){deleteMemoAt(id,i);renderMemoPanel(panel);refreshMemoCounts();});
    meta.appendChild(dt);meta.appendChild(del);
    row.appendChild(tx);row.appendChild(meta);list.appendChild(row);
  });
}
function fmtDate(iso){try{const d=new Date(iso);return d.getFullYear()+'年'+(d.getMonth()+1)+'月'+d.getDate()+'日 '+String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0')}catch(e){return''}}
function refreshButtons(){
  const later=getLater(),skip=getSkip();
  document.querySelectorAll('[data-later-btn]').forEach(function(b){const on=later.includes(+b.dataset.laterBtn);b.classList.toggle('on',on);b.textContent=on?'後で読む ✓':'後で読む';});
  document.querySelectorAll('[data-skip-btn]').forEach(function(b){const on=skip.includes(+b.dataset.skipBtn);b.classList.toggle('on',on);b.textContent=on?'いらない ✓':'いらない';});
}
function refreshPrefUI(){refreshButtons();if(window.onPrefChange)window.onPrefChange();}
function applyReadState(){
  const read=getRead();
  document.querySelectorAll('[data-tid]').forEach(function(el){
    if(read.includes(+el.dataset.tid)){el.classList.add('is-read');const b=el.querySelector('[data-read-badge]');if(b)b.style.display='inline-block';}
  });
}
document.addEventListener('click',function(e){
  const lb=e.target.closest('[data-later-btn]');if(lb){toggleLater(+lb.dataset.laterBtn);return;}
  const sb=e.target.closest('[data-skip-btn]');if(sb){toggleSkip(+sb.dataset.skipBtn);}
});
const SORT_KEY='lib_sort_v1';
const SORT_KEYS=['default','total','novelty','interest','buzz','relevance','genre'];
function getSortPref(){
  try{const s=JSON.parse(localStorage.getItem(SORT_KEY));if(s&&SORT_KEYS.indexOf(s.key)>=0&&(s.dir==='asc'||s.dir==='desc'))return{key:s.key,dir:s.dir};}catch(e){}
  return{key:'default',dir:'desc'};
}
function setSortPref(p){localStorage.setItem(SORT_KEY,JSON.stringify(p))}
function sortItemsBy(items,pref){
  const key=pref.key,dir=(pref.dir==='asc')?1:-1;
  return items.slice().sort(function(a,b){
    if(key==='default')return a.i-b.i;
    const va=a[key],vb=b[key];
    if(va===null&&vb===null)return a.i-b.i;
    if(va===null)return 1;
    if(vb===null)return -1;
    const c=(va-vb)*dir;
    return (c!==0)?c:(a.i-b.i);
  });
}
function readSortVals(el){
  function num(name){const v=el.getAttribute(name);return (v===null||v==='')?null:parseFloat(v);}
  return {total:num('data-total'),novelty:num('data-novelty'),interest:num('data-interest'),buzz:num('data-buzz'),relevance:num('data-relevance'),genre:num('data-genre-idx')};
}
function applySort(){
  const pref=getSortPref();
  document.querySelectorAll('ul.sortable').forEach(function(ul){
    const els=Array.prototype.slice.call(ul.children).filter(function(el){return el.hasAttribute&&el.hasAttribute('data-tid');});
    const items=els.map(function(el,i){const o=readSortVals(el);o.i=i;o.el=el;return o;});
    sortItemsBy(items,pref).forEach(function(o){ul.appendChild(o.el);});
  });
  document.querySelectorAll('[data-sort-key]').forEach(function(sel){sel.value=pref.key;});
  document.querySelectorAll('[data-sort-dir]').forEach(function(btn){
    btn.textContent=(pref.dir==='asc')?'昇順 ▲':'降順 ▼';
    btn.disabled=(pref.key==='default');
    btn.style.opacity=(pref.key==='default')?'0.5':'';
  });
}
function initSortUI(){
  document.querySelectorAll('[data-sort-key]').forEach(function(sel){
    sel.value=getSortPref().key;
    sel.addEventListener('change',function(){
      const p=getSortPref();p.key=sel.value;setSortPref(p);applySort();
    });
  });
  document.querySelectorAll('[data-sort-dir]').forEach(function(btn){
    btn.addEventListener('click',function(){
      const p=getSortPref();p.dir=(p.dir==='asc')?'desc':'asc';setSortPref(p);applySort();
    });
  });
  if(document.querySelector('ul.sortable'))applySort();
}
const FILTER_KEY='lib_filter_v1';
const FILTER_STATUSES=['all','unread','read','later','skip'];
function getFilterPref(){
  try{const f=JSON.parse(localStorage.getItem(FILTER_KEY));if(f&&typeof f==='object'&&!Array.isArray(f)){
    return {status:(FILTER_STATUSES.indexOf(f.status)>=0)?f.status:'all',
            genre:(typeof f.genre==='string'&&f.genre)?f.genre:'all',
            issue:(typeof f.issue==='string'&&f.issue)?f.issue:'all',
            keyword:(typeof f.keyword==='string')?f.keyword:''};
  }}catch(e){}
  return {status:'all',genre:'all',issue:'all',keyword:''};
}
function setFilterPref(f){localStorage.setItem(FILTER_KEY,JSON.stringify(f))}
function themeMatchesStatus(id,status,read,later,skip){
  if(status==='unread')return !read.includes(id);
  if(status==='read')return read.includes(id);
  if(status==='later')return later.includes(id);
  if(status==='skip')return skip.includes(id);
  return true;
}
function rowMatchesFilter(v,f,ctx){
  if(!themeMatchesStatus(v.tid,f.status,ctx.read,ctx.later,ctx.skip))return false;
  if(f.genre!=='all'&&v.genre!==f.genre)return false;
  if(f.issue!=='all'&&v.issue!==f.issue)return false;
  if(f.keyword&&String(v.title||'').indexOf(f.keyword)<0)return false;
  return true;
}
document.addEventListener('DOMContentLoaded',function(){
  initSortUI();
  const mb=document.getElementById('menuBtn'),mp=document.getElementById('menuPanel');
  if(mb&&mp){mb.addEventListener('click',function(){mp.hidden=!mp.hidden;});mp.querySelectorAll('a').forEach(function(a){a.addEventListener('click',function(){mp.hidden=true;});});}
  document.querySelectorAll('[data-memo-open]').forEach(function(btn){
    btn.addEventListener('click',function(){
      const panel=document.querySelector('[data-memo-panel="'+btn.getAttribute('data-memo-open')+'"]');
      if(panel){renderMemoPanel(panel);panel.hidden=false;}
    });
  });
  document.querySelectorAll('[data-memo-panel]').forEach(function(panel){
    const id=panel.getAttribute('data-memo-panel');
    panel.querySelector('[data-memo-close]').addEventListener('click',function(){panel.hidden=true;});
    panel.addEventListener('click',function(e){if(e.target===panel)panel.hidden=true;});
    panel.querySelector('[data-memo-add]').addEventListener('click',function(){
      const ta=panel.querySelector('[data-memo-input]');
      if(addMemos(id,ta.value)>0){ta.value='';renderMemoPanel(panel);refreshMemoCounts();}
    });
  });
  refreshMemoCounts();
  applyReadState();
  refreshPrefUI();
});
