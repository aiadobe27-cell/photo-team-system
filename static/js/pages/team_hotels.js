
const RECENT_ADDED_NBE_NIDS = new Set(["30111053100156", "30406192701679", "30107102701635", "28710182703152", "30109262701316", "28401282800195", "29906121301251", "29909182702991", "29806150400353", "30211112700558", "30012251700659", "29410272701515", "30307042500413", "30507063100155", "29809152107431", "29901172600278", "30207012700715", "30411143100132", "27010090201074", "28311252800591", "29604223100033", "28401068800412", "30102221701099", "28701152107131", "30210012709756", "29910121500332", "30201012411251", "28801040101495", "30509033100277", "29509012706714", "30612170400135", "30207012700731", "30807202608278", "29807281700332", "29612212701615", "29609182700391", "30003041202312", "29909013100273", "29906061600912", "30611080400318", "29204281701375", "28912102703876", "30304142702014", "30011022700517", "28105308800719", "30006222701352", "27206022700072", "30305242700198", "27506171100391", "30812012714792", "29904101602457", "28807302801092"]);
function isRecentlyAddedNbeEmployee(r) {
  const u = String(r?.username || '').trim().toLowerCase();
  const nid = String(r?.national_id || '').trim();
  return u.startsWith('nbe_') || (nid && RECENT_ADDED_NBE_NIDS.has(nid));
}

// ============================================================================
// 📌 ملف الكود البرمجي (team_hotels.js): كود شاشة الموظفين والفنادق (إضافة موظف، صلاحيات الفنادق، ونقل موظف من فندق لفندق)
// ============================================================================

let hotelsCache = [], teamCache = [], editingTeamId = null, tempPermissions = new Set();

const PERMS = {
  bookings_access: 'إدارة الحجوزات و Checkout',
  laundry_access: 'إدارة ومتابعة المغسلة',
  assets_access: 'إدارة عُهدة المعدات والفساتين',
  sales_access: 'شاشة المبيعات والعمولات',
  finances_access: 'التقارير المالية والتقفيل والمرتبات',
  team_access: 'إدارة الموظفين والفنادق'
};

const ROLES = {
  CEO: 'CEO / مدير عام',
  Manager: 'Manager / مدير',
  Photographer: 'Photographer / مصور',
  Sales: 'Sales / مبيعات',
  Accountant: 'Accountant / حسابات',
  Reviewer: 'Reviewer / مراجعة'
};

async function loadTeamHotels() {
  initLogicTabs();
  try {
    await fetch('/api/team/sync-nbe-roster', {method:'POST'}).catch(()=>{});
    [teamCache, hotelsCache] = await Promise.all([api('/api/team'), api('/api/hotels')]);
    teamCache = (teamCache || []).filter(r => !isRecentlyAddedNbeEmployee(r));
    renderTeam();
    renderHotels();
    fillHotelParent();
  } catch (e) {
    toast(e.message, 'bad');
  }
}

function memberRoles(r) {
  const xs = Array.isArray(r?.roles) && r.roles.length ? r.roles : (r?.role ? [r.role] : []);
  return [...new Set(xs)];
}

function hasMemberRole(r, role) {
  return memberRoles(r).some(x => String(x).toLowerCase() === String(role).toLowerCase());
}

function managerHotelsText(r) {
  if (hasMemberRole(r, 'Manager')) {
    const xs = r.manager_hotels || [];
    return xs.length ? xs.map(x => x.hotel_name).join('، ') : (r.hotel_name || 'لم تُحدد فنادق');
  }
  return r.hotel_name || '-';
}

function rolesText(r) {
  return memberRoles(r).map(x => ROLES[x] || x).join(' + ') || '-';
}

async function syncNbeRosterToTeam() {
  try {
    const res = await api('/api/team/sync-nbe-roster', { method: 'POST' });
    toast(res.message || 'تمت مزامنة موظفي شيت البنك الأهلي بنجاح');
    await loadTeamHotels();
  } catch (e) {
    toast(e.message, 'bad');
  }
}
window.syncNbeRosterToTeam = syncNbeRosterToTeam;

function renderTeam() {
  const q = String($('teamSearchInput')?.value || '').trim().toLowerCase();
  const filtered = teamCache.filter(r => {
    if (!q) return true;
    return String(r.full_name || '').toLowerCase().includes(q) ||
           String(r.nickname || '').toLowerCase().includes(q) ||
           String(r.national_id || '').toLowerCase().includes(q) ||
           String(r.username || '').toLowerCase().includes(q);
  });
  $('teamBody').innerHTML = filtered.map((r, i) => `
    <tr class="select-row" ondblclick="openTeamForm(${r.id})">
      <td>${i + 1}</td>
      <td><b>${esc(r.full_name)}</b></td>
      <td><span class="badge blue">${esc(r.nickname)}</span></td>
      <td dir="ltr" style="font-family:monospace;font-weight:700;">${esc(r.national_id || '-')}</td>
      <td>
        <span class="badge ${String(r.nbe_type || '').includes('حسابات') ? 'amber' : 'blue'}">${esc(r.nbe_type || 'ON US بطاقات')}</span>
        ${r.visa_card_number ? `<div dir="ltr" style="font-size:11px;margin-top:2px;">${esc(r.visa_card_number)}</div>` : ''}
      </td>
      <td>${esc(rolesText(r))}</td>
      <td>${esc(managerHotelsText(r))}</td>
      <td><b>${money(r.base_salary || 0, 0)} LE</b> <small>(${money(r.commission_rate)}%)</small></td>
      <td dir="ltr">${esc(r.username || '-')}</td>
      <td>${r.is_active && r.session_active !== 0 ? '<span class="badge green">✅ نشط</span>' : '<span class="badge red">❌ معطل / مفصول</span>'}</td>
      <td><div class="context-actions">
        <button class="mini-btn blue" title="نقل الموظف لفندق آخر (مع حفظ شغله السابق)" onclick="openTransferHotelModal(${r.id})">🔄 نقل فندق</button><button class="mini-btn amber" onclick="openTeamForm(${r.id})">✏️</button>
        <button class="mini-btn green" onclick="sendCredentialsWhatsapp(${r.id})">💬</button>
        <button class="mini-btn purple" onclick="forceLogoutUser(${r.id})">🔒</button>
        <button class="mini-btn ${r.is_active ? 'red' : 'green'}" onclick="toggleTeamStatus(${r.id})">${r.is_active ? '⛔' : '✅'}</button>
      </div></td>
    </tr>`).join('') || '<tr><td colspan="11" class="empty-state">لا يوجد موظفون</td></tr>';
}

function renderHotels() {
  const map = Object.fromEntries(hotelsCache.map(h => [h.id, h.hotel_name]));
  $('hotelsBody').innerHTML = hotelsCache.map(r => `<tr>
  <td>${r.id}</td>
  <td><b>${esc(r.hotel_name)}</b></td>
  <td>${esc(r.parent_hotel_id ? map[r.parent_hotel_id] || r.parent_hotel_id : 'رئيسي / مستقل')}</td>
  <td>${esc(r.created_at || '-')}</td>
  <td>
    <button class="mini-btn amber" onclick="editHotel(${r.id})">✏️</button>
    <button class="mini-btn red" onclick="disableHotel(${r.id})">🚫</button>
  </td>
  </tr>`).join('') || '<tr><td colspan="5">لا توجد فنادق</td></tr>';
}

async function editHotel(id){
  const h = hotelsCache.find(x => Number(x.id) === Number(id));
  if(!h) return;

  const options = hotelsCache
    .filter(x => Number(x.id) !== Number(id))
    .map(x => `${x.id}: ${x.hotel_name}`)
    .join('\\n');

  const name = prompt('اسم الفندق', h.hotel_name);
  if(!name) return;

  const currentParent = h.parent_hotel_id || '';
  const parentInput = prompt(
    'اكتب رقم الفندق الرئيسي الجديد (اتركه فارغًا للفندق المستقل)\\n\\n' + options,
    currentParent
  );

  if(parentInput !== null && Number(parentInput) === Number(id)){
    toast('لا يمكن جعل الفندق تابعًا لنفسه','bad');
    return;
  }

  const parentId = parentInput ? Number(parentInput) : null;

  await api('/api/hotels/'+id, {
    method:'PUT',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      hotel_name:name,
      parent_hotel_id: Number.isFinite(parentId) ? parentId : null
    })
  });

  toast('تم تعديل الفندق والتبعية بنجاح','good');
  loadTeamHotels();
}

async function disableHotel(id){
  if(!confirm('هل تريد تعطيل هذا الفندق؟')) return;
  await api('/api/hotels/'+id,{method:'DELETE'});
  toast('تم تعطيل الفندق','good');
  loadTeamHotels();
}

function fillHotelParent() {
  $('hParent').innerHTML = '<option value="">-- فندق رئيسي / مستقل --</option>' + hotelsCache.map(h => `<option value="${h.id}">${esc(h.hotel_name)}</option>`).join('');
}

function permissionHTML() {
  return Object.entries(PERMS).map(([k, v]) => `<label class="permission-item"><input type="checkbox" class="perm-cb" value="${k}" ${tempPermissions.has(k) ? 'checked' : ''}><span>${esc(v)}</span></label>`).join('');
}

function roleChecksHTML(r) {
  const selected = new Set(memberRoles(r));
  if (!selected.size && !r) selected.add('Photographer');
  return Object.entries(ROLES).map(([k, v]) => `<label class="permission-item role-item"><input type="checkbox" class="role-cb" value="${k}" ${selected.has(k) ? 'checked' : ''}><span>${esc(v)}</span></label>`).join('');
}

function hotelChecksHTML(r) {
  const selected = new Set((r?.manager_hotels || []).map(x => Number(x.hotel_id)));
  return hotelsCache.map(h => `<label class="hotel-perm"><input type="checkbox" class="manager-hotel-cb" value="${h.id}" ${selected.has(Number(h.id)) ? 'checked' : ''}> ${esc(h.hotel_name)}</label>`).join('');
}

function getSelectedRoles() {
  return $$('.role-cb:checked').map(x => x.value);
}

function refreshPrimaryRole(preferred = null) {
  const select = $('tPrimaryRole');
  if (!select) return;
  const selected = getSelectedRoles();
  const current = preferred || select.value;
  select.innerHTML = selected.map(r => `<option value="${r}">${esc(ROLES[r] || r)}</option>`).join('');
  if (selected.includes(current)) select.value = current;
  else if (selected.length) select.value = selected[0];
}

function roleUI(preferredPrimary = null) {
  const roles = getSelectedRoles();
  const isManager = roles.includes('Manager');
  if ($('singleHotelWrap')) $('singleHotelWrap').hidden = isManager;
  if ($('multiHotelWrap')) $('multiHotelWrap').hidden = !isManager;
  refreshPrimaryRole(preferredPrimary);
}

function selectAllPermissions(flag) {
  $$('.perm-cb').forEach(cb => { cb.checked = !!flag; });
}

async function openTeamForm(id = null) {
  editingTeamId = id;
  const r = id ? teamCache.find(x => x.id === id) : null;
  tempPermissions = new Set(r?.permissions || (r ? [] : ['assets_access']));
  const currentPrimary = r?.role || (memberRoles(r)[0] || 'Photographer');

  showModal(`
    <div class="modal-title"><h2>${r ? '✏️ تعديل بيانات الموظف' : '➕ إضافة موظف جديد'}</h2><p>يمكن اختيار أكثر من دور لنفس الموظف، ثم تحديد الصلاحيات الفعلية من الـ Checkboxes.</p></div>
    <form id="teamForm">
      <div class="form-grid two">
        <div class="field"><label>الاسم بالكامل *</label><input class="input" id="tFull" value="${esc(r?.full_name || '')}" required></div>
        <div class="field"><label>اللقب (الاسم الحركي) *</label><input class="input" id="tNick" value="${esc(r?.nickname || '')}" required></div>
        <div class="field"><label>رقم الهاتف (WhatsApp)</label><input class="input" id="tPhone" value="${esc(r?.phone_number || '')}"></div>
        <div class="field"><label>صلاحية الوصول للأجهزة</label><select class="input" id="tAccess"><option>وصول كامل (Desktop + Mobile)</option><option>تطبيق سطح المكتب فقط</option><option>تطبيق الهاتف فقط</option></select></div>
      </div>

      <div class="form-section">
        <h3>👥 الأدوار المتعددة</h3>
        <p class="muted">مثال: يمكن أن يكون الموظف Manager + Photographer في نفس الوقت.</p>
        <div class="permission-grid role-grid">${roleChecksHTML(r)}</div>
        <div class="field" style="margin-top:10px"><label>الدور الأساسي (للتوافق مع الشاشات القديمة)</label><select class="input" id="tPrimaryRole"></select></div>
      </div>

      <div class="form-grid two">
        <div class="field" id="singleHotelWrap"><label>الفندق</label><select class="input" id="tHotel"><option value="">-- بدون فندق محدد --</option>${hotelsCache.map(h => `<option value="${h.id}">${esc(h.hotel_name)}</option>`).join('')}</select></div>
        <div class="field full-span" id="multiHotelWrap"><label>اختر الفنادق المسؤول عنها المدير</label><div class="hotel-perm-grid">${hotelChecksHTML(r)}</div></div>
        <div class="field"><label>نسبة العمولة %</label><input class="input" type="number" step=".01" id="tCommission" value="${num(r?.commission_rate)}"></div>
        <div class="field"><label>الراتب الأساسي LE</label><input class="input" type="number" step=".01" id="tSalary" value="${num(r?.base_salary)}"></div>
        <div class="field"><label>الرقم القومي</label><input class="input" id="tNational" value="${esc(r?.national_id || '')}"></div>
        <div class="field"><label>رقم الفيزا / كارت البنك</label><input class="input" id="tVisa" value="${esc(r?.visa_card_number || '')}"></div>
        <div class="field"><label>اسم المستخدم *</label><input class="input" id="tUsername" value="${esc(r?.username || '')}" required></div>
        <div class="field"><label>${r ? 'كلمة المرور (اتركها فارغة لتثبيت القديمة)' : 'كلمة المرور *'}</label><input class="input" type="password" id="tPassword" ${r ? '' : 'required'}></div>
      </div>

      <div class="form-section">
        <div class="panel-head"><div><h3>⚙️ الصلاحيات المخصصة</h3><p>الصلاحيات هنا هي التي تتحكم فعليًا في الشاشات والـ API.</p></div><div class="action-grid"><button type="button" class="mini-btn blue" onclick="applyRoleDefaultPermissions()">⚡ صلاحيات الدور تلقائياً</button><button type="button" class="mini-btn green" onclick="selectAllPermissions(true)">☑ الكل</button><button type="button" class="mini-btn gray" onclick="selectAllPermissions(false)">☐ إلغاء الكل</button></div></div>
        <div class="permission-grid">${permissionHTML()}</div>
      </div>

      <div class="action-grid">
        <button type="button" class="btn green" onclick="sendCredentialsWhatsapp(${id || 0},true)">💬 إرسال بيانات الدخول واتساب</button>
        ${r ? `<button type="button" class="btn purple" onclick="forceLogoutUser(${r.id})">🔒 إجبار خروج وتفريغ الجلسات</button><button type="button" class="btn amber" onclick="toggleTeamStatus(${r.id})">🔄 تغيير حالة الحساب</button>` : ''}
      </div>
      <div class="modal-actions"><button type="button" class="btn" onclick="closeModal()">❌ إلغاء</button><button class="btn green">${r ? '💾 حفظ التعديلات' : '➕ إضافة موظف جديد'}</button></div>
    </form>`, 'modal-xl');

  $('tAccess').value = r?.access_type || 'وصول كامل (Desktop + Mobile)';
  $('tHotel').value = r?.hotel_id || '';
  $$('.role-cb').forEach(cb => cb.addEventListener('change', () => roleUI()));
  roleUI(currentPrimary);
  $('teamForm').addEventListener('submit', saveTeam);
}

async function saveTeam(e) {
  e.preventDefault();
  const roles = getSelectedRoles();
  if (!roles.length) return toast('اختر دوراً واحداً على الأقل للموظف', 'bad');
  const primaryRole = $('tPrimaryRole').value || roles[0];
  const manager_hotels = $$('.manager-hotel-cb:checked').map(x => ({hotel_id: Number(x.value), can_edit: 1}));
  const permissions = $$('.perm-cb:checked').map(x => x.value);
  const body = {
    full_name: $('tFull').value.trim(),
    nickname: $('tNick').value.trim(),
    phone_number: $('tPhone').value.trim(),
    role: primaryRole,
    roles,
    access_type: $('tAccess').value,
    hotel_id: roles.includes('Manager') ? (manager_hotels[0]?.hotel_id || null) : ($('tHotel').value || null),
    manager_hotels,
    permissions,
    commission_rate: num($('tCommission').value),
    base_salary: num($('tSalary').value),
    national_id: $('tNational').value.trim(),
    visa_card_number: $('tVisa').value.trim(),
    username: $('tUsername').value.trim(),
    password: $('tPassword').value
  };
  try {
    await apiJSON(editingTeamId ? `/api/team/${editingTeamId}` : '/api/team', editingTeamId ? 'PUT' : 'POST', body);
    toast(`تم حفظ (${body.nickname}) بالأدوار والصلاحيات المحددة بنجاح`);
    closeModal();
    await loadTeamHotels();
  } catch (err) {
    toast(err.message, 'bad');
  }
}

function sendCredentialsWhatsapp(id = 0, fromForm = false) {
  const r = id ? teamCache.find(x => x.id === id) : null;
  const phone = fromForm ? $('tPhone')?.value : r?.phone_number;
  const nick = fromForm ? $('tNick')?.value : r?.nickname;
  const user = fromForm ? $('tUsername')?.value : r?.username;
  const pass = fromForm ? $('tPassword')?.value : '';
  if (!phone || !user) return toast('يرجى إدخال رقم الهاتف واسم المستخدم أولاً', 'bad');
  let pc = String(phone).replace(/\D/g, '');
  if (pc.length === 11 && pc.startsWith('01')) pc = '2' + pc;
  const msg = `أهلاً بك يا ${nick || 'زميلنا'} في فريق التصوير 📸\nإليك بيانات حسابك للوصول للنظام:\n👤 اسم المستخدم: ${user}\n🔑 كلمة المرور: ${pass || '*(كلمتك السرية الخاصة)*'}\nنتمنى لك التوفيق دائماً!`;
  window.open(`https://wa.me/${pc}?text=${encodeURIComponent(msg)}`, '_blank');
}

async function forceLogoutUser(id) {
  const r = teamCache.find(x => x.id === id);
  if (!confirmAction(`هل تريد إجبار الموظف (${r?.nickname || id}) على تسجيل الخروج وإبطال جلسته؟`)) return;
  try {
    await api(`/api/team/${id}/force-logout`, {method: 'POST'});
    toast('تم إبطال جلسة الموظف بنجاح');
    closeModal();
    loadTeamHotels();
  } catch (e) { toast(e.message, 'bad'); }
}

async function toggleTeamStatus(id) {
  const r = teamCache.find(x => x.id === id);
  if (!confirmAction(`تغيير حالة حساب (${r?.nickname || id})؟`)) return;
  try {
    const x = await api(`/api/team/${id}/toggle`, {method: 'POST'});
    toast(x.is_active ? 'تم تنشيط الحساب' : 'تم تعطيل الحساب');
    closeModal();
    loadTeamHotels();
  } catch (e) { toast(e.message, 'bad'); }
}

async function saveHotel(e) {
  e.preventDefault();
  try {
    await apiJSON('/api/hotels', 'POST', {hotel_name: $('hName').value.trim(), parent_hotel_id: $('hParent').value || null});
    toast(`تمت إضافة الفندق (${$('hName').value}) بنجاح`);
    $('hotelInlineForm').reset();
    await loadTeamHotels();
  } catch (err) { toast(err.message, 'bad'); }
}

document.addEventListener('DOMContentLoaded', () => {$('hotelInlineForm')?.addEventListener('submit', saveHotel);});
loadTeamHotels();

function openTransferHotelModal(uid) {
  const r = teamCache.find(x => Number(x.id) === Number(uid));
  if (!r) return;
  const hotelOpts = hotelsCache.map(h =>
    `<option value="${h.id}" ${Number(r.hotel_id) === Number(h.id) ? 'selected' : ''}>${esc(h.hotel_name)}</option>`
  ).join('');
  showModal(`
    <div class="modal-title">
      <h2>🔄 نقل فندق الموظف • ${esc(r.nickname)}</h2>
    </div>
    <form id="transferHotelForm">
      <div class="form-grid two">
        <div class="field">
          <label>الفندق الحالي</label>
          <input class="input" readonly value="${esc(r.hotel_name || '-')}">
        </div>
        <div class="field">
          <label>نقل إلى الفندق الجديد *</label>
          <select class="input" id="trNewHotelId" required>${hotelOpts}</select>
        </div>
      </div>
      <div style="margin-top:12px;padding:10px 12px;border-radius:10px;background:var(--bg-surface-2);border:1px solid var(--border);font-size:12.5px;font-weight:700;">
        ✅ جميع الحجوزات والأوردرات السابقة المسجلة في الفندق القديم تظل محفوظة كما هي في فندقها الأصلي وباسم الموظف.
      </div>
      <div class="modal-actions">
        <button type="button" class="btn" onclick="closeModal()">إلغاء</button>
        <button type="submit" class="btn green">💾 تأكيد النقل</button>
      </div>
    </form>
  `, 'modal-lg');
  $('transferHotelForm').addEventListener('submit', async e => {
    e.preventDefault();
    try {
      const res = await apiJSON(`/api/team/${uid}/transfer-hotel`, 'POST', { hotel_id: Number($('trNewHotelId').value) });
      closeModal();
      toast(`✅ تم نقل (${r.nickname}) إلى فندق (${res.new_hotel}) مع الحفاظ على أعماله السابقة`);
      await loadTeamHotels();
    } catch (err) {
      toast(err.message, 'bad');
    }
  });
}
window.openTransferHotelModal = openTransferHotelModal;

