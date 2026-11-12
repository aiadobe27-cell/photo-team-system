// ============================================================================
// 📌 ملف الكود البرمجي (app.js): المحرك الأساسي للواجهة (الإشعارات، المساعد الذكي والمايك الصوتي، الطباعة الحرارية POS، وتبديل المظهر الفاتح والداكن)
// ============================================================================

const $=(id)=>document.getElementById(id);
// Visual themes only. Business logic / API behavior is untouched.
const UI_THEMES=[
  ['dark','Dark Classic'],
  ['pearl','Pearl Light'],
  ['slate','Cloud Slate']
];
function applyTheme(name,notify=false){
  const found=UI_THEMES.find(x=>x[0]===name)||UI_THEMES[1];
  const sheet=document.getElementById('lightThemeSheet');
  document.body.dataset.theme=found[0];
  if(sheet) sheet.disabled=(found[0]==='dark');
  localStorage.setItem('phototeam_theme',found[0]);
  localStorage.removeItem('phototeam_light_theme');
  if($('themeName')) $('themeName').textContent=found[1];
  if($('themeSelect')) $('themeSelect').value=found[0];
  if(notify) toast(`تم تطبيق ستايل ${found[1]}`,'good');
}
function cycleTheme(){
  const current=document.body.dataset.theme||localStorage.getItem('phototeam_theme')||'pearl';
  const i=UI_THEMES.findIndex(x=>x[0]===current);
  applyTheme(UI_THEMES[(i+1)%UI_THEMES.length][0],true);
}
// Backward-compatible alias for V4 buttons if a cached template is opened.
function cycleLightTheme(){cycleTheme()}
const legacy=localStorage.getItem('phototeam_light_theme');
applyTheme(localStorage.getItem('phototeam_theme')||(legacy?'pearl':'pearl'));

const $$=(sel)=>Array.from(document.querySelectorAll(sel));
const esc=(v)=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
const escapeHtml=esc;window.esc=esc;window.escapeHtml=esc;
const money=(v,d=2)=>Number(v||0).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});
const todayISO=()=>new Date().toISOString().slice(0,10);
const monthISO=()=>new Date().toISOString().slice(0,7);
const firstDayMonth=()=>monthISO()+'-01';
const num=(v)=>Number(v||0)||0;
async function api(url,options={}){options.headers=Object.assign({'ngrok-skip-browser-warning':'true'},options.headers||{});const res=await fetch(url,options);let data={};try{data=await res.json()}catch(e){}if(res.status===401){location.href='/login';throw new Error('انتهت الجلسة')}if(!res.ok||data.ok===false)throw new Error(data.error||`خطأ ${res.status}`);return data.data??data}
async function apiJSON(url,method='POST',body={}){
  if (isOfflineModeActive() && ['POST','PUT'].includes(String(method).toUpperCase()) && !String(url).includes('/api/auth/')) {
    const item = enqueueOfflineOperation(url, method, body);
    return { queued_offline: true, id: item.id };
  }
  try {
    const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' }, body: JSON.stringify(body) });
    let data = {};
    try { data = await res.json(); } catch(e) {}
    if (res.status === 423 && data.locked) {
      if (typeof window.openRequestDayUnlockModal === 'function') {
        window.openRequestDayUnlockModal(data.lock_date, data.hotel_name, data.room_number, body);
      }
      throw new Error(data.error || '🔒 حسابات هذا اليوم مقفولة ومعتمدة من المحاسب');
    }
    if (res.status === 401) { location.href = '/login'; throw new Error('انتهت الجلسة'); }
    if (!res.ok || data.ok === false) throw new Error(data.error || `خطأ ${res.status}`);
    return data.data ?? data;
  } catch (err) {
    if (err instanceof TypeError && ['POST','PUT'].includes(String(method).toUpperCase()) && !String(url).includes('/api/auth/')) {
      const item = enqueueOfflineOperation(url, method, body);
      return { queued_offline: true, id: item.id };
    }
    throw err;
  }
}
async function apiSafe(url,fallback,label=''){try{return await api(url)}catch(e){console.error(label||url,e);toast((label?label+': ':'')+e.message,'bad');return fallback}}
function toast(message,type='good'){const d=document.createElement('div');d.className=`toast ${type}`;d.textContent=message;($('toastStack')||document.body).appendChild(d);setTimeout(()=>d.remove(),3500)}
function statusBadge(status){const s=String(status||'').toLowerCase();let c='blue';if(s.includes('مؤكد')||s.includes('confirm')||s.includes('deliver')||s.includes('تسليم')||s.includes('متاح')||s.includes('تم الإصلاح'))c='green';else if(s.includes('انتظار')||s.includes('pending')||s.includes('صيانة')||s.includes('تأجيل')||s.includes('تقديم'))c='amber';else if(s.includes('كنسل')||s.includes('cancel')||s.includes('ملغ')||s.includes('تالف')||s.includes('معطل'))c='red';return `<span class="badge ${c}">${esc(status||'-')}</span>`}
function showModal(html,size='modal-xl'){const m=$('globalModal');const card=m.querySelector('.modal-card');card.className=`modal-card ${size}`;$('globalModalBody').innerHTML=html;m.hidden=false;return $('globalModalBody')}
function closeModal(){if($('globalModal'))$('globalModal').hidden=true}
function confirmAction(msg){return window.confirm(msg)}
function buildModernExcelSpreadsheetHtml(titleText, headers = [], rows = []) {
  const safeHeaders = (headers || []).map(h => String(h ?? ''));
  const safeRows = Array.isArray(rows) ? rows : [];
  const colSums = safeHeaders.map(() => 0);
  const colHasNumeric = safeHeaders.map(() => false);

  safeRows.forEach(r => {
    (r || []).forEach((cell, idx) => {
      if (idx === 0) return; // عمود المسلسل أو الكود الأول لا يُجمع
      const hName = String(safeHeaders[idx] || '');
      if (hName.includes('غرفة') || hName.includes('تاريخ') || hName.includes('تليفون') || hName.includes('هاتف') || hName.includes('نسبة') || hName.includes('سعر الصرف') || hName.includes('الريت')) return;
      const cleaned = String(cell ?? '').replace(/[,$€£EGPLE%\s]/gi, '').trim();
      if (cleaned !== '' && !isNaN(Number(cleaned)) && /^-?\d+(\.\d+)?$/.test(cleaned)) {
        colSums[idx] += Number(cleaned);
        colHasNumeric[idx] = true;
      }
    });
  });

  const hasAnySum = colHasNumeric.some(Boolean);
  const headerCellsHtml = safeHeaders.map(h =>
    `<th style="background-color:#1e3a8a;color:#ffffff;font-weight:bold;font-size:11.5pt;padding:10px 12px;border:1px solid #1e40af;text-align:center;">${esc(h)}</th>`
  ).join('');

  const bodyRowsHtml = safeRows.map((r, rIdx) => {
    const bg = rIdx % 2 === 0 ? '#ffffff' : '#f1f5f9';
    const tds = (r || []).map((cell, cIdx) => {
      const s = String(cell ?? '');
      const isMoney = s.includes('$') || s.includes('€') || s.includes('LE') || colHasNumeric[cIdx];
      const color = isMoney ? '#0f766e' : '#0f172a';
      const weight = (cIdx <= 2 || isMoney) ? 'bold' : 'normal';
      return `<td style="background-color:${bg};color:${color};font-weight:${weight};font-size:10.5pt;padding:8px 10px;border:1px solid #cbd5e1;text-align:center;">${esc(s)}</td>`;
    }).join('');
    return `<tr>${tds}</tr>`;
  }).join('');

  const footerRowHtml = hasAnySum ? `
    <tr>
      ${safeHeaders.map((_, cIdx) => {
        if (cIdx === 0) {
          return `<td style="background-color:#dbeafe;color:#1e3a8a;font-weight:bold;font-size:11pt;padding:10px;border:2px solid #2563eb;text-align:center;">الإجمالي</td>`;
        }
        if (colHasNumeric[cIdx]) {
          return `<td style="background-color:#ecfdf5;color:#047857;font-weight:bold;font-size:11pt;padding:10px;border:2px solid #10b981;text-align:center;">${money(colSums[cIdx])}</td>`;
        }
        return `<td style="background-color:#dbeafe;color:#64748b;font-weight:bold;padding:10px;border:1px solid #93c5fd;text-align:center;">—</td>`;
      }).join('')}
    </tr>
  ` : '';

  const colCount = Math.max(safeHeaders.length, 1);
  return `<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40" dir="rtl" lang="ar">
<head>
<meta charset="utf-8">
<!--[if gte mso 9]><xml><x:ExcelWorkbook><x:ExcelWorksheets><x:ExcelWorksheet><x:Name>PHOTO TEAM</x:Name><x:WorksheetOptions><x:DisplayRightToLeft/><x:DisplayGridlines/></x:WorksheetOptions></x:ExcelWorksheet></x:ExcelWorksheets></x:ExcelWorkbook></xml><![endif]-->
<style>
  body, table, th, td { font-family: 'Cairo', 'Segoe UI', Tahoma, Arial, sans-serif; direction: rtl; }
  table { border-collapse: collapse; width: 100%; }
</style>
</head>
<body>
  <table>
    <tr>
      <td colspan="${colCount}" style="background-color:#0f172a;color:#ffffff;font-size:15pt;font-weight:bold;padding:14px;text-align:center;border:1px solid #0f172a;">
        📸 PHOTO TEAM STUDIO SYSTEM — ${esc(titleText)}
      </td>
    </tr>
    <tr>
      <td colspan="${colCount}" style="background-color:#eff6ff;color:#1e3a8a;font-size:10.5pt;font-weight:bold;padding:8px 12px;text-align:center;border:1px solid #bfdbfe;">
        تاريخ الاستخراج: ${todayISO()} • إجمالي السجلات: ${safeRows.length} سجل
      </td>
    </tr>
    <tr>${headerCellsHtml}</tr>
    ${bodyRowsHtml}
    ${footerRowHtml}
  </table>
</body>
</html>`;
}
window.buildModernExcelSpreadsheetHtml = buildModernExcelSpreadsheetHtml;

async function downloadCSV(filename, headers = [], rows = []) {
  const baseStem = String(filename || 'PhotoTeam_Export').replace(/\.(csv|xls|xlsx)$/i, '');
  const xlsFilename = `${baseStem}.xls`;
  const titleLabel = baseStem.replace(/_/g, ' ');
  const styledExcelHtml = buildModernExcelSpreadsheetHtml(titleLabel, headers, rows);

  // 1) تنزيل ملف إكسيل منسق ومودرن (.xls) يعمل مباشرة في Microsoft Excel بالألوان والجدول المنسق
  try {
    const blob = new Blob(['\ufeff' + styledExcelHtml], { type: 'application/vnd.ms-excel;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = xlsFilename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      URL.revokeObjectURL(url);
      a.remove();
    }, 2000);
  } catch (e) {}

  // 2) حفظ مباشر عبر الباك إند في مجلد Downloads و exports
  if (location.protocol.startsWith('http')) {
    try {
      const res = await apiJSON('/api/export/excel', 'POST', {
        filename: xlsFilename,
        headers: headers,
        rows: rows,
        styled_html: styledExcelHtml
      });
      if (res && res.saved_to) {
        toast(`📥 تم تصدير شيت الإكسيل المنسق (${xlsFilename}) في: ${res.saved_to}`);
        return;
      }
    } catch (err) {}
  }
  toast(`📥 تم تحميل شيت الإكسيل المنسق (${xlsFilename}) بنجاح`);
}
window.downloadCSV = downloadCSV;

function openQuickChangePasswordModal() {
  showModal(`
    <div class="modal-title">
      <div>
        <h2>🔑 تغيير كلمة المرور الخاصة بالحساب</h2>
        <p>أدخل كلمة المرور الجديدة لحسابك وسيتم تحديثها فوراً</p>
      </div>
      <button type="button" class="btn" onclick="closeModal()">إغلاق</button>
    </div>
    <form id="selfChangePassForm" style="display:flex;flex-direction:column;gap:12px;">
      <div class="field">
        <label>كلمة المرور الجديدة *</label>
        <input class="input" type="password" id="scpNewPass" placeholder="4 أحرف أو أرقام على الأقل" required minlength="4">
      </div>
      <div class="field">
        <label>تأكيد كلمة المرور الجديدة *</label>
        <input class="input" type="password" id="scpConfirmPass" placeholder="أعد كتابة كلمة المرور الجديدة" required minlength="4">
      </div>
      <div class="modal-actions">
        <button type="submit" class="btn green">💾 حفظ كلمة المرور الجديدة</button>
        <button type="button" class="btn" onclick="closeModal()">إلغاء</button>
      </div>
    </form>
  `, 'modal-md');
  $('selfChangePassForm')?.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const p1 = $('scpNewPass')?.value || '';
    const p2 = $('scpConfirmPass')?.value || '';
    if (p1.length < 4) return toast('كلمة المرور يجب ألا تقل عن 4 أحرف أو أرقام', 'bad');
    if (p1 !== p2) return toast('كلمة المرور وتأكيدها غير متطابقين', 'bad');
    try {
      await apiJSON('/api/auth/change-password', 'POST', { new_password: p1 });
      closeModal();
      toast('✅ تم تحديث كلمة المرور بنجاح!');
    } catch (e) {
      toast(e.message || 'تعذر تغيير كلمة المرور', 'bad');
    }
  });
}
window.openQuickChangePasswordModal = openQuickChangePasswordModal;
// ============================================================================
// 📄 BUILT-IN REPORT & PDF VIEWER + INTERNAL IFRAME PRINTER (NO window.open('_blank'))
// يعالج مشكلة "برجاء اختيار البرنامج للعرض" في ويندوز و pywebview نهائياً
// ============================================================================
let _LAST_REPORT_HTML_DOC = '';
let _LAST_REPORT_TITLE = 'Report';

function getOrCreateInternalPrintIframe() {
  let frame = document.getElementById('ptInternalPrintFrame');
  if (!frame) {
    frame = document.createElement('iframe');
    frame.id = 'ptInternalPrintFrame';
    frame.style.cssText = 'position:fixed;right:-9999px;bottom:-9999px;width:900px;height:700px;border:0;opacity:0;pointer-events:none;z-index:-1;';
    document.body.appendChild(frame);
  }
  return frame;
}

function printHtmlViaInternalIframe(fullHtmlDoc) {
  const htmlToPrint = fullHtmlDoc || _LAST_REPORT_HTML_DOC;
  if (!htmlToPrint) return window.print();
  const isLandscape = String(htmlToPrint).includes('landscape');
  triggerDirectInPagePrint(htmlToPrint, isLandscape ? 'A4 landscape' : 'A4 portrait');
}

function downloadCurrentReportHtmlFile() {
  if (!_LAST_REPORT_HTML_DOC) return;
  const safeName = String(_LAST_REPORT_TITLE || 'PhotoTeam_Report').replace(/[^\w\u0600-\u06FF\-]+/g, '_');
  const blob = new Blob([_LAST_REPORT_HTML_DOC], { type: 'text/html;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${safeName}.html`;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    URL.revokeObjectURL(a.href);
    a.remove();
  }, 500);
  toast('📥 تم حفظ ملف التقرير بنجاح');
}

function openBuiltInReportViewer(fullHtmlDoc, title = 'معاينة التقرير وطباعة PDF', autoTriggerPrint = false) {
  _LAST_REPORT_HTML_DOC = fullHtmlDoc;
  _LAST_REPORT_TITLE = title;
  showModal(`
    <div class="modal-title" style="flex-direction:row !important;justify-content:space-between !important;align-items:center !important;flex-wrap:wrap;gap:10px;">
      <div>
        <h2>📄 ${esc(title)}</h2>
        <p>عارض التقارير المدمج داخل النظام (يعمل مباشرة بدون الحاجة لأي برنامج خارجي)</p>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;">
        <button type="button" class="btn green" onclick="printHtmlViaInternalIframe()">🖨️ طباعة / حفظ PDF الآن</button>
        <button type="button" class="btn primary" onclick="downloadCurrentReportHtmlFile()">📥 حفظ نسخة من التقرير</button>
        <button type="button" class="btn" onclick="closeModal()">إغلاق</button>
      </div>
    </div>
    <div style="background:#f1f5f9;padding:12px;border-radius:16px;border:1px solid var(--border);height:72vh;display:flex;flex-direction:column;">
      <iframe id="inAppReportPreviewFrame" style="width:100%;height:100%;border:1px solid #cbd5e1;border-radius:10px;background:#ffffff;"></iframe>
    </div>
  `, 'modal-xxl');

  const previewFrame = document.getElementById('inAppReportPreviewFrame');
  if (previewFrame && previewFrame.contentWindow) {
    const pdoc = previewFrame.contentWindow.document;
    pdoc.open();
    pdoc.write(fullHtmlDoc);
    pdoc.close();
  }
  if (autoTriggerPrint) {
    setTimeout(() => printHtmlViaInternalIframe(fullHtmlDoc), 350);
  }
}

function printHTML(title, html) {
  const fullDoc = `<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>${esc(title)}</title><style>
    @page { size: A4 portrait; margin: 12mm; }
    body { font-family: 'Cairo', 'Segoe UI', Tahoma, Arial, sans-serif; padding: 24px; color: #0f172a; background: #ffffff; direction: rtl; }
    h1 { font-size: 20px; color: #1e3a8a; border-bottom: 2px solid #2563eb; padding-bottom: 8px; margin-top: 0; }
    table { width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 13px; }
    th, td { border: 1px solid #cbd5e1; padding: 8px; text-align: center; }
    th { background: #1e3a8a; color: #ffffff; font-weight: bold; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    tr:nth-child(even) td { background: #f8fafc; }
    .sign { display: flex; justify-content: space-between; margin-top: 45px; font-weight: bold; padding: 0 30px; }
    .print-btn { display: none !important; }
  </style></head><body><h1>${esc(title)}</h1>${html}</body></html>`;
  openBuiltInReportViewer(fullDoc, title, false);
}
function initLogicTabs(root=document){root.querySelectorAll('[data-tab-group]').forEach(group=>{const buttons=group.querySelectorAll('[data-tab-target]');buttons.forEach(btn=>btn.addEventListener('click',()=>{buttons.forEach(x=>x.classList.remove('active'));btn.classList.add('active');const scope=group.parentElement;scope.querySelectorAll('.tab-pane').forEach(p=>p.classList.toggle('active',p.id===btn.dataset.tabTarget));btn.dispatchEvent(new CustomEvent('tabshown'))}))})}
async function logout(){try{await api('/api/auth/logout',{method:'POST'})}catch(e){}location.href='/login'}
function updateClock(){const d=new Date();if($('sideDate'))$('sideDate').textContent=d.toLocaleDateString('ar-EG',{weekday:'long',year:'numeric',month:'long',day:'numeric'});if($('sideClock'))$('sideClock').textContent=d.toLocaleTimeString('en-GB');if($('footerClock'))$('footerClock').textContent=d.toLocaleTimeString('en-GB')}setInterval(updateClock,1000);updateClock();
async function checkHealth(){try{await api('/api/health');if($('dbStatus'))$('dbStatus').textContent='● متصل بقاعدة البيانات'}catch(e){if($('dbStatus')){$('dbStatus').textContent='● غير متصل';$('dbStatus').style.color='#ef414b'}}}checkHealth();
$('mobileMenuBtn')?.addEventListener('click',()=>$('sidebar')?.classList.toggle('open'));
const commandItems=[
  ['الرئيسية','/',null],
  ['إدارة الحجوزات','/reservations','bookings_access'],
  ['غرفة العمليات والتشغيل','/control-room','bookings_access'],
  ['الدخل اليومي والمبيعات','/daily-sales','sales_access'],
  ['العمولات والبونص','/commissions','sales_access'],
  ['عهدة المعدات والفساتين','/assets','assets_access'],
  ['متابعة المغسلة','/laundry','laundry_access'],
  ['حساب وصرف المرتبات','/salaries','finances_access'],
  ['التقارير الشاملة','/reports','finances_access'],
  ['الفريق والفنادق','/team-hotels','team_access'],
  ['الإعدادات العامة','/settings','finances_access']
];
function canAccessCmd(perm){
  if(!perm||window.FULL_ACCESS)return true;
  return Array.isArray(window.USER_PERMISSIONS)&&window.USER_PERMISSIONS.includes(perm);
}
function renderCommands(q=''){const h=$('commandList');if(h)h.innerHTML=commandItems.filter(x=>canAccessCmd(x[2])&&x[0].includes(q)).map(x=>`<a href="${x[1]}"><b>${x[0]}</b><span>↵</span></a>`).join('')}
function openCommand(){$('commandOverlay').hidden=false;renderCommands();setTimeout(()=>$('commandInput')?.focus(),10)}function closeCommand(){if($('commandOverlay'))$('commandOverlay').hidden=true}
$('commandInput')?.addEventListener('input',e=>renderCommands(e.target.value));$('commandOverlay')?.addEventListener('click',e=>{if(e.target.id==='commandOverlay')closeCommand()});document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openCommand()}if(e.key==='Escape'){closeCommand();closeModal()}});
let ALL_NOTIFICATIONS_CACHE = [];
let ACTIVE_NOTIF_FILTER = 'all';
let LAST_SEEN_NOTIF_ID = Number(localStorage.getItem('pt_last_notif_id') || 0);

function playNotifChime(){
  try{
    const ctx=new (window.AudioContext||window.webkitAudioContext)();
    const osc=ctx.createOscillator(),gain=ctx.createGain();
    osc.type='sine';osc.frequency.setValueAtTime(587.33,ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(880,ctx.currentTime+0.16);
    gain.gain.setValueAtTime(0.08,ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001,ctx.currentTime+0.35);
    osc.connect(gain);gain.connect(ctx.destination);
    osc.start();osc.stop(ctx.currentTime+0.36);
  }catch(e){}
}

function notificationIcon(r){
  const t=(String(r.notification_type||'')+' '+String(r.title||'')).toLowerCase();
  if(t.includes('broadcast')||t.includes('تعميم')||t.includes('📢'))return '📢';
  if(t.includes('deposit')||t.includes('عربون')||t.includes('sale')||t.includes('دخل'))return '💰';
  if(t.includes('bonus')||t.includes('مكافأ'))return '🏆';
  if(t.includes('deduction')||t.includes('خصم')||t.includes('سلفة'))return '🏷️';
  if(t.includes('payroll')||t.includes('مرتب')||t.includes('مستحقات'))return '💳';
  if(t.includes('مغسل'))return '🧺';
  if(t.includes('معدات')||t.includes('عهد'))return '📷';
  if(t.includes('booking')||t.includes('حجز')||t.includes('أوردر')||t.includes('checkout'))return '📸';
  return '🔔';
}

function notificationCategory(r){
  const t=(String(r.notification_type||'')+' '+String(r.title||'')).toLowerCase();
  if(t.includes('broadcast')||t.includes('تعميم'))return 'broadcast';
  if(t.includes('deposit')||t.includes('sale')||t.includes('bonus')||t.includes('deduction')||t.includes('payroll')||t.includes('عربون')||t.includes('دخل')||t.includes('مرتب')||t.includes('خصم'))return 'finance';
  if(t.includes('booking')||t.includes('checkout')||t.includes('حجز')||t.includes('أوردر')||t.includes('عهد')||t.includes('مغسل'))return 'ops';
  return 'all';
}

function canApprovePending(){return !!window.FULL_ACCESS||(window.USER_PERMISSIONS||[]).includes('finances_access')}
function canSendBroadcast(){return !window.PERSONAL_SCOPE && (!!window.FULL_ACCESS||(window.USER_PERMISSIONS||[]).length>0)}

function notificationMoney(r){
  if(r.notification_type!=='pending_deposit')return '';
  const a=[];
  if(num(r.pending_usd))a.push(`<b class="currency-usd">$${money(r.pending_usd)}</b>`);
  if(num(r.pending_eur))a.push(`<b class="currency-eur">€${money(r.pending_eur)}</b>`);
  const egp=num(r.pending_cash)+num(r.pending_visa);
  if(egp)a.push(`<b class="currency-egp">${money(egp)} EGP</b>`);
  return a.length?`<div class="notif-money">${a.join(' + ')}</div>`:'';
}

async function markNotificationRead(id){try{await api(`/api/notifications/${id}/read`,{method:'POST'})}catch(e){}refreshNotificationCount()}
async function markAllNotificationsRead(){
  try{
    await api('/api/notifications/read-all',{method:'POST'});
    toast('✓ تم تعليم جميع الإشعارات كمقروءة');
    const x=await refreshNotificationCount();
    ALL_NOTIFICATIONS_CACHE=x.rows||[];
    renderNotificationsList();
  }catch(e){toast(e.message,'bad')}
}
async function deleteNotificationItem(id,ev){
  if(ev)ev.stopPropagation();
  try{
    await api(`/api/notifications/${id}`,{method:'DELETE'});
    ALL_NOTIFICATIONS_CACHE=ALL_NOTIFICATIONS_CACHE.filter(x=>x.id!==id);
    renderNotificationsList();
    refreshNotificationCount();
  }catch(e){toast(e.message,'bad')}
}
async function goToNotification(id,url){await markNotificationRead(id);closeModal();location.href=url||'/'}
async function confirmPendingDeposit(id){if(!confirmAction('هل استلمت مبلغ العربون نقداً من السيلز وتريد تأكيده وترحيله الآن إلى خانة الدخل اليومي؟'))return;try{await apiJSON(`/api/pending-deposits/${id}/confirm`,'POST',{});toast('✅ تم تأكيد استلام العربون وترحيله مباشرة إلى خانة الدخل اليومي!');await refreshNotificationCount();openNotifications();if(typeof loadSalesSearch==='function')loadSalesSearch();if(typeof loadEligible==='function')loadEligible();}catch(e){toast(e.message,'bad')}}
async function rejectPendingDeposit(id){if(!confirmAction('رفض ترحيل هذا العربون؟ لن يدخل حركة العرابين.'))return;try{await apiJSON(`/api/pending-deposits/${id}/reject`,'POST',{});toast('تم رفض ترحيل العربون','good');await refreshNotificationCount();openNotifications()}catch(e){toast(e.message,'bad')}}

function renderNotificationCard(r){
  const unread=String(r.status||'').toLowerCase()!=='read';
  const pending=r.notification_type==='pending_deposit'&&String(r.pending_deposit_status||'')==='Pending';
  const prioBadge=r.priority==='critical'?'<span class="badge red">عاجل 🔴</span>':r.priority==='high'?'<span class="badge amber">هام 🟠</span>':'';
  const targetBadge=r.target_employee?`<span class="badge blue">👤 ${esc(r.target_employee)}</span>`:r.target_role&&r.target_role!=='all'?`<span class="badge blue">👥 ${esc(r.target_role)}</span>`:'';
  const actions=pending&&canApprovePending()?`<div class="notif-actions" style="margin-top:8px;padding:8px 10px;background:#fffbeb;border:1px solid #f59e0b;border-radius:10px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;"><span style="font-size:11.5px;font-weight:800;color:#b45309;">⏳ عربون معلق مع السيلز — يبقى معلقاً حتى استلام النقدية وتأكيدك:</span><div style="display:flex;gap:6px;"><button class="btn green" style="min-height:32px;padding:4px 12px;font-size:12px;" onclick="event.stopPropagation();confirmPendingDeposit(${r.pending_deposit_id})">💵 استلمت الفلوس — تأكيد وترحيل للدخل ✅</button><button class="mini-btn red" onclick="event.stopPropagation();rejectPendingDeposit(${r.pending_deposit_id})">✕ رفض</button><button class="mini-btn blue" onclick="event.stopPropagation();goToNotification(${r.id},'${String(r.target_url||'/').replaceAll("'","\\'")}')">فتح الحجز</button></div></div>`:(pending?`<div style="margin-top:6px;"><span class="badge amber">⏳ معلق في إشعارات المدير لحين تسليم النقدية واعتمادها</span></div>`:'');
  const resolved=r.notification_type==='pending_deposit'&&!pending?`<div class="notif-actions">${statusBadge(r.pending_deposit_status||'تم التعامل')}</div>`:'';
  return `<div class="notification-card ${unread?'unread':''} ${r.priority==='critical'?'notif-critical':''}" onclick="goToNotification(${r.id},'${String(r.target_url||'/').replaceAll("'","\\'")}')">
    <span class="notif-icon">${notificationIcon(r)}</span>
    <div>
      <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
        <h3>${esc(r.title||'إشعار')}</h3>
        ${prioBadge}${targetBadge}
        ${unread?'<span class="badge green" style="padding:2px 7px;font-size:10px;">جديد</span>':''}
      </div>
      <p>${esc(r.message||'')}</p>
      ${notificationMoney(r)}${actions}${resolved}
    </div>
    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;">
      <time>${esc(r.created_at||'')}</time>
      <button class="mini-btn red" title="حذف الإشعار" onclick="deleteNotificationItem(${r.id},event)" style="width:24px;height:24px;padding:0;font-size:11px;">×</button>
    </div>
  </div>`;
}

function filterNotificationsByTab(tabKey){
  ACTIVE_NOTIF_FILTER=tabKey;
  $$('.notif-filter-tab').forEach(b=>b.classList.toggle('active',b.dataset.nfilter===tabKey));
  renderNotificationsList();
}

function renderNotificationsList(){
  const host=$('notifHost');
  if(!host)return;
  const rows=ALL_NOTIFICATIONS_CACHE.filter(r=>{
    if(ACTIVE_NOTIF_FILTER==='unread')return String(r.status||'').toLowerCase()!=='read';
    if(ACTIVE_NOTIF_FILTER==='ops')return notificationCategory(r)==='ops';
    if(ACTIVE_NOTIF_FILTER==='finance')return notificationCategory(r)==='finance';
    if(ACTIVE_NOTIF_FILTER==='broadcast')return notificationCategory(r)==='broadcast';
    return true;
  });
  host.innerHTML=rows.map(renderNotificationCard).join('')||'<div class="empty-state">لا توجد إشعارات في هذا التصنيف</div>';
}

async function refreshNotificationCount(){
  try{
    const x=await api('/api/notifications');
    const rows=x.rows||[];
    const c=$('notifCount');
    if(c){c.textContent=x.unread||0;c.dataset.zero=(x.unread||0)?'0':'1'}
    // تنبيه فوري بالصوت والـ Toast عند وصول إشعار جديد غير مقروء
    const newestUnread=rows.find(r=>String(r.status||'').toLowerCase()!=='read');
    if(newestUnread && Number(newestUnread.id)>LAST_SEEN_NOTIF_ID){
      if(LAST_SEEN_NOTIF_ID>0){
        playNotifChime();
        toast(`🔔 ${newestUnread.title}: ${String(newestUnread.message||'').slice(0,70)}`,'good');
      }
      LAST_SEEN_NOTIF_ID=Number(newestUnread.id);
      try{localStorage.setItem('pt_last_notif_id',String(LAST_SEEN_NOTIF_ID))}catch(e){}
    }
    return x;
  }catch(e){return {rows:[],unread:0}}
}

async function openBroadcastComposer(){
  const teamOpts=await apiSafe('/api/team/options',{all:[]},'');
  const emps=(teamOpts.all||[]).map(x=>`<option value="${esc(x.nickname)}">${esc(x.nickname)} (${esc(x.role||'')})</option>`).join('');
  const box=$('broadcastComposerBox');
  if(!box)return;
  box.hidden=!box.hidden;
  if(!box.innerHTML){
    box.innerHTML=`
      <form id="broadcastForm" style="background:var(--bg-surface-2);border:1px solid var(--border-strong);border-radius:14px;padding:14px;margin-bottom:14px;">
        <h3 style="margin:0 0 10px;font-size:14px;color:var(--text-heading);">📢 إرسال إشعار أو تعميم إداري فوري</h3>
        <div class="form-grid three" style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:10px;">
          <div class="field"><label>توجيه إلى</label><select class="input" id="bcTargetType" onchange="toggleBcTarget()"><option value="all">🌐 كل الفريق</option><option value="role">👥 قسم / وظيفة محددة</option><option value="employee">👤 موظف محدد بالاسم</option></select></div>
          <div class="field" id="bcRoleWrap" hidden><label>اختر القسم</label><select class="input" id="bcRole"><option value="Sales">Sales / المبيعات</option><option value="Photographer">Photographer / المصورين</option><option value="Accountant">Accountant / الحسابات</option><option value="Manager">Manager / المديرين</option></select></div>
          <div class="field" id="bcEmpWrap" hidden><label>اختر الموظف</label><select class="input" id="bcEmp">${emps}</select></div>
          <div class="field"><label>الأهمية</label><select class="input" id="bcPriority"><option value="normal">🔵 عادي</option><option value="high">🟠 هام</option><option value="critical">🔴 عاجل جداً</option></select></div>
        </div>
        <div class="form-grid two" style="display:grid;grid-template-columns:1fr 2fr;gap:10px;">
          <div class="field"><label>عنوان الإشعار *</label><input class="input" id="bcTitle" placeholder="مثال: اجتماع شيفت المساء" required></div>
          <div class="field"><label>نص التعميم / الرسالة *</label><input class="input" id="bcMsg" placeholder="اكتب تفاصيل التعميم أو التوجيه..." required></div>
        </div>
        <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:10px;">
          <button type="button" class="btn" onclick="$('broadcastComposerBox').hidden=true">إلغاء</button>
          <button type="submit" class="btn primary">🚀 إرسال الإشعار الآن</button>
        </div>
      </form>
    `;
    $('broadcastForm').addEventListener('submit',async e=>{
      e.preventDefault();
      try{
        await apiJSON('/api/notifications/broadcast','POST',{
          target_type:$('bcTargetType').value,
          target_role:$('bcRole')?.value,
          target_employee:$('bcEmp')?.value,
          priority:$('bcPriority').value,
          title:$('bcTitle').value,
          message:$('bcMsg').value
        });
        toast('📢 تم إرسال التعميم / الإشعار بنجاح');
        $('broadcastComposerBox').hidden=true;
        const x=await refreshNotificationCount();
        ALL_NOTIFICATIONS_CACHE=x.rows||[];
        renderNotificationsList();
      }catch(err){toast(err.message,'bad')}
    });
  }
}

function toggleBcTarget(){
  const t=$('bcTargetType')?.value;
  if($('bcRoleWrap'))$('bcRoleWrap').hidden=(t!=='role');
  if($('bcEmpWrap'))$('bcEmpWrap').hidden=(t!=='employee');
}

async function openNotifications(){
  showModal(`
    <div class="modal-title" style="flex-direction:row !important;justify-content:space-between !important;align-items:center !important;flex-wrap:wrap;gap:10px;">
      <div>
        <h2>🔔 مركز الإشعارات والتنبيهات الذكي</h2>
        <p>تنبيهات الأوردرات، العرابين، المبيعات، المرتبات، وتعاميم الإدارة (مخصصة حسب صلاحيتك)</p>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;">
        ${canSendBroadcast()?`<button class="btn primary" style="min-height:34px;padding:6px 12px;font-size:12px;" onclick="openBroadcastComposer()">📢 إرسال إشعار / تعميم</button>`:''}
        <button class="btn" style="min-height:34px;padding:6px 12px;font-size:12px;" onclick="markAllNotificationsRead()">✓ تعليم الكل كمقروء</button>
      </div>
    </div>
    <div id="broadcastComposerBox" hidden></div>
    <div class="logic-tabs" style="margin-bottom:12px;">
      <button class="logic-tab notif-filter-tab active" data-nfilter="all" onclick="filterNotificationsByTab('all')">الكل</button>
      <button class="logic-tab notif-filter-tab" data-nfilter="unread" onclick="filterNotificationsByTab('unread')">🔴 غير مقروء</button>
      <button class="logic-tab notif-filter-tab" data-nfilter="ops" onclick="filterNotificationsByTab('ops')">📸 الأوردرات والميدان</button>
      <button class="logic-tab notif-filter-tab" data-nfilter="finance" onclick="filterNotificationsByTab('finance')">💰 المالية والمبيعات</button>
      <button class="logic-tab notif-filter-tab" data-nfilter="broadcast" onclick="filterNotificationsByTab('broadcast')">📢 تعاميم الإدارة</button>
    </div>
    <div id="notifHost" class="timeline-list" style="max-height:58vh;overflow-y:auto;"><div class="empty-state">جاري التحميل...</div></div>
  `,'modal-xl');
  try{
    const x=await refreshNotificationCount();
    ALL_NOTIFICATIONS_CACHE=x.rows||[];
    ACTIVE_NOTIF_FILTER='all';
    renderNotificationsList();
  }catch(e){toast(e.message,'bad')}
}



refreshNotificationCount();setInterval(refreshNotificationCount,15000);

// V7 — global financial currency colorizer. UI only; no values or calculations are changed.
const CURRENCY_CLASS_NAMES=['currency-usd','currency-eur','currency-egp'];
function detectCurrencyType(text=''){
  const t=String(text||'').replace(/\s+/g,' ').trim().toLowerCase();
  if(!t) return '';
  // Order matters: Coin safe is EUR; LE/EGP comes before generic finance wording.
  if(t.includes('€') || /\b(eur|euro)\b/.test(t) || t.includes('يورو') || t.includes('كوين')) return 'eur';
  if(/\bl\.?e\.?\b/i.test(t) || /\begp\b/i.test(t) || t.includes('ج.م') || t.includes('ج م') || t.includes('مصري')) return 'egp';
  if(t.includes('$') || /\busd\b/i.test(t) || t.includes('دولار')) return 'usd';
  return '';
}
function setCurrencyClass(el,type){
  if(!el) return;
  CURRENCY_CLASS_NAMES.forEach(c=>el.classList.remove(c));
  if(type) el.classList.add(`currency-${type}`);
}
function colorizeFinancialCurrencies(root=document){
  const scope=(root && root.querySelectorAll)?root:document;

  // 1) Tables: detect currency from the column header and color the whole column.
  scope.querySelectorAll('table').forEach(table=>{
    const headers=Array.from(table.querySelectorAll('thead tr:first-child th'));
    headers.forEach((th,index)=>{
      let type=detectCurrencyType(th.textContent);
      // Reservation totals/remaining are USD in the original ReservationWindow logic.
      if(table.id==='bookingTable' && (index===15 || index===16)) type='usd';
      if(!type) return;
      setCurrencyClass(th,type);
      table.querySelectorAll('tbody tr').forEach(tr=>setCurrencyClass(tr.children[index],type));
    });
  });

  // 2) Form fields: label decides the currency; input gets a matching border/text color.
  scope.querySelectorAll('.field').forEach(field=>{
    const label=field.querySelector('label');
    const type=detectCurrencyType(label?.textContent||'');
    if(!type) return;
    setCurrencyClass(label,type);
    field.querySelectorAll('input,select,textarea,.input').forEach(el=>setCurrencyClass(el,type));
  });

  // 3) KPI / summary cards whose title explicitly contains a currency.
  scope.querySelectorAll('.kpi-card,.summary-box,.detail-row').forEach(card=>{
    const label=card.querySelector('small,label');
    const type=detectCurrencyType(label?.textContent||card.textContent||'');
    if(!type) return;
    if(label) setCurrencyClass(label,type);
    card.querySelectorAll('strong,b').forEach(el=>setCurrencyClass(el,type));
  });

  // 4) Known calculated values that intentionally omit a symbol in their static title.
  const explicit={
    saleDeposit:'usd',saleConverted:'usd',saleGross:'usd',saleCosts:'usd',saleNet:'usd',
    kUsd:'usd',kEur:'eur',kCash:'egp',kOffice:'egp',kCoin:'eur',kCoinBal:'eur',kNet:'usd',
    coinBalance:'eur',coinIn:'eur',coinOut:'eur',coinAmount:'eur',
    salGrandNet:'egp',salGrandSales:'usd',
    rpAgreed:'usd',rpRemaining:'usd',rpIncome:'usd',rpCosts:'usd',
    kIncome:'usd',kRemaining:'usd'
  };
  Object.entries(explicit).forEach(([id,type])=>setCurrencyClass(document.getElementById(id),type));

  // 5) Any standalone element that already prints an explicit currency symbol/name.
  scope.querySelectorAll('.money-value,.amount,.metric-value,.stat-value,.detail-row b,.summary-box strong').forEach(el=>{
    const type=detectCurrencyType(el.textContent);
    if(type) setCurrencyClass(el,type);
  });
}
let currencyPaintPending=false;
function scheduleCurrencyColorize(mutations){
  if(Array.isArray(mutations)){
    const onlyClock = mutations.every(m => {
      const t = m.target?.nodeType === 1 ? m.target : m.target?.parentElement;
      return t && (t.id === 'sideClock' || t.id === 'footerClock' || t.id === 'sideDate' || t.closest?.('.header-clock-pill') || t.closest?.('.sidebar-status-box'));
    });
    if(onlyClock) return;
  }
  if(currencyPaintPending) return;
  currencyPaintPending=true;
  requestAnimationFrame(()=>{currencyPaintPending=false;colorizeFinancialCurrencies(document)});
}
colorizeFinancialCurrencies(document);
new MutationObserver(scheduleCurrencyColorize).observe(document.body,{childList:true,subtree:true});

initLogicTabs();
// Theme toggle is handled once in templates/base.html (applyTheme).
// The old duplicate listener here wrote a conflicting 'phototeam_theme' value and was removed in V72.


// ============================================================================
// 🤖 PHOTO TEAM AI COPILOT — المساعد الذكي التفاعلي (مع عزل الصلاحيات)
// ============================================================================
let AI_CHAT_INITIALIZED = false;

function getAiRoleQuickPrompts() {
  return [];
}

function formatAiMarkdown(text = '') {
  let safe = esc(String(text || ''));
  safe = safe.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  safe = safe.replace(/`([^`]+)`/g, '<code style="background:rgba(37,99,235,0.09);padding:1px 6px;border-radius:6px;font-weight:800;color:var(--primary);">$1</code>');
  safe = safe.replace(/^&gt;\s*(.+)$/gm, '<blockquote style="margin:6px 0;padding:8px 12px;background:#f8fafc;border-right:3px solid var(--primary);border-radius:8px;font-size:12px;direction:ltr;text-align:left;">$1</blockquote>');
  return safe.replace(/\n/g, '<br>');
}

function buildAiInlineQuickIncomeWidgetHTML(w = {}) {
  const wid = 'aiQi_' + Date.now() + '_' + Math.floor(Math.random() * 1000);
  const salesList = Array.isArray(w.sales) ? w.sales : [];
  const photoList = Array.isArray(w.photographers) ? w.photographers : [];
  const hotelsList = Array.isArray(w.hotels) ? w.hotels : [];
  const preSales = String(w.preselected_sales || '');
  const prePhotog = String(w.preselected_photographer || '');
  const prePhotog2 = String(w.preselected_photographer_2 || '');
  const preRoom = String(w.preselected_room || '');
  const preUsd = Number(w.preselected_usd || 0);
  const preEur = Number(w.preselected_eur || 0);
  const preCash = Number(w.preselected_cash || 0);
  const preOffice = Number(w.preselected_office || 0);
  const preDep = Number(w.preselected_deposit || 0);

  const salesOpts = `<option value="">-- اختر اسم السيلز --</option>` + salesList.map(s => {
    const name = typeof s === 'object' ? (s.nickname || s.full_name || '') : String(s);
    return `<option value="${esc(name)}" ${name === preSales ? 'selected' : ''}>${esc(name)}</option>`;
  }).join('');

  const photoOpts1 = `<option value="">-- اختر اسم المصور --</option>` + photoList.map(p => {
    const name = typeof p === 'object' ? (p.nickname || p.full_name || '') : String(p);
    return `<option value="${esc(name)}" ${name === prePhotog ? 'selected' : ''}>${esc(name)}</option>`;
  }).join('');

  const photoOpts2 = `<option value="">-- بدون مصور ثاني (اختياري) --</option>` + photoList.map(p => {
    const name = typeof p === 'object' ? (p.nickname || p.full_name || '') : String(p);
    return `<option value="${esc(name)}" ${name === prePhotog2 ? 'selected' : ''}>${esc(name)}</option>`;
  }).join('');

  const hotelOpts = hotelsList.length
    ? hotelsList.map(h => `<option value="${esc(h.id || 1)}">${esc(h.hotel_name || h)}</option>`).join('')
    : `<option value="1">الفندق الرئيسي</option>`;

  return `
    <div class="ai-inline-qi-card" id="${wid}" data-ai-qi-card="1" style="margin-top:10px;padding:12px;border-radius:12px;background:var(--bg-surface-2, #f8fafc);border:1.5px solid var(--primary, #2563eb);display:flex;flex-direction:column;gap:8px;direction:rtl;">
      <div style="font-weight:900;font-size:12.5px;color:var(--primary, #2563eb);display:flex;justify-content:space-between;align-items:center;">
        <span>⚡ تسجيل دخل جديد في الدخل اليومي (من نطاق عملنا)</span>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">
        <div>
          <label style="font-size:11px;font-weight:800;display:block;margin-bottom:2px;">اختر اسم السيلز *</label>
          <select class="input ai-qi-sales" style="min-height:32px;height:32px;padding:2px 6px;font-size:12px;width:100%;">${salesOpts}</select>
        </div>
        <div>
          <label style="font-size:11px;font-weight:800;display:block;margin-bottom:2px;">اختر اسم المصور *</label>
          <select class="input ai-qi-photog1" style="min-height:32px;height:32px;padding:2px 6px;font-size:12px;width:100%;">${photoOpts1}</select>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;">
        <div>
          <label style="font-size:10.5px;font-weight:800;display:block;margin-bottom:2px;">مصور ثاني (اختياري)</label>
          <select class="input ai-qi-photog2" style="min-height:30px;height:30px;padding:2px 6px;font-size:11.5px;width:100%;">${photoOpts2}</select>
        </div>
        <div>
          <label style="font-size:10.5px;font-weight:800;display:block;margin-bottom:2px;">الفندق</label>
          <select class="input ai-qi-hotel" style="min-height:30px;height:30px;padding:2px 6px;font-size:11.5px;width:100%;">${hotelOpts}</select>
        </div>
        <div>
          <label style="font-size:10.5px;font-weight:800;display:block;margin-bottom:2px;">الغرفة (اختياري)</label>
          <input type="text" class="input ai-qi-room" value="${esc(preRoom)}" placeholder="أو دخل سريع" style="min-height:30px;height:30px;padding:2px 6px;font-size:11.5px;width:100%;">
        </div>
      </div>
      <div style="font-size:11px;font-weight:900;color:var(--text-heading);margin-top:2px;">💵 المبلغ بأنواعه وعملاته:</div>
      <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:6px;">
        <div>
          <label style="font-size:10.5px;font-weight:800;display:block;margin-bottom:2px;">دخل دولار ($ USD)</label>
          <input type="number" step="0.01" class="input ai-qi-usd" value="${preUsd}" oninput="recalcAiInlineQuickIncome('${wid}')" style="min-height:30px;height:30px;padding:2px 6px;font-size:12px;width:100%;">
        </div>
        <div>
          <label style="font-size:10.5px;font-weight:800;display:block;margin-bottom:2px;">دخل يورو (€ EUR)</label>
          <input type="number" step="0.01" class="input ai-qi-eur" value="${preEur}" oninput="recalcAiInlineQuickIncome('${wid}')" style="min-height:30px;height:30px;padding:2px 6px;font-size:12px;width:100%;">
        </div>
        <div>
          <label style="font-size:10.5px;font-weight:800;display:block;margin-bottom:2px;">دخل كاش مصري (LE)</label>
          <input type="number" step="0.01" class="input ai-qi-cash" value="${preCash}" oninput="recalcAiInlineQuickIncome('${wid}')" style="min-height:30px;height:30px;padding:2px 6px;font-size:12px;width:100%;">
        </div>
        <div>
          <label style="font-size:10.5px;font-weight:800;display:block;margin-bottom:2px;">دخل مكتب / فيزا (LE)</label>
          <input type="number" step="0.01" class="input ai-qi-office" value="${preOffice}" oninput="recalcAiInlineQuickIncome('${wid}')" style="min-height:30px;height:30px;padding:2px 6px;font-size:12px;width:100%;">
        </div>
      </div>
      <input type="hidden" class="ai-qi-dep" value="${preDep}">
      <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 10px;border-radius:8px;background:rgba(16,185,129,0.12);border:1px solid rgba(16,185,129,0.35);font-size:12px;">
        <span>الصافي المعادل بالدولار:</span>
        <strong class="ai-qi-net-preview" style="color:#059669;font-size:14px;">$0.00</strong>
      </div>
      <button type="button" class="btn green" style="width:100%;min-height:34px;font-weight:900;font-size:12.5px;" onclick="submitAiInlineQuickIncome('${wid}')">💾 حفظ في الدخل اليومي الآن</button>
    </div>
  `;
}

function recalcAiInlineQuickIncome(wid) {
  const card = document.getElementById(wid);
  if (!card) return;
  const usd = num(card.querySelector('.ai-qi-usd')?.value);
  const eur = num(card.querySelector('.ai-qi-eur')?.value);
  const cash = num(card.querySelector('.ai-qi-cash')?.value);
  const office = num(card.querySelector('.ai-qi-office')?.value);
  const dep = num(card.querySelector('.ai-qi-dep')?.value);
  const net = dep + usd + eur + ((cash + office) / 50);
  const prev = card.querySelector('.ai-qi-net-preview');
  if (prev) prev.textContent = '$' + money(net);
}
window.recalcAiInlineQuickIncome = recalcAiInlineQuickIncome;

async function hydrateAiInlineTeamListsIfEmpty(wid) {
  const card = document.getElementById(wid);
  if (!card) return;
  const sSel = card.querySelector('.ai-qi-sales');
  const p1Sel = card.querySelector('.ai-qi-photog1');
  const p2Sel = card.querySelector('.ai-qi-photog2');
  const hSel = card.querySelector('.ai-qi-hotel');
  if (sSel && sSel.options.length <= 1) {
    try {
      const [tOpts, hOpts] = await Promise.all([
        apiSafe('/api/team/options', { sales: [], photographers: [] }),
        apiSafe('/api/hotels', [])
      ]);
      if (sSel && (tOpts.sales || []).length) {
        sSel.innerHTML = `<option value="">-- اختر اسم السيلز --</option>` + (tOpts.sales || []).map(x => `<option value="${esc(x.nickname)}">${esc(x.nickname)}</option>`).join('');
      }
      if (p1Sel && (tOpts.photographers || []).length) {
        p1Sel.innerHTML = `<option value="">-- اختر اسم المصور --</option>` + (tOpts.photographers || []).map(x => `<option value="${esc(x.nickname)}">${esc(x.nickname)}</option>`).join('');
      }
      if (p2Sel && (tOpts.photographers || []).length) {
        p2Sel.innerHTML = `<option value="">-- بدون مصور ثاني (اختياري) --</option>` + (tOpts.photographers || []).map(x => `<option value="${esc(x.nickname)}">${esc(x.nickname)}</option>`).join('');
      }
      if (hSel && (hOpts || []).length) {
        hSel.innerHTML = hOpts.map(h => `<option value="${esc(h.id)}">${esc(h.hotel_name)}</option>`).join('');
      }
    } catch (e) {}
  }
  recalcAiInlineQuickIncome(wid);
}

async function submitAiInlineQuickIncome(wid) {
  const card = document.getElementById(wid);
  if (!card) return;
  const sales = (card.querySelector('.ai-qi-sales')?.value || '').trim();
  const photog1 = (card.querySelector('.ai-qi-photog1')?.value || '').trim();
  const photog2 = (card.querySelector('.ai-qi-photog2')?.value || '').trim();
  const hotelId = num(card.querySelector('.ai-qi-hotel')?.value) || 1;
  const room = (card.querySelector('.ai-qi-room')?.value || '').trim() || 'دخل سريع';
  const usd = num(card.querySelector('.ai-qi-usd')?.value);
  const eur = num(card.querySelector('.ai-qi-eur')?.value);
  const cash = num(card.querySelector('.ai-qi-cash')?.value);
  const office = num(card.querySelector('.ai-qi-office')?.value);
  const dep = num(card.querySelector('.ai-qi-dep')?.value);

  if (!sales) return toast('⚠️ يرجى اختيار اسم السيلز من القائمة أولاً', 'bad');
  if (!photog1) return toast('⚠️ يرجى اختيار اسم المصور من القائمة أولاً', 'bad');
  const gross = dep + usd + eur + ((cash + office) / 50);
  if (gross <= 0) return toast('⚠️ يرجى إدخال المبلغ بأحد أنواعه (دولار $، يورو €، كاش LE، أو مكتب LE)', 'bad');

  const photogs = [photog1];
  if (photog2 && photog2.toLowerCase() !== photog1.toLowerCase()) photogs.push(photog2);
  const photogStr = photogs.join(', ');

  try {
    const r = await apiJSON('/api/daily-sales', 'POST', {
      hotel_id: hotelId,
      room_number: room,
      income_date: (document.getElementById('dsEntryDate')?.value) || todayISO(),
      sales_person: sales,
      photographer: photogStr,
      deposit_applied: dep,
      income_usd: usd,
      income_eur: eur,
      income_le_k: cash,
      income_le_m: office,
      le_to_usd: 50,
      cost_dress: 0,
      cost_usb: 0,
      cost_album: 0
    });
    toast(`✅ تم حفظ الدخل في الدخل اليومي بنجاح (الصافي: $${money(r.daily_total)})`);
    appendAiMessage(
      'assistant',
      `✅ **تم تسجيل وحفظ الدخل في الدخل اليومي بنجاح!**
` +
      `• **اسم السيلز:** \`${sales}\` | **اسم المصور:** \`${photogStr}\`
` +
      `• **الغرفة / البيان:** \`${room}\`
` +
      `• **المبلغ المحفوظ:** دولار **$${money(usd)}** | يورو **€${money(eur)}** | كاش **${money(cash)} LE** | مكتب **${money(office)} LE**
` +
      `• **صافي الدخل اليومي:** **$${money(r.daily_total)}**`,
      [{ label: '💰 فتح الدخل اليومي', href: '/daily-sales' }]
    );
    if (typeof loadEligible === 'function') loadEligible();
    if (typeof loadSalesSearch === 'function') loadSalesSearch();
    if (typeof loadAnalytics === 'function') loadAnalytics();
  } catch (err) {
    toast(err.message || 'تعذر حفظ الدخل', 'bad');
  }
}
window.submitAiInlineQuickIncome = submitAiInlineQuickIncome;

function appendAiMessage(role, text, actions = [], widget = null) {
  const list = $('aiMessagesList');
  if (!list) return;
  const div = document.createElement('div');
  div.className = `ai-msg-bubble ${role}`;
  let html = `<div>${formatAiMarkdown(text)}</div>`;
  if (widget && widget.type === 'quick_income_form') {
    html += buildAiInlineQuickIncomeWidgetHTML(widget);
  }
  if (Array.isArray(actions) && actions.length) {
    html += `<div class="ai-msg-actions">` + actions.map((a) => {
      const linkUrl = a.href || a.url;
      if (a.onclick) {
        return `<button type="button" class="ai-action-pill" onclick="${esc(a.onclick)}">${esc(a.label)}</button>`;
      }
      if (linkUrl) {
        return `<a class="ai-action-pill" href="${esc(linkUrl)}">${esc(a.label)}</a>`;
      }
      if (a.prompt) {
        return `<button type="button" class="ai-action-pill" data-aiprompt="${esc(a.prompt)}" onclick="sendAiQuickPrompt(this.dataset.aiprompt)">${esc(a.label)}</button>`;
      }
      return '';
    }).join('') + `</div>`;
  }
  div.innerHTML = html;
  list.appendChild(div);
  list.scrollTop = list.scrollHeight;
  const card = div.querySelector('[data-ai-qi-card="1"]');
  if (card && card.id) {
    hydrateAiInlineTeamListsIfEmpty(card.id);
  }
}

function initAiCopilotUI() {
  if (AI_CHAT_INITIALIZED) return;
  AI_CHAT_INITIALIZED = true;

  const user = window.CURRENT_USER || {};
  const personal = Boolean(window.PERSONAL_SCOPE);
  const sub = $('aiScopeSubtitle');
  if (sub) {
    sub.textContent = personal
      ? `🔒 نطاق شخصي معزول (${user.nickname || user.full_name || 'موظف'}) • يحلل بياناتك فقط`
      : `👑 صلاحية إدارية شاملة (${user.nickname || user.full_name || 'المدير'}) • كل الفروع`;
  }

  const savedKey = localStorage.getItem('photo_team_ai_api_key') || '';
  if ($('aiExternalApiKey')) $('aiExternalApiKey').value = savedKey;

  const chipsHost = $('aiQuickChips');
  if (chipsHost) {
    chipsHost.innerHTML = getAiRoleQuickPrompts().map(c =>
      `<button type="button" class="ai-chip-btn" data-prompt="${esc(c.prompt)}" onclick="sendAiQuickPrompt(this.dataset.prompt)">${esc(c.label)}</button>`
    ).join('');
  }

  const list = $('aiMessagesList');
  if (list && !list.children.length) {
    const welcome = personal
      ? `أهلاً بك يا **${user.nickname || user.full_name || 'بطل'}** 👋
أنا **المساعد الذكي Photo Team AI** المتصل ببياناتك الشخصية. اكتب سؤالك مباشرة بالأسفل.`
      : `أهلاً بك يا **${user.nickname || user.full_name || 'ريس'}** 👋
أنا **المساعد الذكي Photo Team AI** المتصل مباشرة بقاعدة البيانات. اكتب سؤالك مباشرة بالأسفل.`;
    appendAiMessage('assistant', welcome, []);
  }
}

function toggleAiCopilot(forceState) {
  const drawer = $('aiCopilotDrawer');
  if (!drawer) return;
  initAiCopilotUI();
  const nextOpen = typeof forceState === 'boolean' ? forceState : drawer.hidden;
  drawer.hidden = !nextOpen;
  if (nextOpen) {
    setTimeout(() => $('aiChatInput')?.focus(), 60);
  }
}

function toggleAiSettingsBox() {
  const box = $('aiSettingsBox');
  if (box) box.hidden = !box.hidden;
}

function saveAiExternalApiKey() {
  const key = ($('aiExternalApiKey')?.value || '').trim();
  try {
    if (key) localStorage.setItem('photo_team_ai_api_key', key);
    else localStorage.removeItem('photo_team_ai_api_key');
  } catch (e) {}
  toast(key ? '🤖 تم حفظ مفتاح الذكاء الاصطناعي الخارجي بنجاح' : '🤖 تم التبديل إلى المحرك الذكي المدمج');
  if ($('aiSettingsBox')) $('aiSettingsBox').hidden = true;
}

function clearAiChatHistory() {
  const list = $('aiMessagesList');
  if (list) list.innerHTML = '';
  AI_CHAT_INITIALIZED = false;
  initAiCopilotUI();
}

function sendAiQuickPrompt(promptText) {
  if (!promptText) return;
  const input = $('aiChatInput');
  if (input) input.value = promptText;
  submitAiQuery(promptText);
}

async function handleAiChatSubmit(e) {
  if (e) e.preventDefault();
  const input = $('aiChatInput');
  const q = (input?.value || '').trim();
  if (!q) return;
  submitAiQuery(q);
}

async function submitAiQuery(q) {
  const input = $('aiChatInput');
  if (input) input.value = '';
  appendAiMessage('user', q);

  const btn = $('aiSendBtn');
  if (btn) { btn.disabled = true; btn.textContent = '⏳...'; }

  try {
    const extKey = localStorage.getItem('photo_team_ai_api_key') || '';
    const res = await apiJSON('/api/ai/chat', 'POST', {
      message: q,
      api_key: extKey,
      provider: 'auto'
    });
    appendAiMessage('assistant', res.reply || 'تم تحليل البيانات بنجاح.', res.actions || [], res.widget || null);
  } catch (err) {
    appendAiMessage('assistant', `⚠️ تعذر الاتصال بالخادم حالياً: ${err.message}`);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '🚀 إرسال'; }
  }
}

document.addEventListener('keydown', function(e) {
  if (e.altKey && (e.key.toLowerCase() === 'a' || e.key === 'ش')) {
    e.preventDefault();
    toggleAiCopilot();
  }
});


// ============================================================================
// 🖨️ THERMAL POS RECEIPT ENGINE (80mm / 58mm) — إيصال حجز حراري + إيصال مبيعات حراري
// ============================================================================
window.THERMAL_PAPER_WIDTH = localStorage.getItem('pt_thermal_width') || '80mm';

function setThermalPaperWidth(w) {
  window.THERMAL_PAPER_WIDTH = w === '58mm' ? '58mm' : '80mm';
  try { localStorage.setItem('pt_thermal_width', window.THERMAL_PAPER_WIDTH); } catch(e) {}
  const previewCard = document.getElementById('thermalReceiptPaper');
  if (previewCard) {
    previewCard.style.maxWidth = window.THERMAL_PAPER_WIDTH === '58mm' ? '235px' : '315px';
  }
  document.querySelectorAll('.pos-size-btn').forEach(b => {
    b.classList.toggle('primary', b.dataset.size === window.THERMAL_PAPER_WIDTH);
  });
}

function buildThermalBookingReceiptHTML(b = {}) {
  const recNo = b.id ? `BK-${b.id}` : `BK-${String(Date.now()).slice(-4)}`;
  const room = esc(b.room_number || '-');
  const hotel = esc(b.hotel || b.hotel_name || 'PHOTO TEAM RESORT');
  const bdate = esc(String(b.booking_date || todayISO()).slice(0, 10));
  const btime = esc(String(b.booking_time || '--:--').slice(0, 5));
  const nat = esc(b.nationality || '-');
  const phone = esc(b.phone_number || '-');
  const sales = esc(b.sales_person || '-');
  const photog = esc(b.photographer || 'يحدد بالشفت');
  const sessionDesc = esc(b.session_details || 'جلسة تصوير احترافية');

  let clothesHtml = '';
  const items = Array.isArray(b.clothing_items) ? b.clothing_items : (Array.isArray(b.clothing) ? b.clothing : []);
  if (items.length) {
    clothesHtml = items.map((c, idx) =>
      `<div style="display:flex;justify-content:space-between;font-size:12px;padding:2px 0;border-bottom:1px dotted #cbd5e1;">
        <span>${idx+1}. ${esc(c.type||'فستان')} (${esc(c.color||'-')} • ${esc(c.size||'M')})</span>
        <b>× ${esc(c.qty||1)}</b>
      </div>`
    ).join('');
  } else if (typeof b.clothing_items === 'string' && b.clothing_items.trim()) {
    clothesHtml = `<div style="font-size:12px;font-weight:700;">${esc(b.clothing_items)}</div>`;
  } else {
    clothesHtml = `<div style="font-size:12px;color:#475569;">بدون فساتين إضافية / ملابس شخصية</div>`;
  }

  const usd = num(b.deposit_usd);
  const eur = num(b.deposit_eur);
  const cash = num(b.deposit_le_cash);
  const visa = num(b.deposit_le_visa);
  const rate = num(b.rate) || 50;
  const totalAgreed = num(b.total_agreement ?? b.total_price);
  const paidEquiv = b.paid_equiv !== undefined ? num(b.paid_equiv) : (usd + eur + ((cash + visa) / rate));
  const remaining = b.remaining !== undefined ? num(b.remaining) : Math.max(0, totalAgreed - paidEquiv);

  const paidLines = [];
  if (usd > 0) paidLines.push(`USD: $${money(usd)}`);
  if (eur > 0) paidLines.push(`EUR: €${money(eur)}`);
  if (cash > 0) paidLines.push(`Cash: ${money(cash)} LE`);
  if (visa > 0) paidLines.push(`Visa: ${money(visa)} LE`);
  const paidBreakdown = paidLines.length ? paidLines.join(' + ') : '$0.00';

  return `
    <div id="thermalReceiptPaper" style="margin:0 auto;max-width:${window.THERMAL_PAPER_WIDTH==='58mm'?'235px':'315px'};background:#ffffff;color:#000000;padding:14px 12px;border:1px solid #94a3b8;border-radius:6px;box-shadow:0 8px 25px rgba(0,0,0,0.12);font-family:'Cairo','Tahoma',monospace;direction:rtl;line-height:1.45;">
      <div style="text-align:center;border-bottom:2px dashed #000;padding-bottom:8px;margin-bottom:8px;">
        <div style="font-size:17px;font-weight:900;letter-spacing:0.5px;">📸 PHOTO TEAM STUDIO</div>
        <div style="font-size:12px;font-weight:800;">${hotel}</div>
        <div style="display:inline-block;margin-top:4px;padding:2px 10px;background:#000;color:#fff;font-size:11.5px;font-weight:900;border-radius:4px;">
          إيصال حجز وموعد • BOOKING RECEIPT
        </div>
        <div style="font-size:10.5px;margin-top:4px;color:#334155;" dir="ltr">
          No: #${recNo} • ${new Date().toLocaleString('en-GB')}
        </div>
      </div>

      <div style="border:2px solid #000;border-radius:6px;padding:7px 10px;margin-bottom:8px;text-align:center;background:#f8fafc;">
        <div style="font-size:11px;font-weight:800;">رقم الغرفة / ROOM NUMBER</div>
        <div style="font-size:24px;font-weight:900;letter-spacing:1px;">${room}</div>
        <div style="display:flex;justify-content:space-between;font-size:11.5px;font-weight:800;border-top:1px dashed #000;margin-top:4px;padding-top:4px;">
          <span>📅 التاريخ: <b dir="ltr">${bdate}</b></span>
          <span>⏰ الموعد: <b dir="ltr">${btime}</b></span>
        </div>
      </div>

      <div style="font-size:11.5px;margin-bottom:8px;border-bottom:1px dashed #000;padding-bottom:6px;">
        <div style="display:flex;justify-content:space-between;"><span>الجنسية / Guest:</span><b>${nat}</b></div>
        <div style="display:flex;justify-content:space-between;"><span>الهاتف / Phone:</span><b dir="ltr">${phone}</b></div>
        <div style="display:flex;justify-content:space-between;"><span>مسؤول الحجز / Sales:</span><b>${sales}</b></div>
        <div style="display:flex;justify-content:space-between;"><span>المصور / Photographer:</span><b>${photog}</b></div>
      </div>

      <div style="margin-bottom:8px;border-bottom:1px dashed #000;padding-bottom:6px;">
        <div style="font-size:11.5px;font-weight:900;margin-bottom:3px;">👗 الفساتين وتفاصيل السيشن / Dresses:</div>
        ${clothesHtml}
        <div style="font-size:11px;margin-top:4px;color:#1e293b;">📝 ${sessionDesc}</div>
      </div>

      <div style="border:2px solid #000;border-radius:6px;padding:8px;margin-bottom:8px;background:#fff;">
        <div style="display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:4px;">
          <span>إجمالي الاتفاق / Total Agreed:</span>
          <b dir="ltr">${money(totalAgreed)} $</b>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:2px;">
          <span>المدفوع (عربون) / Paid Deposit:</span>
          <b dir="ltr">${money(paidEquiv)} $</b>
        </div>
        <div style="font-size:10.5px;color:#334155;text-align:left;margin-bottom:5px;" dir="ltr">
          (${paidBreakdown})
        </div>
        <div style="display:flex;justify-content:space-between;font-size:14.5px;font-weight:900;border-top:2px dashed #000;padding-top:5px;">
          <span>المتبقي / Remaining Due:</span>
          <b dir="ltr">${money(remaining)} $</b>
        </div>
      </div>

      <div style="text-align:center;font-size:10.5px;line-height:1.45;">
        <div style="font-weight:900;">⚠️ يرجى الحضور قبل الموعد بـ 10 دقائق</div>
        <div>Please arrive 10 mins before your session time</div>
        <div style="margin-top:6px;font-family:monospace;font-size:13px;letter-spacing:3px;font-weight:900;">||| |||| || |||| |||</div>
        <div style="font-size:10px;color:#475569;">Thank you • PHOTO TEAM RESORT STUDIO</div>
      </div>
    </div>
  `;
}

function buildThermalSalesReceiptHTML(r = {}) {
  const invNo = r.id ? `INV-${r.id}` : `INV-${String(Date.now()).slice(-4)}`;
  const room = esc(r.room_number || '-');
  const hotel = esc(r.hotel_name || r.hotel || 'PHOTO TEAM RESORT');
  const sdate = esc(String(r.income_date || todayISO()).slice(0, 10));
  const sales = esc(r.sales_person || r.deposit_sales_person || '-');
  const photog = esc(r.photographer || '-');

  const dep = num(r.deposit_applied ?? r.deposit);
  const usd = num(r.income_usd);
  const eur = num(r.income_eur);
  const cashLe = num(r.income_le_k ?? r.income_le_cash);
  const officeLe = num(r.income_le_m ?? r.income_le_visa);
  const rate = num(r.le_to_usd ?? r.rate) || 50;
  const gross = num(r.gross_total) || (dep + usd + eur + ((cashLe + officeLe) / rate));
  const remaining = num(r.remaining_amount ?? 0);

  return `
    <div id="thermalReceiptPaper" style="margin:0 auto;max-width:${window.THERMAL_PAPER_WIDTH==='58mm'?'235px':'315px'};background:#ffffff;color:#000000;padding:14px 12px;border:1px solid #94a3b8;border-radius:6px;box-shadow:0 8px 25px rgba(0,0,0,0.12);font-family:'Cairo','Tahoma',monospace;direction:rtl;line-height:1.45;">
      <div style="text-align:center;border-bottom:2px dashed #000;padding-bottom:8px;margin-bottom:8px;">
        <div style="font-size:17px;font-weight:900;letter-spacing:0.5px;">📸 PHOTO TEAM STUDIO</div>
        <div style="font-size:12px;font-weight:800;">${hotel}</div>
        <div style="display:inline-block;margin-top:4px;padding:2px 10px;background:#000;color:#fff;font-size:11.5px;font-weight:900;border-radius:4px;">
          إيصال مبيعات وسداد • SALES RECEIPT
        </div>
        <div style="font-size:10.5px;margin-top:4px;color:#334155;" dir="ltr">
          Invoice: #${invNo} • Date: ${sdate}
        </div>
      </div>

      <div style="border:2px solid #000;border-radius:6px;padding:7px 10px;margin-bottom:8px;text-align:center;background:#f8fafc;">
        <div style="font-size:11px;font-weight:800;">رقم الغرفة / ROOM NUMBER</div>
        <div style="font-size:24px;font-weight:900;letter-spacing:1px;">${room}</div>
      </div>

      <div style="font-size:11.5px;margin-bottom:8px;border-bottom:1px dashed #000;padding-bottom:6px;">
        <div style="display:flex;justify-content:space-between;"><span>المصور / Photographer:</span><b>${photog}</b></div>
        <div style="display:flex;justify-content:space-between;"><span>مسؤول المبيعات / Sales:</span><b>${sales}</b></div>
        <div style="display:flex;justify-content:space-between;"><span>تاريخ السداد / Date:</span><b dir="ltr">${sdate}</b></div>
      </div>

      <div style="margin-bottom:8px;border-bottom:1px dashed #000;padding-bottom:6px;font-size:12px;">
        <div style="font-weight:900;margin-bottom:4px;">💳 تفاصيل السداد / Payment Breakdown:</div>
        <div style="display:flex;justify-content:space-between;"><span>العربون المخصوم / Deposit:</span><b dir="ltr">${money(dep)} $</b></div>
        ${usd > 0 ? `<div style="display:flex;justify-content:space-between;"><span>مدفوع دولار / Cash USD:</span><b dir="ltr">${money(usd)} $</b></div>` : ''}
        ${eur > 0 ? `<div style="display:flex;justify-content:space-between;"><span>مدفوع يورو / Cash EUR:</span><b dir="ltr">${money(eur)} €</b></div>` : ''}
        ${cashLe > 0 ? `<div style="display:flex;justify-content:space-between;"><span>مدفوع كاش مصري / EGP Cash:</span><b dir="ltr">${money(cashLe)} LE</b></div>` : ''}
        ${officeLe > 0 ? `<div style="display:flex;justify-content:space-between;"><span>مدفوع مكتب/فيزا / EGP Card:</span><b dir="ltr">${money(officeLe)} LE</b></div>` : ''}
      </div>

      <div style="border:2px solid #000;border-radius:6px;padding:8px;margin-bottom:8px;background:#fff;">
        <div style="display:flex;justify-content:space-between;font-size:14px;font-weight:900;">
          <span>إجمالي المسدد / Total Paid:</span>
          <b dir="ltr">${money(gross)} $</b>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:12.5px;font-weight:900;border-top:1px dashed #000;margin-top:5px;padding-top:4px;">
          <span>المتبقي / Remaining:</span>
          <b dir="ltr">${money(remaining)} $ (${remaining <= 0 ? 'خالصة / PAID ✅' : 'متبقي'})</b>
        </div>
      </div>

      <div style="text-align:center;font-size:10.5px;line-height:1.45;">
        <div style="font-weight:900;">✅ تم السداد واستلام الأوردر بنجاح</div>
        <div>Thank you for choosing PHOTO TEAM Studio!</div>
        <div style="margin-top:6px;font-family:monospace;font-size:13px;letter-spacing:3px;font-weight:900;">||| |||| || |||| |||</div>
      </div>
    </div>
  `;
}

function executeThermalPrint() {
  const paper = document.getElementById('thermalReceiptPaper');
  if (!paper) return window.print();
  const w = window.THERMAL_PAPER_WIDTH || '80mm';
  const thermalHtml = `<div style="width:${w};max-width:100%;margin:0 auto;background:#fff;color:#000;font-family:'Cairo','Tahoma',monospace;direction:rtl;">${paper.outerHTML}</div>`;
  triggerDirectInPagePrint(thermalHtml, `${w} auto`);
}

function openThermalBookingReceiptModal(b = {}) {
  const html = buildThermalBookingReceiptHTML(b);
  showModal(`
    <div class="modal-title" style="flex-direction:row !important;justify-content:space-between !important;align-items:center !important;flex-wrap:wrap;gap:10px;">
      <div>
        <h2>🖨️ معاينة وطباعة إيصال الحجز الحراري (POS Receipt)</h2>
        <p>مخصص لطابعات الإيصالات الحرارية الصغيرة (80mm / 58mm) لتسليمه للعميل وقت الحجز</p>
      </div>
      <div style="display:flex;gap:6px;">
        <button type="button" class="btn pos-size-btn ${window.THERMAL_PAPER_WIDTH==='80mm'?'primary':''}" data-size="80mm" onclick="setThermalPaperWidth('80mm')">📄 ورق 80mm</button>
        <button type="button" class="btn pos-size-btn ${window.THERMAL_PAPER_WIDTH==='58mm'?'primary':''}" data-size="58mm" onclick="setThermalPaperWidth('58mm')">📄 ورق 58mm</button>
      </div>
    </div>
    <div style="background:var(--bg-surface-2);padding:18px;border-radius:16px;border:1px solid var(--border);max-height:62vh;overflow-y:auto;">
      ${html}
    </div>
    <div class="modal-actions" style="margin-top:14px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;">
      <button type="button" class="btn" onclick="closeModal()">إغلاق</button>
      <div style="display:flex;gap:8px;">
        <button type="button" class="btn primary" onclick="executeThermalPrint()">🖨️ طباعة فورية على طابعة الإيصالات</button>
      </div>
    </div>
  `, 'modal-lg');
}

function openThermalSalesReceiptModal(r = {}) {
  const html = buildThermalSalesReceiptHTML(r);
  showModal(`
    <div class="modal-title" style="flex-direction:row !important;justify-content:space-between !important;align-items:center !important;flex-wrap:wrap;gap:10px;">
      <div>
        <h2>🖨️ معاينة وطباعة إيصال المبيعات الحراري (Sales POS Receipt)</h2>
        <p>إيصال مبيعات وسداد نهائي لطابعة الكاشير الحرارية (80mm / 58mm)</p>
      </div>
      <div style="display:flex;gap:6px;">
        <button type="button" class="btn pos-size-btn ${window.THERMAL_PAPER_WIDTH==='80mm'?'primary':''}" data-size="80mm" onclick="setThermalPaperWidth('80mm')">📄 ورق 80mm</button>
        <button type="button" class="btn pos-size-btn ${window.THERMAL_PAPER_WIDTH==='58mm'?'primary':''}" data-size="58mm" onclick="setThermalPaperWidth('58mm')">📄 ورق 58mm</button>
      </div>
    </div>
    <div style="background:var(--bg-surface-2);padding:18px;border-radius:16px;border:1px solid var(--border);max-height:62vh;overflow-y:auto;">
      ${html}
    </div>
    <div class="modal-actions" style="margin-top:14px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;">
      <button type="button" class="btn" onclick="closeModal()">إغلاق</button>
      <div style="display:flex;gap:8px;">
        <button type="button" class="btn green" onclick="executeThermalPrint()">🖨️ طباعة إيصال المبيعات الآن</button>
      </div>
    </div>
  `, 'modal-lg');
}


function triggerDirectInPagePrint(contentHtml, pageSizeCss = 'A4 portrait') {
  let zone = document.getElementById('ptDirectPrintZone');
  if (!zone) {
    zone = document.createElement('div');
    zone.id = 'ptDirectPrintZone';
    document.body.appendChild(zone);
  }
  let styleTag = document.getElementById('ptDirectPrintStyle');
  if (!styleTag) {
    styleTag = document.createElement('style');
    styleTag.id = 'ptDirectPrintStyle';
    document.head.appendChild(styleTag);
  }
  styleTag.textContent = `
    #ptDirectPrintZone { display: none; }
    @media print {
      @page { size: ${pageSizeCss}; margin: 6mm; }
      html, body { background: #ffffff !important; color: #000000 !important; margin: 0 !important; padding: 0 !important; height: auto !important; overflow: visible !important; }
      body.pt-printing-custom > *:not(#ptDirectPrintZone) { display: none !important; }
      body.pt-printing-custom #ptDirectPrintZone {
        display: block !important;
        position: static !important;
        width: 100% !important;
        background: #ffffff !important;
        color: #000000 !important;
        padding: 0 !important;
        margin: 0 !important;
      }
    }
  `;
  // Extract body innerHTML if full HTML document was passed
  let bodyContent = contentHtml;
  const bodyMatch = String(contentHtml).match(/<body[^>]*>([\s\S]*?)<\/body>/i);
  const styleMatches = String(contentHtml).match(/<style[^>]*>([\s\S]*?)<\/style>/gi) || [];
  if (bodyMatch) {
    bodyContent = styleMatches.join('\n') + bodyMatch[1];
  }
  zone.innerHTML = bodyContent;
  document.body.classList.add('pt-printing-custom');
  const cleanup = () => {
    document.body.classList.remove('pt-printing-custom');
    window.removeEventListener('afterprint', cleanup);
  };
  window.addEventListener('afterprint', cleanup);
  setTimeout(() => {
    window.focus();
    window.print();
    setTimeout(cleanup, 1500);
  }, 120);
}
window.triggerDirectInPagePrint = triggerDirectInPagePrint;


window.toggleAiCopilot = toggleAiCopilot;
window.toggleAiSettingsBox = toggleAiSettingsBox;
window.saveAiExternalApiKey = saveAiExternalApiKey;
window.clearAiChatHistory = clearAiChatHistory;
window.sendAiQuickPrompt = sendAiQuickPrompt;
window.handleAiChatSubmit = handleAiChatSubmit;
window.submitAiQuery = submitAiQuery;
window.openThermalBookingReceiptModal = openThermalBookingReceiptModal;
window.openThermalSalesReceiptModal = openThermalSalesReceiptModal;
window.executeThermalPrint = executeThermalPrint;
window.setThermalPaperWidth = setThermalPaperWidth;
window.openBuiltInReportViewer = openBuiltInReportViewer;
window.printHtmlViaInternalIframe = printHtmlViaInternalIframe;
window.downloadCurrentReportHtmlFile = downloadCurrentReportHtmlFile;
window.printHTML = printHTML;


// Dual-Mode Controller (Mode 1: White & Blue | Mode 2: VIP Onyx Black & Royal Gold)
let CURRENT_MAIN_MODE = 1;
let MODE1_USE_LAYOUT3 = false;
let MODE2_USE_LAYOUT3 = false;

function switchMainSystemMode(modeNum) {
    CURRENT_MAIN_MODE = modeNum === 2 ? 2 : 1;
    const btn1 = document.getElementById('btnSwitchMode1');
    const btn2 = document.getElementById('btnSwitchMode2');

    if (CURRENT_MAIN_MODE === 1) {
        document.body.classList.add('system-mode-1', 'theme-light');
        document.body.classList.remove('system-mode-2', 'theme-dark');
        document.body.removeAttribute('data-black-style');
        document.body.classList.toggle('layout-ribbon-dock', MODE1_USE_LAYOUT3);
        document.body.classList.toggle('arch-layout3', MODE1_USE_LAYOUT3);

        if (btn1) btn1.className = 'dm-switch-btn active-mode1';
        if (btn2) btn2.className = 'dm-switch-btn';

        try { localStorage.setItem('photo_team_main_mode', '1'); } catch (e) {}
    } else {
        document.body.classList.remove('system-mode-1', 'theme-light');
        document.body.classList.add('system-mode-2', 'theme-dark');
        document.body.setAttribute('data-black-style', 'black-gold');
        document.body.classList.toggle('layout-ribbon-dock', MODE2_USE_LAYOUT3);
        document.body.classList.toggle('arch-layout3', MODE2_USE_LAYOUT3);

        if (btn1) btn1.className = 'dm-switch-btn';
        if (btn2) btn2.className = 'dm-switch-btn active-mode2';

        try { localStorage.setItem('photo_team_main_mode', '2'); } catch (e) {}
    }
}
window.switchMainSystemMode = switchMainSystemMode;

function toggleMode1MenuArch() {
    if (CURRENT_MAIN_MODE === 1) {
        MODE1_USE_LAYOUT3 = !MODE1_USE_LAYOUT3;
        switchMainSystemMode(1);
    } else {
        MODE2_USE_LAYOUT3 = !MODE2_USE_LAYOUT3;
        switchMainSystemMode(2);
    }
}
window.toggleMode1MenuArch = toggleMode1MenuArch;

(function() {
    let savedMode = '1';
    try { savedMode = localStorage.getItem('photo_team_main_mode') || '1'; } catch (e) {}
    switchMainSystemMode(savedMode === '2' ? 2 : 1);
})();

async function openNgrokMobileModal() {
    let st = { active: false, ngrok_login_url: '', ngrok_interactive_url: '', lan_login_url: location.origin + '/login', port: 5000 };
    try {
        st = await api('/api/ngrok_status');
    } catch (e) {}
    const activeUrl = st.ngrok_login_url || '';
    const qrTarget = activeUrl || st.lan_login_url || (location.origin + '/login');
    showModal(`
        <div class="modal-title" style="flex-direction:row !important;justify-content:space-between !important;align-items:center !important;flex-wrap:wrap;gap:10px;">
            <div>
                <h2>📱 تشغيل ومشاركة لينك الموبايلات عبر Ngrok & Wi-Fi</h2>
                <p>افتح السيستم من أي عدد من الموبايلات في نفس الوقت بقاعدة بيانات موحدة لحظياً</p>
            </div>
            <span class="badge ${st.active ? 'green' : 'amber'}">${st.active ? 'Ngrok متصل الآن ✅' : 'في انتظار تشغيل Ngrok'}</span>
        </div>
        <div class="details-wrapper" style="display:flex;flex-direction:column;gap:14px;">
            <div class="form-section custom-section" style="border:2px solid #0284c7;">
                <h3>🚀 1. لينك Ngrok العام (يعمل من أي موبايل على الإنترنت 4G/5G وفي أي فندق)</h3>
                <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;">
                    <input id="mdlNgrokUrl" class="input" readonly dir="ltr" style="flex:1;min-width:240px;font-weight:900;color:#0284c7;" value="${esc(activeUrl || 'اضغط على زر (تشغيل Ngrok الآن) بالأسفل لتوليد اللينك...')}">
                    <button type="button" class="btn primary" onclick="copyTextValue('mdlNgrokUrl')">📋 نسخ اللينك</button>
                    <button type="button" class="btn green" onclick="shareUrlWhatsApp('mdlNgrokUrl')">💬 إرسال واتساب</button>
                </div>
                <div style="margin-top:12px;padding-top:12px;border-top:1px dashed var(--border);display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
                    <input id="mdlNgrokToken" class="input" dir="ltr" style="flex:1;min-width:220px;" placeholder="اختياري: الصق Ngrok Authtoken هنا لو أول مرة...">
                    <button type="button" class="btn green" onclick="triggerStartNgrokFromModal()">⚡ تشغيل / تحديث Ngrok الآن</button>
                </div>
                <p id="mdlNgrokStatusMsg" style="font-size:12.5px;font-weight:800;color:var(--primary);margin:6px 0 0;"></p>
            </div>

            <div class="form-section custom-section">
                <h3>📶 2. لينك الـ Wi-Fi المحلي (للموبايلات المتصلة بنفس راوتر الكمبيوتر بدون إنترنت)</h3>
                <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;">
                    <input id="mdlLanUrl" class="input" readonly dir="ltr" style="flex:1;min-width:240px;font-weight:800;" value="${esc(st.lan_login_url)}">
                    <button type="button" class="btn primary" onclick="copyTextValue('mdlLanUrl')">📋 نسخ لينك Wi-Fi</button>
                    <button type="button" class="btn green" onclick="shareUrlWhatsApp('mdlLanUrl')">💬 إرسال واتساب</button>
                </div>
            </div>
        </div>
        <div class="modal-actions">
            <button type="button" class="btn" onclick="closeModal()">إغلاق</button>
        </div>
    `, 'modal-lg');
}
window.openNgrokMobileModal = openNgrokMobileModal;

function copyTextValue(inputId) {
    const el = document.getElementById(inputId);
    if (!el || !el.value.startsWith('http')) return toast('قم بتشغيل Ngrok أولاً ليظهر الرابط', 'bad');
    navigator.clipboard.writeText(el.value);
    toast('✅ تم نسخ الرابط بنجاح! يمكنك إرساله لأي موبايل الآن.');
}
window.copyTextValue = copyTextValue;

function shareUrlWhatsApp(inputId) {
    const el = document.getElementById(inputId);
    if (!el || !el.value.startsWith('http')) return toast('قم بتشغيل Ngrok أولاً ليظهر الرابط', 'bad');
    window.open('https://wa.me/?text=' + encodeURIComponent('📸 رابط نظام Photo Team للموبايل: ' + el.value), '_blank');
}
window.shareUrlWhatsApp = shareUrlWhatsApp;

async function triggerStartNgrokFromModal() {
    const msgEl = document.getElementById('mdlNgrokStatusMsg');
    if (msgEl) msgEl.textContent = '⏳ جاري تشغيل Ngrok على بورت 5000 وجلب الرابط...';
    const authtoken = (document.getElementById('mdlNgrokToken')?.value || '').trim();
    try {
        const res = await apiJSON('/api/ngrok_start', 'POST', { authtoken });
        if (document.getElementById('mdlNgrokUrl')) {
            document.getElementById('mdlNgrokUrl').value = res.ngrok_login_url || '';
        }
        if (msgEl) {
            msgEl.style.color = '#059669';
            msgEl.textContent = '✅ تم تشغيل Ngrok بنجاح! انسخ الرابط أعلاه وافتحه من أي موبايل.';
        }
        toast('✅ تم تشغيل لينك Ngrok بنجاح!');
    } catch (e) {
        if (msgEl) {
            msgEl.style.color = '#dc2626';
            msgEl.textContent = '⚠️ ' + e.message;
        }
    }
}
window.triggerStartNgrokFromModal = triggerStartNgrokFromModal;



function fillAiVoiceText(txt) {
    const inp = document.getElementById('aiChatInput');
    if (!inp) return;
    inp.value = txt;
    inp.focus();
    toast('🎙️ تم تحويل الأمر إلى كتابة — اضغط إرسال للتنفيذ الفوري');
}
window.fillAiVoiceText = fillAiVoiceText;

window._BACKEND_SPEECH_REC = null;
window._BACKEND_IS_LISTENING = false;
function toggleBackendAiVoiceMic() {
    const micBtn = document.getElementById('aiMicBtn');
    const banner = document.getElementById('aiVoiceStatusBanner');
    const inp = document.getElementById('aiChatInput');
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (window._BACKEND_IS_LISTENING && window._BACKEND_SPEECH_REC) {
        try { window._BACKEND_SPEECH_REC.stop(); } catch (e) {}
        window._BACKEND_IS_LISTENING = false;
        if (micBtn) micBtn.style.background = '#f8fafc';
        if (banner) banner.hidden = true;
        return;
    }
    if (!SpeechRec) {
        if (banner) {
            banner.hidden = false;
            banner.textContent = '🎙️ اختر أي أمر صوتي من الأزرار بالأعلى أو اكتب أمرك مباشرة.';
        }
        return;
    }
    try {
        const rec = new SpeechRec();
        rec.lang = 'ar-EG';
        rec.continuous = false;
        rec.interimResults = true;
        window._BACKEND_SPEECH_REC = rec;
        window._BACKEND_IS_LISTENING = true;
        if (micBtn) micBtn.style.background = '#fecaca';
        if (banner) {
            banner.hidden = false;
            banner.textContent = '🔴 جاري الاستماع من المايك... اتكلم دلوقتي وهيتحول كلامك لكتابة مباشرة!';
        }
        rec.onresult = function(ev) {
            let t = '';
            for (let i = 0; i < ev.results.length; i++) t += ev.results[i][0].transcript;
            if (inp) inp.value = window.convertSpokenArabicNumbersToDigits ? window.convertSpokenArabicNumbersToDigits(t) : t.trim();
        };
        rec.onerror = function() {
            window._BACKEND_IS_LISTENING = false;
            if (micBtn) micBtn.style.background = '#f8fafc';
        };
        rec.onend = function() {
            window._BACKEND_IS_LISTENING = false;
            if (micBtn) micBtn.style.background = '#f8fafc';
            if (banner) banner.hidden = true;
            if (inp && inp.value.trim()) toast('✅ تم تحويل الصوت لكتابة! اضغط إرسال للتنفيذ.');
        };
        rec.start();
    } catch (e) {
        window._BACKEND_IS_LISTENING = false;
    }
}
window.toggleBackendAiVoiceMic = toggleBackendAiVoiceMic;


// ============================================================================
// 📡 17. نظام وضع عدم الاتصال المؤقت للموبايل (Offline Queue) + قفل حسابات اليوم
// ============================================================================
const OFFLINE_QUEUE_KEY = 'pt_offline_queue_v1';
const OFFLINE_SIM_KEY = 'pt_manual_offline_mode';

function getOfflineQueue() {
  try {
    return JSON.parse(localStorage.getItem(OFFLINE_QUEUE_KEY) || '[]') || [];
  } catch (e) {
    return [];
  }
}

function saveOfflineQueue(list) {
  try {
    localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(list || []));
  } catch (e) {}
  updateOfflineQueueUI();
}

function isOfflineModeActive() {
  try {
    return !navigator.onLine || localStorage.getItem(OFFLINE_SIM_KEY) === '1';
  } catch (e) {
    return false;
  }
}

function toggleManualOfflineMode() {
  try {
    const next = localStorage.getItem(OFFLINE_SIM_KEY) === '1' ? '0' : '1';
    localStorage.setItem(OFFLINE_SIM_KEY, next);
    updateOfflineQueueUI();
    if (next === '1') {
      toast('📴 تم تفعيل وضع عدم الاتصال المؤقت للموبايل — سيتم حفظ الحجوزات والمبيعات محلياً لحين عودة الشبكة', 'amber');
    } else {
      toast('🟢 تم الاتصال بالشبكة — جاري مزامنة العمليات المحفوظة...', 'good');
      syncOfflineQueueNow();
    }
    if ($('globalModal') && !$('globalModal').hidden && $('offlineQueueModalMarker')) {
      openOfflineQueueModal();
    }
  } catch (e) {}
}
window.toggleManualOfflineMode = toggleManualOfflineMode;

function enqueueOfflineOperation(url, method, body, label = '') {
  const q = getOfflineQueue();
  const item = {
    id: Date.now() + Math.floor(Math.random() * 1000),
    url,
    method: method || 'POST',
    body: body || {},
    label: label || describeOfflineOp(url, body),
    created_at: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  };
  q.push(item);
  saveOfflineQueue(q);
  toast(`📡 تم حفظ العملية في طابور عدم الاتصال (${item.label}) — ستُرفع تلقائياً فور عودة الشبكة`, 'amber');
  return item;
}
window.enqueueOfflineOperation = enqueueOfflineOperation;

function describeOfflineOp(url, body = {}) {
  const u = String(url || '');
  if (u.includes('/api/bookings')) return `حجز غرفة ${body.room_number || '-'} (${body.hotel || 'الفندق'})`;
  if (u.includes('/api/daily-sales/notes')) return `ملاحظة دخل (${body.person_name || '-'})`;
  if (u.includes('/api/daily-sales')) return `تسجيل دخل غرفة ${body.room_number || '-'}`;
  if (u.includes('/api/deposits')) return `عربون غرفة ${body.room_number || '-'}`;
  if (u.includes('/api/treasury')) return `حركة خزنة (${body.description || '-'})`;
  return `عملية محفوظة (${u})`;
}

function updateOfflineQueueUI() {
  const q = getOfflineQueue();
  const manualOff = isOfflineModeActive();
  const badge = $('offlineQueueCount');
  const btn = $('offlineQueueTopBtn');
  if (badge) {
    badge.textContent = String(q.length);
    badge.dataset.zero = q.length === 0 ? '1' : '0';
  }
  if (btn) {
    btn.style.borderColor = manualOff ? '#f59e0b' : (q.length > 0 ? '#10b981' : '');
    btn.title = manualOff
      ? `📴 وضع عدم الاتصال نشط (${q.length} عملية بالانتظار)`
      : `📡 طابور عدم الاتصال (${q.length} عملية بالانتظار)`;
  }
}

async function syncOfflineQueueNow() {
  const q = getOfflineQueue();
  if (!q.length) {
    toast('لا توجد عمليات معلقة في طابور عدم الاتصال');
    return;
  }
  if (isOfflineModeActive()) {
    try { localStorage.setItem(OFFLINE_SIM_KEY, '0'); } catch (e) {}
  }
  let synced = 0;
  const remaining = [];
  for (const item of q) {
    try {
      const res = await fetch(item.url, {
        method: item.method || 'POST',
        headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
        body: JSON.stringify(item.body || {})
      });
      if (res.ok) {
        synced++;
      } else {
        remaining.push(item);
      }
    } catch (e) {
      remaining.push(item);
    }
  }
  saveOfflineQueue(remaining);
  if (synced > 0) {
    toast(`✅ تم رفع ومزامنة ${synced} عملية من طابور الموبايل إلى السيرفر بنجاح!`);
    if (typeof loadSalesSearch === 'function') loadSalesSearch();
    if (typeof loadBookings === 'function') loadBookings();
  }
  if ($('globalModal') && !$('globalModal').hidden && $('offlineQueueModalMarker')) {
    openOfflineQueueModal();
  }
}
window.syncOfflineQueueNow = syncOfflineQueueNow;

function removeOfflineQueueItem(itemId) {
  const q = getOfflineQueue().filter(x => Number(x.id) !== Number(itemId));
  saveOfflineQueue(q);
  openOfflineQueueModal();
}
window.removeOfflineQueueItem = removeOfflineQueueItem;

function openOfflineQueueModal() {
  const q = getOfflineQueue();
  const isOff = isOfflineModeActive();
  const rowsHtml = q.length ? q.map((item, idx) => `
    <tr>
      <td>${idx + 1}</td>
      <td><b>${esc(item.label)}</b></td>
      <td dir="ltr">${esc(item.created_at)}</td>
      <td><span class="badge amber">⏳ في انتظار الرفع</span></td>
      <td><button type="button" class="mini-btn red" onclick="removeOfflineQueueItem(${item.id})">🗑️ حذف</button></td>
    </tr>
  `).join('') : `<tr><td colspan="5" class="empty-state">لا توجد عمليات معلقة حالياً — جميع البيانات متزامنة مع السيرفر ✅</td></tr>`;

  showModal(`
    <div id="offlineQueueModalMarker" class="modal-title" style="flex-direction:row !important;justify-content:space-between !important;align-items:center !important;flex-wrap:wrap;gap:10px;">
      <div>
        <h2>📡 وضع عدم الاتصال المؤقت للموبايل (Offline Queue)</h2>
        <p>يحفظ الحجوزات والمبيعات على الموبايل عند ضعف شبكة الشاطئ أو حمام السباحة ويرفعها للسيرفر فور عودة الشبكة</p>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;">
        <button type="button" class="btn ${isOff ? 'amber' : 'primary'}" onclick="toggleManualOfflineMode()">
          ${isOff ? '📴 وضع بدون شبكة: نشط الآن (اضغط للاتصال)' : '📶 الشبكة متصلة (اضغط لتجربة وضع بدون شبكة)'}
        </button>
        <button type="button" class="btn green" onclick="syncOfflineQueueNow()">🔄 مزامنة ورفع الكل الآن (${q.length})</button>
        <button type="button" class="btn" onclick="closeModal()">إغلاق</button>
      </div>
    </div>
    <div class="table-wrap">
      <table class="modern-table">
        <thead>
          <tr><th>#</th><th>تفاصيل العملية المحفوظة</th><th>وقت التسجيل</th><th>الحالة</th><th>إجراء</th></tr>
        </thead>
        <tbody>${rowsHtml}</tbody>
      </table>
    </div>
  `, 'modal-lg');
}
window.openOfflineQueueModal = openOfflineQueueModal;

window.addEventListener('online', () => {
  updateOfflineQueueUI();
  if (getOfflineQueue().length > 0) {
    toast('🟢 عادت الشبكة! جاري رفع العمليات المحفوظة في طابور الموبايل تلقائياً...');
    syncOfflineQueueNow();
  }
});
window.addEventListener('offline', () => {
  updateOfflineQueueUI();
  toast('📴 انقطعت الشبكة — تم تفعيل الحفظ المؤقت تلقائياً (Offline Queue)', 'amber');
});
setTimeout(updateOfflineQueueUI, 200);


// ============================================================================
// 🎙️ V109: محرك تحويل الأرقام المنطوقة بالعربي والعامية المصرية إلى أرقام حسابية (123)
// ============================================================================
(function() {
  const SINGLE_DIGITS = {
    "صفر": 0, "زيرو": 0, "zero": 0,
    "واحد": 1, "واحده": 1, "واحدة": 1, "ون": 1, "one": 1,
    "اتنين": 2, "إتنين": 2, "اثنين": 2, "اثنان": 2, "إثنين": 2, "إثنان": 2, "تو": 2, "two": 2,
    "تلاته": 3, "تلاتة": 3, "ثلاثه": 3, "ثلاثة": 3, "تلات": 3, "ثلاث": 3, "ثري": 3, "three": 3,
    "اربعه": 4, "اربعة": 4, "أربعه": 4, "أربعة": 4, "اربع": 4, "أربع": 4, "فور": 4, "four": 4,
    "خمسه": 5, "خمسة": 5, "خمس": 5, "فايف": 5, "five": 5,
    "سته": 6, "ستة": 6, "ست": 6, "سكس": 6, "six": 6,
    "سبعه": 7, "سبعة": 7, "سبع": 7, "سفن": 7, "seven": 7,
    "تمانيه": 8, "تمانية": 8, "ثمانيه": 8, "ثمانية": 8, "تمن": 8, "ثمان": 8, "ثماني": 8, "ايت": 8, "eight": 8,
    "تسعه": 9, "تسعة": 9, "تسع": 9, "ناين": 9, "nine": 9
  };
  const TEENS = {
    "عشره": 10, "عشرة": 10, "عشر": 10, "تن": 10, "ten": 10,
    "حداشر": 11, "احداشر": 11, "إحداشر": 11, "أحداشر": 11,
    "اتناشر": 12, "إتناشر": 12, "اثناشر": 12, "إثناشر": 12,
    "تلتاشر": 13, "تلاتاشر": 13, "ثلاثتاشر": 13,
    "اربعتاشر": 14, "أربعتاشر": 14,
    "خمستاشر": 15, "ستاشر": 16, "سبعتاشر": 17,
    "تمنتاشر": 18, "ثمانتاشر": 18, "تمانتاشر": 18,
    "تسعتاشر": 19
  };
  const TENS = {
    "عشرين": 20, "عشرون": 20, "تلاتين": 30, "ثلاثين": 30, "ثلاثون": 30,
    "اربعين": 40, "أربعين": 40, "اربعون": 40, "أربعون": 40,
    "خمسين": 50, "خمسون": 50, "ستين": 60, "ستون": 60,
    "سبعين": 70, "سبعون": 70, "تمانين": 80, "ثمانين": 80, "ثمانون": 80,
    "تسعين": 90, "تسعون": 90
  };
  const HUNDREDS = {
    "ميه": 100, "مية": 100, "مائة": 100, "مائه": 100, "مئة": 100, "مئه": 100,
    "ميتين": 200, "مائتين": 200, "مائتان": 200, "مئتين": 200, "مئتان": 200,
    "تلتميه": 300, "تلتمية": 300, "ثلاثمائة": 300, "ثلاثمئة": 300, "تلاتميه": 300, "تلاتمية": 300,
    "اربعميه": 400, "اربعمية": 400, "أربعميه": 400, "أربعمية": 400, "اربعمائة": 400, "أربعمائة": 400, "اربعمئة": 400,
    "خمسميه": 500, "خمسمية": 500, "خمسمائة": 500, "خمسمئة": 500,
    "ستميه": 600, "ستمية": 600, "ستمائة": 600, "ستمئة": 600,
    "سبعميه": 700, "سبعمية": 700, "سبعمائة": 700, "سبعمئة": 700,
    "تمنميه": 800, "تمنمية": 800, "ثمانمائة": 800, "ثمانمئة": 800, "تمانميه": 800, "تمانمية": 800,
    "تسعميه": 900, "تسعمية": 900, "تسعمائة": 900, "تسعمئة": 900
  };
  const THOUSANDS = {
    "الف": 1000, "ألف": 1000, "الفين": 2000, "ألفين": 2000, "ألفان": 2000, "الفان": 2000
  };

  window.convertSpokenArabicNumbersToDigits = function(rawText) {
    if (rawText === null || rawText === undefined) return "";
    let s = String(rawText)
      .replace(/[٠-٩]/g, d => "٠١٢٣٤٥٦٧٨٩".indexOf(d))
      .replace(/[۰-۹]/g, d => "۰۱۲۳۴۵۶۷۸۹".indexOf(d));

    s = s.replace(/الوردر|لوردر|الأوردر|الاوردر|أوردر/g, "اوردر")
         .replace(/أحجز|إحجز/g, "احجز")
         .replace(/غرفه/g, "غرفة")
         .replace(/الغرفه/g, "الغرفة");

    s = s.replace(/(?:أحد|احد|إحدى|احدى)\s+عشر(?:ة|ه)?/g, "حداشر")
         .replace(/(?:اثنا|إثنا|اثني|إثني|اتنين)\s+عشر(?:ة|ه)?/g, "اتناشر")
         .replace(/(?:ثلاثة|ثلاث|تلاته|تلاتة|تلات)\s+عشر(?:ة|ه)?/g, "تلتاشر")
         .replace(/(?:أربعة|اربعة|أربع|اربع|اربعه)\s+عشر(?:ة|ه)?/g, "اربعتاشر")
         .replace(/(?:خمسة|خمس|خمسه)\s+عشر(?:ة|ه)?/g, "خمستاشر")
         .replace(/(?:ستة|ست|سته)\s+عشر(?:ة|ه)?/g, "ستاشر")
         .replace(/(?:سبعة|سبع|سبعه)\s+عشر(?:ة|ه)?/g, "سبعتاشر")
         .replace(/(?:ثمانية|ثماني|تمانية|تمانيه|ثمان)\s+عشر(?:ة|ه)?/g, "تمنتاشر")
         .replace(/(?:تسعة|تسع|تسعه)\s+عشر(?:ة|ه)?/g, "تسعتاشر")
         .replace(/(?:ثلاثة|ثلاث|تلاته|تلاتة|تلات)\s+(?:آلاف|الاف|ألاف)/g, "3000")
         .replace(/(?:أربعة|اربعة|أربع|اربع|اربعه)\s+(?:آلاف|الاف|ألاف)/g, "4000")
         .replace(/(?:خمسة|خمس|خمسه)\s+(?:آلاف|الاف|ألاف)/g, "5000");

    function classifyToken(tok) {
      const clean = tok.replace(/[،,.;:!?]/g, "");
      let hasLeadingWaw = false;
      let base = clean;
      if (clean === "و") return { type: "waw", raw: tok };
      if (clean.startsWith("و") && clean.length > 1) {
        const sub = clean.slice(1);
        if (SINGLE_DIGITS[sub] !== undefined || TEENS[sub] !== undefined || TENS[sub] !== undefined || HUNDREDS[sub] !== undefined || THOUSANDS[sub] !== undefined) {
          hasLeadingWaw = true;
          base = sub;
        }
      }
      if (SINGLE_DIGITS[base] !== undefined) return { type: "digit", val: SINGLE_DIGITS[base], waw: hasLeadingWaw, raw: tok };
      if (TEENS[base] !== undefined) return { type: "teen", val: TEENS[base], waw: hasLeadingWaw, raw: tok };
      if (TENS[base] !== undefined) return { type: "ten", val: TENS[base], waw: hasLeadingWaw, raw: tok };
      if (HUNDREDS[base] !== undefined) return { type: "hundred", val: HUNDREDS[base], waw: hasLeadingWaw, raw: tok };
      if (THOUSANDS[base] !== undefined) return { type: "thousand", val: THOUSANDS[base], waw: hasLeadingWaw, raw: tok };
      if (/^\d+$/.test(base)) return { type: "num_literal", val: base, waw: hasLeadingWaw, raw: tok };
      return { type: "word", raw: tok };
    }

    const rawTokens = s.trim().split(/\s+/).filter(Boolean);
    if (!rawTokens.length) return "";
    const classified = rawTokens.map(classifyToken);
    const out = [];
    let i = 0;

    while (i < classified.length) {
      const cur = classified[i];
      if (cur.type === "word" || cur.type === "waw") {
        out.push(cur.raw);
        i++;
        continue;
      }
      const seq = [cur];
      let j = i + 1;
      while (j < classified.length) {
        if (classified[j].type === "waw" && j + 1 < classified.length && ["digit", "teen", "ten", "hundred", "thousand", "num_literal"].includes(classified[j + 1].type)) {
          seq.push(Object.assign({}, classified[j + 1], { waw: true }));
          j += 2;
        } else if (["digit", "teen", "ten", "hundred", "thousand", "num_literal"].includes(classified[j].type)) {
          seq.push(classified[j]);
          j++;
        } else {
          break;
        }
      }

      if (seq.every(x => x.type === "digit" || x.type === "num_literal")) {
        out.push(seq.map(x => String(x.val)).join(""));
        i = j;
        continue;
      }
      if (seq.length === 2 && !seq[1].waw) {
        if ((seq[0].type === "digit" && seq[1].type === "teen") || (seq[0].type === "teen" && seq[1].type === "digit")) {
          out.push(String(seq[0].val) + String(seq[1].val));
          i = j;
          continue;
        }
        if (seq[0].type === "ten" && seq[1].type === "digit") {
          out.push(String(seq[0].val / 10) + "0" + String(seq[1].val));
          i = j;
          continue;
        }
      }

      let total = 0;
      let k = 0;
      while (k < seq.length) {
        const item = seq[k];
        if (item.type === "digit" && k + 1 < seq.length && seq[k + 1].type === "thousand" && !seq[k + 1].waw) {
          total += item.val * 1000; k += 2;
        } else if (item.type === "digit" && k + 1 < seq.length && seq[k + 1].type === "hundred" && !seq[k + 1].waw) {
          total += item.val * 100; k += 2;
        } else if (item.type === "thousand" || item.type === "hundred" || item.type === "teen") {
          total += item.val; k++;
        } else if (item.type === "digit" && k + 1 < seq.length && seq[k + 1].type === "ten") {
          total += item.val + seq[k + 1].val; k += 2;
        } else if (item.type === "ten" || item.type === "digit") {
          total += item.val; k++;
        } else if (item.type === "num_literal") {
          total += Number(item.val); k++;
        } else {
          k++;
        }
      }
      out.push(String(total));
      i = j;
    }
    return out.join(" ").replace(/\s+/g, " ").trim();
  };

  const _origSubmitAi = window.submitAiQuery;
  if (typeof _origSubmitAi === "function") {
    window.submitAiQuery = async function(q) {
      const converted = window.convertSpokenArabicNumbersToDigits(q);
      return _origSubmitAi(converted);
    };
  }

  let debounceTimer = null;
  document.addEventListener("input", function(ev) {
    const el = ev.target;
    if (!el || el.tagName !== "INPUT") return;
    const id = (el.id || "").toLowerCase();
    const ph = (el.placeholder || "").toLowerCase();
    if (id === "aichatinput" || id.includes("room") || ph.includes("غرفة") || ph.includes("غرفه")) {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function() {
        const val = el.value;
        if (!val) return;
        const converted = window.convertSpokenArabicNumbersToDigits(val);
        if (converted !== val) {
          el.value = converted + (/\s$/.test(val) ? " " : "");
        }
      }, 280);
    }
  });
})();


// ============================================================================
// ⚡➕ نافذة وزرار "إضافة دخل سريع" (Quick Income Modal — يحفظ مباشرة في الدخل اليومي)
// ============================================================================
let _CACHED_QI_TEAM = null;
let _CACHED_QI_HOTELS = null;

async function openQuickIncomeModal(prefill = {}) {
  try {
    const [teamResp, hotelsResp] = await Promise.all([
      apiSafe('/api/team/options', _CACHED_QI_TEAM || { sales: [], photographers: [], all: [] }),
      apiSafe('/api/hotels', _CACHED_QI_HOTELS || [])
    ]);
    _CACHED_QI_TEAM = teamResp || { sales: [], photographers: [], all: [] };
    _CACHED_QI_HOTELS = Array.isArray(hotelsResp) ? hotelsResp : [];
  } catch (e) {
    _CACHED_QI_TEAM = _CACHED_QI_TEAM || { sales: [], photographers: [], all: [] };
    _CACHED_QI_HOTELS = _CACHED_QI_HOTELS || [];
  }

  const salesList = _CACHED_QI_TEAM.sales || [];
  const photoList = _CACHED_QI_TEAM.photographers || [];
  const hotelsList = _CACHED_QI_HOTELS || [];

  const curHotelId = prefill.hotel_id || document.getElementById('dsHotel')?.value || (hotelsList[0]?.id) || 1;
  const curDate = prefill.date || document.getElementById('dsEntryDate')?.value || todayISO();
  const curRoom = prefill.room || '';

  const salesOptionsHtml = `<option value="">-- اختر اسم السيلز --</option>` +
    salesList.map(s => `<option value="${esc(s.nickname)}" ${prefill.sales_person === s.nickname ? 'selected' : ''}>${esc(s.nickname)}</option>`).join('');

  const photoOptions1Html = `<option value="">-- اختر اسم المصور --</option>` +
    photoList.map(p => `<option value="${esc(p.nickname)}" ${prefill.photographer === p.nickname ? 'selected' : ''}>${esc(p.nickname)}</option>`).join('');

  const photoOptions2Html = `<option value="">-- بدون مصور ثاني (اختياري) --</option>` +
    photoList.map(p => `<option value="${esc(p.nickname)}">${esc(p.nickname)}</option>`).join('');

  const hotelOptionsHtml = hotelsList.length
    ? hotelsList.map(h => `<option value="${esc(h.id)}" ${Number(curHotelId) === Number(h.id) ? 'selected' : ''}>${esc(h.hotel_name)}</option>`).join('')
    : `<option value="1">الفندق الرئيسي</option>`;

  showModal(`
    <div class="modal-title" style="flex-direction:row !important;justify-content:space-between !important;align-items:center !important;flex-wrap:wrap;gap:10px;">
      <div>
        <h2>⚡➕ إضافة دخل سريع في الدخل اليومي</h2>
        <p>اختر اسم السيلز واسم المصور من فريق العمل وأدخل المبلغ بأنواعه وعملاته ليُحفظ مباشرة في جدول الدخل اليومي</p>
      </div>
      <button type="button" class="btn" onclick="closeModal()">إغلاق</button>
    </div>

    <form id="quickIncomeModalForm" style="display:flex;flex-direction:column;gap:14px;">
      <div class="form-grid three">
        <div class="field">
          <label style="font-weight:900;color:var(--primary);">💼 اختر اسم السيلز *</label>
          <select class="input" id="qiModalSales" required style="font-weight:800;">
            ${salesOptionsHtml}
          </select>
        </div>
        <div class="field">
          <label style="font-weight:900;color:var(--primary);">📸 اختر اسم المصور *</label>
          <select class="input" id="qiModalPhotog1" required onchange="calcQuickIncomeModalPreview()" style="font-weight:800;">
            ${photoOptions1Html}
          </select>
        </div>
        <div class="field">
          <label>📸 مصور مشارك ثاني (اختياري)</label>
          <select class="input" id="qiModalPhotog2" onchange="calcQuickIncomeModalPreview()">
            ${photoOptions2Html}
          </select>
        </div>
      </div>

      <div class="form-grid three">
        <div class="field">
          <label>🏨 الفندق *</label>
          <select class="input" id="qiModalHotel" required>
            ${hotelOptionsHtml}
          </select>
        </div>
        <div class="field">
          <label>📅 تاريخ الدخل *</label>
          <input class="input" type="date" id="qiModalDate" value="${esc(curDate)}" required>
        </div>
        <div class="field">
          <label>🚪 رقم الغرفة / البيان (اختياري)</label>
          <input class="input" type="text" id="qiModalRoom" value="${esc(curRoom)}" placeholder="رقم الغرفة أو اتركه ليتسجل (دخل سريع)">
        </div>
      </div>

      <div style="padding:12px 14px;border-radius:14px;background:var(--bg-surface-2);border:1.5px solid var(--border-strong);">
        <div style="font-weight:900;font-size:13.5px;margin-bottom:10px;color:var(--text-heading);">💰 المبلغ بأنواعه وعملاته:</div>
        <div class="form-grid four" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:10px;">
          <div class="field">
            <label>💵 دخل دولار ($ USD)</label>
            <input class="input" type="number" step="0.01" id="qiModalUsd" value="${num(prefill.usd || 0)}" oninput="calcQuickIncomeModalPreview()">
          </div>
          <div class="field">
            <label>💶 دخل يورو (€ EUR)</label>
            <input class="input" type="number" step="0.01" id="qiModalEur" value="${num(prefill.eur || 0)}" oninput="calcQuickIncomeModalPreview()">
          </div>
          <div class="field">
            <label>💷 دخل كاش مصري (L.E كاش)</label>
            <input class="input" type="number" step="0.01" id="qiModalCash" value="${num(prefill.cash || 0)}" oninput="calcQuickIncomeModalPreview()">
          </div>
          <div class="field">
            <label>💳 دخل مكتب / فيزا (L.E مكتب)</label>
            <input class="input" type="number" step="0.01" id="qiModalOffice" value="${num(prefill.office || 0)}" oninput="calcQuickIncomeModalPreview()">
          </div>
        </div>
        <div class="form-grid two" style="margin-top:10px;">
          <div class="field">
            <label>عربون مسدد مسبقاً ($) (اختياري)</label>
            <input class="input" type="number" step="0.01" id="qiModalDeposit" value="${num(prefill.deposit || 0)}" oninput="calcQuickIncomeModalPreview()">
          </div>
          <div class="field">
            <label>سعر الصرف (Rate LE/$)</label>
            <input class="input" type="number" step="0.01" id="qiModalRate" value="50" oninput="calcQuickIncomeModalPreview()">
          </div>
        </div>
      </div>

      <details style="padding:8px 12px;border-radius:10px;border:1px dashed var(--border-strong);">
        <summary style="cursor:pointer;font-weight:800;font-size:12.5px;color:var(--text-muted);">➕ إضافة تكاليف على الأوردر (فستان / فلاشة USB / ألبوم — اختياري)</summary>
        <div class="form-grid three" style="margin-top:10px;">
          <div class="field"><label>تكلفة فستان ($)</label><input class="input" type="number" step="0.01" id="qiModalCostDress" value="0" oninput="calcQuickIncomeModalPreview()"></div>
          <div class="field"><label>تكلفة فلاشة USB ($)</label><input class="input" type="number" step="0.01" id="qiModalCostUsb" value="0" oninput="calcQuickIncomeModalPreview()"></div>
          <div class="field"><label>تكلفة ألبوم ($)</label><input class="input" type="number" step="0.01" id="qiModalCostAlbum" value="0" oninput="calcQuickIncomeModalPreview()"></div>
        </div>
      </details>

      <div class="money-summary" style="margin:0;">
        <div class="summary-box"><small>مقابل الجنيه بالدولار</small><strong id="qiModalLeEquiv" style="color:var(--primary);">0.00 $</strong></div>
        <div class="summary-box"><small>إجمالي الدخل (Gross)</small><strong id="qiModalGross">0.00 $</strong></div>
        <div class="summary-box"><small>الصافي النهائي للدخل اليومي</small><strong id="qiModalNet" style="color:#10b981;font-size:18px;">0.00 $</strong></div>
      </div>

      <div class="modal-actions" style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;">
        <button type="button" class="btn" onclick="closeModal()">إلغاء</button>
        <button type="submit" class="btn green" style="font-weight:900;padding:10px 24px;font-size:14px;">💾 حفظ في الدخل اليومي الآن</button>
      </div>
    </form>
  `, 'modal-lg');

  calcQuickIncomeModalPreview();

  document.getElementById('quickIncomeModalForm')?.addEventListener('submit', async function(ev) {
    ev.preventDefault();
    const sales = (document.getElementById('qiModalSales')?.value || '').trim();
    const photog1 = (document.getElementById('qiModalPhotog1')?.value || '').trim();
    const photog2 = (document.getElementById('qiModalPhotog2')?.value || '').trim();
    const hotelId = num(document.getElementById('qiModalHotel')?.value) || 1;
    const entryDate = document.getElementById('qiModalDate')?.value || todayISO();
    const room = (document.getElementById('qiModalRoom')?.value || '').trim() || 'دخل سريع';

    const usd = num(document.getElementById('qiModalUsd')?.value);
    const eur = num(document.getElementById('qiModalEur')?.value);
    const cash = num(document.getElementById('qiModalCash')?.value);
    const office = num(document.getElementById('qiModalOffice')?.value);
    const dep = num(document.getElementById('qiModalDeposit')?.value);
    const rate = num(document.getElementById('qiModalRate')?.value) || 50;
    const costDress = num(document.getElementById('qiModalCostDress')?.value);
    const costUsb = num(document.getElementById('qiModalCostUsb')?.value);
    const costAlbum = num(document.getElementById('qiModalCostAlbum')?.value);

    if (!sales) return toast('⚠️ يرجى اختيار اسم السيلز أولاً', 'bad');
    if (!photog1) return toast('⚠️ يرجى اختيار اسم المصور أولاً', 'bad');

    const gross = dep + usd + eur + ((cash + office) / rate);
    if (gross <= 0) return toast('⚠️ يرجى إدخال المبلغ بأحد أنواعه (دولار، يورو، كاش مصري، أو مكتب)', 'bad');

    const photogs = [photog1];
    if (photog2 && photog2.toLowerCase() !== photog1.toLowerCase()) photogs.push(photog2);
    const photogStr = photogs.join(', ');

    try {
      const res = await apiJSON('/api/daily-sales', 'POST', {
        hotel_id: hotelId,
        room_number: room,
        income_date: entryDate,
        sales_person: sales,
        photographer: photogStr,
        deposit_applied: dep,
        income_usd: usd,
        income_eur: eur,
        income_le_k: cash,
        income_le_m: office,
        le_to_usd: rate,
        cost_dress: costDress,
        cost_usb: costUsb,
        cost_album: costAlbum
      });
      closeModal();
      toast(`✅ تم حفظ الدخل السريع في الدخل اليومي بنجاح! (السيلز: ${sales} • المصور: ${photogStr} • الصافي: $${money(res.daily_total)})`);
      if (typeof loadEligible === 'function') loadEligible();
      if (typeof loadSalesSearch === 'function') loadSalesSearch();
      if (typeof loadAnalytics === 'function') loadAnalytics();
    } catch (err) {
      toast(err.message || 'تعذر حفظ الدخل السريع', 'bad');
    }
  });
}
window.openQuickIncomeModal = openQuickIncomeModal;

function calcQuickIncomeModalPreview() {
  const usd = num(document.getElementById('qiModalUsd')?.value);
  const eur = num(document.getElementById('qiModalEur')?.value);
  const cash = num(document.getElementById('qiModalCash')?.value);
  const office = num(document.getElementById('qiModalOffice')?.value);
  const dep = num(document.getElementById('qiModalDeposit')?.value);
  const rate = num(document.getElementById('qiModalRate')?.value) || 50;
  const cost = num(document.getElementById('qiModalCostDress')?.value) + num(document.getElementById('qiModalCostUsb')?.value) + num(document.getElementById('qiModalCostAlbum')?.value);

  const leEq = (cash + office) / rate;
  const gross = dep + usd + eur + leEq;
  const net = gross - cost;

  if (document.getElementById('qiModalLeEquiv')) document.getElementById('qiModalLeEquiv').textContent = money(leEq) + ' $';
  if (document.getElementById('qiModalGross')) document.getElementById('qiModalGross').textContent = money(gross) + ' $';
  if (document.getElementById('qiModalNet')) document.getElementById('qiModalNet').textContent = money(net) + ' $';
}
window.calcQuickIncomeModalPreview = calcQuickIncomeModalPreview;
