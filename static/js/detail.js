// 岗位详情页 JS：打印 + 生成独立详情页 + 导出
async function genDetailPage(){
  const jobId = window.__JOB_ID__;
  showToast('正在生成独立详情页...','');
  const data = await fetchJSON(`/api/detail_page/${jobId}`);
  if(data.code!==0){ showToast('生成失败','error'); return; }
  const url = data.data.download_url;
  document.getElementById('detailUrlBox').innerHTML = `访问地址：<a href="${url}" target="_blank">${location.origin}${url}</a>`;
  document.getElementById('detailOpenBtn').href = url;
  document.getElementById('detailModal').classList.add('show');
  showToast('详情页已生成，可转发分享','success');
}

function exportOne(){
  showToast('正在导出该岗位到 Excel 报表...','');
  location.href = `/api/export_excel?keyword=${encodeURIComponent(document.querySelector('.detail-head h1').textContent)}`;
}
