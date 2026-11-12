// ============================================================================
// 📌 ملف الكود البرمجي (reservations.js): كود شاشة الحجوزات (إضافة وتعديل حجز، حساب العربون والمتبقي، تغيير الميعاد، وتجهيز الفساتين)
// ============================================================================

// =========================
// STATE
// =========================

let bookings = [];
let selectedBookingId = null;
let hotels = [];

let team = {
    sales: [],
    photographers: []
};

let assetData = {
    dresses: []
};

let clothingItems = [];
const nationalities = [
    'مصري',
    'روسي',
    'إنجليزي',
    'ألماني',
    'إيطالي',
    'فرنسي',
    'بولندي',
    'روماني',
    'تشيكي',
    'أوكراني',
    'عربي (أخرى)',
    'أجنبي (أخرى)'
];


// =========================
// async function initReservations
// =========================

async function initReservations(){[hotels,team,assetData]=await Promise.all([apiSafe('/api/hotels',[],'تحميل الفنادق'),apiSafe('/api/team/options',{sales:[],photographers:[],all:[]},'تحميل الفريق'),apiSafe('/api/assets',{dresses:[],equipment:[]},'')]);const mySalesHotel=(window.SALES_ONLY?(window.USER_HOTEL_NAME||window.CURRENT_USER?.hotel_name||(hotels.length===1?hotels[0].hotel_name:'')):'');$('rHotel').innerHTML=(hotels.length>1?'<option value="">الكل</option>':'')+hotels.map(h=>`<option value="${esc(h.hotel_name)}">${esc(h.hotel_name)}</option>`).join('');['rMonth','rDay','rHotel','rGroup'].forEach(id=>$(id).addEventListener('change',loadBookings));$('rSearch').addEventListener('input',debounce(loadBookings,220));document.addEventListener('keydown',e=>{if(e.ctrlKey&&e.key.toLowerCase()==='f'){e.preventDefault();$('rSearch').focus();$('rSearch').select()}});await loadBookings();const openId=new URLSearchParams(location.search).get('open');if(openId){try{await viewDetails(Number(openId))}catch(e){toast('تعذر فتح الحجز المرتبط: '+e.message,'bad')}}}


// =========================
// function debounce
// =========================

function debounce(fn,ms){let t;return(...a)=>{clearTimeout(t);t=setTimeout(()=>fn(...a),ms)}}


// =========================
// async function loadBookings
// =========================

async function loadBookings(){const p=new URLSearchParams();if($('rSearch').value)p.set('q',$('rSearch').value);if($('rHotel').value)p.set('hotel',$('rHotel').value);if($('rGroup').value)p.set('group',$('rGroup').value);if($('rMonth').value){p.set('month',`${new Date().getFullYear()}-${$('rMonth').value}`);if($('rDay').value)p.set('date',`${new Date().getFullYear()}-${$('rMonth').value}-${$('rDay').value}`)}try{bookings=await api('/api/bookings?'+p);renderBookings()}catch(e){bookings=[];renderBookings();$('rBody').innerHTML=`<tr><td colspan="19" class="empty-state text-red">${esc(e.message)}</td></tr>`;toast(e.message,'bad')}}


// =========================
// function dressSummary
// =========================

function dressSummary(b){return `فستان: ${b.dress_count||0} | جلابية: ${b.galabeya_count||0}`}

// =========================
// STATUS BADGE
// =========================

function statusBadge(status){

    if(!status){

        return `
        <span class="status-badge">
            -
        </span>
        `;

    }


    const s = String(status).toLowerCase();



    // Pending

    if(
        s.includes("انتظار") ||
        s.includes("pending")
    ){

        return `
        <span class="status-badge pending">
            ⏳ انتظار
        </span>
        `;

    }



    // Confirmed

    if(
        s.includes("مؤكد") ||
        s.includes("confirmed")
    ){

        return `
        <span class="status-badge confirmed">
            ✓ مؤكد
        </span>
        `;

    }



    // Cancelled

    if(
        s.includes("كنسل") ||
        s.includes("cancel") ||
        s.includes("ملغ")
    ){

        return `
        <span class="status-badge cancelled">
            ✕ ملغي
        </span>
        `;

    }



    // Delivered

    if(
        s.includes("deliver")
    ){

        return `
        <span class="status-badge delivered">
            ⚡ تم التسليم
        </span>
        `;

    }



    return `
    <span class="status-badge">
        ${esc(status)}
    </span>
    `;

}
// =========================
// PHOTOGRAPHER BADGE
// =========================

function photographerBadge(name){
    const n=String(name||'').trim();
    if(n){
        return `<span class="photographer-capsule assigned" title="${esc(n)}"><span class="pulse-dot green"></span>${esc(n)}</span>`;
    }
    return `<span class="photographer-capsule unassigned"><span class="pulse-dot red"></span>بدون مصور</span>`;
}
// =========================
// function renderBookings
// =========================

function renderBookings(){let p=0,c=0,x=0;bookings.forEach(b=>{const s=String(b.status||'').toLowerCase();if(s.includes('كنسل')||s.includes('cancel')||s.includes('ملغ'))x++;else if(s.includes('مؤكد')||s.includes('deliver'))c++;else p++});$('rTotal').textContent=bookings.length;$('rPending').textContent=p;$('rConfirmed').textContent=c;$('rCancelled').textContent=x;const photos=(team.photographers||[]).length||9;const active=bookings.filter(b=>!String(b.status||'').toLowerCase().match(/كنسل|cancel|deliver/)).length;$('rPhotogAvail').textContent=`${Math.max(0,photos-active)} من ${photos}`;const dressQty=(assetData.dresses||[]).reduce((a,x)=>a+num(x.quantity),0);$('rDressAvail').textContent=Math.max(0,dressQty-active);$('rBody').innerHTML=bookings.map((b,i)=>`<tr class="select-row ${selectedBookingId===b.id?'selected':''}" data-booking-id="${b.id}" onclick="selectBooking(${b.id},this)"><td>${i+1}</td><td>${statusBadge(b.status)}</td><td>${esc(b.hotel)}</td><td>${esc(b.booking_date)}</td><td><b>${esc(b.room_number)}</b></td><td>${esc(b.phone_number||'')}</td><td>${esc(b.booking_time||'')}</td><td>${esc(b.nationality||'')}</td><td title="${esc(b.session_details||'')}">${esc(String(b.session_details||'').slice(0,25))}</td><td>${esc(dressSummary(b))}</td><td>${money(b.deposit_usd)}</td><td>${money(b.deposit_eur)}</td><td>${money(b.deposit_le_cash)}</td><td>${money(b.deposit_le_visa)}</td><td>${money(b.total_agreement)}</td><td>${money(b.remaining)}</td><td>${esc(b.sales_person||'')}</td><td>${photographerBadge(b.photographer)}</td><td><div class="context-actions">${window.PHOTOGRAPHER_ONLY?`<button class="mini-btn blue" title="التفاصيل" onclick="event.stopPropagation();viewDetails(${b.id})">◉ التفاصيل</button>`:`${window.SALES_ONLY?'':`<button class="mini-btn green" title="Checkout وتسليم" onclick="event.stopPropagation();openCheckout(${b.id})">⚡</button>`}<button class="mini-btn purple" title="طباعة إيصال حجز حراري POS" onclick="event.stopPropagation();printBookingPosById(${b.id})">🖨️</button><button class="mini-btn blue" title="التفاصيل" onclick="event.stopPropagation();viewDetails(${b.id})">◉</button><button class="mini-btn amber" title="تعديل" onclick="event.stopPropagation();editBooking(${b.id})">✎</button><button class="mini-btn purple" title="كل الإجراءات" onclick="event.stopPropagation();openRowMenu(event,${b.id})">⋮</button>`}</div></td></tr>`).join('')||'<tr><td colspan="19" class="empty-state">لا توجد حجوزات</td></tr>'}


// =========================
// function selectBooking
// =========================

function selectBooking(id,row){selectedBookingId=id;$$('#rBody tr').forEach(x=>x.classList.remove('selected'));row?.classList.add('selected')}


// =========================
// function selected
// =========================

function selected(){return bookings.find(x=>x.id===selectedBookingId)}

// =========================
// function needSelected
// =========================

function needSelected(){const b=selected();if(!b)toast('يرجى تحديد حجز أولاً','bad');return b}


// =========================
// function openRowMenu
// =========================

function openRowMenu(ev,id){selectedBookingId=id;const b=bookings.find(x=>x.id===id);showModal(`<div class="modal-title"><h2>إجراءات الحجز #${id}</h2><p>غرفة ${esc(b?.room_number)}</p></div><div class="action-grid"><button class="btn primary" onclick="closeModal();openCheckout(${id})">➕ Checkout وتسليم الأوردر</button><button class="btn green" onclick="sendWhatsapp(${id})">💬 إرسال تذكير واتساب</button><button class="btn purple" onclick="showVoucher(${id})">🎫 كارت الموعد</button><button class="btn" onclick="duplicateBooking(${id})">📄 استنساخ الحجز</button><button class="btn" onclick="viewDetails(${id})">📋 التفاصيل</button><button class="btn amber" onclick="closeModal();editBooking(${id})">✏️ تعديل</button><button class="btn red" onclick="deleteBooking(${id})">🗑️ حذف</button></div>`,'modal-lg')}
function bookingOptions(){return hotels.map(h=>`<option>${esc(h.hotel_name)}</option>`).join('')}function salesOptions(){return (team.sales||[]).map(x=>`<option>${esc(x.nickname)}</option>`).join('')}function photographerOptions(){return (team.photographers||[]).map(x=>`<option>${esc(x.nickname)}</option>`).join('')}
function clothingBuilderHTML(){const types=[...new Set((assetData.dresses||[]).map(x=>x.dress_type).filter(Boolean))];const colors=[...new Set((assetData.dresses||[]).map(x=>x.color).filter(Boolean))];const sizes=[...new Set((assetData.dresses||[]).map(x=>x.size_category).filter(Boolean))];const tOpts=(types.length?types:['فستان','جلابية']);if(!tOpts.includes('فستان'))tOpts.unshift('فستان');if(!tOpts.includes('جلابية'))tOpts.push('جلابية');const cOpts=(colors.length?colors:['أزرق ملكي','أبيض','أحمر','ذهبي','أسود','وردي','غير محدد']);const sOpts=(sizes.length?sizes:['S','M','L','XL','ستاندرد']);return `<div class="pt-bk-dresses-strip" id="clothingVisualStrip"><button type="button" class="pt-bk-add-dress-card" onclick="addClothing()"><span style="font-size:20px;line-height:1;">+</span><span>إضافة قطعة</span></button><div id="clothingList" style="display:flex;gap:8px;align-items:stretch;"></div></div><div class="clothing-builder" style="margin-top:6px;"><div class="field"><label>النوع</label><select class="input" id="clType">${tOpts.map(x=>`<option>${esc(x)}</option>`).join('')}</select></div><div class="field"><label>اللون</label><select class="input" id="clColor">${cOpts.map(x=>`<option>${esc(x)}</option>`).join('')}</select></div><div class="field"><label>الحجم</label><select class="input" id="clSize">${sOpts.map(x=>`<option>${esc(x)}</option>`).join('')}</select></div><div class="field"><label>العدد</label><input class="input" id="clQty" type="number" min="1" value="1"></div><button type="button" class="btn primary" onclick="addClothing()">➕ إضافة</button></div>`}
function bookingFormHTML(b={},duplicate=false){
  clothingItems=Array.isArray(b.clothing_items)?structuredClone(b.clothing_items):[];
  const hotelField=`<select class="input" id="bfHotel">${bookingOptions()}</select>`;
  const salesField=`<select class="input" id="bfSales">${salesOptions()}</select>`;
  return `
  <form id="bookingForm" class="pt-bk-sheet" style="display:flex !important;">
    <input type="hidden" id="bfId" value="${duplicate?'':(b.id||'')}">
    <div class="pt-bk-header">
      <button type="button" class="pt-bk-header-btn" onclick="closeModal()" title="إغلاق">➔</button>
      <h2>${b.id&&!duplicate?'✏️ تعديل الحجز #'+b.id:'➕ حجز أوردر جديد'}</h2>
      <button type="submit" class="pt-bk-header-btn" onclick="window._PRINT_AFTER_SAVE=false" title="حفظ سريع">✓</button>
    </div>

    <div>
      <div class="pt-bk-sec-title"><span>📋 تفاصيل الحجز</span><small style="color:var(--text-muted);font-weight:700;">أدخل بيانات الغرفة والموعد</small></div>
      <div class="pt-bk-grid-2">
        <div class="pt-bk-field"><label>رقم الغرفة *</label><div class="pt-bk-input-row"><span class="pt-bk-icon">🚪</span><input class="input" id="bfRoom" required value="${esc(b.room_number||'')}" placeholder="مثال: 412"></div></div>
        <div class="pt-bk-field"><label>رقم الهاتف (اختياري)</label><div class="pt-bk-input-row"><input class="input" id="bfPhone" value="${esc(b.phone_number||'')}" dir="ltr" placeholder="+20 10..."><span class="pt-bk-icon">📞</span></div></div>
        <div class="pt-bk-field"><label>التاريخ</label><div class="pt-bk-input-row"><input class="input" type="date" id="bfDate" value="${esc(duplicate?todayISO():(b.booking_date||todayISO()))}"><span class="pt-bk-icon">📅</span></div></div>
        <div class="pt-bk-field"><label>موعد التصوير</label><div class="pt-bk-input-row"><input class="input" type="time" id="bfTime" value="${esc(String(b.booking_time||'16:00').slice(0,5))}"><span class="pt-bk-icon">🕒</span></div></div>
        <div class="pt-bk-field"><label>الجنسية</label><div class="pt-bk-input-row"><span class="pt-bk-icon">🏳️</span><select class="input" id="bfNat">${nationalities.map(n=>`<option>${n}</option>`).join('')}</select></div></div>
        <div class="pt-bk-field"><label>تفاصيل السيشن</label><div class="pt-bk-input-row"><span class="pt-bk-icon">📝</span><input class="input" id="bfSession" value="${esc(b.session_details||'')}" placeholder="تفاصيل السيشن وملاحظات..."></div></div>
        <div class="pt-bk-field"><label>الفندق ${window.SALES_ONLY?'🔒':''}</label><div class="pt-bk-input-row"><span class="pt-bk-icon">🏨</span>${hotelField}</div></div>
        <div class="pt-bk-field"><label>السيلز (مسؤول الحجز) ${window.SALES_ONLY?'🔒':''}</label><div class="pt-bk-input-row"><span class="pt-bk-icon">💼</span>${salesField}</div></div>
        <div class="pt-bk-field"><label>المصور</label><div class="pt-bk-input-row"><span class="pt-bk-icon">📸</span><select class="input" id="bfPhotog"><option value="">بدون مصور</option>${photographerOptions()}</select></div></div>
        <div class="pt-bk-field"><label>حالة الحجز</label><div class="pt-bk-input-row"><span class="pt-bk-icon">🏷️</span><select class="input" id="bfStatus"><option>انتظار</option><option>مؤكد</option><option>كنسل</option><option>تقديم ميعاد</option><option>تأخير ميعاد</option></select></div></div>
      </div>
      <div class="pt-bk-field" id="reschedBox" hidden style="margin-top:8px;"><label>تاريخ النقل الجديد</label><input class="input" type="date" id="bfReschedule" value="${todayISO()}"></div>
    </div>

    <div>
      <div class="pt-bk-sec-title"><span>👗 إضافة الفساتين والملابس</span><span style="font-size:15px;">🧥</span></div>
      ${clothingBuilderHTML()}
    </div>

    <div>
      <div class="pt-bk-sec-title"><span>💳 المدفوعات والعربون</span><span style="font-size:12px;color:var(--text-muted);">دولار • يورو • فيزا • كاش</span></div>
      <div class="pt-bk-grid-2">
        <div class="pt-bk-field"><label>عربون دولار ($)</label><div class="pt-bk-input-row"><strong style="font-size:16px;color:#0d6e5b;">$</strong><input class="input calc" type="number" step=".01" id="bfUsd" value="${num(duplicate?0:b.deposit_usd)}"></div></div>
        <div class="pt-bk-field"><label>عربون يورو (€)</label><div class="pt-bk-input-row"><strong style="font-size:16px;color:#0d6e5b;">€</strong><input class="input calc" type="number" step=".01" id="bfEur" value="${num(duplicate?0:b.deposit_eur)}"></div></div>
      </div>
      <div class="pt-bk-pay-split">
        <div class="pt-bk-rem-box">
          <div class="pt-bk-field" style="width:100%;margin-bottom:4px;">
            <label>إجمالي الاتفاق ($)</label>
            <input class="input calc" type="number" step=".01" id="bfTotal" value="${num(b.total_agreement)}" style="text-align:center;font-size:16px !important;font-weight:900 !important;">
          </div>
          <small style="color:var(--text-muted);font-weight:800;">المتبقي المطلوب</small>
          <strong id="bfRemBoxEgp" style="font-size:16px;font-weight:900;color:#0d6e5b;">0.00 $</strong>
        </div>
        <div style="display:flex;flex-direction:column;gap:8px;justify-content:center;">
          <div class="pt-bk-field"><label>مكنة فيزا (LE)</label><div class="pt-bk-input-row"><span class="pt-bk-icon">💳</span><input class="input calc" type="number" step=".01" id="bfVisa" value="${num(duplicate?0:b.deposit_le_visa)}"></div></div>
          <div class="pt-bk-field"><label>كاش مصري (LE)</label><div class="pt-bk-input-row"><span class="pt-bk-icon">💵</span><input class="input calc" type="number" step=".01" id="bfCash" value="${num(duplicate?0:b.deposit_le_cash)}"></div></div>
        </div>
      </div>
      <div class="pt-bk-rate-bar">
        <span>💱 سعر الصرف (الريت):</span>
        <div style="display:flex;align-items:center;gap:6px;">
          <span>1$ =</span>
          <input class="input calc" type="number" step=".01" id="bfRate" value="50" style="width:72px;height:28px !important;text-align:center;font-weight:900;">
          <span>LE</span>
        </div>
      </div>
    </div>

    <div class="pt-bk-summary-card">
      <div style="font-weight:900;font-size:13px;color:var(--text-heading);margin-bottom:2px;">📊 ملخص الحجز (Summary)</div>
      <div class="pt-bk-sum-row"><span>إجمالي الاتفاق</span><strong id="bfTotalView">0.00 $</strong></div>
      <div class="pt-bk-sum-row"><span>إجمالي المدفوع المعادل</span><strong id="bfPaidView" style="color:#059669;">0.00 $</strong></div>
      <div id="bfPaidBreakdown" style="font-size:11px;color:var(--text-muted);text-align:left;" dir="ltr"></div>
      <div class="pt-bk-sum-row total-rem"><span style="color:#0d6e5b;">المتبقي على العميل</span><strong id="bfRemView" class="text-red">0.00 $</strong></div>
    </div>

    <div style="display:flex;flex-direction:column;gap:8px;margin-top:2px;">
      <button type="submit" class="pt-bk-primary-cta" onclick="window._PRINT_AFTER_SAVE=false">✓ 💾 حفظ الحجز فقط</button>
      <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;">
        <button type="button" class="btn" onclick="closeModal()">إلغاء</button>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          <button type="button" class="btn purple" onclick="previewBookingReceiptFromForm()">🖨️ معاينة وطباعة إيصال الحجز (POS)</button>
          <button type="submit" class="btn primary" onclick="window._PRINT_AFTER_SAVE=true">💾🖨️ حفظ وطباعة إيصال للزبون</button>
        </div>
      </div>
    </div>
  </form>`;
}
async function openBookingForm(){if(window.PHOTOGRAPHER_ONLY)return toast('حساب المصور مخصص لعرض الأوردرات فقط ولا يمكنه إضافة حجز أو عربون','bad');const host=showModal(bookingFormHTML({}),'modal-xxl');bindBookingForm({})}
async function editBooking(id){if(window.PHOTOGRAPHER_ONLY)return toast('حساب المصور للعرض فقط','bad');const b=await api('/api/bookings/'+id);const host=showModal(bookingFormHTML(b,false),'modal-xxl');bindBookingForm(b)}function editSelected(){const b=needSelected();if(b)editBooking(b.id)}
async function duplicateBooking(id){const b=await api('/api/bookings/'+id);showModal(bookingFormHTML(b,true),'modal-xxl');bindBookingForm(b,true)}
function bindBookingForm(b,duplicate=false){const mySalesName=window.CURRENT_USER?.nickname||window.CURRENT_USER?.username||'';const myHotelName=window.USER_HOTEL_NAME||window.CURRENT_USER?.hotel_name||'';$('bfHotel').value=b.hotel||myHotelName||hotels[0]?.hotel_name||'';$('bfNat').value=b.nationality||'مصري';$('bfStatus').value=duplicate?'انتظار':(b.status||'انتظار');$('bfSales').value=b.sales_person||mySalesName||team.sales?.[0]?.nickname||'';$('bfPhotog').value=duplicate?'':(b.photographer||'');renderClothing();const toggle=()=>{$('reschedBox').hidden=!['تقديم ميعاد','تأخير ميعاد'].includes($('bfStatus').value)};$('bfStatus').addEventListener('change',toggle);toggle();$$('.calc').forEach(x=>x.addEventListener('input',calcBooking));calcBooking();$('bookingForm').addEventListener('submit',saveBooking)}
function addClothing(){clothingItems.push({type:$('clType').value,color:$('clColor').value,size:$('clSize').value,qty:String(Math.max(1,num($('clQty').value)))});renderClothing()}function removeClothing(i){clothingItems.splice(i,1);renderClothing()}function renderClothing(){if(!$('clothingList'))return;$('clothingList').innerHTML=clothingItems.map((x,i)=>`<div class="pt-bk-dress-card"><button type="button" class="pt-bk-dc-remove" onclick="removeClothing(${i})" title="حذف">×</button><div style="font-size:18px;text-align:center;">${String(x.type||'').includes('جلاب')?'👘':'👗'}</div><div style="font-size:11.5px;font-weight:900;text-align:center;">${esc(x.type)} • ${esc(x.color)}</div><div style="font-size:10.5px;color:var(--text-muted);text-align:center;">${esc(x.size)} × <b>${esc(x.qty)}</b></div></div>`).join('')||'<div style="display:flex;align-items:center;padding:0 12px;color:var(--text-muted);font-size:12px;font-weight:700;">لا توجد قطع مضافة بعد</div>'}
function calcBooking(){const total=num($('bfTotal').value),usd=num($('bfUsd').value),eur=num($('bfEur').value),cash=num($('bfCash').value),visa=num($('bfVisa').value),rate=num($('bfRate').value)||50;const paid=usd+eur+((cash+visa)/rate),rem=total-paid;$('bfTotalView').textContent=money(total)+' $';$('bfPaidView').textContent=money(paid)+' $';$('bfRemView').textContent=money(rem)+' $';$('bfRemView').className=rem<=0?'text-green':'text-red';if($('bfRemBoxEgp')){$('bfRemBoxEgp').textContent=`${money(rem)} $ (${money(rem*rate,0)} LE)`;$('bfRemBoxEgp').style.color=rem<=0?'#059669':'#dc2626';}if($('bfPaidBreakdown')){const p=[];if(usd>0)p.push('USD: $'+money(usd));if(eur>0)p.push('EUR: €'+money(eur));if(cash+visa>0)p.push('EGP: '+money(cash+visa,0));$('bfPaidBreakdown').textContent=p.join(' • ');}}
async function saveBooking(e){e.preventDefault();const id=$('bfId').value;const rate=num($('bfRate').value)||50;const total=num($('bfTotal').value),paid=num($('bfUsd').value)+num($('bfEur').value)+(num($('bfCash').value)+num($('bfVisa').value))/rate;const body={hotel:$('bfHotel').value,booking_date:$('bfDate').value,nationality:$('bfNat').value,room_number:$('bfRoom').value.trim(),phone_number:$('bfPhone').value.trim(),booking_time:$('bfTime').value,session_details:$('bfSession').value,clothing:clothingItems,deposit_usd:num($('bfUsd').value),deposit_eur:num($('bfEur').value),deposit_le_cash:num($('bfCash').value),deposit_le_visa:num($('bfVisa').value),total_agreement:total,remaining:total-paid,sales_person:$('bfSales').value,photographer:$('bfPhotog').value,status:$('bfStatus').value,rate,refund_deposit:false};if(['تقديم ميعاد','تأخير ميعاد'].includes(body.status))body.reschedule_date=$('bfReschedule').value;if(body.status==='كنسل'&&confirmAction('هل يوجد مرتجع عربون؟'))body.refund_deposit=true;try{const saved=await apiJSON(id?'/api/bookings/'+id:'/api/bookings',id?'PUT':'POST',body);toast(saved?.deposit_pending?'✅ تم حفظ الحجز وإرسال إشعار للمدير — العربون معلق في إشعارات المدير لحين استلام الفلوس وتأكيده لترحيله للدخل':'✅ تم حفظ الحجز وإرسال إشعار للمدير بنجاح','good');const shouldPrint=window._PRINT_AFTER_SAVE;window._PRINT_AFTER_SAVE=false;closeModal();await loadBookings();if(shouldPrint){openThermalBookingReceiptModal(Object.assign({id:saved?.id||id,clothing_items:clothingItems},body));}}catch(err){if(String(err.message).includes('مسجلة بالفعل')&&confirmAction('الغرفة مسجلة بالفعل في نفس التاريخ. هل تريد حفظ الحجز المزدوج؟')){body.allow_duplicate=true;await apiJSON('/api/bookings','POST',body);closeModal();loadBookings()}else toast(err.message,'bad')}}
async function deleteBooking(id){if(!confirmAction('هل أنت متأكد من حذف هذا الحجز نهائياً؟'))return;try{await api('/api/bookings/'+id,{method:'DELETE'});toast('تم حذف الحجز');closeModal();selectedBookingId=null;loadBookings()}catch(e){toast(e.message,'bad')}}function deleteSelected(){const b=needSelected();if(b)deleteBooking(b.id)}
async function viewDetails(id) {
    const b = await api('/api/bookings/' + id);
    const items = b.clothing_items || [];
    
    showModal(`
        <div class="modal-title details-modal-title">
            <h2>📄 تفاصيل الحجز الشاملة • أوردر #${b.id}</h2>
            <p>${esc(b.hotel)} • غرفة ${esc(b.room_number)}</p>
        </div>

        <div class="details-wrapper">
            <!-- القسم الأيمن: بيانات العميل -->
            <div class="form-section custom-section">
                <h3>👤 بيانات الحجز والعميل</h3>
                <div class="detail-list grid-auto">
                    <div class="detail-row highlight-blue"><small>رقم الغرفة</small><b>${esc(b.room_number)}</b></div>
                    <div class="detail-row"><small>الجنسية</small><b>${esc(b.nationality || '-')}</b></div>
                    <div class="detail-row"><small>تاريخ السيشن</small><b>${b.booking_date}</b></div>
                    <div class="detail-row"><small>وقت السيشن</small><b dir="ltr">${b.booking_time || '-'}</b></div>
                    <div class="detail-row"><small>مسؤول المبيعات</small><b>${esc(b.sales_person || '-')}</b></div>
                    <div class="detail-row"><small>المصورين</small><b>${esc(b.photographer || 'بدون مصور')}</b></div>
                    <div class="detail-row full-width"><small>رقم الهاتف</small><b dir="ltr">${esc(b.phone_number || '-')}</b></div>
                    <div class="detail-row full-width"><small>حالة الأوردر</small><b>${statusBadge(b.status)}</b></div>
                    <div class="detail-row full-width"><small>تفاصيل السيشن</small><b>${esc(b.session_details || 'لا توجد ملاحظات')}</b></div>
                </div>
            </div>

            <!-- القسم الأيسر: الحسابات المالية -->
            <div class="form-section custom-section">
                <h3>💰 الحسابات المالية</h3>
                <div class="detail-list grid-single">
                    <div class="detail-row"><small>إجمالي الاتفاق</small><b>${money(b.total_agreement)} $</b></div>
                    <div class="detail-row"><small>عربون دولار</small><b>${money(b.deposit_usd)} $</b></div>
                    <div class="detail-row"><small>عربون يورو</small><b>${money(b.deposit_eur)} €</b></div>
                    <div class="detail-row"><small>كاش مصري</small><b>${money(b.deposit_le_cash)} LE</b></div>
                    <div class="detail-row"><small>فيزا مصري</small><b>${money(b.deposit_le_visa)} LE</b></div>
                    <div class="detail-row ${b.remaining <= 0 ? 'highlight-green' : 'highlight-red'}"><small>المتبقي للتحصيل</small><b class="big-val">${money(b.remaining)} $</b></div>
                    <div class="detail-row"><small>اعتماد العربون</small><b>${b.pending_deposit ? (b.pending_deposit.status === 'Pending' ? '⏳ معلق' : '✅ معتمد') : 'لا يوجد'}</b></div>
                </div>
            </div>
        </div>

        <div class="form-section custom-section">
            <h3>👗 تجهيزات الملابس</h3>
            <div class="cloth-grid">
                ${items.map((x, i) => `
                    <div class="cloth-card">
                        <div class="cloth-title"><span class="cloth-index">#${i + 1}</span> ${esc(x.type)} -${esc(x.color)}</div>
                        <div class="cloth-details">المقاس: ${esc(x.size)} • <b>العدد: ${esc(x.qty)}</b></div>
                    </div>
                `).join('') || '<div class="empty-state cloth-empty">لا توجد ملابس مطلوبة لهذا الحجز</div>'}
            </div>
        </div>
    `, 'modal-xl');
}
function viewSelectedDetails(){const b=needSelected();if(b)viewDetails(b.id)}
async function openCheckout(id) {
    id = id || needSelected()?.id;
    if (!id) return;
    const b = await api('/api/bookings/' + id);
    const p = b.photographers || [];
    
    showModal(`
        <div class="modal-title details-modal-title">
            <h2>⚡ تسليم الأوردر (Checkout) وتحديث الحسابات</h2>
            <p>${esc(b.hotel)} • غرفة ${esc(b.room_number)} • تاريخ: ${esc(b.booking_date)}</p>
        </div>

        <!-- شريط الإجماليات العلوي -->
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 25px;">
            <div style="background: var(--bg-surface); padding: 15px; border-radius: 12px; border: 1px solid var(--border); text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.02);">
                <small style="color: var(--text-muted); font-weight: 800; display: block; margin-bottom: 5px;">إجمالي الاتفاق</small>
                <strong style="font-size: 22px; color: var(--text-main); font-weight: 900;">${money(b.total_agreement)} $</strong>
            </div>
            <div style="background: rgba(16, 185, 129, 0.05); padding: 15px; border-radius: 12px; border: 1px solid rgba(16, 185, 129, 0.2); text-align: center; transition: 0.3s;">
                <small style="color: var(--text-muted); font-weight: 800; display: block; margin-bottom: 5px;">إجمالي المدفوع</small>
                <strong id="coPaid" style="font-size: 22px; color: #10b981; font-weight: 900;">0 $</strong>
            </div>
            <div id="remBox" style="background: rgba(239, 68, 68, 0.05); padding: 15px; border-radius: 12px; border: 1px solid rgba(239, 68, 68, 0.2); text-align: center; transition: 0.3s;">
                <small style="color: var(--text-muted); font-weight: 800; display: block; margin-bottom: 5px;">المتبقي للتحصيل</small>
                <strong id="coRem" style="font-size: 22px; color: #ef4444; font-weight: 900;">0 $</strong>
            </div>
        </div>

        <form id="checkoutForm">
            <!-- قسم الأموال المقبوضة -->
            <div class="custom-section" style="margin-bottom: 25px; padding: 20px; background: var(--bg-surface); border: 1px solid var(--border); border-radius: 12px;">
                <h3 style="margin-top: 0 !important; border:none; padding:0; background:transparent;">💰 المبالغ المستلمة من النزيل</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 15px; margin-top: 15px;">
                    <div style="display: flex; flex-direction: column; gap: 6px;">
                        <label style="font-size: 12px; color: var(--text-muted); font-weight: bold;">دولار ($)</label>
                        <input class="input coCalc" id="coUsd" type="number" step=".01" value="${num(b.deposit_usd)}" style="height: 40px; font-weight: 900; color: #38bdf8;">
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 6px;">
                        <label style="font-size: 12px; color: var(--text-muted); font-weight: bold;">يورو (€)</label>
                        <input class="input coCalc" id="coEur" type="number" step=".01" value="${num(b.deposit_eur)}" style="height: 40px; font-weight: 900; color: #fbbf24;">
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 6px;">
                        <label style="font-size: 12px; color: var(--text-muted); font-weight: bold;">كاش مصري (LE)</label>
                        <input class="input coCalc" id="coCash" type="number" step=".01" value="${num(b.deposit_le_cash)}" style="height: 40px; font-weight: 900; color: #10b981;">
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 6px;">
                        <label style="font-size: 12px; color: var(--text-muted); font-weight: bold;">فيزا مصري (LE)</label>
                        <input class="input coCalc" id="coVisa" type="number" step=".01" value="${num(b.deposit_le_visa)}" style="height: 40px; font-weight: 900; color: #10b981;">
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 6px;">
                        <label style="font-size: 12px; color: var(--text-muted); font-weight: bold;">الريت</label>
                        <input class="input coCalc" id="coRate" type="number" step=".01" value="50" style="height: 40px;">
                    </div>
                </div>
            </div>

            <!-- قسم الحالة والمصورين (مقسوم نصفين) -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px;">
                <div class="custom-section" style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border); border-radius: 12px;">
                    <h3 style="margin-top: 0 !important; border:none; padding:0; background:transparent;">⚙️ تحديث الحالة</h3>
                    <div style="display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; margin-top: 15px;">
                        <label style="font-size: 12px; color: var(--text-muted); font-weight: bold;">حالة الأوردر بعد التسليم</label>
                        <select class="input" id="coStatus" style="height: 42px;">
                            <option>Delivered</option>
                            <option>مؤكد</option>
                            <option>انتظار</option>
                            <option>كنسل</option>
                            <option>تقديم ميعاد</option>
                            <option>تأخير ميعاد</option>
                        </select>
                    </div>
                    <div id="coReschedWrap" hidden style="display: flex; flex-direction: column; gap: 6px;">
                        <label style="font-size: 12px; color: var(--text-muted); font-weight: bold;">تاريخ النقل الجديد</label>
                        <input class="input" type="date" id="coResched" value="${todayISO()}" style="height: 42px;">
                    </div>
                </div>

                <div class="custom-section" style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border); border-radius: 12px;">
                    <h3 style="margin-top: 0 !important; border:none; padding:0; background:transparent;">📸 تعيين مصوري الأوردر</h3>
                    <div style="display: grid; gap: 12px; margin-top: 15px;">
                        ${[0, 1, 2].map((i) => `
                            <div style="display: flex; flex-direction: column; gap: 6px;">
                                <label style="font-size: 11px; color: var(--text-muted); font-weight: bold;">المصور ${i + 1}</label>
                                <select class="input" id="coP${i + 1}" style="height: 38px;">
                                    <option value="">لا يوجد</option>
                                    ${photographerOptions()}
                                </select>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>

            <!-- أزرار الحفظ -->
            <div class="modal-actions" style="margin-top: 25px; padding-top: 20px; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 12px;">
                <button type="button" class="btn" style="background: transparent; border: 1px solid var(--border); color: var(--text-main); font-weight: bold;" onclick="closeModal()">إلغاء</button>
                <button type="submit" class="btn green" style="background: #10b981; color: #fff; border: none; font-weight: 900; padding: 0 24px; font-size: 14px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);">⚡ تأكيد التسليم والحفظ</button>
            </div>
        </form>
    `, 'modal-xl');

    // تحديد المصورين السابقين في القائمة إن وُجدوا
    p.slice(0, 3).forEach((n, i) => {
        if ($('coP' + (i + 1)))$('coP' + (i + 1)).value = n;
    });

    // دالة تحديث الإجماليات بشكل حي أثناء الكتابة
    const calc = () => {
        const paid = num($('coUsd').value) + num($('coEur').value) + (num($('coCash').value) + num($('coVisa').value)) / (num($('coRate').value) || 50);
        const rem = num(b.total_agreement) - paid;
        
        $('coPaid').textContent = money(paid) + '$';
        $('coRem').textContent = money(rem) + '$';
        
        // تغيير ألوان مربع (المتبقي) حسب وجود مديونية أم لا
        $('coRem').style.color = rem <= 0 ? '#10b981' : '#ef4444';
        $('remBox').style.background = rem <= 0 ? 'rgba(16, 185, 129, 0.05)' : 'rgba(239, 68, 68, 0.05)';
        $('remBox').style.borderColor = rem <= 0 ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)';     };      $$('.coCalc').forEach(x => x.addEventListener('input', calc));
    calc();

    // إظهار/إخفاء مربع تغيير التاريخ عند التأجيل
    const sw = () => {
        $('coReschedWrap').hidden = !['تقديم ميعاد', 'تأخير ميعاد'].includes($('coStatus').value);
    };
    $('coStatus').addEventListener('change', sw);
    sw();

    // الإرسال لقاعدة البيانات
    $('checkoutForm').addEventListener('submit', async e => {
        e.preventDefault();
        const body = {
            status: $('coStatus').value,
            deposit_usd: num($('coUsd').value),
            deposit_eur: num($('coEur').value),
            deposit_le_cash: num($('coCash').value),
            deposit_le_visa: num($('coVisa').value),
            rate: num($('coRate').value) || 50,
            photographers: [$('coP1').value, $('coP2').value, $('coP3').value].filter(Boolean)
        };
        if (['تقديم ميعاد', 'تأخير ميعاد'].includes(body.status)) body.reschedule_date = $('coResched').value;
        if (body.status === 'كنسل' && confirmAction('يوجد عربون مدفوع، هل يوجد مرتجع عربون؟')) body.refund_deposit = true;
        try {
            await apiJSON('/api/bookings/' + id + '/checkout', 'POST', body);
            toast('تمت عملية Checkout بنجاح');
            closeModal();
            loadBookings();
        } catch (err) {
            toast(err.message, 'bad');
        }
    });
}
async function openTimeline(){const date=$('rMonth').value&&$('rDay').value?`${new Date().getFullYear()}-${$('rMonth').value}-${$('rDay').value}`:todayISO();const rows=await api('/api/bookings/timeline?date='+date);showModal(`<div class="modal-title"><h2>⏱️ جدول مواعيد جلسات التصوير اليومية</h2><p>${date}</p></div><div class="timeline-list">${rows.map(r=>`<div class="timeline-card"><b>⏰ ${esc(r.booking_time||'--')}</b><span><b>غرفة ${esc(r.room_number)}</b> • ${esc(r.hotel)} • مصور: ${esc(r.photographer||'غير معين')}<br><small>${esc(r.session_details||'')}</small></span>${statusBadge(r.status)}</div>`).join('')||'<div class="empty-state">لا توجد سيشنات</div>'}</div>`,'modal-xl')}
let LAST_PREP_ROWS = [];
let LAST_PREP_DATE = '';
async function openPrep(){
  const date=$('rMonth').value&&$('rDay').value?`${new Date().getFullYear()}-${$('rMonth').value}-${$('rDay').value}`:todayISO();
  const rows=await api('/api/bookings/prep?date='+date);
  LAST_PREP_ROWS = rows || [];
  LAST_PREP_DATE = date;
  showModal(`
    <div class="modal-title" style="flex-direction:row !important;justify-content:space-between !important;align-items:center !important;flex-wrap:wrap;gap:10px;">
      <div>
        <h2>👗 كشف الفساتين والملابس المطلوب تجهيزها</h2>
        <p>التاريخ: ${date}</p>
      </div>
      <div style="display:flex;gap:8px;">
        <button type="button" class="btn green" onclick="exportPrepDressesCSV()">📥 حفظ الفساتين Excel (CSV)</button>
        <button type="button" class="btn primary" onclick="printHTML('كشف تجهيز فساتين اليوم - '+LAST_PREP_DATE, document.getElementById('prepTableWrap').innerHTML)">🖨️ طباعة</button>
      </div>
    </div>
    <div id="prepTableWrap" class="table-wrap">
      <table>
        <thead><tr><th>#</th><th>النوع</th><th>اللون</th><th>المقاس</th><th>العدد</th></tr></thead>
        <tbody>${rows.map((r,i)=>`<tr><td>${i+1}</td><td>${esc(r.type)}</td><td>${esc(r.color)}</td><td>${esc(r.size)}</td><td><b>${r.qty}</b></td></tr>`).join('')||'<tr><td colspan="5">لا توجد ملابس مطلوبة</td></tr>'}</tbody>
      </table>
    </div>
  `,'modal-lg');
}

async function exportPrepDressesCSV() {
  const date = $('rMonth')?.value && $('rDay')?.value ? `${new Date().getFullYear()}-${$('rMonth').value}-${$('rDay').value}` : (LAST_PREP_DATE || todayISO());
  let rows = LAST_PREP_ROWS;
  if (!rows || !rows.length) {
    try { rows = await api('/api/bookings/prep?date=' + date); } catch(e) { rows = []; }
  }
  if (!rows || !rows.length) {
    // في حال عدم وجود حجوزات انتظار في هذا اليوم، نصدر الفساتين من الحجوزات المعروضة حالياً بالجدول
    const agg = {};
    (bookings || []).forEach(b => {
      const items = Array.isArray(b.clothing_items) ? b.clothing_items : [];
      items.forEach(it => {
        const k = `${it.type||'فستان'}|${it.color||'غير محدد'}|${it.size||'ستاندرد'}`;
        agg[k] = (agg[k] || 0) + Math.max(1, Number(it.qty || 1));
      });
    });
    rows = Object.entries(agg).map(([k, q]) => {
      const [type, color, size] = k.split('|');
      return { type, color, size, qty: q };
    });
  }
  downloadCSV(
    `Dresses_Prep_${date}.csv`,
    ['#', 'التاريخ', 'النوع', 'اللون', 'المقاس', 'العدد المطلوب'],
    (rows || []).map((r, i) => [i + 1, date, r.type || 'فستان', r.color || '-', r.size || '-', r.qty || 1])
  );
}
window.exportPrepDressesCSV = exportPrepDressesCSV;
window.openPrep = openPrep;
async function showVoucher(id){const b=await api('/api/bookings/'+id);printHTML(`PHOTOTEAM RESORT VOUCHER - غرفة ${b.room_number}`,`<div style="border:2px solid #1675dd;padding:20px"><h2>📸 PHOTOTEAM RESORT VOUCHER</h2><p>بطاقة تأكيد حجز موعد جلسة التصوير</p><table><tr><th>الفندق</th><td>${esc(b.hotel)}</td></tr><tr><th>الغرفة</th><td>${esc(b.room_number)}</td></tr><tr><th>تاريخ السيشن</th><td>${esc(b.booking_date)}</td></tr><tr><th>وقت السيشن</th><td>${esc(b.booking_time)}</td></tr><tr><th>مسؤول المبيعات</th><td>${esc(b.sales_person)}</td></tr><tr><th>المصور</th><td>${esc(b.photographer||'سيتم التحديد')}</td></tr></table><b>⚠️ يرجى الحضور قبل الموعد بـ 10 دقائق</b></div>`)}
function sendWhatsapp(id){const b=bookings.find(x=>x.id===id);if(!b?.phone_number)return toast('لا يوجد رقم هاتف مسجل','bad');let phone=String(b.phone_number).replace(/\D/g,'');if(phone.length===11&&phone.startsWith('01'))phone='2'+phone;const foreign=b.nationality&&!['مصري','عربي (أخرى)'].includes(b.nationality);const msg=foreign?`Hello from Phototeam! 📸 Friendly reminder of your photo session today at ${b.booking_time} (Room: ${b.room_number}, Hotel: ${b.hotel}). We look forward to seeing you!`:`أهلاً بك من فريق التصوير! 📸 نذكرك بموعد جلستك اليوم في تمام الساعة ${b.booking_time} (غرفة: ${b.room_number} - ${b.hotel}). نتمنى لك جلسة ممتعة!`;window.open(`https://wa.me/${phone}?text=${encodeURIComponent(msg)}`,'_blank')}
function exportDailyRunSheet(){
  const day = todayISO();
  const rows = (bookings && bookings.length) ? bookings : [];
  downloadCSV(
    `Reservations_${day}.csv`,
    ['#', 'رقم الحجز', 'الفندق', 'تاريخ السيشن', 'رقم الغرفة', 'الهاتف', 'الوقت', 'الجنسية', 'تفاصيل السيشن', 'الفساتين والملابس', 'عربون ($)', 'عربون (€)', 'عربون كاش (LE)', 'عربون فيزا (LE)', 'إجمالي الاتفاق ($)', 'المتبقي ($)', 'السيلز', 'المصور', 'الحالة'],
    rows.map((b, i) => [
      i + 1,
      b.id || '',
      b.hotel || '',
      b.booking_date || '',
      b.room_number || '',
      b.phone_number || '',
      b.booking_time || '',
      b.nationality || '',
      b.session_details || '',
      dressSummary(b),
      num(b.deposit_usd),
      num(b.deposit_eur),
      num(b.deposit_le_cash),
      num(b.deposit_le_visa),
      num(b.total_agreement),
      num(b.remaining),
      b.sales_person || '',
      b.photographer || 'بدون مصور',
      b.status || ''
    ])
  );
}
window.exportDailyRunSheet = exportDailyRunSheet;

// =========================
// V72: قائمة الكليك اليمين للحجوزات (نفس إجراءات زر ⋮)
// =========================
if(window.PTContextMenu){
    PTContextMenu.register('#rBody tr[data-booking-id]',function(row){
        const id=Number(row.dataset.bookingId);
        if(!id)return [];
        selectBooking(id,row);
        return [
            {icon:'⚡',label:'Checkout وتسليم الأوردر',action:()=>openCheckout(id)},
            {icon:'📋',label:'التفاصيل',action:()=>viewDetails(id)},
            {icon:'✏️',label:'تعديل',action:()=>editBooking(id)},
            {icon:'📄',label:'استنساخ الحجز',action:()=>duplicateBooking(id)},
            '-',
            {icon:'💬',label:'إرسال تذكير واتساب',action:()=>sendWhatsapp(id)},
            {icon:'🎫',label:'كارت الموعد',action:()=>showVoucher(id)},
            '-',
            {icon:'🗑️',label:'حذف',danger:true,action:()=>deleteBooking(id)}
        ];
    },{title:row=>{const b=bookings.find(x=>x.id===Number(row.dataset.bookingId));return b?`حجز #${b.id} • غرفة ${b.room_number||'-'}`:''}});
}

initReservations();


function collectCurrentBookingFormData() {
  const rate = num($('bfRate')?.value) || 50;
  const total = num($('bfTotal')?.value);
  const usd = num($('bfUsd')?.value);
  const eur = num($('bfEur')?.value);
  const cash = num($('bfCash')?.value);
  const visa = num($('bfVisa')?.value);
  const paid = usd + eur + ((cash + visa) / rate);
  return {
    id: $('bfId')?.value || '',
    hotel: $('bfHotel')?.value || '',
    booking_date: $('bfDate')?.value || todayISO(),
    nationality: $('bfNat')?.value || '',
    room_number: ($('bfRoom')?.value || '').trim() || '---',
    phone_number: ($('bfPhone')?.value || '').trim(),
    booking_time: $('bfTime')?.value || '',
    session_details: $('bfSession')?.value || '',
    clothing_items: clothingItems || [],
    deposit_usd: usd,
    deposit_eur: eur,
    deposit_le_cash: cash,
    deposit_le_visa: visa,
    total_agreement: total,
    paid_equiv: paid,
    remaining: Math.max(0, total - paid),
    sales_person: $('bfSales')?.value || '',
    photographer: $('bfPhotog')?.value || '',
    rate: rate
  };
}

function previewBookingReceiptFromForm() {
  const data = collectCurrentBookingFormData();
  const paperHtml = buildThermalBookingReceiptHTML(data);
  const w = window.THERMAL_PAPER_WIDTH || '80mm';
  triggerDirectInPagePrint(`<div style="width:${w};max-width:100%;margin:0 auto;background:#fff;color:#000;font-family:'Cairo','Tahoma',monospace;direction:rtl;">${paperHtml}</div>`, `${w} auto`);
}

async function printBookingPosById(id) {
  let b = bookings.find(x => Number(x.id) === Number(id));
  try {
    const full = await api('/api/bookings/' + id);
    if (full && full.id) b = full;
  } catch (e) {}
  if (!b) return toast('يرجى اختيار حجز أولاً', 'bad');
  openThermalBookingReceiptModal(b);
}

function printSelectedBookingPosReceipt() {
  const b = needSelected();
  if (b) printBookingPosById(b.id);
}

function printSelectedReceipt() {
  const b = needSelected();
  if (b) printBookingPosById(b.id);
}


window.previewBookingReceiptFromForm = previewBookingReceiptFromForm;
window.printBookingPosById = printBookingPosById;
window.printSelectedBookingPosReceipt = printSelectedBookingPosReceipt;
window.printSelectedReceipt = printSelectedReceipt;

function printBookingsReportPDF() {
    const rowsHtml = (bookings || []).map((b, i) => `
        <tr>
            <td>${i + 1}</td>
            <td>${esc(b.hotel || '-')}</td>
            <td>${esc(b.booking_date || '')}</td>
            <td><b>${esc(b.room_number || '')}</b></td>
            <td>${esc(b.booking_time || '')}</td>
            <td>${esc(b.nationality || '')}</td>
            <td>$${money(b.total_agreement || 0)}</td>
            <td>$${money(b.deposit_usd || 0)}</td>
            <td>$${money(b.remaining || 0)}</td>
            <td>${esc(b.sales_person || '')}</td>
            <td>${esc(b.photographer || 'بدون مصور')}</td>
            <td>${esc(b.status || '')}</td>
        </tr>
    `).join('') || '<tr><td colspan="12">لا توجد حجوزات</td></tr>';
    printHTML('كشف الحجوزات الشامل (PDF)', `
        <p>تاريخ الاستخراج: <b>${todayISO()}</b> • إجمالي الحجوزات: <b>${(bookings || []).length}</b></p>
        <table>
            <thead>
                <tr><th>#</th><th>الفندق</th><th>التاريخ</th><th>الغرفة</th><th>الوقت</th><th>الجنسية</th><th>الاتفاق ($)</th><th>العربون ($)</th><th>المتبقي ($)</th><th>السيلز</th><th>المصور</th><th>الحالة</th></tr>
            </thead>
            <tbody>${rowsHtml}</tbody>
        </table>
    `);
}
window.printBookingsReportPDF = printBookingsReportPDF;
