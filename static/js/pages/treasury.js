// ============================================================================
// 📌 ملف الكود البرمجي (treasury.js): كود شاشة الخزنة والمصروفات (إيداع العهدة للأونر، تسجيل المصروفات، وتصدير/طباعة كشف الخزنة)
// ============================================================================

let trsRows = [];
let trsSummary = { total_deposits: 0, total_expenses: 0, balance: 0, expense_count: 0, categories: [] };
let trsHotels = [];
let trsIsCeo = false;

const EXPENSE_CATEGORIES = [
  'طباعة وخامات ألبومات وفلاشات',
  'شراء وصيانة فساتين ومغسلة',
  'صيانة كاميرات ومعدات إضاءة',
  'مواصلات وانتقالات وشحن',
  'إيجارات وفواتير وضيافة فنادق',
  'سلف ومصاريف نثرية',
  'مصاريف تشغيل أخرى'
];

async function initTreasury() {
  if ($('trsMonthFilter')) $('trsMonthFilter').value = monthISO();
  trsHotels = await apiSafe('/api/hotels', [], 'تحميل الفنادق');
  if ($('trsHotelFilter')) {
    $('trsHotelFilter').innerHTML = '<option value="">كل الفنادق</option>' + trsHotels.map(h => `<option value="${h.id}">${esc(h.hotel_name)}</option>`).join('');
  }
  await loadTreasuryData();
}

async function loadTreasuryData() {
  const m = $('trsMonthFilter')?.value || '';
  const t = $('trsTypeFilter')?.value || '';
  const h = $('trsHotelFilter')?.value || '';
  const res = await apiSafe(`/api/treasury?month=${encodeURIComponent(m)}&tx_type=${encodeURIComponent(t)}&hotel_id=${encodeURIComponent(h)}`, { rows: [], summary: {} }, 'تحميل الخزنة');
  trsRows = res.rows || [];
  trsSummary = res.summary || { total_deposits: 0, total_expenses: 0, balance: 0, expense_count: 0, categories: [] };
  trsIsCeo = Boolean(res.is_ceo);
  renderTreasuryUI();
}

function renderTreasuryUI() {
  if ($('trsTotalDeposits')) $('trsTotalDeposits').textContent = money(trsSummary.total_deposits) + ' LE';
  if ($('trsTotalExpenses')) $('trsTotalExpenses').textContent = '-' + money(trsSummary.total_expenses) + ' LE';
  if ($('trsNetBalance')) $('trsNetBalance').textContent = money(trsSummary.balance) + ' LE';
  if ($('trsExpenseCount')) $('trsExpenseCount').textContent = (trsSummary.expense_count || 0) + ' حركة';

  const catBox = $('trsCategoryBreakdown');
  if (catBox) {
    const cats = trsSummary.categories || [];
    catBox.innerHTML = cats.length ? cats.map(c => `
      <div style="padding:9px 12px;border-radius:10px;background:var(--bg-surface);border:1px solid var(--border);">
        <div style="display:flex;justify-content:space-between;align-items:center;font-size:12px;margin-bottom:5px;">
          <b>${esc(c.category)}</b>
          <strong style="color:#ef4444;" dir="ltr">${money(c.amount_egp)} LE (${c.pct}%)</strong>
        </div>
        <div class="capacity-bar" style="height:6px;border-radius:99px;overflow:hidden;">
          <i style="display:block;height:100%;width:${Math.min(100, c.pct)}%;background:linear-gradient(90deg,#f59e0b,#ef4444);"></i>
        </div>
      </div>
    `).join('') : '<div class="empty-state compact">لا توجد مصروفات مسجلة</div>';
  }

  const tbody = $('trsTableBody');
  if (tbody) {
    tbody.innerHTML = trsRows.length ? trsRows.map((r, i) => {
      const isDep = String(r.tx_type).toUpperCase() === 'DEPOSIT';
      return `<tr>
        <td>${i + 1}</td>
        <td>${esc(r.tx_date)}</td>
        <td>${isDep ? '<span class="badge green">➕ إيداع</span>' : '<span class="badge red">➖ مصروف</span>'}</td>
        <td><b>${esc(r.category)}</b></td>
        <td>${esc(r.resolved_hotel || r.hotel_name || 'جميع الفنادق')}</td>
        <td><b>${esc(r.beneficiary || '-')}</b></td>
        <td>${esc(r.description)}</td>
        <td dir="ltr"><b style="color:${isDep ? '#10b981' : '#ef4444'};">${isDep ? '+' : '-'}${money(r.amount_egp)} LE</b></td>
        <td>${esc(r.payment_method || 'نقدي')}</td>
        <td><small>${esc(r.created_by || '-')}</small></td>
        <td>
          ${trsIsCeo ? `
          <div class="context-actions">
            <button type="button" class="mini-btn blue" title="تعديل" onclick="openTreasuryModal('${isDep ? 'DEPOSIT' : 'EXPENSE'}', ${r.id})">✏️</button>
            <button type="button" class="mini-btn red" title="حذف" onclick="deleteTreasuryTx(${r.id})">🗑️</button>
          </div>` : `<span class="badge amber" style="font-size:10px;">🔒 للأونر</span>`}
        </td>
      </tr>`;
    }).join('') : '<tr><td colspan="11" class="empty-state">لا توجد حركات مسجلة</td></tr>';
  }
}

function openTreasuryModal(txType = 'EXPENSE', editId = null) {
  const rec = editId ? trsRows.find(x => Number(x.id) === Number(editId)) : null;
  const finalType = rec ? String(rec.tx_type).toUpperCase() : txType;
  if ((editId || finalType === 'DEPOSIT') && !trsIsCeo) {
    return toast('🔒 التعديل أو الإيداع متاح للأونر فقط', 'bad');
  }
  const isDep = finalType === 'DEPOSIT';
  const hotelOpts = '<option value="">جميع الفنادق</option>' + trsHotels.map(h =>
    `<option value="${h.id}" ${rec && Number(rec.hotel_id) === Number(h.id) ? 'selected' : ''}>${esc(h.hotel_name)}</option>`
  ).join('');
  const catOpts = isDep
    ? '<option value="إيداع عهدة شهرية">إيداع عهدة شهرية</option><option value="تغذية خزنة">تغذية خزنة</option>'
    : EXPENSE_CATEGORIES.map(c => `<option value="${esc(c)}" ${rec && rec.category === c ? 'selected' : ''}>${esc(c)}</option>`).join('');

  showModal(`
    <div class="modal-title">
      <h2>${rec ? '✏️ تعديل حركة #' + rec.id : isDep ? '➕ إيداع رصيد بالخزنة' : '💸 تسجيل مصروف'}</h2>
    </div>
    <form id="trsModalForm">
      <div class="form-grid three">
        <div class="field">
          <label>التاريخ *</label>
          <input type="date" class="input" id="trsFormDate" value="${esc(rec ? String(rec.tx_date).slice(0,10) : todayISO())}" required>
        </div>
        <div class="field">
          <label>${isDep ? 'نوع الإيداع' : 'بند المصروف'} *</label>
          <input type="text" class="input" id="trsFormCategory" value="${esc(rec?.category || (isDep ? 'عهدة شهرية' : ''))}" placeholder="${isDep ? 'اكتب نوع الإيداع...' : 'اكتب هنا المصاريف دي عبارة عن إيه...'}" required>
        </div>
        <div class="field">
          <label>الفندق</label>
          <select class="input" id="trsFormHotel">${hotelOpts}</select>
        </div>
      </div>
      <div class="form-grid three" style="margin-top:10px;">
        <div class="field">
          <label>المبلغ (LE) *</label>
          <input type="number" step=".01" class="input" id="trsFormAmount" value="${num(rec?.amount_egp || (isDep ? 50000 : 0))}" required>
        </div>
        <div class="field">
          <label>${isDep ? 'المستلم *' : 'المستفيد / الجهة *'}</label>
          <input class="input" id="trsFormBeneficiary" value="${esc(rec?.beneficiary || '')}" required>
        </div>
        <div class="field">
          <label>طريقة الدفع</label>
          <select class="input" id="trsFormMethod">
            <option value="نقدي" ${rec?.payment_method==='نقدي'?'selected':''}>نقدي</option>
            <option value="تحويل بنكي / انستاباي" ${rec?.payment_method==='تحويل بنكي / انستاباي'?'selected':''}>تحويل بنكي / انستاباي</option>
            <option value="فودافون كاش" ${rec?.payment_method==='فودافون كاش'?'selected':''}>فودافون كاش</option>
          </select>
        </div>
      </div>
      <div class="field" style="margin-top:10px;">
        <label>البيان *</label>
        <input class="input" id="trsFormDesc" value="${esc(rec?.description || '')}" required>
      </div>
      <div class="modal-actions">
        <button type="button" class="btn" onclick="closeModal()">إلغاء</button>
        <button type="submit" class="btn ${isDep ? 'primary' : 'green'}">💾 حفظ</button>
      </div>
    </form>
  `, 'modal-lg');

  $('trsModalForm').addEventListener('submit', async e => {
    e.preventDefault();
    try {
      await apiJSON('/api/treasury', 'POST', {
        id: rec?.id || undefined,
        tx_type: finalType,
        tx_date: $('trsFormDate').value,
        category: $('trsFormCategory').value,
        hotel_id: num($('trsFormHotel').value) || null,
        amount_egp: num($('trsFormAmount').value),
        beneficiary: $('trsFormBeneficiary').value.trim(),
        payment_method: $('trsFormMethod').value,
        description: $('trsFormDesc').value.trim()
      });
      closeModal();
      toast('تم الحفظ بنجاح');
      await loadTreasuryData();
    } catch (err) {
      toast(err.message, 'bad');
    }
  });
}

async function deleteTreasuryTx(id) {
  if (!trsIsCeo) return toast('🔒 الحذف متاح للأونر فقط', 'bad');
  if (!confirmAction('تأكيد حذف السجل؟')) return;
  try {
    await api(`/api/treasury/${id}`, { method: 'DELETE' });
    toast('تم الحذف');
    await loadTreasuryData();
  } catch (err) {
    toast(err.message, 'bad');
  }
}

function exportTreasuryCSV() {
  downloadCSV(
    `Treasury_${todayISO()}.csv`,
    ['#', 'التاريخ', 'النوع', 'البند', 'الفندق', 'المستفيد', 'البيان', 'المبلغ (LE)', 'طريقة الدفع', 'المسؤول'],
    trsRows.map((r, i) => [
      i + 1,
      r.tx_date,
      String(r.tx_type).toUpperCase() === 'DEPOSIT' ? 'إيداع (+)' : 'مصروف (-)',
      r.category,
      r.resolved_hotel || r.hotel_name || 'جميع الفنادق',
      r.beneficiary || '-',
      r.description,
      (String(r.tx_type).toUpperCase() === 'DEPOSIT' ? '+' : '-') + money(r.amount_egp),
      r.payment_method || 'نقدي',
      r.created_by || '-'
    ])
  );
}

function printTreasuryPDF() {
  const rowsHtml = trsRows.map((r, i) => {
    const isDep = String(r.tx_type).toUpperCase() === 'DEPOSIT';
    return `<tr>
      <td>${i + 1}</td>
      <td>${esc(r.tx_date)}</td>
      <td>${isDep ? 'إيداع' : 'مصروف'}</td>
      <td><b>${esc(r.category)}</b></td>
      <td>${esc(r.resolved_hotel || r.hotel_name || 'جميع الفنادق')}</td>
      <td>${esc(r.beneficiary || '-')}</td>
      <td>${esc(r.description)}</td>
      <td dir="ltr"><b>${isDep ? '+' : '-'}${money(r.amount_egp)} LE</b></td>
    </tr>`;
  }).join('');
  const w = window.open('', '_blank');
  if (!w) return window.print();
  w.document.write(`<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>كشف الخزنة والمصروفات</title>
    <style>body{font-family:Tahoma,sans-serif;padding:20px;direction:rtl;}table{width:100%;border-collapse:collapse;margin-top:12px;font-size:12px;}th{background:#1e3a8a;color:#fff;padding:8px;border:1px solid #1e3a8a;}td{padding:6px;border:1px solid #cbd5e1;text-align:center;}</style>
    </head><body>
    <h2>🏦 PHOTO TEAM — كشف الخزنة والمصروفات</h2>
    <p>إجمالي الإيداعات: <b>${money(trsSummary.total_deposits)} LE</b> • إجمالي المصروفات: <b>${money(trsSummary.total_expenses)} LE</b> • الرصيد الحالي: <b>${money(trsSummary.balance)} LE</b></p>
    <table><thead><tr><th>#</th><th>التاريخ</th><th>النوع</th><th>البند</th><th>الفندق</th><th>المستفيد</th><th>البيان</th><th>المبلغ (LE)</th></tr></thead><tbody>${rowsHtml}</tbody></table>
    </body></html>`);
  w.document.close();
  w.focus();
  w.print();
}

document.addEventListener('DOMContentLoaded', initTreasury);
