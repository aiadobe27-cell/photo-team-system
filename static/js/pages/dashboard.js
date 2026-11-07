// ============================================================================
// 📌 ملف الكود البرمجي (dashboard.js): كود تشغيل الشاشة الرئيسية وتحديث كروت الإحصائيات وحالة الفريق
// ============================================================================

let dashboardData={};

function timeLabel(t){
  if(!t)return '--';
  const [hh,mm]=String(t).slice(0,5).split(':').map(Number);
  const h12=((hh+11)%12)+1;
  return `${h12}:${String(mm||0).padStart(2,'0')} ${hh>=12?'م':'ص'}`;
}
function capacityClass(x){return num(x.available)<=0?'full':num(x.available)===1?'tight':'open'}
function availabilityChip(x){return `<span class="availability-chip ${capacityClass(x)}"><b>${timeLabel(x.time)}</b><small>${x.available} متاح</small></span>`}

function previewAvailability(rows){
  rows=rows||[];if(!rows.length)return [];
  const firstBusy=rows.findIndex(x=>num(x.busy)>0);
  if(firstBusy>=0){const start=Math.max(0,firstBusy-1);return rows.slice(start,start+6)}
  const now=new Date(),mins=now.getHours()*60+now.getMinutes();let idx=rows.findIndex(x=>{const [h,m]=String(x.time).split(':').map(Number);return h*60+m>=mins});if(idx<0)idx=0;return rows.slice(Math.max(0,idx-1),Math.max(0,idx-1)+6);
}

async function loadDashboard(){
 try{
  const d=$('dashDate').value||todayISO();
  const x=await api('/api/dashboard?date='+encodeURIComponent(d));dashboardData=x||{};
  $('kTotal').textContent=num(x.bookings?.total);$('kDresses').textContent=num(x.dresses_required_count);$('kLaundry').textContent=num(x.laundry?.dresses);$('kTeam').textContent=num(x.total_team);$('kPhotographers').textContent=num(x.total_photographers);$('kSalesBookings').textContent=(x.sales_bookings_today||[]).length;
  const avail=x.team_availability||[];
  $('availabilityPreview').innerHTML=previewAvailability(avail).map(availabilityChip).join('')||'<span class="muted">لا يوجد مصورون مسجلون</span>';
  $('availabilityBoard').innerHTML=previewAvailability(avail).map(x=>`<div class="availability-row ${capacityClass(x)}"><span>${timeLabel(x.time)}</span><div class="capacity-bar"><i style="width:${x.total?Math.min(100,(x.busy/x.total)*100):0}%"></i></div><b>${x.available} من ${x.total} متاح</b></div>`).join('')||'<div class="empty-state">لا توجد بيانات توافر</div>';
  $('dressTodayBody').innerHTML=(x.dresses_required||[]).slice(0,14).map((r,i)=>`<tr class="select-row" onclick="openDressGroupDetails(${i})"><td><b>${esc(r.type)}</b></td><td><span class="dress-color-chip">${esc(r.color)}</span></td><td><span class="size-chip">${esc(r.size)}</span></td><td><strong class="dress-total-qty">${num(r.qty)}</strong></td><td>${num(r.booking_count)}</td><td>${esc(r.rooms_text||'-')}</td></tr>`).join('')||'<tr><td colspan="6" class="empty-state">لا توجد ملابس مطلوبة من حجوزات انتظار في هذا اليوم</td></tr>';
  $('upcomingBody').innerHTML=(x.timeline||[]).slice(0,10).map(r=>`<tr class="select-row" onclick="openBookingFromDashboard(${r.id})"><td><b>${timeLabel(r.booking_time)}</b></td><td>${esc(r.room_number)}</td><td>${esc(r.hotel)}</td><td>${esc(r.sales_person||'-')}</td><td>${esc(r.photographer||'غير معين')}</td><td>${statusBadge(r.status)}</td></tr>`).join('')||'<tr><td colspan="6" class="empty-state">لا توجد حجوزات لهذا اليوم</td></tr>';
  $('salesSummary').innerHTML=(x.sales_summary||[]).map(r=>`<button class="sales-person-card" onclick="openSalesBookingsDetails('${String(r.sales_person).replaceAll("'","\\'")}')"><span>👤</span><div><b>${esc(r.sales_person)}</b><small>حجوزات اليوم</small></div><strong>${r.count}</strong></button>`).join('')||'<div class="empty-state">لا توجد حجوزات أضافها السيلز اليوم</div>';
 }catch(e){toast(e.message,'bad')}
}

function openBookingFromDashboard(id){if(id)location.href=`/reservations?open=${id}&source=dashboard`}

function openDressGroupDetails(index){
 const r=(dashboardData.dresses_required||[])[index];if(!r)return;
 const bookings=r.bookings||[];
 showModal(`<div class="modal-title"><h2>👗 ${esc(r.type)} • ${esc(r.color)} • ${esc(r.size)}</h2><p>إجمالي المطلوب: <b>${num(r.qty)} قطعة</b> من ${num(r.booking_count)} حجز انتظار في ${esc(dashboardData.date||'')}</p></div><div class="table-wrap maxh"><table><thead><tr><th>#</th><th>الغرفة</th><th>الفندق</th><th>الوقت</th><th>السيلز</th><th>العدد</th><th>الحالة</th><th></th></tr></thead><tbody>${bookings.map((b,i)=>`<tr><td>${i+1}</td><td><b>${esc(b.room_number)}</b></td><td>${esc(b.hotel||'-')}</td><td>${timeLabel(b.booking_time)}</td><td>${esc(b.sales_person||'-')}</td><td><b>${num(b.qty)}</b></td><td>${statusBadge(b.status)}</td><td><button class="mini-btn blue" onclick="location.href='/reservations?open=${b.id}&source=dress-summary'">فتح</button></td></tr>`).join('')||'<tr><td colspan="8" class="empty-state">لا توجد تفاصيل</td></tr>'}</tbody></table></div>`,'modal-xl');
}

function openTeamAvailability(){
 const rows=dashboardData.team_availability||[];
 showModal(`<div class="modal-title"><h2>👥 التيم المتاح حسب الوقت</h2><p>${esc(dashboardData.date||'')} • إجمالي المصورين: ${num(dashboardData.total_photographers)} • مدة السيشن: ${num(dashboardData.session_duration_minutes||60)} دقيقة</p></div><div class="availability-modal-grid">${rows.map(x=>`<div class="availability-slot ${capacityClass(x)}"><b>${timeLabel(x.time)}</b><strong>${x.available}</strong><small>متاح من ${x.total} • مشغول ${x.busy} • السيشن ساعة</small></div>`).join('')||'<div class="empty-state">لا توجد بيانات</div>'}</div>`,'modal-xl');
}

function pendingDepositLabel(r){
 const vals=[];if(num(r.deposit_usd))vals.push(`<span class="currency-usd">$${money(r.deposit_usd)}</span>`);if(num(r.deposit_eur))vals.push(`<span class="currency-eur">€${money(r.deposit_eur)}</span>`);if(num(r.deposit_le_cash)+num(r.deposit_le_visa))vals.push(`<span class="currency-egp">${money(num(r.deposit_le_cash)+num(r.deposit_le_visa))} EGP</span>`);return vals.join(' + ')||'-';
}
function openSalesBookingsDetails(filterSales=''){
 const rows=(dashboardData.sales_bookings_today||[]).filter(r=>!filterSales||r.sales_person===filterSales);
 const title=filterSales?`حجوزات ${esc(filterSales)} اليوم`:'تفاصيل حجوزات السيلز اليوم';
 showModal(`<div class="modal-title"><h2>🧾 ${title}</h2><p>الحجوزات التي تم إنشاؤها اليوم، بغض النظر عن تاريخ السيشن.</p></div><div class="table-wrap maxh"><table><thead><tr><th>#</th><th>السيلز</th><th>الغرفة</th><th>الفندق</th><th>تاريخ السيشن</th><th>الوقت</th><th>العربون</th><th>الحالة</th><th></th></tr></thead><tbody>${rows.map((r,i)=>`<tr><td>${i+1}</td><td><b>${esc(r.sales_person||'-')}</b></td><td>${esc(r.room_number)}</td><td>${esc(r.hotel)}</td><td>${esc(r.booking_date)}</td><td>${timeLabel(r.booking_time)}</td><td>${pendingDepositLabel(r)}</td><td>${statusBadge(r.status)}</td><td><button class="mini-btn blue" onclick="location.href='/reservations?open=${r.id}&source=sales-details'">فتح</button></td></tr>`).join('')||'<tr><td colspan="9" class="empty-state">لا توجد حجوزات</td></tr>'}</tbody></table></div>`,'modal-xxl');
}

$('dashDate').value = todayISO();
$('dashDate').addEventListener('change', loadDashboard);
loadDashboard();