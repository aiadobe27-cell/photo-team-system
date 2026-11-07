// ============================================================================
// 📌 ملف الكود البرمجي (chat.js): كود شاشة المحادثات الداخلية (التبديل بين شات المديرين وشات فريق العمل وإرسال الرسائل)
// ============================================================================

let currentChatChannel = window.CAN_MANAGERS_CHAT ? 'managers' : 'team';
let chatHotels = [];

async function initChatPage() {
  chatHotels = await apiSafe('/api/hotels', [], 'تحميل الفنادق');
  if ($('chatHotelFilter')) {
    $('chatHotelFilter').innerHTML = '<option value="">جميع الفنادق</option>' + chatHotels.map(h => `<option value="${h.id}">${esc(h.hotel_name)}</option>`).join('');
  }
  if ($('chatSendForm')) {
    $('chatSendForm').addEventListener('submit', sendChatMessage);
  }
  switchChatChannel(currentChatChannel);
}

function switchChatChannel(ch) {
  if (ch === 'managers' && !window.CAN_MANAGERS_CHAT) {
    return toast('شات الإدارة مخصص للأونر والمديرين فقط', 'bad');
  }
  currentChatChannel = ch;
  if ($('tabBtnManagersChat')) $('tabBtnManagersChat').className = ch === 'managers' ? 'btn primary' : 'btn';
  if ($('tabBtnTeamChat')) $('tabBtnTeamChat').className = ch === 'team' ? 'btn primary' : 'btn';
  if ($('activeChatChannelTitle')) {
    $('activeChatChannelTitle').textContent = ch === 'managers' ? '👔 شات الإدارة والمديرين (الأونر والمديرين فقط)' : '👥 شات فريق العمل (المدير والموظفين)';
  }
  if ($('chatHotelFilter')) {
    $('chatHotelFilter').style.display = ch === 'team' ? '' : 'none';
  }
  loadChatMessages();
}

async function loadChatMessages() {
  const h = $('chatHotelFilter')?.value || '';
  const res = await apiSafe(`/api/chat/messages?channel=${encodeURIComponent(currentChatChannel)}&hotel_id=${encodeURIComponent(h)}`, { rows: [] }, 'تحميل المحادثة');
  const rows = res.rows || [];
  const isCeo = Boolean(res.is_ceo);
  const box = $('chatMessagesBox');
  if (!box) return;
  box.innerHTML = rows.length ? rows.map(m => `
    <div style="padding:10px 14px;border-radius:12px;background:var(--bg-card);border:1px solid var(--border);display:flex;justify-content:space-between;align-items:flex-start;gap:10px;">
      <div>
        <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:4px;">
          <b style="color:var(--primary);font-size:13px;">${esc(m.sender_name)}</b>
          <span class="badge blue" style="font-size:10px;padding:1px 7px;">${esc(m.sender_role)}</span>
          ${m.hotel_name ? `<span class="badge green" style="font-size:10px;padding:1px 7px;">${esc(m.hotel_name)}</span>` : ''}
          <small style="color:var(--text-muted);font-size:11px;" dir="ltr">${esc(m.formatted_time || '')}</small>
        </div>
        <div style="font-size:13.5px;color:var(--text-main);line-height:1.5;">${esc(m.message_text)}</div>
      </div>
      ${isCeo ? `<button type="button" class="mini-btn red" onclick="deleteChatMsg(${m.id})">×</button>` : ''}
    </div>
  `).join('') : '<div class="empty-state">لا توجد رسائل بعد في هذه المحادثة</div>';
  box.scrollTop = box.scrollHeight;
}

async function sendChatMessage(e) {
  e.preventDefault();
  const inp = $('chatInputText');
  const txt = (inp?.value || '').trim();
  if (!txt) return;
  try {
    await apiJSON('/api/chat/messages', 'POST', {
      channel: currentChatChannel,
      hotel_id: num($('chatHotelFilter')?.value) || null,
      message_text: txt
    });
    inp.value = '';
    await loadChatMessages();
  } catch (err) {
    toast(err.message, 'bad');
  }
}

async function deleteChatMsg(id) {
  try {
    await api(`/api/chat/messages/${id}`, { method: 'DELETE' });
    await loadChatMessages();
  } catch (err) {
    toast(err.message, 'bad');
  }
}

document.addEventListener('DOMContentLoaded', initChatPage);
