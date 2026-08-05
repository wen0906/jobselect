// 可视化大屏 JS：指标卡片 + 柱状图 + 饼图 + 筛选联动刷新
let chartIndustry, chartEdu, chartSalary;

function initCharts(){
  chartIndustry = echarts.init(document.getElementById('chart_industry'));
  chartEdu = echarts.init(document.getElementById('chart_edu'));
  chartSalary = echarts.init(document.getElementById('chart_salary'));
  window.addEventListener('resize', ()=>{ chartIndustry.resize(); chartEdu.resize(); chartSalary.resize(); });
}

function getFilters(){
  const f = {};
  const r = document.getElementById('f_region').value; if(r && r!=='all') f.region = r;
  const i = document.getElementById('f_industry').value; if(i && i!=='all') f.industry = i;
  const e = document.getElementById('f_edu').value; if(e && e!=='0') f.edu_level = e;
  const s = document.getElementById('f_salary').value; if(s) f.salary_min = s;
  const sh = document.getElementById('f_shift').value; if(sh && sh!=='all') f.shift = sh;
  const l = document.getElementById('f_label').value; if(l && l!=='all') f.label = l;
  if(document.getElementById('f_caring').checked) f.is_caring = '1';
  if(document.getElementById('f_cert').checked) f.has_cert = '1';
  const k = document.getElementById('f_keyword').value.trim(); if(k) f.keyword = k;
  return f;
}

function buildQuery(f){
  return Object.keys(f).map(k=>`${k}=${encodeURIComponent(f[k])}`).join('&');
}

async function refresh(){
  const f = getFilters();
  const q = buildQuery(f);
  const data = await fetchJSON('/api/stats?'+q);
  if(data.code!==0){ showToast('数据加载失败','error'); return; }
  const d = data.data;
  // 指标卡片
  document.getElementById('m_total').innerHTML = d.cards.total + '<span class="unit">个</span>';
  document.getElementById('m_caring').innerHTML = d.cards.caring + '<span class="unit">个</span>';
  document.getElementById('m_high').innerHTML = d.cards.high_salary + '<span class="unit">个</span>';
  document.getElementById('m_food').innerHTML = d.cards.food_shelter + '<span class="unit">个</span>';
  // 图表
  chartIndustry.setOption(d.industry_bar_option, true);
  chartEdu.setOption(d.edu_pie_option, true);
  chartSalary.setOption(d.salary_pie_option, true);
}

function applyFilters(){ refresh(); showToast('筛选条件已应用，图表已联动刷新','success'); }
function resetFilters(){
  ['f_region','f_industry','f_shift','f_label'].forEach(id=>document.getElementById(id).value='all');
  document.getElementById('f_edu').value='0';
  document.getElementById('f_salary').value='';
  document.getElementById('f_keyword').value='';
  document.getElementById('f_caring').checked=false;
  document.getElementById('f_cert').checked=false;
  refresh();
  showToast('已重置筛选条件','');
}

document.addEventListener('DOMContentLoaded', ()=>{
  initCharts();
  refresh();
});
