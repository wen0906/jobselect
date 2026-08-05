// 岗位筛选列表 JS：复合筛选 + 分页 + 联动统计 + 导出
let currentPage = 1;

function getFilters(){
  const f = {};
  const get = (id)=>document.getElementById(id).value;
  if(get('f_region')!=='all') f.region = get('f_region');
  if(get('f_caring')!=='all') f.is_caring = get('f_caring');
  if(get('f_edu')!=='0') f.edu_level = get('f_edu');
  if(get('f_salary')) f.salary_min = get('f_salary');
  if(get('f_industry')!=='all') f.industry = get('f_industry');
  if(get('f_shift')!=='all') f.shift = get('f_shift');
  if(get('f_label')!=='all') f.label = get('f_label');
  if(get('f_cert')!=='all') f.has_cert = get('f_cert');
  if(get('f_keyword').trim()) f.keyword = get('f_keyword').trim();
  return f;
}

function buildQuery(f){ return Object.keys(f).map(k=>`${k}=${encodeURIComponent(f[k])}`).join('&'); }

async function loadJobs(page){
  currentPage = page || 1;
  const f = getFilters();
  const q = buildQuery(f);
  const data = await fetchJSON(`/api/jobs?${q}&page=${currentPage}`);
  if(data.code!==0){ showToast('加载失败','error'); return; }
  const d = data.data;
  // 联动统计
  const c = d.stats.cards;
  document.getElementById('m_total').innerHTML = c.total + '<span class="unit">个</span>';
  document.getElementById('m_caring').innerHTML = c.caring + '<span class="unit">个</span>';
  document.getElementById('m_high').innerHTML = c.high_salary + '<span class="unit">个</span>';
  document.getElementById('m_food').innerHTML = c.food_shelter + '<span class="unit">个</span>';
  document.getElementById('result_count').textContent = `共匹配 ${d.total} 条`;
  // 渲染卡片
  const grid = document.getElementById('jobGrid');
  if(!d.list.length){ grid.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:40px;grid-column:1/-1">未匹配到岗位，请调整筛选条件</div>'; }
  else{
    grid.innerHTML = d.list.map(j=>renderCard(j)).join('');
  }
  // 分页
  document.getElementById('pagination').innerHTML = renderPagination(d.total, d.total_pages, d.page, 'loadJobs');
}

function renderCard(j){
  const labelsHtml = renderLabels(j.labels);
  const badges = [];
  if(j.is_caring) badges.push('<span class="caring-flag">爱心岗位</span>');
  if(j.has_cert_priority) badges.push('<span class="cert-flag">持证优先</span>');
  const salaryCls = j.max_salary>=8000 ? 'style="color:#ef4444"' : '';
  return `
    <div class="job-card" onclick="location.href='/jobs/${j.id}'">
      <div class="j-badges">${badges.join('')}</div>
      <div class="j-head">
        <div class="j-name">${escapeHtml(j.job_name)}</div>
        <div class="j-region">${j.region||'—'}</div>
      </div>
      <div class="j-company">${escapeHtml(j.company)}</div>
      <div class="j-salary" ${salaryCls}>${j.salary_text}<small> / 月</small></div>
      <div class="j-meta">
        <span>招聘 ${j.recruit_num} 人</span>
        <span>${j.education}</span>
        <span>${j.industry}</span>
        <span>${j.shift}</span>
      </div>
      <div class="j-labels">${labelsHtml}</div>
      <div class="j-foot">
        <span class="phone">📞 ${escapeHtml(j.phone||'—')}</span>
        <span>${escapeHtml(j.contact||'—')}</span>
      </div>
    </div>`;
}

function escapeHtml(s){ return (s||'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

function resetFilters(){
  ['f_region','f_caring','f_industry','f_shift','f_label','f_cert'].forEach(id=>document.getElementById(id).value='all');
  document.getElementById('f_edu').value='0';
  document.getElementById('f_salary').value='';
  document.getElementById('f_keyword').value='';
  loadJobs(1);
}

function exportExcel(){
  const f = getFilters(); const q = buildQuery(f);
  showToast('正在生成 Excel 报表...','');
  location.href = '/api/export_excel?'+q;
}

function exportContacts(){
  const f = getFilters(); const q = buildQuery(f);
  location.href = '/api/export_contacts?'+q;
}

// 回车查询
document.getElementById('f_keyword').addEventListener('keydown', e=>{ if(e.key==='Enter') loadJobs(1); });

document.addEventListener('DOMContentLoaded', ()=>loadJobs(1));
