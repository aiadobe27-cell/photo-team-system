// ============================================================================
// 📌 ملف الكود البرمجي (context-menu.js): قائمة الكليك يمين السريعة على الجداول والكروت
// ============================================================================

/* =========================================================
   V72 — Context Menu Engine (يحل محل v45_interaction_engine.js)

   - بيظهر بس على صفوف/كروت فيها إجراءات حقيقية.
   - كل عنصر في القائمة بينفذ نفس الدالة الأصلية (مفيش منطق جديد).
   - الصفحات تقدر تسجّل قائمة مخصصة:
       PTContextMenu.register('#rBody tr[data-booking-id]', row => [ {label, icon, action, danger}, '-' , ... ])
   - غير كده: القائمة بتعرض أزرار الإجراءات الموجودة في الصف نفسه وتضغطها.
   - الكليك اليمين على input / نص متحدد / عناوين الجدول = قائمة المتصفح العادية (نسخ/لصق).
   ========================================================= */
(function () {
    'use strict';

    const ROW_SELECTOR = 'tbody tr, .booking-card, .list-item, .card[data-ctx]';
    const registry = [];
    let menu = null;
    let currentRow = null;
    let lastFocus = null;

    // تسميات للأزرار اللي عليها أيقونة بس
    const ICON_LABELS = {
        '✏️': 'تعديل', '✎': 'تعديل',
        '🗑️': 'حذف', '🗑': 'حذف',
        '🔍': 'عرض', '◉': 'عرض التفاصيل', '👁': 'عرض', '🖼️': 'عرض الصورة',
        '🖨️': 'طباعة', '📋': 'نسخ / تفاصيل', '⚡': 'Checkout وتسليم',
        '✂️': 'خصم', '💬': 'رسالة', '🔒': 'الصلاحيات / كلمة المرور',
        '🚫': 'إيقاف', '⛔': 'تعطيل', '✅': 'تفعيل / إنهاء', '⋮': 'كل الإجراءات…'
    };
    const DANGER_RE = /حذف|delete|remove|🗑|إيقاف|تعطيل|⛔|🚫|رفض/i;

    function ensureMenu() {
        if (menu) return menu;
        menu = document.createElement('div');
        menu.className = 'pt-ctx-menu';
        menu.setAttribute('role', 'menu');
        menu.setAttribute('aria-label', 'إجراءات');
        document.body.appendChild(menu);

        menu.addEventListener('click', function (e) {
            const btn = e.target.closest('.pt-ctx-item');
            if (!btn || btn.getAttribute('aria-disabled') === 'true') return;
            e.preventDefault();
            e.stopPropagation();
            const fn = btn._ptAction;
            close();
            if (typeof fn === 'function') {
                try { fn(); } catch (err) {
                    console.error('[ContextMenu]', err);
                    if (typeof window.toast === 'function') window.toast(err.message || 'حدث خطأ', 'bad');
                }
            }
        });

        menu.addEventListener('keydown', function (e) {
            const items = Array.from(menu.querySelectorAll('.pt-ctx-item:not([aria-disabled="true"])'));
            const i = items.indexOf(document.activeElement);
            if (e.key === 'ArrowDown') { e.preventDefault(); items[(i + 1) % items.length]?.focus(); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); items[(i - 1 + items.length) % items.length]?.focus(); }
            else if (e.key === 'Home') { e.preventDefault(); items[0]?.focus(); }
            else if (e.key === 'End') { e.preventDefault(); items[items.length - 1]?.focus(); }
            else if (e.key === 'Tab') { close(); }
        });
        return menu;
    }

    function labelFor(btn) {
        const explicit = btn.getAttribute('title') || btn.getAttribute('aria-label') || btn.dataset.label;
        const text = (btn.textContent || '').replace(/\s+/g, ' ').trim();
        if (explicit) return { icon: '', label: explicit.trim() };
        const m = text.match(/^(\p{Extended_Pictographic}\uFE0F?|[◉✎⋮⚡✓✕☐☑])\s*(.*)$/u);
        if (m) return { icon: m[1], label: m[2] || ICON_LABELS[m[1]] || m[1] };
        return { icon: '', label: text };
    }

    function isUsable(el) {
        if (el.disabled || el.getAttribute('aria-disabled') === 'true') return false;
        if (el.closest('[hidden]')) return false;
        const cs = getComputedStyle(el);
        return cs.display !== 'none' && cs.visibility !== 'hidden';
    }

    // القائمة الافتراضية: أزرار الإجراءات الموجودة في الصف
    function itemsFromRow(row) {
        const seen = new Set();
        return Array.from(row.querySelectorAll('button, a.btn, a[role="button"]'))
            .filter(isUsable)
            .map(function (btn) {
                const l = labelFor(btn);
                if (!l.label || seen.has(l.label)) return null;
                seen.add(l.label);
                return {
                    icon: l.icon, label: l.label,
                    danger: DANGER_RE.test(l.label + ' ' + l.icon + ' ' + btn.className),
                    action: function () { btn.click(); }
                };
            })
            .filter(Boolean);
    }

    function findRegistration(target) {
        for (let i = registry.length - 1; i >= 0; i--) {
            const row = target.closest(registry[i].selector);
            if (row) return { row: row, reg: registry[i] };
        }
        return null;
    }

    function render(items, title) {
        const m = ensureMenu();
        m.innerHTML = '';
        if (title) {
            const t = document.createElement('div');
            t.className = 'pt-ctx-title';
            t.textContent = title;
            m.appendChild(t);
        }
        items.forEach(function (it) {
            if (it === '-' || it === null) {
                if (m.lastChild && !m.lastChild.classList.contains('pt-ctx-sep') && !m.lastChild.classList.contains('pt-ctx-title')) {
                    const s = document.createElement('div');
                    s.className = 'pt-ctx-sep';
                    s.setAttribute('role', 'separator');
                    m.appendChild(s);
                }
                return;
            }
            const b = document.createElement('button');
            b.type = 'button';
            b.className = 'pt-ctx-item' + (it.danger ? ' danger' : '');
            b.setAttribute('role', 'menuitem');
            if (it.disabled) b.setAttribute('aria-disabled', 'true');
            const ic = document.createElement('span');
            ic.className = 'pt-ctx-icon';
            ic.textContent = it.icon || '';
            const lb = document.createElement('span');
            lb.textContent = it.label;
            b.append(ic, lb);
            b._ptAction = it.action;
            m.appendChild(b);
        });
        if (m.lastChild && m.lastChild.classList.contains('pt-ctx-sep')) m.lastChild.remove();
    }

    function position(x, y) {
        const m = menu;
        m.style.left = '0px';
        m.style.top = '0px';
        m.classList.add('open');
        // offsetWidth/Height بدل getBoundingClientRect علشان أنيميشن الـ scale ما يلخبطش القياس
        const r = { width: m.offsetWidth, height: m.offsetHeight };
        const pad = 8;
        // RTL: نفتح القائمة لشمال المؤشر، ولو مفيش مكان نفتحها لليمين
        let left = x - r.width;
        if (left < pad) left = x;
        if (left + r.width > window.innerWidth - pad) left = window.innerWidth - r.width - pad;
        let top = y;
        if (top + r.height > window.innerHeight - pad) top = Math.max(pad, y - r.height);
        m.style.left = Math.max(pad, left) + 'px';
        m.style.top = Math.max(pad, top) + 'px';
    }

    function open(e, items, row, title) {
        if (!items || !items.length) return false;
        e.preventDefault();
        lastFocus = document.activeElement;
        render(items, title);
        clearRowMark();
        currentRow = row;
        row?.classList?.add('pt-ctx-target');
        position(e.clientX, e.clientY);
        // لو فتحت بالكيبورد (زر القائمة / Shift+F10) نركّز أول عنصر
        if (e.clientX === 0 && e.clientY === 0) menu.querySelector('.pt-ctx-item')?.focus();
        return true;
    }

    function clearRowMark() {
        currentRow?.classList?.remove('pt-ctx-target');
        currentRow = null;
    }

    function close() {
        if (!menu || !menu.classList.contains('open')) return;
        menu.classList.remove('open');
        clearRowMark();
        if (lastFocus && document.contains(lastFocus) && menu.contains(document.activeElement)) lastFocus.focus?.();
    }

    function targetEl(e) {
        const t = e.target;
        if (t && t.nodeType === 1) return t;
        if (t && t.nodeType === 3) return t.parentElement;
        return null;
    }

    function shouldUseNativeMenu(e, t) {
        if (e.shiftKey && e.type === 'contextmenu' && e.button === 2) return true; // Shift+كليك يمين = قائمة المتصفح
        if (t.closest('input, textarea, select, [contenteditable=""], [contenteditable="true"], .pt-ctx-menu')) return true;
        if (t.closest('thead, tfoot, .modal, .modal-backdrop, #commandOverlay')) return true;
        const sel = window.getSelection && String(window.getSelection() || '');
        if (sel && sel.trim()) return true; // في نص متحدد: سيب النسخ شغال
        return false;
    }

    document.addEventListener('contextmenu', function (e) {
        const t = targetEl(e);
        if (!t || shouldUseNativeMenu(e, t)) { close(); return; }

        const hit = findRegistration(t);
        if (hit) {
            let items = [];
            try { items = hit.reg.build(hit.row, e) || []; } catch (err) { console.error('[ContextMenu]', err); }
            if (open(e, items, hit.row, hit.reg.title ? hit.reg.title(hit.row) : '')) return;
        }

        const row = t.closest(ROW_SELECTOR);
        if (!row || row.querySelector('td[colspan]') && row.children.length === 1) { close(); return; }
        if (!open(e, itemsFromRow(row), row, '')) close();
    });

    document.addEventListener('mousedown', function (e) {
        if (menu && !menu.contains(e.target)) close();
    }, true);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
    window.addEventListener('blur', close);
    window.addEventListener('resize', close);
    document.addEventListener('scroll', function (e) { if (!menu || !menu.contains(e.target)) close(); }, true);

    window.PTContextMenu = {
        /** selector: صفوف تتسجل لها القائمة. build(row, event) => [{label, icon, action, danger, disabled} | '-'] */
        register: function (selector, build, options) {
            registry.push({ selector: selector, build: build, title: options && options.title });
        },
        close: close
    };
    // توافق مع الاسم القديم
    window.PHOTO_TEAM_CONTEXT_MENU_V72 = { init: function () {}, register: window.PTContextMenu.register };
})();
