// ============================================================================
// 📌 ملف الكود البرمجي (login.js): كود شاشة تسجيل الدخول، إنشاء حساب جديد، وتغيير كلمة السر
// ============================================================================

// PHOTO TEAM SYSTEM — Login + Bottom Create Account & Change Password

const password = document.getElementById("password");
const showPassword = document.getElementById("showPassword");

if (showPassword && password) {
    showPassword.addEventListener("click", () => {
        password.type = password.type === "password" ? "text" : "password";
    });
}

const darkBtn = document.getElementById("darkBtn");
const lightBtn = document.getElementById("lightBtn");

function setLoginThemeMode(modeNum) {
    const isDark = Number(modeNum) === 2;
    document.body.classList.toggle("theme-dark", isDark);
    document.body.classList.toggle("theme-light", !isDark);
    darkBtn?.classList.toggle("active", isDark);
    lightBtn?.classList.toggle("active", !isDark);
    try {
        localStorage.setItem("photo_team_main_mode", isDark ? "2" : "1");
    } catch (e) {}
}
window.setLoginThemeMode = setLoginThemeMode;

darkBtn?.addEventListener("click", () => setLoginThemeMode(2));
lightBtn?.addEventListener("click", () => setLoginThemeMode(1));

try {
    const savedMode = localStorage.getItem("photo_team_main_mode") || "2";
    setLoginThemeMode(Number(savedMode));
} catch (e) {
    setLoginThemeMode(2);
}

// تحميل الفنادق المتاحة لقائمة إنشاء حساب جديد
(async function loadPublicHotels() {
    const sel = document.getElementById("regHotel");
    if (!sel) return;
    try {
        const res = await fetch("/api/public/hotels");
        const j = await res.json();
        const rows = j.data || [];
        if (rows.length) {
            sel.innerHTML = `<option value="" style="color:#000;">🏨 اختر الفندق المخصص للعمل...</option>` +
                rows.map(h => `<option value="${h.id}" style="color:#000;">🏨 ${h.hotel_name}</option>`).join("");
        }
    } catch (e) {}
})();

function showAuthFeedback(msg, type = "bad") {
    const box = document.getElementById("authFeedbackBox");
    if (!box) return;
    box.textContent = msg;
    box.className = `auth-feedback ${type}`;
    box.hidden = false;
}

function clearAuthFeedback() {
    const box = document.getElementById("authFeedbackBox");
    if (box) box.hidden = true;
}

function switchAuthTab(tabName) {
    clearAuthFeedback();
    const tabs = {
        login: {
            form: "loginForm",
            title: "مرحباً بعودتك 👋",
            sub: "سجل الدخول إلى حسابك"
        },
        register: {
            form: "registerForm",
            title: "إنشاء حساب جديد ✨",
            sub: "أدخل الاسم الرباعي واسم الشهرة والفندق ورقم الهاتف والبطاقة"
        },
        reset: {
            form: "resetPasswordForm",
            title: "تغيير كلمة السر 🔑",
            sub: "أدخل اسم المستخدم ورقم البطاقة ورقم الهاتف لتعيين كلمة سر جديدة"
        }
    };
    const cfg = tabs[tabName] || tabs.login;
    ["loginForm", "registerForm", "resetPasswordForm"].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.hidden = (id !== cfg.form);
            el.classList.toggle("active", id === cfg.form);
        }
    });
    const tEl = document.getElementById("authCardTitle");
    const sEl = document.getElementById("authCardSub");
    if (tEl) tEl.textContent = cfg.title;
    if (sEl) sEl.textContent = cfg.sub;
}
window.switchAuthTab = switchAuthTab;

// 1. تسجيل الدخول
const loginForm = document.getElementById("loginForm");
loginForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAuthFeedback();
    const username = document.getElementById("username").value.trim();
    const passwordVal = document.getElementById("password").value;

    try {
        const response = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password: passwordVal })
        });
        const result = await response.json();
        if (result.ok) {
            window.location.href = "/";
        } else {
            showAuthFeedback(result.error || "خطأ في اسم المستخدم أو كلمة المرور", "bad");
        }
    } catch (error) {
        showAuthFeedback("حدث خطأ في الاتصال بالسيرفر", "bad");
    }
});

// 2. إنشاء حساب جديد
const registerForm = document.getElementById("registerForm");
registerForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAuthFeedback();
    const full_name = document.getElementById("regFullName").value.trim();
    const username = document.getElementById("regUsername").value.trim();
    const role = document.getElementById("regRole").value;
    const hotel_id = document.getElementById("regHotel")?.value || null;
    const phone_number = document.getElementById("regPhone").value.trim();
    const national_id = document.getElementById("regNationalId").value.trim();
    const passwordVal = document.getElementById("regPassword").value;

    if (full_name.length < 2) {
        return showAuthFeedback("يرجى كتابة الاسم بالكامل", "bad");
    }

    try {
        const response = await fetch("/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                full_name,
                username,
                nickname: username,
                role,
                hotel_id,
                phone_number,
                national_id,
                password: passwordVal
            })
        });
        const result = await response.json();
        if (result.ok) {
            showAuthFeedback("✅ تم إنشاء الحساب الجديد بنجاح! جاري الدخول للنظام...", "good");
            setTimeout(() => { window.location.href = "/"; }, 600);
        } else {
            showAuthFeedback(result.error || "تعذر إنشاء الحساب", "bad");
        }
    } catch (error) {
        showAuthFeedback("حدث خطأ في الاتصال بالسيرفر", "bad");
    }
});

// 3. تغيير كلمة السر
const resetPasswordForm = document.getElementById("resetPasswordForm");
resetPasswordForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAuthFeedback();
    const username = document.getElementById("rstUsername").value.trim();
    const national_id = document.getElementById("rstNationalId").value.trim();
    const phone_number = document.getElementById("rstPhone").value.trim();
    const new_password = document.getElementById("rstNewPassword").value;
    const confirm_password = document.getElementById("rstConfirmPassword").value;

    if (new_password !== confirm_password) {
        return showAuthFeedback("كلمة السر الجديدة وتأكيدها غير متطابقين", "bad");
    }

    try {
        const response = await fetch("/api/auth/reset-password", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username,
                national_id,
                phone_number,
                new_password
            })
        });
        const result = await response.json();
        if (result.ok) {
            switchAuthTab("login");
            document.getElementById("username").value = username;
            showAuthFeedback("✅ تم التحقق وتغيير كلمة السر بنجاح! سجل دخولك الآن.", "good");
        } else {
            showAuthFeedback(result.error || "بيانات التحقق غير مطابقة", "bad");
        }
    } catch (error) {
        showAuthFeedback("حدث خطأ في الاتصال بالسيرفر", "bad");
    }
});
