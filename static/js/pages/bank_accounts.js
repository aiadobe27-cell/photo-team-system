// ============================================================================
// 📌 ملف الكود البرمجي (bank_accounts.js): شاشة حسابات البنك وإجمالي جميع أنواع الدخل (للأونر فقط)
// ============================================================================

let bkHotels = [], bkRawRows = [], bkRateUsd = 50, bkRateEur = 54;

async function initBankAccountsPage() {
  if ($('bkFrom')) $('bkFrom').value = firstDayMonth();
  if ($('bkTo')) $('bkTo').value = todayISO();
  try {
    bkHotels = await api('/api/hotels');
    if ($('bkHotel')) {
      $('bkHotel').innerHTML = '<option value="">🌐 جميع الفنادق (إجمالي الكل)</option>' +
        bkHotels.map(h => `<option value="${h.id}">${esc(h.hotel_name)}</option>`).join('');
    }
  } catch (e) {}
  await loadBankAccountsOverview();
}

async function loadBankAccountsOverview() {
  try {
    const q = new URLSearchParams({
      start: $('bkFrom')?.value || firstDayMonth(),
      end: $('bkTo')?.value || todayISO(),
      hotel_id: $('bkHotel')?.value || ''
    });
    const res = await api('/api/bank-accounts/overview?' + q.toString());
    bkRawRows = res.rows || [];
    bkRateUsd = Number(res.exchange_rate_usd || 50) || 50;
    bkRateEur = Number(res.exchange_rate_eur || 54) || 54;
    renderBankAccountsData();
  } catch (e) {
    toast(e.message || 'تعذر تحميل بيانات حسابات البنك', 'bad');
  }
}

function getFilteredBkRows() {
  const typeF = $('bkIncomeType')?.value || 'ALL';
  const statusF = $('bkVisaStatus')?.value || 'ALL';
  const q = String($('bkSearch')?.value || '').trim().toLowerCase();

  return bkRawRows.filter(r => {
    const usd = num(r.income_usd) + num(r.deposit_usd) + num(r.deposit_applied);
    const eur = num(r.income_eur) + num(r.deposit_eur);
    const leCash = num(r.income_le_k) + num(r.deposit_le_cash);
    const leVisa = num(r.income_le_m) + num(r.deposit_le_visa);
    const settled = Boolean(r.bank_visa_settled);

    if (statusF === 'SETTLED' && !settled) return false;
    if (statusF === 'PENDING' && settled) return false;

    if (typeF === 'VISA' && leVisa <= 0) return false;
    if (typeF === 'USD' && usd <= 0) return false;
    if (typeF === 'EUR' && eur <= 0) return false;
    if (typeF === 'LE_CASH' && leCash <= 0) return false;
    if (typeF === 'DEPOSIT' && (num(r.deposit_applied) + num(r.deposit_usd) + num(r.deposit_le_cash) + num(r.deposit_le_visa)) <= 0) return false;

    if (q) {
      const hay = `${r.hotel_name || ''} ${r.room_number || ''} ${r.sales_person || ''} ${r.photographer || ''} ${r.income_date || ''}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function renderBankAccountsData() {
  const rows = getFilteredBkRows();
  const feePct = num($('bkFeePct')?.value ?? 1.5);

  let sumUsd = 0, sumEur = 0, sumLeCash = 0, sumVisaGross = 0, sumVisaSettled = 0, sumVisaPending = 0;
  const byHotel = {};

  rows.forEach(r => {
    const u = num(r.income_usd) + num(r.deposit_applied);
    const e = num(r.income_eur);
    const lc = num(r.income_le_k) + num(r.deposit_le_cash);
    const lv = num(r.income_le_m) + num(r.deposit_le_visa);
    const settled = Boolean(r.bank_visa_settled);

    sumUsd += u;
    sumEur += e;
    sumLeCash += lc;
    sumVisaGross += lv;
    if (settled) sumVisaSettled += lv;
    else sumVisaPending += lv;

    const hName = r.hotel_name || 'الفندق الرئيسي';
    if (!byHotel[hName]) {
      byHotel[hName] = { count: 0, usd: 0, eur: 0, leCash: 0, visaGross: 0, visaSettled: 0, visaPending: 0 };
    }
    byHotel[hName].count += 1;
    byHotel[hName].usd += u;
    byHotel[hName].eur += e;
    byHotel[hName].leCash += lc;
    byHotel[hName].visaGross += lv;
    if (settled) byHotel[hName].visaSettled += lv;
    else byHotel[hName].visaPending += lv;
  });

  const visaFee = sumVisaGross * (feePct / 100);
  const visaNet = Math.max(0, sumVisaGross - visaFee);
  const grandEgp = (sumUsd * bkRateUsd) + (sumEur * bkRateEur) + sumLeCash + visaNet;
  const grandUsd = grandEgp / bkRateUsd;

  if ($('kpiBkUsd')) $('kpiBkUsd').textContent = '$' + money(sumUsd);
  if ($('kpiBkEur')) $('kpiBkEur').textContent = '€' + money(sumEur);
  if ($('kpiBkLeCash')) $('kpiBkLeCash').textContent = money(sumLeCash, 0) + ' LE';
  if ($('kpiBkVisaGross')) $('kpiBkVisaGross').textContent = money(sumVisaGross, 0) + ' LE';
  if ($('kpiBkVisaFee')) $('kpiBkVisaFee').textContent = `عمولة الماكينة (${feePct}%): ${money(visaFee, 1)} LE`;
  if ($('kpiBkVisaNet')) $('kpiBkVisaNet').textContent = money(visaNet, 0) + ' LE';
  if ($('kpiBkVisaSplit')) $('kpiBkVisaSplit').textContent = `✅ نزل: ${money(sumVisaSettled, 0)} LE | ⏳ معلق: ${money(sumVisaPending, 0)} LE`;
  if ($('kpiBkGrandUsd')) $('kpiBkGrandUsd').textContent = '$' + money(grandUsd);
  if ($('kpiBkGrandEgp')) $('kpiBkGrandEgp').textContent = `المعادل بالمصري: ${money(grandEgp, 0)} LE`;

  const hotelEntries = Object.entries(byHotel);
  if ($('bkHotelsSummaryBody')) {
    const hRowsHtml = hotelEntries.map(([hName, st]) => {
      const hNetVisa = st.visaGross * (1 - feePct / 100);
      const hEgp = (st.usd * bkRateUsd) + (st.eur * bkRateEur) + st.leCash + hNetVisa;
      const hUsd = hEgp / bkRateUsd;
      return `
        <tr>
          <td><b>🏨 ${esc(hName)}</b></td>
          <td>${st.count}</td>
          <td class="text-green">$${money(st.usd)}</td>
          <td class="text-blue">€${money(st.eur)}</td>
          <td>${money(st.leCash, 0)} LE</td>
          <td><b>${money(st.visaGross, 0)} LE</b></td>
          <td class="text-green">${money(st.visaSettled, 0)} LE</td>
          <td class="text-amber">${money(st.visaPending, 0)} LE</td>
          <td class="text-blue"><b>${money(hNetVisa, 0)} LE</b></td>
          <td class="text-green"><b>$${money(hUsd)}</b></td>
          <td><b>${money(hEgp, 0)} LE</b></td>
        </tr>
      `;
    }).join('');

    const totalRowHtml = `
      <tr style="font-weight:900;border-top:2px solid var(--primary);">
        <td>💎 الإجمالي العام</td>
        <td>${rows.length}</td>
        <td class="text-green">$${money(sumUsd)}</td>
        <td class="text-blue">€${money(sumEur)}</td>
        <td>${money(sumLeCash, 0)} LE</td>
        <td>${money(sumVisaGross, 0)} LE</td>
        <td class="text-green">${money(sumVisaSettled, 0)} LE</td>
        <td class="text-amber">${money(sumVisaPending, 0)} LE</td>
        <td class="text-blue">${money(visaNet, 0)} LE</td>
        <td class="text-green">$${money(grandUsd)}</td>
        <td>${money(grandEgp, 0)} LE</td>
      </tr>
    `;
    $('bkHotelsSummaryBody').innerHTML = hRowsHtml + totalRowHtml;
  }

  if ($('bkLedgerBody')) {
    $('bkLedgerBody').innerHTML = rows.map(r => {
      const u = num(r.income_usd) + num(r.deposit_applied);
      const lc = num(r.income_le_k) + num(r.deposit_le_cash);
      const lv = num(r.income_le_m) + num(r.deposit_le_visa);
      const fee = lv * (feePct / 100);
      const netV = Math.max(0, lv - fee);
      const settled = Boolean(r.bank_visa_settled);
      return `
        <tr>
          <td>${esc(r.income_date || '-')}</td>
          <td><b>${esc(r.hotel_name || '-')}</b></td>
          <td><b>${esc(r.room_number || '-')}</b></td>
          <td>${esc(r.sales_person || '-')} / ${esc(r.photographer || '-')}</td>
          <td class="text-green">$${money(u)}</td>
          <td class="text-blue">€${money(r.income_eur)}</td>
          <td>${money(lc, 0)} LE</td>
          <td><b>${money(lv, 0)} LE</b></td>
          <td class="text-red">${money(fee, 1)} LE</td>
          <td class="text-blue"><b>${money(netV, 1)} LE</b></td>
          <td class="text-green"><b>$${money(r.daily_total)}</b></td>
          <td>${lv <= 0 ? '<span class="badge">كاش</span>' : settled ? '<span class="badge green">✅ نزل بالبنك</span>' : '<span class="badge amber">⏳ معلق بالبنك</span>'}</td>
          <td>${lv > 0 ? `<button class="mini-btn ${settled ? 'amber' : 'green'}" onclick="toggleBankRowVisa(${r.id})">${settled ? '↩️ تعليق' : '✅ تأكيد نزول'}</button>` : '-'}</td>
        </tr>
      `;
    }).join('') || '<tr><td colspan="13" class="empty-state">لا توجد حركات مطابقة</td></tr>';
  }
}

async function toggleBankRowVisa(id) {
  try {
    await apiJSON('/api/bank-accounts/toggle-visa', 'POST', { id });
    await loadBankAccountsOverview();
    toast('✅ تم تحديث حالة تحصيل الفيزا في حساب البنك');
  } catch (e) {
    toast(e.message, 'bad');
  }
}

async function settleAllBankVisa() {
  try {
    const res = await apiJSON('/api/bank-accounts/settle-all', 'POST', {
      start: $('bkFrom')?.value || firstDayMonth(),
      end: $('bkTo')?.value || todayISO(),
      hotel_id: $('bkHotel')?.value || ''
    });
    await loadBankAccountsOverview();
    toast(res.message || '✅ تم تأكيد نزول جميع عمليات الفيزا المعلقة بالبنك');
  } catch (e) {
    toast(e.message, 'bad');
  }
}

function exportBankOverviewExcel() {
  const rows = getFilteredBkRows();
  const feePct = num($('bkFeePct')?.value ?? 1.5);
  const out = rows.map(r => {
    const u = num(r.income_usd) + num(r.deposit_applied);
    const lc = num(r.income_le_k) + num(r.deposit_le_cash);
    const lv = num(r.income_le_m) + num(r.deposit_le_visa);
    const fee = lv * (feePct / 100);
    const netV = Math.max(0, lv - fee);
    return [
      r.income_date || '',
      r.hotel_name || '',
      r.room_number || '',
      `${r.sales_person || ''} / ${r.photographer || ''}`,
      money(u),
      money(r.income_eur),
      money(lc, 0),
      money(lv, 0),
      money(fee, 1),
      money(netV, 1),
      money(r.daily_total),
      lv <= 0 ? 'كاش' : (r.bank_visa_settled ? 'نزل بالبنك' : 'معلق بالبنك')
    ];
  });
  downloadCSV(
    `كشف_حسابات_البنك_والدخل_الشامل_${todayISO()}.csv`,
    ['التاريخ', 'الفندق', 'الغرفة', 'السيلز / المصور', 'دولار $', 'يورو €', 'كاش مصري LE', 'فيزا البنك LE', 'عمولة البنك LE', 'صافي الفيزا LE', 'إجمالي الأوردر $', 'حالة الفيزا'],
    out
  );
}

function printBankOverviewPDF() {
  const summaryHtml = $('bkHotelsSummaryBody')?.innerHTML || '';
  printHTML('تقرير حسابات البنك وإجمالي جميع أنواع الدخل (خاص بالأونر CEO)', `
    <table>
      <thead>
        <tr><th>الفندق</th><th>الأوردرات</th><th>دولار $</th><th>يورو €</th><th>كاش مصري LE</th><th>فيزا البنك LE</th><th>نزل بالبنك ✅</th><th>معلق ⏳</th><th>صافي الفيزا LE</th><th>إجمالي الدخل $</th><th>المعادل بالمصري LE</th></tr>
      </thead>
      <tbody>${summaryHtml}</tbody>
    </table>
  `);
}

async function triggerSystemBackupSaveAs() {
  try {
    const res = await fetch('/api/backup/save-dialog', { method: 'POST' });
    if (res.ok) {
      const data = await res.json();
      if (data && data.saved && data.path) {
        return toast(`✅ تم حفظ النسخة الاحتياطية في: ${data.path}`);
      }
      if (data && data.cancelled) {
        return toast('تم إلغاء الحفظ', 'bad');
      }
    }
  } catch (e) {}
  location.href = '/api/backup/export';
}

document.addEventListener('DOMContentLoaded', initBankAccountsPage);
