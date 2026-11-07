// ============================================================================
// 📌 ملف الكود البرمجي (salaries.js): كود شاشة حساب وصرف المرتبات الشهرية
// ============================================================================

let salHotels=[],salaryData={rows:[],summary:{}},salaryArchive=[],teamRows=[],selectedSalaryNames=new Set();
async function initSalaries(){initLogicTabs();[salHotels,teamRows]=await Promise.all([apiSafe('/api/hotels',[],'تحميل الفنادق'),apiSafe('/api/salaries/employees',[],'تحميل الموظفين')]);$('salHotel').innerHTML='<option value="">جميع الفنادق</option>'+salHotels.map(h=>`<option value="${h.id}">${esc(h.hotel_name)}</option>`).join('');$('salEmployee').innerHTML='<option value="">جميع الموظفين</option>'+[...teamRows].filter(r=>r.nickname).sort((a,b)=>String(a.nickname).localeCompare(String(b.nickname),'ar')).map(r=>`<option value="${esc(r.nickname)}">${esc(r.nickname)}${r.role?' - '+esc(r.role):''}</option>`).join('');$('salMonth').value=monthISO();['salMonth','salPeriod','salFrom','salTo','salHotel','salEmployee'].forEach(id=>$(id).addEventListener('change',loadSalaries));$('salPeriod').addEventListener('change',toggleCustom);toggleCustom();await Promise.allSettled([loadSalaries(),loadSalaryArchive()])}
function toggleCustom(){$$('.custom-sal').forEach(x=>x.style.display=$('salPeriod').value==='custom'?'block':'none')}
function salaryQuery(){const p=new URLSearchParams({month:$('salMonth').value,period:$('salPeriod').value});if($('salPeriod').value==='custom'){p.set('day_from',$('salFrom').value);p.set('day_to',$('salTo').value)}if($('salHotel').value)p.set('hotel_id',$('salHotel').value);if($('salEmployee').value)p.set('employee_name',$('salEmployee').value);return p}
async function loadSalaries(){try{salaryData=await api('/api/salaries?'+salaryQuery());await cleanupSeededFakeBaseSalaries();renderSalaries()}catch(e){salaryData={rows:[],summary:{}};renderSalaries();$('salaryBody').innerHTML=`<tr><td colspan="13" class="text-red">تعذر تحميل المرتبات: ${esc(e.message)}</td></tr>`;toast(e.message,'bad')}}
function renderSalaries(){const rows=salaryData.rows||[],s=salaryData.summary||{};$('salGrandNet').textContent=money(s.grand_net_egp)+' LE';$('salGrandSales').textContent=money(s.grand_sales_usd)+' $';$('salRate').textContent=money(s.exchange_rate);$('salPeriodText').textContent=salaryData.period_text||'-';$('salaryBody').innerHTML=rows.map(r=>`<tr class="select-row"><td><input type="checkbox" ${selectedSalaryNames.has(r.nickname)?'checked':''} onchange="toggleSalary('${esc(r.nickname)}',this.checked)"></td><td><b>${esc(r.nickname)}</b><br><small>${esc(r.full_name)}</small></td><td>${esc(r.role)}</td><td>${esc(r.hotel_name||'-')}</td><td>${money(r.period_base_salary)}</td><td>${money(r.net_sales)}</td><td>${money(r.commission_usd)}</td><td>${money(r.personal_bonus_egp)}</td><td>${money(r.hotel_bonus_egp)}</td><td>${money(r.deductions_egp)}</td><td><b>${money(r.net_egp)}</b></td><td><span class="payroll-status">${esc(r.status)}</span></td><td><button class="mini-btn purple" onclick="salaryActions('${esc(r.nickname)}')">⋮</button></td></tr>`).join('')||'<tr><td colspan="13">لا توجد بيانات رواتب</td></tr>'}
function toggleSalary(n,v){v?selectedSalaryNames.add(n):selectedSalaryNames.delete(n)}function selectedRows(){return (salaryData.rows||[]).filter(r=>selectedSalaryNames.has(r.nickname))}
async function paySelected(){const rows=selectedRows();if(!rows.length)return toast('حدد موظفاً واحداً على الأقل','bad');await apiJSON('/api/salaries/pay','POST',{employees:rows.map(r=>r.nickname),month:$('salMonth').value,period:$('salPeriod').value,day_from:$('salFrom').value,day_to:$('salTo').value,hotel_id:$('salHotel').value});toast('تم صرف المحدد');selectedSalaryNames.clear();loadSalaries();loadSalaryArchive()}
async function payAll(){const rows=(salaryData.rows||[]).filter(r=>!r.paid);if(!rows.length)return toast('جميع الموظفين تم صرفهم بالفعل','bad');const warn=rows.filter(r=>String(r.status||'').includes('ناقصة')||String(r.status||'').includes('مديونية')).map(r=>r.nickname);const msg=warn.length?`سيتم صرف ${rows.length} موظف.\n⚠️ يوجد بيانات ناقصة أو مديونية لدى: ${warn.join('، ')}\nهل تريد المتابعة؟`:`سيتم صرف ${rows.length} موظف وإرسالهم للأرشيف. هل تريد المتابعة؟`;if(!confirmAction(msg))return;await apiJSON('/api/salaries/pay','POST',{all:true,month:$('salMonth').value,period:$('salPeriod').value,day_from:$('salFrom').value,day_to:$('salTo').value,hotel_id:$('salHotel').value,employee_name:$('salEmployee').value});toast('تم تنفيذ صرف الكل');loadSalaries();loadSalaryArchive()}
async function undoSelectedPayment(){const rows=selectedRows();if(rows.length!==1)return toast('حدد موظفاً واحداً لإلغاء صرفه','bad');await apiJSON('/api/salaries/undo','POST',{employee_name:rows[0].nickname,month:$('salMonth').value,period:$('salPeriod').value,day_from:$('salFrom').value,day_to:$('salTo').value,hotel_id:$('salHotel').value});toast('تم إلغاء عملية الصرف');loadSalaries();loadSalaryArchive()}
function salaryActions(name){const r=(salaryData.rows||[]).find(x=>x.nickname===name);showModal(`<div class="modal-title"><h2>${esc(name)}</h2><p>${esc(r?.role||'')}</p></div><div class="action-grid"><button class="btn amber" onclick="openEmployeeDeductions('${esc(name)}')">✂️ إدارة وتقسيط الخصومات والسلف</button><button class="btn purple" onclick="openEmployeeLedger('${esc(name)}')">📁 عرض كشف حساب الموظف</button><button class="btn green" onclick="closeModal();selectedSalaryNames=new Set(['${esc(name)}']);paySelected()">💳 تأكيد صرف المرتب</button><button class="btn" onclick="printPayslip('${esc(name)}')">🖨️ طباعة مفردات المرتب</button></div>`,'modal-lg')}
async function openEmployeeDeductions(name){const rows=await api(`/api/deductions?employee=${encodeURIComponent(name)}`);showModal(`<div class="modal-title"><h2>✂️ الخصومات والسلف - ${esc(name)}</h2></div><div class="table-wrap"><table><thead><tr><th>#</th><th>التاريخ</th><th>النوع</th><th>القيمة</th><th>السبب</th><th>تقسيط / ترحيل</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${r.id}</td><td>${r.deduction_date}</td><td>${esc(r.type)}</td><td>${money(r.amount_egp)}</td><td>${esc(r.reason)}</td><td><button class="mini-btn amber" onclick="partialDeduction(${r.id},${num(r.amount_egp)})">✂️</button></td></tr>`).join('')||'<tr><td colspan="6">لا توجد خصومات</td></tr>'}</tbody></table></div>`,'modal-xl')}
function partialDeduction(id,total){showModal(`<div class="modal-title"><h2>✂️ تخصيم جزء أو ترحيل السلفة أوتوماتيكياً</h2><p>القيمة الأصلية: ${money(total)} LE</p></div><form id="partialForm"><div class="field"><label>القيمة التي تخصم الآن (0 = ترحيل كامل)</label><input class="input" type="number" min="0" max="${total}" id="cutAmount" value="${total}"></div><div class="modal-actions"><button class="btn amber">تأكيد الخصم / الترحيل الأوتوماتيكي</button></div></form>`,'modal-lg');$('partialForm').addEventListener('submit',async e=>{e.preventDefault();const r=await apiJSON(`/api/deductions/${id}/partial`,'POST',{cut_amount:num($('cutAmount').value),month:$('salMonth').value,period:$('salPeriod').value});toast(`تم: خصم ${money(r.cut)} وترحيل ${money(r.deferred)}`);closeModal();loadSalaries()})}
async function openEmployeeLedger(name){const [deds,arch]=await Promise.all([api(`/api/deductions?employee=${encodeURIComponent(name)}`),api('/api/salaries/archive')]);const r=(salaryData.rows||[]).find(x=>x.nickname===name);showModal(`<div class="modal-title"><h2>📁 كشف حساب الموظف - ${esc(name)}</h2></div><div class="detail-list"><div class="detail-row"><small>حجم التشغيل الحالي</small><b>${money(r?.net_sales)} $</b></div><div class="detail-row"><small>عمولة الفترة</small><b>${money(r?.commission_usd)} $</b></div><div class="detail-row"><small>بونص الفترة</small><b>${money(r?.bonus_egp)} LE</b></div><div class="detail-row"><small>خصومات الفترة</small><b>${money(r?.deductions_egp)} LE</b></div></div><h3>الخصومات والسلف</h3><div class="table-wrap"><table><tr><th>التاريخ</th><th>النوع</th><th>المبلغ</th><th>السبب</th></tr>${deds.map(x=>`<tr><td>${x.deduction_date}</td><td>${esc(x.type)}</td><td>${money(x.amount_egp)}</td><td>${esc(x.reason)}</td></tr>`).join('')}</table></div><h3>سجل الصرف</h3><div class="table-wrap"><table><tr><th>الشهر</th><th>الفترة</th><th>الصافي</th><th>التاريخ</th></tr>${arch.filter(x=>x.employee_name===name).map(x=>`<tr><td>${x.month_str}</td><td>${esc(x.period_text)}</td><td>${money(x.net_amount_egp)}</td><td>${esc(x.paid_date)}</td></tr>`).join('')}</table></div>`,'modal-xl')}
function printPayslip(name){const r=(salaryData.rows||[]).find(x=>x.nickname===name);if(!r)return;const monthVal=$('salMonth')?.value||'';const monthText=monthVal?monthVal.split('-')[1]||monthVal:monthVal;const periodText=salaryData.period_text||'-';const employeeName=r.full_name?`${esc(r.full_name)}${r.nickname&&r.nickname!==r.full_name?` (${esc(r.nickname)})`:''}`:esc(r.nickname||name);const extraBonus=num(r.bonus_egp);const html=`<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><title>مفردات مرتب - ${esc(r.nickname||name)}</title><style>body{font-family:'Segoe UI',Tahoma,sans-serif;background:#fff;color:#1e293b;padding:30px;direction:rtl} .slip-box{width:650px;max-width:100%;margin:0 auto;border:2px solid #2563eb;border-radius:12px;padding:30px;box-shadow:0 4px 10px rgba(0,0,0,.10)} h2{text-align:center;color:#1d4ed8;margin-bottom:5px} .sub-title{text-align:center;color:#64748b;margin-bottom:25px;font-size:13px} .info-grid{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:12px;background:#f8fafc;padding:12px;border-radius:8px;font-weight:bold;font-size:14px} .info-grid span{flex:1;min-width:220px} table{width:100%;border-collapse:collapse;margin-bottom:20px} th,td{padding:10px;border:1px solid #e2e8f0;font-size:14px;text-align:center} th{background:#2563eb;color:#fff} .net-box{text-align:center;font-size:20px;color:#16a34a;margin:20px 0;font-weight:bold;background:#f0fdf4;padding:12px;border-radius:8px;border:1px solid #bbf7d0} .signatures{display:flex;justify-content:space-between;gap:20px;margin-top:50px;font-weight:bold} .sig{text-align:center;flex:1;border-top:2px solid #1e293b;padding-top:10px} .print-btn{display:block;width:220px;margin:30px auto 0;padding:10px;background:#16a34a;color:#fff;border:none;border-radius:6px;font-size:16px;cursor:pointer;font-weight:bold;text-align:center} @media print{body{padding:0} .slip-box{width:auto;box-shadow:none;margin:0;border-width:1.5px} .print-btn{display:none}}</style></head><body><div class="slip-box"><h2>إيصال مفردات المرتب</h2><div class="sub-title">عن شهر: ${esc(monthText)} | فترة الدفعة: ${esc(periodText)}</div><div class="info-grid"><span>اسم الموظف: ${employeeName}</span><span>الوظيفة: ${esc(r.role||'-')}</span></div><div class="info-grid"><span>رقم البطاقة: ${esc(r.national_id||'-')}</span><span>رقم الفيزا / الحساب: ${esc(r.visa_card_number||'-')}</span></div><table><thead><tr><th>البيان</th><th>القيمة المحسوبة</th></tr></thead><tbody><tr><td>المرتب الأساسي الثابت</td><td style="color:#2563eb;">${money(r.period_base_salary)} ج.م</td></tr><tr><td>إجمالي المبيعات المحققة</td><td>${money(r.net_sales)} $</td></tr><tr><td>إجمالي العمولات المستحقة</td><td>${money(r.commission_usd)} $</td></tr><tr><td>المكافآت / الزيادات الإضافية</td><td style="color:#16a34a;">+${money(extraBonus)} ج.م</td></tr><tr><td>الخصومات والسلف المعلقة</td><td style="color:#dc2626;">${money(r.deductions_egp)} ج.م</td></tr></tbody></table><div class="net-box">الصافي المستحق للصرف: ${money(r.net_egp)} ج.م</div><div class="signatures"><div class="sig">توقيع المدير العام</div><div class="sig">توقيع الموظف المستلم</div></div></div><button class="print-btn" onclick="window.print()">🖨️ طباعة الإيصال</button></body></html>`;openBuiltInReportViewer(html.replace('onclick="window.print()"','onclick="parent.printHtmlViaInternalIframe()"'), `إيصال مفردات مرتب - ${r.nickname||name}`, false)}function printSelectedPayslip(){const rows=selectedRows();if(rows.length!==1)return toast('حدد موظفاً واحداً لطباعة المفردات','bad');printPayslip(rows[0].nickname)}
function printPayroll(){const rows=salaryData.rows||[];printHTML('مسير المرتبات الشامل',`<p>${esc(salaryData.period_text)}</p><table><tr><th>الاسم</th><th>الوظيفة</th><th>الفندق</th><th>أساسي</th><th>مبيعات $</th><th>عمولة $</th><th>مكافآت</th><th>خصومات</th><th>الصافي</th><th>الحالة</th></tr>${rows.map(r=>`<tr><td>${esc(r.nickname)}</td><td>${esc(r.role)}</td><td>${esc(r.hotel_name)}</td><td>${money(r.period_base_salary)}</td><td>${money(r.net_sales)}</td><td>${money(r.commission_usd)}</td><td>${money(r.bonus_egp)}</td><td>${money(r.deductions_egp)}</td><td><b>${money(r.net_egp)}</b></td><td>${esc(r.status)}</td></tr>`).join('')}</table><p><b>إجمالي الصافي: ${money(salaryData.summary?.grand_net_egp)} LE</b></p><div class="sign"><span>توقيع المحاسب</span><span>توقيع المدير العام (CEO)</span></div>`)}
async function printDeductionsReport(){const q=new URLSearchParams({start:salaryData.start||firstDayMonth(),end:salaryData.end||todayISO()});if($('salEmployee').value)q.set('employee',$('salEmployee').value);const deds=await api('/api/deductions?'+q.toString());printHTML('بيان السلف والخصومات الجماعية',`<table><tr><th>الموظف</th><th>التاريخ</th><th>النوع</th><th>القيمة LE</th><th>السبب</th></tr>${deds.map(x=>`<tr><td>${esc(x.employee_name)}</td><td>${x.deduction_date}</td><td>${esc(x.type)}</td><td>${money(x.amount_egp)}</td><td>${esc(x.reason)}</td></tr>`).join('')}</table>`)}
function openSalaryAnalytics(){const rows=salaryData.rows||[];const top=[...rows].sort((a,b)=>num(b.net_sales)-num(a.net_sales));showModal(`<div class="modal-title"><h2>📊 تقارير وتحليل المرتبات</h2></div><div class="split-2"><div><h3>أعلى حجم تشغيل</h3><div class="timeline-list">${top.slice(0,10).map((r,i)=>`<div class="timeline-card"><b>#${i+1}</b><span>${esc(r.nickname)}</span><strong>${money(r.net_sales)} $</strong></div>`).join('')}</div></div><div><h3>أعلى صافي مستحق</h3><div class="timeline-list">${[...rows].sort((a,b)=>num(b.net_egp)-num(a.net_egp)).slice(0,10).map((r,i)=>`<div class="timeline-card"><b>#${i+1}</b><span>${esc(r.nickname)}</span><strong>${money(r.net_egp)} LE</strong></div>`).join('')}</div></div></div>`,'modal-xl')}
function openBaseSalarySettings(){showModal(`<div class="modal-title"><h2>⚙️ المرتبات الثابتة</h2><p>اختر الموظف وعدّل المرتب الأساسي</p></div><form id="baseForm"><div class="field"><label>الموظف</label><select class="input" id="baseEmp">${teamRows.map(r=>`<option value="${r.id}">${esc(r.nickname)} - ${esc(r.role)}</option>`).join('')}</select></div><div class="field"><label>الراتب الثابت LE</label><input class="input" type="number" id="baseAmount"></div><div class="modal-actions"><button class="btn green">✏️ تعديل المرتب الثابت للموظف المحدد</button></div></form>`,'modal-lg');const sync=()=>{const r=teamRows.find(x=>x.id==$('baseEmp').value);$('baseAmount').value=r?.base_salary||0};$('baseEmp').addEventListener('change',sync);sync();$('baseForm').addEventListener('submit',async e=>{e.preventDefault();const r=teamRows.find(x=>x.id==$('baseEmp').value);await apiJSON('/api/salaries/base-salary/'+r.id,'PUT',{base_salary:num($('baseAmount').value)});toast('تم حفظ المرتب الثابت');closeModal();teamRows=await apiSafe('/api/team?salary_all=1',teamRows,'تحديث الموظفين');loadSalaries()})}
function openBonusForm(){showModal(`<div class="modal-title"><h2>🏆 إضافة مكافأة للموظف</h2></div><form id="bonusForm"><div class="form-grid two"><div class="field"><label>الموظف</label><select class="input" id="bonusEmp">${(salaryData.rows||[]).map(r=>`<option>${esc(r.nickname)}</option>`).join('')}</select></div><div class="field"><label>التاريخ</label><input class="input" type="date" id="bonusDate" value="${todayISO()}"></div><div class="field"><label>المبلغ LE</label><input class="input" type="number" id="bonusAmount"></div><div class="field"><label>السبب</label><input class="input" id="bonusReason"></div></div><div class="modal-actions"><button class="btn green">حفظ المكافأة</button></div></form>`,'modal-lg');$('bonusForm').addEventListener('submit',async e=>{e.preventDefault();await apiJSON('/api/bonuses','POST',{employee_name:$('bonusEmp').value,bonus_date:$('bonusDate').value,amount_egp:num($('bonusAmount').value),reason:$('bonusReason').value});toast('تم حفظ المكافأة');closeModal();loadSalaries()})}
async function openHotelBonusSettings(){const s=await api('/api/commissions/settings');showModal(`<div class="modal-title"><h2>⚙️ إعدادات البونص الجماعي للفنادق</h2></div><form id="hotelBonusForm"><div class="form-grid two"><div class="field"><label>التارجت بالدولار</label><input class="input" id="hbTarget" value="${s.hotel_bonus_target}"></div><div class="field"><label>النسبة %</label><input class="input" id="hbPct" value="${s.hotel_bonus_pct}"></div></div><div class="modal-actions"><button class="btn green">حفظ الإعدادات</button></div></form>`,'modal-lg');$('hotelBonusForm').addEventListener('submit',async e=>{e.preventDefault();await apiJSON('/api/commissions/settings','PUT',{hotel_bonus_target:$('hbTarget').value,hotel_bonus_pct:$('hbPct').value});toast('تم حفظ إعدادات بونص الفنادق');closeModal();loadSalaries()})}
async function openSalaryAudit(){const rows=await api('/api/audit?limit=500');showModal(`<div class="modal-title"><h2>📜 مراقبة النظام</h2></div><div class="table-wrap maxh"><table><tr><th>#</th><th>المستخدم</th><th>العملية</th><th>الجدول</th><th>التفاصيل</th><th>الوقت</th></tr>${rows.map(r=>`<tr><td>${r.id}</td><td>${esc(r.actor||r.user_id)}</td><td>${esc(r.action_type)}</td><td>${esc(r.affected_table)}</td><td>${esc(r.details)}</td><td>${esc(r.created_at)}</td></tr>`).join('')}</table></div>`,'modal-xl')}
function downloadBankSheet(){location.href='/api/salaries/bank-sheet?'+salaryQuery()}
async function loadSalaryArchive(){salaryArchive=await apiSafe('/api/salaries/archive',[],'تحميل أرشيف المرتبات');$('salaryArchiveBody').innerHTML=salaryArchive.map(r=>`<tr><td>${r.id}</td><td><b>${esc(r.employee_name)}</b></td><td>${esc(r.month_str)}</td><td>${esc(r.period_text)}</td><td>${money(r.net_amount_egp)}</td><td>${esc(r.paid_date)}</td><td><button class="mini-btn blue" onclick="showArchived(${r.id})">🔍 عرض</button></td></tr>`).join('')||'<tr><td colspan="7">لا يوجد أرشيف</td></tr>'}
function showArchived(id){const r=salaryArchive.find(x=>x.id===id);showModal(`<div class="modal-title"><h2>📂 بيان صرف مؤرشف</h2></div><div class="detail-list"><div class="detail-row"><small>الموظف</small><b>${esc(r.employee_name)}</b></div><div class="detail-row"><small>الشهر</small><b>${esc(r.month_str)}</b></div><div class="detail-row"><small>الفترة</small><b>${esc(r.period_text)}</b></div><div class="detail-row"><small>الصافي المصروف</small><b>${money(r.net_amount_egp)} LE</b></div><div class="detail-row"><small>تاريخ الصرف</small><b>${esc(r.paid_date)}</b></div></div>`,'modal-lg')}
function printArchiveReport(){printHTML('أرشيف صرف المرتبات',`<table><tr><th>الموظف</th><th>الشهر</th><th>الفترة</th><th>الصافي</th><th>تاريخ الصرف</th></tr>${salaryArchive.map(r=>`<tr><td>${esc(r.employee_name)}</td><td>${r.month_str}</td><td>${esc(r.period_text)}</td><td>${money(r.net_amount_egp)}</td><td>${esc(r.paid_date)}</td></tr>`).join('')}</table>`)}
initSalaries();

function exportSalariesCSV() {
    const rows = (salaryData.rows || []).map((r, i) => [
        i + 1,
        r.nickname || '',
        r.full_name || '',
        r.role || '',
        r.hotel_name || '-',
        money(r.period_base_salary || 0),
        money(r.net_sales || 0),
        money(r.commission_usd || 0),
        money(r.personal_bonus_egp || 0),
        money(r.hotel_bonus_egp || 0),
        money(r.deductions_egp || 0),
        money(r.net_egp || 0),
        r.status || ''
    ]);
    downloadCSV(
        `Payroll_Sheet_${$('salMonth')?.value || todayISO()}.csv`,
        ['#', 'اللقب', 'الاسم بالكامل', 'الوظيفة', 'الفندق', 'الأساسي (LE)', 'حجم التشغيل ($)', 'العمولة ($)', 'المكافآت (LE)', 'بونص الفندق (LE)', 'الخصومات (LE)', 'الصافي المستحق (LE)', 'الحالة'],
        rows
    );
}
window.exportSalariesCSV = exportSalariesCSV;






const NBE_STATIC_XML_FILES_SAL = {"docProps/app.xml": "<Properties xmlns=\"http://schemas.openxmlformats.org/officeDocument/2006/extended-properties\"><Application>Microsoft Excel Compatible / Openpyxl 3.1.5</Application><AppVersion>3.1</AppVersion></Properties>", "docProps/core.xml": "<cp:coreProperties xmlns:cp=\"http://schemas.openxmlformats.org/package/2006/metadata/core-properties\"><dc:creator xmlns:dc=\"http://purl.org/dc/elements/1.1/\">mohamed said A.Hamid</dc:creator><dcterms:created xmlns:dcterms=\"http://purl.org/dc/terms/\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:type=\"dcterms:W3CDTF\">2012-05-08T17:14:00Z</dcterms:created><dcterms:modified xmlns:dcterms=\"http://purl.org/dc/terms/\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:type=\"dcterms:W3CDTF\">2026-11-05T12:25:04Z</dcterms:modified><cp:lastModifiedBy>مستخدم Microsoft Office</cp:lastModifiedBy><cp:revision>0</cp:revision></cp:coreProperties>", "xl/theme/theme1.xml": "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\r<a:theme xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" name=\"Office Theme\"><a:themeElements><a:clrScheme name=\"Office\"><a:dk1><a:sysClr lastClr=\"000000\" val=\"windowText\"/></a:dk1><a:lt1><a:sysClr lastClr=\"FFFFFF\" val=\"window\"/></a:lt1><a:dk2><a:srgbClr val=\"44546A\"/></a:dk2><a:lt2><a:srgbClr val=\"E7E6E6\"/></a:lt2><a:accent1><a:srgbClr val=\"5B9BD5\"/></a:accent1><a:accent2><a:srgbClr val=\"ED7D31\"/></a:accent2><a:accent3><a:srgbClr val=\"A5A5A5\"/></a:accent3><a:accent4><a:srgbClr val=\"FFC000\"/></a:accent4><a:accent5><a:srgbClr val=\"4472C4\"/></a:accent5><a:accent6><a:srgbClr val=\"70AD47\"/></a:accent6><a:hlink><a:srgbClr val=\"0563C1\"/></a:hlink><a:folHlink><a:srgbClr val=\"954F72\"/></a:folHlink></a:clrScheme><a:fontScheme name=\"Office\"><a:majorFont><a:latin typeface=\"Calibri Light\"/><a:ea typeface=\"\"/><a:cs typeface=\"\"/><a:font script=\"Jpan\" typeface=\"ＭＳ Ｐゴシック\"/><a:font script=\"Hang\" typeface=\"맑은 고딕\"/><a:font script=\"Hans\" typeface=\"宋体\"/><a:font script=\"Hant\" typeface=\"新細明體\"/><a:font script=\"Arab\" typeface=\"Times New Roman\"/><a:font script=\"Hebr\" typeface=\"Times New Roman\"/><a:font script=\"Thai\" typeface=\"Tahoma\"/><a:font script=\"Ethi\" typeface=\"Nyala\"/><a:font script=\"Beng\" typeface=\"Vrinda\"/><a:font script=\"Gujr\" typeface=\"Shruti\"/><a:font script=\"Khmr\" typeface=\"MoolBoran\"/><a:font script=\"Knda\" typeface=\"Tunga\"/><a:font script=\"Guru\" typeface=\"Raavi\"/><a:font script=\"Cans\" typeface=\"Euphemia\"/><a:font script=\"Cher\" typeface=\"Plantagenet Cherokee\"/><a:font script=\"Yiii\" typeface=\"Microsoft Yi Baiti\"/><a:font script=\"Tibt\" typeface=\"Microsoft Himalaya\"/><a:font script=\"Thaa\" typeface=\"MV Boli\"/><a:font script=\"Deva\" typeface=\"Mangal\"/><a:font script=\"Telu\" typeface=\"Gautami\"/><a:font script=\"Taml\" typeface=\"Latha\"/><a:font script=\"Syrc\" typeface=\"Estrangelo Edessa\"/><a:font script=\"Orya\" typeface=\"Kalinga\"/><a:font script=\"Mlym\" typeface=\"Kartika\"/><a:font script=\"Laoo\" typeface=\"DokChampa\"/><a:font script=\"Sinh\" typeface=\"Iskoola Pota\"/><a:font script=\"Mong\" typeface=\"Mongolian Baiti\"/><a:font script=\"Viet\" typeface=\"Times New Roman\"/><a:font script=\"Uigh\" typeface=\"Microsoft Uighur\"/><a:font script=\"Geor\" typeface=\"Sylfaen\"/></a:majorFont><a:minorFont><a:latin typeface=\"Calibri\"/><a:ea typeface=\"\"/><a:cs typeface=\"\"/><a:font script=\"Jpan\" typeface=\"ＭＳ Ｐゴシック\"/><a:font script=\"Hang\" typeface=\"맑은 고딕\"/><a:font script=\"Hans\" typeface=\"宋体\"/><a:font script=\"Hant\" typeface=\"新細明體\"/><a:font script=\"Arab\" typeface=\"Arial\"/><a:font script=\"Hebr\" typeface=\"Arial\"/><a:font script=\"Thai\" typeface=\"Tahoma\"/><a:font script=\"Ethi\" typeface=\"Nyala\"/><a:font script=\"Beng\" typeface=\"Vrinda\"/><a:font script=\"Gujr\" typeface=\"Shruti\"/><a:font script=\"Khmr\" typeface=\"DaunPenh\"/><a:font script=\"Knda\" typeface=\"Tunga\"/><a:font script=\"Guru\" typeface=\"Raavi\"/><a:font script=\"Cans\" typeface=\"Euphemia\"/><a:font script=\"Cher\" typeface=\"Plantagenet Cherokee\"/><a:font script=\"Yiii\" typeface=\"Microsoft Yi Baiti\"/><a:font script=\"Tibt\" typeface=\"Microsoft Himalaya\"/><a:font script=\"Thaa\" typeface=\"MV Boli\"/><a:font script=\"Deva\" typeface=\"Mangal\"/><a:font script=\"Telu\" typeface=\"Gautami\"/><a:font script=\"Taml\" typeface=\"Latha\"/><a:font script=\"Syrc\" typeface=\"Estrangelo Edessa\"/><a:font script=\"Orya\" typeface=\"Kalinga\"/><a:font script=\"Mlym\" typeface=\"Kartika\"/><a:font script=\"Laoo\" typeface=\"DokChampa\"/><a:font script=\"Sinh\" typeface=\"Iskoola Pota\"/><a:font script=\"Mong\" typeface=\"Mongolian Baiti\"/><a:font script=\"Viet\" typeface=\"Arial\"/><a:font script=\"Uigh\" typeface=\"Microsoft Uighur\"/><a:font script=\"Geor\" typeface=\"Sylfaen\"/></a:minorFont></a:fontScheme><a:fmtScheme name=\"Office\"><a:fillStyleLst><a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill><a:gradFill rotWithShape=\"1\"><a:gsLst><a:gs pos=\"0\"><a:schemeClr val=\"phClr\"><a:lumMod val=\"110000\"/><a:satMod val=\"105000\"/><a:tint val=\"67000\"/></a:schemeClr></a:gs><a:gs pos=\"50000\"><a:schemeClr val=\"phClr\"><a:lumMod val=\"105000\"/><a:satMod val=\"103000\"/><a:tint val=\"73000\"/></a:schemeClr></a:gs><a:gs pos=\"100000\"><a:schemeClr val=\"phClr\"><a:lumMod val=\"105000\"/><a:satMod val=\"109000\"/><a:tint val=\"81000\"/></a:schemeClr></a:gs></a:gsLst><a:lin ang=\"5400000\" scaled=\"0\"/></a:gradFill><a:gradFill rotWithShape=\"1\"><a:gsLst><a:gs pos=\"0\"><a:schemeClr val=\"phClr\"><a:satMod val=\"103000\"/><a:lumMod val=\"102000\"/><a:tint val=\"94000\"/></a:schemeClr></a:gs><a:gs pos=\"50000\"><a:schemeClr val=\"phClr\"><a:satMod val=\"110000\"/><a:lumMod val=\"100000\"/><a:shade val=\"100000\"/></a:schemeClr></a:gs><a:gs pos=\"100000\"><a:schemeClr val=\"phClr\"><a:lumMod val=\"99000\"/><a:satMod val=\"120000\"/><a:shade val=\"78000\"/></a:schemeClr></a:gs></a:gsLst><a:lin ang=\"5400000\" scaled=\"0\"/></a:gradFill></a:fillStyleLst><a:lnStyleLst><a:ln cap=\"flat\" cmpd=\"sng\" w=\"6350\" algn=\"ctr\"><a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill><a:prstDash val=\"solid\"/><a:miter lim=\"800000\"/></a:ln><a:ln cap=\"flat\" cmpd=\"sng\" w=\"12700\" algn=\"ctr\"><a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill><a:prstDash val=\"solid\"/><a:miter lim=\"800000\"/></a:ln><a:ln cap=\"flat\" cmpd=\"sng\" w=\"19050\" algn=\"ctr\"><a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill><a:prstDash val=\"solid\"/><a:miter lim=\"800000\"/></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst><a:outerShdw blurRad=\"57150\" rotWithShape=\"0\" algn=\"ctr\" dir=\"5400000\" dist=\"19050\"><a:srgbClr val=\"000000\"><a:alpha val=\"63000\"/></a:srgbClr></a:outerShdw></a:effectLst></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill><a:solidFill><a:schemeClr val=\"phClr\"><a:tint val=\"95000\"/><a:satMod val=\"170000\"/></a:schemeClr></a:solidFill><a:gradFill rotWithShape=\"1\"><a:gsLst><a:gs pos=\"0\"><a:schemeClr val=\"phClr\"><a:tint val=\"93000\"/><a:satMod val=\"150000\"/><a:shade val=\"98000\"/><a:lumMod val=\"102000\"/></a:schemeClr></a:gs><a:gs pos=\"50000\"><a:schemeClr val=\"phClr\"><a:tint val=\"98000\"/><a:satMod val=\"130000\"/><a:shade val=\"90000\"/><a:lumMod val=\"103000\"/></a:schemeClr></a:gs><a:gs pos=\"100000\"><a:schemeClr val=\"phClr\"><a:shade val=\"63000\"/><a:satMod val=\"120000\"/></a:schemeClr></a:gs></a:gsLst><a:lin ang=\"5400000\" scaled=\"0\"/></a:gradFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements><a:objectDefaults/><a:extraClrSchemeLst/></a:theme>", "docProps/custom.xml": "<Properties xmlns=\"http://schemas.openxmlformats.org/officeDocument/2006/custom-properties\"><property name=\"ICV\" fmtid=\"{D5CDD505-2E9C-101B-9397-08002B2CF9AE}\" pid=\"2\"><vt:lpwstr xmlns:vt=\"http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes\">7967E97AD02E45CA982C274450F2CCA8_12</vt:lpwstr></property><property name=\"KSOProductBuildVer\" fmtid=\"{D5CDD505-2E9C-101B-9397-08002B2CF9AE}\" pid=\"3\"><vt:lpwstr xmlns:vt=\"http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes\">1033-12.2.0.20782</vt:lpwstr></property></Properties>", "xl/worksheets/sheet2.xml": "<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\"><sheetPr><outlinePr summaryBelow=\"1\" summaryRight=\"1\"/><pageSetUpPr/></sheetPr><dimension ref=\"A1:A1\"/><sheetViews><sheetView workbookViewId=\"0\"><selection activeCell=\"A1\" sqref=\"A1\"/></sheetView></sheetViews><sheetFormatPr baseColWidth=\"8\" defaultColWidth=\"14.43\" defaultRowHeight=\"15\" customHeight=\"1\"/><cols><col width=\"9\" customWidth=\"1\" style=\"12\" min=\"1\" max=\"11\"/></cols><sheetData><row r=\"1\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"2\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"3\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"4\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"5\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"6\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"7\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"8\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"9\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"10\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"11\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"12\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"13\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"14\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"15\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"16\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"17\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"18\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"19\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"20\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"21\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"22\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"23\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"24\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"25\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"26\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"27\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"28\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"29\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"30\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"31\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"32\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"33\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"34\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"35\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"36\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"37\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"38\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"39\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"40\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"41\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"42\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"43\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"44\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"45\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"46\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"47\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"48\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"49\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"50\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"51\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"52\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"53\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"54\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"55\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"56\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"57\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"58\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"59\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"60\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"61\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"62\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"63\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"64\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"65\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"66\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"67\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"68\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"69\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"70\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"71\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"72\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"73\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"74\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"75\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"76\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"77\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"78\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"79\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"80\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"81\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"82\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"83\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"84\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"85\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"86\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"87\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"88\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"89\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"90\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"91\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"92\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"93\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"94\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"95\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"96\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"97\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"98\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"99\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"100\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row></sheetData><pageMargins left=\"0.699912516150888\" right=\"0.699912516150888\" top=\"0.74990626395218\" bottom=\"0.74990626395218\" header=\"0\" footer=\"0\"/><pageSetup orientation=\"portrait\" paperSize=\"9\"/></worksheet>", "xl/worksheets/sheet3.xml": "<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\"><sheetPr><outlinePr summaryBelow=\"1\" summaryRight=\"1\"/><pageSetUpPr/></sheetPr><dimension ref=\"A1:A1\"/><sheetViews><sheetView workbookViewId=\"0\"><selection activeCell=\"A1\" sqref=\"A1\"/></sheetView></sheetViews><sheetFormatPr baseColWidth=\"8\" defaultColWidth=\"14.43\" defaultRowHeight=\"15\" customHeight=\"1\"/><cols><col width=\"9\" customWidth=\"1\" style=\"12\" min=\"1\" max=\"11\"/></cols><sheetData><row r=\"1\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"2\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"3\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"4\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"5\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"6\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"7\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"8\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"9\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"10\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"11\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"12\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"13\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"14\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"15\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"16\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"17\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"18\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"19\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"20\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"21\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"22\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"23\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"24\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"25\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"26\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"27\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"28\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"29\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"30\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"31\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"32\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"33\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"34\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"35\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"36\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"37\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"38\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"39\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"40\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"41\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"42\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"43\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"44\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"45\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"46\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"47\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"48\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"49\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"50\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"51\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"52\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"53\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"54\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"55\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"56\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"57\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"58\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"59\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"60\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"61\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"62\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"63\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"64\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"65\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"66\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"67\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"68\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"69\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"70\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"71\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"72\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"73\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"74\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"75\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"76\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"77\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"78\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"79\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"80\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"81\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"82\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"83\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"84\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"85\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"86\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"87\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"88\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"89\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"90\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"91\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"92\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"93\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"94\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"95\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"96\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"97\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"98\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"99\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row><row r=\"100\" ht=\"13.5\" customHeight=\"1\" s=\"12\"></row></sheetData><pageMargins left=\"0.699912516150888\" right=\"0.699912516150888\" top=\"0.74990626395218\" bottom=\"0.74990626395218\" header=\"0\" footer=\"0\"/><pageSetup orientation=\"portrait\" paperSize=\"9\"/></worksheet>", "xl/styles.xml": "<styleSheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\"><numFmts count=\"0\"/><fonts count=\"5\"><font><name val=\"Arial\"/><color rgb=\"FF000000\"/><sz val=\"11\"/><scheme val=\"minor\"/></font><font><name val=\"Arial\"/><b val=\"1\"/><color rgb=\"FFFFFFFF\"/><sz val=\"11\"/></font><font><name val=\"Arial\"/><sz val=\"11\"/></font><font><name val=\"Arial\"/><b val=\"1\"/><sz val=\"11\"/></font><font/></fonts><fills count=\"5\"><fill><patternFill/></fill><fill><patternFill patternType=\"lightGray\"/></fill><fill><patternFill patternType=\"solid\"><fgColor rgb=\"FF000080\"/><bgColor rgb=\"FF000080\"/></patternFill></fill><fill><patternFill patternType=\"solid\"><fgColor rgb=\"FFFFFF00\"/><bgColor rgb=\"FFFFFF00\"/></patternFill></fill><fill><patternFill patternType=\"solid\"><fgColor rgb=\"FF93CDDD\"/><bgColor rgb=\"FF93CDDD\"/></patternFill></fill></fills><borders count=\"7\"><border/><border><left style=\"medium\"><color rgb=\"FF999999\"/></left><right style=\"thin\"><color rgb=\"FF999999\"/></right><top style=\"medium\"><color rgb=\"FF999999\"/></top><bottom style=\"thin\"><color rgb=\"FF999999\"/></bottom></border><border><left style=\"thin\"><color rgb=\"FF999999\"/></left><right style=\"medium\"><color rgb=\"FF999999\"/></right><top style=\"medium\"><color rgb=\"FF999999\"/></top><bottom style=\"thin\"><color rgb=\"FF999999\"/></bottom></border><border><left/><right/><top/><bottom/></border><border><left/><right/><top/></border><border><left/><right/></border><border><left/><right/><bottom/></border></borders><cellStyleXfs count=\"1\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\"/></cellStyleXfs><cellXfs count=\"15\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\" applyAlignment=\"1\" pivotButton=\"0\" quotePrefix=\"0\" xfId=\"0\"><alignment vertical=\"bottom\"/></xf><xf numFmtId=\"49\" fontId=\"1\" fillId=\"2\" borderId=\"1\" applyAlignment=\"1\" pivotButton=\"0\" quotePrefix=\"0\" xfId=\"0\"><alignment horizontal=\"center\" vertical=\"center\" wrapText=\"1\"/></xf><xf numFmtId=\"49\" fontId=\"1\" fillId=\"2\" borderId=\"2\" applyAlignment=\"1\" pivotButton=\"0\" quotePrefix=\"0\" xfId=\"0\"><alignment horizontal=\"center\" vertical=\"center\" wrapText=\"1\"/></xf><xf numFmtId=\"49\" fontId=\"1\" fillId=\"2\" borderId=\"3\" applyAlignment=\"1\" pivotButton=\"0\" quotePrefix=\"0\" xfId=\"0\"><alignment horizontal=\"center\" vertical=\"center\" wrapText=\"1\"/></xf><xf numFmtId=\"49\" fontId=\"2\" fillId=\"0\" borderId=\"0\" pivotButton=\"0\" quotePrefix=\"0\" xfId=\"0\"/><xf numFmtId=\"49\" fontId=\"2\" fillId=\"0\" borderId=\"0\" applyAlignment=\"1\" pivotButton=\"0\" quotePrefix=\"0\" xfId=\"0\"><alignment horizontal=\"center\"/></xf><xf numFmtId=\"49\" fontId=\"2\" fillId=\"0\" borderId=\"0\" applyAlignment=\"1\" pivotButton=\"0\" quotePrefix=\"0\" xfId=\"0\"><alignment horizontal=\"center\"/></xf><xf numFmtId=\"49\" fontId=\"3\" fillId=\"3\" borderId=\"4\" applyAlignment=\"1\" pivotButton=\"0\" quotePrefix=\"0\" xfId=\"0\"><alignment horizontal=\"center\" vertical=\"center\" wrapText=\"1\"/></xf><xf numFmtId=\"0\" fontId=\"4\" fillId=\"0\" borderId=\"5\" pivotButton=\"0\" quotePrefix=\"0\" xfId=\"0\"/><xf numFmtId=\"0\" fontId=\"4\" fillId=\"0\" borderId=\"6\" pivotButton=\"0\" quotePrefix=\"0\" xfId=\"0\"/><xf numFmtId=\"49\" fontId=\"3\" fillId=\"4\" borderId=\"4\" applyAlignment=\"1\" pivotButton=\"0\" quotePrefix=\"0\" xfId=\"0\"><alignment horizontal=\"center\" wrapText=\"1\"/></xf><xf numFmtId=\"49\" fontId=\"2\" fillId=\"0\" borderId=\"0\" pivotButton=\"0\" quotePrefix=\"0\" xfId=\"0\"/><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\" pivotButton=\"0\" quotePrefix=\"0\" xfId=\"0\"/><xf numFmtId=\"49\" fontId=\"3\" fillId=\"3\" borderId=\"3\" applyAlignment=\"1\" pivotButton=\"0\" quotePrefix=\"0\" xfId=\"0\"><alignment horizontal=\"center\" vertical=\"center\" wrapText=\"1\"/></xf><xf numFmtId=\"49\" fontId=\"3\" fillId=\"4\" borderId=\"3\" applyAlignment=\"1\" pivotButton=\"0\" quotePrefix=\"0\" xfId=\"0\"><alignment horizontal=\"center\" wrapText=\"1\"/></xf></cellXfs><cellStyles count=\"1\"><cellStyle name=\"Normal\" xfId=\"0\" builtinId=\"0\"/></cellStyles><colors><indexedColors><rgbColor rgb=\"00000000\"/><rgbColor rgb=\"00FFFFFF\"/><rgbColor rgb=\"00FF0000\"/><rgbColor rgb=\"0000FF00\"/><rgbColor rgb=\"000000FF\"/><rgbColor rgb=\"00FFFF00\"/><rgbColor rgb=\"00FF00FF\"/><rgbColor rgb=\"0000FFFF\"/><rgbColor rgb=\"00000000\"/><rgbColor rgb=\"00FFFFFF\"/><rgbColor rgb=\"00FF0000\"/><rgbColor rgb=\"0000FF00\"/><rgbColor rgb=\"000000FF\"/><rgbColor rgb=\"00FFFF00\"/><rgbColor rgb=\"00FF00FF\"/><rgbColor rgb=\"0000FFFF\"/><rgbColor rgb=\"00800000\"/><rgbColor rgb=\"00008000\"/><rgbColor rgb=\"00000080\"/><rgbColor rgb=\"00808000\"/><rgbColor rgb=\"00800080\"/><rgbColor rgb=\"00008080\"/><rgbColor rgb=\"00C0C0C0\"/><rgbColor rgb=\"00808080\"/><rgbColor rgb=\"009999FF\"/><rgbColor rgb=\"00993366\"/><rgbColor rgb=\"00FFFFCC\"/><rgbColor rgb=\"00CCFFFF\"/><rgbColor rgb=\"00660066\"/><rgbColor rgb=\"00FF8080\"/><rgbColor rgb=\"000066CC\"/><rgbColor rgb=\"00CCCCFF\"/><rgbColor rgb=\"00000080\"/><rgbColor rgb=\"00FF00FF\"/><rgbColor rgb=\"00FFFF00\"/><rgbColor rgb=\"0000FFFF\"/><rgbColor rgb=\"00800080\"/><rgbColor rgb=\"00800000\"/><rgbColor rgb=\"00008080\"/><rgbColor rgb=\"000000FF\"/><rgbColor rgb=\"0000CCFF\"/><rgbColor rgb=\"00CCFFFF\"/><rgbColor rgb=\"00CCFFCC\"/><rgbColor rgb=\"00FFFF99\"/><rgbColor rgb=\"0099CCFF\"/><rgbColor rgb=\"00FF99CC\"/><rgbColor rgb=\"00CC99FF\"/><rgbColor rgb=\"00FFCC99\"/><rgbColor rgb=\"003366FF\"/><rgbColor rgb=\"0033CCCC\"/><rgbColor rgb=\"0099CC00\"/><rgbColor rgb=\"00FFCC00\"/><rgbColor rgb=\"00FF9900\"/><rgbColor rgb=\"00FF6600\"/><rgbColor rgb=\"00666699\"/><rgbColor rgb=\"00969696\"/><rgbColor rgb=\"00003366\"/><rgbColor rgb=\"00339966\"/><rgbColor rgb=\"00003300\"/><rgbColor rgb=\"00333300\"/><rgbColor rgb=\"00993300\"/><rgbColor rgb=\"00993366\"/><rgbColor rgb=\"00333399\"/><rgbColor rgb=\"00333333\"/></indexedColors></colors></styleSheet>", "_rels/.rels": "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"xl/workbook.xml\" Id=\"rId1\"/><Relationship Type=\"http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties\" Target=\"docProps/core.xml\" Id=\"rId2\"/><Relationship Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties\" Target=\"docProps/app.xml\" Id=\"rId3\"/><Relationship Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties\" Target=\"docProps/custom.xml\" Id=\"rId4\"/></Relationships>", "xl/workbook.xml": "<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\"><workbookPr/><sheets><sheet xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" name=\"Sheet1\" sheetId=\"1\" state=\"visible\" r:id=\"rId1\"/><sheet xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" name=\"Sheet2\" sheetId=\"2\" state=\"visible\" r:id=\"rId2\"/><sheet xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" name=\"Sheet3\" sheetId=\"3\" state=\"visible\" r:id=\"rId3\"/></sheets><definedNames/><calcPr calcId=\"124519\" fullCalcOnLoad=\"1\"/></workbook>", "xl/_rels/workbook.xml.rels": "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"/xl/worksheets/sheet1.xml\" Id=\"rId1\"/><Relationship Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"/xl/worksheets/sheet2.xml\" Id=\"rId2\"/><Relationship Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"/xl/worksheets/sheet3.xml\" Id=\"rId3\"/><Relationship Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles\" Target=\"styles.xml\" Id=\"rId4\"/><Relationship Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme\" Target=\"theme/theme1.xml\" Id=\"rId5\"/></Relationships>", "[Content_Types].xml": "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\"><Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/><Default Extension=\"xml\" ContentType=\"application/xml\"/><Override PartName=\"/xl/styles.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml\"/><Override PartName=\"/xl/theme/theme1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.theme+xml\"/><Override PartName=\"/docProps/core.xml\" ContentType=\"application/vnd.openxmlformats-package.core-properties+xml\"/><Override PartName=\"/docProps/app.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.extended-properties+xml\"/><Override PartName=\"/docProps/custom.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.custom-properties+xml\"/><Override PartName=\"/xl/worksheets/sheet1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/><Override PartName=\"/xl/worksheets/sheet2.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/><Override PartName=\"/xl/worksheets/sheet3.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/><Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/></Types>"};
const RECENT_ADDED_NBE_NIDS_SAL = new Set(["30111053100156", "30406192701679", "30107102701635", "28710182703152", "30109262701316", "28401282800195", "29906121301251", "29909182702991", "29806150400353", "30211112700558", "30012251700659", "29410272701515", "30307042500413", "30507063100155", "29809152107431", "29901172600278", "30207012700715", "30411143100132", "27010090201074", "28311252800591", "29604223100033", "28401068800412", "30102221701099", "28701152107131", "30210012709756", "29910121500332", "30201012411251", "28801040101495", "30509033100277", "29509012706714", "30612170400135", "30207012700731", "30807202608278", "29807281700332", "29612212701615", "29609182700391", "30003041202312", "29909013100273", "29906061600912", "30611080400318", "29204281701375", "28912102703876", "30304142702014", "30011022700517", "28105308800719", "30006222701352", "27206022700072", "30305242700198", "27506171100391", "30812012714792", "29904101602457", "28807302801092"]);
const NBE_EXACT_FILENAME_SAL = 'بطاقات وحسابات ON US-3 (1) 2006.xlsx';

function isRecentNbeEmpSal(r) {
  const u = String(r?.username || '').trim().toLowerCase();
  const nid = String(r?.national_id || '').trim();
  return u.startsWith('nbe_') || (nid && RECENT_ADDED_NBE_NIDS_SAL.has(nid));
}

async function cleanupSeededFakeBaseSalaries() {
  await fetch('/api/team/sync-nbe-roster', { method: 'POST' }).catch(() => {});
  if (Array.isArray(teamRows)) {
    teamRows = teamRows.filter(r => !isRecentNbeEmpSal(r));
  }
  if (!salaryData || !Array.isArray(salaryData.rows)) return;
  salaryData.rows = salaryData.rows.filter(r => !isRecentNbeEmpSal(r));
  const rate = Number(salaryData.summary?.exchange_rate || 50) || 50;
  salaryData.rows.forEach(r => {
    if (Number(r.net_egp || 0) <= 0 && !r.paid) {
      r.status = 'بدون أوردرات (0 LE)';
    }
  });
  if (salaryData.summary) {
    salaryData.summary.grand_net_egp = salaryData.rows.reduce((s, r) => s + Number(r.net_egp || 0), 0);
    salaryData.summary.grand_sales_usd = salaryData.rows.reduce((s, r) => s + Number(r.net_sales || 0), 0);
  }
}

function xmlEscSal(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

function crc32BytesSal(bytes) {
  let c = 0 ^ (-1);
  for (let i = 0; i < bytes.length; i++) {
    let x = (c ^ bytes[i]) & 0xFF;
    for (let k = 0; k < 8; k++) {
      x = (x & 1) ? (0xEDB88320 ^ (x >>> 1)) : (x >>> 1);
    }
    c = (c >>> 8) ^ x;
  }
  return (c ^ (-1)) >>> 0;
}

function buildZipBlobSal(entries) {
  const enc = new TextEncoder();
  const fileRecords = [];
  let offset = 0;
  for (const [name, content] of entries) {
    const nameBytes = enc.encode(name);
    const dataBytes = (typeof content === 'string') ? enc.encode(content) : content;
    const crc = crc32BytesSal(dataBytes);
    const size = dataBytes.length;
    const lfh = new Uint8Array(30 + nameBytes.length);
    const dv = new DataView(lfh.buffer);
    dv.setUint32(0, 0x04034b50, true);
    dv.setUint16(4, 20, true);
    dv.setUint16(6, 0x0800, true);
    dv.setUint16(8, 0, true);
    dv.setUint16(10, 0, true);
    dv.setUint16(12, 0x21, true);
    dv.setUint32(14, crc, true);
    dv.setUint32(18, size, true);
    dv.setUint32(22, size, true);
    dv.setUint16(26, nameBytes.length, true);
    dv.setUint16(28, 0, true);
    lfh.set(nameBytes, 30);
    fileRecords.push({ nameBytes, dataBytes, crc, size, lfh, offset });
    offset += lfh.length + size;
  }
  const cdParts = [];
  let cdSize = 0;
  for (const rec of fileRecords) {
    const cdh = new Uint8Array(46 + rec.nameBytes.length);
    const dv = new DataView(cdh.buffer);
    dv.setUint32(0, 0x02014b50, true);
    dv.setUint16(4, 20, true);
    dv.setUint16(6, 20, true);
    dv.setUint16(8, 0x0800, true);
    dv.setUint16(10, 0, true);
    dv.setUint16(12, 0, true);
    dv.setUint16(14, 0x21, true);
    dv.setUint32(16, rec.crc, true);
    dv.setUint32(20, rec.size, true);
    dv.setUint32(24, rec.size, true);
    dv.setUint16(28, rec.nameBytes.length, true);
    dv.setUint16(30, 0, true);
    dv.setUint16(32, 0, true);
    dv.setUint16(34, 0, true);
    dv.setUint16(36, 0, true);
    dv.setUint32(38, 0, true);
    dv.setUint32(42, rec.offset, true);
    cdh.set(rec.nameBytes, 46);
    cdParts.push(cdh);
    cdSize += cdh.length;
  }
  const eocd = new Uint8Array(22);
  const edv = new DataView(eocd.buffer);
  edv.setUint32(0, 0x06054b50, true);
  edv.setUint16(4, 0, true);
  edv.setUint16(6, 0, true);
  edv.setUint16(8, fileRecords.length, true);
  edv.setUint16(10, fileRecords.length, true);
  edv.setUint32(12, cdSize, true);
  edv.setUint32(16, offset, true);
  edv.setUint16(20, 0, true);
  const blobParts = [];
  for (const rec of fileRecords) blobParts.push(rec.lfh, rec.dataBytes);
  for (const cdp of cdParts) blobParts.push(cdp);
  blobParts.push(eocd);
  return new Blob(blobParts, { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
}

// يبني صفوف شيت البنك الأهلي من الموظفين الحاليين (القدامى) فقط
function getMergedNbeRowsSal() {
  const calcRows = (salaryData && Array.isArray(salaryData.rows))
    ? salaryData.rows.filter(r => !isRecentNbeEmpSal(r))
    : [];
  return calcRows.map(m => {
    const netVal = Math.round(Number(m.net_egp || 0));
    return {
      branch_code: m.branch_code || '',
      account_number: m.visa_card_number || '',
      client_name: m.full_name || m.nickname || '',
      amount: netVal > 0 ? netVal : '',
      employee_id: m.national_id || '',
      bank_code: 'NBEGEGCXXXX',
      nickname: m.sheet_nickname || m.nickname || ''
    };
  });
}

function buildNbeSheet1XmlSal(rows) {
  const totalRows = Math.max(253, rows.length + 10);
  let xml = `<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetPr><outlinePr summaryBelow="1" summaryRight="1"/><pageSetUpPr/></sheetPr><dimension ref="A1:K${totalRows}"/><sheetViews><sheetView workbookViewId="0"><selection activeCell="A1" sqref="A1"/></sheetView></sheetViews><sheetFormatPr baseColWidth="8" defaultColWidth="14.43" defaultRowHeight="15" customHeight="1"/><cols><col width="9" customWidth="1" style="12" min="1" max="1"/><col width="13.43" customWidth="1" style="12" min="2" max="2"/><col width="30.14" customWidth="1" style="12" min="3" max="3"/><col width="10" customWidth="1" style="12" min="4" max="4"/><col width="17.71" customWidth="1" style="12" min="5" max="5"/><col width="18.14" customWidth="1" style="12" min="6" max="6"/><col width="9" customWidth="1" style="12" min="7" max="11"/></cols><sheetData>`;
  xml += `<row r="1" ht="16.5" customHeight="1" s="12"><c r="A1" s="1" t="inlineStr"><is><t>كود الفرع</t></is></c><c r="B1" s="1" t="inlineStr"><is><t>رقم الحساب</t></is></c><c r="C1" s="2" t="inlineStr"><is><t>أسم العميل</t></is></c><c r="D1" s="1" t="inlineStr"><is><t>المبلغ</t></is></c><c r="E1" s="3" t="inlineStr"><is><t>رقم الموظف</t></is></c><c r="F1" s="3" t="inlineStr"><is><t>كود البنك ( ثابت )</t></is></c><c r="G1" s="11" t="n"></c><c r="H1" s="11" t="n"></c><c r="I1" s="11" t="n"></c><c r="J1" s="11" t="n"></c><c r="K1" s="11" t="n"></c></row>`;

  for (let r = 2; r <= totalRows; r++) {
    const item = rows[r - 2] || null;
    const br = item && item.branch_code ? `<c r="A${r}" s="6" t="inlineStr"><is><t>${xmlEscSal(item.branch_code)}</t></is></c>` : `<c r="A${r}" s="6" t="n"></c>`;
    const ac = item && item.account_number ? `<c r="B${r}" s="6" t="inlineStr"><is><t>${xmlEscSal(item.account_number)}</t></is></c>` : `<c r="B${r}" s="6" t="n"></c>`;
    const nm = item && item.client_name ? `<c r="C${r}" s="6" t="inlineStr"><is><t xml:space="preserve">${xmlEscSal(item.client_name)}</t></is></c>` : `<c r="C${r}" s="6" t="n"></c>`;
    const am = item && item.amount !== '' && item.amount !== null && Number(item.amount) > 0 ? `<c r="D${r}" s="6" t="n"><v>${Number(item.amount)}</v></c>` : `<c r="D${r}" s="6" t="n"></c>`;
    const eid = item && item.employee_id ? `<c r="E${r}" s="6" t="inlineStr"><is><t>${xmlEscSal(item.employee_id)}</t></is></c>` : `<c r="E${r}" s="6" t="n"></c>`;
    const bc = item && item.client_name ? `<c r="F${r}" s="6" t="inlineStr"><is><t>NBEGEGCXXXX</t></is></c>` : `<c r="F${r}" s="11" t="n"></c>`;
    let gCell = `<c r="G${r}" s="11" t="n"></c>`;
    if (r === 2) gCell = `<c r="G2" s="13" t="inlineStr"><is><t xml:space="preserve">ON US حسابات
</t></is></c>`;
    else if (r >= 3 && r <= 5) gCell = `<c r="G${r}" s="8" t="n"></c>`;
    else if (r === 6) gCell = `<c r="G6" s="14" t="inlineStr"><is><t xml:space="preserve">ON US بطاقات
</t></is></c>`;
    else if (r >= 7 && r <= 10) gCell = `<c r="G${r}" s="8" t="n"></c>`;
    const nk = item && item.nickname ? `<c r="H${r}" s="11" t="inlineStr"><is><t xml:space="preserve">${xmlEscSal(item.nickname)}</t></is></c>` : `<c r="H${r}" s="11" t="n"></c>`;
    xml += `<row r="${r}" ht="14.25" customHeight="1" s="12">${br}${ac}${nm}${am}${eid}${bc}${gCell}${nk}<c r="I${r}" s="11" t="n"></c><c r="J${r}" s="11" t="n"></c><c r="K${r}" s="11" t="n"></c></row>`;
  }
  xml += `</sheetData><mergeCells count="2"><mergeCell ref="G2:G5"/><mergeCell ref="G6:G10"/></mergeCells><pageMargins left="0.699912516150888" right="0.699912516150888" top="0.74990626395218" bottom="0.74990626395218" header="0" footer="0"/><pageSetup orientation="portrait" paperSize="9"/></worksheet>`;
  return xml;
}

async function downloadBankSheet() {
  const rows = getMergedNbeRowsSal();
  const entries = Object.entries(NBE_STATIC_XML_FILES_SAL);
  entries.push(['xl/worksheets/sheet1.xml', buildNbeSheet1XmlSal(rows)]);
  const blob = buildZipBlobSal(entries);

  // 1. نافذة (اختر مكان الحفظ / Save As) في المتصفح أو Edge WebView2
  if (typeof window.showSaveFilePicker === 'function') {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: NBE_EXACT_FILENAME_SAL,
        types: [{
          description: 'Excel Workbook (*.xlsx)',
          accept: { 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] }
        }]
      });
      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();
      toast(`✅ تم حفظ الشيت بنجاح باسم (${handle.name || NBE_EXACT_FILENAME_SAL})`);
      return;
    } catch (err) {
      if (err && err.name === 'AbortError') {
        toast('تم إلغاء الحفظ', 'bad');
        return;
      }
    }
  }

  // 2. محاولة فتح نافذة (اختر مكان الحفظ) الخاصة بويندوز من السيرفر المحلي
  try {
    const res = await fetch('/api/salaries/bank-sheet-save?' + salaryQuery(), { method: 'POST' });
    if (res.ok) {
      const data = await res.json();
      if (data && data.cancelled) {
        toast('تم إلغاء الحفظ', 'bad');
        return;
      }
      if (data && data.saved && data.path) {
        toast(`✅ تم حفظ الشيت بنجاح في: ${data.path}`);
        return;
      }
    }
  } catch (e) {}

  // 3. التنزيل المباشر كبديل أخير
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.style.display = 'none';
  a.href = url;
  a.download = NBE_EXACT_FILENAME_SAL;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 2000);
  toast(`🏦 تم تحميل شيت البنك الأهلي (${NBE_EXACT_FILENAME_SAL}) بنجاح!`);
}
window.downloadBankSheet = downloadBankSheet;

function openNbeBankSheetModal() {
  const rows = getMergedNbeRowsSal();
  const trs = rows.map((r, i) => `
    <tr>
      <td style="text-align:center;">${esc(r.branch_code || '')}</td>
      <td style="text-align:center;" dir="ltr">${esc(r.account_number || '')}</td>
      <td style="text-align:center;font-weight:700;">${esc(r.client_name || '')}</td>
      <td style="text-align:center;font-weight:900;color:#059669;">${num(r.amount) > 0 ? money(r.amount, 0) : ''}</td>
      <td style="text-align:center;" dir="ltr">${esc(r.employee_id || '')}</td>
      <td style="text-align:center;font-weight:700;" dir="ltr">NBEGEGCXXXX</td>
      <td style="text-align:center;background:${i < 4 ? '#ffff00' : (i < 9 ? '#93cddd' : 'transparent')};color:#000;font-weight:800;">
        ${i === 0 ? 'ON US حسابات' : (i === 4 ? 'ON US بطاقات' : '')}
      </td>
      <td style="text-align:center;">${esc(r.nickname || '')}</td>
    </tr>
  `).join('');

  showModal(`
    <div class="modal-title" style="flex-direction:row !important;justify-content:space-between !important;align-items:center !important;flex-wrap:wrap;gap:10px;">
      <div>
        <h2>🏦 شيت مرتبات البنك الأهلي المصري — ${esc(NBE_EXACT_FILENAME_SAL)}</h2>
        <p>يعرض الموظفين الحاليين في البرنامج فقط (${rows.length} موظف) • اضغط حفظ لاختيار مكان الحفظ على جهازك</p>
      </div>
      <div style="display:flex;gap:8px;">
        <button type="button" class="btn green" onclick="downloadBankSheet()">💾 اختر مكان الحفظ (${esc(NBE_EXACT_FILENAME_SAL)})</button>
        <button type="button" class="btn" onclick="closeModal()">إغلاق</button>
      </div>
    </div>
    <div class="table-wrap" style="max-height:68vh;overflow-y:auto;">
      <table style="width:100%;border-collapse:collapse;font-family:Arial,sans-serif;font-size:13px;">
        <thead>
          <tr>
            <th style="background:#000080 !important;color:#ffffff !important;padding:8px;border:1px solid #999;">كود الفرع</th>
            <th style="background:#000080 !important;color:#ffffff !important;padding:8px;border:1px solid #999;">رقم الحساب</th>
            <th style="background:#000080 !important;color:#ffffff !important;padding:8px;border:1px solid #999;">أسم العميل</th>
            <th style="background:#000080 !important;color:#ffffff !important;padding:8px;border:1px solid #999;">المبلغ</th>
            <th style="background:#000080 !important;color:#ffffff !important;padding:8px;border:1px solid #999;">رقم الموظف</th>
            <th style="background:#000080 !important;color:#ffffff !important;padding:8px;border:1px solid #999;">كود البنك ( ثابت )</th>
            <th style="background:#f8fafc !important;color:#000 !important;padding:8px;border:1px solid #cbd5e1;">نوع التحويل</th>
            <th style="background:#f8fafc !important;color:#000 !important;padding:8px;border:1px solid #cbd5e1;">اللقب / الشهرة</th>
          </tr>
        </thead>
        <tbody>${trs}</tbody>
      </table>
    </div>
  `, 'modal-xl');
}
window.openNbeBankSheetModal = openNbeBankSheetModal;
