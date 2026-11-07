#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

ROOT = Path("/working_dir/c_0788515bf7bf9bd8/project_src")

# ============================================================================
# 1. PATCH static/js/pages/daily_sales.js:
#    - Unified Official Daily Report builder (used by both printSalesReport & printAllHotelsReportPDF)
#    - Coin Safe movements filtered strictly to the single report day (targetDay)
#    - Deposits strictly matched to their exact hotel (no !d.hotel_name bug, no fake deposits)
# ============================================================================
ds_js_path = ROOT / "static/js/pages/daily_sales.js"
ds_js = ds_js_path.read_text(encoding="utf-8")

old_print_sales_pattern = re.compile(
    r"async function printSalesReport\(\) \{.*?\n\}\ninitDaily\(\);",
    re.DOTALL
)

new_print_sales_block = '''const OFFICIAL_DAILY_REPORT_CSS = `
  @page { size: A4 landscape; margin: 8mm; }
  body { font-family: 'Cairo', 'Segoe UI', Tahoma, sans-serif; color: #1e293b; margin: 0; padding: 12px; background: #fff; font-size: 11px; direction: rtl; }
  .report-page-break { page-break-before: always; break-before: page; padding-top: 8px; }
  .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #1e3a8a; padding-bottom: 10px; margin-bottom: 12px; }
  .header-title h1 { margin: 0; font-size: 20px; color: #1e3a8a; font-weight: 900; }
  .header-title p { margin: 3px 0 0; color: #64748b; font-size: 11.5px; font-weight: bold; }
  .header-meta { text-align: left; background: #f8fafc; padding: 7px 14px; border-radius: 8px; border: 1px solid #cbd5e1; font-size: 11px; line-height: 1.5; }
  .grand-box { background: linear-gradient(135deg, #1e3a8a, #0f172a); color: #fff; padding: 10px 18px; border-radius: 10px; display: flex; justify-content: space-around; align-items: center; margin-bottom: 12px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .g-item { text-align: center; }
  .g-item span { display: block; font-size: 11px; color: #94a3b8; font-weight: bold; margin-bottom: 2px; }
  .g-item strong { font-size: 18px; font-weight: 900; }
  .kpi-container { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; margin-bottom: 12px; }
  .kpi-card { background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 4px; text-align: center; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .kpi-card span { display: block; font-size: 9.5px; color: #475569; font-weight: bold; margin-bottom: 2px; }
  .kpi-card strong { font-size: 12.5px; color: #0f172a; font-weight: 900; }
  .section-title { background: #e2e8f0; color: #1e3a8a; padding: 5px 10px; font-size: 12px; font-weight: 900; border-right: 4px solid #1e3a8a; margin: 10px 0 6px 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 10px; font-size: 10.5px; }
  th { background: #1e3a8a; color: #ffffff; padding: 6px 4px; font-weight: bold; border: 1px solid #1e3a8a; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  td { padding: 5px 4px; border: 1px solid #cbd5e1; text-align: center; }
  tr:nth-child(even) td { background: #f8fafc; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .footer-signatures { margin-top: 14px; display: flex; justify-content: space-between; font-weight: bold; font-size: 11.5px; color: #334155; padding: 0 30px; }
`;

function buildSingleHotelOfficialReportSection({
  titleLabel,
  subtitleLabel,
  start,
  end,
  targetDay,
  sRows = [],
  dRows = [],
  cRowsToday = [],
  nRows = [],
  pageBadge = ''
}) {
  let t_dep = 0, t_usd = 0, t_eur = 0, t_cash = 0, t_office = 0;
  let t_dress = 0, t_usb = 0, t_album = 0, t_gross = 0, t_costs = 0, t_net = 0;

  sRows.forEach(r => {
    t_dep += num(r.deposit_applied);
    t_usd += num(r.income_usd);
    t_eur += num(r.income_eur);
    t_cash += num(r.income_le_k);
    t_office += num(r.income_le_m);
    t_dress += num(r.cost_dress);
    t_usb += num(r.cost_usb);
    t_album += num(r.cost_album);
    t_gross += num(r.gross_total);
    t_costs += num(r.cost_total);
    t_net += num(r.daily_total);
  });

  let dep_usd = 0, dep_eur = 0, dep_cash = 0, dep_visa = 0, dep_equiv = 0;
  dRows.forEach(d => {
    const u = num(d.deposit_usd), e = num(d.deposit_eur), c = num(d.deposit_le_cash), v = num(d.deposit_le_visa);
    dep_usd += u; dep_eur += e; dep_cash += c; dep_visa += v;
    dep_equiv += (u + e + ((c + v) / 50));
  });

  let coin_in = 0, coin_out = 0;
  cRowsToday.forEach(r => {
    if (String(r.transaction_type || '').toUpperCase() === 'IN') coin_in += num(r.amount);
    else coin_out += num(r.amount);
  });
  const coin_today_net = coin_in - coin_out;

  const notes_in = nRows.filter(n => String(n.note_type || '').toUpperCase() === 'IN').reduce((s, n) => s + num(n.equivalent_usd), 0);
  const notes_out = nRows.filter(n => String(n.note_type || '').toUpperCase() !== 'IN').reduce((s, n) => s + num(n.equivalent_usd), 0);
  const final_net_after_notes = t_net + notes_in - notes_out;

  const sales_table_body = sRows.length ? sRows.map(r => {
    const net = num(r.daily_total);
    const phRaw = r.photographer || '';
    const phList = phRaw.split(/[+,،/\\\\|&]+/).map(s => s.trim()).filter(Boolean);
    let phFormatted = esc(phRaw);
    if (phList.length > 1) {
      const share = (net / phList.length).toFixed(2);
      phFormatted = phList.map(p => `${esc(p)} <b style="color:#d97706;">($${share})</b>`).join(' + ');
    } else if (phList.length === 1) {
      phFormatted = `${esc(phList[0])} <b style="color:#16a34a;">($${net.toFixed(2)})</b>`;
    }
    const dStr = (r.income_date || '').substring(0, 10);
    return `<tr>
      <td>${dStr}</td>
      <td style="font-weight:900;color:#1e3a8a;font-size:11.5px;">${esc(r.room_number)}</td>
      <td style="font-weight:bold;">${esc(r.sales_person)}</td>
      <td style="font-size:10.5px;">${phFormatted}</td>
      <td>$${money(r.deposit_applied)}</td>
      <td>$${money(r.income_usd)}</td>
      <td>€${money(r.income_eur)}</td>
      <td>${money(r.income_le_k)}</td>
      <td>${money(r.income_le_m)}</td>
      <td style="font-weight:bold;color:#0284c7;">$${money(r.gross_total)}</td>
      <td style="color:#dc2626;">$${money(r.cost_total)}</td>
      <td style="font-weight:900;color:#16a34a;background:#f0fdf4;">$${money(net)}</td>
    </tr>`;
  }).join('') : `<tr><td colspan="12" style="text-align:center;padding:10px;color:#64748b;">لا توجد مبيعات مسجلة في هذه الفترة</td></tr>`;

  const deposits_table_body = dRows.length ? dRows.map((d, idx) => {
    const eq = num(d.deposit_usd) + num(d.deposit_eur) + ((num(d.deposit_le_cash) + num(d.deposit_le_visa)) / 50);
    return `<tr>
      <td>${idx + 1}</td>
      <td>${esc((d.deposit_date || '').substring(0, 10))}</td>
      <td style="font-weight:900;color:#1e3a8a;">${esc(d.room_number)}</td>
      <td style="font-weight:bold;">${esc(d.deposit_sales_person || '-')}</td>
      <td>$${money(d.deposit_usd)}</td>
      <td>€${money(d.deposit_eur)}</td>
      <td>${money(d.deposit_le_cash)} LE</td>
      <td>${money(d.deposit_le_visa)} LE</td>
      <td style="font-weight:900;color:#059669;background:#f0fdf4;">$${money(eq)}</td>
    </tr>`;
  }).join('') : `<tr><td colspan="9" style="text-align:center;padding:8px;color:#64748b;">لا توجد عرابين مسجلة لهذا الفندق في هذه الفترة</td></tr>`;

  const coin_table_body = cRowsToday.length ? cRowsToday.map(r => {
    const is_in = String(r.transaction_type || '').toUpperCase() === 'IN';
    const dStr = (r.created_at || '').substring(0, 16);
    return `<tr>
      <td>${r.transaction_id || r.id || '-'}</td>
      <td dir="ltr">${dStr}</td>
      <td style="font-weight:bold;">${esc(r.user_name || '-')}</td>
      <td style="font-weight:bold;color:${is_in ? '#16a34a' : '#dc2626'};">${is_in ? 'إيداع (IN) ➕' : 'سحب (OUT) ➖'}</td>
      <td style="font-weight:900;">€${money(r.amount)}</td>
      <td>${esc(r.notes || '-')}</td>
    </tr>`;
  }).join('') : `<tr><td colspan="6" style="text-align:center;padding:8px;color:#64748b;">لا توجد حركات كوين مسجلة في هذا اليوم (${esc(targetDay)})</td></tr>`;

  const notes_section_html = nRows.length ? `
    <div class="section-title">4. جدول تفاصيل ملاحظات وحركات الدخل اليومي (وارد لينا + / منصرف -)</div>
    <table>
      <thead>
        <tr>
          <th>#</th><th>التاريخ</th><th>نوع الحركة</th><th>الطرف / الجهة</th><th>البيان</th><th>$</th><th>€</th><th>كاش LE</th><th>مكتب LE</th><th>الأثر على الصافي ($)</th>
        </tr>
      </thead>
      <tbody>
        ${nRows.map((n, i) => {
          const isIn = String(n.note_type || '').toUpperCase() === 'IN';
          return `<tr>
            <td>${i + 1}</td>
            <td>${esc(String(n.note_date || '').slice(0, 10))}</td>
            <td style="font-weight:bold;color:${isIn ? '#16a34a' : '#dc2626'};">${isIn ? '➕ وارد (زيادة)' : '➖ منصرف (خصم)'}</td>
            <td style="font-weight:bold;">${esc(n.person_name || '-')}</td>
            <td>${esc(n.note_text || '-')}</td>
            <td>${num(n.amount_usd) ? '$' + money(n.amount_usd) : '-'}</td>
            <td>${num(n.amount_eur) ? '€' + money(n.amount_eur) : '-'}</td>
            <td>${num(n.amount_le_cash) ? money(n.amount_le_cash) : '-'}</td>
            <td>${num(n.amount_le_office) ? money(n.amount_le_office) : '-'}</td>
            <td dir="ltr" style="font-weight:900;color:${isIn ? '#16a34a' : '#dc2626'};">${isIn ? '+' : '-'}$${money(n.equivalent_usd)}</td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>
  ` : '';

  return `
    <div class="header">
      <div class="header-title">
        <h1>PHOTO TEAM STUDIO — ${esc(titleLabel)}</h1>
        <p>${esc(subtitleLabel || 'التقرير المالي اليومي الشامل (الدخل، العرابين، وحركات الكوين لليوم)')}</p>
      </div>
      <div class="header-meta">
        <div>الفترة: <b>من ${esc(start)} إلى ${esc(end)}</b></div>
        <div>تاريخ اليوم المعتمد للكوين: <b>${esc(targetDay)}</b> ${pageBadge ? `• <b>${esc(pageBadge)}</b>` : ''}</div>
      </div>
    </div>

    <div class="grand-box">
      <div class="g-item"><span>إجمالي المبيعات (Gross)</span><strong style="color:#38bdf8;">$${money(t_gross)}</strong></div>
      <div class="g-item"><span>إجمالي العرابين (${dRows.length} عربون)</span><strong style="color:#a7f3d0;">$${money(dep_equiv)}</strong></div>
      <div class="g-item"><span>إجمالي التكاليف (Cost)</span><strong style="color:#f87171;">$${money(t_costs)}</strong></div>
      <div class="g-item"><span>صافي الأرباح (Net Profit)</span><strong style="color:#4ade80;">$${money(t_net)}</strong></div>
      <div class="g-item"><span>الصافي النهائي (بعد الملاحظات)</span><strong style="color:#fde047;">$${money(final_net_after_notes)}</strong></div>
    </div>

    <div class="kpi-container">
      <div class="kpi-card"><span>صافي $ نقداً</span><strong style="color:#0284c7;">$${money(t_usd)}</strong></div>
      <div class="kpi-card"><span>صافي € نقداً</span><strong style="color:#d97706;">€${money(t_eur)}</strong></div>
      <div class="kpi-card"><span>تحصيل كاش L.E</span><strong>${money(t_cash)}</strong></div>
      <div class="kpi-card"><span>تحصيل مكتب L.E</span><strong>${money(t_office)}</strong></div>
      <div class="kpi-card"><span>تكلفة الفساتين</span><strong style="color:#dc2626;">$${money(t_dress)}</strong></div>
      <div class="kpi-card"><span>تكلفة الفلاشات</span><strong style="color:#dc2626;">$${money(t_usb)}</strong></div>
      <div class="kpi-card"><span>تكلفة الألبومات</span><strong style="color:#dc2626;">$${money(t_album)}</strong></div>
    </div>

    <div class="section-title">1. جدول تفاصيل الدخل اليومي وحصص المصورين (${sRows.length} أوردر)</div>
    <table>
      <thead>
        <tr>
          <th style="width:8%;">التاريخ</th>
          <th style="width:6%;">الغرفة</th>
          <th style="width:9%;">السيلز</th>
          <th style="width:21%;">المصورين وحصصهم</th>
          <th style="width:7%;">العربون</th>
          <th style="width:6%;">$</th>
          <th style="width:6%;">€</th>
          <th style="width:7%;">كاش LE</th>
          <th style="width:7%;">مكتب LE</th>
          <th style="width:7%;">الإجمالي</th>
          <th style="width:7%;">التكلفة</th>
          <th style="width:9%;">الصافي</th>
        </tr>
      </thead>
      <tbody>${sales_table_body}</tbody>
    </table>

    <div class="section-title">2. جدول تفاصيل العرابين المسجلة (${dRows.length} عربون)</div>
    <table>
      <thead>
        <tr>
          <th style="width:5%;">#</th>
          <th style="width:12%;">التاريخ</th>
          <th style="width:10%;">الغرفة</th>
          <th style="width:18%;">مسؤول السيلز</th>
          <th style="width:11%;">عربون $</th>
          <th style="width:11%;">عربون €</th>
          <th style="width:11%;">كاش LE</th>
          <th style="width:11%;">فيزا LE</th>
          <th style="width:11%;">المعادل ($)</th>
        </tr>
      </thead>
      <tbody>${deposits_table_body}</tbody>
    </table>

    <div class="section-title" style="display:flex;justify-content:space-between;align-items:center;">
      <span>3. حركات خزنة الكوين لليوم نفسه فقط (${esc(targetDay)})</span>
      <span style="font-size:10.5px;color:#0f172a;">وارد اليوم: <b style="color:#16a34a;">€${money(coin_in)}</b> | منصرف اليوم: <b style="color:#dc2626;">€${money(coin_out)}</b> | صافي حركة اليوم: <b style="color:#d97706;">€${money(coin_today_net)}</b></span>
    </div>
    <table>
      <thead>
        <tr>
          <th style="width:7%;">رقم الحركة</th>
          <th style="width:16%;">التاريخ والوقت</th>
          <th style="width:16%;">المسؤول</th>
          <th style="width:14%;">نوع الحركة</th>
          <th style="width:12%;">المبلغ (€)</th>
          <th style="width:35%;">البيان والملاحظات</th>
        </tr>
      </thead>
      <tbody>${coin_table_body}</tbody>
    </table>

    ${notes_section_html}

    <div class="footer-signatures">
      <div>توقيع مسؤول الخزنة: ....................</div>
      <div>توقيع مراجع الحسابات: ....................</div>
      <div>يعتمد، المدير العام: ....................</div>
    </div>
  `;
}

async function printSalesReport() {
  const hotel_id = $('dsHotel')?.value || '';
  const hotel_name = $('dsHotel')?.options[$('dsHotel')?.selectedIndex]?.text || 'جميع الفنادق';
  const start = $('dsStart')?.value || firstDayMonth();
  const end = $('dsEnd')?.value || todayISO();
  const targetDay = $('dsEnd')?.value || $('dsEntryDate')?.value || todayISO();
  const salesFilter = $('dsSalesFilter')?.value || '';
  const photoFilter = $('dsPhotoFilter')?.value || '';

  const [salesData, depsData, coinData] = await Promise.all([
    apiSafe(`/api/daily-sales?hotel_id=${hotel_id}&start=${start}&end=${end}&sales_person=${encodeURIComponent(salesFilter)}&photographer=${encodeURIComponent(photoFilter)}`, { rows: [], notes: [] }),
    apiSafe(`/api/deposits?hotel_id=${hotel_id}&start=${start}&end=${end}`, []),
    apiSafe(`/api/coin-safe?hotel_id=${hotel_id}`, { rows: [] })
  ]);

  const sRows = salesData.rows || [];
  const rawDeps = Array.isArray(depsData) ? depsData : (depsData.rows || []);
  const dRows = rawDeps.filter(d => {
    if ((num(d.deposit_usd) + num(d.deposit_eur) + num(d.deposit_le_cash) + num(d.deposit_le_visa)) <= 0) return false;
    if (!hotel_id) return true;
    const dh = String(d.hotel_name || d.hotel || '').trim();
    if (dh) return dh === String(hotel_name).trim();
    if (d.hotel_id) return Number(d.hotel_id) === Number(hotel_id);
    return false;
  });
  const nRows = salesData.notes || [];
  const coinRowsAll = coinData.rows || [];
  // تصفية حركات خزنة الكوين لتكون لحركات اليوم نفسه فقط (وليس كل الحركات القديمة)
  const cRowsToday = coinRowsAll.filter(r => String(r.created_at || '').substring(0, 10) === targetDay);

  const pageBody = buildSingleHotelOfficialReportSection({
    titleLabel: `التقرير اليومي الشامل — ${hotel_name}`,
    subtitleLabel: 'قسم الدخل اليومي والعرابين وحركات خزنة الكوين لليوم',
    start,
    end,
    targetDay,
    sRows,
    dRows,
    cRowsToday,
    nRows
  });

  const htmlContent = `<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>التقرير اليومي الشامل - ${esc(hotel_name)}</title><style>${OFFICIAL_DAILY_REPORT_CSS}</style></head><body>${pageBody}</body></html>`;
  openBuiltInReportViewer(htmlContent, `التقرير اليومي الشامل (${hotel_name} • ${start} إلى ${end})`, false);
}
initDaily();'''

assert old_print_sales_pattern.search(ds_js), "printSalesReport not found in daily_sales.js"
ds_js = old_print_sales_pattern.sub(lambda m: new_print_sales_block, ds_js, count=1)

# Now replace printAllHotelsReportPDF in static/js/pages/daily_sales.js so it uses the EXACT same layout and strict deposit matching!
old_all_hotels_pattern = re.compile(
    r"async function printAllHotelsReportPDF\(\) \{.*?\n\}\nwindow\.printAllHotelsReportPDF = printAllHotelsReportPDF;",
    re.DOTALL
)

new_all_hotels_block = '''async function printAllHotelsReportPDF() {
  const start = $('dsStart')?.value || firstDayMonth();
  const end = $('dsEnd')?.value || todayISO();
  const targetDay = $('dsEnd')?.value || $('dsEntryDate')?.value || todayISO();

  const [allSalesResp, allDepsResp, allCoinResp] = await Promise.all([
    apiSafe(`/api/daily-sales?start=${start}&end=${end}`, { rows: [], notes: [] }),
    apiSafe(`/api/deposits?start=${start}&end=${end}`, []),
    apiSafe(`/api/coin-safe`, { rows: [] })
  ]);

  const sRows = allSalesResp.rows || [];
  const rawDeps = Array.isArray(allDepsResp) ? allDepsResp : (allDepsResp.rows || []);
  const dRows = rawDeps.filter(d => (num(d.deposit_usd) + num(d.deposit_eur) + num(d.deposit_le_cash) + num(d.deposit_le_visa)) > 0);
  const nRows = allSalesResp.notes || [];
  const cRowsAll = allCoinResp.rows || [];
  const cRowsTodayAll = cRowsAll.filter(r => String(r.created_at || '').substring(0, 10) === targetDay);

  const hotelsObjs = (dsHotels && dsHotels.length)
    ? dsHotels
    : [...new Set(sRows.map(r => r.hotel_name).filter(Boolean))].map((name, i) => ({ id: i + 1, hotel_name: name }));

  const hStats = hotelsObjs.map(hObj => {
    const hName = String(hObj.hotel_name || '').trim();
    const hId = Number(hObj.id || 0);
    const hs = sRows.filter(r => String(r.hotel_name || '').trim() === hName || (hId && Number(r.hotel_id) === hId));
    // مطابقة صارمة للعرابين الخاصة بهذا الفندق فقط (بدون أي عرابين وهمية للفنادق التي ليس بها عربون)
    const hd = dRows.filter(d => {
      const dh = String(d.hotel_name || d.hotel || '').trim();
      if (dh) return dh === hName;
      if (hId && d.hotel_id) return Number(d.hotel_id) === hId;
      return false;
    });
    const hn = nRows.filter(n => String(n.hotel_name || '').trim() === hName || (hId && Number(n.hotel_id) === hId));
    const hcToday = cRowsTodayAll.filter(c => {
      const ch = String(c.hotel_name || c.hotel_id || '').trim();
      return ch === hName || (hId && Number(c.hotel_id) === hId);
    });

    const gross = hs.reduce((a, r) => a + num(r.gross_total), 0);
    const cost = hs.reduce((a, r) => a + num(r.cost_total), 0);
    const net = hs.reduce((a, r) => a + num(r.daily_total), 0);
    const dep = hd.reduce((a, d) => a + num(d.deposit_usd) + num(d.deposit_eur) + ((num(d.deposit_le_cash) + num(d.deposit_le_visa)) / 50), 0);
    const nIn = hn.filter(n => String(n.note_type || '').toUpperCase() === 'IN').reduce((a, n) => a + num(n.equivalent_usd), 0);
    const nOut = hn.filter(n => String(n.note_type || '').toUpperCase() !== 'IN').reduce((a, n) => a + num(n.equivalent_usd), 0);
    const finalNet = net + nIn - nOut;
    return { hObj, hName, hs, hd, hn, hcToday, gross, cost, net, dep, notesDiff: nIn - nOut, finalNet };
  });

  // الصفحة الأولى: إجمالي كل الفنادق بنفس شكل التقرير اليومي + جدول مقارنة الفنادق
  const summaryRowsHtml = hStats.map((st, idx) => `
    <tr>
      <td>${idx + 1}</td>
      <td style="font-weight:900;color:#1e3a8a;text-align:right;padding-right:10px;">🏨 ${esc(st.hName)}</td>
      <td><b>${st.hs.length}</b></td>
      <td><b>${st.hd.length}</b></td>
      <td>$${money(st.dep)}</td>
      <td style="font-weight:bold;color:#0284c7;">$${money(st.gross)}</td>
      <td style="color:#dc2626;">$${money(st.cost)}</td>
      <td style="font-weight:bold;color:#16a34a;">$${money(st.net)}</td>
      <td dir="ltr">${st.notesDiff >= 0 ? '+' : ''}$${money(st.notesDiff)}</td>
      <td style="font-weight:900;color:#16a34a;background:#f0fdf4;">$${money(st.finalNet)}</td>
    </tr>
  `).join('');

  const page1OverviewHtml = buildSingleHotelOfficialReportSection({
    titleLabel: 'التقرير المالي المجمع لجميع الفنادق (الإجمالي العام)',
    subtitleLabel: `الصفحة الأولى: ملخص وإجمالي جميع الفنادق (${hStats.length} فنادق) — يليه صفحة مستقلة لكل فندق بنفس تصميم التقرير اليومي`,
    start,
    end,
    targetDay,
    sRows,
    dRows,
    cRowsToday: cRowsTodayAll,
    nRows,
    pageBadge: `صفحة 1 من ${hStats.length + 1}`
  });

  const page1ComparisonTable = `
    <div class="section-title">📊 جدول مقارنة إجماليات الفنادق (${hStats.length} فنادق)</div>
    <table>
      <thead>
        <tr>
          <th style="width:5%;">#</th>
          <th style="width:22%;">اسم الفندق</th>
          <th style="width:9%;">عدد الأوردرات</th>
          <th style="width:9%;">عدد العرابين</th>
          <th style="width:10%;">إجمالي العرابين ($)</th>
          <th style="width:11%;">إجمالي المبيعات ($)</th>
          <th style="width:10%;">إجمالي التكاليف ($)</th>
          <th style="width:11%;">صافي الأوردرات ($)</th>
          <th style="width:6%;">الملاحظات</th>
          <th style="width:11%;">الصافي النهائي ($)</th>
        </tr>
      </thead>
      <tbody>${summaryRowsHtml}</tbody>
    </table>
  `;

  const perHotelPagesHtml = hStats.map((st, idx) => `
    <div class="report-page-break">
      ${buildSingleHotelOfficialReportSection({
        titleLabel: `التقرير اليومي الفردي — فندق ${st.hName}`,
        subtitleLabel: `كشف تفصيلي مستقل لفندق (${st.hName}) بنفس تصميم التقرير اليومي المعتمد`,
        start,
        end,
        targetDay,
        sRows: st.hs,
        dRows: st.hd,
        cRowsToday: st.hcToday,
        nRows: st.hn,
        pageBadge: `صفحة ${idx + 2} من ${hStats.length + 1}`
      })}
    </div>
  `).join('');

  const htmlDoc = `<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>تقرير كل الفنادق الشامل (${esc(start)} إلى ${esc(end)})</title><style>${OFFICIAL_DAILY_REPORT_CSS}</style></head><body>
    ${page1ComparisonTable}
    ${page1OverviewHtml}
    ${perHotelPagesHtml}
  </body></html>`;

  openBuiltInReportViewer(htmlDoc, `تقرير كل الفنادق الشامل (${start} إلى ${end})`, false);
}
window.printAllHotelsReportPDF = printAllHotelsReportPDF;'''

assert old_all_hotels_pattern.search(ds_js), "printAllHotelsReportPDF not found in daily_sales.js"
ds_js = old_all_hotels_pattern.sub(lambda m: new_all_hotels_block, ds_js, count=1)
ds_js_path.write_text(ds_js, encoding="utf-8")
print("✅ Patched static/js/pages/daily_sales.js")

# ============================================================================
# 2. PATCH templates/daily_sales.html:
#    Make #dailyIncomeNotesPanel a compact, slim collapsible bar (~38px tall)
# ============================================================================
ds_html_path = ROOT / "templates/daily_sales.html"
ds_html = ds_html_path.read_text(encoding="utf-8")

old_notes_panel_pattern = re.compile(
    r'<section class="panel" id="dailyIncomeNotesPanel".*?</section>',
    re.DOTALL
)

new_notes_panel = '''<section class="panel compact-notes-bar" id="dailyIncomeNotesPanel" style="margin-bottom:10px;padding:7px 14px !important;border:1px solid var(--border-strong);border-radius:10px;">
        <div class="panel-head" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:0;">
            <div style="display:flex;align-items:center;gap:8px;">
                <h2 style="margin:0;font-size:13px;font-weight:800;">📝 ملاحظات الصادر والوارد (اختياري)</h2>
                <button type="button" class="mini-btn blue" style="padding:2px 8px;font-size:11px;" onclick="const w=this.closest('#dailyIncomeNotesPanel').querySelector('.table-wrap');w.hidden=!w.hidden;this.textContent=w.hidden?'📂 عرض السجل':'🔼 إخفاء السجل';">📂 عرض السجل</button>
            </div>
            <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                <span class="badge blue" style="font-size:11px;padding:2px 7px;">صافي الأوردرات: <b id="dinOrdersNet">$0.00</b></span>
                <span class="badge green" style="font-size:11px;padding:2px 7px;">➕ وارد: <b id="dinTotalIn">+$0.00</b></span>
                <span class="badge red" style="font-size:11px;padding:2px 7px;">➖ منصرف: <b id="dinTotalOut">-$0.00</b></span>
                <span class="badge amber" style="font-size:11.5px;padding:2px 8px;">💰 الصافي النهائي: <b id="dinFinalNet">$0.00</b></span>
                <button type="button" class="btn green" style="min-height:26px !important;height:26px !important;padding:2px 10px !important;font-size:11.5px !important;" onclick="openDailyIncomeNoteModal()">➕ حركة</button>
            </div>
        </div>
        <div class="table-wrap" hidden style="max-height:170px;overflow-y:auto;margin-top:8px;">
            <table class="modern-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>التاريخ</th>
                        <th>الفندق</th>
                        <th>النوع</th>
                        <th>الشخص / الجهة</th>
                        <th>البيان</th>
                        <th>$</th>
                        <th>€</th>
                        <th>كاش LE</th>
                        <th>مكتب LE</th>
                        <th>الصافي المعادل ($)</th>
                        <th>بواسطة</th>
                        <th>إجراءات</th>
                    </tr>
                </thead>
                <tbody id="dailyIncomeNotesBody">
                    <tr><td colspan="13" class="empty-state">لا توجد ملاحظات مسجلة في هذه الفترة</td></tr>
                </tbody>
            </table>
        </div>
    </section>'''

assert old_notes_panel_pattern.search(ds_html), "dailyIncomeNotesPanel not found in templates/daily_sales.html"
ds_html = old_notes_panel_pattern.sub(lambda m: new_notes_panel, ds_html, count=1)
ds_html_path.write_text(ds_html, encoding="utf-8")
print("✅ Patched templates/daily_sales.html")
