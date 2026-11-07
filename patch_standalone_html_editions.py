#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path
SHARED_THEME_AND_TOGGLE_BLOCK = '<!-- ==========================================================================\n     🌙☀️ V101 THEME OVERHAUL:\n     1. WHITE & SOFT SKY BLUE SIDEBAR IN LIGHT MODE (NO DARK NAVY IN LIGHT MODE)\n     2. COHESIVE DARK MODE IN MODE 2 (ZERO WHITE PATCHES)\n     3. PURE MODERN SLIDING TOGGLE SWITCH (NO TEXT "نهاري / ليلي")\n     ========================================================================== -->\n<style id="completeDarkModeAndModernToggleCSS">\n/* ============================================================================\n   1. LIGHT MODE (system-mode-1): WHITE & SOFT SKY BLUE SIDEBAR + WELCOME BANNER\n   ============================================================================ */\nhtml body:not(.system-mode-2) #sidebar,\nhtml body:not(.system-mode-2) aside.sidebar,\nhtml body.system-mode-1 #sidebar,\nhtml body.system-mode-1 aside.sidebar {\n  background: linear-gradient(180deg, #ffffff 0%, #f0f7ff 55%, #e0f2fe 100%) !important;\n  border-left: 1px solid #bae6fd !important;\n  box-shadow: -4px 0 22px rgba(37, 99, 235, 0.08) !important;\n  color: #1e3a8a !important;\n}\n\nhtml body:not(.system-mode-2) .sidebar-brand,\nhtml body.system-mode-1 .sidebar-brand {\n  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%) !important;\n  border: 1px solid #bfdbfe !important;\n  border-radius: 12px !important;\n  box-shadow: 0 3px 10px rgba(37, 99, 235, 0.08) !important;\n}\n\nhtml body:not(.system-mode-2) .sidebar-brand .brand-details strong,\nhtml body.system-mode-1 .sidebar-brand .brand-details strong {\n  color: #1e3a8a !important;\n}\n\nhtml body:not(.system-mode-2) .sidebar-brand .brand-details small,\nhtml body.system-mode-1 .sidebar-brand .brand-details small {\n  color: #2563eb !important;\n  font-weight: 700 !important;\n}\n\nhtml body:not(.system-mode-2) #sidebar .nav-group-label span,\nhtml body.system-mode-1 #sidebar .nav-group-label span {\n  color: #2563eb !important;\n  font-weight: 800 !important;\n}\n\nhtml body:not(.system-mode-2) #sidebar nav a,\nhtml body.system-mode-1 #sidebar nav a {\n  background: rgba(255, 255, 255, 0.88) !important;\n  color: #1e3a8a !important;\n  border: 1px solid #dbeafe !important;\n  box-shadow: 0 1px 3px rgba(37, 99, 235, 0.04) !important;\n}\n\nhtml body:not(.system-mode-2) #sidebar nav a .nav-icon-box,\nhtml body.system-mode-1 #sidebar nav a .nav-icon-box {\n  background: #eff6ff !important;\n  color: #2563eb !important;\n  border: 1px solid #bfdbfe !important;\n}\n\nhtml body:not(.system-mode-2) #sidebar nav a:hover,\nhtml body.system-mode-1 #sidebar nav a:hover {\n  background: #dbeafe !important;\n  color: #1d4ed8 !important;\n  border-color: #93c5fd !important;\n  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15) !important;\n  transform: translateX(-2px) !important;\n}\n\nhtml body:not(.system-mode-2) #sidebar nav a.active,\nhtml body.system-mode-1 #sidebar nav a.active {\n  background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%) !important;\n  color: #ffffff !important;\n  border-color: #1d4ed8 !important;\n  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.32) !important;\n}\n\nhtml body:not(.system-mode-2) #sidebar nav a.active .nav-label,\nhtml body.system-mode-1 #sidebar nav a.active .nav-label {\n  color: #ffffff !important;\n}\n\nhtml body:not(.system-mode-2) #sidebar nav a.active .nav-icon-box,\nhtml body.system-mode-1 #sidebar nav a.active .nav-icon-box {\n  background: rgba(255, 255, 255, 0.22) !important;\n  color: #ffffff !important;\n  border-color: rgba(255, 255, 255, 0.4) !important;\n}\n\nhtml body:not(.system-mode-2) #sidebar .sidebar-footer,\nhtml body.system-mode-1 #sidebar .sidebar-footer {\n  background: rgba(255, 255, 255, 0.92) !important;\n  border-top: 1px solid #bae6fd !important;\n  color: #1e3a8a !important;\n}\n\nhtml body:not(.system-mode-2) .dash-welcome,\nhtml body.system-mode-1 .dash-welcome {\n  background: linear-gradient(135deg, #ffffff 0%, #f0f7ff 55%, #dbeafe 100%) !important;\n  border: 1px solid #bae6fd !important;\n  color: #0f172a !important;\n  box-shadow: 0 6px 20px rgba(37, 99, 235, 0.08) !important;\n}\n\nhtml body:not(.system-mode-2) .dash-welcome h1,\nhtml body:not(.system-mode-2) .dash-welcome h2,\nhtml body:not(.system-mode-2) .dash-welcome strong,\nhtml body.system-mode-1 .dash-welcome h1,\nhtml body.system-mode-1 .dash-welcome h2,\nhtml body.system-mode-1 .dash-welcome strong {\n  color: #1e3a8a !important;\n}\n\nhtml body:not(.system-mode-2) .dash-welcome p,\nhtml body:not(.system-mode-2) .dash-welcome small,\nhtml body:not(.system-mode-2) .dash-welcome span:not(.badge),\nhtml body.system-mode-1 .dash-welcome p,\nhtml body.system-mode-1 .dash-welcome small,\nhtml body.system-mode-1 .dash-welcome span:not(.badge) {\n  color: #334155 !important;\n}\n\n/* ============================================================================\n   2. PURE MODERN SLIDING TOGGLE SWITCH (NO TEXT "نهاري / ليلي")\n   ============================================================================ */\nhtml body .dual-mode-top-switcher,\nhtml body .system-mode-switcher {\n  position: relative !important;\n  display: inline-flex !important;\n  align-items: center !important;\n  justify-content: space-between !important;\n  width: 56px !important;\n  min-width: 56px !important;\n  max-width: 56px !important;\n  height: 28px !important;\n  padding: 3px !important;\n  border-radius: 999px !important;\n  background: linear-gradient(135deg, #dbeafe 0%, #93c5fd 100%) !important;\n  border: 1.5px solid #60a5fa !important;\n  box-shadow: inset 0 2px 4px rgba(30, 58, 138, 0.15), 0 2px 8px rgba(37, 99, 235, 0.15) !important;\n  cursor: pointer !important;\n  transition: all 0.28s cubic-bezier(0.16, 1, 0.3, 1) !important;\n  overflow: hidden !important;\n  user-select: none !important;\n}\n\nhtml body.system-mode-2 .dual-mode-top-switcher,\nhtml body.system-mode-2 .system-mode-switcher {\n  background: linear-gradient(135deg, #090d16 0%, #1e293b 100%) !important;\n  border-color: rgba(245, 158, 11, 0.65) !important;\n  box-shadow: 0 0 14px rgba(245, 158, 11, 0.3), inset 0 2px 5px rgba(0, 0, 0, 0.7) !important;\n}\n\n/* Hide ANY text inside the toggle switch buttons — icon-only sliding knob */\nhtml body .dual-mode-top-switcher button span,\nhtml body .system-mode-switcher button span {\n  display: none !important;\n  font-size: 0 !important;\n  width: 0 !important;\n  height: 0 !important;\n  overflow: hidden !important;\n}\n\nhtml body .dual-mode-top-switcher button,\nhtml body .system-mode-switcher button {\n  width: 22px !important;\n  min-width: 22px !important;\n  max-width: 22px !important;\n  height: 22px !important;\n  min-height: 22px !important;\n  max-height: 22px !important;\n  padding: 0 !important;\n  margin: 0 !important;\n  border-radius: 50% !important;\n  border: none !important;\n  display: inline-flex !important;\n  align-items: center !important;\n  justify-content: center !important;\n  font-size: 12px !important;\n  line-height: 1 !important;\n  background: transparent !important;\n  color: #64748b !important;\n  box-shadow: none !important;\n  transition: all 0.28s cubic-bezier(0.16, 1, 0.3, 1) !important;\n}\n\nhtml body.system-mode-1 #btnSwitchMode1,\nhtml body:not(.system-mode-2) #btnSwitchMode1,\nhtml body.system-mode-1 .sys-mode-btn[data-mode="1"],\nhtml body:not(.system-mode-2) .sys-mode-btn[data-mode="1"] {\n  background: #ffffff !important;\n  color: #f59e0b !important;\n  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.25), 0 0 8px rgba(245, 158, 11, 0.35) !important;\n  transform: scale(1.05) !important;\n}\n\nhtml body.system-mode-1 #btnSwitchMode2,\nhtml body:not(.system-mode-2) #btnSwitchMode2,\nhtml body.system-mode-1 .sys-mode-btn[data-mode="2"],\nhtml body:not(.system-mode-2) .sys-mode-btn[data-mode="2"] {\n  background: transparent !important;\n  color: #1e3a8a !important;\n  opacity: 0.55 !important;\n  box-shadow: none !important;\n}\n\nhtml body.system-mode-2 #btnSwitchMode2,\nhtml body.system-mode-2 .sys-mode-btn[data-mode="2"] {\n  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;\n  color: #090d16 !important;\n  box-shadow: 0 0 12px rgba(245, 158, 11, 0.65) !important;\n  transform: scale(1.05) !important;\n}\n\nhtml body.system-mode-2 #btnSwitchMode1,\nhtml body.system-mode-2 .sys-mode-btn[data-mode="1"] {\n  background: transparent !important;\n  color: #94a3b8 !important;\n  opacity: 0.5 !important;\n  box-shadow: none !important;\n}\n\n/* ============================================================================\n   3. COMPLETE DARK MODE (system-mode-2): ZERO WHITE PATCHES ANYWHERE\n   ============================================================================ */\nhtml body.system-mode-2 {\n  --bg-body: #090d16 !important;\n  --bg-card: #111827 !important;\n  --bg-surface-1: #111827 !important;\n  --bg-surface-2: #1e293b !important;\n  --border: #1e293b !important;\n  --border-strong: #334155 !important;\n  --text-main: #f8fafc !important;\n  --text-heading: #ffffff !important;\n  --text-muted: #94a3b8 !important;\n  background-color: #090d16 !important;\n  color: #f8fafc !important;\n}\n\nhtml body.system-mode-2 .app,\nhtml body.system-mode-2 .main,\nhtml body.system-mode-2 .content,\nhtml body.system-mode-2 .view-section,\nhtml body.system-mode-2 .tab-pane {\n  background-color: transparent !important;\n  color: #f8fafc !important;\n}\n\nhtml body.system-mode-2 .header,\nhtml body.system-mode-2 .footer,\nhtml body.system-mode-2 .panel,\nhtml body.system-mode-2 .bento-panel,\nhtml body.system-mode-2 .kpi-card,\nhtml body.system-mode-2 .stat-card,\nhtml body.system-mode-2 .page-heading,\nhtml body.system-mode-2 .toolbar,\nhtml body.system-mode-2 .action-grid,\nhtml body.system-mode-2 .table-wrap,\nhtml body.system-mode-2 .modal-card,\nhtml body.system-mode-2 .command-box,\nhtml body.system-mode-2 .logic-tabs,\nhtml body.system-mode-2 .summary-box,\nhtml body.system-mode-2 .photo-split-preview,\nhtml body.system-mode-2 .detail-row,\nhtml body.system-mode-2 .timeline-card,\nhtml body.system-mode-2 .empty-state,\nhtml body.system-mode-2 .edit-income-banner,\nhtml body.system-mode-2 .dress-item-row,\nhtml body.system-mode-2 .clothing-builder,\nhtml body.system-mode-2 .hotel-perm-grid,\nhtml body.system-mode-2 .permission-grid,\nhtml body.system-mode-2 .form-section {\n  background: #111827 !important;\n  border-color: #1f2937 !important;\n  color: #f8fafc !important;\n}\n\nhtml body.system-mode-2 div[style*="background:#fff"],\nhtml body.system-mode-2 div[style*="background: #fff"],\nhtml body.system-mode-2 div[style*="background:#ffffff"],\nhtml body.system-mode-2 div[style*="background: #ffffff"],\nhtml body.system-mode-2 div[style*="background:#f8fafc"],\nhtml body.system-mode-2 div[style*="background: #f8fafc"],\nhtml body.system-mode-2 div[style*="background:#f1f5f9"],\nhtml body.system-mode-2 div[style*="background: #f1f5f9"],\nhtml body.system-mode-2 div[style*="background:#eff6ff"],\nhtml body.system-mode-2 div[style*="background: #eff6ff"],\nhtml body.system-mode-2 section[style*="background:#fff"],\nhtml body.system-mode-2 section[style*="background: #fff"],\nhtml body.system-mode-2 section[style*="background:#f8fafc"],\nhtml body.system-mode-2 section[style*="background: #f8fafc"],\nhtml body.system-mode-2 aside[style*="background:#f8fafc"],\nhtml body.system-mode-2 aside[style*="background: #f8fafc"] {\n  background: #151f32 !important;\n  border-color: #334155 !important;\n  color: #f8fafc !important;\n}\n\nhtml body.system-mode-2 input,\nhtml body.system-mode-2 select,\nhtml body.system-mode-2 textarea,\nhtml body.system-mode-2 .input {\n  background: #0b1120 !important;\n  border: 1px solid #334155 !important;\n  color: #f8fafc !important;\n}\n\nhtml body.system-mode-2 table,\nhtml body.system-mode-2 .modern-table {\n  background: #111827 !important;\n  color: #f8fafc !important;\n}\n\nhtml body.system-mode-2 table thead th,\nhtml body.system-mode-2 .modern-table thead th {\n  background: #0b1120 !important;\n  color: #fbbf24 !important;\n  border-bottom: 1px solid #334155 !important;\n}\n\nhtml body.system-mode-2 table tbody tr,\nhtml body.system-mode-2 table tbody td {\n  background: #111827 !important;\n  color: #e2e8f0 !important;\n  border-bottom: 1px solid #1e293b !important;\n}\n\nhtml body.system-mode-2 table tbody tr:nth-child(even) td {\n  background: #0f172a !important;\n}\n\nhtml body.system-mode-2 table tbody tr:hover td {\n  background: rgba(245, 158, 11, 0.08) !important;\n}\n\nhtml body.system-mode-2 h1,\nhtml body.system-mode-2 h2,\nhtml body.system-mode-2 h3,\nhtml body.system-mode-2 h4,\nhtml body.system-mode-2 strong,\nhtml body.system-mode-2 b,\nhtml body.system-mode-2 label {\n  color: #f8fafc !important;\n}\n\nhtml body.system-mode-2 .header .user {\n  background: #151f32 !important;\n  border-color: #334155 !important;\n  color: #f8fafc !important;\n}\n\nhtml body.system-mode-2 #notificationButton,\nhtml body.system-mode-2 #headerChatQuickBtn,\nhtml body.system-mode-2 .header .notification-trigger {\n  background: #151f32 !important;\n  color: #fbbf24 !important;\n  border: 1px solid rgba(245, 158, 11, 0.45) !important;\n}\n\n/* Compact Daily Income Notes Bar */\n.compact-notes-bar {\n  padding: 6px 12px !important;\n  margin-bottom: 10px !important;\n  border-radius: 10px !important;\n}\n</style>\n\n<script id="modernThemeToggleUpgraderJS">\n(function() {\n  const SUN_SVG = \'<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>\';\n  const MOON_SVG = \'<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>\';\n\n  function stylePureSlidingToggle() {\n    const b1 = document.getElementById(\'btnSwitchMode1\');\n    const b2 = document.getElementById(\'btnSwitchMode2\');\n    if (b1) {\n      b1.innerHTML = SUN_SVG;\n      b1.removeAttribute(\'style\');\n    }\n    if (b2) {\n      b2.innerHTML = MOON_SVG;\n      b2.removeAttribute(\'style\');\n    }\n    document.querySelectorAll(\'.sys-mode-btn[data-mode="1"]\').forEach(el => { el.innerHTML = SUN_SVG; });\n    document.querySelectorAll(\'.sys-mode-btn[data-mode="2"]\').forEach(el => { el.innerHTML = MOON_SVG; });\n\n    // Make clicking anywhere on the toggle track flip between Mode 1 and Mode 2\n    document.querySelectorAll(\'.dual-mode-top-switcher, .system-mode-switcher\').forEach(sw => {\n      if (sw.dataset.toggleBound === \'1\') return;\n      sw.dataset.toggleBound = \'1\';\n      sw.addEventListener(\'click\', function(ev) {\n        ev.preventDefault();\n        ev.stopPropagation();\n        const isDark = document.body.classList.contains(\'system-mode-2\');\n        const nextMode = isDark ? 1 : 2;\n        if (typeof window.switchMainSystemMode === \'function\') {\n          window.switchMainSystemMode(nextMode);\n        } else if (typeof window.switchMobileSystemMode === \'function\') {\n          window.switchMobileSystemMode(nextMode);\n        }\n        setTimeout(stylePureSlidingToggle, 20);\n      }, true);\n    });\n  }\n\n  document.addEventListener(\'DOMContentLoaded\', function() {\n    stylePureSlidingToggle();\n    setTimeout(stylePureSlidingToggle, 200);\n    setTimeout(stylePureSlidingToggle, 600);\n  });\n})();\n</script>'

ROOT = Path("/working_dir/c_0788515bf7bf9bd8/project_src")

STANDALONE_JS_OVERRIDES = '''
<!-- ==========================================================================
     🚀 V101 UNIFIED FIXES FOR STANDALONE HTML EDITIONS:
     1. Fixed Create New Account (Register), Change Password (Reset), & Login
     2. Unified Official Daily Report & All-Hotels Multi-Page PDF Report
        (Exact same layout, zero fake deposits in hotels without deposits,
         and Coin Safe movements filtered strictly to the single report day)
     3. Modern Formatted RTL Excel Spreadsheet (.xls) Exports
     4. Compact Collapsible Daily Income Notes Bar
     ========================================================================== -->
<script id="v101StandaloneComprehensiveFixesJS">
(function() {
  // --------------------------------------------------------------------------
  // 1. Clean DB.deposits so hotels without deposits have 0 deposits
  // --------------------------------------------------------------------------
  if (window.DB && Array.isArray(window.DB.deposits)) {
    window.DB.deposits = window.DB.deposits.filter(d =>
      d && d.hotel_name && (d.hotel_name === 'Albatros Aqua Park' || d.hotel_name === 'Sea World Resort')
    );
  }

  // --------------------------------------------------------------------------
  // 2. Fix Auth Overlay: Tab Switching, Login, Create Account, & Change Password
  // --------------------------------------------------------------------------
  window.switchLoginPreviewTab = function(tabName) {
    const fb = document.getElementById('lpAuthFeedback');
    if (fb) { fb.hidden = true; fb.style.display = 'none'; }
    document.querySelectorAll('.lp-tab-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.lpTab === tabName);
    });
    const map = {
      login: document.getElementById('lpFormLogin'),
      register: document.getElementById('lpFormRegister'),
      reset: document.getElementById('lpFormReset')
    };
    Object.entries(map).forEach(([k, el]) => {
      if (!el) return;
      const isTarget = (k === tabName);
      el.hidden = !isTarget;
      el.style.display = isTarget ? 'flex' : 'none';
    });
  };

  function showLpMsg(msg, isGood = false) {
    const fb = document.getElementById('lpAuthFeedback');
    if (!fb) {
      if (typeof toast === 'function') toast(msg, isGood ? 'good' : 'bad');
      return;
    }
    fb.hidden = false;
    fb.style.display = 'block';
    fb.textContent = msg;
    fb.style.background = isGood ? 'rgba(16, 185, 129, 0.16)' : 'rgba(239, 68, 68, 0.16)';
    fb.style.border = isGood ? '1px solid rgba(16, 185, 129, 0.45)' : '1px solid rgba(239, 68, 68, 0.45)';
    fb.style.color = isGood ? '#059669' : '#e11d48';
  }

  window.submitFullLoginOverlay = function() {
    const u = (document.getElementById('lpUsername')?.value || '').trim();
    const p = (document.getElementById('lpPassword')?.value || '').trim();
    if (!u || !p) {
      showLpMsg('يرجى إدخال اسم المستخدم وكلمة المرور', false);
      return;
    }
    const team = (window.DB && Array.isArray(window.DB.team)) ? window.DB.team : [];
    const matched = team.find(m =>
      String(m.username || '').toLowerCase() === u.toLowerCase() ||
      String(m.nickname || '').toLowerCase() === u.toLowerCase() ||
      String(m.full_name || '').toLowerCase() === u.toLowerCase()
    );
    if (!matched) {
      showLpMsg('اسم المستخدم غير موجود — يمكنك إنشاء حساب جديد من تبويب (إنشاء حساب جديد)', false);
      return;
    }
    if (matched.password && String(matched.password) !== p) {
      showLpMsg('كلمة المرور غير صحيحة — يمكنك استعادتها من تبويب (تغيير كلمة المرور)', false);
      return;
    }
    const role = matched.role || 'CEO';
    if (typeof applySimulatedRole === 'function') {
      applySimulatedRole(role, matched.nickname || matched.username || u, [matched.hotel_name || 'Albatros Aqua Park']);
    }
    if (typeof closeFullLoginOverlay === 'function') closeFullLoginOverlay();
    if (typeof toast === 'function') toast(`🔓 مرحباً بك ${matched.full_name || matched.nickname || u} (${role})`);
  };

  window.submitFullRegisterOverlay = function() {
    const fullName = (document.getElementById('lpRegFullName')?.value || '').trim();
    const username = (document.getElementById('lpRegUsername')?.value || '').trim();
    const role = document.getElementById('lpRegRole')?.value || 'Photographer';
    const hotel = document.getElementById('lpRegHotel')?.value || 'Albatros Aqua Park';
    const phone = (document.getElementById('lpRegPhone')?.value || '').trim();
    const nid = (document.getElementById('lpRegNationalId')?.value || '').trim();
    const pass = (document.getElementById('lpRegPass')?.value || '').trim();

    if (!fullName || fullName.length < 2) {
      showLpMsg('يرجى كتابة الاسم بالكامل', false);
      return;
    }
    if (!username) {
      showLpMsg('يرجى إدخال اسم المستخدم (اسم الشهرة)', false);
      return;
    }
    if (!phone || phone.replace(/\\D/g, '').length < 6) {
      showLpMsg('يرجى إدخال رقم الهاتف بشكل صحيح', false);
      return;
    }
    if (!nid || nid.replace(/\\D/g, '').length < 4) {
      showLpMsg('يرجى إدخال رقم البطاقة / الهوية', false);
      return;
    }
    if (!pass || pass.length < 4) {
      showLpMsg('يرجى اختيار كلمة مرور لا تقل عن 4 أحرف أو أرقام', false);
      return;
    }

    window.DB = window.DB || {};
    window.DB.team = window.DB.team || [];
    const exists = window.DB.team.find(m =>
      String(m.username || '').toLowerCase() === username.toLowerCase() ||
      String(m.nickname || '').toLowerCase() === username.toLowerCase()
    );
    if (exists) {
      showLpMsg('اسم المستخدم مسجل بالفعل — اختر اسماً آخر أو استخدم تبويب (تغيير كلمة المرور)', false);
      return;
    }

    const newMember = {
      id: Date.now(),
      full_name: fullName,
      nickname: username,
      username: username,
      password: pass,
      role: role,
      commission_rate: role === 'Photographer' ? 12 : (role === 'Sales' ? 10 : 0),
      base_salary: 0,
      hotel_name: hotel,
      phone_number: phone,
      national_id: nid,
      is_active: 1
    };
    window.DB.team.push(newMember);

    showLpMsg(`✅ تم إنشاء حساب (${username}) بنجاح! جاري الدخول للنظام...`, true);
    setTimeout(() => {
      if (typeof applySimulatedRole === 'function') {
        applySimulatedRole(role, username, [hotel]);
      }
      if (typeof renderTeamHotelsView === 'function') renderTeamHotelsView();
      if (typeof closeFullLoginOverlay === 'function') closeFullLoginOverlay();
      if (typeof toast === 'function') toast(`🎉 مرحباً بك ${fullName}! تم إنشاء حسابك وتسجيل دخولك بنجاح`);
    }, 350);
  };

  window.submitFullResetOverlay = function() {
    const username = (document.getElementById('lpRstUsername')?.value || '').trim();
    const nid = (document.getElementById('lpRstNationalId')?.value || '').trim().replace(/\\D/g, '');
    const phone = (document.getElementById('lpRstPhone')?.value || '').trim().replace(/\\D/g, '');
    const p1 = (document.getElementById('lpRstPass1')?.value || '').trim();
    const p2 = (document.getElementById('lpRstPass2')?.value || '').trim();

    if (!username) {
      showLpMsg('يرجى إدخال اسم المستخدم أو اسم الشهرة', false);
      return;
    }
    if (!p1 || p1.length < 4) {
      showLpMsg('يرجى إدخال كلمة مرور جديدة لا تقل عن 4 أحرف أو أرقام', false);
      return;
    }
    if (p1 !== p2) {
      showLpMsg('كلمة المرور الجديدة وتأكيدها غير متطابقين', false);
      return;
    }

    const team = (window.DB && Array.isArray(window.DB.team)) ? window.DB.team : [];
    const matched = team.find(m =>
      String(m.username || '').toLowerCase() === username.toLowerCase() ||
      String(m.nickname || '').toLowerCase() === username.toLowerCase() ||
      String(m.full_name || '').toLowerCase() === username.toLowerCase()
    );
    if (!matched) {
      showLpMsg('اسم المستخدم / الشهرة غير موجود في النظام', false);
      return;
    }

    const dbPhone = String(matched.phone_number || '').replace(/\\D/g, '');
    const dbNid = String(matched.national_id || '').replace(/\\D/g, '');
    const phoneMatch = !dbPhone || !phone || dbPhone === phone || dbPhone.endsWith(phone.slice(-8)) || phone.endsWith(dbPhone.slice(-8));
    const nidMatch = !dbNid || !nid || dbNid === nid || dbNid.endsWith(nid.slice(-6));

    if (!phoneMatch && !nidMatch) {
      showLpMsg('بيانات التحقق (رقم البطاقة أو رقم الهاتف) غير مطابقة لاسم المستخدم', false);
      return;
    }

    matched.password = p1;
    if (phone) matched.phone_number = phone;
    if (nid) matched.national_id = nid;

    window.switchLoginPreviewTab('login');
    if (document.getElementById('lpUsername')) document.getElementById('lpUsername').value = matched.username || matched.nickname;
    if (document.getElementById('lpPassword')) document.getElementById('lpPassword').value = p1;
    showLpMsg(`✅ تم تحديث كلمة المرور لحساب (${matched.nickname || username}) بنجاح! اضغط دخول الآن.`, true);
    if (typeof toast === 'function') toast(`🔑 تم تغيير كلمة المرور لحساب (${matched.nickname || username}) بنجاح!`);
  };

  window.openQuickChangePasswordModalPreview = function() {
    const sc = window.ACTIVE_SIM_SCOPE || { role: 'CEO', empName: 'Bassem' };
    const currentName = sc.empName || 'Bassem';
    showModal(`
      <div class="modal-title">
        <div>
          <h2>🔑 تغيير كلمة المرور الخاصة بالحساب (${esc(currentName)})</h2>
          <p>أدخل كلمة المرور الجديدة لحسابك وسيتم تحديثها فوراً</p>
        </div>
        <button type="button" class="btn" onclick="closeModal()">إغلاق</button>
      </div>
      <form id="previewSelfChangePassForm" style="display:flex;flex-direction:column;gap:12px;">
        <div class="field">
          <label>اسم المستخدم / الحساب</label>
          <input class="input" type="text" id="pscpUser" value="${esc(currentName)}" required>
        </div>
        <div class="field">
          <label>كلمة المرور الجديدة *</label>
          <input class="input" type="password" id="pscpNewPass" placeholder="4 أحرف أو أرقام على الأقل" required minlength="4">
        </div>
        <div class="field">
          <label>تأكيد كلمة المرور الجديدة *</label>
          <input class="input" type="password" id="pscpConfirmPass" placeholder="أعد كتابة كلمة المرور الجديدة" required minlength="4">
        </div>
        <div class="modal-actions">
          <button type="submit" class="btn green">💾 حفظ كلمة المرور الجديدة</button>
          <button type="button" class="btn" onclick="closeModal()">إلغاء</button>
        </div>
      </form>
    `, 'modal-md');
    document.getElementById('previewSelfChangePassForm')?.addEventListener('submit', function(ev) {
      ev.preventDefault();
      const uname = (document.getElementById('pscpUser')?.value || '').trim();
      const p1 = (document.getElementById('pscpNewPass')?.value || '').trim();
      const p2 = (document.getElementById('pscpConfirmPass')?.value || '').trim();
      if (p1.length < 4) return toast('كلمة المرور يجب ألا تقل عن 4 أحرف أو أرقام', 'bad');
      if (p1 !== p2) return toast('كلمة المرور وتأكيدها غير متطابقين', 'bad');
      const m = (window.DB?.team || []).find(x =>
        String(x.nickname || '').toLowerCase() === uname.toLowerCase() ||
        String(x.username || '').toLowerCase() === uname.toLowerCase()
      );
      if (m) m.password = p1;
      closeModal();
      toast(`✅ تم تحديث كلمة المرور لحساب (${uname}) بنجاح!`);
    });
  };

  // --------------------------------------------------------------------------
  // 3. Modern Formatted RTL Excel Spreadsheet (.xls) Exporter
  // --------------------------------------------------------------------------
  window.buildModernExcelSpreadsheetHtml = function(titleText, headers = [], rows = []) {
    const safeHeaders = (headers || []).map(h => String(h ?? ''));
    const safeRows = Array.isArray(rows) ? rows : [];
    const colSums = safeHeaders.map(() => 0);
    const colHasNumeric = safeHeaders.map(() => false);

    safeRows.forEach(r => {
      (r || []).forEach((cell, idx) => {
        if (idx === 0) return;
        const hName = String(safeHeaders[idx] || '');
        if (hName.includes('غرفة') || hName.includes('تاريخ') || hName.includes('تليفون') || hName.includes('هاتف') || hName.includes('نسبة') || hName.includes('الريت')) return;
        const cleaned = String(cell ?? '').replace(/[,$€£EGPLE%\\s]/gi, '').trim();
        if (cleaned !== '' && !isNaN(Number(cleaned)) && /^-?\\d+(\\.\\d+)?$/.test(cleaned)) {
          colSums[idx] += Number(cleaned);
          colHasNumeric[idx] = true;
        }
      });
    });

    const hasAnySum = colHasNumeric.some(Boolean);
    const headerCellsHtml = safeHeaders.map(h =>
      `<th style="background-color:#1e3a8a;color:#ffffff;font-weight:bold;font-size:11.5pt;padding:10px 12px;border:1px solid #1e40af;text-align:center;">${esc(h)}</th>`
    ).join('');

    const bodyRowsHtml = safeRows.map((r, rIdx) => {
      const bg = rIdx % 2 === 0 ? '#ffffff' : '#f1f5f9';
      const tds = (r || []).map((cell, cIdx) => {
        const s = String(cell ?? '');
        const isMoney = s.includes('$') || s.includes('€') || s.includes('LE') || colHasNumeric[cIdx];
        const color = isMoney ? '#0f766e' : '#0f172a';
        const weight = (cIdx <= 2 || isMoney) ? 'bold' : 'normal';
        return `<td style="background-color:${bg};color:${color};font-weight:${weight};font-size:10.5pt;padding:8px 10px;border:1px solid #cbd5e1;text-align:center;">${esc(s)}</td>`;
      }).join('');
      return `<tr>${tds}</tr>`;
    }).join('');

    const footerRowHtml = hasAnySum ? `
      <tr>
        ${safeHeaders.map((_, cIdx) => {
          if (cIdx === 0) {
            return `<td style="background-color:#dbeafe;color:#1e3a8a;font-weight:bold;font-size:11pt;padding:10px;border:2px solid #2563eb;text-align:center;">الإجمالي</td>`;
          }
          if (colHasNumeric[cIdx]) {
            return `<td style="background-color:#ecfdf5;color:#047857;font-weight:bold;font-size:11pt;padding:10px;border:2px solid #10b981;text-align:center;">${money(colSums[cIdx])}</td>`;
          }
          return `<td style="background-color:#dbeafe;color:#64748b;font-weight:bold;padding:10px;border:1px solid #93c5fd;text-align:center;">—</td>`;
        }).join('')}
      </tr>
    ` : '';

    const colCount = Math.max(safeHeaders.length, 1);
    return `<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40" dir="rtl" lang="ar">
<head>
<meta charset="utf-8">
<!--[if gte mso 9]><xml><x:ExcelWorkbook><x:ExcelWorksheets><x:ExcelWorksheet><x:Name>PHOTO TEAM</x:Name><x:WorksheetOptions><x:DisplayRightToLeft/><x:DisplayGridlines/></x:WorksheetOptions></x:ExcelWorksheet></x:ExcelWorksheets></x:ExcelWorkbook></xml><![endif]-->
<style>
  body, table, th, td { font-family: 'Cairo', 'Segoe UI', Tahoma, Arial, sans-serif; direction: rtl; }
  table { border-collapse: collapse; width: 100%; }
</style>
</head>
<body>
  <table>
    <tr>
      <td colspan="${colCount}" style="background-color:#0f172a;color:#ffffff;font-size:15pt;font-weight:bold;padding:14px;text-align:center;border:1px solid #0f172a;">
        📸 PHOTO TEAM STUDIO SYSTEM — ${esc(titleText)}
      </td>
    </tr>
    <tr>
      <td colspan="${colCount}" style="background-color:#eff6ff;color:#1e3a8a;font-size:10.5pt;font-weight:bold;padding:8px 12px;text-align:center;border:1px solid #bfdbfe;">
        تاريخ الاستخراج: ${todayISO()} • إجمالي السجلات: ${safeRows.length} سجل
      </td>
    </tr>
    <tr>${headerCellsHtml}</tr>
    ${bodyRowsHtml}
    ${footerRowHtml}
  </table>
</body>
</html>`;
  };

  window.downloadPreviewCSV = function(filename, headers = [], rows = []) {
    const baseStem = String(filename || 'PhotoTeam_Export').replace(/\\.(csv|xls|xlsx)$/i, '');
    const xlsFilename = `${baseStem}.xls`;
    const styledExcelHtml = window.buildModernExcelSpreadsheetHtml(baseStem.replace(/_/g, ' '), headers, rows);
    try {
      const blob = new Blob(['\\ufeff' + styledExcelHtml], { type: 'application/vnd.ms-excel;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = xlsFilename;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        URL.revokeObjectURL(url);
        a.remove();
      }, 2000);
    } catch (e) {}
    if (typeof toast === 'function') toast(`📥 تم تصدير شيت الإكسيل المودرن المنسق (${xlsFilename}) بنجاح`);
  };
  window.downloadCSV = window.downloadPreviewCSV;

  // --------------------------------------------------------------------------
  // 4. Unified Official Daily Report & All-Hotels Multi-Page PDF Report
  // --------------------------------------------------------------------------
  const OFFICIAL_DAILY_REPORT_CSS_PREVIEW = `
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

  function buildOfficialDailyReportSectionPreview({
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

    let dep_equiv = 0;
    dRows.forEach(d => {
      dep_equiv += (num(d.deposit_usd) + num(d.deposit_eur) + ((num(d.deposit_le_cash) + num(d.deposit_le_visa)) / 50));
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
      return `<tr>
        <td>${esc((r.income_date || '').substring(0, 10))}</td>
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
      return `<tr>
        <td>${r.transaction_id || r.id || '-'}</td>
        <td dir="ltr">${esc((r.created_at || '').substring(0, 16))}</td>
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
            <th>#</th><th>التاريخ</th><th>نوع الحركة</th><th>الطرف / الجهة</th><th>البيان</th><th>الأثر على الصافي ($)</th>
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

  window.printSalesReportPreview = function() {
    const hFilter = document.getElementById('dsHotel')?.value || '';
    const start = document.getElementById('dsStart')?.value || '2026-10-01';
    const end = document.getElementById('dsEnd')?.value || '2026-10-14';
    const targetDay = document.getElementById('dsEnd')?.value || document.getElementById('dsEntryDate')?.value || '2026-10-14';

    const allSales = typeof getPreviewScopedSales === 'function' ? getPreviewScopedSales() : (window.DB?.daily_sales || []);
    const sRows = allSales.filter(s => !hFilter || String(s.hotel_name || '').trim() === hFilter);
    const dRows = (window.DB?.deposits || []).filter(d => {
      if ((num(d.deposit_usd) + num(d.deposit_eur) + num(d.deposit_le_cash) + num(d.deposit_le_visa)) <= 0) return false;
      if (!hFilter) return Boolean(d.hotel_name);
      return String(d.hotel_name || '').trim() === hFilter;
    });
    const nRows = (typeof getScopedDailyIncomeNotesPreview === 'function' ? getScopedDailyIncomeNotesPreview() : (window.DB?.daily_income_notes || [])).filter(n => !hFilter || String(n.hotel_name || '').trim() === hFilter);
    const cRowsToday = (window.DB?.coin_safe || []).filter(c => {
      const sameDay = String(c.created_at || '').substring(0, 10) === targetDay;
      const sameHotel = !hFilter || String(c.hotel_id || c.hotel_name || '').trim() === hFilter;
      return sameDay && sameHotel;
    });

    const bodyHtml = buildOfficialDailyReportSectionPreview({
      titleLabel: `التقرير اليومي الشامل — ${hFilter || 'جميع الفنادق'}`,
      subtitleLabel: 'قسم الدخل اليومي والعرابين وحركات خزنة الكوين لليوم',
      start,
      end,
      targetDay,
      sRows,
      dRows,
      cRowsToday,
      nRows
    });

    const fullDoc = `<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>التقرير اليومي الشامل</title><style>${OFFICIAL_DAILY_REPORT_CSS_PREVIEW}</style></head><body>${bodyHtml}</body></html>`;
    if (typeof openPreviewBuiltInReportViewer === 'function') {
      openPreviewBuiltInReportViewer(fullDoc, `التقرير اليومي الشامل (${hFilter || 'جميع الفنادق'})`);
    } else if (typeof triggerPreviewDirectPrint === 'function') {
      triggerPreviewDirectPrint(fullDoc, 'A4 landscape');
    }
  };
  window.printSalesReport = window.printSalesReportPreview;

  window.printAllHotelsMultiPageReportPDF = function() {
    const start = document.getElementById('dsStart')?.value || '2026-10-01';
    const end = document.getElementById('dsEnd')?.value || '2026-10-14';
    const targetDay = document.getElementById('dsEnd')?.value || document.getElementById('dsEntryDate')?.value || '2026-10-14';

    const hotelsList = (window.DB?.hotels || []).map(h => h.hotel_name);
    const allSales = window.DB?.daily_sales || [];
    const allDeposits = (window.DB?.deposits || []).filter(d => (num(d.deposit_usd) + num(d.deposit_eur) + num(d.deposit_le_cash) + num(d.deposit_le_visa)) > 0);
    const allNotes = window.DB?.daily_income_notes || [];
    const allCoinToday = (window.DB?.coin_safe || []).filter(c => String(c.created_at || '').substring(0, 10) === targetDay);

    const hStats = hotelsList.map(hName => {
      const cleanName = String(hName || '').trim();
      const hs = allSales.filter(s => String(s.hotel_name || '').trim() === cleanName);
      // مطابقة صارمة لاسم الفندق فقط — الفنادق التي ليس بها عربون يظهر بها 0 عربون
      const hd = allDeposits.filter(d => String(d.hotel_name || '').trim() === cleanName);
      const hn = allNotes.filter(n => String(n.hotel_name || '').trim() === cleanName);
      const hcToday = allCoinToday.filter(c => String(c.hotel_id || c.hotel_name || '').trim() === cleanName);

      const gross = hs.reduce((a, r) => a + num(r.gross_total), 0);
      const cost = hs.reduce((a, r) => a + num(r.cost_total), 0);
      const net = hs.reduce((a, r) => a + num(r.daily_total), 0);
      const dep = hd.reduce((a, d) => a + num(d.deposit_usd) + num(d.deposit_eur) + ((num(d.deposit_le_cash) + num(d.deposit_le_visa)) / 50), 0);
      const nIn = hn.filter(n => String(n.note_type || '').toUpperCase() === 'IN').reduce((a, n) => a + num(n.equivalent_usd), 0);
      const nOut = hn.filter(n => String(n.note_type || '').toUpperCase() !== 'IN').reduce((a, n) => a + num(n.equivalent_usd), 0);
      const finalNet = net + nIn - nOut;
      return { hName: cleanName, hs, hd, hn, hcToday, gross, cost, net, dep, notesDiff: nIn - nOut, finalNet };
    });

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

    const page1OverviewHtml = buildOfficialDailyReportSectionPreview({
      titleLabel: 'التقرير المالي المجمع لجميع الفنادق (الإجمالي العام)',
      subtitleLabel: `الصفحة الأولى: ملخص وإجمالي جميع الفنادق (${hStats.length} فنادق) — يليه صفحة مستقلة لكل فندق بنفس تصميم التقرير اليومي`,
      start,
      end,
      targetDay,
      sRows: allSales,
      dRows: allDeposits,
      cRowsToday: allCoinToday,
      nRows: allNotes,
      pageBadge: `صفحة 1 من ${hStats.length + 1}`
    });

    const perHotelPagesHtml = hStats.map((st, idx) => `
      <div class="report-page-break">
        ${buildOfficialDailyReportSectionPreview({
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

    const fullDoc = `<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>تقرير كل الفنادق الشامل</title><style>${OFFICIAL_DAILY_REPORT_CSS_PREVIEW}</style></head><body>
      ${page1ComparisonTable}
      ${page1OverviewHtml}
      ${perHotelPagesHtml}
    </body></html>`;

    if (typeof openPreviewBuiltInReportViewer === 'function') {
      openPreviewBuiltInReportViewer(fullDoc, `تقرير كل الفنادق الشامل (${hStats.length} فنادق)`);
    } else if (typeof triggerPreviewDirectPrint === 'function') {
      triggerPreviewDirectPrint(fullDoc, 'A4 landscape');
    }
  };
  window.printAllHotelsReportPDF = window.printAllHotelsMultiPageReportPDF;

  // --------------------------------------------------------------------------
  // 5. Make Daily Income Notes Panels Compact & Collapsible + Add Change Password Button
  // --------------------------------------------------------------------------
  function compactifyNotesPanelsAndHeader() {
    ['dinEntrySummaryPanel', 'dinSearchSummaryPanel', 'dailyIncomeNotesPanel'].forEach(pid => {
      const panel = document.getElementById(pid);
      if (!panel || panel.dataset.compactified === '1') return;
      panel.dataset.compactified = '1';
      panel.classList.add('compact-notes-bar');
      panel.style.cssText = 'grid-column:1/-1;padding:6px 12px !important;margin:6px 0 10px !important;border:1px solid var(--border-strong);border-radius:10px;';
      const head = panel.querySelector('.panel-head');
      const wrap = panel.querySelector('.table-wrap');
      if (head) {
        head.style.marginBottom = '0';
        const h2 = head.querySelector('h2');
        if (h2) {
          h2.style.fontSize = '13px';
          h2.textContent = '📝 ملاحظات الصادر والوارد (اختياري)';
          if (!head.querySelector('.toggle-notes-tbl-btn')) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'mini-btn blue toggle-notes-tbl-btn';
            btn.style.cssText = 'margin-right:8px;padding:2px 8px;font-size:11px;';
            btn.textContent = '📂 عرض السجل';
            btn.onclick = function() {
              if (!wrap) return;
              wrap.hidden = !wrap.hidden;
              wrap.style.display = wrap.hidden ? 'none' : 'block';
              btn.textContent = wrap.hidden ? '📂 عرض السجل' : '🔼 إخفاء السجل';
            };
            h2.parentNode.style.display = 'flex';
            h2.parentNode.style.alignItems = 'center';
            h2.parentNode.appendChild(btn);
          }
        }
      }
      if (wrap) {
        wrap.hidden = true;
        wrap.style.display = 'none';
        wrap.style.marginTop = '8px';
        wrap.style.maxHeight = '160px';
      }
    });

    // Update register form labels inside #loginPreviewModal
    const regNameInput = document.getElementById('lpRegFullName');
    if (regNameInput) {
      regNameInput.placeholder = 'اكتب اسمك بالكامل...';
      const lbl = regNameInput.previousElementSibling;
      if (lbl && lbl.tagName === 'LABEL') lbl.textContent = 'الاسم بالكامل *';
    }
    const regRoleSelect = document.getElementById('lpRegRole');
    if (regRoleSelect && !regRoleSelect.innerHTML.includes('Accountant')) {
      regRoleSelect.innerHTML = `
        <option value="Photographer">📸 مصور (Photographer)</option>
        <option value="Sales">💼 سيلز (Sales)</option>
        <option value="Accountant">🧮 محاسب (Accountant)</option>
        <option value="Manager">🏨 مدير فرع (Manager)</option>
      `;
    }

    // Add quick Change Password button in header if not present
    const logoutBtn = document.querySelector('.logout-pill-btn[onclick*="openFullLoginOverlay"]');
    if (logoutBtn && !document.getElementById('quickSelfPassBtn')) {
      const passBtn = document.createElement('button');
      passBtn.id = 'quickSelfPassBtn';
      passBtn.type = 'button';
      passBtn.className = 'logout-pill-btn';
      passBtn.title = 'تغيير كلمة المرور';
      passBtn.style.cssText = 'background:#eff6ff;color:#2563eb;border-color:#bfdbfe;';
      passBtn.textContent = '🔑';
      passBtn.onclick = function(ev) {
        ev.stopPropagation();
        window.openQuickChangePasswordModalPreview();
      };
      logoutBtn.parentNode.insertBefore(passBtn, logoutBtn);
    }
  }

  document.addEventListener('DOMContentLoaded', function() {
    compactifyNotesPanelsAndHeader();
    setTimeout(compactifyNotesPanelsAndHeader, 300);
  });
})();
</script>
'''

html_files = [
    ROOT / "PhotoTeam_Desktop_Edition.html",
    ROOT / "PhotoTeam_Mobile_Edition.html",
    ROOT / "PhotoTeam_Interactive_System_V90.html",
]

old_toggle_pattern = re.compile(
    r'<!-- ==========================================================================\s*🌙 COMPLETE DARK MODE OVERHAUL.*?</script>',
    re.DOTALL
)
old_v101_pattern = re.compile(
    r'<!-- ==========================================================================\s*🌙☀️ V101 THEME OVERHAUL:.*?</script>\s*(?:<!-- ==========================================================================\s*🚀 V101 UNIFIED FIXES.*?</script>)?',
    re.DOTALL
)

for hf in html_files:
    if not hf.exists():
        continue
    content = hf.read_text(encoding="utf-8")
    combined_block = SHARED_THEME_AND_TOGGLE_BLOCK + "\n" + STANDALONE_JS_OVERRIDES
    if old_v101_pattern.search(content):
        content = old_v101_pattern.sub(lambda m: combined_block, content, count=1)
    elif old_toggle_pattern.search(content):
        content = old_toggle_pattern.sub(lambda m: combined_block, content, count=1)
    else:
        content = content.replace("</body>", combined_block + "\n</body>")
    hf.write_text(content, encoding="utf-8")
    print(f"✅ Updated {hf.name}")
