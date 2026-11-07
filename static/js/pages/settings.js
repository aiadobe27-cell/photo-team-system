// ============================================================================
// 📌 ملف الكود البرمجي (settings.js): كود شاشة الإعدادات وحفظ سعر الصرف ونسب العمولات
// ============================================================================


let settingsRows=[];
async function loadSettings(){
 try{
  settingsRows=await api('/api/settings');
  $('settingsGrid').innerHTML=settingsRows.map(r=>`<div class="setting-card"><label>${esc(r.setting_key)}</label><input class="input setting-input" data-key="${esc(r.setting_key)}" value="${esc(r.setting_value)}"><small>آخر تحديث: ${esc(r.updated_at||'-')}</small></div>`).join('');
 }catch(e){toast(e.message,'bad')}
}
async function saveSettings(){
 const body={};$$('.setting-input').forEach(x=>body[x.dataset.key]=x.value);
 try{await api('/api/settings',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});toast('تم حفظ الإعدادات')}catch(e){toast(e.message,'bad')}
}
loadSettings();


async function triggerFullBackupSaveAs() {
  try {
    const res = await fetch('/api/backup/save-dialog', { method: 'POST' });
    if (res.ok) {
      const data = await res.json();
      if (data && data.cancelled) return toast('تم إلغاء الحفظ', 'bad');
      if (data && data.saved && data.path) return toast('✅ تم حفظ النسخة الاحتياطية بنجاح في: ' + data.path);
    }
  } catch (e) {}
  location.href = '/api/backup/export';
}
window.triggerFullBackupSaveAs = triggerFullBackupSaveAs;

async function restoreFullBackupFromFile(inputEl) {
  const file = inputEl?.files?.[0];
  if (!file) return;
  try {
    const text = await file.text();
    const parsed = JSON.parse(text);
    const res = await apiJSON('/api/backup/restore', 'POST', parsed);
    toast(res.message || '✅ تم استرجاع النسخة الاحتياطية بنجاح!');
    loadSettings();
  } catch (e) {
    toast(e.message || '⚠️ تعذر استرجاع النسخة الاحتياطية', 'bad');
  }
}
window.restoreFullBackupFromFile = restoreFullBackupFromFile;
