// 后台管理 JS：岗位 CRUD + Excel 导入 + 归档 + 用户 + 日志
function switchTab(name){
  document.querySelectorAll('.tab').forEach((t,i)=>{
    const panels=['jobs','import','archive','users','logs'];
    t.classList.toggle('active', panels[i]===name);
  });
  document.querySelectorAll('.tab-panel').forEach(p=>p.style.display='none');
  document.getElementById('tab_'+name).style.display='block';
  if(name==='archive') loadArchives();
  if(name==='users') loadUsers();
  if(name==='logs') loadLogs();
}

// ===== 岗位管理 =====
async function loadAdminJobs(page){
  page = page||1;
  const kw = document.getElementById('jobs_keyword').value.trim();
  const data = await fetchJSON(`/api/admin/jobs?page=${page}&keyword=${encodeURIComponent(kw)}`);
  if(data.code!==0) return;
  const d = data.data;
  document.getElementById('jobs_count').textContent = `共 ${d.total} 条`;
  const tbody = document.querySelector('#jobsTable tbody');
  tbody.innerHTML = d.list.map(j=>`
    <tr class="${j.is_caring?'row-caring':''}">
      <td>${j.id}</td>
      <td>${j.region||'-'}</td>
      <td>${escapeHtml(j.company)}</td>
      <td>${escapeHtml(j.job_name)}</td>
      <td>${j.recruit_num}</td>
      <td>${j.salary_text}</td>
      <td>${j.education}</td>
      <td>${j.industry}</td>
      <td>${j.is_caring?'<span class="caring-flag">爱心</span>':'-'}</td>
      <td>${j.status==='active'?'<span class="status-active">招聘中</span>':'<span class="status-archived">已下架</span>'}</td>
      <td>
        <button class="btn btn-default btn-sm op-btn" onclick="openEditModal(${j.id})">编辑</button>
        <button class="btn btn-warning btn-sm op-btn" onclick="toggleStatus(${j.id},'${j.status==='active'?'archived':'active'}')">${j.status==='active'?'下架':'上架'}</button>
        <button class="btn btn-danger btn-sm op-btn" onclick="deleteJob(${j.id})">删除</button>
      </td>
    </tr>`).join('');
  document.getElementById('jobs_pagination').innerHTML = renderPagination(d.total, d.total_pages, d.page, 'loadAdminJobs');
}

function openEditModal(id){
  document.getElementById('editModal').classList.add('show');
  ['j_id','j_company','j_job_name','j_contact','j_phone','j_recruit_num','j_salary','j_education','j_duty','j_welfare'].forEach(i=>document.getElementById(i).value='');
  document.getElementById('j_recruit_num').value='0';
  document.getElementById('j_caring').checked=false;
  document.getElementById('j_cert').checked=false;
  document.getElementById('editModalTitle').textContent = '新增岗位';
  if(id){
    fetchJSON(`/api/admin/job/${id}`).then(data=>{
      if(data.code!==0) return;
      const j = data.data;
      document.getElementById('editModalTitle').textContent = '编辑岗位 - #'+id;
      document.getElementById('j_id').value = j.id;
      document.getElementById('j_company').value = j.company||'';
      document.getElementById('j_job_name').value = j.job_name||'';
      document.getElementById('j_contact').value = j.contact||'';
      document.getElementById('j_phone').value = j.phone||'';
      document.getElementById('j_recruit_num').value = j.recruit_num||0;
      document.getElementById('j_salary').value = j.salary_text||'';
      document.getElementById('j_education').value = j.education||'';
      if(j.region) document.getElementById('j_region').value = j.region;
      if(j.industry) document.getElementById('j_industry').value = j.industry;
      if(j.shift) document.getElementById('j_shift').value = j.shift;
      document.getElementById('j_duty').value = j.job_duty||'';
      document.getElementById('j_welfare').value = j.welfare_text||'';
      document.getElementById('j_caring').checked = !!j.is_caring;
      document.getElementById('j_cert').checked = !!j.has_cert_priority;
    });
  }
}

async function saveJob(){
  const id = document.getElementById('j_id').value;
  const payload = {
    company: document.getElementById('j_company').value,
    job_name: document.getElementById('j_job_name').value,
    contact: document.getElementById('j_contact').value,
    phone: document.getElementById('j_phone').value,
    recruit_num: document.getElementById('j_recruit_num').value,
    salary: document.getElementById('j_salary').value,
    education: document.getElementById('j_education').value,
    region: document.getElementById('j_region').value,
    industry: document.getElementById('j_industry').value,
    shift: document.getElementById('j_shift').value,
    duty: document.getElementById('j_duty').value,
    welfare: document.getElementById('j_welfare').value,
    remark: (document.getElementById('j_caring').checked?'爱心 ':'') + (document.getElementById('j_cert').checked?'持证 ':''),
  };
  const url = id ? `/api/admin/job/${id}` : '/api/admin/job/add';
  const method = id ? 'POST' : 'POST';
  const res = await fetch(url, {method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
  const data = await res.json();
  if(data.code===0){
    showToast(id?'已更新':'已新增','success');
    document.getElementById('editModal').classList.remove('show');
    loadAdminJobs(1);
  } else {
    showToast(data.msg||'保存失败','error');
  }
}

async function deleteJob(id){
  if(!confirm('确认删除该岗位？删除不可恢复。')) return;
  const res = await fetch(`/api/admin/job/${id}`, {method:'DELETE'});
  const data = await res.json();
  if(data.code===0){ showToast('已删除','success'); loadAdminJobs(currentAdminPage); }
}

async function toggleStatus(id, status){
  const res = await fetch(`/api/admin/job/${id}/status`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({status})});
  const data = await res.json();
  if(data.code===0){ showToast(status==='active'?'已上架':'已下架','success'); loadAdminJobs(currentAdminPage); }
}
let currentAdminPage=1;
// 覆盖分页回调记录当前页
const _origLoad = loadAdminJobs;
loadAdminJobs = function(page){ page=page||1; currentAdminPage=page; _origLoad(page); };

// ===== Excel 导入（新流程：上传 → 预览 → 确认导入） =====
let _previewData = null;  // 保存预览结果，供确认导入使用

async function uploadExcel(){
  const f = document.getElementById('excelFile').files[0];
  if(!f){ showToast('请先选择文件','warning'); return; }
  const fd = new FormData();
  fd.append('file', f);
  showToast('正在解析 Excel 结构...','');
  try{
    const res = await fetch('/api/admin/excel_preview', {method:'POST', body: fd});
    const data = await res.json();
    if(data.code!==0){
      document.getElementById('importResult').innerHTML = `<div class="import-error">${data.msg||'解析失败'}</div>`;
      return;
    }
    _previewData = data.data;
    renderPreview(data.data);
  }catch(e){
    showToast('解析失败：'+e.message,'error');
  }
}

function renderPreview(d){
  const box = document.getElementById('importResult');
  let html = '';
  html += `<div class="import-success">📋 Excel 结构分析完成</div>`;
  html += `<div style="margin-top:10px;display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:#475569">`;
  html += `<span>📄 文件名：<b>${d.file_name}</b></span>`;
  html += `<span>📑 表头行：第 ${d.header_row_index} 行</span>`;
  html += `<span>📊 识别字段：<b style="color:${d.matched_fields>=8?'#059669':(d.matched_fields>=5?'#d97706':'#dc2626')}">${d.matched_fields}</b> / 14</span>`;
  html += `<span>📦 数据行数：${d.total_data_rows}</span>`;
  html += `</div>`;

  // 字段映射表
  html += `<div style="margin-top:14px"><b>🔍 字段映射（自动识别 ${d.matched_fields} 个字段）</b></div>`;
  html += `<table class="data" style="margin-top:8px;font-size:12px">`;
  html += `<thead><tr><th>标准字段</th><th>状态</th><th>Excel 表头</th><th>命中关键字</th><th>操作</th></tr></thead><tbody>`;
  d.field_mapping.forEach(fm=>{
    const color = fm.matched ? '#059669' : '#dc2626';
    const bg = fm.matched ? '#ecfdf5' : '#fef2f2';
    const options = d.headers.map((h,i)=>{
      const sel = (fm.matched && fm.header===h) ? ' selected' : '';
      return `<option value="${i}"${sel}>${h||'(空)'}</option>`;
    }).join('');
    html += `<tr style="background:${bg}">`;
    html += `<td style="font-weight:500">${fm.label}</td>`;
    html += `<td style="color:${color}">${fm.matched?'✓ 已匹配':'✗ 未匹配'}</td>`;
    html += `<td>${fm.matched?fm.header:'—'}</td>`;
    html += `<td style="color:#94a3b8">${fm.matched_keyword||'—'}</td>`;
    html += `<td><select data-field="${fm.field}" onchange="updateFieldMapping('${fm.field}',this.value)">${options}</select></td>`;
    html += `</tr>`;
  });
  html += `</tbody></table>`;

  // 未匹配表头
  if(d.unmatched_headers && d.unmatched_headers.length){
    html += `<div style="margin-top:12px"><b style="color:#d97706">⚠️ 未匹配的表头：</b> ${d.unmatched_headers.map(h=>'<span class="tag" style="background:#fef3c7;color:#92400e">'+h+'</span>').join(' ')}</div>`;
  }

  // 数据预览
  if(d.sample_rows && d.sample_rows.length){
    html += `<div style="margin-top:14px"><b>👀 数据预览（前 ${d.sample_rows.length} 行）</b></div>`;
    const sampleKeys = Object.keys(d.sample_rows[0]);
    html += `<div style="overflow-x:auto;margin-top:8px">`;
    html += `<table class="data" style="font-size:12px"><thead><tr>`;
    sampleKeys.forEach(k=>html += `<th>${k}</th>`);
    html += `</tr></thead><tbody>`;
    d.sample_rows.forEach(row=>{
      html += `<tr>`;
      sampleKeys.forEach(k=>html += `<td>${row[k]!==undefined&&row[k]!==null?String(row[k]).slice(0,40):''}</td>`);
      html += `</tr>`;
    });
    html += `</tbody></table></div>`;
  }

  // 确认导入按钮
  html += `<div style="margin-top:20px;text-align:center">`;
  html += `<button class="btn btn-primary" onclick="confirmImport()" style="padding:10px 30px;font-size:15px">✓ 确认导入 ${d.total_data_rows} 条数据</button>`;
  html += `<button class="btn btn-default" onclick="document.getElementById('importResult').innerHTML=''" style="margin-left:10px">取消</button>`;
  html += `</div>`;

  box.innerHTML = html;
}

function updateFieldMapping(field, colIdx){
  if(!_previewData) return;
  // 更新字段映射
  _previewData.field_mapping.forEach(fm=>{
    if(fm.field===field){
      const h = _previewData.headers[parseInt(colIdx)]||'';
      fm.matched = !!h;
      fm.header = h;
      fm.matched_keyword = '用户指定';
    }
  });
}

async function confirmImport(){
  if(!_previewData) return;
  // 收集用户调整后的映射
  const mapping = {};
  _previewData.field_mapping.forEach(fm=>{
    if(fm.matched){
      // 找到对应的 col_idx
      const idx = _previewData.headers.indexOf(fm.header);
      if(idx>=0) mapping[fm.field] = idx;
    }
  });
  showToast('正在导入数据...','');
  try{
    const res = await fetch('/api/admin/import_excel',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({file_path: _previewData.file_path, mapping})
    });
    const data = await res.json();
    if(data.code===0){
      const d = data.data;
      let html = `<div class="import-success">✓ 导入完成：成功 ${d.success} 条，跳过 ${d.skip} 条</div>`;
      if(d.errors && d.errors.length){
        html += '<div class="import-skip">错误明细（前 '+d.errors.length+' 条）：</div>';
        d.errors.forEach(e=>html += `<div class="import-error">${e}</div>`);
      }
      document.getElementById('importResult').innerHTML = html;
      showToast(`成功导入 ${d.success} 条`,'success');
      _previewData = null;
      loadAdminJobs(1);
    } else {
      showToast(data.msg||'导入失败','error');
    }
  }catch(e){
    showToast('导入失败：'+e.message,'error');
  }
}

function downloadTemplate(){
  const headers = ['企业名称','联系人','联系电话','岗位名称','招聘人数','薪资','学历要求','地区','行业','班次','岗位职责','福利待遇','备注'];
  const sample = ['杭州XX电子有限公司','王经理','0571-88001122','电子装配工','50','5000-7000','初中','杭州','电子科技','两班倒','流水线组装','五险一金、包吃住、双休',''];
  const csv = '\ufeff' + [headers, sample].map(r=>r.join(',')).join('\n');
  const blob = new Blob([csv], {type:'text/csv;charset=utf-8'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = '岗位导入模板.csv';
  a.click();
}

// ===== 归档 =====
async function loadArchives(){
  const data = await fetchJSON('/api/admin/archives');
  if(data.code!==0) return;
  document.getElementById('archiveList').innerHTML = data.data.map(a=>`
    <tr><td>${a.id}</td><td>${a.archive_month}</td><td>${a.backup_time}</td>
    <td><button class="btn btn-warning btn-sm" onclick="restoreArchive(${a.id})">恢复</button></td></tr>`).join('') || '<tr><td colspan="4" style="text-align:center;color:#94a3b8">暂无归档</td></tr>';
}

async function createArchive(){
  const month = document.getElementById('archiveMonth').value;
  const res = await fetch('/api/admin/archive', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({month})});
  const data = await res.json();
  if(data.code===0){ showToast('归档快照已生成','success'); loadArchives(); }
}

async function restoreArchive(id){
  if(!confirm('恢复将覆盖当前全部在岗数据，确认继续？')) return;
  const res = await fetch(`/api/admin/restore/${id}`, {method:'POST'});
  const data = await res.json();
  if(data.code===0){ showToast(`已恢复 ${data.data.restored} 条岗位`,'success'); loadArchives(); }
}

// ===== 用户 =====
async function loadUsers(){
  const data = await fetchJSON('/api/admin/users');
  if(data.code!==0) return;
  const roleMap = {admin:'管理员', staff:'就业专员', visitor:'访客'};
  document.getElementById('userList').innerHTML = data.data.map(u=>`
    <tr><td>${u.id}</td><td>${u.username}</td><td>${roleMap[u.role]||u.role}</td><td>${u.create_time}</td></tr>`).join('');
}

// ===== 日志 =====
async function loadLogs(){
  const data = await fetchJSON('/api/admin/logs');
  if(data.code!==0) return;
  document.getElementById('logList').innerHTML = data.data.map(l=>`
    <tr><td>${l.op_time}</td><td>${l.operator}</td><td>${l.op_type}</td><td style="font-size:12px;color:#64748b">${l.detail||'-'}</td></tr>`).join('') || '<tr><td colspan="4" style="text-align:center;color:#94a3b8">暂无日志</td></tr>';
}

document.addEventListener('DOMContentLoaded', ()=>loadAdminJobs(1));
