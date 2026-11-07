// ============================================================================
// 📌 ملف الكود البرمجي (control_room.js): كود شاشة متابعة السيشنات وتوزيع المصورين ومهام اليوم
// ============================================================================

let OPS_RAW = null;
let OPS_HOTELS = [];
let OPS_TEAM = [];
let ACTIVE_HOTEL = '';
let SEARCH_QUERY = '';
let AUTO_REFRESH_TIMER = null;

// حساب وتهيئة شارة العد التنازلي بالألوان
function getCountdownChip(mins, status) {
    if (mins === null || mins === undefined) return '<span class="mini-chip muted">--</span>';
    const m = Number(mins);
    const st = String(status || '').toLowerCase();
    const isDone = st.includes('deliver') || st.includes('تسليم') || st.includes('كنسل');

    if (isDone) {
        return '<span class="mini-chip gray">منتهي</span>';
    }
    if (m < 0) {
        return `<span class="mini-chip danger-pulse" title="متأخر عن موعده">⏰ متأخر ${Math.abs(m)} د</span>`;
    }
    if (m <= 25) {
        return `<span class="mini-chip warning" title="اقترب الموعد">⏳ بعد ${m} د</span>`;
    }
    const hours = Math.floor(m / 60);
    const rem = m % 60;
    return `<span class="mini-chip info">بعد ${hours > 0 ? hours + 'س ' : ''}${rem}د</span>`;
}

// فحص ملابس الحجز لعرض شارة التجهيز
function getClothingTag(clothing) {
    if (!clothing) return '';
    try {
        const items = typeof clothing === 'string' ? JSON.parse(clothing) : clothing;
        if (Array.isArray(items) && items.length > 0) {
            const count = items.reduce((sum, it) => sum + (Number(it.qty) || 1), 0);
            return `<span class="cloth-tag" title="يتطلب تجهيز ملابس: ${items.map(i => i.type || 'فستان').join(', ')}">👗 ${count}</span>`;
        }
    } catch (e) {}
    return '';
}

// تحميل ومعالجة البيانات الأساسية
async function loadOps() {
    try {
        const d = $('opsDate')?.value || todayISO();
        const [x, load, hand, hotels, team] = await Promise.all([
            api('/api/ops/overview?date=' + d),
            api('/api/ops/photographer-load?date=' + d),
            api('/api/handover?date=' + d),
            api('/api/hotels'),
            api('/api/team/options')
        ]);

        OPS_RAW = { overview: x, load: load || [], handover: hand || [] };
        OPS_HOTELS = hotels || [];
        OPS_TEAM = (team.photographers || team.all || []);

        populateHotelFilter();
        renderFilteredOps();
    } catch (e) {
        toast(e.message, 'bad');
    }
}

// ملء قائمة الفنادق في الهيدر إن لم تكن ممتلئة
function populateHotelFilter() {
    const sel = $('opsHotelFilter');
    if (!sel || sel.options.length > 1) return;
    sel.innerHTML = '<option value="">🏨 جميع الفنادق</option>' +
        OPS_HOTELS.map(h => `<option value="${esc(h.hotel_name)}">${esc(h.hotel_name)}</option>`).join('');
}

// الفلترة الفورية وإعادة الرسم
function renderFilteredOps() {
    if (!OPS_RAW) return;

    ACTIVE_HOTEL = $('opsHotelFilter')?.value || '';
    SEARCH_QUERY = ($('opsSearch')?.value || '').trim().toLowerCase();

    const qAll = OPS_RAW.overview.queue || [];
    const alertsAll = OPS_RAW.overview.alerts || [];
    const tasksAll = OPS_RAW.overview.tasks || [];
    const loadAll = OPS_RAW.load || [];
    const handAll = OPS_RAW.handover || [];
    const hotelStats = OPS_RAW.overview.hotels || [];

    // تصفية الطابور
    const filteredQueue = qAll.filter(r => {
        const matchHotel = !ACTIVE_HOTEL || String(r.hotel) === ACTIVE_HOTEL;
        const matchSearch = !SEARCH_QUERY ||
            String(r.room_number).toLowerCase().includes(SEARCH_QUERY) ||
            String(r.photographer).toLowerCase().includes(SEARCH_QUERY) ||
            String(r.sales_person).toLowerCase().includes(SEARCH_QUERY);
        return matchHotel && matchSearch;
    });

    // تصفية التنبيهات
    const filteredAlerts = alertsAll.filter(a => {
        if (!ACTIVE_HOTEL) return true;
        const linkedBooking = qAll.find(b => b.id === a.booking_id);
        return linkedBooking ? String(linkedBooking.hotel) === ACTIVE_HOTEL : true;
    });

    // تحديث المؤشرات (KPIs)
    let confirmed = 0, late = 0, unassigned = 0, due = 0;
    filteredQueue.forEach(b => {
        const st = String(b.status || '').toLowerCase();
        if (st.includes('مؤكد') || st.includes('confirm') || st.includes('جاري')) confirmed++;
        if (Number(b.minutes_to_session) < -25 && !st.includes('deliver') && !st.includes('تسليم') && !st.includes('كنسل')) late++;
        if (!b.photographer || b.photographer === 'بدون مصور') unassigned++;
        if (Number(b.remaining) > 0) due++;
    });

    $('opTotal').textContent = filteredQueue.length;
    $('opConfirmed').textContent = confirmed;
    $('opLate').textContent = late;
    $('opUnassigned').textContent = unassigned;
    $('opDue').textContent = due;
    $('opMaintenance').textContent = OPS_RAW.overview.maintenance || 0;

    // 1. رسم التنبيهات
    $('alertCount').textContent = filteredAlerts.length;
    $('opsAlerts').innerHTML = filteredAlerts.map(a => `
        <div class="alert-item ${a.severity === 'critical' ? 'danger' : 'warn'}">
            <span class="alert-icon">${a.type === 'time' ? '⏰' : '⚠️'}</span>
            <div style="flex-grow:1;">
                <b>${esc(a.title)}</b>
                <small>${esc(a.text)}</small>
            </div>
            <button class="btn-action-mini" onclick="focusBookingInQueue(${a.booking_id})">تحديد 🎯</button>
        </div>
    `).join('') || '<div class="empty-state">لا توجد تنبيهات تشغيلية حرجة 🎯</div>';

    // 2. رسم طابور الجلسات الحي
    $('opsQueue').innerHTML = filteredQueue.map(r => {
        const isLate = Number(r.minutes_to_session) < -25 && !String(r.status).includes('تسليم') && !String(r.status).includes('كنسل');
        return `
        <tr id="queue-row-${r.id}" class="${isLate ? 'row-late-alert' : ''}">
            <td><b>${esc(String(r.booking_time || '').slice(0, 5))}</b></td>
            <td>${getCountdownChip(r.minutes_to_session, r.status)}</td>
            <td>
                <span class="room-chip">${esc(r.room_number)}</span>
                ${getClothingTag(r.clothing)}
            </td>
            <td><small>${esc(r.hotel)}</small></td>
            <td>
                <select class="select-chip" onchange="quickUpdateStatus(${r.id}, this.value)">
                    <option value="انتظار" ${r.status === 'انتظار' ? 'selected' : ''}>انتظار</option>
                    <option value="مؤكد" ${r.status === 'مؤكد' ? 'selected' : ''}>مؤكد</option>
                    <option value="جاري التصوير" ${r.status === 'جاري التصوير' ? 'selected' : ''}>جاري التصوير</option>
                    <option value="Delivered" ${r.status === 'Delivered' || r.status === 'تم التسليم' ? 'selected' : ''}>تم التسليم</option>
                    <option value="كنسل" ${r.status === 'كنسل' ? 'selected' : ''}>ملغي</option>
                </select>
            </td>
            <td>
                <select class="select-chip photog-select" onchange="quickAssignPhotographer(${r.id}, this.value)">
                    <option value="">بدون مصور ⚠️</option>
                    ${OPS_TEAM.map(tm => `<option value="${esc(tm.nickname)}" ${r.photographer === tm.nickname ? 'selected' : ''}>${esc(tm.nickname)}</option>`).join('')}
                </select>
            </td>
            <td><small>${esc(r.sales_person || '-')}</small></td>
            <td><b class="${Number(r.remaining) > 0 ? 'text-due' : 'text-ok'}">${money(r.remaining)} $</b></td>
            <td>
                <div class="row-actions">
                    <button class="btn-action-mini icon" title="لوحة تحكم الأوردر والمهمة" onclick="openBookingOps(${r.id})">⚡</button>
                    ${r.phone_number ? `<button class="btn-action-mini icon whatsapp" title="تواصل سريع واتساب" onclick="quickWhatsapp('${esc(r.phone_number)}', '${esc(r.room_number)}')">💬</button>` : ''}
                    <button class="btn-action-mini icon" title="فتح شاشة الحجوزات" onclick="location.href='/reservations?q=${encodeURIComponent(r.room_number)}'">📋</button>
                </div>
            </td>
        </tr>`;
    }).join('') || '<tr><td colspan="9" class="empty-state">لا توجد جلسات تطابق البحث أو الفلتر المحدد</td></tr>';

    // 3. رسم حمل توزيع المصورين مع بار الطاقة
    const maxLoad = Math.max(1, ...loadAll.map(p => p.count || 0));
    $('photographerLoad').innerHTML = loadAll.map(p => {
        const pct = Math.min(100, Math.round((p.count / Math.max(maxLoad, 4)) * 100));
        const color = pct >= 80 ? '#ef4444' : pct >= 50 ? '#f59e0b' : '#10b981';
        return `
        <div class="photog-load-item">
            <div class="photog-load-head">
                <span class="photog-name">📸 ${esc(p.name)}</span>
                <span class="photog-count">${p.count} جلسات</span>
            </div>
            <div class="load-bar-wrap">
                <div class="load-bar-fill" style="width: ${pct}%; background-color: ${color};"></div>
            </div>
            <small class="photog-sessions">${(p.sessions || []).map(s => s.room ? `غ ${s.room} (${s.time})` : s.time).join(' • ') || 'متاح حالياً'}</small>
        </div>`;
    }).join('') || '<div class="empty-state">لا يوجد مصورون مسجلون</div>';

    // 4. مهام التشغيل
    $('opsTasks').innerHTML = tasksAll.map(t => `
        <div class="timeline-item ${t.status === 'done' ? 'row-muted' : ''}">
            <i class="${t.priority === 'critical' ? 'red' : t.priority === 'high' ? 'amber' : 'blue'}"></i>
            <div style="flex-grow:1;">
                <b>${esc(t.title)}</b>
                <small>${esc(t.details || '')} ${t.due_at ? '• ' + esc(t.due_at) : ''}</small>
            </div>
            <button class="btn-action-mini" title="إنهاء المهمة" onclick="doneTask(${t.id})">✓</button>
        </div>
    `).join('') || '<div class="empty-state">لا توجد مهام تشغيل معلقة</div>';

    // 5. تسليم الشيفت
    $('handoverList').innerHTML = handAll.map(n => `
        <div class="timeline-item ${n.resolved_at ? 'row-muted' : ''}">
            <i class="${n.priority === 'critical' ? 'red' : n.priority === 'high' ? 'amber' : 'blue'}"></i>
            <div style="flex-grow:1;">
                <b>${esc(n.shift_name || 'عام')} ${n.hotel_name ? '• ' + esc(n.hotel_name) : ''}</b>
                <small>${esc(n.note)} ${n.author ? '• ' + esc(n.author) : ''}</small>
            </div>
            <button class="btn-action-mini" title="تغيير حالة الملاحظة" onclick="resolveHandover(${n.id})">${n.resolved_at ? '↺' : '✓'}</button>
        </div>
    `).join('') || '<div class="empty-state">لا توجد ملاحظات استلام للشيفت</div>';

    // 6. أداء الفنادق اليوم
    $('hotelOps').innerHTML = hotelStats.map((h, i) => `
        <div class="rank-row">
            <span class="rank-no">${i + 1}</span>
            <div style="flex-grow:1;">
                <b>${esc(h.hotel_name)}</b>
                <small>${h.bookings || 0} حجز • متبقي $${money(h.remaining)}</small>
            </div>
            <strong>$${money(h.net)}</strong>
        </div>
    `).join('') || '<div class="empty-state">لا توجد بيانات فنادق</div>';
}

// تركيز وإبراز الغرفة في الجدول عند الضغط على التنبيه
function focusBookingInQueue(bookingId) {
    const row = document.getElementById(`queue-row-${bookingId}`);
    if (row) {
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        row.classList.add('row-highlight');
        setTimeout(() => row.classList.remove('row-highlight'), 3500);
    } else {
        openBookingOps(bookingId);
    }
}

// تعيين سريع للمصور مباشرة من السطر
async function quickAssignPhotographer(bookingId, photographerName) {
    try {
        await api(`/api/bookings/${bookingId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ photographer: photographerName })
        });
        toast('تم تعيين المصور بنجاح');
        loadOps();
    } catch (e) {
        toast(e.message, 'bad');
    }
}

// تغيير سريع للحالة من السطر مباشرة
async function quickUpdateStatus(bookingId, newStatus) {
    try {
        await api(`/api/bookings/${bookingId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });
        toast('تم تحديث حالة الحجز');
        loadOps();
    } catch (e) {
        toast(e.message, 'bad');
    }
}

// مراسلة العميل واتساب بنقرة واحدة
function quickWhatsapp(phone, room) {
    let clean = String(phone).replace(/\D/g, '');
    if (clean.length === 11 && clean.startsWith('01')) clean = '2' + clean;
    const msg = `مرحباً بحضرتك (غرفة ${room}) بخصوص موعد جلسة التصوير الخاصة بكم مع PHOTO TEAM 📸`;
    window.open(`https://wa.me/${clean}?text=${encodeURIComponent(msg)}`, '_blank');
}

// تفاصيل نافذة المهمة والـ Workflow
async function openBookingOps(id) {
    try {
        const [wf, cl] = await Promise.all([
            api(`/api/bookings/${id}/workflow`),
            api(`/api/bookings/${id}/checklist`)
        ]);

        $('globalModalBody').innerHTML = `
            <div class="modal-title">
                <div>
                    <h2>⚡ التحكم المباشر بالأوردر #${id}</h2>
                    <p>متابعة مراحل التنفيذ وقائمة التجهيزات السريعة</p>
                </div>
            </div>
            
            <div class="section-title" style="margin-top:10px;">مسار مراحل الأوردر (Workflow)</div>
            <div class="timeline" style="margin-bottom:15px;">
                ${wf.map(x => `
                    <div class="timeline-item">
                        <i class="${x.stage_status === 'done' ? 'green' : x.stage_status === 'blocked' ? 'red' : x.stage_status === 'active' ? 'amber' : 'gray'}"></i>
                        <div style="flex-grow:1;">
                            <b>${esc(x.stage_label)}</b>
                            <small>${esc(x.notes || x.stage_status)}</small>
                        </div>
                        <select class="input compact" onchange="setWorkflow(${id}, '${x.stage_key}', this.value)">
                            <option value="pending" ${x.stage_status === 'pending' ? 'selected' : ''}>انتظار</option>
                            <option value="active" ${x.stage_status === 'active' ? 'selected' : ''}>جاري</option>
                            <option value="done" ${x.stage_status === 'done' ? 'selected' : ''}>تم</option>
                            <option value="blocked" ${x.stage_status === 'blocked' ? 'selected' : ''}>متوقف</option>
                        </select>
                    </div>
                `).join('')}
            </div>

            <div class="section-title">قائمة التدقيق قبل الجلسة (Checklist)</div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 15px;">
                ${cl.map(x => `
                    <label class="check-row" style="background:var(--bg-surface); padding:8px 10px; border-radius:8px; border:1px solid var(--border); display:flex; align-items:center; gap:8px;">
                        <input type="checkbox" ${x.is_done ? 'checked' : ''} onchange="setChecklist(${id}, '${x.item_key}', this.checked)">
                        <span style="font-size:12px; font-weight:700;">${esc(x.item_label)}</span>
                    </label>
                `).join('')}
            </div>

            <div class="modal-actions" style="display:flex; justify-content:space-between;">
                <div>
                    <a class="btn" target="_blank" href="/api/bookings/${id}/qr">📱 كود الحجز QR</a>
                    <button class="btn" onclick="addFollowup(${id})">💬 إضافة متابعة</button>
                </div>
                <button class="btn primary" onclick="location.href='/reservations?open=${id}'">فتح بكامل البيانات</button>
            </div>
        `;
        $('globalModal').hidden = false;
    } catch (e) {
        toast(e.message, 'bad');
    }
}

async function setWorkflow(id, key, status) {
    try {
        await api(`/api/bookings/${id}/workflow`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ stage_key: key, stage_status: status })
        });
        toast('تم تحديث مرحلة الأوردر');
    } catch (e) { toast(e.message, 'bad'); }
}

async function setChecklist(id, key, done) {
    try {
        await api(`/api/bookings/${id}/checklist`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_key: key, is_done: done })
        });
    } catch (e) { toast(e.message, 'bad'); }
}

async function addFollowup(id) {
    const msg = prompt('نص المتابعة / التذكير للعميل:');
    if (!msg) return;
    try {
        await api(`/api/bookings/${id}/followups`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ followup_type: 'manual', channel: 'whatsapp', message: msg })
        });
        toast('تم تسجيل المتابعة');
    } catch (e) { toast(e.message, 'bad'); }
}

// إضافة وإنجاز المهام
function openTaskModal() {
    $('globalModalBody').innerHTML = `
        <div class="modal-title">
            <div><h2>➕ إضافة مهمة تشغيل سريعة</h2><p>ربط المهمة بالشيفت أو فندق محدد</p></div>
        </div>
        <div class="form-grid two" style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
            <label>عنوان المهمة *<input id="taskTitle" class="input" style="width:100%;"></label>
            <label>الأولوية<select id="taskPriority" class="input" style="width:100%;">
                <option value="normal">عادية</option>
                <option value="high">عالية</option>
                <option value="critical">حرجة</option>
                <option value="low">منخفضة</option>
            </select></label>
            <label>الفندق المرتبط<select id="taskHotel" class="input" style="width:100%;">
                <option value="">عام / جميع الفنادق</option>
                ${OPS_HOTELS.map(h => `<option value="${h.id}">${esc(h.hotel_name)}</option>`).join('')}
            </select></label>
            <label>الموعد الأقصى<input id="taskDue" type="datetime-local" class="input" style="width:100%;"></label>
            <label style="grid-column:span 2;">تفاصيل إضافية<textarea id="taskDetails" class="input" style="width:100%; height:60px;"></textarea></label>
        </div>
        <div class="modal-actions" style="margin-top:15px; text-align:left;">
            <button class="btn primary" onclick="saveTask()">حفظ المهمة</button>
        </div>
    `;
    $('globalModal').hidden = false;
}

async function saveTask() {
    try {
        await api('/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: $('taskTitle').value,
                priority: $('taskPriority').value,
                hotel_id: $('taskHotel').value,
                due_at: $('taskDue').value || null,
                details: $('taskDetails').value
            })
        });
        closeModal();
        loadOps();
        toast('تمت إضافة المهمة بنجاح');
    } catch (e) { toast(e.message, 'bad'); }
}

async function doneTask(id) {
    try {
        await api('/api/tasks/' + id, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: 'done' })
        });
        loadOps();
    } catch (e) { toast(e.message, 'bad'); }
}

// ملاحظات تسليم الشيفت
function openHandoverModal() {
    $('globalModalBody').innerHTML = `
        <div class="modal-title">
            <div><h2>🔁 تسجيل ملاحظة تسليم شيفت</h2><p>توثيق ملاحظات الوردية لتسليمها للشيفت التالي</p></div>
        </div>
        <div class="form-grid two" style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
            <label>الفندق<select id="handHotel" class="input" style="width:100%;">
                <option value="">عام</option>
                ${OPS_HOTELS.map(h => `<option value="${h.id}">${esc(h.hotel_name)}</option>`).join('')}
            </select></label>
            <label>الوردية<select id="handShift" class="input" style="width:100%;">
                <option>صباحي</option>
                <option>مسائي</option>
                <option>ليلي</option>
                <option>عام</option>
            </select></label>
            <label>الأولوية<select id="handPriority" class="input" style="width:100%;">
                <option value="normal">عادية</option>
                <option value="high">عالية</option>
                <option value="critical">حرجة</option>
            </select></label>
            <label style="grid-column:span 2;">نص الملاحظة *<textarea id="handNote" class="input" style="width:100%; height:70px;"></textarea></label>
        </div>
        <div class="modal-actions" style="margin-top:15px; text-align:left;">
            <button class="btn primary" onclick="saveHandover()">حفظ الملاحظة</button>
        </div>
    `;
    $('globalModal').hidden = false;
}

async function saveHandover() {
    try {
        await api('/api/handover', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                hotel_id: $('handHotel').value || null,
                shift_name: $('handShift').value,
                priority: $('handPriority').value,
                note: $('handNote').value,
                shift_date: $('opsDate').value
            })
        });
        closeModal();
        loadOps();
        toast('تم حفظ ملاحظة الشيفت');
    } catch (e) { toast(e.message, 'bad'); }
}

async function resolveHandover(id) {
    try {
        await api('/api/handover/' + id + '/resolve', { method: 'POST' });
        loadOps();
    } catch (e) { toast(e.message, 'bad'); }
}

// التقفيل اليومي
function openClosingModal() {
    const opts = OPS_HOTELS.map(h => `<option value="${h.id}">${esc(h.hotel_name)}</option>`).join('');
    $('globalModalBody').innerHTML = `
        <div class="modal-title">
            <div><h2>💰 التقفيل اليومي ومطابقة الخزينة</h2><p>مطابقة المحصل الفعلي بالدرج مع سجلات النظام</p></div>
        </div>
        <div style="display:flex; gap:10px; margin-bottom:12px;">
            <select id="closeHotel" class="input" style="flex:1;">${opts}</select>
            <input id="closeDate" type="date" class="input" value="${$('opsDate').value}" style="flex:1;">
            <button class="btn" onclick="loadClosing()">جلب الأرقام</button>
        </div>
        <div id="closingArea"></div>
    `;
    $('globalModal').hidden = false;
    if (OPS_HOTELS.length) loadClosing();
}

async function loadClosing() {
    try {
        const x = await api(`/api/closings/daily?hotel_id=${$('closeHotel').value}&date=${$('closeDate').value}`);
        const e = x.expected || {}, c = x.closing || {};
        $('closingArea').innerHTML = `
            <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-bottom:15px; background:var(--bg-surface); padding:10px; border-radius:8px;">
                <div><small style="display:block; color:var(--text-muted);">المتوقع USD</small><b style="color:#0284c7;">$${money(e.usd)}</b></div>
                <div><small style="display:block; color:var(--text-muted);">المتوقع EUR</small><b style="color:#0284c7;">€${money(e.eur)}</b></div>
                <div><small style="display:block; color:var(--text-muted);">كاش EGP</small><b style="color:#10b981;">${money(e.cash)} LE</b></div>
                <div><small style="display:block; color:var(--text-muted);">فيزا EGP</small><b style="color:#8b5cf6;">${money(e.visa)} LE</b></div>
            </div>
            <div class="section-title">المبالغ الفعلية المستلمة في الدرج</div>
            <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:8px;">
                <label>فعلي USD<input id="actUsd" class="input" type="number" step="0.01" value="${c.actual_usd || e.usd || 0}"></label>
                <label>فعلي EUR<input id="actEur" class="input" type="number" step="0.01" value="${c.actual_eur || e.eur || 0}"></label>
                <label>فعلي كاش LE<input id="actCash" class="input" type="number" step="0.01" value="${c.actual_egp_cash || e.cash || 0}"></label>
                <label>فعلي فيزا LE<input id="actVisa" class="input" type="number" step="0.01" value="${c.actual_egp_visa || e.visa || 0}"></label>
            </div>
            <label style="display:block; margin-top:10px;">ملاحظات الفروقات والعجز/الزيادة
                <textarea id="closeNote" class="input" style="width:100%; height:50px;">${esc(c.variance_note || '')}</textarea>
            </label>
            <div class="modal-actions" style="margin-top:15px; display:flex; justify-content:flex-end; gap:8px;">
                <button class="btn" onclick="saveClosing('open')">حفظ كمسودة</button>
                <button class="btn primary" onclick="saveClosing('closed')">🔒 اعتماد وإغلاق الوردية</button>
            </div>
        `;
    } catch (e) { toast(e.message, 'bad'); }
}

async function saveClosing(status) {
    try {
        await api('/api/closings/daily', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                hotel_id: $('closeHotel').value,
                closing_date: $('closeDate').value,
                actual_usd: $('actUsd').value,
                actual_eur: $('actEur').value,
                actual_egp_cash: $('actCash').value,
                actual_egp_visa: $('actVisa').value,
                variance_note: $('closeNote').value,
                status
            })
        });
        toast(status === 'closed' ? 'تم إغلاق الوردية وتوثيق المطابقة' : 'تم حفظ مسودة التقفيل');
        closeModal();
    } catch (e) { toast(e.message, 'bad'); }
}

// التهيئة والمزامنة الصامتة كل 30 ثانية
$('opsDate').value = todayISO();
loadOps();

if (AUTO_REFRESH_TIMER) clearInterval(AUTO_REFRESH_TIMER);
AUTO_REFRESH_TIMER = setInterval(() => {
    if (document.visibilityState === 'visible') {
        loadOps();
    }
}, 30000);

// ===== V80: الدوال التكميلية لغرفة العمليات (الصوت، وضع الشاشة TV، الساعة الذهبية، لوحة الأوامر) =====
let SOUND_FX_ENABLED = true;

function toggleSoundFx() {
    SOUND_FX_ENABLED = !SOUND_FX_ENABLED;
    const btn = $('soundToggleBtn');
    if (btn) {
        btn.textContent = SOUND_FX_ENABLED ? '🔔 صوت التنبيه: يعمل' : '🔕 صوت التنبيه: مكتوم';
    }
    toast(SOUND_FX_ENABLED ? 'تم تفعيل التنبيهات الصوتية' : 'تم كتم التنبيهات الصوتية');
}

function toggleKioskMode() {
    document.body.classList.toggle('kiosk-mode');
    const isKiosk = document.body.classList.contains('kiosk-mode');
    if (isKiosk && document.documentElement.requestFullscreen) {
        document.documentElement.requestFullscreen().catch(() => {});
    } else if (!isKiosk && document.fullscreenElement && document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
    }
}

function closeCommandPalette(e) {
    if ($('quickCmdPalette')) $('quickCmdPalette').style.display = 'none';
}

function updateGoldenHourBanner() {
    const m = new Date().getMonth() + 1;
    // مواعيد تقريبية للساعة الذهبية والغروب في المنتجعات السياحية حسب الموسم
    const isSummer = m >= 5 && m <= 9;
    if ($('ghStartTime')) $('ghStartTime').textContent = isSummer ? '17:15' : '16:10';
    if ($('ghSunsetTime')) $('ghSunsetTime').textContent = isSummer ? '18:35' : '17:20';
    if ($('goldenHourTitle')) $('goldenHourTitle').textContent = 'توقيت مثالي لجلسات الشاطئ والفساتين قبل الغروب';
}
updateGoldenHourBanner();
