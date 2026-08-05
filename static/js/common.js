// 公共 JS：Toast 提示、权限判断、fetch 封装
function showToast(msg, type){
  let t = document.querySelector('.toast');
  if(!t){ t = document.createElement('div'); t.className='toast'; document.body.appendChild(t); }
  t.className = 'toast ' + (type||'');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(()=>t.classList.remove('show'), 2500);
}

async function fetchJSON(url, opts){
  opts = opts || {};
  opts.headers = Object.assign({'Accept':'application/json'}, opts.headers||{});
  const res = await fetch(url, opts);
  if(res.status === 401){ showToast('登录已失效，请重新登录','error'); setTimeout(()=>location.href='/',1500); throw new Error('401'); }
  if(res.status === 403){ showToast('权限不足','error'); throw new Error('403'); }
  return res.json();
}

// 获取当前用户角色
function currentUserRole(){ return window.__USER_ROLE__ || ''; }

// 渲染福利标签 HTML
function renderLabels(labels){
  if(!labels || !labels.length) return '<span style="color:#94a3b8;font-size:12px">无</span>';
  return labels.map(l=>`<span class="tag tag-welfare">${l}</span>`).join('');
}

// 薪资高亮
function salaryClass(job){ return job.max_salary>=8000 ? 'tag-highsalary' : ''; }

// 分页渲染
function renderPagination(total, total_pages, page, cb){
  let html = '';
  html += `<button ${page<=1?'disabled':''} onclick="${cb}(${page-1})}">上一页</button>`;
  const start = Math.max(1, page-2), end = Math.min(total_pages, page+2);
  if(start>1){ html += `<button onclick="${cb}(1)">1</button>`; if(start>2) html += '<span>...</span>'; }
  for(let i=start;i<=end;i++){ html += `<button class="${i===page?'active':''}" onclick="${cb}(${i})}">${i}</button>`; }
  if(end<total_pages){ if(end<total_pages-1) html += '<span>...</span>'; html += `<button onclick="${cb}(${total_pages})}">${total_pages}</button>`; }
  html += `<button ${page>=total_pages?'disabled':''} onclick="${cb}(${page+1})}">下一页</button>`;
  html += `<span style="margin-left:10px;color:#64748b">共 ${total} 条 / ${total_pages} 页</span>`;
  return html;
}
