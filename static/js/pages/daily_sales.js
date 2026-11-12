// ============================================================================
// 📌 ملف الكود البرمجي (daily_sales.js): كود شاشة الدخل اليومي، تسجيل مبيعات الأوردرات، وملاحظات الدخل اليومي (وارد + / منصرف -)
// ============================================================================

let dsHotels=[],dsTeam={},eligible=[],salesRows=[],depositRows=[],coinRows=[],selectedEligible=null;
async function initDaily(){dsHotels=await apiSafe('/api/hotels',[],'تحميل الفنادق');dsTeam=await apiSafe('/api/team/options',{sales:[],photographers:[],all:[]},'تحميل الفريق');const hs='<option value="">الكل</option>'+dsHotels.map(h=>`<option value="${h.id}">${esc(h.hotel_name)}</option>`).join('');$('dsHotel').innerHTML=hs;$('coinHotel').innerHTML=dsHotels.map(h=>`<option value="${h.id}">${esc(h.hotel_name)}</option>`).join('');$('saleSales').innerHTML='<option value="">-- اختر اسم السيلز --</option>'+(dsTeam.sales||[]).map(x=>`<option value="${esc(x.nickname)}">${esc(x.nickname)}</option>`).join('');if($('salePhotogSelect'))$('salePhotogSelect').innerHTML='<option value="">-- اختر اسم المصور --</option>'+(dsTeam.photographers||[]).map(x=>`<option value="${esc(x.nickname)}">${esc(x.nickname)}</option>`).join('');$('photoNamesList').innerHTML=(dsTeam.photographers||[]).map(x=>`<option value="${esc(x.nickname)}"></option>`).join('');$('dsSalesFilter').innerHTML='<option value="">الكل</option>'+(dsTeam.sales||[]).map(x=>`<option>${esc(x.nickname)}</option>`).join('');$('dsPhotoFilter').innerHTML='<option value="">الكل</option>'+(dsTeam.photographers||[]).map(x=>`<option>${esc(x.nickname)}</option>`).join('');$('dsEntryDate').value=todayISO();$('dsStart').value=firstDayMonth();$('dsEnd').value=todayISO();$('anMonth').value=monthISO();$('dsHotel').addEventListener('change',()=>{loadEligible();loadSalesSearch();loadAnalytics();loadCoin()});$('dsDataType').addEventListener('change',loadSalesSearch);['dsStart','dsEnd','dsSalesFilter','dsPhotoFilter','dsHotel'].forEach(x=>$(x).addEventListener('change',loadSalesSearch));$$('.sale-calc').forEach(x=>x.addEventListener('input',calcSale));$('salePhotog').addEventListener('input',calcSale);$('saleForm').addEventListener('submit',saveSale);$('coinForm').addEventListener('submit',saveCoin);document.addEventListener('keydown',e=>{if(e.key==='Enter'&&document.activeElement?.closest('#saleForm')){e.preventDefault();$('saleForm').requestSubmit()}});await Promise.all([loadEligible(),loadSalesSearch(),loadAnalytics(),loadCoin()])}
async function refreshDailyAll(){await Promise.all([loadEligible(),loadSalesSearch(),loadAnalytics(),loadCoin()]);toast('تم تحديث بيانات الفندق')}
function setSaleFormMode(isEdit, saleRecord=null, bookingRecord=null){
  const banner=$('saleEditBanner'),badge=$('saleModeBadge'),btn=$('saleSubmitBtn'),title=$('saleFormTitle');
  if(isEdit && saleRecord){
    if(banner)banner.hidden=false;
    if(badge){badge.hidden=false;badge.textContent=`✏️ تعديل سجل #${saleRecord.id}`}
    if(title)title.textContent=`✏️ تعديل الدخل المسجل للأوردر (غرفة ${saleRecord.room_number||bookingRecord?.room_number||'-'})`;
    if($('saleEditBannerTitle'))$('saleEditBannerTitle').textContent=`✏️ وضع تعديل الدخل المسجل — سجل #${saleRecord.id} (بتاريخ ${saleRecord.income_date||todayISO()})`;
    if(btn){btn.textContent='✏️ حفظ تعديلات الدخل (Enter)';btn.className='btn edit-mode'}
  }else{
    if(banner)banner.hidden=true;
    if(badge)badge.hidden=true;
    if(title)title.textContent='📝 تفاصيل الأوردر وتسجيل الدخل';
    if(btn){btn.textContent='💾 حفظ سجل الدخل (Enter)';btn.className='btn green'}
  }
}

function populateSaleFormFromRecord(inc, b=null){
  $('saleId').value=inc.id||'';
  $('saleBookingId').value=b?.id||inc.booking_id||'';
  $('saleRoomNumber').value=b?.room_number||inc.room_number||'';
  $('saleHotelId').value=inc.hotel_id||'';
  $('saleIncomeDate').value=String(inc.income_date||'').slice(0,10)||$('dsEntryDate')?.value||todayISO();
  if(inc.sales_person && !Array.from($('saleSales').options).some(o=>o.value===inc.sales_person)){
    $('saleSales').insertAdjacentHTML('beforeend',`<option value="${esc(inc.sales_person)}">${esc(inc.sales_person)}</option>`);
  }
  $('saleSales').value=inc.sales_person||b?.sales_person||'';
  $('salePhotog').value=String(inc.photographer||b?.photographer||'').trim();
  if($('salePhotogSelect'))$('salePhotogSelect').value=splitPhotographerNames($('salePhotog').value)[0]||'';
  if($('saleQuickRoomInput'))$('saleQuickRoomInput').value=b?.room_number||inc.room_number||'';
  $('saleDeposit').value=num(inc.deposit_applied).toFixed(2);
  $('saleUsd').value=num(inc.income_usd);
  $('saleEur').value=num(inc.income_eur);
  $('saleCash').value=num(inc.income_le_k);
  $('saleOffice').value=num(inc.income_le_m);
  $('saleRate').value=num(inc.le_to_usd||inc.order_exchange_rate)||50;
  $('costDress').value=num(inc.cost_dress);
  $('costUsb').value=num(inc.cost_usb);
  $('costAlbum').value=num(inc.cost_album);
  if($('saleAdjustReason'))$('saleAdjustReason').value='';
  setSaleFormMode(true, inc, b);
  calcSale();
}

async function loadEligible(){
  const d=$('dsEntryDate').value;
  try{
    eligible=await api('/api/daily-sales/eligible-bookings?date='+d+($('dsHotel').value?'&hotel_id='+$('dsHotel').value:''));
  }catch(e){
    eligible=[];
    toast('تعذر تحميل أوردرات الدخل: '+e.message,'bad');
  }
  $('eligibleBody').innerHTML=eligible.map(b=>{
    const inc=b.saved_income;
    const savedBadge=b.income_saved
      ? `<span class="badge green">✓ مسجل (${inc?money(inc.daily_total)+'$':''}) • اضغط للتعديل ✏️</span>`
      : `<span class="badge amber">⏳ لم يسجل بعد</span>`;
    return `<tr class="select-row ${b.income_saved?'has-saved-income':''} ${selectedEligible===b.id?'selected':''}" onclick="selectEligible(${b.id},this)">
      <td><b>غرفة ${esc(b.room_number)}</b> • <small>${esc(b.hotel||'')}</small></td>
      <td>${esc(b.sales_person||'')}</td>
      <td>${esc(b.photographer||'بدون مصور')}</td>
      <td>${savedBadge}</td>
      <td>${statusBadge(b.status)}</td>
    </tr>`;
  }).join('')||'<tr><td colspan="5" class="empty-state">لا توجد أوردرات لهذا اليوم</td></tr>';
}

function selectEligible(id,row){
  selectedEligible=id;
  $$('#eligibleBody tr').forEach(x=>x.classList.remove('selected'));
  row?.classList.add('selected');
  const b=eligible.find(x=>x.id===id);
  if(!b)return;
  if(b.saved_income){
    populateSaleFormFromRecord(b.saved_income, b);
    $('selectedOrderInfo').textContent=`غرفة ${b.room_number} • ${b.hotel} • دخل مسجل مسبقاً بصافي ${money(b.saved_income.daily_total)}$ (جاهز للتعديل ✏️)`;
  }else{
    $('saleId').value='';
    $('saleBookingId').value=id;
    $('saleRoomNumber').value=b.room_number||'';
    $('saleHotelId').value='';
    $('saleIncomeDate').value=$('dsEntryDate')?.value||todayISO();
    $('saleSales').value=b.sales_person||'';
    $('salePhotog').value=String(b.photographer||'').trim();
    if($('salePhotogSelect'))$('salePhotogSelect').value=splitPhotographerNames($('salePhotog').value)[0]||'';
    if($('saleQuickRoomInput'))$('saleQuickRoomInput').value=b.room_number||'';
    const dep=b.deposit_history||{};
    const rate=50;
    const depEq=num(dep.usd)+num(dep.eur)+(num(dep.cash)+num(dep.visa))/rate;
    $('saleDeposit').value=depEq.toFixed(2);
    ['saleUsd','saleEur','saleCash','saleOffice','costDress','costUsb','costAlbum'].forEach(k=>{if($(k))$(k).value=0});
    $('saleRate').value=50;
    setSaleFormMode(false, null, b);
    $('selectedOrderInfo').textContent=`غرفة ${b.room_number} • ${b.hotel} • الاتفاق ${money(b.total_agreement)}$ • المتبقي ${money(b.remaining)}$`;
    calcSale();
  }
}

function splitPhotographerNames(value){const out=[];String(value||'').replaceAll('،',',').split(',').forEach(part=>part.split('&').forEach(x=>{const n=x.trim();if(n&&!out.some(v=>v.toLowerCase()===n.toLowerCase()))out.push(n)}));return out.slice(0,3)}
function photographerRate(name){const row=(dsTeam.photographers||[]).find(x=>String(x.nickname||'').trim().toLowerCase()===String(name||'').trim().toLowerCase());const r=num(row?.commission_rate);return r>0?r:10}
function renderPhotoSplit(net){const names=splitPhotographerNames($('salePhotog').value);const rows=$('photoSplitRows'),count=$('photoSplitCount');if(!rows||!count)return;if(!names.length){count.textContent='لا يوجد مصور محدد';rows.innerHTML='<div class="empty-state compact">اختر أوردر لعرض تقسيم صافي الدخل والعمولة على المصورين.</div>';return}const share=net/names.length;count.textContent=`${names.length} مصور • حصة الصافي لكل مصور ${money(share)} $`;rows.innerHTML=names.map((name,i)=>{const rate=photographerRate(name),commission=share*rate/100;return `<div class="photo-split-row"><span class="photo-split-index">${i+1}</span><b>${esc(name)}</b><span>حصة الصافي <strong>${money(share)} $</strong></span><span>النسبة <strong>${money(rate)}%</strong></span><span>العمولة <strong>${money(commission)} $</strong></span></div>`}).join('')}
function calcSale(){const rate=num($('saleRate').value)||50,le=(num($('saleCash').value)+num($('saleOffice').value))/rate,gross=num($('saleDeposit').value)+num($('saleUsd').value)+num($('saleEur').value)+le,cost=num($('costDress').value)+num($('costUsb').value)+num($('costAlbum').value),net=gross-cost;$('saleConverted').textContent=money(le)+' $';$('saleGross').textContent=money(gross)+' $';$('saleCosts').textContent=money(cost)+' $';$('saleNet').textContent=money(net)+' $';renderPhotoSplit(net)}

function clearSaleForm(){
  ['saleId','saleBookingId','saleRoomNumber','saleHotelId','saleIncomeDate','saleUsd','saleEur','saleCash','saleOffice','costDress','costUsb','costAlbum'].forEach(id=>{
    if($(id))$(id).value=['saleId','saleBookingId','saleRoomNumber','saleHotelId','saleIncomeDate'].includes(id)?'':'0';
  });
  $('saleDeposit').value=0;
  $('saleRate').value=50;
  if($('saleSales'))$('saleSales').value='';
  $('salePhotog').value='';
  if($('salePhotogSelect'))$('salePhotogSelect').value='';
  if($('saleQuickRoomInput'))$('saleQuickRoomInput').value='';
  if($('saleAdjustReason'))$('saleAdjustReason').value='';
  selectedEligible=null;
  setSaleFormMode(false);
  $('selectedOrderInfo').textContent='اختر أوردر من القائمة الجانبية للبدء أو لتعديل دخل مسجل';
  calcSale();
  loadEligible();
}

function onSalePhotogSelectChange(val){
  if(!val)return;
  const cur=splitPhotographerNames($('salePhotog')?.value||'');
  if(!cur.length){
    $('salePhotog').value=val;
  }else if(!cur.some(x=>x.toLowerCase()===val.toLowerCase())){
    if(cur.length===1) $('salePhotog').value=val;
    else $('salePhotog').value=[...cur,val].slice(0,3).join(', ');
  }
  calcSale();
}
window.onSalePhotogSelectChange = onSalePhotogSelectChange;

async function saveSale(e){
  e.preventDefault();
  const saleId=num($('saleId')?.value);
  const bookingId=num($('saleBookingId')?.value);
  const salesVal=($('saleSales')?.value||'').trim();
  if(!salesVal)return toast('يرجى اختيار اسم السيلز أولاً','bad');
  const rawPhotog=($('salePhotog')?.value||$('salePhotogSelect')?.value||'').trim();
  const photoNames=splitPhotographerNames(rawPhotog);
  if(!photoNames.length)return toast('يرجى اختيار اسم المصور أولاً','bad');
  $('salePhotog').value=photoNames.join(', ');
  const entryDate=$('saleIncomeDate')?.value||$('dsEntryDate')?.value||todayISO();
  const roomStr=($('saleQuickRoomInput')?.value||$('saleRoomNumber')?.value||'').trim()||'دخل سريع';
  const hotelVal=$('saleHotelId')?.value||$('dsHotel')?.value||(dsHotels[0]?.id)||1;
  const body={
    sale_id:saleId||undefined,
    booking_id:bookingId||undefined,
    room_number:roomStr,
    hotel_id:hotelVal,
    income_date:entryDate,
    sales_person:salesVal,
    photographer:photoNames.join(', '),
    deposit_applied:num($('saleDeposit').value),
    income_usd:num($('saleUsd').value),
    income_eur:num($('saleEur').value),
    income_le_k:num($('saleCash').value),
    income_le_m:num($('saleOffice').value),
    le_to_usd:num($('saleRate').value)||50,
    cost_dress:num($('costDress').value),
    cost_usb:num($('costUsb').value),
    cost_album:num($('costAlbum').value),
    adjustment_reason:($('saleAdjustReason')?.value||'').trim()
  };
  const checkGross=body.deposit_applied+body.income_usd+body.income_eur+((body.income_le_k+body.income_le_m)/(body.le_to_usd||50));
  if(checkGross<=0)return toast('يرجى إدخال المبلغ بأحد أنواعه (دولار $، يورو €، كاش مصري LE، أو مكتب LE)','bad');
  const gross=body.deposit_applied+body.income_usd+body.income_eur+((body.income_le_k+body.income_le_m)/(body.le_to_usd||50)),cost=body.cost_dress+body.cost_usb+body.cost_album,net=gross-cost;
  const actionLabel=saleId?'حفظ التعديلات على سجل الدخل':'حفظ بيانات الدخل الجديد';
  if(!confirmAction(`هل أنت متأكد من ${actionLabel}؟\nالتاريخ: ${entryDate}\n\nإجمالي الدخل: ${money(gross)} $\nإجمالي التكاليف: ${money(cost)} $\nالصافي: ${money(net)} $\n\nالمصورين: ${photoNames.join('، ')}\nحصة الصافي لكل مصور: ${money(net/photoNames.length)} $`))return;
  try{
    const r=saleId
      ? await apiJSON(`/api/daily-sales/${saleId}`,'PUT',body)
      : await apiJSON('/api/daily-sales','POST',body);
    toast(saleId||r.updated ? `✏️ تم تعديل وتحديث دخل الأوردر بنجاح (الصافي: ${money(r.daily_total)}$)` : `💾 تم تسجيل دخل الأوردر بصافي ${money(r.daily_total)}$`);
    clearSaleForm();
    await Promise.allSettled([loadEligible(),loadSalesSearch(),loadAnalytics()]);
  }catch(err){
    toast(err.message,'bad');
  }
}

async function deleteCurrentSaleFromForm(){
  const saleId=num($('saleId')?.value);
  if(!saleId)return;
  if(!confirmAction(`هل أنت متأكد من حذف سجل الدخل #${saleId} نهائياً؟`))return;
  try{
    await api(`/api/daily-sales/${saleId}`,{method:'DELETE'});
    toast('تم حذف سجل الدخل بنجاح');
    clearSaleForm();
    await Promise.allSettled([loadEligible(),loadSalesSearch(),loadAnalytics()]);
  }catch(err){
    toast(err.message,'bad');
  }
}

function editSaleFromTable(saleId){
  const r=salesRows.find(x=>Number(x.id)===Number(saleId));
  if(!r)return toast('لم يتم العثور على سجل الدخل','bad');
  // الانتقال إلى تبويب تسجيل وتعديل الدخل وتعبئة الفورم بالسجل المحدد
  const entryTabBtn=document.querySelector('[data-tab-target="dsEntry"]');
  if(entryTabBtn)entryTabBtn.click();
  populateSaleFormFromRecord(r, null);
  $('selectedOrderInfo').textContent=`تعديل مباشر للسجل #${r.id} • غرفة ${r.room_number||'-'} • ${r.hotel_name||''} • تاريخ ${r.income_date||''}`;
  $('saleForm')?.scrollIntoView({behavior:'smooth',block:'start'});
  toast(`تم تحميل سجل الدخل #${r.id} (غرفة ${r.room_number||'-'}) للتعديل ✏️`);
}

async function deleteSaleById(saleId){
  if(!confirmAction(`هل أنت متأكد من حذف سجل الدخل #${saleId}؟`))return;
  try{
    await api(`/api/daily-sales/${saleId}`,{method:'DELETE'});
    toast('تم حذف سجل الدخل');
    if(num($('saleId')?.value)===Number(saleId))clearSaleForm();
    await Promise.allSettled([loadEligible(),loadSalesSearch(),loadAnalytics()]);
  }catch(e){
    toast(e.message,'bad');
  }
}

let incomeNotesRows=[];
async function loadSalesSearch(){const start=$('dsStart').value,end=$('dsEnd').value;if($('dsDataType').value==='deposits'){depositRows=await api(`/api/deposits?start=${start}&end=${end}${$('dsHotel').value?'&hotel_id='+$('dsHotel').value:''}`);renderDeposits()}else{const x=await api(`/api/daily-sales?start=${start}&end=${end}${$('dsHotel').value?'&hotel_id='+$('dsHotel').value:''}`);salesRows=x.rows||[];incomeNotesRows=x.notes||[];renderSales(x.summary||{});renderDailyIncomeNotes()}await loadCoinKpi()}
function filteredSales(){return salesRows.filter(r=>(!$('dsSalesFilter').value||r.sales_person===$('dsSalesFilter').value)&&(!$('dsPhotoFilter').value||String(r.photographer||'').includes($('dsPhotoFilter').value)))}
function renderSales(summary){const rows=filteredSales();$('searchHead').innerHTML='<tr><th>#</th><th>الفندق</th><th>الغرفة</th><th>السيلز</th><th>المصور</th><th>العربون</th><th>$</th><th>€</th><th>LE مكتب</th><th>LE كاش</th><th>الريت</th><th>إجمالي</th><th>Dress</th><th>USB</th><th>Album</th><th>تكلفة</th><th>الصافي</th><th>التاريخ</th><th>إجراءات</th></tr>';$('searchBody').innerHTML=rows.map((r,i)=>`<tr data-sale-id="${r.id}"><td>${i+1}</td><td>${esc(r.hotel_name||r.hotel_id)}</td><td><b>${esc(r.room_number||'-')}</b></td><td>${esc(r.sales_person)}</td><td>${esc(r.photographer)}</td><td>${money(r.deposit_applied)}</td><td>${money(r.income_usd)}</td><td>${money(r.income_eur)}</td><td>${money(r.income_le_m)}</td><td>${money(r.income_le_k)}</td><td>${money(r.le_to_usd)}</td><td>${money(r.gross_total)}</td><td>${money(r.cost_dress)}</td><td>${money(r.cost_usb)}</td><td>${money(r.cost_album)}</td><td>${money(r.cost_total)}</td><td><b>${money(r.daily_total)}</b></td><td>${esc(r.income_date)}</td><td><div class="context-actions"><button class="mini-btn purple" title="طباعة إيصال مبيعات حراري POS" onclick="printSalePosById(${r.id})">🖨️ إيصال</button>${(window.PHOTOGRAPHER_ONLY||window.SALES_ONLY)?'':`<button class="mini-btn blue" title="تعديل الدخل" onclick="editSaleFromTable(${r.id})">✏️ تعديل</button><button class="mini-btn red" title="حذف السجل" onclick="deleteSaleById(${r.id})">🗑️</button>`}</div></td></tr>`).join('')||'<tr><td colspan="19" class="empty-state">لا توجد مبيعات</td></tr>';const rs=rows;
const nIn=(incomeNotesRows||[]).filter(n=>String(n.note_type||'').toUpperCase()==='IN');
const nOut=(incomeNotesRows||[]).filter(n=>String(n.note_type||'').toUpperCase()!=='IN');
const diffUsd=nIn.reduce((a,n)=>a+num(n.amount_usd),0)-nOut.reduce((a,n)=>a+num(n.amount_usd),0);
const diffEur=nIn.reduce((a,n)=>a+num(n.amount_eur),0)-nOut.reduce((a,n)=>a+num(n.amount_eur),0);
const diffCash=nIn.reduce((a,n)=>a+num(n.amount_le_cash),0)-nOut.reduce((a,n)=>a+num(n.amount_le_cash),0);
const diffOffice=nIn.reduce((a,n)=>a+num(n.amount_le_office),0)-nOut.reduce((a,n)=>a+num(n.amount_le_office),0);
const ordersNet=rs.reduce((a,x)=>a+num(x.daily_total),0);
const totInEq=nIn.reduce((a,n)=>a+num(n.equivalent_usd),0);
const totOutEq=nOut.reduce((a,n)=>a+num(n.equivalent_usd),0);
const finalNet=ordersNet+totInEq-totOutEq;
$('kUsd').textContent=money(rs.reduce((a,x)=>a+num(x.income_usd),0)+diffUsd);
$('kEur').textContent=money(rs.reduce((a,x)=>a+num(x.income_eur),0)+diffEur);
$('kCash').textContent=money(rs.reduce((a,x)=>a+num(x.income_le_k),0)+diffCash);
$('kOffice').textContent=money(rs.reduce((a,x)=>a+num(x.income_le_m),0)+diffOffice);
$('kNet').textContent=money(finalNet);
if($('dinOrdersNet'))$('dinOrdersNet').textContent='$'+money(ordersNet);
if($('dinTotalIn'))$('dinTotalIn').textContent='+$'+money(totInEq);
if($('dinTotalOut'))$('dinTotalOut').textContent='-$'+money(totOutEq);
if($('dinFinalNet'))$('dinFinalNet').textContent='$'+money(finalNet);}
function renderDeposits(){
  $('searchHead').innerHTML='<tr><th>#</th><th>الغرفة</th><th>مسؤول مبيعات العربون</th><th>$</th><th>€</th><th>كاش LE</th><th>فيزا LE</th><th>التاريخ</th><th>إجراءات</th></tr>';
  $('searchBody').innerHTML=depositRows.map((r,i)=>`<tr><td>${i+1}</td><td><b>${esc(r.room_number)}</b></td><td>${esc(r.deposit_sales_person)}</td><td>${money(r.deposit_usd)}</td><td>${money(r.deposit_eur)}</td><td>${money(r.deposit_le_cash)}</td><td>${money(r.deposit_le_visa)}</td><td>${esc(r.deposit_date)}</td><td><div class="context-actions"><button class="mini-btn blue" title="تعديل العربون" onclick="openEditDepositModal(${r.id})">✏️ تعديل</button><button class="mini-btn red" title="حذف العربون" onclick="deleteDepositById(${r.id})">🗑️</button></div></td></tr>`).join('')||'<tr><td colspan="9" class="empty-state">لا توجد عرابين</td></tr>';
  $('kUsd').textContent=money(depositRows.reduce((a,x)=>a+num(x.deposit_usd),0));
  $('kEur').textContent=money(depositRows.reduce((a,x)=>a+num(x.deposit_eur),0));
  $('kCash').textContent=money(depositRows.reduce((a,x)=>a+num(x.deposit_le_cash),0));
  $('kOffice').textContent=money(depositRows.reduce((a,x)=>a+num(x.deposit_le_visa),0));
  $('kNet').textContent='-';
}

function openEditDepositModal(id){
  const r=depositRows.find(x=>Number(x.id)===Number(id));
  if(!r)return toast('سجل العربون غير موجود','bad');
  showModal(`
    <div class="modal-title">
      <h2>✏️ تعديل سجل العربون #${r.id}</h2>
      <p>تعديل مبالغ العربون أو رقم الغرفة أو مسؤول المبيعات</p>
    </div>
    <form id="editDepositForm">
      <div class="form-grid three">
        <div class="field"><label>رقم الغرفة</label><input class="input" id="edRoom" value="${esc(r.room_number||'')}" required></div>
        <div class="field"><label>مسؤول المبيعات (Sales)</label><input class="input" id="edSales" value="${esc(r.deposit_sales_person||'')}"></div>
        <div class="field"><label>تاريخ العربون</label><input class="input" type="date" id="edDate" value="${esc(String(r.deposit_date||'').slice(0,10))}"></div>
      </div>
      <div class="form-grid four" style="margin-top:12px;">
        <div class="field"><label>عربون دولار ($)</label><input class="input" type="number" step=".01" id="edUsd" value="${num(r.deposit_usd)}"></div>
        <div class="field"><label>عربون يورو (€)</label><input class="input" type="number" step=".01" id="edEur" value="${num(r.deposit_eur)}"></div>
        <div class="field"><label>كاش مصري (LE)</label><input class="input" type="number" step=".01" id="edCash" value="${num(r.deposit_le_cash)}"></div>
        <div class="field"><label>فيزا مصري (LE)</label><input class="input" type="number" step=".01" id="edVisa" value="${num(r.deposit_le_visa)}"></div>
      </div>
      <div class="modal-actions">
        <button type="button" class="btn" onclick="closeModal()">إلغاء</button>
        <button type="submit" class="btn green">💾 حفظ تعديلات العربون</button>
      </div>
    </form>
  `,'modal-lg');
  $('editDepositForm').addEventListener('submit',async e=>{
    e.preventDefault();
    try{
      await apiJSON(`/api/deposits/${id}`,'PUT',{
        room_number:$('edRoom').value.trim(),
        deposit_sales_person:$('edSales').value.trim(),
        deposit_date:$('edDate').value,
        deposit_usd:num($('edUsd').value),
        deposit_eur:num($('edEur').value),
        deposit_le_cash:num($('edCash').value),
        deposit_le_visa:num($('edVisa').value)
      });
      toast('تم تعديل سجل العربون بنجاح');
      closeModal();
      await Promise.allSettled([loadSalesSearch(),loadEligible()]);
    }catch(err){
      toast(err.message,'bad');
    }
  });
}

async function deleteDepositById(id){
  if(!confirmAction(`هل أنت متأكد من حذف سجل العربون #${id}؟`))return;
  try{
    await api(`/api/deposits/${id}`,{method:'DELETE'});
    toast('تم حذف سجل العربون');
    await Promise.allSettled([loadSalesSearch(),loadEligible()]);
  }catch(e){
    toast(e.message,'bad');
  }
}

async function openIncomeAdjustments(txId=null){
  const q=txId?`?transaction_id=${txId}`:'';
  const rows=await apiSafe(`/api/daily-sales/adjustments${q}`,[],'سجل التعديلات');
  showModal(`
    <div class="modal-title">
      <h2>📜 سجل تاريخ تعديلات الدخل ${txId?`للسجل #${txId}`:'الشامل'}</h2>
      <p>يوثق جميع التعديلات المالية التي تمت على أوردرات الدخل اليومي والفرق المالي والمسؤول عنها</p>
    </div>
    <div class="table-wrap maxh">
      <table class="modern-table">
        <thead>
          <tr><th>#</th><th>رقم السجل</th><th>الغرفة</th><th>الفندق</th><th>الفرق المالي ($)</th><th>سبب وتفاصيل التعديل</th><th>بواسطة</th><th>التاريخ</th></tr>
        </thead>
        <tbody>
          ${rows.map(r=>{
            const imp=num(r.impact_amount);
            const impBadge=imp>0?`<span class="badge green">+${money(imp)} $</span>`:imp<0?`<span class="badge red">${money(imp)} $</span>`:`<span class="badge blue">0.00 $</span>`;
            return `<tr>
              <td>${r.adjustment_id}</td>
              <td><b>#${r.transaction_id}</b></td>
              <td><b>${esc(r.room_number||'-')}</b></td>
              <td>${esc(r.hotel_name||r.hotel_id||'-')}</td>
              <td>${impBadge}</td>
              <td>${esc(r.reason||'')}</td>
              <td><b>${esc(r.created_by||'')}</b></td>
              <td>${esc(r.adjustment_date||'')}</td>
            </tr>`;
          }).join('')||'<tr><td colspan="8" class="empty-state">لا توجد تعديلات مسجلة بعد</td></tr>'}
        </tbody>
      </table>
    </div>
  `,'modal-xl');
}
async function loadCoinKpi(){const x=await apiSafe('/api/coin-safe'+($('dsHotel').value?'?hotel_id='+$('dsHotel').value:''),{rows:[],balance:0},'');if($('kCoinBal'))$('kCoinBal').textContent=money(x.balance);if($('kCoin'))$('kCoin').textContent=money((x.rows||[]).reduce((a,r)=>a+(r.transaction_type==='OUT'?num(r.amount):0),0))}
async function loadAnalytics(){const m=$('anMonth').value||monthISO();let [y,mo]=m.split('-'),from=1,to=new Date(Number(y),Number(mo),0).getDate();const p=$('anPeriod').value;if(p==='p1')to=10;if(p==='p2'){from=11;to=20}if(p==='p3')from=21;const start=`${m}-${String(from).padStart(2,'0')}`,end=`${m}-${String(to).padStart(2,'0')}`;const x=await api(`/api/daily-sales/analytics?start=${start}&end=${end}${$('dsHotel').value?'&hotel_id='+$('dsHotel').value:''}`);const cards=arr=>arr.map((r,i)=>`<div class="timeline-card"><b>#${i+1}</b><span>${esc(r.name)}</span><strong>${money(r.value)} $</strong></div>`).join('')||'<div class="empty-state">لا توجد بيانات</div>';$('photoRanking').innerHTML=cards(x.photographers||[]);$('salesRanking').innerHTML=cards(x.sales||[]);$('trendList').innerHTML=(x.trend||[]).map(r=>`<div class="timeline-card"><b>${esc(r.date)}</b><span>صافي الدخل</span><strong>${money(r.value)} $</strong></div>`).join('')||'<div class="empty-state">لا توجد بيانات</div>'}
async function loadCoin(){const x=await apiSafe('/api/coin-safe'+($('dsHotel').value?'?hotel_id='+$('dsHotel').value:''),{rows:[],balance:0},'');coinRows=x.rows||[];const cIn=coinRows.filter(x=>x.transaction_type==='IN').reduce((a,x)=>a+num(x.amount),0);const cOut=coinRows.filter(x=>x.transaction_type==='OUT').reduce((a,x)=>a+num(x.amount),0);const bal=num(x.balance)||(cIn-cOut);if($('coinBalance'))$('coinBalance').textContent=money(bal);if($('coinIn'))$('coinIn').textContent=money(cIn);if($('coinOut'))$('coinOut').textContent=money(cOut);if($('kCoinBal'))$('kCoinBal').textContent=money(bal);if($('kCoin'))$('kCoin').textContent=money(cOut);if($('coinBody'))$('coinBody').innerHTML=coinRows.map(r=>`<tr><td>${r.transaction_id}</td><td>${esc(r.hotel_name||r.hotel_id)}</td><td>${esc(r.user_name)}</td><td><span class="badge ${r.transaction_type==='IN'?'green':'red'}">${r.transaction_type==='IN'?'وارد IN':'منصرف OUT'}</span></td><td><b>€${money(r.amount)}</b></td><td>${esc(r.notes||'')}</td><td>${esc(r.created_at||'')}</td><td><button type="button" class="mini-btn amber" onclick="editCoinById(${r.transaction_id})">✏️ تعديل</button> <button type="button" class="mini-btn red" onclick="deleteCoin(${r.transaction_id})">🗑️ حذف</button></td></tr>`).join('')||'<tr><td colspan="8">لا توجد حركات</td></tr>'}
function editCoinById(id){const r=coinRows.find(x=>x.transaction_id===id);if(r)editCoin(r)}
function editCoin(r){$('coinId').value=r.transaction_id;$('coinHotel').value=r.hotel_id;$('coinType').value=r.transaction_type;$('coinAmount').value=r.amount;$('coinNotes').value=r.notes||''}function cancelCoinEdit(){$('coinForm').reset();$('coinId').value=''}
async function saveCoin(e){e.preventDefault();const id=$('coinId').value,body={hotel_id:$('coinHotel').value,transaction_type:$('coinType').value,amount:num($('coinAmount').value),notes:$('coinNotes').value};try{await apiJSON(id?'/api/coin-safe/'+id:'/api/coin-safe',id?'PUT':'POST',body);toast('تم حفظ حركة الكوين');cancelCoinEdit();loadCoin();loadSalesSearch()}catch(e){toast(e.message,'bad')}}async function deleteCoin(id){if(!confirmAction('حذف حركة الكوين؟'))return;await api('/api/coin-safe/'+id,{method:'DELETE'});loadCoin();loadSalesSearch()}
async function openAudit(){const rows=await api('/api/audit?limit=300');showModal(`<div class="modal-title"><h2>📜 System Audit</h2></div><div class="table-wrap maxh"><table><thead><tr><th>#</th><th>المستخدم</th><th>العملية</th><th>الجدول</th><th>التفاصيل</th><th>التاريخ</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${r.id}</td><td>${esc(r.actor||r.user_id||'-')}</td><td>${esc(r.action_type)}</td><td>${esc(r.affected_table)}</td><td>${esc(r.details)}</td><td>${esc(r.created_at)}</td></tr>`).join('')}</tbody></table></div>`,'modal-xl')}
function exportSalesCSV(){if($('dsDataType').value==='deposits')downloadCSV('Deposits.csv',['الغرفة','السيلز','$','€','كاش','فيزا','التاريخ'],depositRows.map(r=>[r.room_number,r.deposit_sales_person,r.deposit_usd,r.deposit_eur,r.deposit_le_cash,r.deposit_le_visa,r.deposit_date]));else downloadCSV('Daily_Income.csv',['الفندق','السيلز','المصور','العربون','$','€','LE مكتب','LE كاش','الريت','التكلفة','الصافي','التاريخ'],filteredSales().map(r=>[r.hotel_name,r.sales_person,r.photographer,r.deposit_applied,r.income_usd,r.income_eur,r.income_le_m,r.income_le_k,r.le_to_usd,r.cost_total,r.daily_total,r.income_date]))}
const OFFICIAL_DAILY_REPORT_CSS = `
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
    const phList = phRaw.split(/[+,،/\\|&]+/).map(s => s.trim()).filter(Boolean);
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
initDaily();


// ===== moved from templates/daily_sales.html (inline script) =====
    // ----------------------------------------------------
    // 1. فلتر التواريخ السريعة لشاشة (تسجيل الدخل)
    // ----------------------------------------------------
    function applyQuickEntryDate() {
        const val = document.getElementById('quickEntryDate').value;
        const dateInput = document.getElementById('dsEntryDate');
        const now = new Date();

        const formatDate = (dateObj) => {
            const y = dateObj.getFullYear();
            const m = String(dateObj.getMonth() + 1).padStart(2, '0');
            const d = String(dateObj.getDate()).padStart(2, '0');
            return `${y}-${m}-${d}`;
        };

        if (val === 'today') {
            dateInput.value = formatDate(now);
            if (typeof loadEligible === 'function') loadEligible();
        } else if (val === 'yesterday') {
            const yesterday = new Date(now);
            yesterday.setDate(now.getDate() - 1);
            dateInput.value = formatDate(yesterday);
            if (typeof loadEligible === 'function') loadEligible();
        } else if (val === 'custom') {
            dateInput.focus();
            if (typeof dateInput.showPicker === 'function') {
                dateInput.showPicker();
            }
        }
    }

    // إذا قام المستخدم بتغيير التاريخ يدوياً، نجعل القائمة "مخصص" ونعيد تحميل الأوردرات
    document.getElementById('dsEntryDate').addEventListener('change', function() {
        document.getElementById('quickEntryDate').value = 'custom';
        if (typeof loadEligible === 'function') loadEligible();
    });


    // ----------------------------------------------------
    // 2. فلتر التواريخ السريعة لشاشة (البحث والعرابين)
    // ----------------------------------------------------
    function applyQuickDates() {
        const val = document.getElementById('quickDateFilter').value;
        if (val === 'custom') return;

        const startInput = document.getElementById('dsStart');
        const endInput = document.getElementById('dsEnd');
        const now = new Date();

        const formatDate = (dateObj) => {
            const y = dateObj.getFullYear();
            const m = String(dateObj.getMonth() + 1).padStart(2, '0');
            const d = String(dateObj.getDate()).padStart(2, '0');
            return `${y}-${m}-${d}`;
        };

        if (val === 'today') {
            startInput.value = formatDate(now);
            endInput.value = formatDate(now);
        } 
        else if (val === 'yesterday') {
            const yesterday = new Date(now);
            yesterday.setDate(now.getDate() - 1);
            startInput.value = formatDate(yesterday);
            endInput.value = formatDate(yesterday);
        } 
        else if (val === 'this_month') {
            const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
            const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
            startInput.value = formatDate(firstDay);
            endInput.value = formatDate(lastDay);
        } 
        else if (val === 'last_month') {
            const firstDay = new Date(now.getFullYear(), now.getMonth() - 1, 1);
            const lastDay = new Date(now.getFullYear(), now.getMonth(), 0);
            startInput.value = formatDate(firstDay);
            endInput.value = formatDate(lastDay);
        }

        if (typeof loadSalesSearch === 'function') {
            loadSalesSearch();
        }
    }


// V80: قفل الفلاتر وإخفاء أدوات الإدارة عند دخول المصور أو السيلز (العزل الشخصي)
function enforcePersonalScopeDailySales(){
  if(!window.PERSONAL_SCOPE)return;
  const myNick=(window.CURRENT_USER?.nickname||window.CURRENT_USER?.full_name||'').trim();
  const roles=(window.USER_ROLES||[]).map(r=>String(r).toLowerCase());
  const isSales=roles.includes('sales'), isPhoto=roles.includes('photographer');

  // إخفاء تبويب خزنة الكوين وأزرار النسخ الاحتياطي والـ Audit عن المصور والسيلز
  const coinTab=document.querySelector('[data-tab-target="dsCoin"]');
  if(coinTab)coinTab.style.display='none';
  $$('#dsSearch .action-grid button').forEach(btn=>{
    if(/نسخ احتياطي|Audit|سجل تعديلات/.test(btn.textContent||''))btn.style.display='none';
  });

  // قفل فلاتر السيلز والمصور على اسم الموظف نفسه فقط
  if(isSales && !isPhoto && $('dsSalesFilter') && myNick){
    $('dsSalesFilter').innerHTML=`<option value="${esc(myNick)}">${esc(myNick)} (مبيعاتي فقط 🔒)</option>`;
    $('dsSalesFilter').value=myNick;
    $('dsSalesFilter').disabled=true;
  }
  if(isPhoto && !isSales && $('dsPhotoFilter') && myNick){
    $('dsPhotoFilter').innerHTML=`<option value="${esc(myNick)}">${esc(myNick)} (أوردراتي فقط 🔒)</option>`;
    $('dsPhotoFilter').value=myNick;
    $('dsPhotoFilter').disabled=true;
  }
}
setTimeout(enforcePersonalScopeDailySales, 150);


function printSalePosById(saleId) {
  const r = (salesRows || []).find(x => Number(x.id) === Number(saleId));
  if (!r) return toast('لم يتم العثور على سجل المبيعات', 'bad');
  openThermalSalesReceiptModal(r);
}

function printCurrentSaleFormPosReceipt() {
  const room = ($('saleRoomNumber')?.value || '').trim();
  if (!room) {
    return toast('يرجى اختيار أوردر من القائمة اليسرى أو تحديد سجل مبيعات أولاً لطباعة إيصاله', 'bad');
  }
  const rate = num($('saleRate')?.value) || 50;
  const dep = num($('saleDeposit')?.value);
  const usd = num($('saleUsd')?.value);
  const eur = num($('saleEur')?.value);
  const cash = num($('saleCash')?.value);
  const office = num($('saleOffice')?.value);
  const gross = dep + usd + eur + ((cash + office) / rate);
  const costs = num($('costDress')?.value) + num($('costUsb')?.value) + num($('costAlbum')?.value);
  openThermalSalesReceiptModal({
    id: $('saleId')?.value || '',
    room_number: room,
    hotel_name: $('dsHotel')?.selectedOptions?.[0]?.textContent || 'PHOTO TEAM RESORT',
    sales_person: $('saleSales')?.value || '',
    photographer: $('salePhotog')?.value || '',
    deposit_applied: dep,
    income_usd: usd,
    income_eur: eur,
    income_le_k: cash,
    income_le_m: office,
    le_to_usd: rate,
    gross_total: gross,
    cost_total: costs,
    daily_total: gross - costs,
    income_date: $('saleIncomeDate')?.value || todayISO()
  });
}

window.printSalePosById = printSalePosById;
window.printCurrentSaleFormPosReceipt = printCurrentSaleFormPosReceipt;
window.printSalesReport = printSalesReport;

function renderDailyIncomeNotes(){
  const body=$('dailyIncomeNotesBody');
  if(!body)return;
  if(!incomeNotesRows || !incomeNotesRows.length){
    body.innerHTML='<tr><td colspan="13" class="empty-state">لا توجد ملاحظات مسجلة في هذه الفترة — اضغط على (➕ إضافة ملاحظة) لتسجيل فلوس مبعوتة لواحد أو فلوس جاية لينا</td></tr>';
    return;
  }
  body.innerHTML=incomeNotesRows.map((n,i)=>{
    const isIn=String(n.note_type||'').toUpperCase()==='IN';
    return `<tr>
      <td>${i+1}</td>
      <td>${esc(n.note_date)}</td>
      <td>${esc(n.hotel_name||'الفندق')}</td>
      <td>${isIn?'<span class="badge green">➕ وارد</span>':'<span class="badge red">➖ منصرف</span>'}</td>
      <td><b>${esc(n.person_name||'-')}</b></td>
      <td>${esc(n.note_text)}</td>
      <td>${num(n.amount_usd)?'$'+money(n.amount_usd):'-'}</td>
      <td>${num(n.amount_eur)?'€'+money(n.amount_eur):'-'}</td>
      <td>${num(n.amount_le_cash)?money(n.amount_le_cash)+' LE':'-'}</td>
      <td>${num(n.amount_le_office)?money(n.amount_le_office)+' LE':'-'}</td>
      <td><b style="color:${isIn?'#10b981':'#ef4444'};direction:ltr;display:inline-block;">${isIn?'+':'-'}$${money(n.equivalent_usd)}</b></td>
      <td><small>${esc(n.created_by||'المدير')}</small></td>
      <td>
        <div class="context-actions">
          <button class="mini-btn blue" onclick="openDailyIncomeNoteModal(${n.id})">✏️</button>
          <button class="mini-btn red" onclick="deleteDailyIncomeNote(${n.id})">🗑️</button>
        </div>
      </td>
    </tr>`;
  }).join('');
}

function openDailyIncomeNoteModal(editId=null){
  const rec=editId?(incomeNotesRows||[]).find(x=>Number(x.id)===Number(editId)):null;
  const hotelOpts=(dsHotels||[]).map(h=>`<option value="${h.id}" ${(rec&&Number(rec.hotel_id)===Number(h.id))||(!rec&&Number($('dsHotel')?.value)===Number(h.id))?'selected':''}>${esc(h.hotel_name)}</option>`).join('');
  showModal(`
    <div class="modal-title">
      <h2>${rec?'✏️ تعديل ملاحظة الدخل اليومي':'📝➕ إضافة ملاحظة على الدخل اليومي (وارد لينا + / صادر مبعوت -)'}</h2>
      <p></p>
    </div>
    <form id="dinModalForm">
      <div class="form-grid three">
        <div class="field">
          <label>نوع الحركة وتأثيرها على الدخل *</label>
          <select class="input" id="dinType" onchange="calcDinPreview()" style="font-weight:900;">
            <option value="OUT" ${(!rec||rec.note_type==='OUT')?'selected':''}>➖ منصرف / مخصوم</option>
            <option value="IN" ${(rec&&rec.note_type==='IN')?'selected':''}>➕ وارد / مضاف</option>
          </select>
        </div>
        <div class="field">
          <label>الفندق *</label>
          <select class="input" id="dinHotel">${hotelOpts}</select>
        </div>
        <div class="field">
          <label>التاريخ *</label>
          <input class="input" type="date" id="dinDate" value="${esc(rec?String(rec.note_date).slice(0,10):($('dsEntryDate')?.value||todayISO()))}" required>
        </div>
      </div>
      <div class="form-grid two" style="margin-top:12px;">
        <div class="field">
          <label>الطرف / الجهة *</label>
          <input class="input" id="dinPerson" value="${esc(rec?.person_name||'')}" placeholder="مثال: مندوب بأمر الأونر / استلام نقدية من..." required>
        </div>
        <div class="field">
          <label>البيان *</label>
          <input class="input" id="dinText" value="${esc(rec?.note_text||'')}" placeholder="مثال: الأونر طلب تحويل مبلغ لـ... / فلوس واردة من..." required>
        </div>
      </div>
      <div class="form-grid four" style="margin-top:12px;">
        <div class="field"><label>المبلغ بالدولار ($)</label><input class="input" type="number" step=".01" id="dinUsd" value="${num(rec?.amount_usd||0)}" oninput="calcDinPreview()"></div>
        <div class="field"><label>المبلغ باليورو (€)</label><input class="input" type="number" step=".01" id="dinEur" value="${num(rec?.amount_eur||0)}" oninput="calcDinPreview()"></div>
        <div class="field"><label>المبلغ كاش مصري (LE)</label><input class="input" type="number" step=".01" id="dinCash" value="${num(rec?.amount_le_cash||0)}" oninput="calcDinPreview()"></div>
        <div class="field"><label>المبلغ مكتب/تحويل (LE)</label><input class="input" type="number" step=".01" id="dinOffice" value="${num(rec?.amount_le_office||0)}" oninput="calcDinPreview()"></div>
      </div>
      <div id="dinCalcPreviewBox" style="margin-top:14px;padding:12px 16px;border-radius:12px;background:var(--bg-surface-2);border:1.5px solid var(--border-strong);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
        <span>التأثير التلقائي على صافي الدخل اليومي:</span>
        <strong id="dinEquivText" style="font-size:18px;">$0.00</strong>
      </div>
      <div class="modal-actions">
        <button type="button" class="btn" onclick="closeModal()">إلغاء</button>
        <button type="submit" class="btn green">💾 حفظ الملاحظة وحسابها مع الدخل تلقائياً</button>
      </div>
    </form>
  `,'modal-lg');
  calcDinPreview();
  $('dinModalForm').addEventListener('submit', async e=>{
    e.preventDefault();
    try{
      await apiJSON('/api/daily-sales/notes','POST',{
        id:rec?.id||undefined,
        note_type:$('dinType').value,
        hotel_id:num($('dinHotel').value)||1,
        note_date:$('dinDate').value,
        person_name:$('dinPerson').value.trim(),
        note_text:$('dinText').value.trim(),
        amount_usd:num($('dinUsd').value),
        amount_eur:num($('dinEur').value),
        amount_le_cash:num($('dinCash').value),
        amount_le_office:num($('dinOffice').value),
        exchange_rate:50
      });
      closeModal();
      toast('✅ تم حفظ الملاحظة وتحديث إجمالي الدخل اليومي تلقائياً!');
      await loadSalesSearch();
    }catch(err){
      toast(err.message,'bad');
    }
  });
}
window.openDailyIncomeNoteModal = openDailyIncomeNoteModal;

function calcDinPreview(){
  const t=$('dinType')?.value||'OUT';
  const eq=num($('dinUsd')?.value)+num($('dinEur')?.value)+((num($('dinCash')?.value)+num($('dinOffice')?.value))/50);
  const el=$('dinEquivText');
  if(!el)return;
  if(t==='IN'){
    el.style.color='#10b981';
    el.textContent=`➕ زيادة على إجمالي الدخل: +$${money(eq)}`;
  }else{
    el.style.color='#ef4444';
    el.textContent=`➖ خصم/نقص من إجمالي الدخل: -$${money(eq)}`;
  }
}
window.calcDinPreview = calcDinPreview;

async function deleteDailyIncomeNote(id){
  if(!confirmAction('هل أنت متأكد من حذف هذه الملاحظة وإلغاء تأثيرها من إجمالي الدخل؟'))return;
  try{
    await api(`/api/daily-sales/notes/${id}`,{method:'DELETE'});
    toast('تم حذف الملاحظة وتحديث إجمالي الدخل');
    await loadSalesSearch();
  }catch(e){
    toast(e.message,'bad');
  }
}
window.deleteDailyIncomeNote = deleteDailyIncomeNote;



async function printAllHotelsReportPDF() {
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
window.printAllHotelsReportPDF = printAllHotelsReportPDF;


// ============================================================================
// 🔒 كود قفل حسابات اليوم المعتمد + طلب إذن تعديل من المدير للمحاسب (قبول / رفض)
// ============================================================================
let CURRENT_DAY_LOCK_STATE = { locks: [], requests: [], active_lock: null, can_lock: false, is_blocked_for_me: false };

async function refreshDayLockStatus() {
  const targetDate = $('dsEntryDate')?.value || $('dsEnd')?.value || todayISO();
  const hotelSel = $('dsHotel');
  const hotelName = (hotelSel && hotelSel.value && hotelSel.selectedOptions?.[0]) ? hotelSel.selectedOptions[0].textContent.trim() : 'جميع الفنادق';
  try {
    const data = await api(`/api/day-locks?date=${encodeURIComponent(targetDate)}&hotel_name=${encodeURIComponent(hotelName)}`);
    CURRENT_DAY_LOCK_STATE = data || CURRENT_DAY_LOCK_STATE;
    renderDayLockBar(targetDate, hotelName);
  } catch (e) {}
}
window.refreshDayLockStatus = refreshDayLockStatus;

function renderDayLockBar(targetDate, hotelName) {
  const badge = $('dayLockStatusBadge');
  const sub = $('dayLockSubText');
  const btnToggle = $('btnToggleDayLock');
  const pendingSpan = $('dayLockPendingCount');
  const st = CURRENT_DAY_LOCK_STATE || {};
  const pendingReqs = (st.requests || []).filter(r => r.status === 'Pending');
  if (pendingSpan) pendingSpan.textContent = String(pendingReqs.length);

  const lk = st.active_lock;
  const isLocked = Boolean(lk && Number(lk.is_locked) === 1 && Number(lk.unlocked_for_manager) === 0);
  const isUnlockedForMgr = Boolean(lk && Number(lk.unlocked_for_manager) === 1);

  if (badge) {
    if (isLocked) {
      badge.className = 'badge red';
      badge.textContent = `🔒 حسابات يوم (${targetDate}) مقفولة ومعتمدة (${lk.hotel_name || hotelName})`;
    } else if (isUnlockedForMgr) {
      badge.className = 'badge amber';
      badge.textContent = `🔓 تم فتح تعديل يوم (${targetDate}) للمدير بموافقة المحاسب`;
    } else {
      badge.className = 'badge green';
      badge.textContent = `🟢 حسابات يوم (${targetDate}) مفتوحة للتعديل`;
    }
  }
  if (sub) {
    sub.textContent = isLocked
      ? `تم القفل بواسطة (${lk.locked_by || 'المحاسب'}) — أي تعديل من المدير يتطلب إرسال طلب موافقة للمحاسب`
      : `يمكن للمحاسب قفل حسابات اليوم بعد المراجعة لمنع أي تعديل إلا بإذن`;
  }
  if (btnToggle) {
    if (isLocked) {
      btnToggle.className = 'btn green';
      btnToggle.textContent = '🔓 فك قفل حسابات اليوم';
    } else {
      btnToggle.className = 'btn red';
      btnToggle.textContent = '🔒 قفل واعتماد حسابات اليوم';
    }
  }
}

async function toggleCurrentDayLock() {
  const targetDate = $('dsEntryDate')?.value || $('dsEnd')?.value || todayISO();
  const hotelSel = $('dsHotel');
  const hotelName = (hotelSel && hotelSel.value && hotelSel.selectedOptions?.[0]) ? hotelSel.selectedOptions[0].textContent.trim() : 'جميع الفنادق';
  const lk = CURRENT_DAY_LOCK_STATE?.active_lock;
  const currentlyLocked = Boolean(lk && Number(lk.is_locked) === 1 && Number(lk.unlocked_for_manager) === 0);
  try {
    await apiJSON('/api/day-locks/toggle', 'POST', {
      lock_date: targetDate,
      hotel_name: hotelName,
      is_locked: !currentlyLocked
    });
    toast(!currentlyLocked ? `🔒 تم قفل واعتماد حسابات يوم (${targetDate}) بنجاح!` : `🔓 تم فك قفل حسابات يوم (${targetDate})!`);
    await refreshDayLockStatus();
  } catch (e) {
    toast(e.message, 'bad');
  }
}
window.toggleCurrentDayLock = toggleCurrentDayLock;

function openRequestDayUnlockModal(lockDate = '', hotelName = '', roomNumber = '', proposedPayload = null) {
  const dVal = lockDate || $('dsEntryDate')?.value || $('dsEnd')?.value || todayISO();
  const hotelSel = $('dsHotel');
  const hVal = hotelName || ((hotelSel && hotelSel.value && hotelSel.selectedOptions?.[0]) ? hotelSel.selectedOptions[0].textContent.trim() : 'جميع الفنادق');
  const rVal = roomNumber || $('saleRoomNumber')?.value || '';

  showModal(`
    <div class="modal-title">
      <div>
        <h2>📩 إرسال طلب إذن تعديل للمحاسب (يوم مقفول 🔒)</h2>
        <p>حسابات هذا اليوم معتمدة ومقفولة — اكتب سبب التعديل وسيصل إشعار فوري للمحاسب للقبول أو الرفض</p>
      </div>
      <button type="button" class="btn" onclick="closeModal()">إغلاق</button>
    </div>
    <form id="reqDayUnlockForm" style="display:flex;flex-direction:column;gap:12px;">
      <div class="form-grid three">
        <div class="field"><label>تاريخ اليوم المطلوب تعديله</label><input class="input" type="date" id="rduDate" value="${esc(dVal)}" required></div>
        <div class="field"><label>الفندق</label><input class="input" type="text" id="rduHotel" value="${esc(hVal)}" required></div>
        <div class="field"><label>رقم الغرفة / الأوردر</label><input class="input" type="text" id="rduRoom" value="${esc(rVal)}" placeholder="مثال: 412"></div>
      </div>
      <div class="field">
        <label>سبب التعديل المطلوب (يظهر للمحاسب) *</label>
        <input class="input" id="rduReason" placeholder="مثال: العميل أضاف طباعة ألبوم إضافي 30$ بعد تقفيل اليوم..." required>
      </div>
      <div class="modal-actions">
        <button type="submit" class="btn green">📨 إرسال الإشعار والطلب للمحاسب الآن</button>
        <button type="button" class="btn" onclick="closeModal()">إلغاء</button>
      </div>
    </form>
  `, 'modal-lg');

  $('reqDayUnlockForm')?.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    try {
      await apiJSON('/api/day-locks/request-edit', 'POST', {
        lock_date: $('rduDate').value,
        hotel_name: $('rduHotel').value.trim(),
        room_number: $('rduRoom').value.trim(),
        reason: $('rduReason').value.trim(),
        proposed: proposedPayload || null
      });
      closeModal();
      toast('📩 تم إرسال طلب التعديل وإشعار المحاسب بنجاح! في انتظار موافقة المحاسب.');
      await refreshDayLockStatus();
    } catch (e) {
      toast(e.message, 'bad');
    }
  });
}
window.openRequestDayUnlockModal = openRequestDayUnlockModal;

async function openDayLockRequestsModal() {
  await refreshDayLockStatus();
  const reqs = CURRENT_DAY_LOCK_STATE?.requests || [];
  const rowsHtml = reqs.length ? reqs.map((r, i) => {
    const st = String(r.status || 'Pending');
    const badge = st === 'Approved'
      ? '<span class="badge green">✅ مقبول ومفتوح للتعديل</span>'
      : (st === 'Rejected' ? '<span class="badge red">❌ مرفوض</span>' : '<span class="badge amber">⏳ بانتظار قرار المحاسب</span>');
    const actions = st === 'Pending' ? `
      <div class="context-actions">
        <button type="button" class="mini-btn green" onclick="decideDayLockRequest(${r.id}, 'approve')">✅ قبول وفتح التعديل</button>
        <button type="button" class="mini-btn red" onclick="decideDayLockRequest(${r.id}, 'reject')">❌ رفض</button>
      </div>
    ` : `<small>${esc(r.reviewed_by || '-')}</small>`;
    return `<tr>
      <td>${i + 1}</td>
      <td><b>${esc(String(r.lock_date || '').slice(0, 10))}</b></td>
      <td>${esc(r.hotel_name)}</td>
      <td><b>${esc(r.room_number || '-')}</b></td>
      <td>${esc(r.requested_by)}</td>
      <td>${esc(r.reason)}</td>
      <td>${badge}</td>
      <td>${actions}</td>
    </tr>`;
  }).join('') : `<tr><td colspan="8" class="empty-state">لا توجد طلبات تعديل مرسلة من المديرين حالياً</td></tr>`;

  showModal(`
    <div class="modal-title" style="flex-direction:row !important;justify-content:space-between !important;align-items:center !important;">
      <div>
        <h2>📬 طلبات المديرين لتعديل أيام مقفولة (صلاحية المحاسب والأونر)</h2>
        <p>عند الضغط على (✅ قبول وفتح التعديل) يتم فتح اليوم للمدير وإرسال إشعار فوري له بالموافقة</p>
      </div>
      <button type="button" class="btn" onclick="closeModal()">إغلاق</button>
    </div>
    <div class="table-wrap">
      <table class="modern-table">
        <thead>
          <tr><th>#</th><th>تاريخ اليوم</th><th>الفندق</th><th>الغرفة</th><th>مقدم الطلب</th><th>سبب التعديل</th><th>الحالة</th><th>قرار المحاسب</th></tr>
        </thead>
        <tbody>${rowsHtml}</tbody>
      </table>
    </div>
  `, 'modal-xl');
}
window.openDayLockRequestsModal = openDayLockRequestsModal;

async function decideDayLockRequest(reqId, decision) {
  try {
    await apiJSON(`/api/day-locks/requests/${reqId}/decide`, 'POST', { decision });
    toast(decision === 'approve' ? '✅ تمت الموافقة وفتح التعديل للمدير وإشعاره فوراً!' : '❌ تم رفض طلب التعديل وإشعار المدير!');
    await openDayLockRequestsModal();
  } catch (e) {
    toast(e.message, 'bad');
  }
}
window.decideDayLockRequest = decideDayLockRequest;

setTimeout(refreshDayLockStatus, 350);
$('dsEntryDate')?.addEventListener('change', refreshDayLockStatus);
$('dsHotel')?.addEventListener('change', refreshDayLockStatus);
