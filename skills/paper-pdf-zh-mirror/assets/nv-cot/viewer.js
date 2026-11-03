const decode=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
const pdfjs=await import(URL.createObjectURL(new Blob([decode(PACKAGE.pdfjs)],{type:'text/javascript'})));
pdfjs.GlobalWorkerOptions.workerSrc=URL.createObjectURL(new Blob([decode(PACKAGE.worker)],{type:'text/javascript'}));
const documents=await Promise.all([pdfjs.getDocument({data:decode(PACKAGE.original)}).promise,pdfjs.getDocument({data:decode(PACKAGE.translated)}).promise]);
const dimensions=await Promise.all(Array.from({length:documents[0].numPages},async(_,i)=>{const p=await documents[0].getPage(i+1);const v=p.getViewport({scale:1});return {width:v.width,height:v.height}}));
const baseWidth=Math.max(...dimensions.map(p=>p.width));
const panes=[...document.querySelectorAll('.pane')];let columns=1,zoom=1,scale=1,pageNumber=1,generation=0,scrollLock=false,rowTops=[];
const report=PACKAGE.quality;const total=documents[0].numPages;
document.querySelector('#total').textContent=total;
const select=document.querySelector('#page');for(let n=1;n<=total;n++)select.add(new Option('第 '+n+' 页',n));
const observer=new IntersectionObserver(entries=>{for(const entry of entries)if(entry.isIntersecting)renderCanvas(entry.target)}, {rootMargin:'650px'});
async function renderCanvas(box){
  if(box.dataset.rendered===String(generation)||box.dataset.loading===String(generation))return;
  const mine=generation;box.dataset.loading=String(mine);const which=+box.dataset.doc;const number=+box.dataset.page;
  const pdfPage=await documents[which].getPage(number);if(mine!==generation)return;
  const canvas=document.createElement('canvas');canvas.setAttribute('aria-label',(which?'中文版':'英文原版')+'第'+number+'页');
  const ratio=Math.min(devicePixelRatio||1,2),viewport=pdfPage.getViewport({scale:scale*ratio});canvas.width=Math.ceil(viewport.width);canvas.height=Math.ceil(viewport.height);canvas.style.width='100%';
  try{await pdfPage.render({canvasContext:canvas.getContext('2d'),viewport}).promise;if(mine!==generation)return;box.replaceChildren(canvas);box.dataset.rendered=String(mine)}catch(err){box.textContent='第 '+number+' 页渲染失败：'+err.message;window.viewerError=err.message;}
}
function layout(){
  generation++;observer.disconnect();
  const widths=panes.filter(p=>p.offsetWidth>0).map(p=>p.clientWidth);scale=(Math.min(...widths)-36-(columns-1)*18)/(baseWidth*columns)*zoom;
  rowTops=[];let offset=0;for(let n=0;n<total;n+=columns){rowTops.push(offset);offset+=Math.max(...dimensions.slice(n,n+columns).map(p=>p.height))*scale+18}
  for(let d=0;d<panes.length;d++){
    const grid=panes[d].querySelector('.pages');grid.replaceChildren();grid.style.gridTemplateColumns=`repeat(${columns},${baseWidth*scale}px)`;
    for(let n=1;n<=total;n++){const box=document.createElement('div');box.className='pdf-page';box.style.width=dimensions[n-1].width*scale+'px';box.style.height=dimensions[n-1].height*scale+'px';box.dataset.page=n;box.dataset.doc=d;box.textContent='第 '+n+' 页';grid.append(box);observer.observe(box)}
  }
  goTo(pageNumber);document.querySelector('#scale').textContent=Math.round(zoom*100)+'%';
}
function goTo(n){pageNumber=Math.max(1,Math.min(total,n));select.value=pageNumber;const top=rowTops[Math.floor((pageNumber-1)/columns)];for(const p of panes)p.scrollTop=top;showQuality();}
function showQuality(){const p=report.pages[pageNumber-1];document.querySelector('#status').textContent=p.status==='pass'?'本页结构检查通过':'本页有待审校项';document.querySelector('#status').className=p.status;document.querySelector('#quality-page').textContent='第 '+pageNumber+' 页';document.querySelector('#quality-body').innerHTML=`<p>页尺寸：${p.same_dimensions?'一致':'异常'} · 原图对象：${p.images_preserved?'全部保留':'有变化'}</p><p>替换文本区域：${p.replacement_count} · 溢出：${p.overflow_count}</p><p>替换区域外像素变化：${p.outside_mask_changed_pixels}</p><p>微小字号区域：${p.small_font_elements.length} · 未映射自然语言块：${p.unmapped.length}</p><p>原文与译文截图已逐页生成。公式与图像保留检查通过不等于译文语义已由人工核准。</p>${p.unmapped.map(x=>'<p>'+escapeHTML(x.id+'：'+x.text)+'</p>').join('')}<p>行内数学及复杂示例图中的原始图像文字仍需人工核对，详见审校报告。</p>`;}
function escapeHTML(s){return s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
for(const pane of panes)pane.addEventListener('scroll',()=>{
  if(scrollLock)return;scrollLock=true;for(const other of panes)if(other!==pane)other.scrollTop=pane.scrollTop;
  let row=0;for(let i=0;i<rowTops.length;i++)if(rowTops[i]<=pane.scrollTop+10)row=i;const current=Math.min(total,row*columns+1);if(current!==pageNumber){pageNumber=current;select.value=current;showQuality()}
  requestAnimationFrame(()=>scrollLock=false);
});
select.onchange=()=>goTo(+select.value);document.querySelector('#prev').onclick=()=>goTo(pageNumber-1);document.querySelector('#next').onclick=()=>goTo(pageNumber+1);
document.querySelector('#zoom-in').onclick=()=>{zoom=Math.min(2.5,zoom+.1);layout()};document.querySelector('#zoom-out').onclick=()=>{zoom=Math.max(.5,zoom-.1);layout()};document.querySelector('#fit').onclick=()=>{zoom=1;layout()};
document.querySelector('#columns').onchange=e=>{columns=+e.target.value;layout()};
document.querySelector('#view').onchange=e=>{document.body.dataset.view=e.target.value;layout()};
document.querySelector('#quality').onclick=()=>document.querySelector('#report').showModal();document.querySelector('#close-report').onclick=()=>document.querySelector('#report').close();
document.querySelector('#download').onclick=()=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([decode(PACKAGE.translated)],{type:'application/pdf'}));a.download='NV-CoT_中文镜像.pdf';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),60000)};
let resizeTimer;window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(layout,120)});
layout();document.querySelector('#loading').remove();window.viewerReady=true;window.viewerState=()=>({page:pageNumber,columns,zoom,scale,canvases:document.querySelectorAll('canvas').length,pages:total});
