// ============================================================================
// 📌 ملف الكود البرمجي (commissions.js): كود شاشة العمولات والخصومات والتقفيلات للسيلز والمصورين
// ============================================================================

let cHotels=[],cTeam={},commissionData={sales:null,photographer:null},currentClosure=null,archiveRows=[];
async function initCommissions(){initLogicTabs();[cHotels,cTeam]=await Promise.all([apiSafe('/api/hotels',[],'تحميل الفنادق'),apiSafe('/api/team/options',{sales:[],photographers:[],all:[]},'تحميل الفريق')]);$('cHotel').innerHTML='<option value="">الكل</option>'+cHotels.map(h=>`<option value="${h.id}">${esc(h.hotel_name)}</option>`).join('');$('csEmployee').innerHTML='<option value="">جميع السيلز</option>'+(cTeam.sales||[]).map(x=>`<option value="${esc(x.nickname)}">${esc(x.nickname)}</option>`).join('');$('cpEmployee').innerHTML='<option value="">جميع المصورين</option>'+(cTeam.photographers||[]).map(x=>`<option value="${esc(x.nickname)}">${esc(x.nickname)}</option>`).join('');const start=firstDayMonth(),end=todayISO();['csStart','cpStart','clStart'].forEach(x=>$(x).value=start);['csEnd','cpEnd','clEnd'].forEach(x=>$(x).value=end);$('bonusMonth').value=monthISO();$('csEmployee').addEventListener('change',()=>loadCommissionRole('sales'));$('cpEmployee').addEventListener('change',()=>loadCommissionRole('photographer'));await Promise.allSettled([loadCommissionRole('sales'),loadCommissionRole('photographer'),loadBonus(),loadClosureArchive()])}
async function refreshCommissions(){await Promise.allSettled([loadCommissionRole('sales'),loadCommissionRole('photographer'),loadBonus(),loadClosureArchive()]);toast('تم تحديث بيانات العمولات')}
async function loadCommissionRole(role){const start=$(role==='sales'?'csStart':'cpStart').value,end=$(role==='sales'?'csEnd':'cpEnd').value,h=$('cHotel').value,emp=$(role==='sales'?'csEmployee':'cpEmployee').value;const q=new URLSearchParams({start,end,role});if(h)q.set('hotel_id',h);if(emp)q.set('employee_name',emp);const x=await api('/api/commissions?'+q.toString());commissionData[role]=x;renderCommission(role,x)}
function renderCommission(role,x){
    const sId=role==='sales'?'salesSummary':'photoSummary',dId=role==='sales'?'salesDetails':'photoDetails';
    const rate=num(x.exchange_rate)||50;
    
    $(sId).innerHTML=(x.summary||[]).map(r=>`<tr><td><b>${esc(r.employee)}</b></td><td>${money(r.commission_usd)}</td><td class="text-green"><b>${money(r.gross_egp)}</b></td><td class="text-amber">${money(r.deductions_egp)}</td><td><b>${money(r.net_egp)}</b></td><td><button class="mini-btn blue" onclick="showEmployeeCommission('${role}','${esc(r.employee)}')">🔍 عرض</button> <button class="mini-btn green" onclick="printEmployeeCommission('${role}','${esc(r.employee)}')">🖨️ تقرير</button></td></tr>`).join('')||'<tr><td colspan="6">لا توجد بيانات</td></tr>';
    
    $(dId).innerHTML=(x.rows||[]).map(r=>`<tr><td>${esc(r.date)}</td><td>${esc(r.hotel)}</td><td>${esc(r.room)}</td><td>${esc(r.employee)}</td><td>${money(r.gross)}</td><td>${money(r.cost)}</td><td>${money(r.net_share)}</td><td>${money(r.rate)}%</td><td><b>${money(r.commission_usd)}</b></td><td class="text-green"><b>${money(num(r.commission_usd)*rate)}</b></td></tr>`).join('')||'<tr><td colspan="10">لا توجد تفاصيل</td></tr>'
}
function showEmployeeCommission(role,name){
    const x=commissionData[role]||{rows:[],deductions:[],exchange_rate:50};
    const rate=num(x.exchange_rate)||50;
    const rows=x.rows.filter(r=>r.employee===name),deds=(x.deductions||[]).filter(d=>d.employee_name===name);
    showModal(`<div class="modal-title"><h2>تفاصيل ${esc(name)}</h2></div><h3>الأوردرات</h3><div class="table-wrap maxh"><table class="modern-table"><thead><tr><th>التاريخ</th><th>الفندق</th><th>الغرفة</th><th>الصافي</th><th>النسبة</th><th>العمولة $</th><th>العمولة LE</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${r.date}</td><td>${esc(r.hotel)}</td><td>${esc(r.room)}</td><td>${money(r.net_share)}</td><td>${money(r.rate)}\%</td><td>${money(r.commission_usd)}</td><td class="text-green"><b>${money(num(r.commission_usd)*rate)}</b></td></tr>`).join('')}</tbody></table></div><h3>الخصومات والسلف</h3><div class="table-wrap"><table class="modern-table"><thead><tr><th>التاريخ</th><th>النوع</th><th>القيمة LE</th><th>السبب</th><th>إجراءات</th></tr></thead><tbody>${deds.map(d=>`<tr><td>${d.deduction_date}</td><td>${esc(d.type)}</td><td class="text-amber"><b>${money(d.amount_egp)}</b></td><td>${esc(d.reason)}</td><td><button class="mini-btn" onclick="printDeduction(${d.id})">🖨️</button><button class="mini-btn amber" onclick="editDeduction(${d.id})">✏️</button><button class="mini-btn red" onclick="deleteDeduction(${d.id})">🗑️</button></td></tr>`).join('')||'<tr><td colspan="5">لا توجد خصومات</td></tr>'}</tbody></table></div>`,'modal-xl')
}
async function openCommissionSettings(){const s=await api('/api/commissions/settings');showModal(`<div class="modal-title"><h2>⚙️ إعدادات العمولات والبونص</h2></div><form id="commissionSettingsForm"><div class="form-grid three"><div class="field"><label>سعر الصرف</label><input class="input" id="setRate" value="${s.exchange_rate}"></div><div class="field"><label>تارجت Sales $</label><input class="input" id="setST" value="${s.sales_bonus_target}"></div><div class="field"><label>نسبة بونص Sales %</label><input class="input" id="setSP" value="${s.sales_bonus_pct}"></div><div class="field"><label>تارجت Photographer $</label><input class="input" id="setPT" value="${s.photo_bonus_target}"></div><div class="field"><label>نسبة بونص Photographer %</label><input class="input" id="setPP" value="${s.photo_bonus_pct}"></div><div class="field"><label>تارجت Manager $</label><input class="input" id="setMT" value="${s.manager_bonus_target}"></div><div class="field"><label>نسبة Manager %</label><input class="input" id="setMP" value="${s.manager_bonus_pct}"></div><div class="field"><label>تارجت بونص الفندق $</label><input class="input" id="setHT" value="${s.hotel_bonus_target}"></div><div class="field"><label>نسبة بونص الفندق %</label><input class="input" id="setHP" value="${s.hotel_bonus_pct}"></div></div><div class="modal-actions"><button class="btn green">حفظ التعديلات (Enter)</button></div></form>`,'modal-lg');$('commissionSettingsForm').addEventListener('submit',async e=>{e.preventDefault();await apiJSON('/api/commissions/settings','PUT',{exchange_rate:$('setRate').value,sales_bonus_target:$('setST').value,sales_bonus_pct:$('setSP').value,photo_bonus_target:$('setPT').value,photo_bonus_pct:$('setPP').value,manager_bonus_target:$('setMT').value,manager_bonus_pct:$('setMP').value,hotel_bonus_target:$('setHT').value,hotel_bonus_pct:$('setHP').value});toast('تم حفظ الإعدادات');closeModal();refreshCommissions()})}
async function openDeductionForm(row=null){const all=cTeam.all||[];showModal(`<div class="modal-title"><h2>🏷️ تسجيل خصم / سلفة</h2></div><form id="dedForm"><input type="hidden" id="dedId" value="${row?.id||''}"><div class="form-grid two"><div class="field"><label>الموظف</label><select class="input" id="dedEmp">${all.map(x=>`<option>${esc(x.nickname)}</option>`).join('')}</select></div><div class="field"><label>التاريخ</label><input class="input" type="date" id="dedDate" value="${row?.deduction_date||todayISO()}"></div><div class="field"><label>القيمة LE</label><input class="input" type="number" step=".01" id="dedAmount" value="${row?.amount_egp||0}"></div><div class="field"><label>النوع</label><select class="input" id="dedType"><option>خصم / جزاء إداري</option><option>سلفة</option><option>عجز</option><option>أخرى</option></select></div><div class="field full-span"><label>السبب</label><textarea class="input textarea" id="dedReason">${esc(row?.reason||'')}</textarea></div></div><div class="modal-actions"><button class="btn green">حفظ (Enter)</button></div></form>`,'modal-lg');if(row){$('dedEmp').value=row.employee_name;$('dedType').value=row.type}$('dedForm').addEventListener('submit',async e=>{e.preventDefault();const id=$('dedId').value,b={employee_name:$('dedEmp').value,deduction_date:$('dedDate').value,amount_egp:num($('dedAmount').value),type:$('dedType').value,reason:$('dedReason').value};await apiJSON(id?'/api/deductions/'+id:'/api/deductions',id?'PUT':'POST',b);toast('تم حفظ الخصم / السلفة');closeModal();refreshCommissions()})}
async function editDeduction(id){const rows=await api('/api/deductions');const r=rows.find(x=>x.id===id);if(r)openDeductionForm(r)}async function deleteDeduction(id){if(!confirmAction('حذف هذا الخصم / السلفة؟'))return;await api('/api/deductions/'+id,{method:'DELETE'});closeModal();refreshCommissions()}async function printDeduction(id){const rows=await api('/api/deductions');const r=rows.find(x=>x.id===id);if(r)printHTML('إيصال خصم / سلفة',`<table><tr><th>الموظف</th><td>${esc(r.employee_name)}</td></tr><tr><th>التاريخ</th><td>${r.deduction_date}</td></tr><tr><th>النوع</th><td>${esc(r.type)}</td></tr><tr><th>القيمة</th><td>${money(r.amount_egp)} LE</td></tr><tr><th>السبب</th><td>${esc(r.reason)}</td></tr></table><div class="sign"><span>توقيع الموظف</span><span>توقيع الإدارة</span></div>`)}
async function loadBonus(){const q=`/api/commissions/bonus?month=${$('bonusMonth').value}${$('cHotel').value?'&hotel_id='+$('cHotel').value:''}`;const rows=await api(q);$('bonusBody').innerHTML=rows.map(r=>`<tr><td>${esc(r.role)}</td><td><b>${esc(r.employee)}</b></td><td>${money(r.achieved)}</td><td>${money(r.target)}</td><td>${money(r.pct)}%</td><td>${r.hit?'<span class="badge green">محققة 🎯</span>':'<span class="badge red">لم يتم الوصول ❌</span>'}</td><td><b class="text-green">${money(r.bonus_usd)}</b></td></tr>`).join('')}
async function generateClosure(){const role=$('clRole').value,start=$('clStart').value,end=$('clEnd').value,h=$('cHotel').value;currentClosure=await api(`/api/commissions?start=${start}&end=${end}&role=${role}${h?'&hotel_id='+h:''}`);$('closureCurrent').innerHTML=`<div class="table-wrap maxh"><table class="modern-table"><thead><tr><th>الموظف</th><th>عمولة $</th><th>إجمالي LE</th><th>خصومات LE</th><th>صافي LE</th></tr></thead><tbody>${(currentClosure.summary||[]).map(r=>`<tr><td>${esc(r.employee)}</td><td>${money(r.commission_usd)}</td><td>${money(r.gross_egp)}</td><td class="text-amber">${money(r.deductions_egp)}</td><td class="text-green"><b>${money(r.net_egp)}</b></td></tr>`).join('')}</tbody></table></div>`}
async function archiveClosure(){if(!currentClosure)await generateClosure();await apiJSON('/api/closures/archive','POST',{start:$('clStart').value,end:$('clEnd').value,role:$('clRole').value,hotel_id:$('cHotel').value||'الكل'});toast('تم حفظ وأرشفة التقفيلة');loadClosureArchive()}
async function loadClosureArchive(){archiveRows=await api('/api/closures/archive');$('closureArchive').innerHTML=archiveRows.map(r=>`<tr><td>${r.id}</td><td>${esc(r.hotel_id)}</td><td>${esc(r.role_type)}</td><td>${esc(r.employee_name)}</td><td>${esc(r.month_str)}</td><td>${esc(r.period_text)}</td><td>${money(r.total_usd)}</td><td>${money(r.total_egp)}</td><td>${esc(r.closure_date)}</td><td><button class="mini-btn blue" onclick="showClosure(${r.id})">🔍 عرض</button></td></tr>`).join('')||'<tr><td colspan="10">لا يوجد أرشيف</td></tr>'}
async function showClosure(id){const rows=await api('/api/closures/'+id+'/details');showModal(`<div class="modal-title"><h2>📂 تفاصيل التقفيلة #${id}</h2></div><div class="table-wrap maxh"><table class="modern-table"><thead><tr><th>التاريخ</th><th>الموظف</th><th>البند</th><th>$</th><th>LE</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${esc(r.record_date)}</td><td>${esc(r.employee_name)}</td><td>${esc(r.item_name)}</td><td>${money(r.amount_usd)}</td><td class="text-green"><b>${money(r.amount_egp)}</b></td></tr>`).join('')}</tbody></table></div>`,'modal-xl')}
function commissionReportTitle(role){return role==='sales'?'تقرير عمولات المبيعات (Sales)':'تقرير عمولات المصورين'}
function commissionReportDate(){const d=new Date(),p=n=>String(n).padStart(2,'0');return `${p(d.getHours())}:${p(d.getMinutes())} ${p(d.getDate())}-${p(d.getMonth()+1)}-${d.getFullYear()}`}
function buildCommissionReportHTML(role,x,employeeName=''){
  x=x||{rows:[],summary:[],deductions:[],exchange_rate:50};
  const rate=num(x.exchange_rate)||50;
  const target=(employeeName||'').trim().toLowerCase();
  const rows=(x.rows||[]).filter(r=>!target||String(r.employee||'').trim().toLowerCase()===target);
  const deds=(x.deductions||[]).filter(d=>!target||String(d.employee_name||'').trim().toLowerCase()===target);
  const sums=(x.summary||[]).filter(r=>!target||String(r.employee||'').trim().toLowerCase()===target);
  const title=commissionReportTitle(role);
  const netEGP=sums.reduce((a,r)=>a+num(r.net_egp),0);
  const rowsHtml=rows.map(r=>`<tr><td>${esc(r.date||'')}</td><td>${esc(r.hotel||'-')}</td><td>${esc(r.employee||'')}</td><td>${money(r.net_share)}</td><td>$ ${money(r.commission_usd)}</td><td>${money(num(r.commission_usd)*rate)} ج.م</td></tr>`).join('');
  const dedHtml=deds.map(d=>`<tr class="deduction-row"><td>${esc(d.deduction_date||'')}</td><td>-</td><td>${esc(d.employee_name||employeeName||'')}</td><td>${esc(d.type||d.reason||'خصم / سلفة مالية')}</td><td>-</td><td>- ${money(d.amount_egp)} ج.م</td></tr>`).join('');
  const empty=(!rowsHtml&&!dedHtml)?'<tr><td colspan="6">لا توجد بيانات للفترة المحددة</td></tr>':'';
  return `<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><title>${esc(title)}</title><style>
    body{font-family:'Cairo',Tahoma,sans-serif;background:#f8fafc;color:#1e293b;padding:20px;direction:rtl}
    h1{text-align:center;color:#1d4ed8;margin-bottom:5px}
    .date-info{text-align:center;color:#64748b;margin-bottom:25px;font-size:14px}
    .employee-info{text-align:center;color:#334155;margin:-14px 0 20px;font-size:14px;font-weight:bold}
    table{width:100%;border-collapse:collapse;background:white;border-radius:8px;overflow:hidden;box-shadow:0 4px 6px rgba(0,0,0,.05)}
    th{background:#2563eb;color:white;padding:12px;font-size:14px;text-align:center}
    td{padding:10px;border-bottom:1px solid #e2e8f0;font-size:13px;text-align:center}
    tr:nth-child(even){background:#f1f5f9}
    tr.deduction-row td{color:#dc2626!important;font-weight:bold;background:#fef2f2!important}
    .footer-bar{margin-top:25px;background:#1e293b;color:#38bdf8;padding:15px;border-radius:8px;font-size:14px;font-weight:bold;text-align:center}
    .signatures{display:flex;justify-content:space-between;margin-top:50px;padding:0 40px;font-weight:bold}
    .sig-box{text-align:center;width:200px;border-top:2px solid #1e293b;padding-top:10px}
    .print-btn{display:block;width:220px;margin:30px auto 10px;padding:12px;background:#16a34a;color:white;border:none;border-radius:6px;font-size:16px;cursor:pointer;font-weight:bold;text-align:center}
    .print-btn:hover{background:#15803d}
    @media print{.print-btn{display:none}body{background:white;padding:0}}
  </style></head><body>
    <h1>${esc(title)}</h1>
    <div class="date-info">تاريخ الإصدار: ${commissionReportDate()}</div>
    ${employeeName?`<div class="employee-info">الموظف: ${esc(employeeName)}</div>`:''}
    <table><thead><tr><th>التاريخ</th><th>الفندق</th><th>الاسم</th><th>صافي الأوردر ($)</th><th>العمولة ($)</th><th>العمولة بالمصري</th></tr></thead><tbody>${rowsHtml}${dedHtml}${empty}</tbody></table>
    <div class="footer-bar">💵 الصافي النهائي: ${money(netEGP)} ج.م</div>
    <div class="signatures"><div class="sig-box">توقيع المدير العام</div><div class="sig-box">توقيع الموظف المستلم</div></div>
    <button class="print-btn" onclick="window.print()">🖨️ طباعة / حفظ PDF</button>
  </body></html>`;
}
function openCommissionReport(role,x,employeeName=''){
  const htmlDoc = buildCommissionReportHTML(role,x,employeeName).replace('onclick="window.print()"', 'onclick="parent.printHtmlViaInternalIframe()"');
  openBuiltInReportViewer(htmlDoc, `تقرير عمولات ${role==='sales'?'السيلز':'المصورين'} ${employeeName?('• '+employeeName):''}`, false);
}
async function printEmployeeCommission(role,name){
  const start=$(role==='sales'?'csStart':'cpStart').value,end=$(role==='sales'?'csEnd':'cpEnd').value,h=$('cHotel').value;
  const q=new URLSearchParams({start,end,role,employee_name:name});if(h)q.set('hotel_id',h);
  const x=await api('/api/commissions?'+q.toString());openCommissionReport(role,x,name);
}
function printCommission(role){
  const employee=$(role==='sales'?'csEmployee':'cpEmployee').value;
  const x=commissionData[role];if(!x)return toast('اعرض العمولات أولاً','bad');
  openCommissionReport(role,x,employee);
}
function printClosure(){if(!currentClosure)return toast('اعرض تقرير التقفيلة أولاً','bad');printHTML('تقرير التقفيلة',`<table><tr><th>الموظف</th><th>عمولة $</th><th>إجمالي LE</th><th>خصومات</th><th>صافي LE</th></tr>${currentClosure.summary.map(r=>`<tr><td>${esc(r.employee)}</td><td>${money(r.commission_usd)}</td><td>${money(r.gross_egp)}</td><td>${money(r.deductions_egp)}</td><td>${money(r.net_egp)}</td></tr>`).join('')}</table><div class="sign"><span>توقيع المحاسب</span><span>توقيع الإدارة</span></div>`)}
initCommissions();  

// V80: عزل شاشة العمولات للمصور والسيلز (يرى عمولاته وبونصه الشخصي فقط)
function enforcePersonalScopeCommissions(){
  if(!window.PERSONAL_SCOPE)return;
  const myNick=(window.CURRENT_USER?.nickname||window.CURRENT_USER?.full_name||'').trim();
  const roles=(window.USER_ROLES||[]).map(r=>String(r).toLowerCase());
  const isSales=roles.includes('sales'), isPhoto=roles.includes('photographer');

  // إخفاء أزرار إعدادات العمولات وتسجيل الخصم وتبويب التقفيلات الشاملة
  $$('.heading-actions button').forEach(btn=>{
    if(/الإعدادات|خصم/.test(btn.textContent||''))btn.style.display='none';
  });
  const clTab=document.querySelector('[data-tab-target="cClosures"]');
  if(clTab)clTab.style.display='none';

  if(isSales && !isPhoto){
    const pTab=document.querySelector('[data-tab-target="cPhotos"]');
    if(pTab)pTab.style.display='none';
    if($('csEmployee') && myNick){
      $('csEmployee').innerHTML=`<option value="${esc(myNick)}">${esc(myNick)} (عمولاتي فقط 🔒)</option>`;
      $('csEmployee').value=myNick;
      $('csEmployee').disabled=true;
    }
  }
  if(isPhoto && !isSales){
    const sTab=document.querySelector('[data-tab-target="cSales"]');
    const pTab=document.querySelector('[data-tab-target="cPhotos"]');
    if(sTab)sTab.style.display='none';
    if(pTab)pTab.click();
    if($('cpEmployee') && myNick){
      $('cpEmployee').innerHTML=`<option value="${esc(myNick)}">${esc(myNick)} (عمولاتي فقط 🔒)</option>`;
      $('cpEmployee').value=myNick;
      $('cpEmployee').disabled=true;
    }
  }
}
setTimeout(enforcePersonalScopeCommissions, 150);

function exportCommissionCSV(role) {
    const x = commissionData[role] || { rows: [], summary: [] };
    const rows = (x.rows || []).map((r, i) => [
        i + 1,
        r.date || '',
        r.hotel || '-',
        r.room || '-',
        r.employee || '',
        money(r.gross || 0),
        money(r.cost || 0),
        money(r.net_share || 0),
        (r.rate || 0) + '%',
        money(r.commission_usd || 0)
    ]);
    downloadCSV(
        `Commissions_${role}_${todayISO()}.csv`,
        ['#', 'التاريخ', 'الفندق', 'الغرفة', 'الموظف', 'الإجمالي ($)', 'التكلفة ($)', 'الصافي ($)', 'النسبة', 'العمولة ($)'],
        rows
    );
}
window.exportCommissionCSV = exportCommissionCSV;
