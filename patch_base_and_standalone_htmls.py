#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

ROOT = Path("/working_dir/c_0788515bf7bf9bd8/project_src")

# ============================================================================
# SHARED CSS + JS FOR:
# 1. Pure Sliding Toggle Switch (NO "نهاري" / "ليلي" text - toggle switch only)
# 2. Light Mode White & Soft Light Blue Sidebar + Welcome Banner (NO dark navy in Light Mode)
# 3. Full Dark Mode coverage (Zero white patches in Dark Mode)
# 4. Compact Daily Income Notes Bar
# ============================================================================
SHARED_THEME_AND_TOGGLE_BLOCK = '''<!-- ==========================================================================
     🌙☀️ V101 THEME OVERHAUL:
     1. WHITE & SOFT SKY BLUE SIDEBAR IN LIGHT MODE (NO DARK NAVY IN LIGHT MODE)
     2. COHESIVE DARK MODE IN MODE 2 (ZERO WHITE PATCHES)
     3. PURE MODERN SLIDING TOGGLE SWITCH (NO TEXT "نهاري / ليلي")
     ========================================================================== -->
<style id="completeDarkModeAndModernToggleCSS">
/* ============================================================================
   1. LIGHT MODE (system-mode-1): WHITE & SOFT SKY BLUE SIDEBAR + WELCOME BANNER
   ============================================================================ */
html body:not(.system-mode-2) #sidebar,
html body:not(.system-mode-2) aside.sidebar,
html body.system-mode-1 #sidebar,
html body.system-mode-1 aside.sidebar {
  background: linear-gradient(180deg, #ffffff 0%, #f0f7ff 55%, #e0f2fe 100%) !important;
  border-left: 1px solid #bae6fd !important;
  box-shadow: -4px 0 22px rgba(37, 99, 235, 0.08) !important;
  color: #1e3a8a !important;
}

html body:not(.system-mode-2) .sidebar-brand,
html body.system-mode-1 .sidebar-brand {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%) !important;
  border: 1px solid #bfdbfe !important;
  border-radius: 12px !important;
  box-shadow: 0 3px 10px rgba(37, 99, 235, 0.08) !important;
}

html body:not(.system-mode-2) .sidebar-brand .brand-details strong,
html body.system-mode-1 .sidebar-brand .brand-details strong {
  color: #1e3a8a !important;
}

html body:not(.system-mode-2) .sidebar-brand .brand-details small,
html body.system-mode-1 .sidebar-brand .brand-details small {
  color: #2563eb !important;
  font-weight: 700 !important;
}

html body:not(.system-mode-2) #sidebar .nav-group-label span,
html body.system-mode-1 #sidebar .nav-group-label span {
  color: #2563eb !important;
  font-weight: 800 !important;
}

html body:not(.system-mode-2) #sidebar nav a,
html body.system-mode-1 #sidebar nav a {
  background: rgba(255, 255, 255, 0.88) !important;
  color: #1e3a8a !important;
  border: 1px solid #dbeafe !important;
  box-shadow: 0 1px 3px rgba(37, 99, 235, 0.04) !important;
}

html body:not(.system-mode-2) #sidebar nav a .nav-icon-box,
html body.system-mode-1 #sidebar nav a .nav-icon-box {
  background: #eff6ff !important;
  color: #2563eb !important;
  border: 1px solid #bfdbfe !important;
}

html body:not(.system-mode-2) #sidebar nav a:hover,
html body.system-mode-1 #sidebar nav a:hover {
  background: #dbeafe !important;
  color: #1d4ed8 !important;
  border-color: #93c5fd !important;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15) !important;
  transform: translateX(-2px) !important;
}

html body:not(.system-mode-2) #sidebar nav a.active,
html body.system-mode-1 #sidebar nav a.active {
  background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%) !important;
  color: #ffffff !important;
  border-color: #1d4ed8 !important;
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.32) !important;
}

html body:not(.system-mode-2) #sidebar nav a.active .nav-label,
html body.system-mode-1 #sidebar nav a.active .nav-label {
  color: #ffffff !important;
}

html body:not(.system-mode-2) #sidebar nav a.active .nav-icon-box,
html body.system-mode-1 #sidebar nav a.active .nav-icon-box {
  background: rgba(255, 255, 255, 0.22) !important;
  color: #ffffff !important;
  border-color: rgba(255, 255, 255, 0.4) !important;
}

html body:not(.system-mode-2) #sidebar .sidebar-footer,
html body.system-mode-1 #sidebar .sidebar-footer {
  background: rgba(255, 255, 255, 0.92) !important;
  border-top: 1px solid #bae6fd !important;
  color: #1e3a8a !important;
}

html body:not(.system-mode-2) .dash-welcome,
html body.system-mode-1 .dash-welcome {
  background: linear-gradient(135deg, #ffffff 0%, #f0f7ff 55%, #dbeafe 100%) !important;
  border: 1px solid #bae6fd !important;
  color: #0f172a !important;
  box-shadow: 0 6px 20px rgba(37, 99, 235, 0.08) !important;
}

html body:not(.system-mode-2) .dash-welcome h1,
html body:not(.system-mode-2) .dash-welcome h2,
html body:not(.system-mode-2) .dash-welcome strong,
html body.system-mode-1 .dash-welcome h1,
html body.system-mode-1 .dash-welcome h2,
html body.system-mode-1 .dash-welcome strong {
  color: #1e3a8a !important;
}

html body:not(.system-mode-2) .dash-welcome p,
html body:not(.system-mode-2) .dash-welcome small,
html body:not(.system-mode-2) .dash-welcome span:not(.badge),
html body.system-mode-1 .dash-welcome p,
html body.system-mode-1 .dash-welcome small,
html body.system-mode-1 .dash-welcome span:not(.badge) {
  color: #334155 !important;
}

/* ============================================================================
   2. PURE MODERN SLIDING TOGGLE SWITCH (NO TEXT "نهاري / ليلي")
   ============================================================================ */
html body .dual-mode-top-switcher,
html body .system-mode-switcher {
  position: relative !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  width: 56px !important;
  min-width: 56px !important;
  max-width: 56px !important;
  height: 28px !important;
  padding: 3px !important;
  border-radius: 999px !important;
  background: linear-gradient(135deg, #dbeafe 0%, #93c5fd 100%) !important;
  border: 1.5px solid #60a5fa !important;
  box-shadow: inset 0 2px 4px rgba(30, 58, 138, 0.15), 0 2px 8px rgba(37, 99, 235, 0.15) !important;
  cursor: pointer !important;
  transition: all 0.28s cubic-bezier(0.16, 1, 0.3, 1) !important;
  overflow: hidden !important;
  user-select: none !important;
}

html body.system-mode-2 .dual-mode-top-switcher,
html body.system-mode-2 .system-mode-switcher {
  background: linear-gradient(135deg, #090d16 0%, #1e293b 100%) !important;
  border-color: rgba(245, 158, 11, 0.65) !important;
  box-shadow: 0 0 14px rgba(245, 158, 11, 0.3), inset 0 2px 5px rgba(0, 0, 0, 0.7) !important;
}

/* Hide ANY text inside the toggle switch buttons — icon-only sliding knob */
html body .dual-mode-top-switcher button span,
html body .system-mode-switcher button span {
  display: none !important;
  font-size: 0 !important;
  width: 0 !important;
  height: 0 !important;
  overflow: hidden !important;
}

html body .dual-mode-top-switcher button,
html body .system-mode-switcher button {
  width: 22px !important;
  min-width: 22px !important;
  max-width: 22px !important;
  height: 22px !important;
  min-height: 22px !important;
  max-height: 22px !important;
  padding: 0 !important;
  margin: 0 !important;
  border-radius: 50% !important;
  border: none !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  font-size: 12px !important;
  line-height: 1 !important;
  background: transparent !important;
  color: #64748b !important;
  box-shadow: none !important;
  transition: all 0.28s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

html body.system-mode-1 #btnSwitchMode1,
html body:not(.system-mode-2) #btnSwitchMode1,
html body.system-mode-1 .sys-mode-btn[data-mode="1"],
html body:not(.system-mode-2) .sys-mode-btn[data-mode="1"] {
  background: #ffffff !important;
  color: #f59e0b !important;
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.25), 0 0 8px rgba(245, 158, 11, 0.35) !important;
  transform: scale(1.05) !important;
}

html body.system-mode-1 #btnSwitchMode2,
html body:not(.system-mode-2) #btnSwitchMode2,
html body.system-mode-1 .sys-mode-btn[data-mode="2"],
html body:not(.system-mode-2) .sys-mode-btn[data-mode="2"] {
  background: transparent !important;
  color: #1e3a8a !important;
  opacity: 0.55 !important;
  box-shadow: none !important;
}

html body.system-mode-2 #btnSwitchMode2,
html body.system-mode-2 .sys-mode-btn[data-mode="2"] {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
  color: #090d16 !important;
  box-shadow: 0 0 12px rgba(245, 158, 11, 0.65) !important;
  transform: scale(1.05) !important;
}

html body.system-mode-2 #btnSwitchMode1,
html body.system-mode-2 .sys-mode-btn[data-mode="1"] {
  background: transparent !important;
  color: #94a3b8 !important;
  opacity: 0.5 !important;
  box-shadow: none !important;
}

/* ============================================================================
   3. COMPLETE DARK MODE (system-mode-2): ZERO WHITE PATCHES ANYWHERE
   ============================================================================ */
html body.system-mode-2 {
  --bg-body: #090d16 !important;
  --bg-card: #111827 !important;
  --bg-surface-1: #111827 !important;
  --bg-surface-2: #1e293b !important;
  --border: #1e293b !important;
  --border-strong: #334155 !important;
  --text-main: #f8fafc !important;
  --text-heading: #ffffff !important;
  --text-muted: #94a3b8 !important;
  background-color: #090d16 !important;
  color: #f8fafc !important;
}

html body.system-mode-2 .app,
html body.system-mode-2 .main,
html body.system-mode-2 .content,
html body.system-mode-2 .view-section,
html body.system-mode-2 .tab-pane {
  background-color: transparent !important;
  color: #f8fafc !important;
}

html body.system-mode-2 .header,
html body.system-mode-2 .footer,
html body.system-mode-2 .panel,
html body.system-mode-2 .bento-panel,
html body.system-mode-2 .kpi-card,
html body.system-mode-2 .stat-card,
html body.system-mode-2 .page-heading,
html body.system-mode-2 .toolbar,
html body.system-mode-2 .action-grid,
html body.system-mode-2 .table-wrap,
html body.system-mode-2 .modal-card,
html body.system-mode-2 .command-box,
html body.system-mode-2 .logic-tabs,
html body.system-mode-2 .summary-box,
html body.system-mode-2 .photo-split-preview,
html body.system-mode-2 .detail-row,
html body.system-mode-2 .timeline-card,
html body.system-mode-2 .empty-state,
html body.system-mode-2 .edit-income-banner,
html body.system-mode-2 .dress-item-row,
html body.system-mode-2 .clothing-builder,
html body.system-mode-2 .hotel-perm-grid,
html body.system-mode-2 .permission-grid,
html body.system-mode-2 .form-section {
  background: #111827 !important;
  border-color: #1f2937 !important;
  color: #f8fafc !important;
}

html body.system-mode-2 div[style*="background:#fff"],
html body.system-mode-2 div[style*="background: #fff"],
html body.system-mode-2 div[style*="background:#ffffff"],
html body.system-mode-2 div[style*="background: #ffffff"],
html body.system-mode-2 div[style*="background:#f8fafc"],
html body.system-mode-2 div[style*="background: #f8fafc"],
html body.system-mode-2 div[style*="background:#f1f5f9"],
html body.system-mode-2 div[style*="background: #f1f5f9"],
html body.system-mode-2 div[style*="background:#eff6ff"],
html body.system-mode-2 div[style*="background: #eff6ff"],
html body.system-mode-2 section[style*="background:#fff"],
html body.system-mode-2 section[style*="background: #fff"],
html body.system-mode-2 section[style*="background:#f8fafc"],
html body.system-mode-2 section[style*="background: #f8fafc"],
html body.system-mode-2 aside[style*="background:#f8fafc"],
html body.system-mode-2 aside[style*="background: #f8fafc"] {
  background: #151f32 !important;
  border-color: #334155 !important;
  color: #f8fafc !important;
}

html body.system-mode-2 input,
html body.system-mode-2 select,
html body.system-mode-2 textarea,
html body.system-mode-2 .input {
  background: #0b1120 !important;
  border: 1px solid #334155 !important;
  color: #f8fafc !important;
}

html body.system-mode-2 table,
html body.system-mode-2 .modern-table {
  background: #111827 !important;
  color: #f8fafc !important;
}

html body.system-mode-2 table thead th,
html body.system-mode-2 .modern-table thead th {
  background: #0b1120 !important;
  color: #fbbf24 !important;
  border-bottom: 1px solid #334155 !important;
}

html body.system-mode-2 table tbody tr,
html body.system-mode-2 table tbody td {
  background: #111827 !important;
  color: #e2e8f0 !important;
  border-bottom: 1px solid #1e293b !important;
}

html body.system-mode-2 table tbody tr:nth-child(even) td {
  background: #0f172a !important;
}

html body.system-mode-2 table tbody tr:hover td {
  background: rgba(245, 158, 11, 0.08) !important;
}

html body.system-mode-2 h1,
html body.system-mode-2 h2,
html body.system-mode-2 h3,
html body.system-mode-2 h4,
html body.system-mode-2 strong,
html body.system-mode-2 b,
html body.system-mode-2 label {
  color: #f8fafc !important;
}

html body.system-mode-2 .header .user {
  background: #151f32 !important;
  border-color: #334155 !important;
  color: #f8fafc !important;
}

html body.system-mode-2 #notificationButton,
html body.system-mode-2 #headerChatQuickBtn,
html body.system-mode-2 .header .notification-trigger {
  background: #151f32 !important;
  color: #fbbf24 !important;
  border: 1px solid rgba(245, 158, 11, 0.45) !important;
}

/* Compact Daily Income Notes Bar */
.compact-notes-bar {
  padding: 6px 12px !important;
  margin-bottom: 10px !important;
  border-radius: 10px !important;
}
</style>

<script id="modernThemeToggleUpgraderJS">
(function() {
  const SUN_SVG = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>';
  const MOON_SVG = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';

  function stylePureSlidingToggle() {
    const b1 = document.getElementById('btnSwitchMode1');
    const b2 = document.getElementById('btnSwitchMode2');
    if (b1) {
      b1.innerHTML = SUN_SVG;
      b1.removeAttribute('style');
    }
    if (b2) {
      b2.innerHTML = MOON_SVG;
      b2.removeAttribute('style');
    }
    document.querySelectorAll('.sys-mode-btn[data-mode="1"]').forEach(el => { el.innerHTML = SUN_SVG; });
    document.querySelectorAll('.sys-mode-btn[data-mode="2"]').forEach(el => { el.innerHTML = MOON_SVG; });

    // Make clicking anywhere on the toggle track flip between Mode 1 and Mode 2
    document.querySelectorAll('.dual-mode-top-switcher, .system-mode-switcher').forEach(sw => {
      if (sw.dataset.toggleBound === '1') return;
      sw.dataset.toggleBound = '1';
      sw.addEventListener('click', function(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const isDark = document.body.classList.contains('system-mode-2');
        const nextMode = isDark ? 1 : 2;
        if (typeof window.switchMainSystemMode === 'function') {
          window.switchMainSystemMode(nextMode);
        } else if (typeof window.switchMobileSystemMode === 'function') {
          window.switchMobileSystemMode(nextMode);
        }
        setTimeout(stylePureSlidingToggle, 20);
      }, true);
    });
  }

  document.addEventListener('DOMContentLoaded', function() {
    stylePureSlidingToggle();
    setTimeout(stylePureSlidingToggle, 200);
    setTimeout(stylePureSlidingToggle, 600);
  });
})();
</script>'''

# ============================================================================
# 1. UPDATE templates/base.html
# ============================================================================
base_html_path = ROOT / "templates/base.html"
base_html = base_html_path.read_text(encoding="utf-8")

# Add quick Change Password button next to logout button in templates/base.html if not already present
if 'openQuickChangePasswordModal()' not in base_html:
    base_html = base_html.replace(
        '<button class="logout-pill-btn" onclick="logout()" title="تسجيل الخروج">⏻</button>',
        '<button class="logout-pill-btn" type="button" onclick="openQuickChangePasswordModal()" title="تغيير كلمة المرور" style="background:#eff6ff;color:#2563eb;border-color:#bfdbfe;">🔑</button>\n                    <button class="logout-pill-btn" onclick="logout()" title="تسجيل الخروج">⏻</button>'
    )

old_toggle_css_pattern = re.compile(
    r'<!-- ==========================================================================\s*🌙 COMPLETE DARK MODE OVERHAUL.*?</script>',
    re.DOTALL
)
assert old_toggle_css_pattern.search(base_html), "old_toggle_css_pattern not found in templates/base.html"
base_html = old_toggle_css_pattern.sub(lambda m: SHARED_THEME_AND_TOGGLE_BLOCK, base_html, count=1)
base_html_path.write_text(base_html, encoding="utf-8")
print("✅ Patched templates/base.html")
