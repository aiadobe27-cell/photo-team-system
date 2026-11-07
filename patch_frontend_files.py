#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

ROOT = Path("/working_dir/c_0788515bf7bf9bd8/project_src")

# ============================================================================
# 1. PATCH static/js/pages/login.js & templates/login.html
# ============================================================================
login_js_path = ROOT / "static/js/pages/login.js"
login_js = login_js_path.read_text(encoding="utf-8")

# Replace switchAuthTab to enforce display:flex / display:none and remove 3-word restriction
login_js = login_js.replace(
'''    if (full_name.split(/\\s+/).length < 3) {
        return showAuthFeedback("يرجى كتابة الاسم الحقيقي رباعي بالكامل", "bad");
    }''',
'''    if (full_name.length < 2) {
        return showAuthFeedback("يرجى كتابة الاسم بالكامل", "bad");
    }'''
)

old_switch_tab = '''function switchAuthTab(tabName) {
    clearAuthFeedback();
    document.querySelectorAll(".auth-tab-btn").forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.authTab === tabName);
    });
    const forms = {
        login: document.getElementById("loginForm"),
        register: document.getElementById("registerForm"),
        reset: document.getElementById("resetPasswordForm")
    };
    Object.entries(forms).forEach(([key, el]) => {
        if (!el) return;
        const isTarget = key === tabName;
        el.hidden = !isTarget;
        el.classList.toggle("active", isTarget);
    });'''

new_switch_tab = '''function switchAuthTab(tabName) {
    clearAuthFeedback();
    document.querySelectorAll(".auth-tab-btn").forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.authTab === tabName);
    });
    const forms = {
        login: document.getElementById("loginForm"),
        register: document.getElementById("registerForm"),
        reset: document.getElementById("resetPasswordForm")
    };
    Object.entries(forms).forEach(([key, el]) => {
        if (!el) return;
        const isTarget = key === tabName;
        el.hidden = !isTarget;
        el.style.display = isTarget ? "flex" : "none";
        el.classList.toggle("active", isTarget);
    });'''

if old_switch_tab in login_js:
    login_js = login_js.replace(old_switch_tab, new_switch_tab, 1)

login_js_path.write_text(login_js, encoding="utf-8")

login_html_path = ROOT / "templates/login.html"
login_html = login_html_path.read_text(encoding="utf-8")
login_html = login_html.replace("الاسم الحقيقي (رباعي بالكامل)", "الاسم بالكامل")
login_html = login_html.replace("اكتب اسمك الرباعي الحقيقي...", "اكتب اسمك بالكامل...")
login_html = login_html.replace(
'''                        <option value="Photographer">📸 مصور (Photographer)</option>
                        <option value="Sales">💼 سيلز (Sales)</option>''',
'''                        <option value="Photographer">📸 مصور (Photographer)</option>
                        <option value="Sales">💼 سيلز (Sales)</option>
                        <option value="Accountant">🧮 محاسب (Accountant)</option>
                        <option value="Manager">🏨 مدير فرع (Manager)</option>'''
)
#Replace text on login theme switcher so it's also a sleek icon toggle without "نهاري / ليلي"
login_html = re.sub(
    r'<div class="theme-switch" title="تبديل المظهر">.*?</div>',
    '''<div class="theme-switch pure-toggle-switch" id="loginPureToggle" onclick="setLoginThemeMode(document.body.classList.contains('system-mode-2') ? 1 : 2)" title="تبديل المظهر">
        <button id="lightBtn" type="button" class="active" aria-label="Light">☀️</button>
        <button id="darkBtn" type="button" aria-label="Dark">🌙</button>
        <span class="toggle-Variable-Thumb"></span>
    </div>''',
    login_html,
    flags=re.DOTALL
)
login_html_path.write_text(login_html, encoding="utf-8")
print("✅ Patched login.js and login.html")

# ============================================================================
# 2. PATCH static/js/core/app.js:
#    - Modern Formatted RTL Excel Sheet export in downloadCSV()
#    - Quick Self-Service Change Password Modal (openQuickChangePasswordModal)
# ============================================================================
app_js_path = ROOT / "static/js/core/app.js"
app_js = app_js_path.read_text(encoding="utf-8")

old_download_csv_pattern = re.compile(
    r"async function downloadCSV\(filename, headers = \[\], rows = \[\]\) \{.*?\n\}\nwindow\.downloadCSV = downloadCSV;",
    re.DOTALL
)

new_download_csv = '''function buildModernExcelSpreadsheetHtml(titleText, headers = [], rows = []) {
  const safeHeaders = (headers || []).map(h => String(h ?? ''));
  const safeRows = Array.isArray(rows) ? rows : [];
  const colSums = safeHeaders.map(() => 0);
  const colHasNumeric = safeHeaders.map(() => false);

  safeRows.forEach(r => {
    (r || []).forEach((cell, idx) => {
      if (idx === 0) return; // عمود المسلسل أو الكود الأول لا يُجمع
      const hName = String(safeHeaders[idx] || '');
      if (hName.includes('غرفة') || hName.includes('تاريخ') || hName.includes('تليفون') || hName.includes('هاتف') || hName.includes('نسبة') || hName.includes('سعر الصرف') || hName.includes('الريت')) return;
      const cleaned = String(cell ?? '').replace(/[,$€£EGPLE%\\s]/gi, '').trim();
      if (cleaned !== '' && !isNaN(Number(cleaned)) && /^-?\\d+(\\.\\d+)?$/.test(cleaned)) {
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
  const baseStem = String(filename || 'PhotoTeam_Export').replace(/\\.(csv|xls|xlsx)$/i, '');
  const xlsFilename = `${baseStem}.xls`;
  const titleLabel = baseStem.replace(/_/g, ' ');
  const styledExcelHtml = buildModernExcelSpreadsheetHtml(titleLabel, headers, rows);

  // 1) تنزيل ملف إكسيل منسق ومودرن (.xls) يعمل مباشرة في Microsoft Excel بالألوان والجدول المنسق
  try {
    const blob = new Blob(['\\ufeff' + styledExcelHtml], { type: 'application/vnd.ms-excel;charset=utf-8;' });
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
window.openQuickChangePasswordModal = openQuickChangePasswordModal;'''

assert old_download_csv_pattern.search(app_js), "downloadCSV block not found in app.js"
app_js = old_download_csv_pattern.sub(lambda m: new_download_csv, app_js, count=1)
app_js_path.write_text(app_js, encoding="utf-8")
print("✅ Patched static/js/core/app.js")
