// ============================================================================
// 📌 ملف الكود البرمجي (reports.js): كود شاشة التقارير الشاملة والرسوم البيانية وتصدير PDF/Excel
// ============================================================================

let lastReportData = null;

async function loadReport(){
    try{
        const h = $('reportHotel')?.value || ''; 
        const e = $('reportEmployee')?.value || ''; 
        const t = $('reportType')?.value || '';
        
        const x = await api(`/api/reports?start=${$('reportStart').value}&end=${$('reportEnd').value}&hotel_id=${encodeURIComponent(h)}&employee=${encodeURIComponent(e)}&type=${encodeURIComponent(t)}`);
        lastReportData = x;
        
        // مؤشرات الأداء (KPIs)
        $('rpBookings').textContent = x.bookings || 0;
        $('rpAgreed').textContent = money(x.agreed) + '$';
        $('rpRemaining').textContent = money(x.remaining) + '$';
        $('rpIncome').textContent = money(x.income) + '$';
        $('rpCosts').textContent = money(x.costs) + '$';
        $('rpNetProfit').textContent = money(x.net_profit) + '$';
        
        // رسم بياني لاتجاه الدخل
        const rows = x.trend || [];
        const max = Math.max(1, ...rows.map(r => Number(r.total || 0)));
        $('trendChart').innerHTML = rows.map(r => `<div class="bar-item"><b>${money(r.total,0)}</b><div class="bar" style="height:${Math.max(4, Number(r.total||0)/max*165)}px" title="${r.day}: $${money(r.total)}"></div><small>${String(r.day).slice(5)}</small></div>`).join('') || '<div class="empty-state">لا توجد بيانات إيرادات للفترة المحددة</div>';
        
        // مصادر الإيرادات
        $('revenueSourcesList').innerHTML = (x.sources || []).map(s => `<li><span class="name">${esc(s.name)}</span><span class="value green">${s.pct}% ($${money(s.val||0)})</span></li>`).join('') || '<li><span class="name text-muted">لا توجد إيرادات مسجلة</span></li>';
        
        // أفضل الموظفين والمبيعات
        $('topTeamList').innerHTML = (x.top_team || []).map((t, i) => `<li><span class="name">${i+1}. ${esc(t.name)}</span><span class="value">${money(t.value)} $</span></li>`).join('') || '<li><span class="name text-muted">لا توجد مبيعات للموظفين</span></li>';
        
        // إحصائيات الفنادق
        $('topHotelsList').innerHTML = (x.top_hotels || []).map(h => `<li><span class="name">${esc(h.name)}</span><span class="value">${money(h.value)} $</span></li>`).join('') || '<li><span class="name text-muted">لا توجد مبيعات للفنادق</span></li>';
        
        // ملخص التكاليف والمصروفات
        $('expensesSummaryList').innerHTML = (x.expenses || []).map(e => `<li><span class="name">${esc(e.name)}</span><span class="value red">- ${money(e.value)} ${esc(e.currency)}</span></li>`).join('') || '<li><span class="name text-muted">لا توجد مصروفات</span></li>';

    } catch(err) {
        toast(err.message, 'bad');
    }
}

function exportReportCSV(){
    if(!lastReportData){
        return toast('يرجى عرض التقرير أولاً','bad');
    }
    const x = lastReportData;
    const rows = [
        ['ملخص المؤشرات المالية','الفترة من ' + $('reportStart').value + ' إلى ' + $('reportEnd').value,''],
        ['إجمالي الحجوزات', x.bookings || 0, 'حجز'],
        ['قيمة الاتفاقات الكلية', money(x.agreed), 'USD'],
        ['المتبقي للتحصيل', money(x.remaining), 'USD'],
        ['الدخل المحصل الإجمالي', money(x.income), 'USD'],
        ['إجمالي تكاليف التشغيل', money(x.costs), 'USD'],
        ['صافي الربح التقديري', money(x.net_profit), 'USD'],
        ['','',''],
        ['أعلى أداء فريق العمل','القيمة','العملة'],
        ...(x.top_team||[]).map((t,i)=>[`${i+1}. ${t.name}`, money(t.value), 'USD']),
        ['','',''],
        ['إيرادات الفنادق','القيمة','العملة'],
        ...(x.top_hotels||[]).map(h=>[h.name, money(h.value), 'USD']),
        ['','',''],
        ['تفاصيل المصروفات والتكاليف','القيمة','العملة'],
        ...(x.expenses||[]).map(e=>[e.name, money(e.value), e.currency])
    ];
    downloadCSV(`Comprehensive_Report_${$('reportStart').value}_${$('reportEnd').value}.csv`, ['البند / القسم', 'القيمة', 'العملة / الوحدة'], rows);
    toast('تم تصدير التقرير الشامل إلى Excel (CSV) بنجاح');
}

async function initFilters(){
    try {
        const [hotels, team] = await Promise.all([api('/api/hotels'), api('/api/team/options')]);
        if($('reportHotel')){
            $('reportHotel').innerHTML = '<option value="">🏨 جميع الفنادق</option>' + hotels.map(h => `<option value="${h.id}">${esc(h.hotel_name)}</option>`).join('');
        }
        if($('reportEmployee')){
            $('reportEmployee').innerHTML = '<option value="">📸 جميع الموظفين</option>' + (team.all || []).map(e => `<option value="${esc(e.nickname)}">${esc(e.nickname)}</option>`).join('');
        }
    } catch(e) {
        console.error("فشل في تحميل الفلاتر", e);
    }
}

$('reportStart').value = firstDayMonth();
$('reportEnd').value = todayISO();
initFilters().then(loadReport);


function printComprehensiveReportPDF() {
    if (!lastReportData) {
        return toast('يرجى عرض التقرير أولاً', 'bad');
    }
    const x = lastReportData;
    const s = $('reportStart')?.value || '';
    const e = $('reportEnd')?.value || '';
    const htmlBody = `
      <p>الفترة من: <b>${esc(s)}</b> إلى: <b>${esc(e)}</b></p>
      <table>
        <thead><tr><th>إجمالي الحجوزات</th><th>قيمة الاتفاقات</th><th>المتبقي للتحصيل</th><th>إجمالي الدخل المحصل</th><th>إجمالي التكاليف</th><th>صافي الربح</th></tr></thead>
        <tbody><tr>
          <td><b>${x.bookings || 0}</b></td>
          <td>$${money(x.agreed)}</td>
          <td>$${money(x.remaining)}</td>
          <td>$${money(x.income)}</td>
          <td>$${money(x.costs)}</td>
          <td><b>$${money(x.net_profit)}</b></td>
        </tr></tbody>
      </table>
      <h3>🏆 أداء فريق العمل</h3>
      <table>
        <thead><tr><th>#</th><th>الموظف</th><th>إجمالي المبيعات ($)</th></tr></thead>
        <tbody>${(x.top_team||[]).map((t,i)=>`<tr><td>${i+1}</td><td>${esc(t.name)}</td><td>$${money(t.value)}</td></tr>`).join('') || '<tr><td colspan="3">لا توجد بيانات</td></tr>'}</tbody>
      </table>
      <h3>🏨 إيرادات الفنادق</h3>
      <table>
        <thead><tr><th>الفندق</th><th>إجمالي المبيعات ($)</th></tr></thead>
        <tbody>${(x.top_hotels||[]).map(h=>`<tr><td>${esc(h.name)}</td><td>$${money(h.value)}</td></tr>`).join('') || '<tr><td colspan="2">لا توجد بيانات</td></tr>'}</tbody>
      </table>
      <div class="sign"><span>توقيع المحاسب</span><span>اعتماد المدير العام (CEO)</span></div>
    `;
    printHTML(`التقرير التحليلي الشامل (${s} إلى ${e})`, htmlBody);
}
