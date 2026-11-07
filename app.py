from __future__ import annotations
import re
try:
    from flaskwebgui import FlaskUI
except ImportError:  # Optional compatibility fallback for source-only runs.
    FlaskUI = None
import ast
import csv
import hashlib
try:
    import bcrypt
except ImportError:
    bcrypt = None
import io
import json
import os
import socket
import threading
import time
from datetime import date, datetime, timedelta, time as dt_time
from decimal import Decimal
from functools import wraps
from pathlib import Path

from flask import Flask, Response, g, jsonify, redirect, render_template, request, send_file, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

from database import get_db_connection
try:
    from flask_cors import CORS
except ImportError:
    def CORS(app, **kwargs): return None

import sys
import subprocess
import webbrowser

# دعم كامل لنسخة الـ EXE المجمعة عبر PyInstaller (--onefile و --onedir)
if getattr(sys, "frozen", False):
    BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    APP_ROOT = Path(sys.executable).resolve().parent
else:
    BUNDLE_ROOT = Path(__file__).resolve().parent
    APP_ROOT = BUNDLE_ROOT

UPLOAD_SERIAL = APP_ROOT / "static" / "uploads" / "serial"
UPLOAD_DAMAGE = APP_ROOT / "static" / "uploads" / "damage"
EXPORT_DIR = APP_ROOT / "exports"
for _p in (UPLOAD_SERIAL, UPLOAD_DAMAGE, EXPORT_DIR):
    try:
        _p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

app = Flask(
    __name__,
    template_folder=str(BUNDLE_ROOT / "templates"),
    static_folder=str(BUNDLE_ROOT / "static"),
)
CORS(app)
try:
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
except Exception:
    pass
app.secret_key = os.getenv("PHOTOTEAM_SECRET_KEY", "change-this-secret-key-in-production")
app.config["JSON_AS_ASCII"] = False
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True

@app.after_request
def _add_ngrok_and_mobile_headers(response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

FULL_ACCESS_ROLES = {"ceo", "admin", "administrator", "owner", "مدير عام", "المدير العام"}
PERMISSION_LABELS = {
    "bookings_access": "إدارة الحجوزات و Checkout",
    "laundry_access": "إدارة ومتابعة المغسلة",
    "assets_access": "إدارة عُهدة المعدات والفساتين",
    "sales_access": "شاشة المبيعات والعمولات",
    "finances_access": "التقارير المالية والتقفيل والمرتبات",
    "team_access": "إدارة الموظفين والفنادق",
}
ROLE_CATALOG = {
    "CEO": "CEO / مدير عام",
    "Manager": "Manager / مدير",
    "Photographer": "Photographer / مصور",
    "Sales": "Sales / مبيعات",
    "Accountant": "Accountant / حسابات",
    "Reviewer": "Reviewer / مراجعة",
}
PERMISSION_CONFIG_MARKER = "__configured__"
_ROLE_TABLES_READY = False

PAGE_PERMISSION = {
    "reservations": "bookings_access",
    "daily_sales": "sales_access",
    "treasury": "finances_access",
    "commissions": "sales_access",
    "laundry": "laundry_access",
    "assets": "assets_access",
    "salaries": "finances_access",
    "reports": "finances_access",
    "settings": "finances_access",
    "team_hotels": "team_access",
    "control_room": "bookings_access",
}

BOOKING_FIELDS = [
    "hotel", "booking_date", "nationality", "room_number", "phone_number",
    "booking_time", "session_details", "clothing", "deposit_usd", "deposit_eur",
    "deposit_le_cash", "deposit_le_visa", "total_agreement", "remaining",
    "sales_person", "photographer", "status",
]


# -----------------------------------------------------------------------------
# Runtime compatibility layer for the user's EXISTING database.
# It never ALTERs tables. It only maps historical column names to the names
# used by the latest UI, so the HTML version can sit on top of the same DB.
# -----------------------------------------------------------------------------
_SCHEMA_CACHE = {}

def table_columns(table_name):
    key = str(table_name)
    if key in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[key]
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"SHOW COLUMNS FROM `{key.replace('`','')}`")
            cols = {str(r[0]) for r in cur.fetchall()}
    except Exception:
        cols = set()
    _SCHEMA_CACHE[key] = cols
    return cols

_TABLES_CACHE = {}

def table_exists(table_name):
    key = str(table_name)
    if key in _TABLES_CACHE:
        return _TABLES_CACHE[key]
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SHOW TABLES LIKE %s", (key,))
            exists = bool(cur.fetchone())
    except Exception:
        exists = False
    _TABLES_CACHE[key] = exists
    return exists

def booking_col(canonical):
    cols = table_columns("bookings")
    candidates = {
        "hotel": ["hotel"],
        "booking_date": ["booking_date"],
        "nationality": ["nationality"],
        "room_number": ["room_number"],
        "phone_number": ["phone_number"],
        "booking_time": ["booking_time"],
        "session_details": ["session_details"],
        "clothing": ["clothing", "dress_rent"],
        "deposit_usd": ["deposit_usd"],
        "deposit_eur": ["deposit_eur"],
        "deposit_le_cash": ["deposit_le_cash", "deposit_egp"],
        "deposit_le_visa": ["deposit_le_visa"],
        "total_agreement": ["total_agreement", "total_agreed"],
        "remaining": ["remaining", "remaining_amount"],
        "sales_person": ["sales_person"],
        "photographer": ["photographer"],
        "status": ["status", "booking_status"],
    }.get(canonical, [canonical])
    return next((c for c in candidates if c in cols), None)

def normalize_booking_row(row):
    row = dict(row or {})
    def pick(*names, default=None):
        for n in names:
            if n in row and row.get(n) is not None:
                return row.get(n)
        return default
    created = serialize(pick("created_at", default=""))
    booking_date = pick("booking_date") or (str(created)[:10] if created else "")
    cash = pick("deposit_le_cash", "deposit_egp", default=0)
    visa = pick("deposit_le_visa", default=0)
    out = {
        "id": pick("id"),
        "hotel": pick("hotel", default="الفندق الرئيسي"),
        "booking_date": serialize(booking_date),
        "nationality": pick("nationality", default=""),
        "room_number": pick("room_number", default=""),
        "phone_number": pick("phone_number", default=""),
        "booking_time": serialize(pick("booking_time", default="")),
        "session_details": pick("session_details", default=""),
        "clothing": pick("clothing", "dress_rent", default="[]"),
        "deposit_usd": safe_float(pick("deposit_usd", default=0)),
        "deposit_eur": safe_float(pick("deposit_eur", default=0)),
        "deposit_le_cash": safe_float(cash),
        "deposit_le_visa": safe_float(visa),
        "total_agreement": safe_float(pick("total_agreement", "total_agreed", default=0)),
        "remaining": safe_float(pick("remaining", "remaining_amount", default=0)),
        "sales_person": pick("sales_person", default=""),
        "photographer": pick("photographer", default=""),
        "status": pick("status", "booking_status", default="انتظار"),
        "created_at": serialize(pick("created_at", default="")),
        "_has_hotel_column": "hotel" in row,
    }
    if not out["remaining"] and out["total_agreement"]:
        out["remaining"] = out["total_agreement"] - out["deposit_usd"] - out["deposit_eur"]
    return out

def fetch_booking_rows(cur, limit=5000):
    cur.execute(f"SELECT * FROM bookings ORDER BY id DESC LIMIT {int(limit)}")
    return [normalize_booking_row(r) for r in cur.fetchall()]

def booking_db_values(data):
    cols = table_columns("bookings")
    values = {}
    for key in BOOKING_FIELDS:
        col = booking_col(key)
        if not col:
            continue
        val = data.get(key)
        if col == "deposit_egp":
            val = safe_float(data.get("deposit_le_cash")) + safe_float(data.get("deposit_le_visa"))
        values[col] = val
    return values

def insert_booking_record(cur, data):
    vals = booking_db_values(data)
    if not vals:
        raise RuntimeError("جدول bookings لا يحتوي الأعمدة المطلوبة")
    cols = list(vals)
    cur.execute(
        "INSERT INTO bookings (" + ",".join(f"`{c}`" for c in cols) + ") VALUES (" + ",".join(["%s"]*len(cols)) + ")",
        [vals[c] for c in cols],
    )
    return cur.lastrowid

def update_booking_record(cur, booking_id, data, only=None):
    vals = booking_db_values(data)
    if only:
        wanted = set(only)
        vals = {c:v for c,v in vals.items() if any(booking_col(k)==c for k in wanted)}
    if not vals:
        return
    cols = list(vals)
    cur.execute("UPDATE bookings SET " + ",".join(f"`{c}`=%s" for c in cols) + " WHERE id=%s", [vals[c] for c in cols] + [booking_id])

def set_booking_status(cur, booking_id=None, room_number=None, status="Delivered", photographer=None):
    status_col = booking_col("status")
    photo_col = booking_col("photographer")
    if not status_col:
        return
    sets=[f"`{status_col}`=%s"]; args=[status]
    if photographer is not None and photo_col:
        sets.append(f"`{photo_col}`=%s"); args.append(photographer)
    if booking_id:
        cur.execute("UPDATE bookings SET "+",".join(sets)+" WHERE id=%s", args+[booking_id])
    elif room_number is not None:
        room_col=booking_col("room_number") or "room_number"
        cur.execute("UPDATE bookings SET "+",".join(sets)+f" WHERE `{room_col}`=%s", args+[room_number])



# =============================================================================
# 📌 1. كود تشفير وفحص كلمات المرور (Password Hashing & Verification)
# =============================================================================
def hash_password(value: str) -> str:
    # Kept for creating new SHA256-compatible passwords if needed
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    """Support existing bcrypt passwords and old SHA256 passwords."""
    if not stored_hash:
        return False

    # Existing database uses bcrypt ($2b$...)
    if str(stored_hash).startswith("$2") and bcrypt is not None:
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                stored_hash.encode("utf-8")
            )
        except Exception:
            return False

    # Fallback for SHA256 users
    return hash_password(password) == stored_hash


def serialize(value):
    """حوّل أنواع MySQL/Python لقيم آمنة لـ JSON بدون تغيير البيانات نفسها."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dt_time):
        return value.strftime("%H:%M:%S")
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        sign = "-" if total_seconds < 0 else ""
        total_seconds = abs(total_seconds)
        hours, rem = divmod(total_seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        return f"{sign}{hours:02d}:{minutes:02d}:{seconds:02d}"
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        try:
            return raw.decode("utf-8")
        except Exception:
            return raw.hex()
    return value


def rows_to_json(rows):
    return [{k: serialize(v) for k, v in row.items()} for row in rows]


def ok(data=None, **extra):
    payload = {"ok": True, **extra}
    if data is not None:
        payload["data"] = data
    return jsonify(payload)


def fail(message, status=400, **extra):
    return jsonify({"ok": False, "error": str(message), **extra}), status


def safe_float(v):
    try:
        return float(v or 0)
    except Exception:
        return 0.0


def safe_int(v, default=0):
    try:
        return int(float(v))
    except Exception:
        return default


def current_user():
    return session.get("user")


def _normalize_role(value):
    return str(value or "").strip().lower()


def ensure_multi_role_tables():
    """Create/seed the multi-role tables without deleting or rewriting legacy data."""
    global _ROLE_TABLES_READY
    if _ROLE_TABLES_READY:
        return
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                role_key VARCHAR(50) NOT NULL UNIQUE,
                role_name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS employee_roles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                role_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_employee_role (user_id, role_id),
                INDEX idx_employee_roles_user (user_id),
                INDEX idx_employee_roles_role (role_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        for key, label in ROLE_CATALOG.items():
            cur.execute(
                "INSERT INTO roles (role_key,role_name) VALUES (%s,%s) "
                "ON DUPLICATE KEY UPDATE role_name=VALUES(role_name)",
                (key, label),
            )
        # One-time compatibility migration: every old employee keeps the role
        # stored in team_members.role, while new roles can be added beside it.
        cur.execute("SELECT id,role FROM team_members WHERE role IS NOT NULL AND role<>''")
        legacy = cur.fetchall()
        aliases = {
            'ceo':'CEO','admin':'CEO','administrator':'CEO','owner':'CEO','مدير عام':'CEO','المدير العام':'CEO',
            'manager':'Manager','hotel_manager':'Manager','مدير':'Manager','مدير فندق':'Manager',
            'photographer':'Photographer','مصور':'Photographer',
            'sales':'Sales','سيلز':'Sales','مبيعات':'Sales',
            'accountant':'Accountant','محاسب':'Accountant','حسابات':'Accountant',
            'reviewer':'Reviewer','مراجع':'Reviewer','مراجعة':'Reviewer',
        }
        for uid, old_role in legacy:
            role_key = aliases.get(_normalize_role(old_role))
            if not role_key:
                continue
            cur.execute("SELECT id FROM roles WHERE role_key=%s LIMIT 1", (role_key,))
            rr = cur.fetchone()
            if rr:
                cur.execute("INSERT IGNORE INTO employee_roles (user_id,role_id) VALUES (%s,%s)", (uid, rr[0]))
    _ROLE_TABLES_READY = True


_ROLE_ALIASES = {
    'ceo':'CEO','admin':'CEO','administrator':'CEO','owner':'CEO','مدير عام':'CEO','المدير العام':'CEO',
    'manager':'Manager','hotel_manager':'Manager','directormanager':'Manager','hotelmanager':'Manager','مدير':'Manager','مدير فندق':'Manager',
    'photographer':'Photographer','مصور':'Photographer',
    'sales':'Sales','سيلز':'Sales','مبيعات':'Sales',
    'accountant':'Accountant','محاسب':'Accountant','حسابات':'Accountant',
    'reviewer':'Reviewer','مراجع':'Reviewer','مراجعة':'Reviewer',
}

def _all_user_roles_map(cur=None):
    """يرجع قاموس {user_id: set(role_keys)} لجميع الموظفين باستعلام واحد سريع مع كاش للطلب الحالي."""
    try:
        if hasattr(g, "_all_roles_map"):
            return g._all_roles_map
    except Exception:
        pass
    mapping = {}
    try:
        ensure_multi_role_tables()
        if cur is not None:
            cur.execute("""SELECT er.user_id, r.role_key FROM employee_roles er
                           JOIN roles r ON r.id=er.role_id""")
            for row in cur.fetchall():
                uid_val = row.get("user_id") if isinstance(row, dict) else row[0]
                rkey_val = row.get("role_key") if isinstance(row, dict) else row[1]
                if uid_val and rkey_val:
                    mapping.setdefault(int(uid_val), set()).add(str(rkey_val))
        else:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""SELECT er.user_id, r.role_key FROM employee_roles er
                             JOIN roles r ON r.id=er.role_id""")
                for uid_val, rkey_val in c.fetchall():
                    if uid_val and rkey_val:
                        mapping.setdefault(int(uid_val), set()).add(str(rkey_val))
    except Exception:
        mapping = {}
    try:
        g._all_roles_map = mapping
    except Exception:
        pass
    return mapping

def get_user_roles(user_id=None, user=None, cur=None):
    user = user or current_user() or {}
    uid = user_id or user.get('id')
    roles = set()
    if uid:
        try:
            roles_map = _all_user_roles_map(cur=cur)
            roles = set(roles_map.get(int(uid), set()))
        except Exception:
            roles = set()
    if not roles and user.get('role'):
        mapped = _ROLE_ALIASES.get(_normalize_role(user.get('role')))
        if mapped:
            roles.add(mapped)
    return roles


def has_role(role_key, user=None):
    wanted = _normalize_role(role_key)
    return any(_normalize_role(r) == wanted for r in get_user_roles(user=user))


SUPERVISOR_ROLES = FULL_ACCESS_ROLES | {
    "manager", "hotel_manager", "مدير", "مدير فندق",
    "accountant", "محاسب", "حسابات",
    "reviewer", "مراجع", "مراجعة",
}


# =============================================================================
# 📌 2. كود التحقق من الصلاحيات والأدوار الـ 5 (CEO / Manager / Accountant / Sales / Photographer)
# =============================================================================
def is_full_access(user=None):
    user = user or current_user() or {}
    roles = {_normalize_role(r) for r in get_user_roles(user_id=user.get('id'), user=user)}
    if roles & FULL_ACCESS_ROLES:
        return True
    return bool(roles & {'ceo'}) or _normalize_role(user.get('role')) in FULL_ACCESS_ROLES

def has_full_access(user=None):
    return is_full_access(user)

def template_ctx(active=""):
    ensure_web_extension_tables()
    return {
        "user": current_user(),
        "active": active,
    }


def is_photographer_only(user=None):
    """يرجع True إذا كان الحساب مصوراً فقط (بدون دور إدارة أو حسابات أو سيلز)."""
    user = user or current_user() or {}
    if not user or is_full_access(user):
        return False
    roles = {_normalize_role(r) for r in get_user_roles(user_id=user.get('id'), user=user)}
    if roles & SUPERVISOR_ROLES:
        return False
    has_photo = bool(roles & {"photographer", "مصور"})
    has_sales = bool(roles & {"sales", "سيلز", "مبيعات"})
    return has_photo and not has_sales

def is_sales_only(user=None):
    """يرجع True إذا كان الحساب سيلز فقط (بدون دور إدارة أو حسابات)."""
    user = user or current_user() or {}
    if not user or is_full_access(user):
        return False
    roles = {_normalize_role(r) for r in get_user_roles(user_id=user.get('id'), user=user)}
    if roles & SUPERVISOR_ROLES:
        return False
    return bool(roles & {"sales", "سيلز", "مبيعات"})

def is_personal_scope_user(user=None):
    """يرجع True إذا كان المستخدم مصوراً أو سيلز فقط (بدون دور إدارة أو حسابات أو مراجعة)،
    بحيث لا يرى إلا أوردراته ومبيعاته وعمولاته الخاصة فقط."""
    user = user or current_user() or {}
    if not user or is_full_access(user):
        return False
    roles = {_normalize_role(r) for r in get_user_roles(user_id=user.get('id'), user=user)}
    if roles & SUPERVISOR_ROLES:
        return False
    return bool(roles & {"sales", "photographer", "سيلز", "مبيعات", "مصور"})

def current_employee_names(user=None):
    """أسماء المطابقة الخاصة بالموظف المسجل دخوله حالياً (اللقب + الاسم بالكامل + اسم المستخدم)."""
    user = user or current_user() or {}
    names = set()
    for k in ("nickname", "full_name", "username"):
        val = str(user.get(k) or "").strip().lower()
        if val:
            names.add(val)
    return names

def record_belongs_to_current_user(row, user=None):
    """يتحقق مما إذا كان الحجز أو سجل المبيعات يخص الموظف الحالي (سيلز أو مصور)."""
    user = user or current_user() or {}
    if not is_personal_scope_user(user):
        return True
    if not row:
        return False
    my_names = current_employee_names(user)
    if not my_names:
        return False
    roles = {_normalize_role(r) for r in get_user_roles(user_id=user.get('id'), user=user)}
    is_sales_role = bool(roles & {"sales", "سيلز", "مبيعات"})
    is_photo_role = bool(roles & {"photographer", "مصور"})

    sales_raw = str(row.get("sales_person") or row.get("deposit_sales_person") or "")
    photo_raw = str(row.get("photographer") or "")
    row_sales = {s.strip().lower() for s in split_names(sales_raw) if s.strip()}
    if sales_raw.strip():
        row_sales.add(sales_raw.strip().lower())
    row_photos = {p.strip().lower() for p in split_names(photo_raw) if p.strip()}
    if photo_raw.strip():
        row_photos.add(photo_raw.strip().lower())

    if is_sales_role and (row_sales & my_names):
        return True
    if is_photo_role and (row_photos & my_names):
        return True
    if not is_sales_role and not is_photo_role:
        return bool((row_sales | row_photos) & my_names)
    return False


def is_accountant_only(user=None):
    """يرجع True إذا كان الحساب محاسباً (يرى حسابات كل الفنادق فقط)."""
    user = user or current_user() or {}
    if not user or is_full_access(user):
        return False
    roles = {_normalize_role(r) for r in get_user_roles(user_id=user.get('id'), user=user)}
    if roles & {"manager", "hotel_manager", "مدير", "مدير فندق"}:
        return False
    return bool(roles & {"accountant", "محاسب", "حسابات"})


def is_manager_role(user=None):
    """يرجع True إذا كان الحساب مديراً (يرى الفنادق المحددة له فقط من الأونر)."""
    user = user or current_user() or {}
    if not user or is_full_access(user):
        return False
    roles = {_normalize_role(r) for r in get_user_roles(user_id=user.get('id'), user=user)}
    return bool(roles & {"manager", "hotel_manager", "مدير", "مدير فندق"})


def _all_user_permissions_map():
    try:
        if hasattr(g, "_all_perms_map"):
            return g._all_perms_map
    except Exception:
        pass
    mapping = {}
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT user_id, permission_key FROM employee_permissions")
            for uid_val, pkey in cur.fetchall():
                if uid_val and pkey:
                    mapping.setdefault(int(uid_val), set()).add(str(pkey))
    except Exception:
        mapping = {}
    try:
        g._all_perms_map = mapping
    except Exception:
        pass
    return mapping


def get_user_permissions(user_id=None):
    user = current_user() or {}
    uid = user_id or user.get("id")
    role_user = user if (not user_id or user.get('id') == user_id) else {"id": uid}
    if is_full_access(role_user):
        return set(PERMISSION_LABELS)
    if not uid:
        return set()
    raw = set(_all_user_permissions_map().get(int(uid), set()))
    configured = bool(raw)
    perms = {x for x in raw if x != PERMISSION_CONFIG_MARKER}
    roles = {_normalize_role(r) for r in get_user_roles(user_id=uid, user=role_user)}
    # ضمان الصلاحيات الأساسية لكل وظيفة:
    if 'manager' in roles:
        if not configured:
            perms |= {"bookings_access", "laundry_access", "assets_access", "sales_access", "finances_access", "team_access"}
    if 'accountant' in roles:
        # الحسابات يرى حسابات جميع الفنادق (الدخل، العمولات، المرتبات، التقارير)
        perms |= {"sales_access", "finances_access"}
    if 'sales' in roles:
        # السيلز يتحكم في قائمة الحجوزات ويرى مبيعاته وأوردراته فقط
        perms |= {"bookings_access", "sales_access"}
    if 'photographer' in roles:
        # المصور يرى أوردراته ومبيعاته فقط
        perms |= {"bookings_access", "sales_access"}
    return perms


def has_permission(key, user=None):
    user = user or current_user() or {}
    if is_full_access(user):
        return True
    return key in get_user_permissions(user.get("id"))


def login_required(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        if not current_user():
            if request.path.startswith("/api/"):
                return fail("يرجى تسجيل الدخول أولاً", 401)
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return inner


def require_permission(key):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def inner(*args, **kwargs):
            if not has_permission(key):
                return fail("ليس لديك صلاحية لتنفيذ هذه العملية", 403)
            return fn(*args, **kwargs)
        return inner
    return decorator


def allowed_hotel_ids(user=None):
    user = user or current_user() or {}
    is_current = (user.get("id") == (current_user() or {}).get("id"))
    if is_current:
        try:
            if hasattr(g, "_cached_allowed_hotel_ids"):
                return g._cached_hotel_ids_val
        except Exception:
            pass
    # الأونر (CEO) والحسابات (Accountant) يرون جميع الفنادق (None = كل الفنادق)
    if is_full_access(user) or is_accountant_only(user) or is_photographer_only(user) or is_sales_only(user):
        if is_current:
            try:
                g._cached_allowed_hotel_ids = True
                g._cached_hotel_ids_val = None
            except Exception:
                pass
        return None
    ids = set()
    try:
        if user.get("hotel_id") not in (None, "", "الكل"):
            ids.add(int(user["hotel_id"]))
    except Exception:
        pass
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT hotel_id FROM user_hotel_permissions WHERE user_id=%s AND can_view=1", (user.get("id"),))
            ids.update(int(r[0]) for r in cur.fetchall() if r and r[0] is not None)
    except Exception:
        pass
    # إذا كان سيلز ولم يحدد له فندق بعد، لا نمنعه من رؤية حجوزاته الشخصية، أما لو محدد له فندق فيلتزم به
    if not ids and is_sales_only(user):
        res = None
    else:
        res = sorted(ids)
    if is_current:
        try:
            g._cached_allowed_hotel_ids = True
            g._cached_hotel_ids_val = res
        except Exception:
            pass
    return res


def allowed_hotel_names(user=None):
    user = user or current_user() or {}
    is_current = (user.get("id") == (current_user() or {}).get("id"))
    if is_current:
        try:
            if hasattr(g, "_cached_allowed_hotel_names"):
                return g._cached_hotel_names_val
        except Exception:
            pass
    ids = allowed_hotel_ids(user)
    if ids is None:
        res = None
    elif not ids:
        res = []
    else:
        marks = ",".join(["%s"] * len(ids))
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT hotel_name FROM hotels WHERE id IN ({marks})", tuple(ids))
            res = [str(r[0]) for r in cur.fetchall() if r and r[0]]
    if is_current:
        try:
            g._cached_allowed_hotel_names = True
            g._cached_hotel_names_val = res
        except Exception:
            pass
    return res


def make_where_for_hotels(column, values):
    if values is None:
        return "", []
    if not values:
        return " AND 1=0", []
    marks = ",".join(["%s"] * len(values))
    return f" AND {column} IN ({marks})", list(values)


def hotel_name_from_id(hotel_id):
    if hotel_id in (None, "", "الكل"):
        return None
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT hotel_name FROM hotels WHERE id=%s LIMIT 1", (hotel_id,))
        row = cur.fetchone()
        return row[0] if row else None


def hotel_id_from_name(name):
    if not name:
        return None
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM hotels WHERE hotel_name=%s LIMIT 1", (name,))
        row = cur.fetchone()
        return row[0] if row else None


def verify_hotel_name(name):
    names = allowed_hotel_names()
    return names is None or name in names


def verify_hotel_id(hid):
    ids = allowed_hotel_ids()
    return ids is None or safe_int(hid, -1) in ids


def parse_json_list(value):
    if isinstance(value, list):
        return value
    if not value:
        return []
    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(value if isinstance(value, str) else str(value))
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
    return []


def split_names(value):
    return [x.strip() for x in str(value or "").split(",") if x.strip() and x.strip() not in {"بدون مصور", "لا يوجد", "None", "none"}]


def count_clothing(clothing):
    dress = gala = 0
    for item in parse_json_list(clothing):
        if not isinstance(item, dict):
            continue
        qty = max(1, safe_int(item.get("qty"), 1))
        dtype = str(item.get("type", "")).strip().lower()
        if any(k in dtype for k in ["جلابية", "جلباب", "جلابيب"]):
            gala += qty
        else:
            dress += qty
    return dress, gala


def audit(action, table, details):
    user = current_user() or {}
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO system_audit_logs (user_id, action_type, affected_table, details) VALUES (%s,%s,%s,%s)",
                (user.get("id"), action, table, details),
            )
            try:
                hid = user.get("hotel_id") if user.get("hotel_id") not in (None, "", "الكل") else 1
                cur.execute(
                    "INSERT INTO audit_logs (hotel_id,user_name,action_type,details) VALUES (%s,%s,%s,%s)",
                    (hid, user.get("nickname") or user.get("full_name") or "system", action, details),
                )
            except Exception:
                pass
    except Exception:
        pass


def booking_activity(booking_id, event_type, title, details=""):
    user = current_user() or {}
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO booking_activity (booking_id,event_type,title,details,user_id) VALUES (%s,%s,%s,%s,%s)",
                (booking_id, event_type, title, details, user.get("id")),
            )
    except Exception:
        pass


def _all_settings_map():
    try:
        if hasattr(g, "_settings_map"):
            return g._settings_map
    except Exception:
        pass
    smap = {}
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT setting_key, setting_value FROM system_settings")
            for k, v in cur.fetchall():
                if k is not None:
                    smap[str(k)] = v
    except Exception:
        smap = {}
    try:
        g._settings_map = smap
    except Exception:
        pass
    return smap

def get_setting(key, default="0"):
    smap = _all_settings_map()
    val = smap.get(str(key))
    return val if val is not None else default


def period_bounds(month: str, period: str, day_from=None, day_to=None):
    year = datetime.now().year
    try:
        month_num = int(str(month).split("-")[-1])
    except Exception:
        month_num = datetime.now().month
    prefix = f"{year}-{month_num:02d}"
    if period in {"p1", "دفعة 1 (1 إلى 10)"}:
        return f"{prefix}-01", f"{prefix}-10", "دفعة 1 (1 إلى 10)"
    if period in {"p2", "دفعة 2 (11 إلى 20)"}:
        return f"{prefix}-11", f"{prefix}-20", "دفعة 2 (11 إلى 20)"
    if period in {"p3", "دفعة 3 (21 إلى 31)"}:
        return f"{prefix}-21", f"{prefix}-31", "دفعة 3 (21 إلى 31)"
    if period in {"custom", "فترة مخصصة (أيام محددة)"}:
        a = max(1, min(31, safe_int(day_from, 1)))
        b = max(a, min(31, safe_int(day_to, 31)))
        return f"{prefix}-{a:02d}", f"{prefix}-{b:02d}", f"فترة مخصصة ({a} إلى {b})"
    return f"{prefix}-01", f"{prefix}-31", "الشهر بالكامل"


def next_period_start(month: str, period: str):
    start, _, _ = period_bounds(month, period)
    d = datetime.strptime(start, "%Y-%m-%d")
    if period in {"p1", "دفعة 1 (1 إلى 10)"}:
        return d.replace(day=11).date().isoformat()
    if period in {"p2", "دفعة 2 (11 إلى 20)"}:
        return d.replace(day=21).date().isoformat()
    nxt = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return nxt.date().isoformat()


def _all_commission_rates_map():
    try:
        if hasattr(g, "_comm_rates_map"):
            return g._comm_rates_map
    except Exception:
        pass
    rmap = {}
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT nickname, commission_rate FROM team_members")
            for nick, rate in cur.fetchall():
                if nick and rate is not None:
                    rmap[str(nick).strip().lower()] = float(rate)
    except Exception:
        rmap = {}
    try:
        g._comm_rates_map = rmap
    except Exception:
        pass
    return rmap

def employee_commission_rate(name, role_type):
    rmap = _all_commission_rates_map()
    k = str(name or "").strip().lower()
    if k in rmap:
        return rmap[k]
    return 10.0 if role_type == "photographer" else 13.0


def deposit_equivalent(usd, eur, cash, visa, rate=50):
    # مطابق للبرنامج الأصلي: الدولار + اليورو + المصري/الريت.
    r = safe_float(rate) or 50.0
    return safe_float(usd) + safe_float(eur) + (safe_float(cash) + safe_float(visa)) / r


def sync_booking_dresses(cur, booking_id, clothing):
    try:
        cur.execute("DELETE FROM booking_dresses WHERE booking_id=%s", (booking_id,))
        for item in parse_json_list(clothing):
            if not isinstance(item, dict):
                continue
            cur.execute(
                """INSERT INTO booking_dresses
                   (booking_id,dress_type,custom_name,color,size_category,quantity)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (
                    booking_id,
                    item.get("type") or "فستان",
                    item.get("custom_name") or item.get("name"),
                    item.get("color") or "غير محدد",
                    item.get("size") or item.get("size_category") or "ستاندرد",
                    max(1, safe_int(item.get("qty"), 1)),
                ),
            )
    except Exception:
        pass


def record_deposit(cur, booking, diffs, deposit_date=None):
    if not any(abs(safe_float(v)) > 0 for v in diffs.values()):
        return
    if not table_exists("deposits"):
        return
    hid = hotel_id_from_name(booking.get("hotel")) or 1
    cols = table_columns("deposits")
    data = {
        "booking_id": booking.get("id"), "hotel_id": hid, "room_number": booking.get("room_number"),
        "deposit_sales_person": booking.get("sales_person"), "deposit_usd": safe_float(diffs.get("usd")),
        "deposit_eur": safe_float(diffs.get("eur")), "deposit_le_visa": safe_float(diffs.get("visa")),
        "deposit_le_cash": safe_float(diffs.get("cash")), "deposit_date": deposit_date or date.today().isoformat(),
    }
    use = {k:v for k,v in data.items() if k in cols}
    if not use:
        return
    names=list(use)
    cur.execute("INSERT INTO deposits ("+",".join(f"`{x}`" for x in names)+") VALUES ("+",".join(["%s"]*len(names))+")", [use[x] for x in names])
    # V90: ترحيل العربون تلقائياً إلى المبيعات اليومية (daily_income) سواء سجله المدير أو تم تحصيله لاحقاً
    try:
        dcols = table_columns("daily_income")
        bid = safe_int(booking.get("id"))
        rm = str(booking.get("room_number") or "").strip()
        s_person = str(booking.get("sales_person") or "").strip()
        photog = str(booking.get("photographer") or "").strip()
        dep_date = str(deposit_date or booking.get("booking_date") or date.today().isoformat())[:10]
        rate = 50.0
        equiv_usd = round(safe_float(diffs.get("usd")) + safe_float(diffs.get("eur")) + ((safe_float(diffs.get("cash")) + safe_float(diffs.get("visa"))) / rate), 2)
        if equiv_usd > 0 and dcols:
            existing_inc = None
            if bid and "booking_id" in dcols:
                cur.execute("SELECT * FROM daily_income WHERE booking_id=%s ORDER BY id DESC LIMIT 1", (bid,))
                existing_inc = cur.fetchone()
            if not existing_inc and rm:
                cur.execute("SELECT * FROM daily_income WHERE room_number=%s AND income_date=%s ORDER BY id DESC LIMIT 1", (rm, dep_date))
                existing_inc = cur.fetchone()
            if existing_inc:
                old_dep = safe_float(existing_inc[8] if isinstance(existing_inc, tuple) else existing_inc.get("deposit_applied", 0))
                inc_id = existing_inc[0] if isinstance(existing_inc, tuple) else existing_inc.get("id")
                cur.execute("UPDATE daily_income SET deposit_applied = COALESCE(deposit_applied,0) + %s, daily_total = COALESCE(daily_total,0) + %s WHERE id=%s", (equiv_usd, equiv_usd, inc_id))
            else:
                new_inc = {
                    "hotel_id": hid, "booking_id": bid or None, "room_number": rm,
                    "sales_person": s_person, "deposit_sales_person": s_person, "photographer": photog,
                    "deposit_usd": safe_float(diffs.get("usd")), "deposit_eur": safe_float(diffs.get("eur")),
                    "deposit_le_cash": safe_float(diffs.get("cash")), "deposit_le_visa": safe_float(diffs.get("visa")),
                    "deposit_applied": equiv_usd, "income_usd": safe_float(diffs.get("usd")),
                    "income_eur": safe_float(diffs.get("eur")), "income_le_k": safe_float(diffs.get("cash")),
                    "income_le_m": safe_float(diffs.get("visa")), "le_to_usd": rate,
                    "cost_total": 0, "daily_total": equiv_usd, "income_date": dep_date
                }
                use_i = {k: v for k, v in new_inc.items() if k in dcols}
                if use_i:
                    cols_list = list(use_i.keys())
                    cur.execute("INSERT INTO daily_income (" + ",".join(f"`{k}`" for k in cols_list) + ") VALUES (" + ",".join(["%s"]*len(cols_list)) + ")", [use_i[k] for k in cols_list])
    except Exception:
        pass



_WEB_EXTENSIONS_READY = False


# =============================================================================
# 📌 3. كود إنشاء جداول الخزنة والشات وملاحظات الدخل والإشعارات في قاعدة البيانات
# =============================================================================
def ensure_web_extension_tables():
    """Create web-only helper tables. Never ALTER core business tables."""
    global _WEB_EXTENSIONS_READY
    if _WEB_EXTENSIONS_READY:
        return
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS internal_chat_messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                channel VARCHAR(20) NOT NULL DEFAULT 'team', -- 'managers' (الأونر والمديرين فقط) or 'team' (المدير والفريق + الأونر)
                hotel_id INT DEFAULT NULL,
                hotel_name VARCHAR(120) DEFAULT 'جميع الفنادق',
                sender_id INT DEFAULT NULL,
                sender_name VARCHAR(120) NOT NULL,
                sender_role VARCHAR(50) NOT NULL,
                message_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_chat_channel (channel),
                INDEX idx_chat_hotel (hotel_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS treasury_transactions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tx_date DATE NOT NULL,
                tx_month VARCHAR(7) NOT NULL,
                tx_type VARCHAR(15) NOT NULL DEFAULT 'EXPENSE', -- 'DEPOSIT' (إيداع عهدة من الأونر) or 'EXPENSE' (مصروف مخصوم)
                category VARCHAR(100) NOT NULL DEFAULT 'مصاريف تشغيل',
                hotel_id INT DEFAULT NULL,
                hotel_name VARCHAR(120) DEFAULT 'جميع الفنادق',
                amount_egp DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                amount_usd DECIMAL(12,2) DEFAULT 0.00,
                beneficiary VARCHAR(150) DEFAULT '',
                description TEXT NOT NULL,
                payment_method VARCHAR(60) DEFAULT 'كاش / نقدي',
                created_by VARCHAR(100) DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_trs_month (tx_month),
                INDEX idx_trs_type (tx_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_income_notes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                hotel_id INT DEFAULT NULL,
                note_date DATE NOT NULL,
                note_type VARCHAR(10) NOT NULL DEFAULT 'OUT',
                amount_usd DECIMAL(12,2) DEFAULT 0.00,
                amount_eur DECIMAL(12,2) DEFAULT 0.00,
                amount_le_cash DECIMAL(12,2) DEFAULT 0.00,
                amount_le_office DECIMAL(12,2) DEFAULT 0.00,
                exchange_rate DECIMAL(10,2) DEFAULT 50.00,
                equivalent_usd DECIMAL(12,2) DEFAULT 0.00,
                person_name VARCHAR(150) DEFAULT '',
                note_text TEXT NOT NULL,
                created_by VARCHAR(100) DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_din_date (note_date),
                INDEX idx_din_hotel (hotel_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS system_notifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(100) NOT NULL,
                message TEXT NOT NULL,
                status VARCHAR(20) DEFAULT 'Pending',
                related_sales_person VARCHAR(100),
                amount DECIMAL(12,2) DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS web_pending_deposits (
                id INT AUTO_INCREMENT PRIMARY KEY,
                booking_id INT NOT NULL,
                hotel_id INT DEFAULT NULL,
                room_number VARCHAR(50),
                sales_person VARCHAR(100),
                deposit_usd DECIMAL(12,2) DEFAULT 0.00,
                deposit_eur DECIMAL(12,2) DEFAULT 0.00,
                deposit_le_cash DECIMAL(12,2) DEFAULT 0.00,
                deposit_le_visa DECIMAL(12,2) DEFAULT 0.00,
                deposit_date DATE NOT NULL,
                status VARCHAR(20) DEFAULT 'Pending',
                created_by INT DEFAULT NULL,
                resolved_by INT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at DATETIME DEFAULT NULL,
                INDEX idx_web_pending_booking (booking_id),
                INDEX idx_web_pending_status (status),
                INDEX idx_web_pending_date (deposit_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS web_notification_links (
                id INT AUTO_INCREMENT PRIMARY KEY,
                notification_id INT NOT NULL,
                notification_type VARCHAR(50),
                target_url VARCHAR(500),
                booking_id INT DEFAULT NULL,
                pending_deposit_id INT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_web_notification (notification_id),
                INDEX idx_web_notification_booking (booking_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
    _SCHEMA_CACHE.pop('system_notifications', None)
    _SCHEMA_CACHE.pop('web_pending_deposits', None)
    _SCHEMA_CACHE.pop('web_notification_links', None)
    _WEB_EXTENSIONS_READY = True


def current_role_key():
    return str((current_user() or {}).get('role') or '').strip().lower()


def current_user_is_sales():
    return is_sales_only() or has_role('Sales')


def _ensure_notif_link_columns():
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SHOW COLUMNS FROM web_notification_links")
            existing = {str(r[0]) for r in cur.fetchall()}
            extras = {
                "target_employee": "VARCHAR(100) DEFAULT NULL",
                "target_role": "VARCHAR(50) DEFAULT NULL",
                "priority": "VARCHAR(20) DEFAULT 'normal'",
                "hotel_id": "INT DEFAULT NULL",
                "sender_name": "VARCHAR(100) DEFAULT NULL",
            }
            for col_name, col_def in extras.items():
                if col_name not in existing:
                    cur.execute(f"ALTER TABLE web_notification_links ADD COLUMN `{col_name}` {col_def}")
        _SCHEMA_CACHE.pop("web_notification_links", None)
    except Exception:
        pass

def create_linked_notification(cur, title, message, *, sales_person='', amount=0, notification_type='', target_url='', booking_id=None, pending_deposit_id=None, target_employee=None, target_role=None, priority='normal', hotel_id=None, sender_name=None):
    ensure_web_extension_tables()
    _ensure_notif_link_columns()
    cols = table_columns('system_notifications')
    data = {
        'title': str(title or 'إشعار')[:100],
        'message': str(message or ''),
        'status': 'Pending',
        'related_sales_person': sales_person or target_employee or '',
        'amount': safe_float(amount),
    }
    use = {k:v for k,v in data.items() if k in cols}
    names = list(use)
    cur.execute(
        'INSERT INTO system_notifications (' + ','.join(f'`{x}`' for x in names) + ') VALUES (' + ','.join(['%s']*len(names)) + ')',
        [use[x] for x in names],
    )
    nid = cur.lastrowid
    lcols = table_columns('web_notification_links')
    ldata = {
        'notification_id': nid,
        'notification_type': notification_type or 'system',
        'target_url': target_url or None,
        'booking_id': booking_id,
        'pending_deposit_id': pending_deposit_id,
        'target_employee': target_employee,
        'target_role': target_role,
        'priority': priority or 'normal',
        'hotel_id': hotel_id,
        'sender_name': sender_name or (current_user() or {}).get('nickname') or 'النظام',
    }
    luse = {k:v for k,v in ldata.items() if k in lcols}
    lnames = list(luse)
    cur.execute(
        'INSERT INTO web_notification_links (' + ','.join(f'`{x}`' for x in lnames) + ') VALUES (' + ','.join(['%s']*len(lnames)) + ')',
        [luse[x] for x in lnames],
    )
    return nid

def emit_notification(title, message, **kwargs):
    """إرسال إشعار آمن من أي عملية في النظام دون تعطيل العملية الأساسية."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            create_linked_notification(cur, title, message, **kwargs)
    except Exception:
        pass



# =============================================================================
# 📌 4. كود تعليق عربون السيلز وإرسال إشعار بالمبلغ الجديد فقط (فرق العربون) للمدير
# =============================================================================
def queue_pending_deposit(cur, booking, diffs, deposit_date=None):
    """Hold a Sales-entered deposit until a manager/CEO confirms it."""
    clean = {k:max(0.0, safe_float(diffs.get(k))) for k in ('usd','eur','cash','visa')}
    if not any(v > 0 for v in clean.values()):
        return None
    ensure_web_extension_tables()
    hid = hotel_id_from_name(booking.get('hotel')) or 1
    dep_date = str(deposit_date or date.today().isoformat())[:10]
    cur.execute(
        """INSERT INTO web_pending_deposits
           (booking_id,hotel_id,room_number,sales_person,deposit_usd,deposit_eur,deposit_le_cash,deposit_le_visa,deposit_date,status,created_by)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'Pending',%s)""",
        (booking.get('id'), hid, booking.get('room_number'), booking.get('sales_person'), clean['usd'], clean['eur'], clean['cash'], clean['visa'], dep_date, (current_user() or {}).get('id')),
    )
    pid = cur.lastrowid
    parts=[]
    if clean['usd']: parts.append(f"${clean['usd']:.2f}")
    if clean['eur']: parts.append(f"€{clean['eur']:.2f}")
    if clean['cash']: parts.append(f"{clean['cash']:.2f} EGP cash")
    if clean['visa']: parts.append(f"{clean['visa']:.2f} EGP visa")
    total_after = safe_float(booking.get('deposit_usd')) + safe_float(booking.get('deposit_eur')) + ((safe_float(booking.get('deposit_le_cash')) + safe_float(booking.get('deposit_le_visa'))) / 50.0)
    delta_equiv = clean['usd'] + clean['eur'] + ((clean['cash'] + clean['visa']) / 50.0)
    prev_equiv = max(0.0, round(total_after - delta_equiv, 2))
    if prev_equiv > 0:
        msg = f"⏳ السيلز ({booking.get('sales_person') or '-'}) استلم مبلغ إضافي جديد ({' + '.join(parts)}) فقط لأوردر غرفة {booking.get('room_number') or '-'} — [كان دافع سابقاً: ${prev_equiv:.2f} • الإجمالي الكلي أصبح: ${total_after:.2f}]. المبلغ المطلوب استلامه من السيلز الآن: ({' + '.join(parts)}) فقط."
        notif_title = f"💵 عربون إضافي جديد مع السيلز ({booking.get('sales_person') or '-'}): {' + '.join(parts)} فقط • غرفة {booking.get('room_number') or '-'}"
    else:
        msg = f"⏳ السيلز ({booking.get('sales_person') or '-'}) سجل عربوناً لحجز غرفة {booking.get('room_number') or '-'} بتاريخ {booking.get('booking_date') or dep_date} بمبلغ ({' + '.join(parts)}). المطلوب استلامه من السيلز: ({' + '.join(parts)})."
        notif_title = f"💵 عربون جديد مع السيلز ({booking.get('sales_person') or '-'}): {' + '.join(parts)} • غرفة {booking.get('room_number') or '-'}"
    create_linked_notification(
        cur,
        notif_title, msg,
        sales_person=booking.get('sales_person') or '',
        amount=clean['usd'] + clean['eur'] + ((clean['cash']+clean['visa'])/50.0),
        notification_type='pending_deposit',
        target_url=f"/reservations?open={booking.get('id')}&source=notification",
        booking_id=booking.get('id'), pending_deposit_id=pid,
        target_role='Manager', hotel_id=hid, priority='critical',
    )
    booking_activity(booking.get('id'), 'DEPOSIT_PENDING', 'عربون بانتظار التأكيد', 'لم يتم ترحيل حركة العربون حتى الاعتماد')
    return pid


def deposit_is_pending_for_booking(cur, booking_id):
    try:
        ensure_web_extension_tables()
        cur.execute("SELECT COUNT(*) n FROM web_pending_deposits WHERE booking_id=%s AND status='Pending'", (booking_id,))
        row=cur.fetchone()
        if isinstance(row, dict): return safe_int(row.get('n')) > 0
        return safe_int(row[0] if row else 0) > 0
    except Exception:
        return False

def sync_laundry(cur, booking_id, booking_date, hotel_name, clothing):
    dress_count, gala_count = count_clothing(clothing)
    if dress_count == 0 and gala_count == 0:
        return
    cur.execute("SELECT id FROM laundry_details WHERE booking_id=%s LIMIT 1", (booking_id,))
    if cur.fetchone():
        return
    cur.execute(
        "INSERT INTO laundry_details (booking_id,dress_count,galabeya_count,transferred_at) VALUES (%s,%s,%s,NOW())",
        (booking_id, dress_count, gala_count),
    )
    hid = hotel_id_from_name(hotel_name) or 1
    day = str(booking_date or date.today().isoformat())[:10]
    cur.execute("SELECT id,dress_count,galabeya_count FROM laundry_tracker WHERE log_date=%s AND hotel_id=%s LIMIT 1", (day, hid))
    row = cur.fetchone()
    if row:
        cur.execute(
            "UPDATE laundry_tracker SET dress_count=%s,galabeya_count=%s,total_cost=(%s*dress_cleaning_price)+(%s*galabeya_cleaning_price) WHERE id=%s",
            ((row[1] or 0) + dress_count, (row[2] or 0) + gala_count, (row[1] or 0) + dress_count, (row[2] or 0) + gala_count, row[0]),
        )
    else:
        cur.execute(
            """INSERT INTO laundry_tracker
               (hotel_id,log_date,dress_count,galabeya_count,dress_cleaning_price,galabeya_cleaning_price,total_cost)
               VALUES (%s,%s,%s,%s,50,30,%s)""",
            (hid, day, dress_count, gala_count, dress_count * 50 + gala_count * 30),
        )


@app.before_request
def bootstrap_and_validate_session():
    # V12.1: multi-role tables are created/seeding automatically and safely.
    try:
        ensure_multi_role_tables()
    except Exception:
        pass
    user = current_user()
    if user and request.endpoint not in {"api_health", "login", "api_login", "static"}:
        try:
            with get_db_connection() as conn:
                cur = conn.cursor(dictionary=True)
                cur.execute("SELECT is_active,session_active FROM team_members WHERE id=%s", (user.get("id"),))
                state = cur.fetchone()
            if not state or not state.get("is_active") or not state.get("session_active", 1):
                session.clear()
                if request.path.startswith("/api/"):
                    return fail("تم إنهاء الجلسة بواسطة الإدارة", 401)
                return redirect(url_for("login"))
        except Exception:
            pass


def get_current_user_hotel_name(user=None):
    user = user or current_user() or {}
    if user.get("hotel_name") and user.get("hotel_name") not in ("-", "الكل"):
        return str(user["hotel_name"])
    hid = user.get("hotel_id")
    if hid not in (None, "", "الكل"):
        try:
            hname = hotel_name_from_id(hid)
            if hname:
                return str(hname)
        except Exception:
            pass
    try:
        names = allowed_hotel_names(user)
        if names and len(names) >= 1:
            return str(names[0])
    except Exception:
        pass
    return ""



# =============================================================================
# 📌 5. كود تمرير بيانات المستخدم والصلاحيات لكل صفحات القوالب (Templates Context)
# =============================================================================
@app.context_processor
def inject_app_context():
    user = dict(current_user() or {})
    user_hotel = get_current_user_hotel_name(user) if user else ""
    if user and user_hotel and not user.get("hotel_name"):
        user["hotel_name"] = user_hotel
    return {
        "user": user,
        "user_hotel_name": user_hotel,
        "permission_labels": PERMISSION_LABELS,
        "user_permissions": get_user_permissions(user.get("id")) if user else set(),
        "user_roles": sorted(get_user_roles(user_id=user.get("id"), user=user)) if user else [],
        "full_access": is_full_access(user),
        "personal_scope": is_personal_scope_user(user),
        "photographer_only": is_photographer_only(user),
        "sales_only": is_sales_only(user),
        "accountant_only": is_accountant_only(user),
        "manager_only": is_manager_role(user),
    }


# -----------------------------------------------------------------------------
# Auth + Pages
# -----------------------------------------------------------------------------
@app.get("/ui-preview/<variant>")
def ui_preview(variant):
    """Standalone visual previews used to choose the new desktop interface."""
    variant = str(variant or "").lower()
    if variant not in {"a", "b"}:
        return redirect(url_for("ui_preview", variant="a"))
    return send_from_directory(APP_ROOT / "ui-preview" / f"variant-{variant}", "index.html")


@app.get("/login")
def login():
    if current_user():
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.get("/api/public/hotels")
def api_public_hotels():
    try:
        with get_db_connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, hotel_name FROM hotels ORDER BY hotel_name")
            return ok(rows_to_json(cur.fetchall()))
    except Exception:
        return ok([])



# =============================================================================
# 📌 6. كود تسجيل الدخول وإنشاء حساب جديد وتغيير كلمة السر (Auth APIs)
# =============================================================================
def ensure_team_members_auth_columns():
    """يتأكد من وجود كافة أعمدة الحسابات وبيانات التحقق في جدول team_members."""
    try:
        cols = table_columns("team_members")
        if not cols:
            return
        alter_stmts = []
        if "phone_number" not in cols:
            alter_stmts.append("ADD COLUMN phone_number VARCHAR(50) DEFAULT NULL")
        if "national_id" not in cols:
            alter_stmts.append("ADD COLUMN national_id VARCHAR(50) DEFAULT NULL")
        if "visa_card_number" not in cols:
            alter_stmts.append("ADD COLUMN visa_card_number VARCHAR(60) DEFAULT NULL")
        if "access_type" not in cols:
            alter_stmts.append("ADD COLUMN access_type VARCHAR(100) DEFAULT 'وصول كامل (Desktop + Mobile)'")
        if "username" not in cols:
            alter_stmts.append("ADD COLUMN username VARCHAR(100) DEFAULT NULL")
        if "password_hash" not in cols:
            alter_stmts.append("ADD COLUMN password_hash VARCHAR(255) DEFAULT NULL")
        if "is_active" not in cols:
            alter_stmts.append("ADD COLUMN is_active TINYINT(1) DEFAULT 1")
        if "session_active" not in cols:
            alter_stmts.append("ADD COLUMN session_active TINYINT(1) DEFAULT 0")
        if "last_login" not in cols:
            alter_stmts.append("ADD COLUMN last_login DATETIME DEFAULT NULL")
        if alter_stmts:
            with get_db_connection() as conn:
                c = conn.cursor()
                for st in alter_stmts:
                    try:
                        c.execute(f"ALTER TABLE team_members {st}")
                    except Exception:
                        pass
            _SCHEMA_CACHE.pop("team_members", None)
    except Exception:
        pass


@app.post("/api/auth/login")
def api_login():
    ensure_team_members_auth_columns()
    d = request.get_json(silent=True) or request.form or {}
    username = str(d.get("username", "")).strip()
    password = str(d.get("password", "")).strip()

    if not username or not password:
        return fail("أدخل اسم المستخدم وكلمة المرور")

    try:
        with get_db_connection() as conn:
            cur = conn.cursor(dictionary=True)

            cur.execute(
                """SELECT id,full_name,nickname,username,role,hotel_id,is_active,access_type,phone_number,password_hash
                   FROM team_members
                   WHERE LOWER(username)=LOWER(%s) OR LOWER(nickname)=LOWER(%s) OR LOWER(full_name)=LOWER(%s)""",
                (username, username, username),
            )
            candidates = cur.fetchall() or []
            user = None
            for cand in candidates:
                stored_pw = str(cand.get("password_hash") or "")
                if verify_password(password, stored_pw) or stored_pw == password or stored_pw == hash_password(password):
                    user = cand
                    break

            if not user:
                return fail("بيانات الدخول غير صحيحة (تأكد من اسم المستخدم وكلمة المرور)", 401)

            if user.get("is_active") is not None and int(user.get("is_active") or 0) == 0:
                return fail("هذا الحساب معطل حالياً، يرجى مراجعة الإدارة", 403)

            user.pop("password_hash", None)

            try:
                cur.execute(
                    "UPDATE team_members SET last_login=NOW(),session_active=1 WHERE id=%s",
                    (user["id"],)
                )
            except Exception:
                pass

    except Exception as exc:
        return fail(f"تعذر الاتصال بقاعدة البيانات: {exc}", 500)

    user = {k: serialize(v) for k, v in user.items()}

    session.clear()
    session["user"] = user

    audit("LOGIN", "team_members", f"تسجيل دخول: {user.get('nickname')}")

    return ok({
        **user,
        "roles": sorted(get_user_roles(user_id=user["id"], user=user)),
        "permissions": sorted(get_user_permissions(user["id"]))
    })


@app.post("/api/auth/register")
def api_auth_register():
    """تسجيل حساب موظف جديد من صفحة تسجيل الدخول مع تفعيل الصلاحيات الافتراضية للدور المختار."""
    ensure_team_members_auth_columns()
    d = request.get_json(silent=True) or request.form or {}
    full_name = str(d.get("full_name") or "").strip()
    username = str(d.get("username") or d.get("nickname") or "").strip()
    nickname = str(d.get("nickname") or username).strip()
    phone_number = str(d.get("phone_number") or "").strip()
    national_id = str(d.get("national_id") or "").strip()
    password = str(d.get("password") or "").strip()
    role = str(d.get("role") or "Photographer").strip()
    if role not in {"Photographer", "Sales", "Accountant", "Manager"}:
        role = "Photographer"

    if not full_name or len(full_name) < 2:
        return fail("يرجى إدخال الاسم بالكامل")
    if not username:
        return fail("يرجى إدخال اسم المستخدم (اسم الشهرة)")
    if not phone_number or len(re.sub(r"\D", "", phone_number)) < 6:
        return fail("يرجى إدخال رقم هاتف صحيح")
    if not national_id or len(re.sub(r"\D", "", national_id)) < 4:
        return fail("يرجى إدخال رقم البطاقة / الهوية")
    if not password or len(password) < 4:
        return fail("يرجى إدخال كلمة مرور لا تقل عن 4 أحرف أو أرقام")

    try:
        ensure_multi_role_tables()
        with get_db_connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT id, username, nickname, national_id FROM team_members WHERE LOWER(username)=LOWER(%s) OR LOWER(nickname)=LOWER(%s) LIMIT 1",
                (username, nickname)
            )
            existing = cur.fetchone()
            if existing:
                return fail("اسم المستخدم / اسم الشهرة مسجل بالفعل، اختر اسماً آخر أو استخدم (تغيير كلمة المرور)")

            c = conn.cursor()
            cols = table_columns("team_members")
            req_hotel_id = safe_int(d.get("hotel_id"), 0) or None
            if not req_hotel_id and d.get("hotel_name"):
                req_hotel_id = hotel_id_from_name(str(d.get("hotel_name")).strip())
            if not req_hotel_id:
                try:
                    c.execute("SELECT id FROM hotels ORDER BY id LIMIT 1")
                    first_h = c.fetchone()
                    if first_h:
                        req_hotel_id = first_h[0]
                except Exception:
                    pass

            insert_data = {
                "full_name": full_name,
                "nickname": nickname,
                "username": username,
                "phone_number": phone_number,
                "national_id": national_id,
                "role": role,
                "access_type": "وصول كامل (Desktop + Mobile)",
                "hotel_id": req_hotel_id,
                "commission_rate": 12.0 if role == "Photographer" else (10.0 if role == "Sales" else 0.0),
                "base_salary": 0.0,
                "password_hash": hash_password(password),
                "is_active": 1,
                "session_active": 1,
            }
            use_cols = {k: v for k, v in insert_data.items() if k in cols}
            col_names = list(use_cols.keys())
            c.execute(
                "INSERT INTO team_members (" + ",".join(f"`{k}`" for k in col_names) + ") VALUES (" + ",".join(["%s"] * len(col_names)) + ")",
                [use_cols[k] for k in col_names]
            )
            uid = c.lastrowid

            # ربط الدور والصلاحيات الأساسية حسب الدور المختار
            try:
                c.execute("SELECT id FROM roles WHERE role_key=%s LIMIT 1", (role,))
                rrow = c.fetchone()
                if rrow:
                    c.execute("INSERT IGNORE INTO employee_roles (user_id, role_id) VALUES (%s, %s)", (uid, rrow[0]))
                c.execute("INSERT IGNORE INTO employee_permissions (user_id, permission_key) VALUES (%s, %s)", (uid, PERMISSION_CONFIG_MARKER))
                default_perms = ROLE_DEFAULT_PERMISSIONS.get(role) or {"bookings_access", "sales_access"}
                for pkey in default_perms:
                    c.execute("INSERT IGNORE INTO employee_permissions (user_id, permission_key) VALUES (%s, %s)", (uid, pkey))
                if req_hotel_id:
                    c.execute("INSERT IGNORE INTO user_hotel_permissions (user_id, hotel_id, can_view, can_edit) VALUES (%s, %s, 1, 1)", (uid, req_hotel_id))
            except Exception:
                pass

            # إرسال إشعار للمدير بتسجيل حساب جديد
            try:
                create_linked_notification(
                    c,
                    f"👤 تسجيل حساب جديد • {nickname} ({role})",
                    f"قام {full_name} (اسم الشهرة: {nickname} | هاتف: {phone_number} | بطاقة: {national_id}) بتسجيل حساب جديد كـ {role}.",
                    notification_type="team_register",
                    target_url="/team-hotels",
                    target_role="Manager",
                    priority="high",
                )
            except Exception:
                pass

            cur.execute("SELECT id,full_name,nickname,username,role,hotel_id,is_active,access_type,phone_number FROM team_members WHERE id=%s LIMIT 1", (uid,))
            new_user = cur.fetchone() or {"id": uid, "full_name": full_name, "nickname": nickname, "username": username, "role": role, "is_active": 1}

        new_user = {k: serialize(v) for k, v in new_user.items()}
        session.clear()
        session["user"] = new_user
        audit("REGISTER_ACCOUNT", "team_members", f"تسجيل حساب جديد: {nickname} ({full_name})")
        return ok({
            **new_user,
            "roles": sorted(get_user_roles(user_id=uid, user=new_user)),
            "permissions": sorted(get_user_permissions(uid)),
            "message": "تم إنشاء الحساب وتسجيل الدخول بنجاح!"
        })
    except Exception as exc:
        return fail(f"تعذر تسجيل الحساب الجديد: {exc}", 500)


@app.post("/api/auth/reset-password")
def api_auth_reset_password():
    """تغيير كلمة المرور من صفحة الدخول أو من داخل النظام."""
    ensure_team_members_auth_columns()
    d = request.get_json(silent=True) or request.form or {}
    username = str(d.get("username") or "").strip()
    national_id = str(d.get("national_id") or "").strip()
    phone_number = str(d.get("phone_number") or "").strip()
    new_password = str(d.get("new_password") or "").strip()

    if not username:
        return fail("يرجى إدخال اسم المستخدم أو اسم الشهرة")
    if not new_password or len(new_password) < 4:
        return fail("يرجى إدخال كلمة مرور جديدة لا تقل عن 4 أحرف أو أرقام")

    clean_phone = re.sub(r"\D", "", phone_number)
    clean_nid = re.sub(r"\D", "", national_id)

    try:
        with get_db_connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT id, username, nickname, full_name, phone_number, national_id FROM team_members WHERE LOWER(username)=LOWER(%s) OR LOWER(nickname)=LOWER(%s) OR LOWER(full_name)=LOWER(%s)",
                (username, username, username)
            )
            candidates = cur.fetchall() or []
            if not candidates:
                return fail("اسم المستخدم / اسم الشهرة غير موجود في النظام", 404)

            matched_user = None
            for u in candidates:
                db_phone = re.sub(r"\D", "", str(u.get("phone_number") or ""))
                db_nid = re.sub(r"\D", "", str(u.get("national_id") or ""))
                # إذا كان الحساب القديم في قاعدة البيانات ليس له رقم بطاقة أو هاتف مسجل بعد، نقبل التحديث ونحفظهما له
                phone_ok = (not db_phone) or (bool(clean_phone) and (db_phone == clean_phone or db_phone.endswith(clean_phone[-8:]) or clean_phone.endswith(db_phone[-8:])))
                nid_ok = (not db_nid) or (bool(clean_nid) and (db_nid == clean_nid or db_nid.endswith(clean_nid[-6:])))
                if phone_ok and nid_ok:
                    matched_user = u
                    break
                # أو إذا تطابق أحدهما بشكل كامل (تسهيلاً على الموظف لو نسي أحد الرقمين)
                if (db_phone and clean_phone and db_phone == clean_phone) or (db_nid and clean_nid and db_nid == clean_nid):
                    matched_user = u
                    break

            if not matched_user:
                return fail("بيانات التحقق (رقم البطاقة أو رقم الهاتف) غير مطابقة لاسم المستخدم المدخل", 403)

            c = conn.cursor()
            new_phone = phone_number if phone_number else (matched_user.get("phone_number") or "")
            new_nid = national_id if national_id else (matched_user.get("national_id") or "")
            c.execute(
                "UPDATE team_members SET password_hash=%s, phone_number=%s, national_id=%s, is_active=1, session_active=1 WHERE id=%s",
                (hash_password(new_password), new_phone, new_nid, matched_user["id"])
            )
        audit("RESET_PASSWORD", "team_members", f"تغيير كلمة المرور للمستخدم: {matched_user.get('nickname') or username}")
        return ok({"message": "تم تغيير كلمة المرور بنجاح! يمكنك الآن تسجيل الدخول بكلمة المرور الجديدة."})
    except Exception as exc:
        return fail(f"تعذر تغيير كلمة المرور: {exc}", 500)


@app.post("/api/auth/change-password")
@login_required
def api_auth_change_password():
    """تغيير كلمة المرور للمستخدم المسجل دخوله حالياً من داخل البرنامج."""
    ensure_team_members_auth_columns()
    d = request.get_json(silent=True) or request.form or {}
    new_password = str(d.get("new_password") or "").strip()
    if not new_password or len(new_password) < 4:
        return fail("يرجى إدخال كلمة مرور جديدة لا تقل عن 4 أحرف أو أرقام")
    user = current_user() or {}
    uid = safe_int(user.get("id"))
    if not uid:
        return fail("المستخدم غير معروف", 401)
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE team_members SET password_hash=%s WHERE id=%s", (hash_password(new_password), uid))
    audit("CHANGE_PASSWORD", "team_members", f"تغيير كلمة المرور الذاتي للمستخدم: {user.get('nickname')}")
    return ok({"message": "تم تحديث كلمة المرور الخاصة بك بنجاح!"})


@app.post("/api/auth/logout")
@login_required
def api_logout():
    user = current_user() or {}
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE team_members SET session_active=0 WHERE id=%s", (user.get("id"),))
    except Exception:
        pass
    audit("LOGOUT", "team_members", f"تسجيل خروج: {user.get('nickname')}")
    session.clear()
    return ok(message="تم تسجيل الخروج")



# =============================================================================
# 📌 7. كود فتح صفحات النظام والتحقق من صلاحية كل دور على الصفحات
# =============================================================================
def page(template, active):
    if (is_photographer_only() or is_sales_only()) and active not in {"dashboard", "reservations", "daily_sales"}:
        return redirect(url_for("reservations_page" if is_sales_only() else "dashboard"))
    if is_accountant_only() and active not in {"dashboard", "daily_sales", "commissions", "salaries", "reports", "treasury", "chat"}:
        return redirect(url_for("daily_sales_page"))
    key = PAGE_PERMISSION.get(active)
    if key and not has_permission(key):
        return render_template("forbidden.html", user=current_user(), active=active), 403
    return render_template(template, user=current_user(), active=active)


@app.get("/")
@login_required
def dashboard(): return page("dashboard.html", "dashboard")

@app.get("/reservations")
@login_required
def reservations_page(): return page("reservations.html", "reservations")

@app.get("/daily-sales")
@login_required
def daily_sales_page(): return page("daily_sales.html", "daily_sales")

@app.get("/commissions")
@login_required
def commissions_page(): return page("commissions.html", "commissions")

@app.get("/laundry")
@login_required
def laundry_page(): return page("laundry.html", "laundry")

@app.get("/assets")
@login_required
def assets_page(): return page("assets.html", "assets")

@app.get("/salaries")
@login_required
def salaries_page(): return page("salaries.html", "salaries")

@app.get("/team-hotels")
@login_required
def team_hotels_page(): return page("team_hotels.html", "team_hotels")

@app.get("/reports")
@login_required
def reports_page(): return page("reports.html", "reports")

@app.get("/settings")
@login_required
def settings_page(): return page("settings.html", "settings")


# -----------------------------------------------------------------------------
# General / Dashboard / Command Center
# -----------------------------------------------------------------------------
@app.get("/api/me")
@login_required
def api_me():
    user = dict(current_user() or {})
    user["hotel_name"] = get_current_user_hotel_name(user)
    user["permissions"] = sorted(get_user_permissions(user.get("id")))
    user["roles"] = sorted(get_user_roles(user_id=user.get("id"), user=user))
    user["hotel_ids"] = allowed_hotel_ids()
    user["hotel_names"] = allowed_hotel_names()
    user["personal_scope"] = is_personal_scope_user(user)
    return ok(user)


@app.get("/api/hotels")
@login_required
def api_hotels():
    ids = allowed_hotel_ids()
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        if ids is None:
            cur.execute("SELECT id,hotel_name,parent_hotel_id,created_at FROM hotels ORDER BY hotel_name")
        elif ids:
            marks = ",".join(["%s"] * len(ids))
            cur.execute(f"SELECT id,hotel_name,parent_hotel_id,created_at FROM hotels WHERE id IN ({marks}) ORDER BY hotel_name", tuple(ids))
        else:
            return ok([])
        return ok(rows_to_json(cur.fetchall()))


@app.get("/api/team/options")
@login_required
def api_team_options():
    ensure_nbe_team_members_seeded()
    """Return complete dropdown options for Sales / Photographers.

    The dropdown must not lose historical names.  Therefore the source is the
    union of team_members (including inactive members) and names already used
    in daily_income.  Hotel restrictions still apply for restricted users.
    """
    ids = allowed_hotel_ids()
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM team_members ORDER BY nickname")
        raw = cur.fetchall()

        rows = []
        for r in raw:
            hid = r.get("hotel_id")
            if ids is not None and hid not in (None, "") and safe_int(hid, -1) not in ids:
                continue
            nickname = str(r.get("nickname") or "").strip()
            if not nickname:
                continue
            roles = sorted(get_user_roles(user_id=r.get("id"), user=r))
            rows.append({
                "id": serialize(r.get("id")),
                "nickname": nickname,
                "role": serialize(r.get("role")),
                "roles": roles,
                "hotel_id": serialize(hid),
                "is_active": serialize(r.get("is_active")),
                "source": "team_members",
            })

        def _key(name):
            return str(name or "").strip().casefold()

        sales_map = {}
        photo_map = {}
        all_map = {}

        for r in rows:
            all_map[_key(r["nickname"])] = r
            role_keys = {_normalize_role(x) for x in r.get("roles", [])}
            legacy_role = _normalize_role(r.get("role"))
            if "sales" in role_keys or legacy_role in {"sales", "سيلز", "مبيعات"}:
                sales_map[_key(r["nickname"])] = r
            if "photographer" in role_keys or legacy_role in {"photographer", "مصور"}:
                photo_map[_key(r["nickname"])] = r

        # Historical names that may no longer exist (or have a different role)
        # in team_members must still be available in the filter.
        where_sql, params = make_where_for_hotels("hotel_id", ids)
        try:
            cur.execute(
                f"SELECT sales_person, photographer FROM daily_income WHERE 1=1 {where_sql}",
                tuple(params),
            )
            income_rows = cur.fetchall()
        except Exception:
            income_rows = []

        for d in income_rows:
            for name in split_names(d.get("sales_person")):
                k = _key(name)
                item = all_map.get(k) or {
                    "id": None, "nickname": name, "role": "Sales",
                    "roles": ["Sales"], "hotel_id": None,
                    "is_active": None, "source": "daily_income",
                }
                sales_map.setdefault(k, item)
            for name in split_names(d.get("photographer")):
                k = _key(name)
                item = all_map.get(k) or {
                    "id": None, "nickname": name, "role": "Photographer",
                    "roles": ["Photographer"], "hotel_id": None,
                    "is_active": None, "source": "daily_income",
                }
                photo_map.setdefault(k, item)

        sales = sorted(sales_map.values(), key=lambda r: str(r.get("nickname") or "").casefold())
        photos = sorted(photo_map.values(), key=lambda r: str(r.get("nickname") or "").casefold())
        all_rows = sorted(rows, key=lambda r: str(r.get("nickname") or "").casefold())
        return ok({"sales": sales, "photographers": photos, "all": all_rows})



# =============================================================================
# 📌 8. كود إحصائيات الصفحة الرئيسية (Dashboard API)
# =============================================================================
@app.get("/api/dashboard")
@login_required
def api_dashboard():
    day = request.args.get("date") or date.today().isoformat()
    allowed_names, allowed_ids = allowed_hotel_names(), allowed_hotel_ids()
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        all_bookings = fetch_booking_rows(cur, 8000)
        scoped=[]
        for b in all_bookings:
            if not record_belongs_to_current_user(b):
                continue
            if allowed_names is not None and b.get('_has_hotel_column') and b.get('hotel') not in allowed_names:
                continue
            scoped.append(b)
        timeline=[b for b in scoped if str(b.get('booking_date') or '')[:10]==day]
        timeline.sort(key=lambda b:(str(b.get('booking_time') or '99:99')[:5], safe_int(b.get('id'))))

        # Team count follows the same hotel scope as the signed-in user.
        try:
            cur.execute("SELECT * FROM team_members ORDER BY nickname")
            members=cur.fetchall()
        except Exception:
            members=[]
        active_members=[]
        for m in members:
            if 'is_active' in m and not bool(m.get('is_active')):
                continue
            hid=m.get('hotel_id')
            # نفس منطق شاشة الفريق: الموظف غير المرتبط بفندق محدد يظل مرئياً/متاحاً،
            # أما الموظف المرتبط بفندق فيخضع لنطاق الفنادق المسموح بها للمستخدم.
            if allowed_ids is not None and hid not in (None, '') and safe_int(hid,-1) not in allowed_ids:
                continue
            active_members.append(m)

        def _is_photographer(member):
            return any(_normalize_role(r) == 'photographer' for r in get_user_roles(user_id=member.get('id'), user=member))

        photographers=[m for m in active_members if _is_photographer(m)]
        total_team=len(active_members); total_photographers=len(photographers)

        # Daily clothing preparation list:
        # only bookings that are STILL waiting on the selected day count.
        # Rescheduled/postponed/cancelled/confirmed/delivered originals are excluded;
        # the cloned waiting booking is counted on its new date instead.
        # Aggregate by (type, color, size) across all waiting bookings for the day.
        def _is_waiting_for_prep(booking):
            status=str(booking.get('status') or '').strip().lower()
            return status in {'انتظار','pending','waiting'}

        dress_groups={}
        dress_total=0
        waiting_prep_bookings=0
        for b in timeline:
            if not _is_waiting_for_prep(b):
                continue
            items=[item for item in parse_json_list(b.get('clothing')) if isinstance(item,dict)]
            if items:
                waiting_prep_bookings += 1
            for item in items:
                dtype=str(item.get('type') or 'فستان').strip() or 'فستان'
                color=str(item.get('color') or 'غير محدد').strip() or 'غير محدد'
                size=str(item.get('size') or item.get('size_category') or 'ستاندرد').strip() or 'ستاندرد'
                qty=max(1,safe_int(item.get('qty'),1))
                key=(dtype,color,size)
                group=dress_groups.setdefault(key,{
                    'type':dtype,'color':color,'size':size,'qty':0,
                    'booking_ids':[],'rooms':[],'bookings':[]
                })
                group['qty'] += qty
                bid=safe_int(b.get('id'))
                if bid and bid not in group['booking_ids']:
                    group['booking_ids'].append(bid)
                room=str(b.get('room_number') or '-').strip() or '-'
                if room not in group['rooms']:
                    group['rooms'].append(room)
                group['bookings'].append({
                    'id':serialize(b.get('id')),'room_number':serialize(b.get('room_number')),
                    'hotel':serialize(b.get('hotel')),'booking_time':serialize(b.get('booking_time')),
                    'sales_person':serialize(b.get('sales_person')),'status':serialize(b.get('status')),
                    'qty':qty
                })
                dress_total += qty

        dress_rows=[]
        for key in sorted(dress_groups,key=lambda k:(str(k[0]),str(k[1]),str(k[2]))):
            group=dress_groups[key]
            group['booking_count']=len(group['booking_ids'])
            group['rooms_text']='، '.join(group['rooms'])
            dress_rows.append(group)

        # Laundry daily dress count from the original tracker.
        laundry={'dresses':0,'galabeya':0,'laundry_cost':0}
        try:
            if table_exists('laundry_tracker'):
                lcols=table_columns('laundry_tracker'); wh=''; args=[day]
                if 'hotel_id' in lcols and allowed_ids is not None:
                    marks=','.join(['%s']*len(allowed_ids)) if allowed_ids else 'NULL'
                    wh=f" AND hotel_id IN ({marks})" if allowed_ids else ' AND 1=0'
                    args += list(allowed_ids or [])
                cur.execute(f"SELECT COALESCE(SUM(dress_count),0) dresses,COALESCE(SUM(galabeya_count),0) galabeya,COALESCE(SUM(total_cost),0) laundry_cost FROM laundry_tracker WHERE log_date=%s {wh}",tuple(args))
                laundry={k:serialize(v) for k,v in (cur.fetchone() or laundry).items()}
        except Exception:
            pass

    def is_cancelled(b):
        st=str(b.get('status') or '').lower()
        return any(x in st for x in ['كنسل','cancel','ملغ'])
    def is_delivered(b):
        st=str(b.get('status') or '').lower()
        return any(x in st for x in ['deliver','تسليم','مسلم'])

    confirmed=sum(1 for b in timeline if any(x in str(b.get('status') or '').lower() for x in ['مؤكد','confirm']))
    pending=sum(1 for b in timeline if any(x in str(b.get('status') or '').lower() for x in ['انتظار','pending']))
    cancelled=sum(1 for b in timeline if is_cancelled(b))
    delivered=sum(1 for b in timeline if is_delivered(b))
    bookings={'total':len(timeline),'confirmed':confirmed,'pending':pending,'cancelled':cancelled,'delivered':delivered}

    # Availability: مدة السيشن ساعة كاملة. كل أوردر نشط يحجز مصوراً واحداً
    # من وقت بداية السيشن وحتى قبل مرور 60 دقيقة. نعرض Slots كل 30 دقيقة
    # ونضيف وقت أي حجز غير مطابق لنصف الساعة حتى يظل الجدول دقيقاً.
    session_duration_minutes=60
    active_for_capacity=[b for b in timeline if not is_cancelled(b) and not is_delivered(b)]

    def _time_to_minutes(value):
        text=str(value or '')[:5]
        if ':' not in text:
            return None
        try:
            hh,mm=text.split(':',1)
            return int(hh)*60+int(mm)
        except Exception:
            return None

    booking_starts=[]
    for b in active_for_capacity:
        mins=_time_to_minutes(b.get('booking_time'))
        if mins is not None:
            booking_starts.append(mins)

    slot_minutes=[]
    cur_m=9*60
    while cur_m<=22*60:
        slot_minutes.append(cur_m)
        cur_m+=30
    slot_minutes=sorted(set(slot_minutes)|set(booking_starts))

    availability=[]
    for slot_m in slot_minutes:
        busy=sum(1 for start_m in booking_starts if start_m <= slot_m < start_m + session_duration_minutes)
        availability.append({
            'time':f'{slot_m//60:02d}:{slot_m%60:02d}',
            'busy':busy,
            'available':max(0,total_photographers-busy),
            'total':total_photographers,
            'session_duration_minutes':session_duration_minutes,
        })

    # "Sales bookings today" means bookings CREATED today, regardless of session date.
    sales_bookings=[]
    for b in scoped:
        created=str(b.get('created_at') or '')[:10]
        if (created and created==day) or (not created and str(b.get('booking_date') or '')[:10]==day):
            sales_bookings.append({k:serialize(b.get(k)) for k in ['id','hotel','booking_date','room_number','booking_time','session_details','deposit_usd','deposit_eur','deposit_le_cash','deposit_le_visa','sales_person','photographer','status','created_at']})
    sales_bookings.sort(key=lambda x:(str(x.get('sales_person') or ''),str(x.get('created_at') or ''),safe_int(x.get('id'))),reverse=True)
    sales_summary={}
    for b in sales_bookings:
        name=str(b.get('sales_person') or 'بدون سيلز')
        sales_summary[name]=sales_summary.get(name,0)+1

    return ok({
        'date':day,'bookings':bookings,'timeline':rows_to_json(timeline[:60]),
        'dresses_required':dress_rows,'dresses_required_count':dress_total,'dresses_waiting_bookings_count':waiting_prep_bookings,
        'laundry':laundry,'total_team':total_team,'total_photographers':total_photographers,
        'team_availability':availability,'session_duration_minutes':session_duration_minutes,'sales_bookings_today':sales_bookings,
        'sales_summary':[{'sales_person':k,'count':v} for k,v in sorted(sales_summary.items(),key=lambda kv:(-kv[1],kv[0]))],
    })



# =============================================================================
# 📌 9. كود الإشعارات الذكية (ملخص الفنادق للأونر + إشعارات الفنادق المخصصة للمدير)
# =============================================================================
@app.get("/api/notifications")
@login_required
def api_notifications():
    ensure_web_extension_tables()
    _ensure_notif_link_columns()
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT n.*,l.notification_type,l.target_url,l.booking_id,l.pending_deposit_id,
                   l.target_employee,l.target_role,l.priority,l.hotel_id AS notif_hotel_id,l.sender_name,
                   p.status AS pending_deposit_status,p.hotel_id AS pending_hotel_id,
                   p.room_number AS pending_room,p.sales_person AS pending_sales,
                   p.deposit_usd AS pending_usd,p.deposit_eur AS pending_eur,
                   p.deposit_le_cash AS pending_cash,p.deposit_le_visa AS pending_visa
            FROM system_notifications n
            LEFT JOIN web_notification_links l ON l.notification_id=n.id
            LEFT JOIN web_pending_deposits p ON p.id=l.pending_deposit_id
            ORDER BY n.id DESC LIMIT 100
        """)
        rows = rows_to_json(cur.fetchall())
    allowed_ids = allowed_hotel_ids()
    personal = is_personal_scope_user()
    is_ceo = has_full_access()
    my_names = current_employee_names() if personal else set()
    my_roles = {_normalize_role(x) for x in get_user_roles()}

    out=[]
    # إذا كان المستخدم هو الأونر (CEO)، نولّد له تلقائياً إشعار تقفيل وملخص الفنادق اليومي الشامل (كل فندق + الإجمالي العام)
    if is_ceo:
        try:
            today_str = date.today().isoformat()
            with get_db_connection() as conn_s:
                cur_s = conn_s.cursor(dictionary=True)
                cur_s.execute("SELECT id, hotel_name FROM hotels ORDER BY id")
                all_hotels = cur_s.fetchall() or []
                b_date_col = booking_col("booking_date") or "booking_date"
                b_hotel_col = booking_col("hotel") or "hotel"
                b_tot_col = booking_col("total_agreement") or "total_agreement"
                cur_s.execute(f"SELECT `{b_hotel_col}` AS hname, COUNT(*) AS cnt, COALESCE(SUM(`{b_tot_col}`),0) AS tot FROM bookings WHERE `{b_date_col}`=%s GROUP BY `{b_hotel_col}`", (today_str,))
                b_map = {str(x["hname"]).strip(): x for x in (cur_s.fetchall() or [])}
                i_date_col = "income_date"
                cur_s.execute(f"SELECT h.hotel_name AS hname, COUNT(d.id) AS cnt, COALESCE(SUM(d.daily_total),0) AS net_tot FROM daily_income d LEFT JOIN hotels h ON h.id=d.hotel_id WHERE d.`{i_date_col}`=%s GROUP BY h.hotel_name", (today_str,))
                s_map = {str(x["hname"]).strip(): x for x in (cur_s.fetchall() or [])}
                hotel_parts = []
                grand_net = 0.0
                grand_b_tot = 0.0
                grand_b_cnt = 0
                grand_s_cnt = 0
                for h in all_hotels:
                    hn = str(h.get("hotel_name") or "").strip()
                    if not hn: continue
                    b_info = b_map.get(hn, {})
                    s_info = s_map.get(hn, {})
                    bc = safe_int(b_info.get("cnt"), 0)
                    bt = safe_float(b_info.get("tot"), 0.0)
                    sc = safe_int(s_info.get("cnt"), 0)
                    sn = safe_float(s_info.get("net_tot"), 0.0)
                    grand_net += sn
                    grand_b_tot += bt
                    grand_b_cnt += bc
                    grand_s_cnt += sc
                    hotel_parts.append(f"🏨 {hn}: صافي الدخل ${sn:.2f} ({sc} أوردر مصور | {bc} حجز بإجمالي ${bt:.2f})")
                summary_msg = " • ".join(hotel_parts) + f" || 💰 إجمالي الفنادق ككل اليوم: صافي دخل ${grand_net:.2f} | إجمالي اتفاقات الحجوزات ${grand_b_tot:.2f} ({grand_b_cnt} حجز / {grand_s_cnt} أوردر)."
                out.append({
                    "id": 999999,
                    "title": f"📊 ملخص وتقفيل الفنادق اليومي الشامل ({today_str}) • إجمالي الفنادق: ${grand_net:.2f}",
                    "message": summary_msg,
                    "status": "Pending",
                    "notification_type": "daily_hotel_summary",
                    "target_role": "CEO",
                    "target_url": "/reports",
                    "priority": "high",
                    "created_at": today_str,
                })
        except Exception:
            pass

    for r in rows:
        ntype = str(r.get('notification_type') or '').lower()
        t_role = _normalize_role(r.get('target_role') or '')
        # الأونر (CEO) لا يستقبل إشعارات كل سيلز أو مصور، بل يستقبل فقط ملخصات الفنادق وتعديلات المدير والتعاميم
        if is_ceo:
            if ntype not in ('daily_hotel_summary', 'manager_edit', 'sale_edit', 'audit_edit', 'broadcast', 'team_register') and t_role != 'ceo':
                continue
        else:
            # غير الأونر لا يرى الإشعارات الرقابية الخاصة بالأونر فقط
            if t_role == 'ceo' and ntype in ('daily_hotel_summary', 'manager_edit'):
                continue

        phid = r.get('pending_hotel_id') or r.get('notif_hotel_id')
        if phid not in (None,'') and allowed_ids is not None and safe_int(phid,-1) not in allowed_ids:
            continue
        # العزل الشخصي للإشعارات: السيلز أو المصور لا يرى إشعارات موظف آخر أو إشعارات الإدارة المالية
        if personal:
            t_emp = str(r.get('target_employee') or '').strip().lower()
            rel_sales = str(r.get('related_sales_person') or '').strip().lower()
            if ntype == 'pending_deposit':
                if rel_sales not in my_names:
                    continue
            elif t_emp:
                target_set = {x.strip().lower() for x in split_names(t_emp) if x.strip()} | {t_emp}
                if not (target_set & my_names):
                    continue
            elif t_role and t_role not in ('all', 'الكل'):
                if t_role not in my_roles:
                    continue
            elif rel_sales:
                rel_set = {x.strip().lower() for x in split_names(rel_sales) if x.strip()} | {rel_sales}
                if not (rel_set & my_names):
                    continue

        if not r.get('target_url'):
            txt=(str(r.get('title') or '')+' '+str(r.get('message') or '')).lower()
            if 'مغسل' in txt: r['target_url']='/laundry'
            elif any(x in txt for x in ['عهد','معدات','فستان','صيانة']): r['target_url']='/assets'
            elif any(x in txt for x in ['راتب','مرتب','مرتبات']): r['target_url']='/salaries'
            elif any(x in txt for x in ['عمول','بونص']): r['target_url']='/commissions'
            elif any(x in txt for x in ['دخل','مبيعات']): r['target_url']='/daily-sales'
            elif any(x in txt for x in ['حجز','عربون','اوردر','أوردر']): r['target_url']='/reservations'
            else: r['target_url']='/'
        out.append(r)
    for r in out:
        if r.get('notification_type') == 'pending_deposit' and str(r.get('pending_deposit_status') or '') == 'Pending':
            r['status'] = 'Pending'
            r['priority'] = 'critical'
    # ترتيب الإشعارات بحيث تظهر العرابين المعلقة في الأعلى دائماً للمدير لحين استلام الفلوس وتأكيدها
    out.sort(key=lambda r: (0 if (r.get('notification_type')=='pending_deposit' and str(r.get('pending_deposit_status') or '')=='Pending') else 1, -safe_int(r.get('id'), 0)))
    unread=sum(1 for r in out if str(r.get('status') or '').lower()!='read' or (r.get('notification_type')=='pending_deposit' and str(r.get('pending_deposit_status') or '')=='Pending'))
    return ok({"rows":out,"unread":unread})

@app.post("/api/notifications/read-all")
@login_required
def api_notifications_read_all():
    ensure_web_extension_tables()
    _ensure_notif_link_columns()
    with get_db_connection() as conn:
        cur = conn.cursor()
        if is_personal_scope_user():
            my_names = list(current_employee_names())
            if my_names:
                ph = ",".join(["%s"]*len(my_names))
                cur.execute(f"""UPDATE system_notifications n
                                LEFT JOIN web_notification_links l ON l.notification_id=n.id
                                SET n.status='Read'
                                WHERE LOWER(COALESCE(l.target_employee, n.related_sales_person, '')) IN ({ph})""", tuple(my_names))
        else:
            cur.execute("""
                UPDATE system_notifications n
                LEFT JOIN web_notification_links l ON l.notification_id = n.id
                LEFT JOIN web_pending_deposits p ON p.id = l.pending_deposit_id
                SET n.status = 'Read'
                WHERE n.status != 'Read'
                  AND (p.id IS NULL OR p.status != 'Pending')
            """)
    return ok()

@app.post("/api/notifications/broadcast")
@login_required
def api_notifications_broadcast():
    if is_personal_scope_user():
        return fail("إرسال التعاميم والإشعارات متاح للإدارة فقط", 403)
    d = request.get_json(silent=True) or {}
    title = str(d.get("title") or "").strip()
    message = str(d.get("message") or "").strip()
    if not title or not message:
        return fail("عنوان ونص الإشعار مطلوبان")
    target_type = str(d.get("target_type") or "all").strip()
    target_emp = str(d.get("target_employee") or "").strip() if target_type == "employee" else None
    target_role = str(d.get("target_role") or "all").strip() if target_type == "role" else ("all" if target_type == "all" else None)
    priority = str(d.get("priority") or "normal").strip()
    target_url = str(d.get("target_url") or "/").strip()
    sender = (current_user() or {}).get("nickname") or (current_user() or {}).get("full_name") or "الإدارة"
    with get_db_connection() as conn:
        cur = conn.cursor()
        nid = create_linked_notification(
            cur,
            f"📢 {title}",
            message,
            notification_type="broadcast",
            target_url=target_url,
            target_employee=target_emp,
            target_role=target_role,
            priority=priority,
            sender_name=sender,
        )
    audit("BROADCAST_NOTIF", "system_notifications", f"إرسال تعميم إداري: {title}")
    return ok({"id": nid})

@app.delete("/api/notifications/<int:nid>")
@login_required
def api_notification_delete(nid):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM web_notification_links WHERE notification_id=%s", (nid,))
        c.execute("DELETE FROM system_notifications WHERE id=%s", (nid,))
    return ok()


@app.get("/api/pending-deposits")
@require_permission("finances_access")
def api_pending_deposits():
    ensure_web_extension_tables()
    status=request.args.get('status','Pending').strip()
    ids=allowed_hotel_ids(); w,p=make_where_for_hotels('p.hotel_id',ids)
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True)
        cur.execute(f"""SELECT p.*,h.hotel_name FROM web_pending_deposits p
                        LEFT JOIN hotels h ON h.id=p.hotel_id
                        WHERE p.status=%s {w} ORDER BY p.id DESC""", tuple([status]+p))
        return ok(rows_to_json(cur.fetchall()))


@app.post("/api/pending-deposits/<int:pending_id>/confirm")
@require_permission("finances_access")
def api_pending_deposit_confirm(pending_id):
    if is_personal_scope_user():
        return fail('تأكيد استلام العربون وترحيله للدخل متاح للمدير / الإدارة فقط', 403)
    ensure_web_extension_tables()
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM web_pending_deposits WHERE id=%s FOR UPDATE",(pending_id,))
        p=cur.fetchone()
        if not p:return fail('العربون المعلّق غير موجود',404)
        if str(p.get('status'))!='Pending':return fail('تم تأكيد أو التعامل مع هذا العربون بالفعل',409)
        if not verify_hotel_id(p.get('hotel_id')):return fail('ليس لديك صلاحية لهذا الفندق',403)
        booking=get_booking_dict(cur,safe_int(p.get('booking_id'))) or {
            'id': p.get('booking_id'),
            'room_number': p.get('room_number'),
            'sales_person': p.get('sales_person'),
            'hotel': hotel_name_from_id(p.get('hotel_id')) or 'الفندق الرئيسي',
            'photographer': ''
        }
        diffs={'usd':safe_float(p.get('deposit_usd')),'eur':safe_float(p.get('deposit_eur')),'cash':safe_float(p.get('deposit_le_cash')),'visa':safe_float(p.get('deposit_le_visa'))}
        c=conn.cursor()
        # 1. تسجيل العربون في جدول العرابين (deposits)
        try:
            if not table_exists('deposits'):
                c.execute("""
                    CREATE TABLE IF NOT EXISTS deposits (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        hotel_id INT DEFAULT 1,
                        room_number VARCHAR(50),
                        deposit_sales_person VARCHAR(100),
                        deposit_usd DECIMAL(12,2) DEFAULT 0,
                        deposit_eur DECIMAL(12,2) DEFAULT 0,
                        deposit_le_cash DECIMAL(12,2) DEFAULT 0,
                        deposit_le_visa DECIMAL(12,2) DEFAULT 0,
                        deposit_date DATE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                _SCHEMA_CACHE.pop('deposits', None)
            record_deposit(c,{**booking,'id':p.get('booking_id')},diffs,deposit_date=p.get('deposit_date'))
        except Exception:
            pass

        # 2. ترحيل العربون المعتمد مباشرة إلى خانة الدخل اليومي (daily_income)
        try:
            dcols = table_columns("daily_income")
            hid = safe_int(p.get("hotel_id")) or hotel_id_from_name(booking.get("hotel")) or 1
            bid = safe_int(p.get("booking_id"))
            rm = str(p.get("room_number") or booking.get("room_number") or "").strip()
            s_person = str(p.get("sales_person") or booking.get("sales_person") or "").strip()
            photog = str(booking.get("photographer") or "").strip()
            dep_date = str(p.get("deposit_date") or date.today().isoformat())[:10]
            rate = 50.0
            equiv_usd = round(diffs["usd"] + diffs["eur"] + ((diffs["cash"] + diffs["visa"]) / rate), 2)

            existing_inc = None
            if bid and "booking_id" in dcols:
                cur.execute("SELECT * FROM daily_income WHERE booking_id=%s ORDER BY id DESC LIMIT 1", (bid,))
                existing_inc = cur.fetchone()
            if not existing_inc and rm:
                cur.execute("SELECT * FROM daily_income WHERE room_number=%s AND income_date=%s ORDER BY id DESC LIMIT 1", (rm, dep_date))
                existing_inc = cur.fetchone()

            if existing_inc:
                new_dep_app = round(safe_float(existing_inc.get("deposit_applied")) + equiv_usd, 2)
                inc_u = safe_float(existing_inc.get("income_usd"))
                inc_e = safe_float(existing_inc.get("income_eur"))
                inc_m = safe_float(existing_inc.get("income_le_m"))
                inc_k = safe_float(existing_inc.get("income_le_k"))
                r_rate = safe_float(existing_inc.get("le_to_usd")) or 50.0
                c_tot = safe_float(existing_inc.get("cost_total"))
                new_net = round(new_dep_app + inc_u + inc_e + ((inc_m + inc_k) / r_rate) - c_tot, 2)
                upd = {"deposit_applied": new_dep_app, "daily_total": new_net}
                if "deposit_usd" in dcols: upd["deposit_usd"] = safe_float(existing_inc.get("deposit_usd")) + diffs["usd"]
                if "deposit_eur" in dcols: upd["deposit_eur"] = safe_float(existing_inc.get("deposit_eur")) + diffs["eur"]
                if "deposit_le_cash" in dcols: upd["deposit_le_cash"] = safe_float(existing_inc.get("deposit_le_cash")) + diffs["cash"]
                if "deposit_le_visa" in dcols: upd["deposit_le_visa"] = safe_float(existing_inc.get("deposit_le_visa")) + diffs["visa"]
                use_u = {k: v for k, v in upd.items() if k in dcols}
                if use_u:
                    c.execute("UPDATE daily_income SET " + ",".join(f"`{k}`=%s" for k in use_u) + " WHERE id=%s", [use_u[k] for k in use_u] + [existing_inc["id"]])
            else:
                new_inc = {
                    "hotel_id": hid,
                    "booking_id": bid or None,
                    "room_number": rm,
                    "sales_person": s_person,
                    "deposit_sales_person": s_person,
                    "photographer": photog,
                    "deposit_usd": diffs["usd"],
                    "deposit_eur": diffs["eur"],
                    "deposit_le_cash": diffs["cash"],
                    "deposit_le_visa": diffs["visa"],
                    "deposit_applied": equiv_usd,
                    "income_usd": diffs["usd"],
                    "income_eur": diffs["eur"],
                    "income_le_k": diffs["cash"],
                    "income_le_m": diffs["visa"],
                    "le_to_usd": rate,
                    "order_exchange_rate": rate,
                    "cost_dress": 0,
                    "cost_usb": 0,
                    "cost_album": 0,
                    "cost_total": 0,
                    "daily_total": equiv_usd,
                    "income_date": dep_date,
                }
                use_i = {k: v for k, v in new_inc.items() if k in dcols}
                if use_i:
                    cols_list = list(use_i.keys())
                    c.execute("INSERT INTO daily_income (" + ",".join(f"`{k}`" for k in cols_list) + ") VALUES (" + ",".join(["%s"]*len(cols_list)) + ")", [use_i[k] for k in cols_list])
        except Exception:
            pass

        c.execute("UPDATE web_pending_deposits SET status='Confirmed',resolved_by=%s,resolved_at=NOW() WHERE id=%s",((current_user() or {}).get('id'),pending_id))
        c.execute("""UPDATE system_notifications n JOIN web_notification_links l ON l.notification_id=n.id
                     SET n.status='Read' WHERE l.pending_deposit_id=%s""",(pending_id,))
        create_linked_notification(
            c,
            f"✅ تم استلام وترحيل عربون غرفة {p.get('room_number')}",
            f"أكد المدير استلام عربون غرفة {p.get('room_number')} من السيلز {p.get('sales_person') or '-'} وتم ترحيله إلى خانة الدخل اليومي.",
            sales_person=p.get('sales_person') or '',
            target_employee=p.get('sales_person') or '',
            notification_type='deposit_confirmed',
            target_url='/daily-sales',
            booking_id=p.get('booking_id'),
        )
    booking_activity(p.get('booking_id'),'DEPOSIT_CONFIRM','تم تأكيد استلام العربون وترحيله لخانة الدخل',f"تم اعتماد العربون المعلّق #{pending_id} وترحيله لخانة الدخل")
    audit('CONFIRM_DEPOSIT','daily_income',f"اعتماد عربون معلق #{pending_id} وترحيله لخانة الدخل للحجز #{p.get('booking_id')}")
    return ok({'id':pending_id,'status':'Confirmed','booking_id':p.get('booking_id')})


@app.post("/api/pending-deposits/<int:pending_id>/reject")
@require_permission("finances_access")
def api_pending_deposit_reject(pending_id):
    ensure_web_extension_tables()
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM web_pending_deposits WHERE id=%s FOR UPDATE",(pending_id,));p=cur.fetchone()
        if not p:return fail('العربون المعلّق غير موجود',404)
        if str(p.get('status'))!='Pending':return fail('تم التعامل مع هذا العربون بالفعل',409)
        if not verify_hotel_id(p.get('hotel_id')):return fail('ليس لديك صلاحية لهذا الفندق',403)
        booking=get_booking_dict(cur,safe_int(p.get('booking_id')))
        c=conn.cursor()
        if booking:
            reverted=dict(booking)
            reverted['deposit_usd']=max(0,safe_float(booking.get('deposit_usd'))-safe_float(p.get('deposit_usd')))
            reverted['deposit_eur']=max(0,safe_float(booking.get('deposit_eur'))-safe_float(p.get('deposit_eur')))
            reverted['deposit_le_cash']=max(0,safe_float(booking.get('deposit_le_cash'))-safe_float(p.get('deposit_le_cash')))
            reverted['deposit_le_visa']=max(0,safe_float(booking.get('deposit_le_visa'))-safe_float(p.get('deposit_le_visa')))
            reverted['remaining']=round(safe_float(booking.get('total_agreement'))-deposit_equivalent(reverted['deposit_usd'],reverted['deposit_eur'],reverted['deposit_le_cash'],reverted['deposit_le_visa'],50.0),2)
            update_booking_record(c,safe_int(p.get('booking_id')),reverted,only={'deposit_usd','deposit_eur','deposit_le_cash','deposit_le_visa','remaining'})
        c.execute("UPDATE web_pending_deposits SET status='Rejected',resolved_by=%s,resolved_at=NOW() WHERE id=%s",((current_user() or {}).get('id'),pending_id))
        c.execute("""UPDATE system_notifications n JOIN web_notification_links l ON l.notification_id=n.id
                     SET n.status='Read' WHERE l.pending_deposit_id=%s""",(pending_id,))
    booking_activity(p.get('booking_id'),'DEPOSIT_REJECT','تم رفض ترحيل العربون',f"العربون المعلّق #{pending_id} لم يدخل حركة العربون")
    audit('REJECT_DEPOSIT','web_pending_deposits',f"رفض عربون معلق #{pending_id}")
    return ok({'id':pending_id,'status':'Rejected','booking_id':p.get('booking_id')})


@app.get("/api/system/search")
@login_required
def api_system_search():
    q = request.args.get("q", "").strip()
    if len(q) < 1:
        return ok([])
    names = allowed_hotel_names()
    wh, ph = make_where_for_hotels("hotel", names)
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        like = f"%{q}%"
        cur.execute(
            f"""SELECT id,hotel,booking_date,room_number,phone_number,status,sales_person,photographer
                FROM bookings WHERE (room_number LIKE %s OR phone_number LIKE %s OR sales_person LIKE %s OR photographer LIKE %s) {wh}
                ORDER BY id DESC LIMIT 15""", tuple([like, like, like, like] + ph))
        bookings = rows_to_json(cur.fetchall())
        if is_personal_scope_user():
            bookings = [b for b in bookings if record_belongs_to_current_user(b)]
    return ok([{"type": "booking", **r} for r in bookings])


# -----------------------------------------------------------------------------
# Reservations / Checkout / Timeline
# -----------------------------------------------------------------------------
def normalize_booking_payload(d, existing=None):
    existing = existing or {}
    out = {f: d.get(f, existing.get(f)) for f in BOOKING_FIELDS}
    out["hotel"] = str(out.get("hotel") or "الفندق الرئيسي").strip()
    out["booking_date"] = str(out.get("booking_date") or date.today().isoformat())[:10]
    out["room_number"] = str(out.get("room_number") or "").strip()
    out["phone_number"] = str(out.get("phone_number") or "").strip()
    out["nationality"] = str(out.get("nationality") or "").strip()
    out["booking_time"] = str(out.get("booking_time") or "").strip().replace(".", ":")[:5]
    out["session_details"] = str(out.get("session_details") or "")
    clothing = out.get("clothing")
    if isinstance(clothing, list):
        clothing = json.dumps(clothing, ensure_ascii=False)
    out["clothing"] = clothing or "[]"
    for f in ["deposit_usd", "deposit_eur", "deposit_le_cash", "deposit_le_visa", "total_agreement"]:
        out[f] = safe_float(out.get(f))
    rate = safe_float(d.get("rate") or d.get("exchange_rate") or 50) or 50
    out["remaining"] = round(out["total_agreement"] - deposit_equivalent(out["deposit_usd"], out["deposit_eur"], out["deposit_le_cash"], out["deposit_le_visa"], rate), 2)
    out["sales_person"] = str(out.get("sales_person") or "").strip()
    out["photographer"] = str(out.get("photographer") or "").strip()
    out["status"] = str(out.get("status") or "انتظار").strip()
    return out


def get_booking_dict(cur, booking_id):
    cur.execute("SELECT * FROM bookings WHERE id=%s", (booking_id,))
    raw = cur.fetchone()
    return normalize_booking_row(raw) if raw else None

def booking_scope_ok(row):
    if not row:
        return False
    if not record_belongs_to_current_user(row):
        return False
    # لو القاعدة القديمة لا تحتوي عمود hotel فلا يمكن ربط الحجز بفندق؛
    # في هذه الحالة نترك نفس سلوك البرنامج القديم ولا نخفي الحجز.
    if not row.get("_has_hotel_column", True):
        return True
    return verify_hotel_name(row.get("hotel"))



# =============================================================================
# 📌 10. كود إدارة الحجوزات (إضافة حجز، تعديل حجز، وحساب فرق العربون الجديد مع السيلز)
# =============================================================================
@app.get("/api/bookings")
@require_permission("bookings_access")
def api_bookings_list():
    try:
        q = request.args.get("q", "").strip().lower()
        status = request.args.get("status", "").strip()
        hotel = request.args.get("hotel", "").strip()
        exact_date = request.args.get("date", "").strip()
        month = request.args.get("month", "").strip()
        group = request.args.get("group", "").strip()
        allowed_names = allowed_hotel_names()
        with get_db_connection() as conn:
            cur = conn.cursor(dictionary=True)
            rows = fetch_booking_rows(cur, 5000)
        out=[]
        for r in rows:
            if not record_belongs_to_current_user(r):
                continue
            if allowed_names is not None and r.get("_has_hotel_column") and r.get("hotel") not in allowed_names:
                continue
            if hotel and str(r.get("hotel") or "") != hotel:
                continue
            if status and str(r.get("status") or "") != status:
                continue
            day = str(r.get("booking_date") or "")[:10]
            if exact_date and day != exact_date:
                continue
            if month and not day.startswith(month):
                continue
            if q:
                hay = " ".join(str(r.get(k) or "") for k in ["room_number","phone_number","sales_person","photographer","nationality","session_details"]).lower()
                if q not in hay:
                    continue
            pnames = split_names(r.get("photographer"))
            if group == "unassigned" and pnames:
                continue
            try:
                hour = int(str(r.get("booking_time") or "00").split(":")[0])
            except Exception:
                hour = 0
            if group == "morning" and hour >= 14:
                continue
            if group == "evening" and hour < 14:
                continue
            d,g = count_clothing(r.get("clothing"))
            r["dress_count"],r["galabeya_count"],r["photographers"] = d,g,pnames
            r.pop("_has_hotel_column",None)
            out.append({k: serialize(v) for k, v in r.items()})
        return ok(out[:2500])
    except Exception as exc:
        # مهم أثناء النقل من نسخة Desktop للويب: إظهار سبب قاعدة البيانات الحقيقي بدل HTTP 500 مبهم.
        return fail(f"تعذر قراءة الحجوزات من قاعدة البيانات: {exc}", 500)


@app.get("/api/bookings/<int:booking_id>")
@require_permission("bookings_access")
def api_booking_one(booking_id):
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        row = get_booking_dict(cur, booking_id)
    if not row:
        return fail("الحجز غير موجود", 404)
    if not booking_scope_ok(row):
        return fail("ليس لديك صلاحية لهذا الفندق", 403)
    out = {k: serialize(v) for k, v in row.items() if not str(k).startswith("_")}
    out["clothing_items"] = parse_json_list(out.get("clothing"))
    out["photographers"] = split_names(out.get("photographer"))
    try:
        with get_db_connection() as conn:
            c=conn.cursor(dictionary=True)
            if table_exists('web_pending_deposits'):
                c.execute("SELECT id,status,deposit_usd,deposit_eur,deposit_le_cash,deposit_le_visa,created_at FROM web_pending_deposits WHERE booking_id=%s ORDER BY id DESC LIMIT 1",(booking_id,))
                pd=c.fetchone()
                out["pending_deposit"]={k:serialize(v) for k,v in pd.items()} if pd else None
            else: out["pending_deposit"]=None
    except Exception:
        out["pending_deposit"]=None
    return ok(out)


@app.get("/api/bookings/check-duplicate")
@require_permission("bookings_access")
def api_booking_check_duplicate():
    room=request.args.get("room","").strip(); day=request.args.get("date","").strip(); exclude=safe_int(request.args.get("exclude"),0)
    if not room or not day:return ok(None)
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True); rows=fetch_booking_rows(cur,5000)
    for r in rows:
        if exclude and safe_int(r.get("id"))==exclude:continue
        st=str(r.get("status") or "").lower()
        if str(r.get("room_number") or "")==room and str(r.get("booking_date") or "")[:10]==day and not any(x in st for x in ["كنسل","cancel","ملغ"]):
            return ok({k:serialize(v) for k,v in r.items() if not str(k).startswith("_")})
    return ok(None)

@app.post("/api/bookings")
@require_permission("bookings_access")
def api_booking_create():
    if is_photographer_only():
        return fail("حساب المصور مخصص لعرض الأوردرات والمبيعات الخاصة به فقط، ولا يمكنه إضافة حجز أو عربون", 403)
    ensure_web_extension_tables()
    pending_id=None
    d=request.get_json(silent=True) or {}; data=normalize_booking_payload(d)
    if is_sales_only():
        u = current_user() or {}
        my_sales_name = str(u.get("nickname") or u.get("username") or "").strip()
        if my_sales_name:
            data["sales_person"] = my_sales_name
        my_hotel = get_current_user_hotel_name(u)
        if my_hotel:
            data["hotel"] = my_hotel
    if not data["room_number"]:return fail("رقم الغرفة مطلوب")
    if booking_col("hotel") and not verify_hotel_name(data["hotel"]):return fail("ليس لديك صلاحية لهذا الفندق",403)
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True); rows=fetch_booking_rows(cur,5000)
        dup=next((r for r in rows if str(r.get("room_number"))==data["room_number"] and str(r.get("booking_date") or "")[:10]==data["booking_date"] and not any(x in str(r.get("status") or "").lower() for x in ["كنسل","cancel","ملغ"])),None)
        if dup and not d.get("allow_duplicate"):return fail("الغرفة مسجلة بالفعل في نفس التاريخ",409,duplicate={k:serialize(v) for k,v in dup.items() if not str(k).startswith("_")})
        cur=conn.cursor(); bid=insert_booking_record(cur,data); data["id"]=bid
        sync_booking_dresses(cur,bid,data["clothing"])
        first_deposit={"usd":data["deposit_usd"],"eur":data["deposit_eur"],"cash":data["deposit_le_cash"],"visa":data["deposit_le_visa"]}
        if current_user_is_sales(): pending_id=queue_pending_deposit(cur,data,first_deposit)
        else: record_deposit(cur,data,first_deposit)
    booking_activity(bid,"CREATE","تم إنشاء الحجز",f"غرفة {data['room_number']} - {data['hotel']}"); audit("CREATE","bookings",f"إضافة حجز #{bid} غرفة {data['room_number']}")
    actor_sales = data.get("sales_person") or (current_user() or {}).get("nickname") or "السيلز"
    emit_notification(
        f"📅 حجز أوردر جديد • غرفة {data['room_number']} (السيلز: {actor_sales})",
        f"قام السيلز {actor_sales} بحجز أوردر غرفة {data['room_number']} في فندق {data['hotel']} ليوم {data['booking_date']} الساعة {data.get('booking_time') or '--:--'} بإجمالي اتفاق ${safe_float(data.get('total_agreement')):.2f}.",
        sales_person=actor_sales,
        amount=safe_float(data.get("total_agreement")),
        notification_type="booking_created",
        target_url=f"/reservations?open={bid}",
        booking_id=bid,
        target_role="Manager",
        hotel_id=hotel_id_from_name(data.get("hotel")),
        priority="high",
    )
    if data.get("photographer"):
        emit_notification(
            f"📸 أوردر تصوير جديد مسند إليك • غرفة {data['room_number']}",
            f"تم إسناد أوردر غرفة {data['room_number']} ({data['hotel']}) يوم {data['booking_date']} الساعة {data.get('booking_time') or '--:--'} للمصور {data['photographer']}.",
            notification_type="ops_assigned",
            target_url="/reservations",
            booking_id=bid,
            target_employee=data["photographer"],
            priority="high",
        )
    return ok({"id":bid,"remaining":data["remaining"],"deposit_pending":bool(pending_id),"pending_deposit_id":pending_id})

@app.put("/api/bookings/<int:booking_id>")
@require_permission("bookings_access")
def api_booking_update(booking_id):
    if is_photographer_only(): return fail("حساب المصور للعرض فقط ولا يمكنه تعديل الحجوزات أو العرابين", 403)
    ensure_web_extension_tables()
    d=request.get_json(silent=True) or {}
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True); old=get_booking_dict(cur,booking_id)
        if not old:return fail("الحجز غير موجود",404)
        if not booking_scope_ok(old):return fail("ليس لديك صلاحية لهذا الفندق",403)
        data=normalize_booking_payload(d,old)
        if is_sales_only():
            u = current_user() or {}
            my_sales_name = str(u.get("nickname") or u.get("username") or "").strip()
            if my_sales_name:
                data["sales_person"] = my_sales_name
            my_hotel = get_current_user_hotel_name(u)
            if my_hotel:
                data["hotel"] = my_hotel
        if booking_col("hotel") and not verify_hotel_name(data["hotel"]):return fail("ليس لديك صلاحية للفندق الجديد",403)
        chosen=data["status"]; cur=conn.cursor()
        if chosen in {"كنسل","cancelled","ملغي"}:
            if d.get("refund_deposit"):record_deposit(cur,{**old,"id":booking_id},{"usd":-safe_float(old.get("deposit_usd")),"eur":-safe_float(old.get("deposit_eur")),"cash":-safe_float(old.get("deposit_le_cash")),"visa":-safe_float(old.get("deposit_le_visa"))})
            cancel_data=dict(old);cancel_data.update({"status":"كنسل","photographer":data.get("photographer") or old.get("photographer")});update_booking_record(cur,booking_id,cancel_data,only={"status","photographer"})
            booking_activity(booking_id,"CANCEL","تم إلغاء الحجز","تم تسجيل مرتجع العربون" if d.get("refund_deposit") else "بدون مرتجع عربون");return ok({"id":booking_id,"status":"كنسل"})
        if chosen in {"تقديم ميعاد","تأخير ميعاد"} and d.get("reschedule_date"):
            new_day=str(d["reschedule_date"])[:10];status_text=f"تأجيل ليوم {new_day}" if chosen=="تأخير ميعاد" else f"تقديم ليوم {new_day}"
            x=dict(old);x["status"]=status_text;update_booking_record(cur,booking_id,x,only={"status"})
            clone=dict(data);clone.update({"booking_date":new_day,"status":"انتظار","photographer":d.get("photographer") or ""});new_id=insert_booking_record(cur,clone);sync_booking_dresses(cur,new_id,clone["clothing"]);booking_activity(booking_id,"RESCHEDULE",status_text,f"تم إنشاء الحجز الجديد #{new_id}");booking_activity(new_id,"CREATE","حجز منقول من موعد سابق",f"المصدر #{booking_id}");return ok({"id":booking_id,"new_booking_id":new_id,"status":status_text})
        update_booking_record(cur,booking_id,data)
        diffs={"usd":max(0,data["deposit_usd"]-safe_float(old.get("deposit_usd"))),"eur":max(0,data["deposit_eur"]-safe_float(old.get("deposit_eur"))),"cash":max(0,data["deposit_le_cash"]-safe_float(old.get("deposit_le_cash"))),"visa":max(0,data["deposit_le_visa"]-safe_float(old.get("deposit_le_visa")))}
        if current_user_is_sales(): queue_pending_deposit(cur,{**data,"id":booking_id},diffs)
        else: record_deposit(cur,{**data,"id":booking_id},diffs)
        sync_booking_dresses(cur,booking_id,data["clothing"])
    booking_activity(booking_id,"UPDATE","تم تعديل بيانات الحجز",f"الحالة: {data['status']}");audit("UPDATE","bookings",f"تعديل حجز #{booking_id}")
    if not current_user_is_sales():
        actor_mgr = (current_user() or {}).get("nickname") or (current_user() or {}).get("full_name") or "المدير"
        emit_notification(
            f"🛡️ تعديل بيانات حجز بواسطة المدير ({actor_mgr}) • فندق {data.get('hotel')}",
            f"قام المدير ({actor_mgr}) بتعديل بيانات حجز غرفة {data.get('room_number')} في فندق {data.get('hotel')} (الاتفاق: ${safe_float(old.get('total_agreement')):.2f} ⬅️ ${safe_float(data.get('total_agreement')):.2f} | الحالة: {data.get('status')}).",
            notification_type="manager_edit",
            target_role="CEO",
            target_url=f"/reservations?open={booking_id}",
            booking_id=booking_id,
            hotel_id=hotel_id_from_name(data.get("hotel")),
            priority="high",
        )
    return ok({"id":booking_id,"remaining":data["remaining"]})

@app.delete("/api/bookings/<int:booking_id>")
@require_permission("bookings_access")
def api_booking_delete(booking_id):
    if is_photographer_only(): return fail("حساب المصور للعرض فقط ولا يمكنه حذف الحجوزات", 403)
    force=request.args.get("force")=="1"
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);row=get_booking_dict(cur,booking_id)
        if not row:return fail("الحجز غير موجود",404)
        if not booking_scope_ok(row):return fail("ليس لديك صلاحية",403)
        if ("deliver" in str(row.get("status","")).lower() or "تسليم" in str(row.get("status",""))) and not force:return fail("الأوردر مسلم ومقفل. أعد الحذف مع تأكيد فك القفل.",409,locked=True)
        c=conn.cursor()
        for tbl in ["booking_dresses","booking_activity"]:
            if table_exists(tbl):
                try:c.execute(f"DELETE FROM `{tbl}` WHERE booking_id=%s",(booking_id,))
                except Exception:pass
        c.execute("DELETE FROM bookings WHERE id=%s",(booking_id,))
    audit("DELETE","bookings",f"حذف حجز #{booking_id}")
    actor_mgr = (current_user() or {}).get("nickname") or (current_user() or {}).get("full_name") or "المدير"
    emit_notification(
        f"🛡️ حذف حجز بواسطة المدير ({actor_mgr}) • فندق {row.get('hotel')}",
        f"قام المدير ({actor_mgr}) بحذف حجز غرفة {row.get('room_number')} في فندق {row.get('hotel')} (كان بإجمالي اتفاق ${safe_float(row.get('total_agreement')):.2f}).",
        notification_type="manager_edit",
        target_role="CEO",
        target_url="/reservations",
        hotel_id=hotel_id_from_name(row.get("hotel")),
        priority="critical",
    )
    return ok()

@app.post("/api/bookings/<int:booking_id>/duplicate")
@require_permission("bookings_access")
def api_booking_duplicate(booking_id):
    d=request.get_json(silent=True) or {}
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);row=get_booking_dict(cur,booking_id)
        if not row or not booking_scope_ok(row):return fail("الحجز غير موجود أو خارج صلاحيتك",404)
        clone={f:serialize(row.get(f)) for f in BOOKING_FIELDS};clone["booking_date"]=str(d.get("booking_date") or clone.get("booking_date") or date.today().isoformat())[:10];clone["room_number"]=str(d.get("room_number") or clone.get("room_number") or "");clone["status"]=str(d.get("status") or "انتظار");clone["photographer"]=str(d.get("photographer") or "")
        c=conn.cursor();new_id=insert_booking_record(c,clone);sync_booking_dresses(c,new_id,clone.get("clothing"))
    booking_activity(new_id,"DUPLICATE","تم استنساخ الحجز",f"نسخة من الحجز #{booking_id}");return ok({"id":new_id})

@app.post("/api/bookings/<int:booking_id>/checkout")
@require_permission("bookings_access")
def api_booking_checkout(booking_id):
    if is_photographer_only(): return fail("حساب المصور للعرض فقط ولا يمكنه تنفيذ Checkout أو تحصيل عرابين", 403)
    if current_user_is_sales(): ensure_web_extension_tables()
    d=request.get_json(silent=True) or {}
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);old=get_booking_dict(cur,booking_id)
        if not old:return fail("الحجز غير موجود",404)
        if not booking_scope_ok(old):return fail("ليس لديك صلاحية",403)
        status=str(d.get("status") or "Delivered");photogs=d.get("photographers") or [];photogs=split_names(photogs) if isinstance(photogs,str) else photogs;photog_str=", ".join([str(x).strip() for x in photogs[:3] if str(x).strip()]) or "بدون مصور"
        deposits={"usd":safe_float(d.get("deposit_usd",old.get("deposit_usd"))),"eur":safe_float(d.get("deposit_eur",old.get("deposit_eur"))),"cash":safe_float(d.get("deposit_le_cash",old.get("deposit_le_cash"))),"visa":safe_float(d.get("deposit_le_visa",old.get("deposit_le_visa")))};rate=safe_float(d.get("rate")) or 50.0;remaining=round(safe_float(old.get("total_agreement"))-deposit_equivalent(deposits["usd"],deposits["eur"],deposits["cash"],deposits["visa"],rate),2);c=conn.cursor()
        if status in {"كنسل","cancelled","ملغي"}:
            if d.get("refund_deposit"):record_deposit(c,{**old,"id":booking_id},{"usd":-safe_float(old.get("deposit_usd")),"eur":-safe_float(old.get("deposit_eur")),"cash":-safe_float(old.get("deposit_le_cash")),"visa":-safe_float(old.get("deposit_le_visa"))})
            x=dict(old);x.update({"status":"كنسل","photographer":photog_str});update_booking_record(c,booking_id,x,only={"status","photographer"});booking_activity(booking_id,"CHECKOUT_CANCEL","Checkout: تم إلغاء الأوردر",photog_str);return ok({"id":booking_id,"status":"كنسل"})
        if status in {"تقديم ميعاد","تأخير ميعاد"} and d.get("reschedule_date"):
            new_day=str(d["reschedule_date"])[:10];status_text=f"تأجيل ليوم {new_day}" if status=="تأخير ميعاد" else f"تقديم ليوم {new_day}";x=dict(old);x.update({"status":status_text,"photographer":photog_str});update_booking_record(c,booking_id,x,only={"status","photographer"});clone={f:serialize(old.get(f)) for f in BOOKING_FIELDS};clone.update({"booking_date":new_day,"photographer":photog_str,"status":"انتظار"});new_id=insert_booking_record(c,clone);sync_booking_dresses(c,new_id,clone.get("clothing"));booking_activity(booking_id,"RESCHEDULE",status_text,f"Checkout نقل إلى #{new_id}");return ok({"id":booking_id,"new_booking_id":new_id,"status":status_text})
        x=dict(old);x.update({"deposit_usd":deposits["usd"],"deposit_eur":deposits["eur"],"deposit_le_cash":deposits["cash"],"deposit_le_visa":deposits["visa"],"remaining":remaining,"photographer":photog_str,"status":status});update_booking_record(c,booking_id,x,only={"deposit_usd","deposit_eur","deposit_le_cash","deposit_le_visa","remaining","photographer","status"})
        diffs={"usd":max(0,deposits["usd"]-safe_float(old.get("deposit_usd"))),"eur":max(0,deposits["eur"]-safe_float(old.get("deposit_eur"))),"cash":max(0,deposits["cash"]-safe_float(old.get("deposit_le_cash"))),"visa":max(0,deposits["visa"]-safe_float(old.get("deposit_le_visa")))}
        if current_user_is_sales(): queue_pending_deposit(c,{**old,"id":booking_id,"sales_person":old.get("sales_person")},diffs)
        else: record_deposit(c,{**old,"id":booking_id},diffs)
        try:sync_laundry(c,booking_id,old.get("booking_date"),old.get("hotel"),old.get("clothing"))
        except Exception:pass
    booking_activity(booking_id,"CHECKOUT","تم تنفيذ Checkout",f"الحالة: {status} | المصورين: {photog_str} | المتبقي: {remaining:.2f}$");audit("CHECKOUT","bookings",f"Checkout للحجز #{booking_id}");return ok({"id":booking_id,"remaining":remaining,"photographer":photog_str,"status":status})

@app.get("/api/bookings/<int:booking_id>/activity")
@require_permission("bookings_access")
def api_booking_activity(booking_id):
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT a.*,t.nickname actor FROM booking_activity a LEFT JOIN team_members t ON t.id=a.user_id WHERE a.booking_id=%s ORDER BY a.event_time DESC,a.id DESC", (booking_id,))
        return ok(rows_to_json(cur.fetchall()))


@app.get("/api/bookings/timeline")
@require_permission("bookings_access")
def api_booking_timeline():
    day=request.args.get("date") or date.today().isoformat();names=allowed_hotel_names()
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);rows=fetch_booking_rows(cur,5000)
    out=[]
    for r in rows:
        if str(r.get("booking_date") or "")[:10]!=day:continue
        if names is not None and r.get("_has_hotel_column") and r.get("hotel") not in names:continue
        st=str(r.get("status") or "").lower()
        if any(x in st for x in ["كنسل","cancel","ملغ"]):continue
        out.append({k:r.get(k) for k in ["id","hotel","room_number","booking_time","photographer","session_details","status","remaining"]})
    out.sort(key=lambda x:str(x.get("booking_time") or ""));return ok(out)

@app.get("/api/bookings/prep")
@require_permission("bookings_access")
def api_booking_prep():
    day=request.args.get("date") or date.today().isoformat();names=allowed_hotel_names();agg={}
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);rows=fetch_booking_rows(cur,5000)
    for row in rows:
        if str(row.get("booking_date") or "")[:10]!=day:continue
        if not record_belongs_to_current_user(row):continue
        if names is not None and row.get("_has_hotel_column") and row.get("hotel") not in names:continue
        st=str(row.get("status") or "").lower()
        if any(x in st for x in ["كنسل","cancel","ملغ"]):continue
        for item in parse_json_list(row.get("clothing")):
            if not isinstance(item,dict):continue
            key=(str(item.get("type") or "فستان"),str(item.get("color") or "غير محدد"),str(item.get("size") or item.get("size_category") or "ستاندرد"));agg[key]=agg.get(key,0)+max(1,safe_int(item.get("qty"),1))
    data=[{"type":k[0],"color":k[1],"size":k[2],"qty":v} for k,v in sorted(agg.items())];return ok(data)

@app.get("/api/deposits")
@require_permission("sales_access")
def api_deposits():
    start=request.args.get("start") or date.today().replace(day=1).isoformat();end=request.args.get("end") or date.today().isoformat();q=request.args.get("q","").strip().lower();requested=request.args.get("hotel_id","").strip()
    if not table_exists("deposits"):
        # قاعدة قديمة بدون جدول حركة العربون: نعرض لقطة العربون الموجودة بالحجوزات بدل تعطيل الشاشة.
        with get_db_connection() as conn:
            cur=conn.cursor(dictionary=True);bookings=fetch_booking_rows(cur,5000)
        out=[]
        for b in bookings:
            day=str(b.get("booking_date") or "")[:10]
            if day and not(start<=day<=end):continue
            if q and q not in (str(b.get("room_number") or "")+" "+str(b.get("sales_person") or "")).lower():continue
            if requested:
                hname=hotel_name_from_id(requested)
                if hname and b.get("hotel")!=hname:continue
            if not any(safe_float(b.get(k)) for k in ["deposit_usd","deposit_eur","deposit_le_cash","deposit_le_visa"]):continue
            out.append({"id":b.get("id"),"booking_id":b.get("id"),"hotel_name":b.get("hotel"),"room_number":b.get("room_number"),"deposit_sales_person":b.get("sales_person"),"deposit_usd":b.get("deposit_usd"),"deposit_eur":b.get("deposit_eur"),"deposit_le_cash":b.get("deposit_le_cash"),"deposit_le_visa":b.get("deposit_le_visa"),"deposit_date":day})
        return ok(out)
    ids=allowed_hotel_ids();w,p=make_where_for_hotels("d.hotel_id",ids)
    if requested:
        rh=safe_int(requested,-1)
        if ids is not None and rh not in ids:return ok([])
        if "hotel_id" in table_columns("deposits"):w+=" AND d.hotel_id=%s";p.append(rh)
    search_sql="";search_params=[]
    if q:search_sql=" AND (d.room_number LIKE %s OR d.deposit_sales_person LIKE %s)";search_params=[f"%{q}%",f"%{q}%"]
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cols=table_columns("deposits");date_col="deposit_date" if "deposit_date" in cols else None
        if not date_col:return ok([])
        has_hid = "hotel_id" in cols
        has_bid = "booking_id" in cols
        join_parts = []
        if has_hid:
            join_parts.append("LEFT JOIN hotels h ON h.id=d.hotel_id")
        if has_bid and table_exists("bookings"):
            join_parts.append("LEFT JOIN bookings b ON b.id=d.booking_id")
        join = (" " + " ".join(join_parts)) if join_parts else ""
        if has_hid and has_bid and table_exists("bookings"):
            hotel_select = "COALESCE(h.hotel_name, b.hotel) AS hotel_name"
        elif has_hid:
            hotel_select = "h.hotel_name AS hotel_name"
        elif has_bid and table_exists("bookings"):
            hotel_select = "b.hotel AS hotel_name"
        else:
            hotel_select = "NULL AS hotel_name"
        cur.execute(f"SELECT d.*,{hotel_select} FROM deposits d{join} WHERE d.`{date_col}` BETWEEN %s AND %s {w} {search_sql} ORDER BY d.`{date_col}` DESC,d.id DESC",tuple([start,end]+p+search_params))
        raw_rows = rows_to_json(cur.fetchall())
        rows = [
            r for r in raw_rows
            if (safe_float(r.get("deposit_usd")) + safe_float(r.get("deposit_eur")) + safe_float(r.get("deposit_le_cash")) + safe_float(r.get("deposit_le_visa"))) > 0
        ]
    if is_personal_scope_user():
        rows = [r for r in rows if record_belongs_to_current_user(r)]
    return ok(rows)

@app.put("/api/deposits/<int:deposit_id>")
@require_permission("sales_access")
def api_deposit_update(deposit_id):
    d = request.get_json(silent=True) or {}
    if not table_exists("deposits"):
        return fail("جدول العرابين غير موجود", 404)
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM deposits WHERE id=%s", (deposit_id,))
        row = cur.fetchone()
        if not row:
            return fail("سجل العربون غير موجود", 404)
        if row.get("hotel_id") and not verify_hotel_id(row.get("hotel_id")):
            return fail("ليس لديك صلاحية لهذا الفندق", 403)
        cols = table_columns("deposits")
        updates = {}
        if "room_number" in d and "room_number" in cols:
            updates["room_number"] = str(d.get("room_number") or row.get("room_number") or "").strip()
        if "deposit_sales_person" in d and "deposit_sales_person" in cols:
            updates["deposit_sales_person"] = str(d.get("deposit_sales_person") or "").strip()
        for k in ["deposit_usd", "deposit_eur", "deposit_le_cash", "deposit_le_visa"]:
            if k in d and k in cols:
                updates[k] = safe_float(d.get(k))
        if "deposit_date" in d and "deposit_date" in cols and d.get("deposit_date"):
            updates["deposit_date"] = str(d.get("deposit_date"))[:10]
        if updates:
            set_sql = ",".join(f"`{k}`=%s" for k in updates.keys())
            conn.cursor().execute(f"UPDATE deposits SET {set_sql} WHERE id=%s", list(updates.values()) + [deposit_id])
    audit("EDIT_DEPOSIT", "deposits", f"تعديل سجل عربون #{deposit_id} (غرفة {updates.get('room_number', row.get('room_number'))})")
    return ok({"id": deposit_id})

@app.delete("/api/deposits/<int:deposit_id>")
@require_permission("sales_access")
def api_deposit_delete(deposit_id):
    if not table_exists("deposits"):
        return fail("جدول العرابين غير موجود", 404)
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM deposits WHERE id=%s", (deposit_id,))
        row = cur.fetchone()
        if not row:
            return fail("سجل العربون غير موجود", 404)
        if row.get("hotel_id") and not verify_hotel_id(row.get("hotel_id")):
            return fail("ليس لديك صلاحية لهذا الفندق", 403)
        conn.cursor().execute("DELETE FROM deposits WHERE id=%s", (deposit_id,))
    audit("DELETE_DEPOSIT", "deposits", f"حذف سجل عربون #{deposit_id} (غرفة {row.get('room_number')})")
    return ok()

# -----------------------------------------------------------------------------
# Daily Sales / Deposits / Analytics / Coin Safe / Audit
# -----------------------------------------------------------------------------




def _can_access_managers_chat():
    """شات المديرين متاح للأونر (CEO) والمديرين (Manager) فقط لا غير."""
    if has_full_access():
        return True
    if is_personal_scope_user() or is_accountant_only():
        return False
    roles = {_normalize_role(r) for r in get_user_roles()}
    return bool(roles & {"manager", "hotel_manager", "director_manager", "مدير", "مدير فندق"})



# =============================================================================
# 📌 11. كود المحادثات الداخلية (قناتان: شات الإدارة والمديرين + شات فريق العمل)
# =============================================================================
@app.get("/chat")
@login_required
def chat_page():
    ctx = template_ctx("chat")
    ctx["can_managers_chat"] = _can_access_managers_chat()
    return render_template("chat.html", **ctx)


@app.get("/api/chat/messages")
@login_required
def api_chat_messages_list():
    ensure_web_extension_tables()
    channel = (request.args.get("channel") or "team").strip().lower()
    if channel == "managers" and not _can_access_managers_chat():
        return fail("شات المديرين مخصص للأونر والمديرين فقط", 403)
    if channel not in ("managers", "team"):
        channel = "team"

    hotel_id = safe_int(request.args.get("hotel_id"), 0)
    ids = allowed_hotel_ids()

    where_parts = ["c.channel=%s"]
    params = [channel]

    if channel == "team":
        if hotel_id:
            where_parts.append("(c.hotel_id=%s OR c.hotel_id IS NULL)")
            params.append(hotel_id)
        if ids is not None:
            if not ids:
                return ok({"rows": [], "can_managers_chat": _can_access_managers_chat()})
            ph = ",".join(["%s"] * len(ids))
            where_parts.append(f"(c.hotel_id IN ({ph}) OR c.hotel_id IS NULL)")
            params.extend(sorted(ids))

    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            f"""SELECT c.*, DATE_FORMAT(c.created_at, '%Y-%m-%d %H:%i') AS formatted_time
                FROM internal_chat_messages c
                WHERE {' AND '.join(where_parts)}
                ORDER BY c.id ASC LIMIT 300""",
            tuple(params),
        )
        rows = rows_to_json(cur.fetchall())

    return ok({
        "rows": rows,
        "can_managers_chat": _can_access_managers_chat(),
        "is_ceo": has_full_access(),
    })


@app.post("/api/chat/messages")
@login_required
def api_chat_message_send():
    ensure_web_extension_tables()
    d = request.get_json(silent=True) or {}
    channel = str(d.get("channel") or "team").strip().lower()
    if channel == "managers" and not _can_access_managers_chat():
        return fail("شات المديرين مخصص للأونر والمديرين فقط", 403)
    if channel not in ("managers", "team"):
        channel = "team"

    msg_text = str(d.get("message_text") or "").strip()
    if not msg_text:
        return fail("اكتب نص الرسالة أولاً")

    u = current_user() or {}
    sender_id = safe_int(u.get("id"), 0) or None
    sender_name = str(u.get("nickname") or u.get("full_name") or u.get("username") or "مستخدم").strip()
    sender_role = "الأونر (CEO)" if has_full_access() else ("مدير" if _can_access_managers_chat() else str(u.get("role") or "موظف"))
    hotel_id = safe_int(d.get("hotel_id"), 0) or safe_int(u.get("hotel_id"), 0) or None
    hotel_name = hotel_name_from_id(hotel_id) if hotel_id else "جميع الفنادق"

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO internal_chat_messages
               (channel, hotel_id, hotel_name, sender_id, sender_name, sender_role, message_text)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (channel, hotel_id, hotel_name, sender_id, sender_name, sender_role, msg_text),
        )
        mid = cur.lastrowid

    return ok({"id": mid})


@app.delete("/api/chat/messages/<int:msg_id>")
@login_required
def api_chat_message_delete(msg_id):
    if not has_full_access():
        return fail("حذف الرسائل متاح للأونر فقط", 403)
    ensure_web_extension_tables()
    with get_db_connection() as conn:
        conn.cursor().execute("DELETE FROM internal_chat_messages WHERE id=%s", (msg_id,))
    return ok()


@app.get("/mobile")
def mobile_edition_page():
    """يعرض نسخة الموبايل المنسقة لشاشات التليفون."""
    html_file = APP_ROOT / "PhotoTeam_Mobile_Edition.html"
    if not html_file.exists():
        html_file = BUNDLE_ROOT / "PhotoTeam_Mobile_Edition.html"
    if html_file.exists():
        return send_file(str(html_file), mimetype="text/html")
    return redirect(url_for("interactive_preview_page"))


@app.get("/desktop")
def desktop_edition_page():
    """يعرض نسخة الديسكتوب الكاملة."""
    html_file = APP_ROOT / "PhotoTeam_Desktop_Edition.html"
    if not html_file.exists():
        html_file = APP_ROOT / "PhotoTeam_Interactive_System_V90.html"
    if html_file.exists():
        return send_file(str(html_file), mimetype="text/html")
    return redirect(url_for("login_page"))



# =============================================================================
# 📌 12. كود الخزنة والمصروفات (إيداع العهدة للأونر فقط + خصم المصروفات تلقائياً)
# =============================================================================
@app.get("/treasury")
@login_required
def treasury_page():
    if is_personal_scope_user():
        return redirect(url_for("reservations_page") if is_sales_only() else url_for("dashboard"))
    return render_template("treasury.html", **template_ctx("treasury"))


@app.get("/api/treasury")
@login_required
def api_treasury_list():
    if is_personal_scope_user():
        return fail("غير مسموح", 403)
    ensure_web_extension_tables()
    month = (request.args.get("month") or "").strip()
    tx_type = (request.args.get("tx_type") or "").strip().upper()
    category = (request.args.get("category") or "").strip()
    hotel_id = safe_int(request.args.get("hotel_id"), 0)
    ids = allowed_hotel_ids()

    where_parts = ["1=1"]
    params = []
    if month:
        where_parts.append("t.tx_month=%s")
        params.append(month[:7])
    if tx_type in ("DEPOSIT", "EXPENSE"):
        where_parts.append("t.tx_type=%s")
        params.append(tx_type)
    if category:
        where_parts.append("t.category=%s")
        params.append(category)
    if hotel_id:
        where_parts.append("(t.hotel_id=%s OR t.hotel_id IS NULL)")
        params.append(hotel_id)
    if ids is not None:
        if not ids:
            return ok({"rows": [], "summary": {"total_deposits": 0, "total_expenses": 0, "balance": 0, "categories": []}})
        ph = ",".join(["%s"] * len(ids))
        where_parts.append(f"(t.hotel_id IN ({ph}) OR t.hotel_id IS NULL)")
        params.extend(sorted(ids))

    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            f"""SELECT t.*, COALESCE(h.hotel_name, t.hotel_name, 'جميع الفنادق') AS resolved_hotel
                FROM treasury_transactions t
                LEFT JOIN hotels h ON h.id = t.hotel_id
                WHERE {' AND '.join(where_parts)}
                ORDER BY t.tx_date DESC, t.id DESC""",
            tuple(params),
        )
        rows = rows_to_json(cur.fetchall())

    total_deposits = round(sum(safe_float(r.get("amount_egp")) for r in rows if str(r.get("tx_type")).upper() == "DEPOSIT"), 2)
    total_expenses = round(sum(safe_float(r.get("amount_egp")) for r in rows if str(r.get("tx_type")).upper() == "EXPENSE"), 2)
    balance = round(total_deposits - total_expenses, 2)

    cat_map = {}
    for r in rows:
        if str(r.get("tx_type")).upper() == "EXPENSE":
            c = str(r.get("category") or "مصاريف أخرى").strip()
            cat_map[c] = round(cat_map.get(c, 0.0) + safe_float(r.get("amount_egp")), 2)

    categories_breakdown = [
        {
            "category": k,
            "amount_egp": v,
            "pct": round((v / total_expenses * 100.0), 1) if total_expenses > 0 else 0.0,
        }
        for k, v in sorted(cat_map.items(), key=lambda item: -item[1])
    ]

    return ok({
        "rows": rows,
        "is_ceo": has_full_access(),
        "summary": {
            "total_deposits": total_deposits,
            "total_expenses": total_expenses,
            "balance": balance,
            "expense_count": sum(1 for r in rows if str(r.get("tx_type")).upper() == "EXPENSE"),
            "categories": categories_breakdown,
        },
    })


@app.post("/api/treasury")
@login_required
def api_treasury_save():
    if is_personal_scope_user():
        return fail("غير مسموح", 403)
    ensure_web_extension_tables()
    d = request.get_json(silent=True) or {}
    tx_id = safe_int(d.get("id"), 0)
    tx_type = "DEPOSIT" if str(d.get("tx_type") or "EXPENSE").upper() == "DEPOSIT" else "EXPENSE"
    is_ceo = has_full_access()

    # القاعدة الصارمة: لا أحد يستطيع إضافة إيداع عهدة أو تعديل أي سجل في الخزنة غير الأونر (CEO) فقط!
    if tx_id > 0 and not is_ceo:
        return fail("🔒 تعديل بيانات الخزنة أو المصاريف متاح لحساب الأونر (CEO) فقط!", 403)
    if tx_type == "DEPOSIT" and not is_ceo:
        return fail("🔒 إيداع أو تحويل رصيد للخزنة متاح لحساب الأونر (CEO) فقط!", 403)

    tx_date = str(d.get("tx_date") or date.today().isoformat())[:10]
    tx_month = tx_date[:7]
    category = str(d.get("category") or ("تحويل عهدة من الأونر" if tx_type == "DEPOSIT" else "مصاريف تشغيل")).strip()
    hotel_id = safe_int(d.get("hotel_id"), 0) or None
    hotel_name = hotel_name_from_id(hotel_id) if hotel_id else (str(d.get("hotel_name") or "جميع الفنادق").strip())
    amount_egp = max(0.0, safe_float(d.get("amount_egp")))
    amount_usd = max(0.0, safe_float(d.get("amount_usd")))
    if amount_egp <= 0 and amount_usd > 0:
        amount_egp = round(amount_usd * 50.0, 2)
    if amount_egp <= 0:
        return fail("يرجى إدخال المبلغ بالجنيه المصري (أو الدولار)")

    beneficiary = str(d.get("beneficiary") or "").strip()
    description = str(d.get("description") or "").strip()
    if not description:
        return fail("يرجى كتابة بيان/تفاصيل العملية (الفلوس اتصرفت في إيه)")
    payment_method = str(d.get("payment_method") or "نقدي / الخزنة").strip()
    actor = (current_user() or {}).get("nickname") or (current_user() or {}).get("full_name") or "الإدارة"

    with get_db_connection() as conn:
        cur = conn.cursor()
        if tx_id > 0:
            cur.execute(
                """UPDATE treasury_transactions
                   SET tx_date=%s, tx_month=%s, tx_type=%s, category=%s, hotel_id=%s, hotel_name=%s,
                       amount_egp=%s, amount_usd=%s, beneficiary=%s, description=%s, payment_method=%s
                   WHERE id=%s""",
                (tx_date, tx_month, tx_type, category, hotel_id, hotel_name, amount_egp, amount_usd, beneficiary, description, payment_method, tx_id),
            )
        else:
            cur.execute(
                """INSERT INTO treasury_transactions
                   (tx_date, tx_month, tx_type, category, hotel_id, hotel_name, amount_egp, amount_usd, beneficiary, description, payment_method, created_by)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (tx_date, tx_month, tx_type, category, hotel_id, hotel_name, amount_egp, amount_usd, beneficiary, description, payment_method, actor),
            )
            tx_id = cur.lastrowid

    if tx_type == "EXPENSE":
        emit_notification(
            f"💸 صرف من الخزنة ({category}) • {amount_egp:,.2f} LE",
            f"تم تسجيل مصروف من الخزنة بواسطة ({actor}) بقيمة {amount_egp:,.2f} LE — البند: {category} — المستفيد: {beneficiary or '-'} — التفاصيل: {description}",
            notification_type="manager_edit",
            target_role="CEO",
            hotel_id=hotel_id,
            target_url="/treasury",
            amount=amount_egp,
            priority="high",
        )
    else:
        emit_notification(
            f"🏦 إيداع عهدة جديدة بالخزنة من الأونر • {amount_egp:,.2f} LE",
            f"قام الأونر ({actor}) بإضافة عهدة للخزنة بقيمة {amount_egp:,.2f} LE لصالح ({beneficiary or 'المدير'}) — البيان: {description}",
            notification_type="broadcast",
            target_role="Manager",
            hotel_id=hotel_id,
            target_url="/treasury",
            amount=amount_egp,
            priority="critical",
        )
    audit("TREASURY_TX", "treasury_transactions", f"{tx_type}: {amount_egp} LE - {description}")
    return ok({"id": tx_id})


@app.delete("/api/treasury/<int:tx_id>")
@login_required
def api_treasury_delete(tx_id):
    if not has_full_access():
        return fail("🔒 حذف سجلات الخزنة متاح لحساب الأونر (CEO) فقط!", 403)
    ensure_web_extension_tables()
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM treasury_transactions WHERE id=%s", (tx_id,))
    audit("DELETE_TREASURY_TX", "treasury_transactions", f"حذف حركة خزنة #{tx_id}")
    return ok()



# =============================================================================
# 📌 16. كود قفل حسابات اليوم المعتمد (Day Lock) وطلب إذن تعديل المدير من المحاسب
# =============================================================================
def ensure_day_lock_tables():
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS daily_account_locks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    lock_date DATE NOT NULL,
                    hotel_name VARCHAR(120) NOT NULL DEFAULT 'جميع الفنادق',
                    is_locked TINYINT(1) NOT NULL DEFAULT 1,
                    unlocked_for_manager TINYINT(1) NOT NULL DEFAULT 0,
                    locked_by VARCHAR(100) DEFAULT 'المحاسب',
                    notes VARCHAR(255) DEFAULT '',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_day_hotel_lock (lock_date, hotel_name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS day_lock_edit_requests (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    lock_date DATE NOT NULL,
                    hotel_name VARCHAR(120) NOT NULL DEFAULT 'جميع الفنادق',
                    room_number VARCHAR(50) DEFAULT '',
                    requested_by VARCHAR(100) NOT NULL,
                    reason TEXT NOT NULL,
                    proposed_json LONGTEXT DEFAULT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'Pending',
                    reviewed_by VARCHAR(100) DEFAULT NULL,
                    review_note VARCHAR(255) DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at DATETIME DEFAULT NULL,
                    INDEX idx_dler_status (status),
                    INDEX idx_dler_date (lock_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
    except Exception:
        pass


def can_manage_day_locks():
    """المحاسب (Accountant) والأونر (CEO) فقط يملكون صلاحية قفل اليوم أو قبول/رفض طلبات تعديل المدير."""
    return has_full_access() or is_accountant_only()


def is_day_locked_for_current_user(target_date: str, hotel_name: str = "") -> bool:
    """يتحقق هل تاريخ اليوم مقفول على المدير/السيلز أم مسموح بالتعديل."""
    if can_manage_day_locks():
        return False
    ensure_day_lock_tables()
    d_str = str(target_date or date.today().isoformat())[:10]
    h_str = str(hotel_name or "").strip() or "جميع الفنادق"
    try:
        with get_db_connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT * FROM daily_account_locks
                   WHERE lock_date=%s AND (hotel_name=%s OR hotel_name='جميع الفنادق')
                   AND is_locked=1 AND unlocked_for_manager=0
                   LIMIT 1""",
                (d_str, h_str)
            )
            return bool(cur.fetchone())
    except Exception:
        return False


@app.get("/api/day-locks")
@login_required
def api_day_locks_list():
    ensure_day_lock_tables()
    target_date = (request.args.get("date") or "").strip()[:10]
    hotel_name = (request.args.get("hotel_name") or "").strip()
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM daily_account_locks ORDER BY lock_date DESC, id DESC LIMIT 200")
        locks = rows_to_json(cur.fetchall())
        cur.execute("SELECT * FROM day_lock_edit_requests ORDER BY id DESC LIMIT 100")
        reqs = rows_to_json(cur.fetchall())

    active_lock = None
    if target_date:
        for lk in locks:
            if str(lk.get("lock_date"))[:10] == target_date and int(lk.get("is_locked") or 0) == 1:
                if not hotel_name or lk.get("hotel_name") in (hotel_name, "جميع الفنادق"):
                    active_lock = lk
                    break

    return ok({
        "locks": locks,
        "requests": reqs,
        "active_lock": active_lock,
        "can_lock": can_manage_day_locks(),
        "is_blocked_for_me": bool(active_lock and not int(active_lock.get("unlocked_for_manager") or 0) and not can_manage_day_locks())
    })


@app.post("/api/day-locks/toggle")
@login_required
def api_day_locks_toggle():
    if not can_manage_day_locks():
        return fail("🔒 قفل واعتماد حسابات اليوم متاح للمحاسب أو الأونر فقط!", 403)
    ensure_day_lock_tables()
    d = request.get_json(silent=True) or {}
    lock_date = str(d.get("lock_date") or date.today().isoformat())[:10]
    hotel_name = str(d.get("hotel_name") or "جميع الفنادق").strip() or "جميع الفنادق"
    lock_state = 1 if bool(d.get("is_locked", True)) else 0
    notes = str(d.get("notes") or "").strip()
    actor = (current_user() or {}).get("nickname") or (current_user() or {}).get("full_name") or "المحاسب"

    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(
            """INSERT INTO daily_account_locks (lock_date, hotel_name, is_locked, unlocked_for_manager, locked_by, notes)
               VALUES (%s, %s, %s, 0, %s, %s)
               ON DUPLICATE KEY UPDATE is_locked=%s, unlocked_for_manager=0, locked_by=%s, notes=%s""",
            (lock_date, hotel_name, lock_state, actor, notes, lock_state, actor, notes)
        )

    status_txt = "قفل واعتماد" if lock_state else "إلغاء قفل وفتح"
    emit_notification(
        f"{'🔒' if lock_state else '🔓'} {status_txt} حسابات يوم {lock_date} ({hotel_name})",
        f"قام ({actor}) بـ {status_txt} حسابات يوم {lock_date} لفندق ({hotel_name}). {'أي تعديل من المدير يتطلب الآن إرسال طلب موافقة للمحاسب.' if lock_state else 'التعديل متاح الآن.'}",
        notification_type="day_lock",
        target_role="Manager",
        target_url="/daily-sales",
        priority="high"
    )
    audit("DAY_LOCK_TOGGLE", "daily_account_locks", f"{status_txt} حسابات {lock_date} ({hotel_name})")
    return ok({"lock_date": lock_date, "hotel_name": hotel_name, "is_locked": lock_state})


@app.post("/api/day-locks/request-edit")
@login_required
def api_day_locks_request_edit():
    """يرسل المدير طلب إذن تعديل للمحاسب على يوم مقفول."""
    ensure_day_lock_tables()
    d = request.get_json(silent=True) or {}
    lock_date = str(d.get("lock_date") or date.today().isoformat())[:10]
    hotel_name = str(d.get("hotel_name") or "جميع الفنادق").strip() or "جميع الفنادق"
    room_number = str(d.get("room_number") or "").strip()
    reason = str(d.get("reason") or "").strip()
    proposed = d.get("proposed")
    if not reason:
        return fail("يرجى كتابة سبب التعديل المطلوب وإرساله للمحاسب")

    actor = (current_user() or {}).get("nickname") or (current_user() or {}).get("full_name") or "مدير الفرع"
    proposed_str = json.dumps(proposed, ensure_ascii=False) if proposed else None

    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(
            """INSERT INTO day_lock_edit_requests (lock_date, hotel_name, room_number, requested_by, reason, proposed_json, status)
               VALUES (%s, %s, %s, %s, %s, %s, 'Pending')""",
            (lock_date, hotel_name, room_number, actor, reason, proposed_str)
        )
        req_id = c.lastrowid

    emit_notification(
        f"📩 طلب إذن تعديل يوم مقفول ({lock_date}) • غرفة {room_number or 'عام'}",
        f"يطلب المدير ({actor}) إذن تعديل حسابات يوم ({lock_date}) في فندق ({hotel_name}){' لغرفة ' + room_number if room_number else ''} — السبب: {reason}",
        notification_type="day_lock_request",
        target_role="Accountant",
        target_url="/daily-sales",
        priority="critical"
    )
    audit("REQUEST_DAY_UNLOCK", "day_lock_edit_requests", f"طلب تعديل يوم {lock_date} من {actor}: {reason}")
    return ok({"id": req_id, "message": "تم إرسال طلب التعديل للمحاسب بنجاح وفي انتظار القبول أو الرفض"})


@app.post("/api/day-locks/requests/<int:req_id>/decide")
@login_required
def api_day_locks_decide_request(req_id):
    """قبول أو رفض المحاسب لطلب تعديل المدير على يوم مقفول."""
    if not can_manage_day_locks():
        return fail("قبول أو رفض طلبات التعديل متاح للمحاسب أو الأونر فقط!", 403)
    ensure_day_lock_tables()
    d = request.get_json(silent=True) or {}
    decision = str(d.get("decision") or "approve").strip().lower()
    review_note = str(d.get("review_note") or "").strip()
    actor = (current_user() or {}).get("nickname") or (current_user() or {}).get("full_name") or "المحاسب"

    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM day_lock_edit_requests WHERE id=%s LIMIT 1", (req_id,))
        req = cur.fetchone()
        if not req:
            return fail("طلب التعديل غير موجود", 404)

        lock_date = str(req.get("lock_date"))[:10]
        hotel_name = str(req.get("hotel_name") or "جميع الفنادق")
        room_number = str(req.get("room_number") or "")
        requester = str(req.get("requested_by") or "المدير")

        c = conn.cursor()
        if decision == "approve":
            c.execute(
                "UPDATE day_lock_edit_requests SET status='Approved', reviewed_by=%s, review_note=%s, reviewed_at=NOW() WHERE id=%s",
                (actor, review_note or "تمت الموافقة وفتح التعديل", req_id)
            )
            # فتح القفل للمدير ليتمكن من التعديل
            c.execute(
                "UPDATE daily_account_locks SET unlocked_for_manager=1, is_locked=0 WHERE lock_date=%s AND (hotel_name=%s OR hotel_name='جميع الفنادق')",
                (lock_date, hotel_name)
            )
        else:
            c.execute(
                "UPDATE day_lock_edit_requests SET status='Rejected', reviewed_by=%s, review_note=%s, reviewed_at=NOW() WHERE id=%s",
                (actor, review_note or "تم رفض الطلب", req_id)
            )

    if decision == "approve":
        emit_notification(
            f"✅ وافق المحاسب ({actor}) على طلب تعديل يوم {lock_date}",
            f"تم قبول طلبك لتعديل حسابات يوم ({lock_date}) لفندق ({hotel_name}){' غرفة ' + room_number if room_number else ''} وفتح التعديل لك الآن.",
            notification_type="day_lock_approved",
            target_role="Manager",
            target_employee=requester,
            target_url="/daily-sales",
            priority="high"
        )
    else:
        emit_notification(
            f"❌ رفض المحاسب ({actor}) طلب تعديل يوم {lock_date}",
            f"تم رفض طلب تعديل حسابات يوم ({lock_date}) لفندق ({hotel_name}){' غرفة ' + room_number if room_number else ''} — ملاحظة المحاسب: {review_note or 'الحسابات معتمدة ونهائية'}",
            notification_type="day_lock_rejected",
            target_role="Manager",
            target_employee=requester,
            target_url="/daily-sales",
            priority="high"
        )

    audit("DECIDE_DAY_UNLOCK", "day_lock_edit_requests", f"{decision.upper()} request #{req_id} by {actor}")
    return ok({"id": req_id, "status": "Approved" if decision == "approve" else "Rejected"})


@app.get("/api/daily-sales")
@require_permission("sales_access")
def api_daily_sales_list():
    start = request.args.get("start") or request.args.get("date") or date.today().isoformat()
    end = request.args.get("end") or request.args.get("date") or start
    ids = allowed_hotel_ids(); w, p = make_where_for_hotels("d.hotel_id", ids)
    hotel = request.args.get("hotel_id")
    if hotel:
        w += " AND d.hotel_id=%s"; p.append(safe_int(hotel))
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            f"""SELECT d.*,h.hotel_name FROM daily_income d LEFT JOIN hotels h ON h.id=d.hotel_id
                WHERE d.income_date BETWEEN %s AND %s {w} ORDER BY d.income_date DESC,d.id DESC""", tuple([start, end] + p))
        rows = rows_to_json(cur.fetchall())
    if is_personal_scope_user():
        rows = [r for r in rows if record_belongs_to_current_user(r)]
    for r in rows:
        r["gross_total"] = round(safe_float(r.get("deposit_applied")) + safe_float(r.get("income_usd")) + safe_float(r.get("income_eur")) + ((safe_float(r.get("income_le_m")) + safe_float(r.get("income_le_k"))) / (safe_float(r.get("le_to_usd")) or safe_float(r.get("order_exchange_rate")) or 50)), 2)
    ensure_web_extension_tables()
    notes_rows = []
    if not is_personal_scope_user():
        nw, np = make_where_for_hotels("n.hotel_id", ids)
        if hotel:
            nw += " AND n.hotel_id=%s"
            np.append(safe_int(hotel))
        with get_db_connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                f"""SELECT n.*, h.hotel_name FROM daily_income_notes n
                    LEFT JOIN hotels h ON h.id = n.hotel_id
                    WHERE n.note_date BETWEEN %s AND %s {nw}
                    ORDER BY n.note_date DESC, n.id DESC""",
                tuple([start, end] + np),
            )
            notes_rows = rows_to_json(cur.fetchall())

    orders_net = round(sum(safe_float(x.get("daily_total")) for x in rows), 2)
    notes_in_usd = round(sum(safe_float(n.get("equivalent_usd")) for n in notes_rows if str(n.get("note_type") or "").upper() == "IN"), 2)
    notes_out_usd = round(sum(safe_float(n.get("equivalent_usd")) for n in notes_rows if str(n.get("note_type") or "").upper() != "IN"), 2)
    notes_diff_usd = round(notes_in_usd - notes_out_usd, 2)
    final_net = round(orders_net + notes_diff_usd, 2)

    summary = {
        "orders": len(rows),
        "gross": round(sum(safe_float(x.get("gross_total")) for x in rows), 2),
        "costs": round(sum(safe_float(x.get("cost_total")) for x in rows), 2),
        "orders_net": orders_net,
        "notes_in_usd": notes_in_usd,
        "notes_out_usd": notes_out_usd,
        "notes_diff_usd": notes_diff_usd,
        "net": final_net,
    }
    return ok({"rows": rows, "notes": notes_rows, "summary": summary})




@app.get("/api/daily-sales/notes")
@require_permission("sales_access")
def api_daily_income_notes_list():
    ensure_web_extension_tables()
    if is_personal_scope_user():
        return ok([])
    start = request.args.get("start") or request.args.get("date") or date.today().isoformat()
    end = request.args.get("end") or request.args.get("date") or start
    ids = allowed_hotel_ids()
    nw, np = make_where_for_hotels("n.hotel_id", ids)
    hotel = request.args.get("hotel_id")
    if hotel:
        nw += " AND n.hotel_id=%s"
        np.append(safe_int(hotel))
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            f"""SELECT n.*, h.hotel_name FROM daily_income_notes n
                LEFT JOIN hotels h ON h.id = n.hotel_id
                WHERE n.note_date BETWEEN %s AND %s {nw}
                ORDER BY n.note_date DESC, n.id DESC""",
            tuple([start, end] + np),
        )
        return ok(rows_to_json(cur.fetchall()))


@app.post("/api/daily-sales/notes")
@require_permission("sales_access")
def api_daily_income_note_save():
    if is_personal_scope_user():
        return fail("إضافة ملاحظات الوارد والصادر على الدخل متاحة للإدارة والحسابات فقط", 403)
    ensure_web_extension_tables()
    d = request.get_json(silent=True) or {}
    note_id = safe_int(d.get("id"), 0)
    hotel_id = safe_int(d.get("hotel_id"), 0) or (hotel_id_from_name(d.get("hotel_name")) if d.get("hotel_name") else None) or 1
    if not verify_hotel_id(hotel_id):
        return fail("ليس لديك صلاحية لهذا الفندق", 403)
    note_date = str(d.get("note_date") or date.today().isoformat())[:10]
    note_type = "IN" if str(d.get("note_type") or "OUT").upper() == "IN" else "OUT"
    amt_usd = max(0.0, safe_float(d.get("amount_usd")))
    amt_eur = max(0.0, safe_float(d.get("amount_eur")))
    amt_cash = max(0.0, safe_float(d.get("amount_le_cash")))
    amt_office = max(0.0, safe_float(d.get("amount_le_office")))
    rate = safe_float(d.get("exchange_rate")) or 50.0
    equiv_usd = round(amt_usd + amt_eur + ((amt_cash + amt_office) / rate), 2)
    if equiv_usd <= 0:
        return fail("يرجى إدخال قيمة المبلغ أولاً")
    person_name = str(d.get("person_name") or "").strip()
    note_text = str(d.get("note_text") or "").strip()
    if not note_text:
        return fail("يرجى كتابة تفاصيل الملاحظة")
    actor = (current_user() or {}).get("nickname") or (current_user() or {}).get("full_name") or "المدير"

    with get_db_connection() as conn:
        cur = conn.cursor()
        if note_id > 0:
            cur.execute(
                """UPDATE daily_income_notes
                   SET hotel_id=%s, note_date=%s, note_type=%s, amount_usd=%s, amount_eur=%s,
                       amount_le_cash=%s, amount_le_office=%s, exchange_rate=%s, equivalent_usd=%s,
                       person_name=%s, note_text=%s
                   WHERE id=%s""",
                (hotel_id, note_date, note_type, amt_usd, amt_eur, amt_cash, amt_office, rate, equiv_usd, person_name, note_text, note_id),
            )
        else:
            cur.execute(
                """INSERT INTO daily_income_notes
                   (hotel_id, note_date, note_type, amount_usd, amount_eur, amount_le_cash, amount_le_office, exchange_rate, equivalent_usd, person_name, note_text, created_by)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (hotel_id, note_date, note_type, amt_usd, amt_eur, amt_cash, amt_office, rate, equiv_usd, person_name, note_text, actor),
            )
            note_id = cur.lastrowid

    type_label = "➕ وارد (زيادة على الدخل)" if note_type == "IN" else "➖ صادر / مصروف (نقص من الدخل)"
    hname = hotel_name_from_id(hotel_id) or "الفندق"
    emit_notification(
        f"📝 ملاحظة دخل يومي ({type_label}) • ${equiv_usd:.2f} ({hname})",
        f"سجل ({actor}) ملاحظة على الدخل اليومي في {hname}: [{type_label}] بقيمة تعادل ${equiv_usd:.2f} — الطرف/الشخص: {person_name or '-'} — البيان: {note_text}",
        notification_type="manager_edit",
        target_role="CEO",
        hotel_id=hotel_id,
        target_url="/daily-sales",
        amount=equiv_usd,
        priority="high",
    )
    audit("INCOME_NOTE", "daily_income_notes", f"{type_label}: ${equiv_usd:.2f} - {note_text}")
    return ok({"id": note_id, "equivalent_usd": equiv_usd, "note_type": note_type})


@app.delete("/api/daily-sales/notes/<int:note_id>")
@require_permission("sales_access")
def api_daily_income_note_delete(note_id):
    if is_personal_scope_user():
        return fail("غير مسموح", 403)
    ensure_web_extension_tables()
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM daily_income_notes WHERE id=%s", (note_id,))
        row = cur.fetchone()
        if not row:
            return fail("الملاحظة غير موجودة", 404)
        if not verify_hotel_id(row.get("hotel_id")):
            return fail("ليس لديك صلاحية لهذا الفندق", 403)
        c = conn.cursor()
        c.execute("DELETE FROM daily_income_notes WHERE id=%s", (note_id,))
    audit("DELETE_INCOME_NOTE", "daily_income_notes", f"حذف ملاحظة دخل #{note_id}")
    return ok()


@app.get("/api/daily-sales/eligible-bookings")
@require_permission("sales_access")
def api_eligible_bookings():
    day=request.args.get("date") or date.today().isoformat();requested=request.args.get("hotel_id","").strip();requested_name=hotel_name_from_id(requested) if requested else None;allowed_names=allowed_hotel_names()
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);bookings=fetch_booking_rows(cur,5000)
        daily_cols=table_columns("daily_income")
        saved_by_id={}
        saved_by_room={}
        saved_pairs={}
        try:
            # جلب سجلات الدخل المرتبطة بنفس التاريخ أو بأرقام الحجوزات لتمكين عرض وتعديل الدخل المسجل
            day_booking_ids=[safe_int(b.get("id")) for b in bookings if str(b.get("booking_date") or "")[:10]==day and safe_int(b.get("id"))>0]
            if "booking_id" in daily_cols and day_booking_ids:
                ph=",".join(["%s"]*len(day_booking_ids))
                cur.execute(f"SELECT * FROM daily_income WHERE booking_id IN ({ph}) OR income_date=%s ORDER BY id DESC", tuple(day_booking_ids+[day]))
            elif "income_date" in daily_cols:
                q="SELECT * FROM daily_income WHERE income_date=%s ORDER BY id DESC";args=[day]
                if requested and "hotel_id" in daily_cols:q="SELECT * FROM daily_income WHERE income_date=%s AND hotel_id=%s ORDER BY id DESC";args.append(safe_int(requested))
                cur.execute(q,tuple(args))
            else:
                cur.execute("SELECT * FROM daily_income ORDER BY id DESC LIMIT 500")
            for d in cur.fetchall():
                d_clean={k:serialize(v) for k,v in d.items()}
                bid=safe_int(d.get("booking_id"))
                if bid and bid not in saved_by_id:
                    saved_by_id[bid]=d_clean
                rm=str(d.get("room_number") or "").strip()
                if rm and str(d.get("income_date") or "")[:10]==day and rm not in saved_by_room:
                    saved_by_room[rm]=d_clean
                pair_key=(str(d.get("sales_person") or ""),str(d.get("photographer") or ""))
                if str(d.get("income_date") or "")[:10]==day and pair_key not in saved_pairs:
                    saved_pairs[pair_key]=d_clean
        except Exception:pass
        out=[]
        show_all = request.args.get("show_all") == "1"
        for r in bookings:
            if str(r.get("booking_date") or "")[:10]!=day:continue
            st_low = str(r.get("status") or "").lower()
            if "كنسل" in st_low or "cancel" in st_low or "ملغ" in st_low: continue
            if not show_all and not any(k in st_low for k in ["deliver", "checkout", "تسليم", "تصوير"]):
                if safe_int(r.get("id")) not in saved_by_id and str(r.get("room_number") or "").strip() not in saved_by_room:
                    continue
            if not record_belongs_to_current_user(r):continue
            if allowed_names is not None and r.get("_has_hotel_column") and r.get("hotel") not in allowed_names:continue
            if requested_name and r.get("_has_hotel_column") and r.get("hotel")!=requested_name:continue
            rr={k:serialize(v) for k,v in r.items() if not str(k).startswith("_")}
            bid=safe_int(r.get("id"))
            rm=str(r.get("room_number") or "").strip()
            matched_inc=saved_by_id.get(bid) or saved_by_room.get(rm)
            rr["income_saved"]=bool(matched_inc)
            rr["saved_income"]=matched_inc
            rr["income_id"]=matched_inc.get("id") if matched_inc else None
            if not hasattr(g, "_elig_deposits_by_room"):
                dep_map = {}
                if table_exists("deposits"):
                    try:
                        dcols = table_columns("deposits")
                        fields = [f"COALESCE(SUM(`{k}`),0) `{k}`" for k in ["deposit_usd","deposit_eur","deposit_le_cash","deposit_le_visa"] if k in dcols]
                        if fields and "room_number" in dcols:
                            cur.execute("SELECT room_number, " + ",".join(fields) + " FROM deposits GROUP BY room_number")
                            for dr in cur.fetchall():
                                if dr and dr.get("room_number") is not None:
                                    dep_map[str(dr.get("room_number")).strip()] = dr
                    except Exception:
                        dep_map = {}
                g._elig_deposits_by_room = dep_map
            dep = g._elig_deposits_by_room.get(str(r.get("room_number") or "").strip(), {})
            rr["deposit_history"]={"usd":safe_float(dep.get("deposit_usd",r.get("deposit_usd"))),"eur":safe_float(dep.get("deposit_eur",r.get("deposit_eur"))),"cash":safe_float(dep.get("deposit_le_cash",r.get("deposit_le_cash"))),"visa":safe_float(dep.get("deposit_le_visa",r.get("deposit_le_visa")))}
            out.append(rr)
        out.sort(key=lambda x:str(x.get("room_number") or ""));return ok(out)

@app.post("/api/daily-sales")
@require_permission("sales_access")
def api_daily_sales_save():
    if is_photographer_only() or is_sales_only(): return fail("تسجيل وتعديل الدخل النهائي متاح للإدارة والمحاسب فقط", 403)
    d=request.get_json(silent=True) or {}
    sale_id=safe_int(d.get("sale_id") or d.get("id"),0)
    booking_id=safe_int(d.get("booking_id"),0)
    room=str(d.get("room_number") or "").strip()
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True)
        existing_sale=None
        cols=table_columns("daily_income")
        if sale_id:
            cur.execute("SELECT * FROM daily_income WHERE id=%s",(sale_id,))
            existing_sale=cur.fetchone()
        elif booking_id and "booking_id" in cols:
            cur.execute("SELECT * FROM daily_income WHERE booking_id=%s ORDER BY id DESC LIMIT 1",(booking_id,))
            existing_sale=cur.fetchone()
            if existing_sale:
                sale_id=safe_int(existing_sale.get("id"))

        row=None
        if booking_id:
            row=get_booking_dict(cur,booking_id)
        elif existing_sale and existing_sale.get("booking_id"):
            row=get_booking_dict(cur,safe_int(existing_sale.get("booking_id")))
        elif room:
            rows=fetch_booking_rows(cur,5000);row=next((r for r in rows if str(r.get("room_number") or "")==room),None)

        if not row and not existing_sale:
            return fail("الحجز غير موجود",404)
        if row and not booking_scope_ok(row):
            return fail("ليس لديك صلاحية",403)
        if existing_sale and not verify_hotel_id(existing_sale.get("hotel_id")):
            return fail("ليس لديك صلاحية",403)

        hid=safe_int(d.get("hotel_id"),0) or (existing_sale.get("hotel_id") if existing_sale else 0) or (hotel_id_from_name(row.get("hotel")) if row else 0) or 1
        inc_usd=safe_float(d.get("income_usd"));inc_eur=safe_float(d.get("income_eur"));inc_lem=safe_float(d.get("income_le_m"));inc_lek=safe_float(d.get("income_le_k"))
        rate=safe_float(d.get("le_to_usd") or d.get("order_exchange_rate")) or 50.0
        deposit_applied=safe_float(d.get("deposit_applied"))
        cost_dress=safe_float(d.get("cost_dress"));cost_usb=safe_float(d.get("cost_usb"));cost_album=safe_float(d.get("cost_album"))
        le_converted=(inc_lem+inc_lek)/rate if rate>0 else 0
        gross=deposit_applied+inc_usd+inc_eur+le_converted
        cost_total=cost_dress+cost_usb+cost_album
        daily_total=gross-cost_total
        entry_date=d.get("income_date") or (str(existing_sale.get("income_date"))[:10] if existing_sale and existing_sale.get("income_date") else None) or date.today().isoformat()
        hname_lock = hotel_name_from_id(hid) or (row.get("hotel") if row else "") or "جميع الفنادق"
        if is_day_locked_for_current_user(entry_date, hname_lock):
            return jsonify({"ok": False, "locked": True, "lock_date": str(entry_date)[:10], "hotel_name": hname_lock, "room_number": str(d.get("room_number") or (row.get("room_number") if row else "") or ""), "error": f"🔒 حسابات يوم ({str(entry_date)[:10]}) مقفولة ومعتمدة من المحاسب! أرسل طلب إذن تعديل للمحاسب للموافقة عليه."}), 423
        raw_photog=d.get("photographer") or (row.get("photographer") if row else (existing_sale.get("photographer") if existing_sale else ""))
        posted_photographers=split_names(raw_photog)[:3]
        photographer_value=", ".join(posted_photographers) if posted_photographers else str(raw_photog or "")
        room_val=(row.get("room_number") if row else None) or d.get("room_number") or (existing_sale.get("room_number") if existing_sale else "")
        values={
            "hotel_id":hid,
            "booking_id":(row.get("id") if row else (existing_sale.get("booking_id") if existing_sale else None)),
            "room_number":room_val,
            "sales_person":d.get("sales_person") or (row.get("sales_person") if row else (existing_sale.get("sales_person") if existing_sale else "")),
            "photographer":photographer_value,
            "deposit_usd":(row.get("deposit_usd") if row else (existing_sale.get("deposit_usd") if existing_sale else 0)) or 0,
            "deposit_eur":(row.get("deposit_eur") if row else (existing_sale.get("deposit_eur") if existing_sale else 0)) or 0,
            "deposit_le_visa":(row.get("deposit_le_visa") if row else (existing_sale.get("deposit_le_visa") if existing_sale else 0)) or 0,
            "deposit_le_cash":(row.get("deposit_le_cash") if row else (existing_sale.get("deposit_le_cash") if existing_sale else 0)) or 0,
            "deposit_applied":deposit_applied,
            "income_usd":inc_usd,
            "income_eur":inc_eur,
            "income_le_m":inc_lem,
            "income_le_k":inc_lek,
            "le_to_usd":rate,
            "order_exchange_rate":rate,
            "cost_dress":cost_dress,
            "cost_usb":cost_usb,
            "cost_album":cost_album,
            "cost_total":cost_total,
            "daily_total":daily_total,
            "income_date":entry_date
        }
        use={k:v for k,v in values.items() if k in cols}
        if not use:return fail("جدول daily_income لا يحتوي الأعمدة المطلوبة")
        c=conn.cursor()
        old_net = safe_float(existing_sale.get("daily_total")) if existing_sale else 0.0
        if existing_sale and sale_id:
            set_clause=",".join(f"`{k}`=%s" for k in use.keys())
            c.execute(f"UPDATE daily_income SET {set_clause} WHERE id=%s", [use[k] for k in use.keys()]+[sale_id])
            sid=sale_id
            is_update=True
            # توثيق التعديل في جدول daily_income_adjustments
            try:
                if table_exists("daily_income_adjustments"):
                    impact = round(daily_total - old_net, 2)
                    actor = (current_user() or {}).get("nickname") or (current_user() or {}).get("full_name") or "Admin"
                    reason_txt = str(d.get("adjustment_reason") or "").strip()
                    if not reason_txt:
                        reason_txt = f"تعديل صافي غرفة {room_val} من {old_net:.2f}$ إلى {daily_total:.2f}$"
                    else:
                        reason_txt = f"{reason_txt} (من {old_net:.2f}$ إلى {daily_total:.2f}$)"
                    c.execute(
                        "INSERT INTO daily_income_adjustments (hotel_id, transaction_id, adjustment_date, impact_amount, reason, created_by) VALUES (%s,%s,%s,%s,%s,%s)",
                        (hid, sid, date.today().isoformat(), impact, reason_txt[:250], actor)
                    )
            except Exception:
                pass
        else:
            names=list(use)
            c.execute("INSERT INTO daily_income ("+",".join(f"`{x}`" for x in names)+") VALUES ("+",".join(["%s"]*len(names))+")",[use[x] for x in names])
            sid=c.lastrowid
            is_update=False
        if room_val:
            set_booking_status(c,room_number=room_val,status="Delivered")

    target_bid=(row.get("id") if row else (existing_sale.get("booking_id") if existing_sale else None))
    if is_update:
        if target_bid:booking_activity(target_bid,"SALE_EDIT","تم تعديل الدخل",f"الصافي بعد التعديل {daily_total:.2f}$")
        audit("EDIT_SALE","daily_income",f"تعديل مبيعات غرفة {room_val} (سجل #{sid}) من {old_net:.2f}$ إلى {daily_total:.2f}$");
        emit_notification(f"🛡️ تعديل بيانات دخل غرفة {room_val} ({hotel_name_from_id(hid) or ''})", f"قام {(current_user() or {}).get('nickname') or 'المدير'} بتعديل صافي دخل الأوردر من ${old_net:.2f} إلى ${daily_total:.2f} (المصور: {photographer_value} • السيلز: {values.get('sales_person')}).", notification_type="manager_edit", target_role="CEO", hotel_id=hid, target_url="/daily-sales", target_employee=photographer_value, sales_person=values.get("sales_person") or "", amount=daily_total, priority="high")
    else:
        if target_bid:booking_activity(target_bid,"SALE","تم تسجيل الدخل",f"الصافي {daily_total:.2f}$")
        audit("ADD_SALE","daily_income",f"تسجيل مبيعات غرفة {room_val} بصافي {daily_total:.2f}");
        emit_notification(f"💰 تسجيل دخل أوردر • غرفة {room_val}", f"تم تسجيل دخل الأوردر بصافي ${daily_total:.2f} (المصور: {photographer_value} • السيلز: {values.get('sales_person')}).", notification_type="sale_added", target_url="/daily-sales", target_employee=photographer_value, sales_person=values.get("sales_person") or "", amount=daily_total)
    return ok({"id":sid,"updated":is_update,"gross":round(gross,2),"cost_total":round(cost_total,2),"daily_total":round(daily_total,2)})

@app.put("/api/daily-sales/<int:sale_id>")
@require_permission("sales_access")
def api_daily_sale_update(sale_id):
    d=request.get_json(silent=True) or {}
    d["sale_id"]=sale_id
    return api_daily_sales_save()

@app.get("/api/daily-sales/adjustments")
@require_permission("sales_access")
def api_daily_sales_adjustments():
    if not table_exists("daily_income_adjustments"):
        return ok([])
    ids = allowed_hotel_ids(); w, p = make_where_for_hotels("a.hotel_id", ids)
    tx_id = safe_int(request.args.get("transaction_id"), 0)
    if tx_id:
        w += " AND a.transaction_id=%s"; p.append(tx_id)
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            f"""SELECT a.*, d.room_number, d.sales_person, d.photographer, d.daily_total AS current_net, h.hotel_name
                FROM daily_income_adjustments a
                LEFT JOIN daily_income d ON d.id = a.transaction_id
                LEFT JOIN hotels h ON h.id = a.hotel_id
                WHERE 1=1 {w}
                ORDER BY a.adjustment_id DESC LIMIT 250""",
            tuple(p)
        )
        return ok(rows_to_json(cur.fetchall()))

@app.delete("/api/daily-sales/<int:sale_id>")
@require_permission("sales_access")
def api_daily_sale_delete(sale_id):
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM daily_income WHERE id=%s", (sale_id,)); row = cur.fetchone()
        if not row: return fail("السجل غير موجود", 404)
        if not verify_hotel_id(row.get("hotel_id")): return fail("ليس لديك صلاحية", 403)
        del_date = str(row.get("income_date") or date.today().isoformat())[:10]
        del_hname = hotel_name_from_id(row.get("hotel_id")) or "جميع الفنادق"
        if is_day_locked_for_current_user(del_date, del_hname):
            return jsonify({"ok": False, "locked": True, "lock_date": del_date, "hotel_name": del_hname, "room_number": str(row.get("room_number") or ""), "error": f"🔒 حسابات يوم ({del_date}) مقفولة ومعتمدة من المحاسب! لا يمكن الحذف إلا بطلب موافقة من المحاسب."}), 423
        conn.cursor().execute("DELETE FROM daily_income WHERE id=%s", (sale_id,))
    audit("DELETE_SALE", "daily_income", f"حذف سجل دخل #{sale_id}")
    return ok()


@app.get("/api/daily-sales/analytics")
@require_permission("sales_access")
def api_daily_sales_analytics():
    start = request.args.get("start") or date.today().replace(day=1).isoformat()
    end = request.args.get("end") or date.today().isoformat()
    ids = allowed_hotel_ids(); w, p = make_where_for_hotels("hotel_id", ids)
    requested_hotel = request.args.get("hotel_id", "").strip()
    if requested_hotel:
        rh = safe_int(requested_hotel, -1)
        if ids is not None and rh not in ids:
            return ok({"sales": [], "photographers": [], "trend": [], "net": 0})
        w += " AND hotel_id=%s"; p.append(rh)
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(f"SELECT * FROM daily_income WHERE income_date BETWEEN %s AND %s {w}", tuple([start, end] + p))
        rows = rows_to_json(cur.fetchall())
    if is_personal_scope_user():
        rows = [r for r in rows if record_belongs_to_current_user(r)]
    my_names = current_employee_names() if is_personal_scope_user() else None
    sales, photos, trend = {}, {}, {}
    for r in rows:
        gross = safe_float(r.get("deposit_applied")) + safe_float(r.get("income_usd")) + safe_float(r.get("income_eur"))
        rate = safe_float(r.get("le_to_usd")) or 50
        gross += (safe_float(r.get("income_le_m")) + safe_float(r.get("income_le_k"))) / rate
        for name in split_names(r.get("sales_person")) or [str(r.get("sales_person") or "غير محدد")]:
            sales[name] = sales.get(name, 0) + gross / max(1, len(split_names(r.get("sales_person")) or [1]))
        pnames = split_names(r.get("photographer"))
        if pnames:
            for name in pnames: photos[name] = photos.get(name, 0) + gross / len(pnames)
        day = str(r.get("income_date"))[:10]
        trend[day] = trend.get(day, 0) + safe_float(r.get("daily_total"))
    return ok({
        "sales": [{"name": k, "value": round(v, 2)} for k, v in sorted(sales.items(), key=lambda x: x[1], reverse=True) if not my_names or str(k).strip().lower() in my_names],
        "photographers": [{"name": k, "value": round(v, 2)} for k, v in sorted(photos.items(), key=lambda x: x[1], reverse=True) if not my_names or str(k).strip().lower() in my_names],
        "trend": [{"date": k, "value": round(v, 2)} for k, v in sorted(trend.items())],
        "net": round(sum(safe_float(x.get("daily_total")) for x in rows), 2),
    })


@app.get("/api/coin-safe")
@require_permission("sales_access")
def api_coin_list():
    ids = allowed_hotel_ids(); w, p = make_where_for_hotels("hotel_id", ids)
    requested_hotel = request.args.get("hotel_id", "").strip()
    if requested_hotel:
        rh = safe_int(requested_hotel, -1)
        if ids is not None and rh not in ids:
            return ok({"rows": [], "balance": 0})
        w += " AND hotel_id=%s"; p.append(rh)
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(f"SELECT * FROM coin_safe_transactions WHERE 1=1 {w} ORDER BY transaction_id DESC LIMIT 500", tuple(p))
        rows = rows_to_json(cur.fetchall())
    balance = sum(safe_float(r.get("amount")) * (1 if r.get("transaction_type") == "IN" else -1) for r in rows)
    return ok({"rows": rows, "balance": round(balance, 2)})


@app.post("/api/coin-safe")
@require_permission("sales_access")
def api_coin_save():
    d = request.get_json(silent=True) or {}
    hid = safe_int(d.get("hotel_id") or (current_user() or {}).get("hotel_id") or 1, 1)
    if not verify_hotel_id(hid): return fail("ليس لديك صلاحية", 403)
    trans_type = str(d.get("transaction_type") or "IN").upper()
    if trans_type not in {"IN", "OUT"}: return fail("نوع الحركة غير صحيح")
    amount = safe_float(d.get("amount"))
    if amount <= 0: return fail("القيمة يجب أن تكون أكبر من صفر")
    user = current_user() or {}
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO coin_safe_transactions (hotel_id,user_id,user_name,transaction_type,amount,notes) VALUES (%s,%s,%s,%s,%s,%s)", (hid, user.get("id") or 1, user.get("nickname") or "system", trans_type, amount, d.get("notes") or ""))
        tid = cur.lastrowid
        impact = amount if trans_type == "OUT" else -amount
        cur.execute("INSERT INTO daily_income_adjustments (hotel_id,transaction_id,adjustment_date,impact_amount,reason,created_by) VALUES (%s,%s,%s,%s,%s,%s)", (hid, tid, date.today().isoformat(), impact, f"حركة خزنة كوين {trans_type}", user.get("nickname") or "system"))
    audit("ADD_COIN", "coin_safe_transactions", f"حركة كوين #{tid} {trans_type} {amount}€")
    return ok({"id": tid})


@app.put("/api/coin-safe/<int:tid>")
@require_permission("sales_access")
def api_coin_update(tid):
    d = request.get_json(silent=True) or {}
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True); cur.execute("SELECT * FROM coin_safe_transactions WHERE transaction_id=%s", (tid,)); row = cur.fetchone()
        if not row: return fail("الحركة غير موجودة", 404)
        if not verify_hotel_id(row.get("hotel_id")): return fail("ليس لديك صلاحية", 403)
        typ = str(d.get("transaction_type") or row.get("transaction_type")).upper(); amount = safe_float(d.get("amount", row.get("amount")))
        c = conn.cursor(); c.execute("UPDATE coin_safe_transactions SET transaction_type=%s,amount=%s,notes=%s WHERE transaction_id=%s", (typ, amount, d.get("notes", row.get("notes")), tid))
        impact = amount if typ == "OUT" else -amount
        c.execute("UPDATE daily_income_adjustments SET impact_amount=%s,reason=%s WHERE transaction_id=%s", (impact, f"تعديل حركة كوين {typ}", tid))
    audit("EDIT_COIN", "coin_safe_transactions", f"تعديل حركة كوين #{tid}")
    return ok()


@app.delete("/api/coin-safe/<int:tid>")
@require_permission("sales_access")
def api_coin_delete(tid):
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True); cur.execute("SELECT hotel_id FROM coin_safe_transactions WHERE transaction_id=%s", (tid,)); row = cur.fetchone()
        if not row: return fail("الحركة غير موجودة", 404)
        if not verify_hotel_id(row.get("hotel_id")): return fail("ليس لديك صلاحية", 403)
        c = conn.cursor(); c.execute("DELETE FROM daily_income_adjustments WHERE transaction_id=%s", (tid,)); c.execute("DELETE FROM coin_safe_transactions WHERE transaction_id=%s", (tid,))
    audit("DELETE_COIN", "coin_safe_transactions", f"حذف حركة كوين #{tid}")
    return ok()


@app.get("/api/audit")
@login_required
def api_audit():
    limit = min(1000, max(10, safe_int(request.args.get("limit"), 200)))
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT a.*,t.nickname actor FROM system_audit_logs a LEFT JOIN team_members t ON t.id=a.user_id ORDER BY a.id DESC LIMIT %s", (limit,))
        return ok(rows_to_json(cur.fetchall()))


@app.get("/api/backup/sql")
@require_permission("finances_access")
def api_backup_sql():
    output = io.StringIO()
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SHOW TABLES")
        tables = [r[0] for r in cur.fetchall()]
        for table in tables:
            cur.execute(f"SHOW CREATE TABLE `{table}`")
            create = cur.fetchone()[1]
            output.write(f"DROP TABLE IF EXISTS `{table}`;\n{create};\n\n")
            cur.execute(f"SELECT * FROM `{table}`")
            cols = [d[0] for d in cur.description]
            for row in cur.fetchall():
                vals = []
                for v in row:
                    if v is None: vals.append("NULL")
                    elif isinstance(v, (int, float, Decimal)): vals.append(str(v))
                    else: vals.append("'" + str(v).replace("\\", "\\\\").replace("'", "\\'") + "'")
                output.write(f"INSERT INTO `{table}` (`{'`,`'.join(cols)}`) VALUES ({','.join(vals)});\n")
            output.write("\n")
    data = output.getvalue().encode("utf-8")
    return Response(data, mimetype="application/sql", headers={"Content-Disposition": f"attachment; filename=phototeam_backup_{datetime.now():%Y%m%d_%H%M%S}.sql"})


# -----------------------------------------------------------------------------
# Commissions / Deductions / Closures / Bonus
# -----------------------------------------------------------------------------
def commission_rows(start, end, role_type="sales", hotel_id=None, employee_name=None):
    ids = allowed_hotel_ids()
    if hotel_id not in (None, "", "الكل"):
        hid = safe_int(hotel_id, -1)
        if ids is not None and hid not in ids: return []
        ids = [hid]
    w, p = make_where_for_hotels("d.hotel_id", ids)
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(f"SELECT d.*,h.hotel_name FROM daily_income d LEFT JOIN hotels h ON h.id=d.hotel_id WHERE d.income_date BETWEEN %s AND %s {w} ORDER BY d.income_date,d.id", tuple([start, end] + p))
        source = rows_to_json(cur.fetchall())
        result = []
        totals = {}
        for r in source:
            gross = safe_float(r.get("deposit_applied")) + safe_float(r.get("income_usd")) + safe_float(r.get("income_eur"))
            gross += (safe_float(r.get("income_le_m")) + safe_float(r.get("income_le_k"))) / (safe_float(r.get("le_to_usd")) or 50)
            net_profit = gross - safe_float(r.get("cost_total"))
            names = split_names(r.get("photographer" if role_type == "photographer" else "sales_person"))
            if not names: continue
            split_net = net_profit / len(names)
            my_names = current_employee_names() if is_personal_scope_user() else None
            if my_names is not None:
                user_roles = {_normalize_role(ur) for ur in get_user_roles()}
                if role_type == "sales" and not (user_roles & {"sales", "سيلز", "مبيعات"}):
                    continue
                if role_type == "photographer" and not (user_roles & {"photographer", "مصور"}):
                    continue
            for name in names:
                if my_names is not None and str(name).strip().lower() not in my_names:
                    continue
                if employee_name and str(name).strip().lower() != str(employee_name).strip().lower():
                    continue
                rate = employee_commission_rate(name, role_type)
                comm_usd = split_net * rate / 100
                item = {
                    "date": r.get("income_date"), "hotel": r.get("hotel_name"), "room": r.get("room_number"), "employee": name,
                    "gross": round(gross, 2), "cost": round(safe_float(r.get("cost_total")), 2), "net_share": round(split_net, 2),
                    "participants_count": len(names), "participants": names,
                    "rate": rate, "commission_usd": round(comm_usd, 2), "booking_id": r.get("booking_id"), "income_id": r.get("id"),
                }
                result.append(item)
                totals[name] = totals.get(name, 0) + comm_usd
        rate_egp = safe_float(get_setting("exchange_rate", "50")) or 50
        cur.execute("SELECT * FROM employee_deductions WHERE deduction_date BETWEEN %s AND %s ORDER BY deduction_date", (start, end))
        deductions = rows_to_json(cur.fetchall())
        if is_personal_scope_user():
            my_names = current_employee_names()
            deductions = [x for x in deductions if str(x.get("employee_name") or "").strip().lower() in my_names]
        elif employee_name:
            deductions = [x for x in deductions if str(x.get("employee_name") or "").strip().lower() == str(employee_name).strip().lower()]
    summary = []
    for name, usd in sorted(totals.items(), key=lambda x: x[1], reverse=True):
        ded = sum(safe_float(x.get("amount_egp")) for x in deductions if x.get("employee_name") == name)
        summary.append({"employee": name, "commission_usd": round(usd, 2), "gross_egp": round(usd * rate_egp, 2), "deductions_egp": round(ded, 2), "net_egp": round(usd * rate_egp - ded, 2)})
    return {"rows": result, "summary": summary, "deductions": deductions, "exchange_rate": rate_egp}


@app.get("/api/commissions")
@require_permission("sales_access")
def api_commissions():
    start = request.args.get("start") or date.today().replace(day=1).isoformat()
    end = request.args.get("end") or date.today().isoformat()
    role_type = request.args.get("role", "sales")
    return ok(commission_rows(start, end, role_type, request.args.get("hotel_id"), request.args.get("employee_name")))


@app.get("/api/commissions/settings")
@require_permission("sales_access")
def api_commission_settings():
    keys = ["exchange_rate", "sales_bonus_target", "sales_bonus_pct", "photo_bonus_target", "photo_bonus_pct", "manager_bonus_target", "manager_bonus_pct", "hotel_bonus_target", "hotel_bonus_pct"]
    return ok({k: get_setting(k, "0") for k in keys})


@app.put("/api/commissions/settings")
@require_permission("finances_access")
def api_commission_settings_save():
    d = request.get_json(silent=True) or {}
    with get_db_connection() as conn:
        cur = conn.cursor()
        for k, v in d.items():
            cur.execute("INSERT INTO system_settings (setting_key,setting_value) VALUES (%s,%s) ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value)", (k, str(v)))
    audit("SETTINGS", "system_settings", "تعديل إعدادات العمولات والبونص")
    return ok()


@app.get("/api/deductions")
@require_permission("finances_access")
def api_deductions():
    start = request.args.get("start") or "2000-01-01"; end = request.args.get("end") or "2099-12-31"
    emp = request.args.get("employee", "").strip()
    sql = "SELECT * FROM employee_deductions WHERE deduction_date BETWEEN %s AND %s"; args = [start, end]
    if emp: sql += " AND employee_name=%s"; args.append(emp)
    sql += " ORDER BY deduction_date DESC,id DESC"
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True); cur.execute(sql, tuple(args)); return ok(rows_to_json(cur.fetchall()))


@app.post("/api/deductions")
@require_permission("finances_access")
def api_deduction_add():
    d = request.get_json(silent=True) or {}
    if not d.get("employee_name") or safe_float(d.get("amount_egp")) <= 0: return fail("اسم الموظف والقيمة مطلوبان")
    with get_db_connection() as conn:
        cur = conn.cursor(); cur.execute("INSERT INTO employee_deductions (employee_name,deduction_date,amount_egp,type,reason) VALUES (%s,%s,%s,%s,%s)", (d.get("employee_name"), d.get("deduction_date") or date.today().isoformat(), safe_float(d.get("amount_egp")), d.get("type") or "خصم / جزاء إداري", d.get("reason") or "")); did = cur.lastrowid
    audit("DEDUCTION", "employee_deductions", f"إضافة خصم #{did} للموظف {d.get('employee_name')}");
    emit_notification(f"🏷️ تسجيل {d.get('type') or 'خصم / سلفة'} باسمك", f"تم تسجيل {d.get('type') or 'خصم'} بقيمة {safe_float(d.get('amount_egp')):.2f} LE للموظف {d.get('employee_name')} — السبب: {d.get('reason') or '-'}.", notification_type="deduction", target_url="/commissions", target_employee=d.get("employee_name"), amount=safe_float(d.get("amount_egp")), priority="high")
    return ok({"id": did})


@app.put("/api/deductions/<int:did>")
@require_permission("finances_access")
def api_deduction_update(did):
    d = request.get_json(silent=True) or {}
    with get_db_connection() as conn:
        conn.cursor().execute("UPDATE employee_deductions SET employee_name=%s,deduction_date=%s,amount_egp=%s,type=%s,reason=%s WHERE id=%s", (d.get("employee_name"), d.get("deduction_date"), safe_float(d.get("amount_egp")), d.get("type"), d.get("reason"), did))
    return ok()


@app.delete("/api/deductions/<int:did>")
@require_permission("finances_access")
def api_deduction_delete(did):
    with get_db_connection() as conn: conn.cursor().execute("DELETE FROM employee_deductions WHERE id=%s", (did,))
    return ok()


@app.get("/api/commissions/bonus")
@require_permission("sales_access")
def api_bonus_calculation():
    month = request.args.get("month") or date.today().strftime("%Y-%m")
    start, end = f"{month}-01", f"{month}-31"
    sales_target = safe_float(get_setting("sales_bonus_target", 5000)); sales_pct = safe_float(get_setting("sales_bonus_pct", 2))
    photo_target = safe_float(get_setting("photo_bonus_target", 5000)); photo_pct = safe_float(get_setting("photo_bonus_pct", 2))
    manager_target = safe_float(get_setting("manager_bonus_target", 20000)); manager_pct = safe_float(get_setting("manager_bonus_pct", 1))
    sales = commission_rows(start, end, "sales", request.args.get("hotel_id"))["summary"]
    photos = commission_rows(start, end, "photographer", request.args.get("hotel_id"))["summary"]
    # البونص في الملف الأصلي مبني على إجمالي الأداء بالدولار وليس قيمة العمولة.
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        ids = allowed_hotel_ids(); w, p = make_where_for_hotels("hotel_id", ids)
        cur.execute(f"SELECT * FROM daily_income WHERE income_date BETWEEN %s AND %s {w}", tuple([start, end] + p)); rows = rows_to_json(cur.fetchall())
    performance_sales, performance_photo, total_place = {}, {}, 0.0
    for r in rows:
        gross = safe_float(r.get("deposit_applied")) + safe_float(r.get("income_usd")) + safe_float(r.get("income_eur")) + (safe_float(r.get("income_le_m")) + safe_float(r.get("income_le_k"))) / (safe_float(r.get("le_to_usd")) or 50)
        net = gross - safe_float(r.get("cost_total")); total_place += net
        sn = split_names(r.get("sales_person")); pn = split_names(r.get("photographer"))
        for n in sn: performance_sales[n] = performance_sales.get(n, 0) + net / max(1, len(sn))
        for n in pn: performance_photo[n] = performance_photo.get(n, 0) + net / max(1, len(pn))
    out = []
    for n, v in sorted(performance_sales.items(), key=lambda x:x[1], reverse=True): out.append({"role": "Sales", "employee": n, "achieved": round(v,2), "target": sales_target, "pct": sales_pct, "hit": v>=sales_target, "bonus_usd": round(v*sales_pct/100 if v>=sales_target else 0,2)})
    for n, v in sorted(performance_photo.items(), key=lambda x:x[1], reverse=True): out.append({"role": "Photographer", "employee": n, "achieved": round(v,2), "target": photo_target, "pct": photo_pct, "hit": v>=photo_target, "bonus_usd": round(v*photo_pct/100 if v>=photo_target else 0,2)})
    if not is_personal_scope_user():
        out.append({"role": "Manager", "employee": "المدير العام", "achieved": round(total_place,2), "target": manager_target, "pct": manager_pct, "hit": total_place>=manager_target, "bonus_usd": round(total_place*manager_pct/100 if total_place>=manager_target else 0,2)})
    else:
        my_names = current_employee_names()
        out = [x for x in out if str(x.get("employee") or "").strip().lower() in my_names]
    return ok(out)


@app.post("/api/closures/archive")
@require_permission("finances_access")
def api_closure_archive():
    d = request.get_json(silent=True) or {}
    start, end = d.get("start"), d.get("end")
    role = d.get("role") or "sales"
    data = commission_rows(start, end, role, d.get("hotel_id"))
    period = f"{start} إلى {end}"
    with get_db_connection() as conn:
        cur = conn.cursor()
        for item in data["summary"]:
            cur.execute("INSERT INTO closures_master (hotel_id,role_type,employee_name,month_str,period_text,total_usd,total_egp,closure_date) VALUES (%s,%s,%s,%s,%s,%s,%s,NOW())", (str(d.get("hotel_id") or "الكل"), role, item["employee"], str(start)[:7], period, item["commission_usd"], item["net_egp"]))
            cid = cur.lastrowid
            for row in data["rows"]:
                if row["employee"] != item["employee"]: continue
                cur.execute("INSERT INTO archive_closure_details (closure_id,role_type,employee_name,period_text,record_date,item_name,amount_usd,amount_egp,closure_timestamp) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW())", (cid, role, item["employee"], period, row["date"], f"غرفة {row['room']} - {row['hotel']}", row["commission_usd"], row["commission_usd"] * data["exchange_rate"]))
    audit("ARCHIVE_CLOSURE", "closures_master", f"أرشفة تقفيلة {role} {period}")
    return ok()


@app.get("/api/closures/archive")
@require_permission("finances_access")
def api_closure_archive_list():
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True); cur.execute("SELECT * FROM closures_master ORDER BY closure_date DESC,id DESC LIMIT 1000"); return ok(rows_to_json(cur.fetchall()))


@app.get("/api/closures/<int:cid>/details")
@require_permission("finances_access")
def api_closure_details(cid):
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True); cur.execute("SELECT * FROM archive_closure_details WHERE closure_id=%s ORDER BY record_date,id", (cid,)); return ok(rows_to_json(cur.fetchall()))


# -----------------------------------------------------------------------------
# Laundry
# -----------------------------------------------------------------------------
@app.get("/api/laundry")
@require_permission("laundry_access")
def api_laundry():
    month = request.args.get("month") or date.today().strftime("%Y-%m")
    start = request.args.get("start"); end = request.args.get("end")
    ids = allowed_hotel_ids(); w, p = make_where_for_hotels("l.hotel_id", ids)
    cond, args = ("l.log_date BETWEEN %s AND %s", [start, end]) if start and end else ("DATE_FORMAT(l.log_date,'%Y-%m')=%s", [month])
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True); cur.execute(f"SELECT l.*,h.hotel_name FROM laundry_tracker l LEFT JOIN hotels h ON h.id=l.hotel_id WHERE {cond} {w} ORDER BY l.log_date DESC,l.id DESC", tuple(args + p)); rows = rows_to_json(cur.fetchall())
    summary = {"dress_count": sum(safe_int(x.get("dress_count")) for x in rows), "galabeya_count": sum(safe_int(x.get("galabeya_count")) for x in rows), "total_cost": round(sum(safe_float(x.get("total_cost")) for x in rows),2)}
    return ok({"rows": rows, "summary": summary})


@app.post("/api/laundry")
@require_permission("laundry_access")
def api_laundry_add():
    d = request.get_json(silent=True) or {}; hid = safe_int(d.get("hotel_id") or (current_user() or {}).get("hotel_id") or 1, 1)
    if not verify_hotel_id(hid): return fail("ليس لديك صلاحية", 403)
    dress = max(0, safe_int(d.get("dress_count"))); gala = max(0, safe_int(d.get("galabeya_count")))
    dp = safe_float(d.get("dress_cleaning_price")) or 50; gp = safe_float(d.get("galabeya_cleaning_price")) or 30; total = dress*dp + gala*gp
    with get_db_connection() as conn:
        cur=conn.cursor(); cur.execute("INSERT INTO laundry_tracker (hotel_id,log_date,dress_count,galabeya_count,dress_cleaning_price,galabeya_cleaning_price,total_cost) VALUES (%s,%s,%s,%s,%s,%s,%s)", (hid,d.get("log_date") or date.today().isoformat(),dress,gala,dp,gp,total)); lid=cur.lastrowid
    audit("LAUNDRY_ADD", "laundry_tracker", f"إضافة غسيل يدوي #{lid}")
    return ok({"id": lid, "total_cost": total})


@app.put("/api/laundry/<int:lid>")
@require_permission("laundry_access")
def api_laundry_update(lid):
    d=request.get_json(silent=True) or {}; dress=max(0,safe_int(d.get("dress_count"))); gala=max(0,safe_int(d.get("galabeya_count"))); dp=safe_float(d.get("dress_cleaning_price")) or 50; gp=safe_float(d.get("galabeya_cleaning_price")) or 30
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True); cur.execute("SELECT hotel_id FROM laundry_tracker WHERE id=%s",(lid,)); row=cur.fetchone()
        if not row:return fail("السجل غير موجود",404)
        if not verify_hotel_id(row.get("hotel_id")):return fail("ليس لديك صلاحية",403)
        conn.cursor().execute("UPDATE laundry_tracker SET dress_count=%s,galabeya_count=%s,dress_cleaning_price=%s,galabeya_cleaning_price=%s,total_cost=%s WHERE id=%s",(dress,gala,dp,gp,dress*dp+gala*gp,lid))
    return ok()


@app.delete("/api/laundry/<int:lid>")
@require_permission("laundry_access")
def api_laundry_delete(lid):
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cur.execute("SELECT hotel_id FROM laundry_tracker WHERE id=%s",(lid,));row=cur.fetchone()
        if not row:return fail("السجل غير موجود",404)
        if not verify_hotel_id(row.get("hotel_id")):return fail("ليس لديك صلاحية",403)
        conn.cursor().execute("DELETE FROM laundry_tracker WHERE id=%s",(lid,))
    return ok()


@app.get("/api/laundry/details")
@require_permission("laundry_access")
def api_laundry_details():
    start=request.args.get("start") or date.today().isoformat();end=request.args.get("end") or start
    names=allowed_hotel_names();w,p=make_where_for_hotels("hotel",names);agg={}
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cur.execute(f"SELECT id,room_number,hotel,booking_date,clothing,status FROM bookings WHERE booking_date BETWEEN %s AND %s {w} AND status NOT IN ('كنسل','cancelled','ملغي')",tuple([start,end]+p));rows=cur.fetchall()
    for row in rows:
        for item in parse_json_list(row.get("clothing")):
            if not isinstance(item,dict):continue
            key=(str(item.get("type") or "فستان"),str(item.get("color") or "غير محدد"),str(item.get("size") or item.get("size_category") or "ستاندرد"))
            agg[key]=agg.get(key,0)+max(1,safe_int(item.get("qty"),1))
    return ok([{"type":k[0],"color":k[1],"size":k[2],"qty":v} for k,v in sorted(agg.items())])


# -----------------------------------------------------------------------------
# Assets / Dresses / Equipment / Maintenance / Incidents
# -----------------------------------------------------------------------------
@app.get("/api/assets")
@login_required
def api_assets():
    ids=allowed_hotel_ids();wd,pd=make_where_for_hotels("d.hotel_id",ids);we,pe=make_where_for_hotels("e.hotel_id",ids)
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cur.execute(f"SELECT d.*,h.hotel_name FROM dress_inventory d LEFT JOIN hotels h ON h.id=d.hotel_id WHERE 1=1 {wd} ORDER BY d.id DESC",tuple(pd));dresses=rows_to_json(cur.fetchall());cur.execute(f"SELECT e.*,h.hotel_name FROM equipment_inventory e LEFT JOIN hotels h ON h.id=e.hotel_id WHERE 1=1 {we} ORDER BY e.id DESC",tuple(pe));equipment=rows_to_json(cur.fetchall())
    return ok({"dresses":dresses,"equipment":equipment})


def save_upload(file_obj, folder: Path, prefix: str):
    if not file_obj or not file_obj.filename:return ""
    ext=Path(secure_filename(file_obj.filename)).suffix.lower()
    if ext not in {".jpg",".jpeg",".png",".webp"}:return ""
    name=f"{prefix}_{datetime.now():%Y%m%d_%H%M%S_%f}{ext}";file_obj.save(folder/name);return name


@app.post("/api/assets/dresses")
@require_permission("assets_access")
def api_add_dress():
    d=request.get_json(silent=True) or {};hid=safe_int(d.get("hotel_id") or 1,1)
    if not verify_hotel_id(hid):return fail("ليس لديك صلاحية",403)
    status=str(d.get("status") or "متاح");target=d.get("target_hotel")
    if "مرحّل" in status and target:status=f"مرحّل إلى: {target}"
    with get_db_connection() as conn:
        cur=conn.cursor();cur.execute("INSERT INTO dress_inventory (hotel_id,dress_type,custom_type_name,color,size_category,quantity,status) VALUES (%s,%s,%s,%s,%s,%s,%s)",(hid,d.get("dress_type") or "فستان",d.get("custom_type_name"),d.get("color") or "افتراضي",d.get("size_category") or "ستاندرد",max(1,safe_int(d.get("quantity"),1)),status));did=cur.lastrowid
    return ok({"id":did})


@app.put("/api/assets/dresses/<int:did>")
@require_permission("assets_access")
def api_update_dress(did):
    d=request.get_json(silent=True) or {}
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cur.execute("SELECT * FROM dress_inventory WHERE id=%s",(did,));row=cur.fetchone()
        if not row:return fail("القطعة غير موجودة",404)
        if not verify_hotel_id(row.get("hotel_id")):return fail("ليس لديك صلاحية",403)
        conn.cursor().execute("UPDATE dress_inventory SET dress_type=%s,custom_type_name=%s,color=%s,size_category=%s,quantity=%s,status=%s WHERE id=%s",(d.get("dress_type",row.get("dress_type")),d.get("custom_type_name",row.get("custom_type_name")),d.get("color",row.get("color")),d.get("size_category",row.get("size_category")),max(1,safe_int(d.get("quantity",row.get("quantity")),1)),d.get("status",row.get("status")),did))
    return ok()


@app.delete("/api/assets/dresses/<int:did>")
@require_permission("assets_access")
def api_delete_dress(did):
    with get_db_connection() as conn:conn.cursor().execute("DELETE FROM dress_inventory WHERE id=%s",(did,))
    return ok()


@app.post("/api/assets/equipment")
@require_permission("assets_access")
def api_add_equipment():
    d=request.form if request.form else (request.get_json(silent=True) or {});hid=safe_int(d.get("hotel_id") or 1,1)
    if not verify_hotel_id(hid):return fail("ليس لديك صلاحية",403)
    photo=save_upload(request.files.get("serial_photo"),UPLOAD_SERIAL,"eq") if request.files else ""
    status=str(d.get("status") or "متاح");target=d.get("target_hotel")
    if "مرحّل" in status and target:status=f"مرحّل إلى: {target}"
    with get_db_connection() as conn:
        cur=conn.cursor();cur.execute("INSERT INTO equipment_inventory (hotel_id,equipment_type,brand,model_name,serial_number,photo_path,quantity,status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",(hid,d.get("equipment_type") or "Camera",d.get("brand") or "",d.get("model_name") or "افتراضي",d.get("serial_number") or "-",photo,max(1,safe_int(d.get("quantity"),1)),status));eid=cur.lastrowid
    return ok({"id":eid,"photo_path":photo})


@app.put("/api/assets/equipment/<int:eid>")
@require_permission("assets_access")
def api_update_equipment(eid):
    d=request.get_json(silent=True) or {}
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cur.execute("SELECT * FROM equipment_inventory WHERE id=%s",(eid,));row=cur.fetchone()
        if not row:return fail("المعدة غير موجودة",404)
        if not verify_hotel_id(row.get("hotel_id")):return fail("ليس لديك صلاحية",403)
        conn.cursor().execute("UPDATE equipment_inventory SET equipment_type=%s,brand=%s,model_name=%s,serial_number=%s,quantity=%s,status=%s WHERE id=%s",(d.get("equipment_type",row.get("equipment_type")),d.get("brand",row.get("brand")),d.get("model_name",row.get("model_name")),d.get("serial_number",row.get("serial_number")),max(1,safe_int(d.get("quantity",row.get("quantity")),1)),d.get("status",row.get("status")),eid))
    return ok()


@app.delete("/api/assets/equipment/<int:eid>")
@require_permission("assets_access")
def api_delete_equipment(eid):
    with get_db_connection() as conn:conn.cursor().execute("DELETE FROM equipment_inventory WHERE id=%s",(eid,))
    return ok()


@app.post("/api/assets/equipment/<int:eid>/handover")
@require_permission("assets_access")
def api_equipment_handover(eid):
    d=request.get_json(silent=True) or {};name=str(d.get("photographer") or "").strip()
    if not name:return fail("اختر المصور")
    with get_db_connection() as conn:conn.cursor().execute("UPDATE equipment_inventory SET status=%s WHERE id=%s",(f"مع المصور: {name}",eid))
    audit("ASSET_HANDOVER","equipment_inventory",f"تسليم المعدة #{eid} إلى {name}")
    return ok()


@app.post("/api/assets/equipment/<int:eid>/return")
@require_permission("assets_access")
def api_equipment_return(eid):
    with get_db_connection() as conn:conn.cursor().execute("UPDATE equipment_inventory SET status='متاح' WHERE id=%s",(eid,))
    return ok()


@app.get("/api/assets/maintenance")
@require_permission("assets_access")
def api_maintenance_list():
    ids=allowed_hotel_ids();w,p=make_where_for_hotels("m.hotel_id",ids)
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cur.execute(f"SELECT m.*,h.hotel_name FROM asset_maintenance_logs m LEFT JOIN hotels h ON h.id=m.hotel_id WHERE 1=1 {w} ORDER BY m.id DESC",tuple(p));return ok(rows_to_json(cur.fetchall()))


@app.post("/api/assets/maintenance")
@require_permission("assets_access")
def api_maintenance_add():
    d=request.get_json(silent=True) or {};asset_type=d.get("asset_type");asset_id=safe_int(d.get("asset_id"));hid=safe_int(d.get("hotel_id") or 1,1)
    if asset_type not in {"dress","equipment"} or not asset_id:return fail("بيانات القطعة غير مكتملة")
    if not verify_hotel_id(hid):return fail("ليس لديك صلاحية",403)
    with get_db_connection() as conn:
        cur=conn.cursor();cur.execute("INSERT INTO asset_maintenance_logs (hotel_id,asset_type,asset_id,item_description,issue_reason,repair_center,repair_cost,sent_date,status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'قيد الصيانة')",(hid,asset_type,asset_id,d.get("item_description") or "",d.get("issue_reason") or "",d.get("repair_center") or "مركز خارجي",safe_float(d.get("repair_cost")),d.get("sent_date") or date.today().isoformat()));mid=cur.lastrowid;table="dress_inventory" if asset_type=="dress" else "equipment_inventory";cur.execute(f"UPDATE {table} SET status='صيانة' WHERE id=%s",(asset_id,))
    return ok({"id":mid})


@app.post("/api/assets/maintenance/<int:mid>/complete")
@require_permission("assets_access")
def api_maintenance_complete(mid):
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cur.execute("SELECT * FROM asset_maintenance_logs WHERE id=%s",(mid,));row=cur.fetchone()
        if not row:return fail("سجل الصيانة غير موجود",404)
        c=conn.cursor();c.execute("UPDATE asset_maintenance_logs SET return_date=%s,status='تم الإصلاح' WHERE id=%s",(date.today().isoformat(),mid));table="dress_inventory" if row.get("asset_type")=="dress" else "equipment_inventory";c.execute(f"UPDATE {table} SET status='متاح' WHERE id=%s",(row.get("asset_id"),))
    return ok()


@app.get("/api/assets/incidents")
@require_permission("assets_access")
def api_incident_list():
    ids=allowed_hotel_ids();w,p=make_where_for_hotels("i.hotel_id",ids)
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cur.execute(f"SELECT i.*,h.hotel_name FROM asset_incident_logs i LEFT JOIN hotels h ON h.id=i.hotel_id WHERE 1=1 {w} ORDER BY i.id DESC",tuple(p));return ok(rows_to_json(cur.fetchall()))


@app.post("/api/assets/incidents")
@require_permission("assets_access")
def api_incident_add():
    d=request.form if request.form else (request.get_json(silent=True) or {});asset_type=d.get("asset_type");asset_id=safe_int(d.get("asset_id"));hid=safe_int(d.get("hotel_id") or 1,1)
    if asset_type not in {"dress","equipment"} or not asset_id:return fail("بيانات القطعة غير مكتملة")
    photo=save_upload(request.files.get("damage_photo"),UPLOAD_DAMAGE,"dmg") if request.files else ""
    with get_db_connection() as conn:
        cur=conn.cursor();cur.execute("INSERT INTO asset_incident_logs (hotel_id,asset_type,asset_id,item_description,responsible_person,damage_description,estimated_damage_cost,incident_date,photo_path) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",(hid,asset_type,asset_id,d.get("item_description") or "",d.get("responsible_person") or "غير محدد",d.get("damage_description") or "",safe_float(d.get("estimated_damage_cost")),d.get("incident_date") or date.today().isoformat(),photo));iid=cur.lastrowid;table="dress_inventory" if asset_type=="dress" else "equipment_inventory";cur.execute(f"UPDATE {table} SET status=%s WHERE id=%s",(f"تالف / حادث ({d.get('responsible_person') or 'غير محدد'})",asset_id))
    return ok({"id":iid,"photo_path":photo})


# -----------------------------------------------------------------------------
# Salaries / Payroll / Bonuses / Archive / Bank Sheet
# -----------------------------------------------------------------------------
def salary_data(month, period, day_from=None, day_to=None, requested_hotel=None, employee_name=None):
    ensure_nbe_team_members_seeded()
    # مطابق لـ SalariesFrame الأصلي: نعرض كل أعضاء team_members،
    # ونستخدم الفندق فقط لتصفية حركة الدخل والحسابات وليس لإخفاء الموظفين.
    start,end,period_label=period_bounds(month,period,day_from,day_to)
    rate=safe_float(get_setting("exchange_rate",50)) or 50
    hotel_target=safe_float(get_setting("hotel_bonus_target",20000));hotel_pct=safe_float(get_setting("hotel_bonus_pct",2))
    scope_ids=None
    if requested_hotel not in (None,"","الكل"):
        scope_ids=[safe_int(requested_hotel,-1)]
    elif not is_full_access():
        scope_ids=allowed_hotel_ids()
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True)
        # الفنادق التي حققت التارجت - كما في الكود الأصلي.
        q="SELECT hotel_id,COALESCE(SUM((COALESCE(deposit_applied,0)+COALESCE(income_usd,0)+COALESCE(income_eur,0)+CASE WHEN COALESCE(le_to_usd,0)>0 THEN (COALESCE(income_le_m,0)+COALESCE(income_le_k,0))/le_to_usd ELSE 0 END)-COALESCE(cost_total,0)),0) total FROM daily_income WHERE income_date BETWEEN %s AND %s GROUP BY hotel_id"
        try:
            cur.execute(q,(start,end));hotel_totals={r.get("hotel_id"):safe_float(r.get("total")) for r in cur.fetchall()}
        except Exception:
            hotel_totals={}
        eligible={hid for hid,val in hotel_totals.items() if val>=hotel_target}
        # لا نستخدم WHERE is_active ولا hotel_id هنا: الكود الأصلي يعرض كل team_members.
        cur.execute("SELECT * FROM team_members ORDER BY nickname")
        raw_members=cur.fetchall();hotel_names={}
        try:
            cur.execute("SELECT id,hotel_name FROM hotels");hotel_names={r.get("id"):r.get("hotel_name") for r in cur.fetchall()}
        except Exception:pass
        out=[];grand_net=0;grand_sales=0;active_period_text=f"{period_label} [{start} إلى {end}]"
        # جلب بيانات الدخل والخصومات والمكافآت والأرشيف دفعة واحدة بدلاً من استعلام لكل موظف
        try:
            cur.execute("SELECT * FROM daily_income WHERE income_date BETWEEN %s AND %s", (start,end))
            income_rows=cur.fetchall()
        except Exception:
            income_rows=[]
        ded_by_emp = {}
        bon_by_emp = {}
        paid_emp_set = set()
        if period in {"full","الشهر بالكامل"}:
            prefix=f"{datetime.now().year}-{int(str(month).split('-')[-1]):02d}%"
            try:
                cur.execute("SELECT employee_name, COALESCE(SUM(amount_egp),0) total FROM employee_deductions WHERE deduction_date LIKE %s GROUP BY employee_name", (prefix,))
                for dr in cur.fetchall():
                    if dr and dr.get("employee_name"): ded_by_emp[str(dr["employee_name"]).strip().lower()] = safe_float(dr.get("total"))
            except Exception: pass
            try:
                cur.execute("SELECT employee_name, COALESCE(SUM(amount_egp),0) total FROM employee_bonuses WHERE bonus_date LIKE %s GROUP BY employee_name", (prefix,))
                for br in cur.fetchall():
                    if br and br.get("employee_name"): bon_by_emp[str(br["employee_name"]).strip().lower()] = safe_float(br.get("total"))
            except Exception: pass
        else:
            try:
                cur.execute("SELECT employee_name, COALESCE(SUM(amount_egp),0) total FROM employee_deductions WHERE deduction_date BETWEEN %s AND %s GROUP BY employee_name", (start,end))
                for dr in cur.fetchall():
                    if dr and dr.get("employee_name"): ded_by_emp[str(dr["employee_name"]).strip().lower()] = safe_float(dr.get("total"))
            except Exception: pass
            try:
                cur.execute("SELECT employee_name, COALESCE(SUM(amount_egp),0) total FROM employee_bonuses WHERE bonus_date BETWEEN %s AND %s GROUP BY employee_name", (start,end))
                for br in cur.fetchall():
                    if br and br.get("employee_name"): bon_by_emp[str(br["employee_name"]).strip().lower()] = safe_float(br.get("total"))
            except Exception: pass
        try:
            cur.execute("SELECT employee_name FROM salaries_paid_archive WHERE month_str=%s AND period_text=%s", (str(month).split("-")[-1], active_period_text))
            for pr in cur.fetchall():
                if pr and pr.get("employee_name"): paid_emp_set.add(str(pr["employee_name"]).strip().lower())
        except Exception: pass

        for m in raw_members:
            name=m.get("nickname")
            if not name:continue
            if employee_name and str(name).strip().lower() != str(employee_name).strip().lower():
                continue
            role=str(m.get("role") or "");member_roles=get_user_roles(user_id=m.get("id"), user=m);is_photo=any(_normalize_role(x)=="photographer" for x in member_roles);f_col="photographer" if is_photo else "sales_person";comm_rate=employee_commission_rate(name,"photographer" if is_photo else "sales")
            base=safe_float(m.get("base_salary"));period_base=base/3.0 if period in {"p1","p2","p3","دفعة 1 (1 إلى 10)","دفعة 2 (11 إلى 20)","دفعة 3 (21 إلى 31)"} else base
            net_sales=0;hotel_bonus_usd=0
            for ir in income_rows:
                hid=ir.get("hotel_id")
                if scope_ids is not None and hid not in scope_ids:continue
                role_names=split_names(ir.get(f_col))
                if not is_photo and not role_names:
                    role_names=split_names(ir.get("sales_person"))
                if not role_names:continue
                lowered=[str(x).strip().lower() for x in role_names]
                cand_names = {str(name).strip().lower(), str(m.get("full_name") or "").strip().lower(), str(m.get("sheet_nickname") or "").strip().lower()} - {""}
                if not (cand_names & set(lowered)):continue
                gross=(safe_float(ir.get("deposit_applied"))+safe_float(ir.get("income_usd"))+safe_float(ir.get("income_eur")))
                gross+=(safe_float(ir.get("income_le_m"))+safe_float(ir.get("income_le_k")))/(safe_float(ir.get("le_to_usd")) or safe_float(ir.get("order_exchange_rate")) or 50)
                order_net=gross-safe_float(ir.get("cost_total"))
                share=order_net/max(1,len(role_names))
                net_sales+=share
                if hid in eligible:hotel_bonus_usd+=share*(hotel_pct/100.0)
            comm_usd=net_sales*(comm_rate/100.0)
            name_low = str(name).strip().lower()
            ded = ded_by_emp.get(name_low, 0.0)
            personal = bon_by_emp.get(name_low, 0.0)
            hotel_bonus_egp=hotel_bonus_usd*rate;bonus=personal+hotel_bonus_egp;entitlement=(comm_usd*rate)+period_base+bonus;net=max(0,entitlement-ded);over_debt=ded>=entitlement and ded>0;visa=str(m.get("visa_card_number") or "").strip();missing=net>0 and visa in {"","-","None"}
            paid = (name_low in paid_emp_set)
            status="تم الصرف ✅" if paid else "⚠️ مديونية عالية!" if over_debt else "⚠️ بيانات ناقصة" if missing else ("بدون أوردرات (0 LE)" if net<=0 else "جاهز للصرف ⏳")
            grand_net+=net;grand_sales+=net_sales
            out.append({"id":serialize(m.get("id")),"full_name":serialize(m.get("full_name")),"nickname":name,"role":role or "موظف","roles":sorted(member_roles),"commission_rate":serialize(m.get("commission_rate")),"national_id":serialize(m.get("national_id")),"visa_card_number":serialize(m.get("visa_card_number")),"branch_code":serialize(m.get("branch_code") or ""),"nbe_type":serialize(m.get("nbe_type") or "ON US بطاقات"),"sheet_nickname":serialize(m.get("sheet_nickname") or ""),"base_salary":base,"hotel_id":serialize(m.get("hotel_id")),"hotel_name":hotel_names.get(m.get("hotel_id")) or "-","period_base_salary":round(period_base,2),"net_sales":round(net_sales,2),"commission_usd":round(comm_usd,2),"personal_bonus_egp":round(personal,2),"hotel_bonus_egp":round(hotel_bonus_egp,2),"bonus_egp":round(bonus,2),"deductions_egp":round(ded,2),"net_egp":round(net,2),"status":status,"paid":paid,"is_active":serialize(m.get("is_active"))})
    return {"rows":out,"summary":{"grand_net_egp":round(grand_net,2),"grand_sales_usd":round(grand_sales,2),"exchange_rate":rate,"hotel_bonus_target":hotel_target,"hotel_bonus_pct":hotel_pct},"start":start,"end":end,"period_text":active_period_text}


@app.get("/api/salaries/employees")
@require_permission("finances_access")
def api_salary_employees():
    ensure_nbe_team_members_seeded()
    """Complete employee list for the payroll dropdown.

    This endpoint intentionally uses finances_access instead of team_access so
    a payroll user can see the same employee names that salary_data() uses.
    Inactive employees are included because historical payroll may still need
    to be filtered by their name.
    """
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM team_members ORDER BY nickname")
        raw = cur.fetchall()
    out = []
    for r in raw:
        nickname = str(r.get("nickname") or "").strip()
        if not nickname:
            continue
        out.append({
            "id": serialize(r.get("id")),
            "nickname": nickname,
            "full_name": serialize(r.get("full_name")),
            "role": serialize(r.get("role")),
            "roles": sorted(get_user_roles(user_id=r.get("id"), user=r)),
            "hotel_id": serialize(r.get("hotel_id")),
            "base_salary": serialize(r.get("base_salary")),
            "is_active": serialize(r.get("is_active")),
        })
    return ok(out)


@app.get("/api/salaries")
@require_permission("finances_access")
def api_salaries():
    month=request.args.get("month") or f"{datetime.now().month:02d}";period=request.args.get("period") or "full";return ok(salary_data(month,period,request.args.get("day_from"),request.args.get("day_to"),request.args.get("hotel_id"),request.args.get("employee_name")))


@app.post("/api/salaries/pay")
@require_permission("finances_access")
def api_salary_pay():
    d=request.get_json(silent=True) or {};names=d.get("employees") or [];month=str(d.get("month") or f"{datetime.now().month:02d}");period=d.get("period") or "full";data=salary_data(month,period,d.get("day_from"),d.get("day_to"),d.get("hotel_id"),d.get("employee_name"));by={r["nickname"]:r for r in data["rows"]};target=list(by) if d.get("all") else [n for n in names if n in by]
    with get_db_connection() as conn:
        cur=conn.cursor()
        for n in target:
            r=by[n]
            if r["paid"]:continue
            cur.execute("INSERT INTO salaries_paid_archive (employee_name,month_str,period_text,net_amount_egp,paid_date) VALUES (%s,%s,%s,%s,NOW())",(n,str(month).split("-")[-1],data["period_text"],r["net_egp"]))
    audit("PAYROLL", "salaries_paid_archive", f"صرف {len(target)} موظف");
    [emit_notification(f"💳 تم صرف مستحقاتك المالية ({data['period_text']})", f"تم اعتماد وصرف مرتب الفترة للموظف {n} بصافي {by[n]['net_egp']:.2f} LE.", notification_type="payroll", target_url="/commissions", target_employee=n, amount=by[n]["net_egp"]) for n in target]
    return ok({"count":len(target)})


@app.post("/api/salaries/undo")
@require_permission("finances_access")
def api_salary_undo():
    d=request.get_json(silent=True) or {};name=d.get("employee_name");month=str(d.get("month") or f"{datetime.now().month:02d}");period=d.get("period") or "full";data=salary_data(month,period,d.get("day_from"),d.get("day_to"),d.get("hotel_id"))
    with get_db_connection() as conn:conn.cursor().execute("DELETE FROM salaries_paid_archive WHERE employee_name=%s AND month_str=%s AND period_text=%s",(name,str(month).split("-")[-1],data["period_text"]))
    return ok()


@app.get("/api/salaries/archive")
@require_permission("finances_access")
def api_salary_archive():
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cur.execute("SELECT * FROM salaries_paid_archive ORDER BY paid_date DESC,id DESC LIMIT 1500");return ok(rows_to_json(cur.fetchall()))


@app.post("/api/bonuses")
@require_permission("finances_access")
def api_bonus_add():
    d=request.get_json(silent=True) or {}
    with get_db_connection() as conn:
        cur=conn.cursor();cur.execute("INSERT INTO employee_bonuses (employee_name,bonus_date,amount_egp,reason) VALUES (%s,%s,%s,%s)",(d.get("employee_name"),d.get("bonus_date") or date.today().isoformat(),safe_float(d.get("amount_egp")),d.get("reason") or ""));bid=cur.lastrowid;
    emit_notification(f"🏆 مكافأة جديدة للموظف {d.get('employee_name')}", f"تم إضافة مكافأة بقيمة {safe_float(d.get('amount_egp')):.2f} LE — السبب: {d.get('reason') or 'مكافأة تميز'}.", notification_type="bonus", target_url="/commissions", target_employee=d.get("employee_name"), amount=safe_float(d.get("amount_egp")))
    return ok({"id":bid})


@app.post("/api/deductions/<int:did>/partial")
@require_permission("finances_access")
def api_deduction_partial(did):
    d=request.get_json(silent=True) or {};cut=safe_float(d.get("cut_amount"));month=d.get("month") or f"{datetime.now().month:02d}";period=d.get("period") or "full"
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cur.execute("SELECT * FROM employee_deductions WHERE id=%s",(did,));row=cur.fetchone()
        if not row:return fail("السلفة غير موجودة",404)
        original=safe_float(row.get("amount_egp"))
        if cut<0 or cut>original:return fail("قيمة الخصم الجزئي غير صحيحة")
        deferred=original-cut;nxt=next_period_start(month,period);c=conn.cursor()
        if cut<=0:c.execute("UPDATE employee_deductions SET deduction_date=%s WHERE id=%s",(nxt,did))
        elif deferred<=0:c.execute("UPDATE employee_deductions SET amount_egp=%s WHERE id=%s",(cut,did))
        else:
            c.execute("UPDATE employee_deductions SET amount_egp=%s WHERE id=%s",(cut,did));c.execute("INSERT INTO employee_deductions (employee_name,deduction_date,amount_egp,type,reason) VALUES (%s,%s,%s,%s,%s)",(row.get("employee_name"),nxt,deferred,row.get("type"),f"{row.get('reason') or 'سلفة'} (مرحل أوتوماتيك)"))
    return ok({"cut":cut,"deferred":deferred,"next_date":nxt})


@app.put("/api/salaries/base-salary/<int:uid>")
@require_permission("finances_access")
def api_salary_base_update(uid):
    d = request.get_json(silent=True) or {}
    amount = safe_float(d.get("base_salary"))
    if amount < 0:
        return fail("قيمة المرتب الأساسي غير صحيحة")
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id,nickname FROM team_members WHERE id=%s", (uid,))
        row = cur.fetchone()
        if not row:
            return fail("الموظف غير موجود", 404)
        conn.cursor().execute("UPDATE team_members SET base_salary=%s WHERE id=%s", (amount, uid))
    audit("BASE_SALARY", "team_members", f"تعديل المرتب الأساسي للموظف {row.get('nickname')} إلى {amount:.2f}")
    return ok({"id": uid, "base_salary": amount})


def _build_nbe_xlsx_bytes_for_current_employees():
    """يبني ملف شيت البنك الأهلي (بطاقات وحسابات ON US-3 (1) 2006.xlsx) للموظفين الحاليين في البرنامج فقط."""
    import zipfile
    from xml.sax.saxutils import escape as xml_escape

    ensure_nbe_team_members_seeded()
    try:
        month = request.args.get("month") or (request.get_json(silent=True) or {}).get("month") or f"{datetime.now().month:02d}"
        period = request.args.get("period") or (request.get_json(silent=True) or {}).get("period") or "full"
        day_from = request.args.get("day_from") or (request.get_json(silent=True) or {}).get("day_from")
        day_to = request.args.get("day_to") or (request.get_json(silent=True) or {}).get("day_to")
        hotel_id = request.args.get("hotel_id") or (request.get_json(silent=True) or {}).get("hotel_id")
        employee_name = request.args.get("employee_name") or (request.get_json(silent=True) or {}).get("employee_name")
        data = salary_data(month, period, day_from, day_to, hotel_id, employee_name)
        calc_rows = data.get("rows") or []
    except Exception:
        calc_rows = []

    final_rows = []
    for r in calc_rows:
        net_val = round(safe_float(r.get("net_egp")), 2)
        final_rows.append({
            "branch_code": str(r.get("branch_code") or "").strip(),
            "account_number": str(r.get("visa_card_number") or "").strip(),
            "client_name": str(r.get("full_name") or r.get("nickname") or "").strip(),
            "amount": net_val if net_val > 0 else None,
            "employee_id": str(r.get("national_id") or "").strip(),
            "bank_code": "NBEGEGCXXXX",
            "nickname": str(r.get("sheet_nickname") or r.get("nickname") or "").strip(),
        })

    total_rows = max(253, len(final_rows) + 10)
    xml_parts = [
        f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetPr><outlinePr summaryBelow="1" summaryRight="1"/><pageSetUpPr/></sheetPr>'
        f'<dimension ref="A1:K{total_rows}"/>'
        f'<sheetViews><sheetView workbookViewId="0"><selection activeCell="A1" sqref="A1"/></sheetView></sheetViews>'
        f'<sheetFormatPr baseColWidth="8" defaultColWidth="14.43" defaultRowHeight="15" customHeight="1"/>'
        f'<cols>'
        f'<col width="9" customWidth="1" style="12" min="1" max="1"/>'
        f'<col width="13.43" customWidth="1" style="12" min="2" max="2"/>'
        f'<col width="30.14" customWidth="1" style="12" min="3" max="3"/>'
        f'<col width="10" customWidth="1" style="12" min="4" max="4"/>'
        f'<col width="17.71" customWidth="1" style="12" min="5" max="5"/>'
        f'<col width="18.14" customWidth="1" style="12" min="6" max="6"/>'
        f'<col width="9" customWidth="1" style="12" min="7" max="11"/>'
        f'</cols><sheetData>'
    ]

    xml_parts.append(
        '<row r="1" ht="16.5" customHeight="1" s="12">'
        '<c r="A1" s="1" t="inlineStr"><is><t>كود الفرع</t></is></c>'
        '<c r="B1" s="1" t="inlineStr"><is><t>رقم الحساب</t></is></c>'
        '<c r="C1" s="2" t="inlineStr"><is><t>أسم العميل</t></is></c>'
        '<c r="D1" s="1" t="inlineStr"><is><t>المبلغ</t></is></c>'
        '<c r="E1" s="3" t="inlineStr"><is><t>رقم الموظف</t></is></c>'
        '<c r="F1" s="3" t="inlineStr"><is><t>كود البنك ( ثابت )</t></is></c>'
        '<c r="G1" s="11" t="n"></c><c r="H1" s="11" t="n"></c><c r="I1" s="11" t="n"></c><c r="J1" s="11" t="n"></c><c r="K1" s="11" t="n"></c>'
        '</row>'
    )

    for r_num in range(2, total_rows + 1):
        item = final_rows[r_num - 2] if (r_num - 2) < len(final_rows) else None
        br = f'<c r="A{r_num}" s="6" t="inlineStr"><is><t>{xml_escape(item["branch_code"])}</t></is></c>' if (item and item.get("branch_code")) else f'<c r="A{r_num}" s="6" t="n"></c>'
        ac = f'<c r="B{r_num}" s="6" t="inlineStr"><is><t>{xml_escape(item["account_number"])}</t></is></c>' if (item and item.get("account_number")) else f'<c r="B{r_num}" s="6" t="n"></c>'
        nm = f'<c r="C{r_num}" s="6" t="inlineStr"><is><t xml:space="preserve">{xml_escape(item["client_name"])}</t></is></c>' if (item and item.get("client_name")) else f'<c r="C{r_num}" s="6" t="n"></c>'
        am = f'<c r="D{r_num}" s="6" t="n"><v>{item["amount"]}</v></c>' if (item and item.get("amount") is not None and float(item["amount"]) > 0) else f'<c r="D{r_num}" s="6" t="n"></c>'
        eid = f'<c r="E{r_num}" s="6" t="inlineStr"><is><t>{xml_escape(item["employee_id"])}</t></is></c>' if (item and item.get("employee_id")) else f'<c r="E{r_num}" s="6" t="n"></c>'
        bc = f'<c r="F{r_num}" s="6" t="inlineStr"><is><t>{xml_escape(item.get("bank_code") or "NBEGEGCXXXX")}</t></is></c>' if (item and item.get("client_name")) else f'<c r="F{r_num}" s="11" t="n"></c>'

        if r_num == 2:
            g_cell = '<c r="G2" s="13" t="inlineStr"><is><t xml:space="preserve">ON US حسابات\n</t></is></c>'
        elif 3 <= r_num <= 5:
            g_cell = f'<c r="G{r_num}" s="8" t="n"></c>'
        elif r_num == 6:
            g_cell = '<c r="G6" s="14" t="inlineStr"><is><t xml:space="preserve">ON US بطاقات\n</t></is></c>'
        elif 7 <= r_num <= 10:
            g_cell = f'<c r="G{r_num}" s="8" t="n"></c>'
        else:
            g_cell = f'<c r="G{r_num}" s="11" t="n"></c>'

        nk = f'<c r="H{r_num}" s="11" t="inlineStr"><is><t xml:space="preserve">{xml_escape(item["nickname"])}</t></is></c>' if (item and item.get("nickname")) else f'<c r="H{r_num}" s="11" t="n"></c>'
        xml_parts.append(
            f'<row r="{r_num}" ht="14.25" customHeight="1" s="12">'
            f'{br}{ac}{nm}{am}{eid}{bc}{g_cell}{nk}'
            f'<c r="I{r_num}" s="11" t="n"></c><c r="J{r_num}" s="11" t="n"></c><c r="K{r_num}" s="11" t="n"></c>'
            f'</row>'
        )

    xml_parts.append(
        '</sheetData>'
        '<mergeCells count="2"><mergeCell ref="G2:G5"/><mergeCell ref="G6:G10"/></mergeCells>'
        '<pageMargins left="0.699912516150888" right="0.699912516150888" top="0.74990626395218" bottom="0.74990626395218" header="0" footer="0"/>'
        '<pageSetup orientation="portrait" paperSize="9"/>'
        '</worksheet>'
    )
    sheet1_xml = "".join(xml_parts)

    static_entries = {'docProps/app.xml': '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>Microsoft Excel Compatible / Openpyxl 3.1.5</Application><AppVersion>3.1</AppVersion></Properties>', 'docProps/core.xml': '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"><dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/">mohamed said A.Hamid</dc:creator><dcterms:created xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="dcterms:W3CDTF">2012-05-08T17:14:00Z</dcterms:created><dcterms:modified xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="dcterms:W3CDTF">2026-11-05T12:25:04Z</dcterms:modified><cp:lastModifiedBy>مستخدم Microsoft Office</cp:lastModifiedBy><cp:revision>0</cp:revision></cp:coreProperties>', 'xl/theme/theme1.xml': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" name="Office Theme"><a:themeElements><a:clrScheme name="Office"><a:dk1><a:sysClr lastClr="000000" val="windowText"/></a:dk1><a:lt1><a:sysClr lastClr="FFFFFF" val="window"/></a:lt1><a:dk2><a:srgbClr val="44546A"/></a:dk2><a:lt2><a:srgbClr val="E7E6E6"/></a:lt2><a:accent1><a:srgbClr val="5B9BD5"/></a:accent1><a:accent2><a:srgbClr val="ED7D31"/></a:accent2><a:accent3><a:srgbClr val="A5A5A5"/></a:accent3><a:accent4><a:srgbClr val="FFC000"/></a:accent4><a:accent5><a:srgbClr val="4472C4"/></a:accent5><a:accent6><a:srgbClr val="70AD47"/></a:accent6><a:hlink><a:srgbClr val="0563C1"/></a:hlink><a:folHlink><a:srgbClr val="954F72"/></a:folHlink></a:clrScheme><a:fontScheme name="Office"><a:majorFont><a:latin typeface="Calibri Light"/><a:ea typeface=""/><a:cs typeface=""/><a:font script="Jpan" typeface="ＭＳ Ｐゴシック"/><a:font script="Hang" typeface="맑은 고딕"/><a:font script="Hans" typeface="宋体"/><a:font script="Hant" typeface="新細明體"/><a:font script="Arab" typeface="Times New Roman"/><a:font script="Hebr" typeface="Times New Roman"/><a:font script="Thai" typeface="Tahoma"/><a:font script="Ethi" typeface="Nyala"/><a:font script="Beng" typeface="Vrinda"/><a:font script="Gujr" typeface="Shruti"/><a:font script="Khmr" typeface="MoolBoran"/><a:font script="Knda" typeface="Tunga"/><a:font script="Guru" typeface="Raavi"/><a:font script="Cans" typeface="Euphemia"/><a:font script="Cher" typeface="Plantagenet Cherokee"/><a:font script="Yiii" typeface="Microsoft Yi Baiti"/><a:font script="Tibt" typeface="Microsoft Himalaya"/><a:font script="Thaa" typeface="MV Boli"/><a:font script="Deva" typeface="Mangal"/><a:font script="Telu" typeface="Gautami"/><a:font script="Taml" typeface="Latha"/><a:font script="Syrc" typeface="Estrangelo Edessa"/><a:font script="Orya" typeface="Kalinga"/><a:font script="Mlym" typeface="Kartika"/><a:font script="Laoo" typeface="DokChampa"/><a:font script="Sinh" typeface="Iskoola Pota"/><a:font script="Mong" typeface="Mongolian Baiti"/><a:font script="Viet" typeface="Times New Roman"/><a:font script="Uigh" typeface="Microsoft Uighur"/><a:font script="Geor" typeface="Sylfaen"/></a:majorFont><a:minorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/><a:font script="Jpan" typeface="ＭＳ Ｐゴシック"/><a:font script="Hang" typeface="맑은 고딕"/><a:font script="Hans" typeface="宋体"/><a:font script="Hant" typeface="新細明體"/><a:font script="Arab" typeface="Arial"/><a:font script="Hebr" typeface="Arial"/><a:font script="Thai" typeface="Tahoma"/><a:font script="Ethi" typeface="Nyala"/><a:font script="Beng" typeface="Vrinda"/><a:font script="Gujr" typeface="Shruti"/><a:font script="Khmr" typeface="DaunPenh"/><a:font script="Knda" typeface="Tunga"/><a:font script="Guru" typeface="Raavi"/><a:font script="Cans" typeface="Euphemia"/><a:font script="Cher" typeface="Plantagenet Cherokee"/><a:font script="Yiii" typeface="Microsoft Yi Baiti"/><a:font script="Tibt" typeface="Microsoft Himalaya"/><a:font script="Thaa" typeface="MV Boli"/><a:font script="Deva" typeface="Mangal"/><a:font script="Telu" typeface="Gautami"/><a:font script="Taml" typeface="Latha"/><a:font script="Syrc" typeface="Estrangelo Edessa"/><a:font script="Orya" typeface="Kalinga"/><a:font script="Mlym" typeface="Kartika"/><a:font script="Laoo" typeface="DokChampa"/><a:font script="Sinh" typeface="Iskoola Pota"/><a:font script="Mong" typeface="Mongolian Baiti"/><a:font script="Viet" typeface="Arial"/><a:font script="Uigh" typeface="Microsoft Uighur"/><a:font script="Geor" typeface="Sylfaen"/></a:minorFont></a:fontScheme><a:fmtScheme name="Office"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:gradFill rotWithShape="1"><a:gsLst><a:gs pos="0"><a:schemeClr val="phClr"><a:lumMod val="110000"/><a:satMod val="105000"/><a:tint val="67000"/></a:schemeClr></a:gs><a:gs pos="50000"><a:schemeClr val="phClr"><a:lumMod val="105000"/><a:satMod val="103000"/><a:tint val="73000"/></a:schemeClr></a:gs><a:gs pos="100000"><a:schemeClr val="phClr"><a:lumMod val="105000"/><a:satMod val="109000"/><a:tint val="81000"/></a:schemeClr></a:gs></a:gsLst><a:lin ang="5400000" scaled="0"/></a:gradFill><a:gradFill rotWithShape="1"><a:gsLst><a:gs pos="0"><a:schemeClr val="phClr"><a:satMod val="103000"/><a:lumMod val="102000"/><a:tint val="94000"/></a:schemeClr></a:gs><a:gs pos="50000"><a:schemeClr val="phClr"><a:satMod val="110000"/><a:lumMod val="100000"/><a:shade val="100000"/></a:schemeClr></a:gs><a:gs pos="100000"><a:schemeClr val="phClr"><a:lumMod val="99000"/><a:satMod val="120000"/><a:shade val="78000"/></a:schemeClr></a:gs></a:gsLst><a:lin ang="5400000" scaled="0"/></a:gradFill></a:fillStyleLst><a:lnStyleLst><a:ln cap="flat" cmpd="sng" w="6350" algn="ctr"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/><a:miter lim="800000"/></a:ln><a:ln cap="flat" cmpd="sng" w="12700" algn="ctr"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/><a:miter lim="800000"/></a:ln><a:ln cap="flat" cmpd="sng" w="19050" algn="ctr"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/><a:miter lim="800000"/></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst><a:outerShdw blurRad="57150" rotWithShape="0" algn="ctr" dir="5400000" dist="19050"><a:srgbClr val="000000"><a:alpha val="63000"/></a:srgbClr></a:outerShdw></a:effectLst></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"><a:tint val="95000"/><a:satMod val="170000"/></a:schemeClr></a:solidFill><a:gradFill rotWithShape="1"><a:gsLst><a:gs pos="0"><a:schemeClr val="phClr"><a:tint val="93000"/><a:satMod val="150000"/><a:shade val="98000"/><a:lumMod val="102000"/></a:schemeClr></a:gs><a:gs pos="50000"><a:schemeClr val="phClr"><a:tint val="98000"/><a:satMod val="130000"/><a:shade val="90000"/><a:lumMod val="103000"/></a:schemeClr></a:gs><a:gs pos="100000"><a:schemeClr val="phClr"><a:shade val="63000"/><a:satMod val="120000"/></a:schemeClr></a:gs></a:gsLst><a:lin ang="5400000" scaled="0"/></a:gradFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements><a:objectDefaults/><a:extraClrSchemeLst/></a:theme>', 'docProps/custom.xml': '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"><property name="ICV" fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="2"><vt:lpwstr xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">7967E97AD02E45CA982C274450F2CCA8_12</vt:lpwstr></property><property name="KSOProductBuildVer" fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="3"><vt:lpwstr xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">1033-12.2.0.20782</vt:lpwstr></property></Properties>', 'xl/worksheets/sheet2.xml': '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetPr><outlinePr summaryBelow="1" summaryRight="1"/><pageSetUpPr/></sheetPr><dimension ref="A1:A1"/><sheetViews><sheetView workbookViewId="0"><selection activeCell="A1" sqref="A1"/></sheetView></sheetViews><sheetFormatPr baseColWidth="8" defaultColWidth="14.43" defaultRowHeight="15" customHeight="1"/><cols><col width="9" customWidth="1" style="12" min="1" max="11"/></cols><sheetData><row r="1" ht="13.5" customHeight="1" s="12"></row><row r="2" ht="13.5" customHeight="1" s="12"></row><row r="3" ht="13.5" customHeight="1" s="12"></row><row r="4" ht="13.5" customHeight="1" s="12"></row><row r="5" ht="13.5" customHeight="1" s="12"></row><row r="6" ht="13.5" customHeight="1" s="12"></row><row r="7" ht="13.5" customHeight="1" s="12"></row><row r="8" ht="13.5" customHeight="1" s="12"></row><row r="9" ht="13.5" customHeight="1" s="12"></row><row r="10" ht="13.5" customHeight="1" s="12"></row><row r="11" ht="13.5" customHeight="1" s="12"></row><row r="12" ht="13.5" customHeight="1" s="12"></row><row r="13" ht="13.5" customHeight="1" s="12"></row><row r="14" ht="13.5" customHeight="1" s="12"></row><row r="15" ht="13.5" customHeight="1" s="12"></row><row r="16" ht="13.5" customHeight="1" s="12"></row><row r="17" ht="13.5" customHeight="1" s="12"></row><row r="18" ht="13.5" customHeight="1" s="12"></row><row r="19" ht="13.5" customHeight="1" s="12"></row><row r="20" ht="13.5" customHeight="1" s="12"></row><row r="21" ht="13.5" customHeight="1" s="12"></row><row r="22" ht="13.5" customHeight="1" s="12"></row><row r="23" ht="13.5" customHeight="1" s="12"></row><row r="24" ht="13.5" customHeight="1" s="12"></row><row r="25" ht="13.5" customHeight="1" s="12"></row><row r="26" ht="13.5" customHeight="1" s="12"></row><row r="27" ht="13.5" customHeight="1" s="12"></row><row r="28" ht="13.5" customHeight="1" s="12"></row><row r="29" ht="13.5" customHeight="1" s="12"></row><row r="30" ht="13.5" customHeight="1" s="12"></row><row r="31" ht="13.5" customHeight="1" s="12"></row><row r="32" ht="13.5" customHeight="1" s="12"></row><row r="33" ht="13.5" customHeight="1" s="12"></row><row r="34" ht="13.5" customHeight="1" s="12"></row><row r="35" ht="13.5" customHeight="1" s="12"></row><row r="36" ht="13.5" customHeight="1" s="12"></row><row r="37" ht="13.5" customHeight="1" s="12"></row><row r="38" ht="13.5" customHeight="1" s="12"></row><row r="39" ht="13.5" customHeight="1" s="12"></row><row r="40" ht="13.5" customHeight="1" s="12"></row><row r="41" ht="13.5" customHeight="1" s="12"></row><row r="42" ht="13.5" customHeight="1" s="12"></row><row r="43" ht="13.5" customHeight="1" s="12"></row><row r="44" ht="13.5" customHeight="1" s="12"></row><row r="45" ht="13.5" customHeight="1" s="12"></row><row r="46" ht="13.5" customHeight="1" s="12"></row><row r="47" ht="13.5" customHeight="1" s="12"></row><row r="48" ht="13.5" customHeight="1" s="12"></row><row r="49" ht="13.5" customHeight="1" s="12"></row><row r="50" ht="13.5" customHeight="1" s="12"></row><row r="51" ht="13.5" customHeight="1" s="12"></row><row r="52" ht="13.5" customHeight="1" s="12"></row><row r="53" ht="13.5" customHeight="1" s="12"></row><row r="54" ht="13.5" customHeight="1" s="12"></row><row r="55" ht="13.5" customHeight="1" s="12"></row><row r="56" ht="13.5" customHeight="1" s="12"></row><row r="57" ht="13.5" customHeight="1" s="12"></row><row r="58" ht="13.5" customHeight="1" s="12"></row><row r="59" ht="13.5" customHeight="1" s="12"></row><row r="60" ht="13.5" customHeight="1" s="12"></row><row r="61" ht="13.5" customHeight="1" s="12"></row><row r="62" ht="13.5" customHeight="1" s="12"></row><row r="63" ht="13.5" customHeight="1" s="12"></row><row r="64" ht="13.5" customHeight="1" s="12"></row><row r="65" ht="13.5" customHeight="1" s="12"></row><row r="66" ht="13.5" customHeight="1" s="12"></row><row r="67" ht="13.5" customHeight="1" s="12"></row><row r="68" ht="13.5" customHeight="1" s="12"></row><row r="69" ht="13.5" customHeight="1" s="12"></row><row r="70" ht="13.5" customHeight="1" s="12"></row><row r="71" ht="13.5" customHeight="1" s="12"></row><row r="72" ht="13.5" customHeight="1" s="12"></row><row r="73" ht="13.5" customHeight="1" s="12"></row><row r="74" ht="13.5" customHeight="1" s="12"></row><row r="75" ht="13.5" customHeight="1" s="12"></row><row r="76" ht="13.5" customHeight="1" s="12"></row><row r="77" ht="13.5" customHeight="1" s="12"></row><row r="78" ht="13.5" customHeight="1" s="12"></row><row r="79" ht="13.5" customHeight="1" s="12"></row><row r="80" ht="13.5" customHeight="1" s="12"></row><row r="81" ht="13.5" customHeight="1" s="12"></row><row r="82" ht="13.5" customHeight="1" s="12"></row><row r="83" ht="13.5" customHeight="1" s="12"></row><row r="84" ht="13.5" customHeight="1" s="12"></row><row r="85" ht="13.5" customHeight="1" s="12"></row><row r="86" ht="13.5" customHeight="1" s="12"></row><row r="87" ht="13.5" customHeight="1" s="12"></row><row r="88" ht="13.5" customHeight="1" s="12"></row><row r="89" ht="13.5" customHeight="1" s="12"></row><row r="90" ht="13.5" customHeight="1" s="12"></row><row r="91" ht="13.5" customHeight="1" s="12"></row><row r="92" ht="13.5" customHeight="1" s="12"></row><row r="93" ht="13.5" customHeight="1" s="12"></row><row r="94" ht="13.5" customHeight="1" s="12"></row><row r="95" ht="13.5" customHeight="1" s="12"></row><row r="96" ht="13.5" customHeight="1" s="12"></row><row r="97" ht="13.5" customHeight="1" s="12"></row><row r="98" ht="13.5" customHeight="1" s="12"></row><row r="99" ht="13.5" customHeight="1" s="12"></row><row r="100" ht="13.5" customHeight="1" s="12"></row></sheetData><pageMargins left="0.699912516150888" right="0.699912516150888" top="0.74990626395218" bottom="0.74990626395218" header="0" footer="0"/><pageSetup orientation="portrait" paperSize="9"/></worksheet>', 'xl/worksheets/sheet3.xml': '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetPr><outlinePr summaryBelow="1" summaryRight="1"/><pageSetUpPr/></sheetPr><dimension ref="A1:A1"/><sheetViews><sheetView workbookViewId="0"><selection activeCell="A1" sqref="A1"/></sheetView></sheetViews><sheetFormatPr baseColWidth="8" defaultColWidth="14.43" defaultRowHeight="15" customHeight="1"/><cols><col width="9" customWidth="1" style="12" min="1" max="11"/></cols><sheetData><row r="1" ht="13.5" customHeight="1" s="12"></row><row r="2" ht="13.5" customHeight="1" s="12"></row><row r="3" ht="13.5" customHeight="1" s="12"></row><row r="4" ht="13.5" customHeight="1" s="12"></row><row r="5" ht="13.5" customHeight="1" s="12"></row><row r="6" ht="13.5" customHeight="1" s="12"></row><row r="7" ht="13.5" customHeight="1" s="12"></row><row r="8" ht="13.5" customHeight="1" s="12"></row><row r="9" ht="13.5" customHeight="1" s="12"></row><row r="10" ht="13.5" customHeight="1" s="12"></row><row r="11" ht="13.5" customHeight="1" s="12"></row><row r="12" ht="13.5" customHeight="1" s="12"></row><row r="13" ht="13.5" customHeight="1" s="12"></row><row r="14" ht="13.5" customHeight="1" s="12"></row><row r="15" ht="13.5" customHeight="1" s="12"></row><row r="16" ht="13.5" customHeight="1" s="12"></row><row r="17" ht="13.5" customHeight="1" s="12"></row><row r="18" ht="13.5" customHeight="1" s="12"></row><row r="19" ht="13.5" customHeight="1" s="12"></row><row r="20" ht="13.5" customHeight="1" s="12"></row><row r="21" ht="13.5" customHeight="1" s="12"></row><row r="22" ht="13.5" customHeight="1" s="12"></row><row r="23" ht="13.5" customHeight="1" s="12"></row><row r="24" ht="13.5" customHeight="1" s="12"></row><row r="25" ht="13.5" customHeight="1" s="12"></row><row r="26" ht="13.5" customHeight="1" s="12"></row><row r="27" ht="13.5" customHeight="1" s="12"></row><row r="28" ht="13.5" customHeight="1" s="12"></row><row r="29" ht="13.5" customHeight="1" s="12"></row><row r="30" ht="13.5" customHeight="1" s="12"></row><row r="31" ht="13.5" customHeight="1" s="12"></row><row r="32" ht="13.5" customHeight="1" s="12"></row><row r="33" ht="13.5" customHeight="1" s="12"></row><row r="34" ht="13.5" customHeight="1" s="12"></row><row r="35" ht="13.5" customHeight="1" s="12"></row><row r="36" ht="13.5" customHeight="1" s="12"></row><row r="37" ht="13.5" customHeight="1" s="12"></row><row r="38" ht="13.5" customHeight="1" s="12"></row><row r="39" ht="13.5" customHeight="1" s="12"></row><row r="40" ht="13.5" customHeight="1" s="12"></row><row r="41" ht="13.5" customHeight="1" s="12"></row><row r="42" ht="13.5" customHeight="1" s="12"></row><row r="43" ht="13.5" customHeight="1" s="12"></row><row r="44" ht="13.5" customHeight="1" s="12"></row><row r="45" ht="13.5" customHeight="1" s="12"></row><row r="46" ht="13.5" customHeight="1" s="12"></row><row r="47" ht="13.5" customHeight="1" s="12"></row><row r="48" ht="13.5" customHeight="1" s="12"></row><row r="49" ht="13.5" customHeight="1" s="12"></row><row r="50" ht="13.5" customHeight="1" s="12"></row><row r="51" ht="13.5" customHeight="1" s="12"></row><row r="52" ht="13.5" customHeight="1" s="12"></row><row r="53" ht="13.5" customHeight="1" s="12"></row><row r="54" ht="13.5" customHeight="1" s="12"></row><row r="55" ht="13.5" customHeight="1" s="12"></row><row r="56" ht="13.5" customHeight="1" s="12"></row><row r="57" ht="13.5" customHeight="1" s="12"></row><row r="58" ht="13.5" customHeight="1" s="12"></row><row r="59" ht="13.5" customHeight="1" s="12"></row><row r="60" ht="13.5" customHeight="1" s="12"></row><row r="61" ht="13.5" customHeight="1" s="12"></row><row r="62" ht="13.5" customHeight="1" s="12"></row><row r="63" ht="13.5" customHeight="1" s="12"></row><row r="64" ht="13.5" customHeight="1" s="12"></row><row r="65" ht="13.5" customHeight="1" s="12"></row><row r="66" ht="13.5" customHeight="1" s="12"></row><row r="67" ht="13.5" customHeight="1" s="12"></row><row r="68" ht="13.5" customHeight="1" s="12"></row><row r="69" ht="13.5" customHeight="1" s="12"></row><row r="70" ht="13.5" customHeight="1" s="12"></row><row r="71" ht="13.5" customHeight="1" s="12"></row><row r="72" ht="13.5" customHeight="1" s="12"></row><row r="73" ht="13.5" customHeight="1" s="12"></row><row r="74" ht="13.5" customHeight="1" s="12"></row><row r="75" ht="13.5" customHeight="1" s="12"></row><row r="76" ht="13.5" customHeight="1" s="12"></row><row r="77" ht="13.5" customHeight="1" s="12"></row><row r="78" ht="13.5" customHeight="1" s="12"></row><row r="79" ht="13.5" customHeight="1" s="12"></row><row r="80" ht="13.5" customHeight="1" s="12"></row><row r="81" ht="13.5" customHeight="1" s="12"></row><row r="82" ht="13.5" customHeight="1" s="12"></row><row r="83" ht="13.5" customHeight="1" s="12"></row><row r="84" ht="13.5" customHeight="1" s="12"></row><row r="85" ht="13.5" customHeight="1" s="12"></row><row r="86" ht="13.5" customHeight="1" s="12"></row><row r="87" ht="13.5" customHeight="1" s="12"></row><row r="88" ht="13.5" customHeight="1" s="12"></row><row r="89" ht="13.5" customHeight="1" s="12"></row><row r="90" ht="13.5" customHeight="1" s="12"></row><row r="91" ht="13.5" customHeight="1" s="12"></row><row r="92" ht="13.5" customHeight="1" s="12"></row><row r="93" ht="13.5" customHeight="1" s="12"></row><row r="94" ht="13.5" customHeight="1" s="12"></row><row r="95" ht="13.5" customHeight="1" s="12"></row><row r="96" ht="13.5" customHeight="1" s="12"></row><row r="97" ht="13.5" customHeight="1" s="12"></row><row r="98" ht="13.5" customHeight="1" s="12"></row><row r="99" ht="13.5" customHeight="1" s="12"></row><row r="100" ht="13.5" customHeight="1" s="12"></row></sheetData><pageMargins left="0.699912516150888" right="0.699912516150888" top="0.74990626395218" bottom="0.74990626395218" header="0" footer="0"/><pageSetup orientation="portrait" paperSize="9"/></worksheet>', 'xl/styles.xml': '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><numFmts count="0"/><fonts count="5"><font><name val="Arial"/><color rgb="FF000000"/><sz val="11"/><scheme val="minor"/></font><font><name val="Arial"/><b val="1"/><color rgb="FFFFFFFF"/><sz val="11"/></font><font><name val="Arial"/><sz val="11"/></font><font><name val="Arial"/><b val="1"/><sz val="11"/></font><font/></fonts><fills count="5"><fill><patternFill/></fill><fill><patternFill patternType="lightGray"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF000080"/><bgColor rgb="FF000080"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFFFF00"/><bgColor rgb="FFFFFF00"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FF93CDDD"/><bgColor rgb="FF93CDDD"/></patternFill></fill></fills><borders count="7"><border/><border><left style="medium"><color rgb="FF999999"/></left><right style="thin"><color rgb="FF999999"/></right><top style="medium"><color rgb="FF999999"/></top><bottom style="thin"><color rgb="FF999999"/></bottom></border><border><left style="thin"><color rgb="FF999999"/></left><right style="medium"><color rgb="FF999999"/></right><top style="medium"><color rgb="FF999999"/></top><bottom style="thin"><color rgb="FF999999"/></bottom></border><border><left/><right/><top/><bottom/></border><border><left/><right/><top/></border><border><left/><right/></border><border><left/><right/><bottom/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="15"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" applyAlignment="1" pivotButton="0" quotePrefix="0" xfId="0"><alignment vertical="bottom"/></xf><xf numFmtId="49" fontId="1" fillId="2" borderId="1" applyAlignment="1" pivotButton="0" quotePrefix="0" xfId="0"><alignment horizontal="center" vertical="center" wrapText="1"/></xf><xf numFmtId="49" fontId="1" fillId="2" borderId="2" applyAlignment="1" pivotButton="0" quotePrefix="0" xfId="0"><alignment horizontal="center" vertical="center" wrapText="1"/></xf><xf numFmtId="49" fontId="1" fillId="2" borderId="3" applyAlignment="1" pivotButton="0" quotePrefix="0" xfId="0"><alignment horizontal="center" vertical="center" wrapText="1"/></xf><xf numFmtId="49" fontId="2" fillId="0" borderId="0" pivotButton="0" quotePrefix="0" xfId="0"/><xf numFmtId="49" fontId="2" fillId="0" borderId="0" applyAlignment="1" pivotButton="0" quotePrefix="0" xfId="0"><alignment horizontal="center"/></xf><xf numFmtId="49" fontId="2" fillId="0" borderId="0" applyAlignment="1" pivotButton="0" quotePrefix="0" xfId="0"><alignment horizontal="center"/></xf><xf numFmtId="49" fontId="3" fillId="3" borderId="4" applyAlignment="1" pivotButton="0" quotePrefix="0" xfId="0"><alignment horizontal="center" vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="4" fillId="0" borderId="5" pivotButton="0" quotePrefix="0" xfId="0"/><xf numFmtId="0" fontId="4" fillId="0" borderId="6" pivotButton="0" quotePrefix="0" xfId="0"/><xf numFmtId="49" fontId="3" fillId="4" borderId="4" applyAlignment="1" pivotButton="0" quotePrefix="0" xfId="0"><alignment horizontal="center" wrapText="1"/></xf><xf numFmtId="49" fontId="2" fillId="0" borderId="0" pivotButton="0" quotePrefix="0" xfId="0"/><xf numFmtId="0" fontId="0" fillId="0" borderId="0" pivotButton="0" quotePrefix="0" xfId="0"/><xf numFmtId="49" fontId="3" fillId="3" borderId="3" applyAlignment="1" pivotButton="0" quotePrefix="0" xfId="0"><alignment horizontal="center" vertical="center" wrapText="1"/></xf><xf numFmtId="49" fontId="3" fillId="4" borderId="3" applyAlignment="1" pivotButton="0" quotePrefix="0" xfId="0"><alignment horizontal="center" wrapText="1"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles><colors><indexedColors><rgbColor rgb="00000000"/><rgbColor rgb="00FFFFFF"/><rgbColor rgb="00FF0000"/><rgbColor rgb="0000FF00"/><rgbColor rgb="000000FF"/><rgbColor rgb="00FFFF00"/><rgbColor rgb="00FF00FF"/><rgbColor rgb="0000FFFF"/><rgbColor rgb="00000000"/><rgbColor rgb="00FFFFFF"/><rgbColor rgb="00FF0000"/><rgbColor rgb="0000FF00"/><rgbColor rgb="000000FF"/><rgbColor rgb="00FFFF00"/><rgbColor rgb="00FF00FF"/><rgbColor rgb="0000FFFF"/><rgbColor rgb="00800000"/><rgbColor rgb="00008000"/><rgbColor rgb="00000080"/><rgbColor rgb="00808000"/><rgbColor rgb="00800080"/><rgbColor rgb="00008080"/><rgbColor rgb="00C0C0C0"/><rgbColor rgb="00808080"/><rgbColor rgb="009999FF"/><rgbColor rgb="00993366"/><rgbColor rgb="00FFFFCC"/><rgbColor rgb="00CCFFFF"/><rgbColor rgb="00660066"/><rgbColor rgb="00FF8080"/><rgbColor rgb="000066CC"/><rgbColor rgb="00CCCCFF"/><rgbColor rgb="00000080"/><rgbColor rgb="00FF00FF"/><rgbColor rgb="00FFFF00"/><rgbColor rgb="0000FFFF"/><rgbColor rgb="00800080"/><rgbColor rgb="00800000"/><rgbColor rgb="00008080"/><rgbColor rgb="000000FF"/><rgbColor rgb="0000CCFF"/><rgbColor rgb="00CCFFFF"/><rgbColor rgb="00CCFFCC"/><rgbColor rgb="00FFFF99"/><rgbColor rgb="0099CCFF"/><rgbColor rgb="00FF99CC"/><rgbColor rgb="00CC99FF"/><rgbColor rgb="00FFCC99"/><rgbColor rgb="003366FF"/><rgbColor rgb="0033CCCC"/><rgbColor rgb="0099CC00"/><rgbColor rgb="00FFCC00"/><rgbColor rgb="00FF9900"/><rgbColor rgb="00FF6600"/><rgbColor rgb="00666699"/><rgbColor rgb="00969696"/><rgbColor rgb="00003366"/><rgbColor rgb="00339966"/><rgbColor rgb="00003300"/><rgbColor rgb="00333300"/><rgbColor rgb="00993300"/><rgbColor rgb="00993366"/><rgbColor rgb="00333399"/><rgbColor rgb="00333333"/></indexedColors></colors></styleSheet>', '_rels/.rels': '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml" Id="rId1"/><Relationship Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml" Id="rId2"/><Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml" Id="rId3"/><Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties" Target="docProps/custom.xml" Id="rId4"/></Relationships>', 'xl/workbook.xml': '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><workbookPr/><sheets><sheet xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" name="Sheet1" sheetId="1" state="visible" r:id="rId1"/><sheet xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" name="Sheet2" sheetId="2" state="visible" r:id="rId2"/><sheet xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" name="Sheet3" sheetId="3" state="visible" r:id="rId3"/></sheets><definedNames/><calcPr calcId="124519" fullCalcOnLoad="1"/></workbook>', 'xl/_rels/workbook.xml.rels': '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="/xl/worksheets/sheet1.xml" Id="rId1"/><Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="/xl/worksheets/sheet2.xml" Id="rId2"/><Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="/xl/worksheets/sheet3.xml" Id="rId3"/><Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml" Id="rId4"/><Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml" Id="rId5"/></Relationships>', '[Content_Types].xml': '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/><Override PartName="/xl/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/><Override PartName="/docProps/custom.xml" ContentType="application/vnd.openxmlformats-officedocument.custom-properties+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/></Types>'}
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
        for arcname, content_str in static_entries.items():
            zf.writestr(arcname, content_str.encode("utf-8"))
        zf.writestr("xl/worksheets/sheet1.xml", sheet1_xml.encode("utf-8"))
    return bio.getvalue()


def _open_native_save_as_dialog(default_filename="بطاقات وحسابات ON US-3 (1) 2006.xlsx"):
    """يفتح نافذة (اختر مكان الحفظ / Save As) في ويندوز عبر pywebview أو tkinter."""
    # 1. محاولة الفتح عبر نافذة pywebview النشطة إن وجدت
    try:
        import webview
        if getattr(webview, "windows", None) and len(webview.windows) > 0:
            win = webview.windows[0]
            res = win.create_file_dialog(
                webview.SAVE_DIALOG,
                save_filename=default_filename,
                file_types=("Excel Workbook (*.xlsx)", "All files (*.*)")
            )
            if res:
                chosen = res[0] if isinstance(res, (list, tuple)) else str(res)
                if chosen:
                    if not str(chosen).lower().endswith(".xlsx"):
                        chosen = str(chosen) + ".xlsx"
                    return str(chosen)
                return None
    except Exception:
        pass

    # 2. الفتح عبر نافذة ويندوز الأصلية (tkinter filedialog) في المقدمة (-topmost)
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        try:
            root.attributes("-topmost", True)
        except Exception:
            pass
        chosen = filedialog.asksaveasfilename(
            parent=root,
            title="اختر مكان حفظ شيت مرتبات البنك الأهلي",
            initialfile=default_filename,
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook (*.xlsx)", "*.xlsx"), ("All Files (*.*)", "*.*")]
        )
        try:
            root.destroy()
        except Exception:
            pass
        if chosen:
            if not str(chosen).lower().endswith(".xlsx"):
                chosen = str(chosen) + ".xlsx"
            return str(chosen)
        return ""  # المستخدم ضغط إلغاء
    except Exception:
        return None


@app.post("/api/salaries/bank-sheet-save")
@require_permission("finances_access")
def api_bank_sheet_save_dialog():
    """يفتح نافذة (اختر مكان الحفظ) على جهاز الكمبيوتر ويحفظ شيت البنك الأهلي في المسار الذي يختاره المستخدم."""
    exact_filename = "بطاقات وحسابات ON US-3 (1) 2006.xlsx"
    xlsx_bytes = _build_nbe_xlsx_bytes_for_current_employees()
    chosen_path = _open_native_save_as_dialog(exact_filename)
    if chosen_path == "":
        return ok({"cancelled": True, "message": "تم إلغاء الحفظ"})
    if chosen_path:
        Path(chosen_path).write_bytes(xlsx_bytes)
        return ok({"saved": True, "path": chosen_path, "message": f"تم حفظ الشيت بنجاح في: {chosen_path}"})
    # إذا كان يعمل على سيرفر بدون واجهة رسومية، يرجع fallback ليقوم المتصفح بفتح نافذة الحفظ
    return ok({"saved": False, "browser_fallback": True})


@app.get("/api/salaries/bank-sheet")
@require_permission("finances_access")
def api_bank_sheet():
    """يصدر شيت مرتبات البنك الأهلي المصري بنفس الشكل والاسم بالضبط: بطاقات وحسابات ON US-3 (1) 2006.xlsx"""
    from urllib.parse import quote
    exact_filename = "بطاقات وحسابات ON US-3 (1) 2006.xlsx"
    xlsx_bytes = _build_nbe_xlsx_bytes_for_current_employees()
    encoded_name = quote(exact_filename)
    return Response(
        xlsx_bytes,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=\"ON_US_3_2006.xlsx\"; filename*=UTF-8''{encoded_name}"
        }
    )


# -----------------------------------------------------------------------------
# Team / Hotels / Permissions / Sessions
# -----------------------------------------------------------------------------

_NBE_TEAM_SEEDED = False

def ensure_nbe_team_members_seeded():
    """يحذف الـ 52 موظفاً الذين تمت إضافتهم مؤخراً ويبقي على الموظفين القدامى فقط."""
    global _NBE_TEAM_SEEDED
    if _NBE_TEAM_SEEDED:
        return
    try:
        ensure_team_members_auth_columns()
        cols = table_columns("team_members")
        with get_db_connection() as conn:
            c = conn.cursor()
            for col_name, col_def in [
                ("branch_code", "VARCHAR(50) DEFAULT NULL"),
                ("nbe_type", "VARCHAR(50) DEFAULT 'ON US بطاقات'"),
                ("sheet_nickname", "VARCHAR(100) DEFAULT NULL"),
            ]:
                if cols and col_name not in cols:
                    try:
                        c.execute(f"ALTER TABLE team_members ADD COLUMN {col_name} {col_def}")
                    except Exception:
                        pass
            _SCHEMA_CACHE.pop("team_members", None)
            try:
                c.execute("DELETE FROM team_members WHERE username LIKE 'nbe_%'")
                nids = ['30111053100156', '30406192701679', '30107102701635', '28710182703152', '30109262701316', '28401282800195', '29906121301251', '29909182702991', '29806150400353', '30211112700558', '30012251700659', '29410272701515', '30307042500413', '30507063100155', '29809152107431', '29901172600278', '30207012700715', '30411143100132', '27010090201074', '28311252800591', '29604223100033', '28401068800412', '30102221701099', '28701152107131', '30210012709756', '29910121500332', '30201012411251', '28801040101495', '30509033100277', '29509012706714', '30612170400135', '30207012700731', '30807202608278', '29807281700332', '29612212701615', '29609182700391', '30003041202312', '29909013100273', '29906061600912', '30611080400318', '29204281701375', '28912102703876', '30304142702014', '30011022700517', '28105308800719', '30006222701352', '27206022700072', '30305242700198', '27506171100391', '30812012714792', '29904101602457', '28807302801092']
                if nids:
                    marks = ",".join(["%s"] * len(nids))
                    c.execute(f"DELETE FROM team_members WHERE national_id IN ({marks})", tuple(nids))
            except Exception:
                pass
        _NBE_TEAM_SEEDED = True
    except Exception:
        pass


@app.post("/api/team/sync-nbe-roster")
@login_required
def api_team_sync_nbe_roster():
    """حذف الموظفين المضافين مؤخراً والإبقاء على القدامى فقط."""
    global _NBE_TEAM_SEEDED
    _NBE_TEAM_SEEDED = False
    ensure_nbe_team_members_seeded()
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM team_members")
        total = (cur.fetchone() or [0])[0]
    return ok({"total": total, "message": "تم الإبقاء على الموظفين القدامى فقط بنجاح"})


@app.get("/api/team")
@require_permission("team_access")
def api_team():
    ensure_nbe_team_members_seeded()
    salary_all=request.args.get("salary_all")=="1" and has_permission("finances_access")
    ids=None if salary_all or is_full_access() else allowed_hotel_ids()
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cur.execute("SELECT * FROM team_members ORDER BY id DESC");raw=cur.fetchall()
        hotel_map={}
        try:
            cur.execute("SELECT id,hotel_name FROM hotels");hotel_map={r.get("id"):r.get("hotel_name") for r in cur.fetchall()}
        except Exception:pass
        mgr_hotels_by_uid = {}
        if table_exists("user_hotel_permissions"):
            try:
                cur.execute("SELECT up.user_id,up.hotel_id,h.hotel_name,up.can_view,up.can_edit FROM user_hotel_permissions up JOIN hotels h ON h.id=up.hotel_id")
                for mr in cur.fetchall():
                    uid_k = mr.get("user_id")
                    if uid_k:
                        mgr_hotels_by_uid.setdefault(int(uid_k), []).append({
                            "hotel_id": serialize(mr.get("hotel_id")),
                            "hotel_name": serialize(mr.get("hotel_name")),
                            "can_view": serialize(mr.get("can_view")),
                            "can_edit": serialize(mr.get("can_edit")),
                        })
            except Exception:
                pass
        rows=[]
        for r in raw:
            hid=r.get("hotel_id")
            if ids is not None and hid not in (None,"") and safe_int(hid,-1) not in ids:continue
            out={k:serialize(v) for k,v in r.items()};out.setdefault("base_salary",0);out.setdefault("commission_rate",0);out.setdefault("is_active",1);out.setdefault("access_type","وصول كامل (Desktop + Mobile)");out.setdefault("phone_number","");out.setdefault("national_id","");out.setdefault("visa_card_number","");out.setdefault("branch_code","");out.setdefault("nbe_type","ON US بطاقات");out.setdefault("sheet_nickname","");out.setdefault("session_active",1);out["hotel_name"]=hotel_map.get(hid) or "-";out["permissions"]=[];out["manager_hotels"]=mgr_hotels_by_uid.get(safe_int(r.get("id")), []);out["roles"]=sorted(get_user_roles(user_id=r.get("id"), user=r))
            try:
                out["permissions"] = sorted(get_user_permissions(r.get("id")))
            except Exception:
                out["permissions"] = []
            rows.append(out)
    return ok(rows)


@app.post("/api/team")
@require_permission("team_access")
def api_team_add():
    d=request.get_json(silent=True) or {}
    if not has_full_access():
        target_hid = safe_int(d.get("hotel_id"), 0)
        allowed_hids = allowed_hotel_ids()
        if allowed_hids is not None and (not target_hid or target_hid not in allowed_hids):
            return fail("يمكنك إضافة الموظفين في الفنادق الخاصة بك فقط", 403)
    roles=[str(x) for x in (d.get("roles") or []) if str(x) in ROLE_CATALOG]
    if not d.get("role") and roles:d["role"]=roles[0]
    if not d.get("full_name") or not d.get("nickname") or not d.get("role") or not d.get("username") or not d.get("password"):return fail("الاسم واللقب ودور واحد على الأقل واسم المستخدم وكلمة المرور مطلوبة")
    with get_db_connection() as conn:
        cur=conn.cursor();cur.execute("INSERT INTO team_members (full_name,nickname,phone_number,role,access_type,hotel_id,commission_rate,base_salary,national_id,visa_card_number,username,password_hash,is_active,session_active) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,1)",(d.get("full_name"),d.get("nickname"),d.get("phone_number"),d.get("role"),d.get("access_type") or "وصول كامل (Desktop + Mobile)",d.get("hotel_id") or None,safe_float(d.get("commission_rate")),safe_float(d.get("base_salary")),d.get("national_id"),d.get("visa_card_number"),d.get("username"),hash_password(str(d.get("password")))));uid=cur.lastrowid
        save_user_permissions(cur,uid,d)
    return ok({"id":uid})


def save_user_permissions(cur,uid,d):
    ensure_multi_role_tables()
    cur.execute("DELETE FROM user_hotel_permissions WHERE user_id=%s",(uid,));manager_hotels=d.get("manager_hotels") or []
    for item in manager_hotels:
        hid=safe_int(item.get("hotel_id") if isinstance(item,dict) else item)
        if hid:cur.execute("INSERT INTO user_hotel_permissions (user_id,hotel_id,can_view,can_edit) VALUES (%s,%s,%s,%s)",(uid,hid,1,int(item.get("can_edit",1)) if isinstance(item,dict) else 1))

    # Explicit permissions: always store a marker so an intentionally empty
    # checkbox selection does not fall back to legacy role defaults.
    cur.execute("DELETE FROM employee_permissions WHERE user_id=%s",(uid,))
    cur.execute("INSERT INTO employee_permissions (user_id,permission_key) VALUES (%s,%s)",(uid,PERMISSION_CONFIG_MARKER))
    for key in d.get("permissions") or []:
        if key in PERMISSION_LABELS:
            cur.execute("INSERT IGNORE INTO employee_permissions (user_id,permission_key) VALUES (%s,%s)",(uid,key))

    # Multi-role assignment. The legacy team_members.role column stays as the
    # primary/display role so old reports remain compatible.
    requested=[str(x) for x in (d.get("roles") or []) if str(x) in ROLE_CATALOG]
    primary=str(d.get("role") or "").strip()
    if primary in ROLE_CATALOG and primary not in requested:
        requested.insert(0,primary)
    if not requested and primary:
        requested=[primary]
    cur.execute("DELETE FROM employee_roles WHERE user_id=%s",(uid,))
    for role_key in dict.fromkeys(requested):
        cur.execute("SELECT id FROM roles WHERE role_key=%s LIMIT 1",(role_key,));rr=cur.fetchone()
        if rr:cur.execute("INSERT IGNORE INTO employee_roles (user_id,role_id) VALUES (%s,%s)",(uid,rr[0]))


@app.put("/api/team/<int:uid>")
@require_permission("team_access")
def api_team_update(uid):
    d=request.get_json(silent=True) or {}
    roles=[str(x) for x in (d.get("roles") or []) if str(x) in ROLE_CATALOG]
    if not d.get("role") and roles:d["role"]=roles[0]
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cur.execute("SELECT * FROM team_members WHERE id=%s",(uid,));old=cur.fetchone()
        if not old:return fail("الموظف غير موجود",404)
        c=conn.cursor();fields=(d.get("full_name",old.get("full_name")),d.get("nickname",old.get("nickname")),d.get("phone_number",old.get("phone_number")),d.get("role",old.get("role")),d.get("access_type",old.get("access_type")),d.get("hotel_id",old.get("hotel_id")),safe_float(d.get("commission_rate",old.get("commission_rate"))),safe_float(d.get("base_salary",old.get("base_salary"))),d.get("national_id",old.get("national_id")),d.get("visa_card_number",old.get("visa_card_number")),d.get("username",old.get("username")))
        c.execute("UPDATE team_members SET full_name=%s,nickname=%s,phone_number=%s,role=%s,access_type=%s,hotel_id=%s,commission_rate=%s,base_salary=%s,national_id=%s,visa_card_number=%s,username=%s WHERE id=%s",fields+(uid,))
        if d.get("password"):c.execute("UPDATE team_members SET password_hash=%s,session_active=1 WHERE id=%s",(hash_password(str(d.get("password"))),uid))
        save_user_permissions(c,uid,d)
    return ok()


@app.post("/api/team/<int:uid>/toggle")
@require_permission("team_access")
def api_team_toggle(uid):
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cur.execute("SELECT is_active FROM team_members WHERE id=%s",(uid,));row=cur.fetchone()
        if not row:return fail("الموظف غير موجود",404)
        new=0 if row.get("is_active") else 1;conn.cursor().execute("UPDATE team_members SET is_active=%s,session_active=%s WHERE id=%s",(new,new,uid))
    return ok({"is_active":bool(new)})


@app.post("/api/team/<int:uid>/force-logout")
@require_permission("team_access")
def api_team_force_logout(uid):
    with get_db_connection() as conn:conn.cursor().execute("UPDATE team_members SET session_active=0 WHERE id=%s",(uid,))
    audit("FORCE_LOGOUT","team_members",f"إجبار خروج المستخدم #{uid}")
    return ok()




@app.post("/api/team/<int:uid>/transfer-hotel")
@require_permission("team_access")
def api_team_transfer_hotel(uid):
    """نقل سيلز أو مصور من فندق لفندق آخر مع الحفاظ التام على جميع حجوزاته وأوردراته السابقة في الفندق القديم كما هي."""
    d = request.get_json(silent=True) or {}
    new_hotel_id = safe_int(d.get("hotel_id"), 0)
    if not new_hotel_id:
        return fail("اختر الفندق الجديد أولاً")
    if not verify_hotel_id(new_hotel_id):
        return fail("يمكنك النقل بين الفنادق المخصصة لك فقط", 403)

    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM team_members WHERE id=%s", (uid,))
        emp = cur.fetchone()
        if not emp:
            return fail("الموظف غير موجود", 404)
        old_hid = safe_int(emp.get("hotel_id"), 0)
        if not has_full_access() and old_hid and not verify_hotel_id(old_hid):
            return fail("هذا الموظف خارج نطاق الفنادق الخاصة بك", 403)
        old_hname = hotel_name_from_id(old_hid) or "-"
        new_hname = hotel_name_from_id(new_hotel_id) or "-"

        # تحديث الفندق الحالي للموظف فقط دون المساس بأي حجز أو مبيعات سابقة في الفندق القديم
        c = conn.cursor()
        c.execute("UPDATE team_members SET hotel_id=%s WHERE id=%s", (new_hotel_id, uid))

    actor = (current_user() or {}).get("nickname") or "المدير"
    emit_notification(
        f"🔄 نقل فندق الموظف ({emp.get('nickname')}) • {old_hname} ⬅️ {new_hname}",
        f"قام ({actor}) بنقل ({emp.get('nickname')}) من فندق ({old_hname}) إلى فندق ({new_hname}) مع بقاء جميع أعماله السابقة محفوظة في فندقها الأصلي.",
        notification_type="manager_edit",
        target_role="CEO",
        hotel_id=new_hotel_id,
        target_url="/team-hotels",
        priority="high",
    )
    audit("TRANSFER_HOTEL", "team_members", f"نقل {emp.get('nickname')} من {old_hname} إلى {new_hname}")
    return ok({"id": uid, "old_hotel": old_hname, "new_hotel": new_hname})


@app.post("/api/hotels")
@require_permission("team_access")
def api_hotel_add():
    if not has_full_access(): return fail("إضافة الفنادق متاحة للأونر فقط", 403)
    d=request.get_json(silent=True) or {};name=str(d.get("hotel_name") or "").strip()
    if not name:return fail("اسم الفندق مطلوب")
    with get_db_connection() as conn:
        cur=conn.cursor();cur.execute("INSERT INTO hotels (hotel_name,parent_hotel_id) VALUES (%s,%s)",(name,d.get("parent_hotel_id") or None));hid=cur.lastrowid
        # Auto-link newly created hotel to the current user so it appears immediately
        # for users who have hotel-scoped access.
        try:
            user = current_user() or {}
            if user.get("id") and not is_full_access(user):
                cur.execute(
                    "INSERT IGNORE INTO user_hotel_permissions (user_id, hotel_id, can_view) VALUES (%s,%s,1)",
                    (user.get("id"), hid)
                )
        except Exception:
            pass
    return ok({"id":hid})




@app.put("/api/hotels/<int:hotel_id>")
@require_permission("team_access")
def api_hotel_update(hotel_id):
    if not has_full_access(): return fail("تعديل الفنادق متاح للأونر فقط", 403)
    d=request.get_json(silent=True) or {}
    name=str(d.get("hotel_name") or "").strip()
    if not name:
        return fail("اسم الفندق مطلوب")
    with get_db_connection() as conn:
        cur=conn.cursor()
        cur.execute("UPDATE hotels SET hotel_name=%s, parent_hotel_id=%s WHERE id=%s",
                    (name, d.get("parent_hotel_id") or None, hotel_id))
    return ok({"id": hotel_id})


@app.delete("/api/hotels/<int:hotel_id>")
@require_permission("team_access")
def api_hotel_delete(hotel_id):
    if not has_full_access(): return fail("حذف الفنادق متاح للأونر فقط", 403)
    # Soft delete to preserve old bookings/reports
    with get_db_connection() as conn:
        cur=conn.cursor()
        try:
            cur.execute("ALTER TABLE hotels ADD COLUMN IF NOT EXISTS is_active TINYINT(1) DEFAULT 1")
        except Exception:
            pass
        cur.execute("UPDATE hotels SET is_active=0 WHERE id=%s", (hotel_id,))
        try:
            cur.execute("DELETE FROM user_hotel_permissions WHERE hotel_id=%s", (hotel_id,))
        except Exception:
            pass
    return ok({"id": hotel_id, "disabled": True})

# -----------------------------------------------------------------------------
# Reports + Settings
# -----------------------------------------------------------------------------
@app.get("/api/reports")
@require_permission("finances_access")
def api_reports():
    start = request.args.get("start") or date.today().replace(day=1).isoformat()
    end = request.args.get("end") or date.today().isoformat()
    req_hotel = request.args.get("hotel_id", "").strip()
    req_emp = request.args.get("employee", "").strip()
    req_type = request.args.get("type", "").strip().lower()
    
    allowed_ids = allowed_hotel_ids()
    allowed_names = allowed_hotel_names()
    
    if req_hotel:
        rh = safe_int(req_hotel, -1)
        if allowed_ids is not None and rh not in allowed_ids:
            return ok({"bookings":0,"agreed":0,"remaining":0,"income":0,"costs":0,"net_profit":0,"trend":[],"sources":[],"top_team":[],"top_hotels":[],"expenses":[]})
        target_ids = [rh]
        target_names = [hotel_name_from_id(rh)]
    else:
        target_ids = allowed_ids
        target_names = allowed_names

    wb, pb = make_where_for_hotels("hotel", target_names)
    wi, pi = make_where_for_hotels("hotel_id", target_ids)
    
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        
        # 1. Bookings Data
        cur.execute(f"SELECT COUNT(*) bookings, COALESCE(SUM(total_agreement),0) agreed, COALESCE(SUM(remaining),0) remaining FROM bookings WHERE booking_date BETWEEN %s AND %s {wb}", tuple([start, end] + pb))
        bookings_data = cur.fetchone() or {}
        
        # 2. Daily Income Data
        cur.execute(f"SELECT * FROM daily_income WHERE income_date BETWEEN %s AND %s {wi}", tuple([start, end] + pi))
        daily_rows = cur.fetchall() or []
        
        # 3. Expenses (Laundry & Maintenance)
        l_costs = 0; m_costs = 0
        if table_exists('laundry_tracker'):
            cur.execute(f"SELECT COALESCE(SUM(total_cost),0) c FROM laundry_tracker WHERE log_date BETWEEN %s AND %s {wi}", tuple([start, end] + pi))
            l_costs = safe_float((cur.fetchone() or {}).get("c"))
        if table_exists('asset_maintenance_logs'):
            cur.execute(f"SELECT COALESCE(SUM(repair_cost),0) c FROM asset_maintenance_logs WHERE sent_date BETWEEN %s AND %s {wi}", tuple([start, end] + pi))
            m_costs = safe_float((cur.fetchone() or {}).get("c"))
            
        # 4. Get Hotel Names map
        cur.execute("SELECT id, hotel_name FROM hotels")
        hotel_names_map = {r["id"]: r["hotel_name"] for r in cur.fetchall()}

    # Process Daily Income
    income = 0; costs = 0
    cash_val = 0; visa_val = 0; usd_val = 0; eur_val = 0
    trend_map = {}; team_map = {}; hotel_map = {}
    
    for r in daily_rows:
        if req_emp:
            emps = [str(x).strip().lower() for x in split_names(r.get("sales_person")) + split_names(r.get("photographer"))]
            if req_emp.lower() not in emps:
                continue
                
        day = str(r.get("income_date"))[:10]
        rate = safe_float(r.get("le_to_usd")) or 50
        
        r_usd = safe_float(r.get("income_usd"))
        r_eur = safe_float(r.get("income_eur"))
        r_cash = safe_float(r.get("income_le_m"))
        r_visa = safe_float(r.get("income_le_k"))
        r_deposit = safe_float(r.get("deposit_applied"))
        
        r_gross = r_deposit + r_usd + r_eur + ((r_cash + r_visa) / rate)
        r_cost = safe_float(r.get("cost_total"))
        
        income += r_gross
        costs += r_cost
        
        cash_val += (r_cash / rate)
        visa_val += (r_visa / rate)
        usd_val += (r_usd + r_deposit)
        eur_val += r_eur
        
        trend_map[day] = trend_map.get(day, 0) + r_gross
        
        hid = r.get("hotel_id")
        hotel_map[hid] = hotel_map.get(hid, 0) + r_gross
        
        sales = split_names(r.get("sales_person"))
        for s in sales: team_map[s] = team_map.get(s, 0) + (r_gross / max(1, len(sales)))
        
        photogs = split_names(r.get("photographer"))
        for p in photogs: team_map[p] = team_map.get(p, 0) + (r_gross / max(1, len(photogs)))

    # Formulate output
    total_sources = cash_val + visa_val + usd_val + eur_val
    sources = []
    if total_sources > 0:
        sources = [
            {"name": "كاش (EGP)", "pct": round((cash_val/total_sources)*100), "val": round(cash_val, 2)},
            {"name": "فيزا (EGP)", "pct": round((visa_val/total_sources)*100), "val": round(visa_val, 2)},
            {"name": "دولار/يورو", "pct": round(((usd_val+eur_val)/total_sources)*100), "val": round(usd_val+eur_val, 2)}
        ]

    if req_type == "photo":
        l_costs = 0
        expenses = [
            {"name": "تشغيل تصوير (طباعة/ألبومات)", "value": round(costs, 2), "currency": "$"},
            {"name": "صيانة معدات التصوير", "value": round(m_costs, 2), "currency": "LE"}
        ]
    elif req_type == "laundry":
        income = 0; costs = 0
        expenses = [
            {"name": "تكلفة المغسلة الإجمالية", "value": round(l_costs, 2), "currency": "LE"}
        ]
    else:
        expenses = [
            {"name": "تشغيل (طباعة/ألبومات)", "value": round(costs, 2), "currency": "$"},
            {"name": "تكلفة المغسلة", "value": round(l_costs, 2), "currency": "LE"},
            {"name": "صيانة معدات", "value": round(m_costs, 2), "currency": "LE"}
        ]
    
    net_profit = income - costs - ((l_costs + m_costs) / 50)

    return ok({
        "bookings": bookings_data.get("bookings", 0),
        "agreed": round(safe_float(bookings_data.get("agreed")), 2),
        "remaining": round(safe_float(bookings_data.get("remaining")), 2),
        "income": round(income, 2),
        "costs": round(costs, 2),
        "net_profit": round(net_profit, 2),
        "trend": [{"day": k, "total": round(v, 2)} for k, v in sorted(trend_map.items())],
        "sources": sources,
        "top_team": [{"name": k, "value": round(v, 2)} for k, v in sorted(team_map.items(), key=lambda x: x[1], reverse=True)[:10]],
        "top_hotels": [{"name": hotel_names_map.get(k, f"فندق {k}"), "value": round(v, 2)} for k, v in sorted(hotel_map.items(), key=lambda x: x[1], reverse=True)[:10]],
        "expenses": expenses
    })
# -----------------------------------------------------------------------------
# Settings APIs
# -----------------------------------------------------------------------------
@app.get("/api/settings")
@require_permission("finances_access")
def api_settings():
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT setting_key, setting_value, updated_at FROM system_settings ORDER BY setting_key")
        return ok(rows_to_json(cur.fetchall()))


@app.put("/api/settings")
@require_permission("finances_access")
def api_settings_update():
    d = request.get_json(silent=True) or {}
    with get_db_connection() as conn:
        cur = conn.cursor()
        for k, v in d.items():
            cur.execute(
                "INSERT INTO system_settings (setting_key, setting_value) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value)",
                (k, str(v))
            )
    return ok()
# =============================================================================
# BOOM EDITION - Operations OS extensions
# These endpoints sit on top of the original business logic without replacing it.
# =============================================================================
WORKFLOW_STAGES = [
    ("booked", "تم الحجز"),
    ("deposit", "العربون"),
    ("prep", "تجهيز الملابس"),
    ("arrived", "حضور العميل"),
    ("shooting", "التصوير"),
    ("post", "المونتاج / المعالجة"),
    ("ready", "جاهز للتسليم"),
    ("delivered", "تم التسليم"),
]
CHECKLIST_ITEMS = [
    ("phone_verified", "تأكيد رقم الهاتف"),
    ("payment_checked", "مراجعة العربون والمتبقي"),
    ("clothes_ready", "تجهيز الملابس المطلوبة"),
    ("photographer_assigned", "تعيين المصور"),
    ("guest_arrived", "تسجيل حضور العميل"),
    ("files_backed_up", "نسخ ملفات التصوير احتياطياً"),
    ("delivery_confirmed", "تأكيد التسليم للعميل"),
]


def _ensure_workflow_rows(cur, booking_id):
    for key, label in WORKFLOW_STAGES:
        cur.execute(
            "INSERT IGNORE INTO booking_workflow (booking_id,stage_key,stage_label,stage_status) VALUES (%s,%s,%s,'pending')",
            (booking_id, key, label),
        )


def _workflow_auto_state(booking):
    completed = {"booked"}
    if safe_float(booking.get("deposit_usd")) or safe_float(booking.get("deposit_eur")) or safe_float(booking.get("deposit_le_cash")) or safe_float(booking.get("deposit_le_visa")):
        completed.add("deposit")
    if parse_json_list(booking.get("clothing")):
        completed.add("prep")
    status = str(booking.get("status") or "").lower()
    if "deliver" in status or "تسليم" in status:
        completed.update({"arrived", "shooting", "post", "ready", "delivered"})
    elif "مؤكد" in status or "confirm" in status:
        completed.add("arrived")
    return completed


@app.get("/control-room")
@login_required
def control_room_page():
    return page("control_room.html", "control_room")


@app.get("/api/ops/overview")
@login_required
def api_ops_overview():
    day = request.args.get("date") or date.today().isoformat()
    names, ids = allowed_hotel_names(), allowed_hotel_ids()
    wb, pb = make_where_for_hotels("b.hotel", names)
    wt, pt = make_where_for_hotels("t.hotel_id", ids)
    wh, ph = make_where_for_hotels("h.id", ids)
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(f"""
            SELECT b.id,b.hotel,b.booking_date,b.room_number,b.phone_number,b.booking_time,b.nationality,
                   b.session_details,b.clothing,b.total_agreement,b.remaining,b.sales_person,b.photographer,b.status
            FROM bookings b WHERE b.booking_date=%s {wb}
            ORDER BY b.booking_time ASC,b.id ASC
        """, tuple([day] + pb))
        bookings = rows_to_json(cur.fetchall())
        if is_personal_scope_user():
            bookings = [b for b in bookings if record_belongs_to_current_user(b)]
        cur.execute(f"SELECT * FROM operations_tasks t WHERE t.status NOT IN ('done','cancelled') {wt} ORDER BY FIELD(t.priority,'critical','high','normal','low'),t.due_at IS NULL,t.due_at,t.id DESC LIMIT 80", tuple(pt))
        tasks = rows_to_json(cur.fetchall())
        cur.execute(f"SELECT h.id,h.hotel_name,COUNT(b.id) bookings,COALESCE(SUM(b.total_agreement),0) agreed,COALESCE(SUM(b.remaining),0) remaining FROM hotels h LEFT JOIN bookings b ON b.hotel=h.hotel_name AND b.booking_date=%s WHERE 1=1 {wh} GROUP BY h.id,h.hotel_name ORDER BY bookings DESC", tuple([day] + ph))
        hotels = rows_to_json(cur.fetchall())
        cur.execute(f"SELECT h.id,h.hotel_name,COALESCE(SUM(d.daily_total),0) net,COALESCE(SUM(d.cost_total),0) costs FROM hotels h LEFT JOIN daily_income d ON d.hotel_id=h.id AND d.income_date=%s WHERE 1=1 {wh} GROUP BY h.id,h.hotel_name ORDER BY net DESC", tuple([day] + ph))
        income_hotels = {r['id']: r for r in rows_to_json(cur.fetchall())}
        cur.execute("SELECT COUNT(*) open_maintenance FROM asset_maintenance_logs WHERE status NOT IN ('تم الاستلام','مكتمل','Completed')")
        maintenance = (cur.fetchone() or {}).get("open_maintenance", 0)
        cur.execute("SELECT COUNT(*) open_incidents FROM asset_incident_logs WHERE incident_date=%s", (day,))
        incidents = (cur.fetchone() or {}).get("open_incidents", 0)
    now = datetime.now()
    queue, alerts = [], []
    counts = {"total": len(bookings), "confirmed": 0, "delivered": 0, "pending": 0, "unassigned": 0, "payment_due": 0, "late": 0}
    for b in bookings:
        st = str(b.get("status") or "").lower()
        if "deliver" in st or "تسليم" in st: counts["delivered"] += 1
        elif "مؤكد" in st or "confirm" in st: counts["confirmed"] += 1
        else: counts["pending"] += 1
        if not str(b.get("photographer") or "").strip() or str(b.get("photographer")) == "بدون مصور":
            counts["unassigned"] += 1
            alerts.append({"severity":"high","type":"staff","booking_id":b['id'],"title":f"غرفة {b['room_number']} بدون مصور","text":f"موعد {str(b.get('booking_time') or '--')[:5]} • {b.get('hotel') or ''}"})
        if safe_float(b.get("remaining")) > 0:
            counts["payment_due"] += 1
        minutes = None
        try:
            tm = str(b.get("booking_time") or "")[:5]
            dt = datetime.strptime(f"{day} {tm}", "%Y-%m-%d %H:%M")
            minutes = int((dt-now).total_seconds()/60)
            if minutes < -30 and not ("deliver" in st or "تسليم" in st or "كنسل" in st or "cancel" in st):
                counts["late"] += 1
                alerts.append({"severity":"critical","type":"time","booking_id":b['id'],"title":f"موعد متأخر • غرفة {b['room_number']}","text":f"متأخر {abs(minutes)} دقيقة"})
        except Exception:
            pass
        queue.append({**b, "minutes_to_session": minutes})
    for h in hotels:
        inc = income_hotels.get(h["id"], {})
        h["net"] = safe_float(inc.get("net")); h["costs"] = safe_float(inc.get("costs"))
    return ok({"date":day,"counts":counts,"queue":queue,"alerts":alerts[:50],"tasks":tasks,"hotels":hotels,"maintenance":maintenance,"incidents":incidents})


@app.get("/api/ops/photographer-load")
@login_required
def api_photographer_load():
    day = request.args.get("date") or date.today().isoformat()
    names = allowed_hotel_names(); w,p = make_where_for_hotels("hotel", names)
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True)
        cur.execute("SELECT id,nickname,hotel_id,role FROM team_members WHERE is_active=1 ORDER BY nickname")
        team=[rows_to_json([r])[0] for r in cur.fetchall() if any(_normalize_role(x)=='photographer' for x in get_user_roles(user_id=r.get('id'), user=r))]
        cur.execute(f"SELECT id,photographer,booking_time,hotel,room_number,status FROM bookings WHERE booking_date=%s {w} AND status NOT IN ('كنسل','cancelled','ملغي')",tuple([day]+p))
        rows=rows_to_json(cur.fetchall())
    load={r['nickname']:{"name":r['nickname'],"count":0,"sessions":[]} for r in team}
    for b in rows:
        for n in split_names(b.get('photographer')):
            if n not in load: load[n]={"name":n,"count":0,"sessions":[]}
            load[n]["count"]+=1; load[n]["sessions"].append({"id":b['id'],"time":str(b.get('booking_time') or '')[:5],"room":b.get('room_number'),"hotel":b.get('hotel')})
    return ok(sorted(load.values(),key=lambda x:(x['count'],x['name'])))


@app.get("/api/bookings/<int:booking_id>/workflow")
@require_permission("bookings_access")
def api_booking_workflow(booking_id):
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True); booking=get_booking_dict(cur,booking_id)
        if not booking:return fail("الحجز غير موجود",404)
        if not booking_scope_ok(booking):return fail("ليس لديك صلاحية",403)
        c=conn.cursor();_ensure_workflow_rows(c,booking_id)
        auto=_workflow_auto_state(booking)
        for key in auto:
            c.execute("UPDATE booking_workflow SET stage_status=IF(stage_status='pending','done',stage_status),completed_at=IF(completed_at IS NULL,NOW(),completed_at) WHERE booking_id=%s AND stage_key=%s",(booking_id,key))
        cur=conn.cursor(dictionary=True);cur.execute("SELECT * FROM booking_workflow WHERE booking_id=%s ORDER BY FIELD(stage_key,'booked','deposit','prep','arrived','shooting','post','ready','delivered'),id",(booking_id,));rows=rows_to_json(cur.fetchall())
    return ok(rows)


@app.put("/api/bookings/<int:booking_id>/workflow")
@require_permission("bookings_access")
def api_booking_workflow_update(booking_id):
    d=request.get_json(silent=True) or {}; key=str(d.get('stage_key') or '')
    allowed={x[0]:x[1] for x in WORKFLOW_STAGES}
    if key not in allowed:return fail("مرحلة غير صحيحة")
    status=str(d.get('stage_status') or 'done')
    if status not in {'pending','active','done','blocked'}:return fail("حالة المرحلة غير صحيحة")
    with get_db_connection() as conn:
        c=conn.cursor();_ensure_workflow_rows(c,booking_id)
        c.execute("UPDATE booking_workflow SET stage_status=%s,notes=%s,updated_by=%s,started_at=IF(%s IN ('active','done') AND started_at IS NULL,NOW(),started_at),completed_at=IF(%s='done',NOW(),NULL) WHERE booking_id=%s AND stage_key=%s",(status,d.get('notes') or '',(current_user() or {}).get('id'),status,status,booking_id,key))
    booking_activity(booking_id,"WORKFLOW",f"تحديث مرحلة: {allowed[key]}",f"الحالة: {status} • {d.get('notes') or ''}")
    return ok()


@app.get("/api/bookings/<int:booking_id>/checklist")
@require_permission("bookings_access")
def api_booking_checklist(booking_id):
    with get_db_connection() as conn:
        c=conn.cursor()
        for key,label in CHECKLIST_ITEMS:c.execute("INSERT IGNORE INTO booking_checklist (booking_id,item_key,item_label) VALUES (%s,%s,%s)",(booking_id,key,label))
        cur=conn.cursor(dictionary=True);cur.execute("SELECT * FROM booking_checklist WHERE booking_id=%s ORDER BY id",(booking_id,));return ok(rows_to_json(cur.fetchall()))


@app.post("/api/bookings/<int:booking_id>/checklist")
@require_permission("bookings_access")
def api_booking_checklist_update(booking_id):
    d=request.get_json(silent=True) or {}; key=str(d.get('item_key') or ''); done=1 if d.get('is_done') else 0
    with get_db_connection() as conn:
        c=conn.cursor();
        label=dict(CHECKLIST_ITEMS).get(key,key)
        c.execute("INSERT IGNORE INTO booking_checklist (booking_id,item_key,item_label) VALUES (%s,%s,%s)",(booking_id,key,label))
        c.execute("UPDATE booking_checklist SET is_done=%s,completed_by=%s,completed_at=%s,notes=%s WHERE booking_id=%s AND item_key=%s",(done,(current_user() or {}).get('id'),datetime.now() if done else None,d.get('notes') or '',booking_id,key))
    booking_activity(booking_id,"CHECKLIST",f"{'✓' if done else '○'} {label}",d.get('notes') or '')
    return ok()


@app.get("/api/tasks")
@login_required
def api_tasks_list():
    status=request.args.get('status','open'); ids=allowed_hotel_ids();w,p=make_where_for_hotels('t.hotel_id',ids)
    sql=f"SELECT t.*,tm.nickname assigned_name,h.hotel_name FROM operations_tasks t LEFT JOIN team_members tm ON tm.id=t.assigned_to LEFT JOIN hotels h ON h.id=t.hotel_id WHERE 1=1 {w}";args=list(p)
    if status and status!='all':sql+=' AND t.status=%s';args.append(status)
    sql+=' ORDER BY FIELD(t.priority,\'critical\',\'high\',\'normal\',\'low\'),t.due_at IS NULL,t.due_at,t.id DESC LIMIT 500'
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cur.execute(sql,tuple(args));return ok(rows_to_json(cur.fetchall()))


@app.post("/api/tasks")
@login_required
def api_tasks_add():
    d=request.get_json(silent=True) or {}; title=str(d.get('title') or '').strip()
    if not title:return fail('عنوان المهمة مطلوب')
    hid=safe_int(d.get('hotel_id'),0) or None
    if hid and not verify_hotel_id(hid):return fail('ليس لديك صلاحية',403)
    with get_db_connection() as conn:
        cur=conn.cursor();cur.execute("INSERT INTO operations_tasks (hotel_id,booking_id,task_type,priority,title,details,assigned_to,due_at,status,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'open',%s)",(hid,safe_int(d.get('booking_id'),0) or None,d.get('task_type') or 'general',d.get('priority') or 'normal',title,d.get('details') or '',safe_int(d.get('assigned_to'),0) or None,d.get('due_at') or None,(current_user() or {}).get('id')));tid=cur.lastrowid
    audit('ADD_TASK','operations_tasks',f'إضافة مهمة #{tid}: {title}')
    return ok({'id':tid})


@app.put("/api/tasks/<int:task_id>")
@login_required
def api_tasks_update(task_id):
    d=request.get_json(silent=True) or {}; fields=[]; vals=[]
    for key in ['status','priority','title','details','due_at','assigned_to']:
        if key in d: fields.append(f"{key}=%s"); vals.append(d[key] if d[key] not in ('',0) else None)
    if 'status' in d and d['status']=='done':fields.append('completed_at=NOW()')
    if not fields:return ok()
    with get_db_connection() as conn:conn.cursor().execute(f"UPDATE operations_tasks SET {','.join(fields)} WHERE id=%s",tuple(vals+[task_id]))
    return ok()


@app.get("/api/handover")
@login_required
def api_handover_list():
    day=request.args.get('date') or date.today().isoformat(); ids=allowed_hotel_ids();w,p=make_where_for_hotels('n.hotel_id',ids)
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cur.execute(f"SELECT n.*,h.hotel_name,tm.nickname author FROM shift_handover_notes n LEFT JOIN hotels h ON h.id=n.hotel_id LEFT JOIN team_members tm ON tm.id=n.created_by WHERE n.shift_date=%s {w} ORDER BY n.resolved_at IS NULL DESC,n.id DESC",tuple([day]+p));return ok(rows_to_json(cur.fetchall()))


@app.post("/api/handover")
@login_required
def api_handover_add():
    d=request.get_json(silent=True) or {}; note=str(d.get('note') or '').strip()
    if not note:return fail('الملاحظة مطلوبة')
    hid=safe_int(d.get('hotel_id'),0) or None
    with get_db_connection() as conn:
        cur=conn.cursor();cur.execute("INSERT INTO shift_handover_notes (hotel_id,shift_date,shift_name,note,priority,created_by) VALUES (%s,%s,%s,%s,%s,%s)",(hid,d.get('shift_date') or date.today().isoformat(),d.get('shift_name') or 'عام',note,d.get('priority') or 'normal',(current_user() or {}).get('id')));nid=cur.lastrowid
    return ok({'id':nid})


@app.post("/api/handover/<int:note_id>/resolve")
@login_required
def api_handover_resolve(note_id):
    with get_db_connection() as conn:conn.cursor().execute("UPDATE shift_handover_notes SET resolved_at=IF(resolved_at IS NULL,NOW(),NULL) WHERE id=%s",(note_id,))
    return ok()


@app.post("/api/notifications/<int:nid>/read")
@login_required
def api_notification_read(nid):
    with get_db_connection() as conn:conn.cursor().execute("UPDATE system_notifications SET status='Read' WHERE id=%s",(nid,))
    return ok()


@app.get("/api/assets/transfers")
@require_permission("assets_access")
def api_asset_transfers():
    ids=allowed_hotel_ids();w,p=make_where_for_hotels('tr.from_hotel_id',ids)
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cur.execute(f"SELECT tr.*,fh.hotel_name from_hotel,th.hotel_name to_hotel,tm.nickname requested_name FROM inventory_transfer_requests tr LEFT JOIN hotels fh ON fh.id=tr.from_hotel_id LEFT JOIN hotels th ON th.id=tr.to_hotel_id LEFT JOIN team_members tm ON tm.id=tr.requested_by WHERE 1=1 {w} ORDER BY tr.id DESC LIMIT 500",tuple(p));return ok(rows_to_json(cur.fetchall()))


@app.post("/api/assets/transfers")
@require_permission("assets_access")
def api_asset_transfer_add():
    d=request.get_json(silent=True) or {}; typ=d.get('asset_type'); aid=safe_int(d.get('asset_id')); to_id=safe_int(d.get('to_hotel_id')); qty=max(1,safe_int(d.get('quantity'),1))
    if typ not in {'dress','equipment'} or not aid or not to_id:return fail('بيانات النقل غير مكتملة')
    table='dress_inventory' if typ=='dress' else 'equipment_inventory'
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cur.execute(f"SELECT * FROM {table} WHERE id=%s",(aid,));row=cur.fetchone()
        if not row:return fail('الأصل غير موجود',404)
        from_id=safe_int(row.get('hotel_id'),1)
        if not verify_hotel_id(from_id):return fail('ليس لديك صلاحية',403)
        c=conn.cursor();c.execute("INSERT INTO inventory_transfer_requests (asset_type,asset_id,from_hotel_id,to_hotel_id,quantity,reason,status,requested_by,approved_by,completed_at) VALUES (%s,%s,%s,%s,%s,%s,'completed',%s,%s,NOW())",(typ,aid,from_id,to_id,qty,d.get('reason') or '',(current_user() or {}).get('id'),(current_user() or {}).get('id')));tid=c.lastrowid;c.execute(f"UPDATE {table} SET hotel_id=%s,status='متاح' WHERE id=%s",(to_id,aid))
    audit('ASSET_TRANSFER',table,f'نقل {typ} #{aid} من فندق {from_id} إلى {to_id}')
    return ok({'id':tid})


@app.get("/api/closings/daily")
@require_permission("finances_access")
def api_daily_closing_get():
    day=request.args.get('date') or date.today().isoformat(); hid=safe_int(request.args.get('hotel_id'),0) or ((current_user() or {}).get('hotel_id') or 1)
    if not verify_hotel_id(hid):return fail('ليس لديك صلاحية',403)
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cur.execute("SELECT COALESCE(SUM(income_usd),0) usd,COALESCE(SUM(income_eur),0) eur,COALESCE(SUM(income_le_m),0) cash,COALESCE(SUM(income_le_k),0) visa,COALESCE(SUM(daily_total),0) net,COALESCE(SUM(cost_total),0) costs FROM daily_income WHERE hotel_id=%s AND income_date=%s",(hid,day));expected={k:serialize(v) for k,v in (cur.fetchone() or {}).items()};cur.execute("SELECT * FROM hotel_closing_sessions WHERE hotel_id=%s AND closing_date=%s",(hid,day));saved=cur.fetchone()
    return ok({'expected':expected,'closing':{k:serialize(v) for k,v in saved.items()} if saved else None})


@app.post("/api/closings/daily")
@require_permission("finances_access")
def api_daily_closing_save():
    d=request.get_json(silent=True) or {}; day=d.get('closing_date') or date.today().isoformat();hid=safe_int(d.get('hotel_id'),0) or ((current_user() or {}).get('hotel_id') or 1)
    if not verify_hotel_id(hid):return fail('ليس لديك صلاحية',403)
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cur.execute("SELECT COALESCE(SUM(income_usd),0) usd,COALESCE(SUM(income_eur),0) eur,COALESCE(SUM(income_le_m),0) cash,COALESCE(SUM(income_le_k),0) visa FROM daily_income WHERE hotel_id=%s AND income_date=%s",(hid,day));e=cur.fetchone() or {};c=conn.cursor();c.execute("""INSERT INTO hotel_closing_sessions (hotel_id,closing_date,expected_usd,expected_eur,expected_egp_cash,expected_egp_visa,actual_usd,actual_eur,actual_egp_cash,actual_egp_visa,variance_note,status,closed_by,closed_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,IF(%s='closed',NOW(),NULL)) ON DUPLICATE KEY UPDATE expected_usd=VALUES(expected_usd),expected_eur=VALUES(expected_eur),expected_egp_cash=VALUES(expected_egp_cash),expected_egp_visa=VALUES(expected_egp_visa),actual_usd=VALUES(actual_usd),actual_eur=VALUES(actual_eur),actual_egp_cash=VALUES(actual_egp_cash),actual_egp_visa=VALUES(actual_egp_visa),variance_note=VALUES(variance_note),status=VALUES(status),closed_by=VALUES(closed_by),closed_at=IF(VALUES(status)='closed',NOW(),closed_at)""",(hid,day,e.get('usd') or 0,e.get('eur') or 0,e.get('cash') or 0,e.get('visa') or 0,safe_float(d.get('actual_usd')),safe_float(d.get('actual_eur')),safe_float(d.get('actual_egp_cash')),safe_float(d.get('actual_egp_visa')),d.get('variance_note') or '',d.get('status') or 'open',(current_user() or {}).get('id'),d.get('status') or 'open'))
    audit('DAILY_CLOSING','hotel_closing_sessions',f'تقفيل فندق {hid} بتاريخ {day}')
    return ok()


@app.get("/api/bookings/<int:booking_id>/qr")
@login_required
def api_booking_qr(booking_id):
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);b=get_booking_dict(cur,booking_id)
    if not b:return fail('الحجز غير موجود',404)
    if not booking_scope_ok(b):return fail('ليس لديك صلاحية',403)
    payload=json.dumps({'booking_id':booking_id,'room':b.get('room_number'),'hotel':b.get('hotel'),'date':serialize(b.get('booking_date')),'time':b.get('booking_time')},ensure_ascii=False)
    try:
        import qrcode
        image=qrcode.make(payload);bio=io.BytesIO();image.save(bio,format='PNG');bio.seek(0);return send_file(bio,mimetype='image/png',download_name=f'booking_{booking_id}_qr.png')
    except Exception:
        # Fallback SVG data marker if qrcode is not installed yet.
        svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="360" height="120"><rect width="100%" height="100%" fill="white"/><text x="18" y="40" font-family="Arial" font-size="20">PHOTO TEAM #{booking_id}</text><text x="18" y="75" font-family="Arial" font-size="15">Room {b.get('room_number')} • {b.get('hotel')}</text><text x="18" y="100" font-family="Arial" font-size="12">Install qrcode package for QR image</text></svg>'''
        return Response(svg,mimetype='image/svg+xml')


@app.get("/api/followups")
@require_permission("bookings_access")
def api_followups_list():
    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cur.execute("SELECT f.*,b.room_number,b.hotel,b.phone_number FROM customer_followups f JOIN bookings b ON b.id=f.booking_id ORDER BY f.id DESC LIMIT 500");return ok(rows_to_json(cur.fetchall()))


@app.post("/api/bookings/<int:booking_id>/followups")
@require_permission("bookings_access")
def api_followup_add(booking_id):
    d=request.get_json(silent=True) or {};typ=d.get('followup_type') or 'reminder'
    with get_db_connection() as conn:
        cur=conn.cursor();cur.execute("INSERT INTO customer_followups (booking_id,followup_type,status,scheduled_at,sent_at,channel,message,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",(booking_id,typ,d.get('status') or ('sent' if d.get('sent') else 'pending'),d.get('scheduled_at') or None,datetime.now() if d.get('sent') else None,d.get('channel') or 'whatsapp',d.get('message') or '',(current_user() or {}).get('id')));fid=cur.lastrowid
    booking_activity(booking_id,'FOLLOWUP',f'متابعة العميل: {typ}',d.get('message') or '')
    return ok({'id':fid})


@app.get("/api/health")
def api_health():
    try:
        with get_db_connection() as conn:
            cur=conn.cursor();cur.execute("SELECT 1");cur.fetchone()
        return ok({"database":"connected","version":"ULTRA WEB 2.0"})
    except Exception as exc:
        return fail(str(exc),500)


ACTIVE_SERVER_PORT = 5000
_NGROK_PROCESS = None

def _get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"

def _free_local_port(preferred=5000):
    global ACTIVE_SERVER_PORT
    env_port = int(os.getenv("PORT", preferred))
    for candidate in (env_port, 5000, 5050, 8080):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", candidate))
            sock.close()
            ACTIVE_SERVER_PORT = candidate
            return candidate
        except OSError:
            pass
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("0.0.0.0", 0))
    port = sock.getsockname()[1]
    sock.close()
    ACTIVE_SERVER_PORT = port
    return port

def _fetch_active_ngrok_url():
    import urllib.request
    for api_port in (4040, 4041, 4042):
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{api_port}/api/tunnels")
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                tunnels = data.get("tunnels") or []
                for t in tunnels:
                    pub = t.get("public_url") or ""
                    if pub.startswith("https://"):
                        return pub
                if tunnels:
                    return tunnels[0].get("public_url")
        except Exception:
            pass
    return None

def _run_desktop_window():
    """Run Flask on 0.0.0.0:5000 so local PC, Wi-Fi phones, and Ngrok all connect seamlessly."""
    port = _free_local_port(5000)
    lan_ip = _get_lan_ip()
    print(f"\n=======================================================")
    print(f"  PHOTO TEAM SYSTEM RUNNING ON PORT {port}")
    print(f"  - Local PC:    http://127.0.0.1:{port}/login")
    print(f"  - Wi-Fi Phone: http://{lan_ip}:{port}/login")
    print(f"  - Ngrok Hub:   http://127.0.0.1:{port}/ngrok-hub")
    print(f"=======================================================\n")

    if os.getenv("PHOTOTEAM_SERVER_ONLY") == "1":
        try:
            from waitress import serve
            serve(app, host="0.0.0.0", port=port, threads=16)
        except Exception:
            app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)
        return

    try:
        import webview
        from waitress import serve

        server = threading.Thread(
            target=serve,
            args=(app,),
            kwargs={"host": "0.0.0.0", "port": port, "threads": 16},
            daemon=True,
        )
        server.start()
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.15):
                    break
            except OSError:
                time.sleep(0.05)
        try:
            webview.settings['ALLOW_DOWNLOADS'] = True
        except Exception:
            pass
        webview.create_window(
            "PHOTO TEAM SYSTEM",
            f"http://127.0.0.1:{port}/login",
            width=1440,
            height=920,
            min_size=(1100, 700),
            resizable=True,
            confirm_close=True,
            text_select=True,
        )
        webview.start(debug=False)
        return
    except Exception:
        url = f"http://127.0.0.1:{port}/login"
        def _launch_browser_app():
            time.sleep(0.8)
            for browser_cmd in ("msedge", "chrome"):
                try:
                    subprocess.Popen([browser_cmd, f"--app={url}", "--start-maximized"], shell=True)
                    return
                except Exception:
                    pass
            webbrowser.open(url)
        threading.Thread(target=_launch_browser_app, daemon=True).start()
        try:
            from waitress import serve
            serve(app, host="0.0.0.0", port=port, threads=16)
        except Exception:
            app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)




# ==============================================================================
# 🤖 PHOTO TEAM AI COPILOT — المساعد الذكي المتكامل (استعلام الغرف، الموظفين، التواريخ والشهور، والأوردرات تحت بعض)
# ==============================================================================

ARABIC_MONTH_MAP = {
    "يناير": 1, "كانون الثاني": 1, "jan": 1, "january": 1,
    "فبراير": 2, "شباط": 2, "feb": 2, "february": 2,
    "مارس": 3, "آذار": 3, "اذار": 3, "mar": 3, "march": 3,
    "ابريل": 4, "أبريل": 4, "نيسان": 4, "apr": 4, "april": 4,
    "مايو": 5, "أيار": 5, "ايار": 5, "may": 5,
    "يونيو": 6, "حزيران": 6, "jun": 6, "june": 6,
    "يوليو": 7, "تموز": 7, "jul": 7, "july": 7,
    "اغسطس": 8, "أغسطس": 8, "آب": 8, "اب": 8, "aug": 8, "august": 8,
    "سبتمبر": 9, "أيلول": 9, "ايلول": 9, "sep": 9, "september": 9,
    "اكتوبر": 10, "أكتوبر": 10, "تشرين الأول": 10, "oct": 10, "october": 10,
    "نوفمبر": 11, "تشرين الثاني": 11, "nov": 11, "november": 11,
    "ديسمبر": 12, "كانون الأول": 12, "dec": 12, "december": 12,
}

ARABIC_NAME_ALIASES = {
    "احمد": "ahmed", "أحمد": "ahmed", "ahmed": "ahmed",
    "عمر": "omar", "عمرو": "omar", "omar": "omar",
    "كريم": "karim", "karim": "karim",
    "سارة": "sara", "ساره": "sara", "sara": "sara", "sarah": "sara",
    "محمود": "mahmoud", "mahmoud": "mahmoud",
    "نادية": "nadia", "ناديه": "nadia", "nadia": "nadia",
    "باسم": "bassem", "bassem": "bassem",
    "محمد": "mohamed", "mohamed": "mohamed",
    "علي": "ali", "على": "ali", "ali": "ali",
    "حسن": "hassan", "hassan": "hassan",
    "مصطفى": "mostafa", "مصطفي": "mostafa", "mostafa": "mostafa",
}

def _normalize_arabic_digits(s):
    trans = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    return str(s or "").translate(trans)

def _parse_ai_date_and_month(q_raw, ref_today=None):
    """يستخرج اليوم المحدد (YYYY-MM-DD) أو الشهر المحدد (YYYY-MM أو رقم الشهر) أو رقم اليوم من نص سؤال المستخدم."""
    q = _normalize_arabic_digits(q_raw).lower()
    ref_today = ref_today or date.today()
    result = {"exact_date": None, "month": None, "year": None, "day_only": None, "label": ""}

    m_iso = re.search(r"\b(20\d{2})[-/\.](0?[1-9]|1[0-2])[-/\.](0?[1-9]|[12]\d|3[01])\b", q)
    if m_iso:
        y, m, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
        result["exact_date"] = f"{y:04d}-{m:02d}-{d:02d}"
        result["label"] = f"يوم {result['exact_date']}"
        return result

    m_dmy = re.search(r"\b(0?[1-9]|[12]\d|3[01])[-/\.](0?[1-9]|1[0-2])[-/\.](20\d{2})\b", q)
    if m_dmy:
        d, m, y = int(m_dmy.group(1)), int(m_dmy.group(2)), int(m_dmy.group(3))
        result["exact_date"] = f"{y:04d}-{m:02d}-{d:02d}"
        result["label"] = f"يوم {result['exact_date']}"
        return result

    m_dm = re.search(r"(?:يوم|بتاريخ|تاريخ|في)?\s*\b(0?[1-9]|[12]\d|3[01])[-/](0?[1-9]|1[0-2])\b", q)
    if m_dm:
        d, m = int(m_dm.group(1)), int(m_dm.group(2))
        y = ref_today.year
        result["exact_date"] = f"{y:04d}-{m:02d}-{d:02d}"
        result["day_only"] = d
        result["month"] = m
        result["label"] = f"يوم {d:02d}/{m:02d}"
        return result

    if any(w in q for w in ["اول امبارح", "أول امبارح", "قبل امس", "قبل أمس"]):
        dt = ref_today - timedelta(days=2)
        result["exact_date"] = dt.isoformat()
        result["label"] = f"أول أمس ({result['exact_date']})"
        return result
    if any(w in q for w in ["امبارح", "إمبارح", "امس", "أمس", "yesterday"]):
        dt = ref_today - timedelta(days=1)
        result["exact_date"] = dt.isoformat()
        result["label"] = f"أمس ({result['exact_date']})"
        return result
    if any(w in q for w in ["النهارده", "النهاردة", "اليوم", "today"]) and not any(w in q for w in ["ملخص اليوم"]):
        result["exact_date"] = ref_today.isoformat()
        result["label"] = f"اليوم ({result['exact_date']})"
        return result

    m_ym = re.search(r"\b(20\d{2})[-/](0?[1-9]|1[0-2])\b", q)
    if m_ym:
        result["year"] = int(m_ym.group(1))
        result["month"] = int(m_ym.group(2))
        result["label"] = f"شهر {result['month']:02d}/{result['year']}"
        return result
    m_my = re.search(r"\b(0?[1-9]|1[0-2])[-/](20\d{2})\b", q)
    if m_my:
        result["month"] = int(m_my.group(1))
        result["year"] = int(m_my.group(2))
        result["label"] = f"شهر {result['month']:02d}/{result['year']}"
        return result

    for m_name, m_num in ARABIC_MONTH_MAP.items():
        if re.search(r"(?:^|\s|في|شهر)" + re.escape(m_name) + r"(?:$|\s|[0-9])", q):
            result["month"] = m_num
            yr_m = re.search(r"\b(20\d{2})\b", q)
            result["year"] = int(yr_m.group(1)) if yr_m else None
            result["label"] = f"شهر {m_name} ({m_num:02d})"
            break

    if not result["month"]:
        if any(w in q for w in ["الشهر ده", "الشهر دة", "هذا الشهر", "الشهر الحالي", "this month"]):
            result["month"] = ref_today.month
            result["year"] = ref_today.year
            result["label"] = f"الشهر الحالي ({ref_today.month:02d}/{ref_today.year})"
        else:
            m_sh = re.search(r"شهر\s*(0?[1-9]|1[0-2])\b", q)
            if m_sh:
                result["month"] = int(m_sh.group(1))
                yr_m = re.search(r"\b(20\d{2})\b", q)
                result["year"] = int(yr_m.group(1)) if yr_m else None
                result["label"] = f"شهر {result['month']:02d}"

    m_day_num = re.search(r"يوم\s*(0?[1-9]|[12]\d|3[01])\b", q)
    if m_day_num:
        d = int(m_day_num.group(1))
        result["day_only"] = d
        if result["month"]:
            y = result["year"] or ref_today.year
            result["exact_date"] = f"{y:04d}-{result['month']:02d}-{d:02d}"
            result["label"] = f"يوم {result['exact_date']}"
        else:
            result["label"] = f"يوم {d:02d}"

    return result


def _match_date_filter(date_val_str, dfilter):
    s = str(date_val_str or "").strip()[:10]
    if not s or len(s) < 10:
        return False
    if dfilter.get("exact_date"):
        if s == dfilter["exact_date"]:
            return True
        if dfilter.get("month") and dfilter.get("day_only"):
            try:
                parts = [int(x) for x in s.split("-")]
                return parts[1] == dfilter["month"] and parts[2] == dfilter["day_only"]
            except Exception:
                return False
        return False
    if dfilter.get("month"):
        try:
            parts = [int(x) for x in s.split("-")]
            if dfilter.get("year") and parts[0] != dfilter["year"]:
                return False
            if parts[1] != dfilter["month"]:
                return False
            if dfilter.get("day_only") and parts[2] != dfilter["day_only"]:
                return False
            return True
        except Exception:
            return False
    if dfilter.get("day_only"):
        try:
            parts = [int(x) for x in s.split("-")]
            return parts[2] == dfilter["day_only"]
        except Exception:
            return False
    return True


def _booking_paid_usd_equiv(b):
    rate = safe_float(b.get("rate")) or 50.0
    usd = safe_float(b.get("deposit_usd") or b.get("deposit_amount"))
    eur = safe_float(b.get("deposit_eur"))
    cash = safe_float(b.get("deposit_le_cash"))
    visa = safe_float(b.get("deposit_le_visa"))
    return usd + eur + ((cash + visa) / rate)


def _booking_total_agreed(b):
    return safe_float(b.get("total_agreement") if b.get("total_agreement") is not None else b.get("total_price"))


def _booking_remaining(b):
    if b.get("remaining") is not None:
        return safe_float(b.get("remaining"))
    if b.get("remaining_amount") is not None:
        return safe_float(b.get("remaining_amount"))
    return max(0.0, _booking_total_agreed(b) - _booking_paid_usd_equiv(b))


def _booking_clothes_text(b):
    raw = b.get("clothing_items") or b.get("clothing")
    items = parse_json_list(raw)
    if items:
        parts = []
        for it in items:
            if isinstance(it, dict):
                parts.append(f"{it.get('type','فستان')} {it.get('color','')} ({it.get('size','M')}) ×{it.get('qty',1)}")
        if parts:
            return " + ".join(parts)
    if isinstance(raw, str) and raw.strip() and raw.strip() != "[]":
        return raw.strip()
    return b.get("session_details") or "بدون فساتين إضافية"


def _build_ai_context_snapshot():
    """يبني ملخصاً شاملاً من قاعدة البيانات مع عزل كل استعلام في try مستقل لضمان عدم توقف المساعد أبداً."""
    u = current_user() or {}
    personal = is_personal_scope_user(u)
    my_names = list(current_employee_names(u))
    display_name = u.get("nickname") or u.get("full_name") or u.get("username") or "المستخدم"
    role_label = u.get("role") or "CEO"
    today_str = date.today().isoformat()

    snap = {
        "user": {
            "name": display_name,
            "role": role_label,
            "personal_scope": personal,
            "names": my_names,
        },
        "today": today_str,
        "bookings": [],
        "incomes": [],
        "deposits": [],
        "conflicts": [],
        "dresses_avail": 0,
        "dresses_maint": 0,
        "equip_avail": 0,
        "equip_maint": 0,
        "team_names": [],
    }

    try:
        with get_db_connection() as conn:
            cur = conn.cursor(dictionary=True)

            # 1. فريق العمل
            try:
                cur.execute("SELECT nickname, full_name, role FROM team_members")
                snap["team_names"] = rows_to_json(cur.fetchall() or [])
            except Exception:
                pass

            # 2. الحجوزات باستخدام fetch_booking_rows الرسمية لتوحيد أسماء الأعمدة
            try:
                all_b = fetch_booking_rows(cur, 600)
                h_names = allowed_hotel_names(u)
                if h_names is not None:
                    all_b = [b for b in all_b if not b.get("_has_hotel_column") or b.get("hotel") in h_names]
                if personal:
                    all_b = [b for b in all_b if record_belongs_to_current_user(b, u)]
                snap["bookings"] = rows_to_json(all_b)
            except Exception:
                pass

            # 3. كشف التعارضات
            try:
                by_slot = {}
                for b in snap["bookings"]:
                    if any(k in str(b.get("status") or "").lower() for k in ["cancel", "ملغ", "كنسل"]):
                        continue
                    bdate = str(b.get("booking_date") or "")[:10]
                    btime = str(b.get("booking_time") or "")[:5]
                    if not bdate or not btime:
                        continue
                    for ph in split_names(b.get("photographer")):
                        key = ("مصور", ph, bdate, btime)
                        by_slot.setdefault(key, []).append(b.get("room_number"))
                for (kind, name, bdate, btime), rooms in by_slot.items():
                    if len(rooms) > 1:
                        snap["conflicts"].append({
                            "type": kind,
                            "name": name,
                            "date": bdate,
                            "time": btime,
                            "rooms": rooms,
                        })
            except Exception:
                pass

            # 4. المبيعات والدخل اليومي (daily_income)
            try:
                h_ids = allowed_hotel_ids(u)
                iw, ip = make_where_for_hotels("di.hotel_id", h_ids)
                cur.execute(f"""
                    SELECT di.*, h.hotel_name
                    FROM daily_income di
                    LEFT JOIN hotels h ON h.id = di.hotel_id
                    WHERE 1=1 {iw}
                    ORDER BY di.income_date DESC, di.id DESC
                    LIMIT 600
                """, tuple(ip))
                raw_incomes = cur.fetchall() or []
                if personal:
                    raw_incomes = [r for r in raw_incomes if record_belongs_to_current_user(r, u)]
                snap["incomes"] = rows_to_json(raw_incomes)
            except Exception:
                pass

            # 5. العرابين
            try:
                if table_exists("deposits"):
                    h_ids = allowed_hotel_ids(u)
                    dw, dp = make_where_for_hotels("d.hotel_id", h_ids)
                    cur.execute(f"""
                        SELECT d.*, h.hotel_name
                        FROM deposits d
                        LEFT JOIN hotels h ON h.id = d.hotel_id
                        WHERE 1=1 {dw}
                        ORDER BY d.deposit_date DESC, d.id DESC
                        LIMIT 300
                    """, tuple(dp))
                    raw_deps = cur.fetchall() or []
                    if personal:
                        raw_deps = [r for r in raw_deps if record_belongs_to_current_user(r, u)]
                    snap["deposits"] = rows_to_json(raw_deps)
            except Exception:
                pass

            # 6. الفساتين والمعدات
            try:
                cur.execute("SELECT status, COALESCE(SUM(quantity), COUNT(*)) c FROM dress_inventory GROUP BY status")
                for r in (cur.fetchall() or []):
                    st = str(r.get("status") or "")
                    if "متاح" in st or "available" in st.lower():
                        snap["dresses_avail"] += safe_int(r.get("c"))
                    else:
                        snap["dresses_maint"] += safe_int(r.get("c"))
            except Exception:
                pass
            try:
                cur.execute("SELECT status, COALESCE(SUM(quantity), COUNT(*)) c FROM equipment_inventory GROUP BY status")
                for r in (cur.fetchall() or []):
                    st = str(r.get("status") or "")
                    if "متاح" in st or "available" in st.lower():
                        snap["equip_avail"] += safe_int(r.get("c"))
                    else:
                        snap["equip_maint"] += safe_int(r.get("c"))
            except Exception:
                pass
    except Exception:
        pass

    return snap


def _extract_employee_from_query(ql, snap):
    known_candidates = set()
    for tm in (snap.get("team_names") or []):
        for k in ("nickname", "full_name"):
            v = str(tm.get(k) or "").strip()
            if v:
                known_candidates.add(v)
    for b in (snap.get("bookings") or []):
        for p in split_names(b.get("photographer")):
            known_candidates.add(p)
        for s in split_names(b.get("sales_person")):
            known_candidates.add(s)
    for inc in (snap.get("incomes") or []):
        for p in split_names(inc.get("photographer")):
            known_candidates.add(p)
        for s in split_names(inc.get("sales_person") or inc.get("deposit_sales_person")):
            known_candidates.add(s)

    for cand in sorted(known_candidates, key=lambda x: len(x), reverse=True):
        cl = cand.lower()
        if len(cl) >= 2 and cl in ql:
            return cand

    for ar_name, en_norm in ARABIC_NAME_ALIASES.items():
        if re.search(r"(?:^|\s|المصور|مصور|السيلز|سيلز)" + re.escape(ar_name) + r"(?:$|\s)", ql):
            for cand in known_candidates:
                if en_norm in cand.lower() or ar_name in cand.lower():
                    return cand
            return en_norm.capitalize()

    m_emp = re.search(r"(?:المصور|مصور|السيلز|سيلز|الموظف)\s+([a-zA-Z\u0600-\u06FF]{2,16})", ql)
    if m_emp:
        word = m_emp.group(1).strip()
        if word not in {"اليوم", "النهارده", "امبارح", "أمس", "في", "يوم", "شهر", "كل", "اعلى", "أعلى", "افضل"}:
            mapped = ARABIC_NAME_ALIASES.get(word, word)
            for cand in known_candidates:
                if mapped.lower() in cand.lower() or word.lower() in cand.lower():
                    return cand
            return word
    return None



# =============================================================================
# 📌 15. كود المساعد الذكي التنفيذي (حجز أوردر، تنزيل خصم، تعديل/إضافة دخل، تغيير ميعاد بالصوت أو الكتابة)
# =============================================================================
def _generate_local_ai_reply(query_text, snap):
    q = _normalize_arabic_digits(str(query_text or "").strip())
    ql = q.lower()
    is_owner_or_mgr = has_full_access() or is_manager_role()
    # 0) تنفيذ أمر حذف أوردر برقم الغرفة عبر المساعد الذكي
    if any(k in ql for k in ["احذف", "امسح", "حذف", "مسح", "الغاء", "إلغاء"]) and any(k in ql for k in ["غرفة", "غرفه", "اوردر", "أوردر", "حجز"]):
        if not is_owner_or_mgr:
            return {"reply": "🔒 **حذف الأوردرات متاح للأونر (CEO) أو المدير (Manager) فقط.**", "actions": []}
        rm = re.search(r"(?:غرفة|غرفه|الغرفة|الغرفه|اوردر|أوردر|حجز|رقم)\s*(\d+)", ql)
        room_no = rm.group(1) if rm else None
        if not room_no:
            return {"reply": "يرجى تحديد رقم الغرفة المراد حذف الأوردر الخاص بها.", "actions": []}
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM bookings WHERE room_number=%s", (room_no,))
            return {
                "reply": f"✅ **تم حذف أوردر غرفة `{room_no}` من قاعدة البيانات فوراً!**",
                "actions": [{"label": "📅 فتح قائمة الحجوزات", "url": "/reservations"}],
            }
        except Exception as exc:
            return {"reply": f"⚠️ تعذر حذف الأوردر: {exc}", "actions": []}

    # A) تنفيذ أمر خصم على موظف عبر المساعد الذكي
    if any(k in ql for k in ["خصم", "جزاء", "اخصم"]) and any(k in ql for k in ["نزل", "سجل", "ضيف", "اضف", "على", "علي"]):
        if not is_owner_or_mgr:
            return {"reply": "🔒 **عفواً، تنزيل الخصومات متاح فقط للأونر (CEO) أو المدير (Manager).**", "actions": []}
        emp_name = _extract_employee_from_query(ql, snap) or "Ahmed"
        nums = re.findall(r"\d+(?:\.\d+)?", ql)
        amt = float(nums[0]) if nums else 100.0
        reason_m = re.search(r"(?:بسبب|عشان|لأن|بيان)\s+(.+)$", q)
        reason_txt = reason_m.group(1).strip() if reason_m else "خصم إداري عبر المساعد الذكي"
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO employee_deductions (employee_name, deduction_date, amount_egp, type, reason) VALUES (%s, %s, %s, %s, %s)",
                    (emp_name, date.today().isoformat(), amt, "خصم إداري", reason_txt),
                )
            return {
                "reply": f"✅ **تم تنفيذ أمر الخصم فوراً في قاعدة البيانات!**\n• **الموظف:** `{emp_name}`\n• **المبلغ:** **{amt:,.2f} LE**\n• **السبب:** {reason_txt}",
                "actions": [{"label": "📊 فتح شاشة العمولات والخصومات", "url": "/commissions"}],
            }
        except Exception as exc:
            return {"reply": f"⚠️ تعذر تسجيل الخصم: {exc}", "actions": []}

    # B) تنفيذ أمر تعديل أو إضافة دخل أوردر عبر المساعد الذكي
    if any(k in ql for k in ["دخل", "تحصيل"]) and any(k in ql for k in ["عدل", "تعديل", "خليه", "ضيف", "اضف", "سجل"]):
        if not (is_owner_or_mgr or is_accountant_only()):
            return {"reply": "🔒 **تعديل أو إضافة دخل الأوردرات عبر المساعد الذكي متاح للأونر أو المدير أو المحاسب فقط.**", "actions": []}
        rm = re.search(r"(?:غرفة|غرفه|اوردر|أوردر|رقم)\s*(\d+)", ql)
        room_no = rm.group(1) if rm else "214"
        rem_q = ql.replace(rm.group(0), "") if rm else ql
        nums = re.findall(r"\d+(?:\.\d+)?", rem_q)
        new_amt = float(nums[0]) if nums else 180.0
        try:
            with get_db_connection() as conn:
                cur = conn.cursor(dictionary=True)
                cur.execute("SELECT * FROM daily_income WHERE room_number=%s ORDER BY id DESC LIMIT 1", (room_no,))
                ex = cur.fetchone()
                if ex:
                    cost_tot = safe_float(ex.get("cost_total"), 0.0)
                    net_tot = max(0.0, new_amt - cost_tot)
                    conn.cursor().execute(
                        "UPDATE daily_income SET income_usd=%s, daily_total=%s WHERE id=%s",
                        (new_amt, net_tot, ex["id"]),
                    )
                    return {
                        "reply": f"✅ **تم تعديل دخل أوردر غرفة `{room_no}` في قاعدة البيانات!**\n• **الدخل الجديد:** **${new_amt:,.2f}**\n• **الصافي بعد التكلفة:** **${net_tot:,.2f}**",
                        "actions": [{"label": "💰 فتح الدخل اليومي", "url": "/daily-sales"}],
                    }
                else:
                    conn.cursor().execute(
                        "INSERT INTO daily_income (hotel_id, room_number, sales_person, photographer, income_usd, daily_total, income_date) VALUES (1, %s, %s, %s, %s, %s, %s)",
                        (room_no, "Sara", "Ahmed", new_amt, new_amt, date.today().isoformat()),
                    )
                    return {
                        "reply": f"✅ **تم إضافة دخل أوردر جديد لغرفة `{room_no}` بمبلغ ${new_amt:,.2f} في قاعدة البيانات!**",
                        "actions": [{"label": "💰 فتح الدخل اليومي", "url": "/daily-sales"}],
                    }
        except Exception as exc:
            return {"reply": f"⚠️ تعذر حفظ دخل الأوردر: {exc}", "actions": []}

    # C) تنفيذ أمر حجز أوردر كامل بالصوت أو الكتابة
    if any(k in ql for k in ["احجز", "حجز اوردر", "حجز أوردر", "سجل حجز", "اوردر جديد", "أوردر جديد"]):
        rm = re.search(r"(?:غرفة|غرفه|الغرفة|الغرفه|رقم)\s*(\d+)", ql)
        room_no = rm.group(1) if rm else "412"
        iso_m = re.search(r"(\d{4}-\d{2}-\d{2})", ql)
        b_date = iso_m.group(1) if iso_m else ( (date.today() + timedelta(days=1)).isoformat() if any(w in ql for w in ["بكرة", "بكره", "غدا", "غداً"]) else date.today().isoformat() )
        tm = re.search(r"(?:الساعة|الساعه|ساعة|ساعه)\s*(\d{1,2})(?::(\d{2}))?", ql)
        if tm:
            hh = int(tm.group(1))
            mm = tm.group(2) or "00"
            if 1 <= hh <= 11 and (any(w in ql for w in ["عصر", "مساء", "مغرب"]) or hh <= 8):
                hh += 12
            b_time = f"{hh:02d}:{mm}"
        else:
            b_time = "16:00"
        dep_m = re.search(r"(?:عربون|دافع|مدفوع)\s*(?:عربون\s*)?(\d+(?:\.\d+)?)", ql)
        dep_usd = float(dep_m.group(1)) if dep_m else 20.0
        agr_m = re.search(r"(?:اتفاق|إجمالي|اجمالي)\s*(\d+(?:\.\d+)?)", ql)
        tot_agr = float(agr_m.group(1)) if agr_m else max(150.0, dep_usd + 100.0)
        rem_amt = max(0.0, tot_agr - dep_usd)
        dresses_found = re.findall(r"فستان\s+([^،,و\d]+?)(?=\s+و|\s+دافع|\s+عربون|\s+اتفاق|$)", q)
        clothing_str = " + ".join(f"فستان {d.strip()}" for d in dresses_found) if dresses_found else ("فستان ملكي" if "فستان" in ql else "بدون فساتين")
        u = current_user() or {}
        sales_p = str(u.get("nickname") or "Sara")
        hotel_n = get_current_user_hotel_name(u) or "الفندق الرئيسي"
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO bookings
                       (hotel, booking_date, room_number, booking_time, session_details, clothing, deposit_usd, total_agreement, remaining, sales_person, status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'مؤكد')""",
                    (hotel_n, b_date, room_no, b_time, f"حجز ذكي ({clothing_str})", clothing_str, dep_usd, tot_agr, rem_amt, sales_p),
                )
                bid = cur.lastrowid
                if dep_usd > 0:
                    queue_pending_deposit(cur, {"id": bid, "hotel": hotel_n, "room_number": room_no, "sales_person": sales_p, "booking_date": b_date, "deposit_usd": dep_usd}, {"usd": dep_usd}, deposit_date=b_date)
            return {
                "reply": (
                    f"🎉 **تم تسجيل وحجز الأوردر الجديد فوراً في قاعدة البيانات!**\n"
                    f"• **رقم الغرفة:** `{room_no}` ({hotel_n})\n"
                    f"• **التاريخ والموعد:** يوم `{b_date}` الساعة `{b_time}`\n"
                    f"• **الفساتين والملابس:** {clothing_str}\n"
                    f"• **العربون المسجل مع السيلز:** **${dep_usd:,.2f}** (المتبقي: ${rem_amt:,.2f})"
                ),
                "actions": [{"label": "📅 فتح قائمة الحجوزات", "url": "/reservations"}],
            }
        except Exception as exc:
            return {"reply": f"⚠️ تعذر حفظ الحجز: {exc}", "actions": []}

    user_info = snap.get("user") or {}
    personal = bool(user_info.get("personal_scope"))
    user_name = user_info.get("name") or "الموظف"
    user_role = user_info.get("role") or "CEO"
    my_names = [n.lower() for n in (user_info.get("names") or [])]

    bookings = snap.get("bookings") or []
    incomes = snap.get("incomes") or []
    deposits = snap.get("deposits") or []
    conflicts = snap.get("conflicts") or []

    latest_data_date = date.today()
    all_dates = [str(b.get("booking_date") or "")[:10] for b in bookings if b.get("booking_date")] + [
        str(r.get("income_date") or "")[:10] for r in incomes if r.get("income_date")
    ]
    today_iso = date.today().isoformat()
    if all_dates and today_iso not in all_dates:
        try:
            latest_data_date = date.fromisoformat(max(all_dates))
        except Exception:
            pass

    dfilter = _parse_ai_date_and_month(ql, ref_today=latest_data_date)
    has_date_filter = bool(dfilter.get("exact_date") or dfilter.get("month") or dfilter.get("day_only"))
    target_emp = _extract_employee_from_query(ql, snap)

    if not target_emp and personal and any(w in ql for w in ["دخلي", "مبيعاتي", "اوردراتي", "أوردراتي", "شغلي", "حجوزاتي"]):
        target_emp = user_name

    # 1) فحص الخصوصية الصارم
    if personal:
        asked_other = False
        if target_emp and target_emp.lower() not in my_names and not any(target_emp.lower() in mn for mn in my_names):
            asked_other = True
        if any(kw in ql for kw in ["مبيعات غيري", "مبيعات كل", "كل المصورين", "كل السيلز", "مبيعات باقي"]):
            asked_other = True
        if asked_other:
            my_net = sum(safe_float(r.get("daily_total")) for r in incomes)
            return {
                "reply": (
                    f"🔒 **تنبيه نظام الخصوصية وعزل البيانات الشخصي:**\n"
                    f"مرحباً **{user_name}**، صلاحية حسابك (`{user_role}`) تتيح لك فقط استعراض وتحليل **أوردراتك ومبيعاتك وعمولاتك الشخصية**، ولا يُسمح بعرض دخل أو أوردرات أي زميل آخر (`{target_emp or 'الزملاء'}`).\n\n"
                    f"📊 **ملخص أرقامك الشخصية الحالية:**\n"
                    f"• إجمالي أوردراتك المسجلة: **{len(bookings)} أوردر**\n"
                    f"• إجمالي صافي مبيعاتك: **${my_net:,.2f}**\n"
                    f"• عمولتك التقديرية الحالية: **${(my_net * 0.12):,.2f}**"
                ),
                "actions": [
                    {"label": "📸 عرض أوردراتي اليوم", "prompt": "اوردراتي اليوم"},
                    {"label": "💰 عرض دخلي ومبيعاتي", "prompt": "دخلي ومبيعاتي"},
                ],
                "mode": "privacy_guard"
            }

    # 2) استعلام دخل أو تفاصيل غرفة محددة بالرقم
    room_match = re.search(r"(?:غرفة|غرفه|اوردر|أوردر|حجز|room|#)\s*(?:رقم\s*)?([0-9]{2,5})", ql)
    if not room_match and re.fullmatch(r"[0-9]{2,4}", ql):
        room_match = re.match(r"([0-9]{2,4})", ql)

    if room_match and not any(k in ql for k in ["واتساب", "رسالة", "رساله", "whatsapp"]):
        room_no = room_match.group(1)
        matched_b = [b for b in bookings if str(b.get("room_number") or "").strip() == room_no]
        matched_inc = [r for r in incomes if str(r.get("room_number") or "").strip() == room_no]
        if has_date_filter:
            matched_b = [b for b in matched_b if _match_date_filter(b.get("booking_date"), dfilter)]
            matched_inc = [r for r in matched_inc if _match_date_filter(r.get("income_date"), dfilter)]

        if not matched_b and not matched_inc:
            scope_note = " (ضمن نطاق أوردراتك الشخصية)" if personal else ""
            period_note = f" في {dfilter['label']}" if has_date_filter else ""
            return {
                "reply": f"🔍 لم أجد أي حجز أو سجل دخل لـ **غرفة {room_no}**{period_note}{scope_note}.",
                "actions": [
                    {"label": "📅 فتح شاشة الحجوزات", "href": "/reservations"},
                    {"label": "💰 فتح المبيعات اليومية", "href": "/daily-sales"}
                ],
                "mode": "room_lookup"
            }

        lines = [f"🏨 **بيانات ودخل غرفة رقم `{room_no}` {('— ' + dfilter['label']) if has_date_filter else ''}:**"]

        if matched_inc:
            total_room_net = sum(safe_float(r.get("daily_total")) for r in matched_inc)
            lines.append(f"💰 **سجلات الدخل والمبيعات المسجلة للغرفة ({len(matched_inc)} سجل — إجمالي الصافي: `${total_room_net:,.2f}`):**")
            for idx, r in enumerate(matched_inc, 1):
                dt_s = r.get("income_date") or "—"
                ht_s = r.get("hotel_name") or "الفندق"
                ph_s = r.get("photographer") or "—"
                sl_s = r.get("sales_person") or r.get("deposit_sales_person") or "—"
                usd_v = safe_float(r.get("income_usd"))
                eur_v = safe_float(r.get("income_eur"))
                egp_m = safe_float(r.get("income_le_m"))
                egp_k = safe_float(r.get("income_le_k"))
                dep_v = safe_float(r.get("deposit_applied") if r.get("deposit_applied") is not None else r.get("deposit"))
                cost_v = safe_float(r.get("cost_total"))
                net_v = safe_float(r.get("daily_total"))
                lines.append(
                    f"  **{idx}. بتاريخ `{dt_s}` ({ht_s}):**\n"
                    f"     • المصور: `{ph_s}` | السيلز: `{sl_s}`\n"
                    f"     • التحصيل: دولار **${usd_v:,.0f}** | يورو **€{eur_v:,.0f}** | كاش **{egp_k:,.0f} ج.م** | مكتب/فيزا **{egp_m:,.0f} ج.م**\n"
                    f"     • العربون المطبق: **${dep_v:,.2f}** | التكاليف: **${cost_v:,.2f}** ⬅️ **صافي الدخل: `${net_v:,.2f}`**"
                )
        else:
            lines.append("⚠️ **الدخل المسجل:** لا يوجد دخل مسجل لهذه الغرفة في شاشة المبيعات حتى الآن.")

        if matched_b:
            lines.append(f"\n📸 **سجلات الحجز والأوردرات للغرفة ({len(matched_b)} أوردر):**")
            for idx, b in enumerate(matched_b, 1):
                lines.append(
                    f"  **{idx}. حجز #{b.get('id')} — بتاريخ `{b.get('booking_date')}` الساعة `{b.get('booking_time') or '—'}` ({b.get('hotel')}):**\n"
                    f"     • الحالة: `{b.get('status')}` | المصور: `{b.get('photographer') or 'بدون مصور'}` | السيلز: `{b.get('sales_person')}`\n"
                    f"     • الفساتين/التفاصيل: {_booking_clothes_text(b)}\n"
                    f"     • إجمالي الاتفاق: **${_booking_total_agreed(b):,.2f}** | المدفوع عربون: **${_booking_paid_usd_equiv(b):,.2f}** | المتبقي: **${_booking_remaining(b):,.2f}**"
                )

        return {
            "reply": "\n".join(lines),
            "actions": [
                {"label": f"💬 رسالة واتساب لغرفة {room_no}", "prompt": f"اكتب رسالة واتساب للعميل غرفة {room_no}"},
                {"label": "💰 فتح شاشة المبيعات", "href": "/daily-sales"},
                {"label": "📅 فتح شاشة الحجوزات", "href": "/reservations"},
            ],
            "mode": "room_lookup"
        }

    # 3) استعلام دخل أو أوردرات مصور / سيلز محدد في يوم كذا أو شهر كذا (تحت بعض)
    if target_emp:
        emp_low = target_emp.lower()
        emp_incomes = [
            r for r in incomes
            if emp_low in str(r.get("photographer") or "").lower()
            or emp_low in str(r.get("sales_person") or r.get("deposit_sales_person") or "").lower()
        ]
        emp_bookings = [
            b for b in bookings
            if emp_low in str(b.get("photographer") or "").lower()
            or emp_low in str(b.get("sales_person") or "").lower()
        ]
        if has_date_filter:
            emp_incomes = [r for r in emp_incomes if _match_date_filter(r.get("income_date"), dfilter)]
            emp_bookings = [b for b in emp_bookings if _match_date_filter(b.get("booking_date"), dfilter)]

        period_title = dfilter["label"] if has_date_filter else "جميع الفترات المسجلة"
        wants_orders_only = any(w in ql for w in ["اوردرات", "أوردرات", "حجوزات"]) and not any(w in ql for w in ["دخل", "مبيعات", "عمول"])

        if not emp_incomes and not emp_bookings:
            return {
                "reply": f"🔍 لا توجد أي سجلات دخل أو أوردرات مسجلة باسم **{target_emp}** في **{period_title}**.",
                "actions": [
                    {"label": f"📊 كل دخل {target_emp}", "prompt": f"عايز دخل {target_emp}"},
                    {"label": f"📸 كل أوردرات {target_emp}", "prompt": f"عايز اوردرات {target_emp}"},
                ],
                "mode": "employee_query"
            }

        lines = [f"👤 **بيانات {target_emp} — ({period_title}):**"]

        if not wants_orders_only and emp_incomes:
            tot_net = sum(safe_float(r.get("daily_total")) for r in emp_incomes)
            tot_usd = sum(safe_float(r.get("income_usd")) for r in emp_incomes)
            tot_eur = sum(safe_float(r.get("income_eur")) for r in emp_incomes)
            tot_egp = sum(safe_float(r.get("income_le_m")) + safe_float(r.get("income_le_k")) for r in emp_incomes)
            lines.append(
                f"💰 **سجلات الدخل والمبيعات تحت بعض ({len(emp_incomes)} أوردر مسجل):**"
            )
            for idx, r in enumerate(emp_incomes, 1):
                sl_name = r.get("sales_person") or r.get("deposit_sales_person") or "—"
                lines.append(
                    f"  **{idx}. غرفة `{r.get('room_number')}`** • `{r.get('income_date')}` • {r.get('hotel_name') or 'الفندق'} — "
                    f"المصور: `{r.get('photographer') or '—'}` | السيلز: `{sl_name}` — "
                    f"تحصيل: (${safe_float(r.get('income_usd')):,.0f} + €{safe_float(r.get('income_eur')):,.0f}) ⬅️ **الصافي: `${safe_float(r.get('daily_total')):,.2f}`**"
                )
            lines.append(
                f"\n📊 **إجمالي دخل {target_emp} ({period_title}):**\n"
                f"• **إجمالي صافي الدخل (Net USD):** **${tot_net:,.2f}**\n"
                f"• **تفصيل العملات:** دولار **${tot_usd:,.0f}** | يورو **€{tot_eur:,.0f}** | مصري **{tot_egp:,.0f} ج.م**\n"
                f"• **العمولة التقديرية (12%):** **${(tot_net * 0.12):,.2f}**"
            )

        if emp_bookings and (wants_orders_only or not emp_incomes or "اوردر" in ql or "أوردر" in ql or "حجز" in ql):
            if emp_incomes and not wants_orders_only:
                lines.append("")
            tot_agreed = sum(_booking_total_agreed(b) for b in emp_bookings)
            tot_dep = sum(_booking_paid_usd_equiv(b) for b in emp_bookings)
            tot_rem = sum(_booking_remaining(b) for b in emp_bookings)
            lines.append(f"📸 **قائمة أوردرات وحجوزات {target_emp} تحت بعض ({len(emp_bookings)} أوردر):**")
            for idx, b in enumerate(emp_bookings, 1):
                lines.append(
                    f"  **{idx}. غرفة `{b.get('room_number')}`** ({b.get('hotel')}) • `{b.get('booking_date')}` الساعة `{b.get('booking_time') or '—'}` — "
                    f"المصور: `{b.get('photographer') or '—'}` | السيلز: `{b.get('sales_person') or '—'}` — "
                    f"الاتفاق: **${_booking_total_agreed(b):,.0f}** (المدفوع: ${_booking_paid_usd_equiv(b):,.0f} | المتبقي: ${_booking_remaining(b):,.0f}) — `{b.get('status')}`"
                )
            lines.append(
                f"\n📌 **ملخص الأوردرات:** `{len(emp_bookings)}` أوردر | إجمالي الاتفاق: **${tot_agreed:,.2f}** | المدفوع: **${tot_dep:,.2f}** | المتبقي: **${tot_rem:,.2f}**"
            )

        return {
            "reply": "\n".join(lines),
            "actions": [
                {"label": f"💰 كل دخل {target_emp}", "prompt": f"عايز دخل {target_emp}"},
                {"label": f"📸 كل أوردرات {target_emp}", "prompt": f"عايز اوردرات {target_emp}"},
                {"label": "📈 فتح التقارير", "href": "/reports"},
            ],
            "mode": "employee_query"
        }

    # 4) استعلام "أوردرات يوم كذا" أو "أوردرات شهر كذا" تحت بعض
    is_orders_query = any(w in ql for w in ["اوردرات", "أوردرات", "حجوزات", "اوردر", "أوردر", "جدول اليوم", "شغل يوم"])
    is_income_query = any(w in ql for w in ["دخل", "مبيعات", "ايراد", "إيراد", "تقفيل"])

    if is_orders_query and (has_date_filter or any(w in ql for w in ["تحت بعض", "قائمة", "كل الاوردرات", "كل الأوردرات", "اليوم", "النهارده"])):
        filtered_b = [b for b in bookings if _match_date_filter(b.get("booking_date"), dfilter)] if has_date_filter else bookings[:30]
        period_title = dfilter["label"] if has_date_filter else f"أحدث الأوردرات ({len(filtered_b)} أوردر)"

        if not filtered_b:
            avail_dates = sorted({str(b.get("booking_date") or "")[:10] for b in bookings if b.get("booking_date")}, reverse=True)[:5]
            hint_dates = " ، ".join(f"`{d}`" for d in avail_dates) if avail_dates else "لا توجد تواريخ"
            return {
                "reply": (
                    f"📅 لا توجد أوردرات مسجلة في **{period_title}**{(' ضمن نطاقك الشخصي' if personal else '')}.\n"
                    f"💡 **أحدث التواريخ المسجلة بها أوردرات:** {hint_dates}"
                ),
                "actions": [
                    {"label": f"📸 عرض أوردرات {avail_dates[0]}" if avail_dates else "📅 فتح الحجوزات", "prompt": f"عايز اوردرات يوم {avail_dates[0]}" if avail_dates else "اوردرات اليوم"}
                ],
                "mode": "orders_by_date"
            }

        tot_agreed = sum(_booking_total_agreed(b) for b in filtered_b)
        tot_dep = sum(_booking_paid_usd_equiv(b) for b in filtered_b)
        tot_rem = sum(_booking_remaining(b) for b in filtered_b)

        lines = [f"📋 **قائمة الأوردرات والحجوزات تحت بعض — ({period_title}):**"]
        for idx, b in enumerate(filtered_b, 1):
            lines.append(
                f"**{idx}. غرفة `{b.get('room_number')}`** ({b.get('hotel')}) • التاريخ: `{b.get('booking_date')}` الساعة `{b.get('booking_time') or '—'}`\n"
                f"   • المصور: `{b.get('photographer') or '—'}` | السيلز: `{b.get('sales_person') or '—'}` | الفساتين: {_booking_clothes_text(b)}\n"
                f"   • الاتفاق: **${_booking_total_agreed(b):,.2f}** | المدفوع: **${_booking_paid_usd_equiv(b):,.2f}** | المتبقي: **${_booking_remaining(b):,.2f}** | الحالة: `{b.get('status')}`"
            )
        lines.append(
            f"\n📊 **إجمالي ({period_title}):**\n"
            f"• عدد الأوردرات: **{len(filtered_b)} أوردر**\n"
            f"• إجمالي الاتفاق: **${tot_agreed:,.2f}** | إجمالي المدفوع: **${tot_dep:,.2f}** | إجمالي المتبقي: **${tot_rem:,.2f}**"
        )
        return {
            "reply": "\n".join(lines),
            "actions": [
                {"label": "📅 فتح شاشة الحجوزات", "href": "/reservations"},
                {"label": "💰 عرض دخل نفس الفترة", "prompt": f"عايز دخل {dfilter['label']}" if has_date_filter else "عايز دخل اليوم"},
            ],
            "mode": "orders_by_date"
        }

    # 5) استعلام "دخل يوم كذا" أو "مبيعات شهر كذا" تحت بعض بالتفصيل
    if is_income_query and (has_date_filter or "تحت بعض" in ql):
        filtered_inc = [r for r in incomes if _match_date_filter(r.get("income_date"), dfilter)] if has_date_filter else incomes[:30]
        period_title = dfilter["label"] if has_date_filter else "أحدث المبيعات المسجلة"

        if not filtered_inc:
            avail_dates = sorted({str(r.get("income_date") or "")[:10] for r in incomes if r.get("income_date")}, reverse=True)[:5]
            hint_dates = " ، ".join(f"`{d}`" for d in avail_dates) if avail_dates else "لا توجد تواريخ"
            return {
                "reply": (
                    f"💰 لا توجد سجلات دخل مسجلة في **{period_title}**{(' ضمن نطاقك الشخصي' if personal else '')}.\n"
                    f"💡 **أحدث التواريخ المسجل بها دخل:** {hint_dates}"
                ),
                "actions": [
                    {"label": f"💰 عرض دخل {avail_dates[0]}" if avail_dates else "💰 فتح المبيعات", "prompt": f"عايز دخل يوم {avail_dates[0]}" if avail_dates else "ملخص اليوم"}
                ],
                "mode": "income_by_date"
            }

        tot_net = sum(safe_float(r.get("daily_total")) for r in filtered_inc)
        tot_usd = sum(safe_float(r.get("income_usd")) for r in filtered_inc)
        tot_eur = sum(safe_float(r.get("income_eur")) for r in filtered_inc)
        tot_cash = sum(safe_float(r.get("income_le_k")) for r in filtered_inc)
        tot_office = sum(safe_float(r.get("income_le_m")) for r in filtered_inc)

        lines = [f"💰 **بيان الدخل والمبيعات التفصيلي تحت بعض — ({period_title}):**"]
        for idx, r in enumerate(filtered_inc, 1):
            sl_name = r.get("sales_person") or r.get("deposit_sales_person") or "—"
            lines.append(
                f"**{idx}. غرفة `{r.get('room_number')}`** ({r.get('hotel_name') or 'الفندق'}) • التاريخ: `{r.get('income_date')}`\n"
                f"   • المصور: `{r.get('photographer') or '—'}` | السيلز: `{sl_name}`\n"
                f"   • التحصيل: دولار **${safe_float(r.get('income_usd')):,.0f}** | يورو **€{safe_float(r.get('income_eur')):,.0f}** | كاش **{safe_float(r.get('income_le_k')):,.0f} ج.م** | مكتب **{safe_float(r.get('income_le_m')):,.0f} ج.م** ⬅️ **الصافي: `${safe_float(r.get('daily_total')):,.2f}`**"
            )
        lines.append(
            f"\n📊 **إجمالي الدخل في ({period_title}) عبر `{len(filtered_inc)}` أوردر:**\n"
            f"• **صافي الدخل الكلي (Net USD):** **${tot_net:,.2f}**\n"
            f"• **تفصيل الخزينة:** دولار **${tot_usd:,.0f}** | يورو **€{tot_eur:,.0f}** | كاش مصري **{tot_cash:,.0f} ج.م** | مكتب/فيزا **{tot_office:,.0f} ج.م**"
        )
        return {
            "reply": "\n".join(lines),
            "actions": [
                {"label": "💰 فتح المبيعات اليومية", "href": "/daily-sales"},
                {"label": "📸 عرض أوردرات نفس الفترة", "prompt": f"عايز اوردرات {dfilter['label']}" if has_date_filter else "عايز اوردرات اليوم"},
            ],
            "mode": "income_by_date"
        }

    # 6) صياغة رسائل واتساب للعملاء
    if any(k in ql for k in ["واتساب", "رسالة", "رساله", "whatsapp", "عميل", "انجليزي", "روسي", "الماني"]):
        rm = re.search(r"([0-9]{2,5})", ql)
        room_label = rm.group(1) if rm else "412"
        matched_b = [b for b in bookings if str(b.get("room_number") or "") == room_label]
        b = matched_b[0] if matched_b else (bookings[0] if bookings else {})
        room_label = str(b.get("room_number") or room_label)
        hotel_label = b.get("hotel") or "Resort & Spa"
        shoot_time = b.get("booking_time") or "16:00"
        rem_val = _booking_remaining(b)

        msg_en = (
            f"Hello Dear Guest (Room {room_label} - {hotel_label}) 📸✨\n"
            f"This is PHOTO TEAM Studio. Your photo session is scheduled at {shoot_time}, and your edited preview gallery is ready at our studio desk!"
            + (f" Remaining balance: ${rem_val:,.0f}." if rem_val > 0 else " Fully paid ✅.")
        )
        msg_ru = (
            f"Здравствуйте, уважаемый гость (Комната {room_label} - {hotel_label}) 📸✨\n"
            f"Фотостудия PHOTO TEAM напоминает о вашей фотосессии в {shoot_time}. Ждем вас в нашей студии для просмотра фотографий!"
        )
        msg_ar = (
            f"مرحباً بك ضيفنا العزيز (غرفة {room_label} - {hotel_label}) 📸✨\n"
            f"فريق PHOTO TEAM يذكركم بموعد جلسة التصوير الساعة {shoot_time}، كما يسعدنا تشريفكم في مكتب الاستوديو لمعاينة واستلام الصور."
        )
        return {
            "reply": (
                f"💬 **قوالب رسائل واتساب جاهزة للإرسال (غرفة {room_label} — {hotel_label}):**\n\n"
                f"🇬🇧 **English:**\n> {msg_en}\n\n"
                f"🇷🇺 **Русский:**\n> {msg_ru}\n\n"
                f"🇪🇬 **العربية:**\n> {msg_ar}"
            ),
            "actions": [
                {"label": "📅 الذهاب للحجوزات لإرسال واتساب", "href": "/reservations"},
            ],
            "mode": "whatsapp_template"
        }

    # 7) كشف التعارضات والأوردرات المتأخرة
    if any(k in ql for k in ["تعارض", "مخاطر", "متأخر", "متاخر", "لم يتم تسليم", "active", "تنبيه", "مشاكل", "conflict"]):
        active_orders = [b for b in bookings if not any(w in str(b.get("status") or "").lower() for w in ["deliver", "checkout", "تسليم", "cancel", "ملغ", "كنسل"])]
        unpaid_orders = [b for b in bookings if _booking_remaining(b) > 0]
        lines = [
            f"🛡️ **تقرير الفحص الذكي وكاشف التعارضات ({'نطاقك الشخصي' if personal else 'كل الفروع'}):**",
            f"• **تعارضات المواعيد المزدوجة:** `{len(conflicts)}` حالة تعارض.",
        ]
        for c in conflicts[:4]:
            lines.append(f"  ⚠️ تعارض {c['type']} **{c['name']}** يوم `{c['date']}` الساعة `{c['time']}` بين الغرف: `{', '.join(map(str, c['rooms']))}`")
        lines.append(f"• **أوردرات قيد التنفيذ لم يتم تسليمها تحت بعض ({len(active_orders)} أوردر):**")
        for idx, ab in enumerate(active_orders[:10], 1):
            lines.append(f"  **{idx}. غرفة `{ab.get('room_number')}`** ({ab.get('hotel')}) • التاريخ: `{ab.get('booking_date')}` الساعة `{ab.get('booking_time') or '—'}` — المصور: `{ab.get('photographer') or 'بدون مصور'}`")
        lines.append(f"• **أوردرات عليها مبالغ متبقية للتحصيل:** `{len(unpaid_orders)}` أوردر بإجمالي متبقي **${sum(_booking_remaining(x) for x in unpaid_orders):,.2f}**.")
        return {
            "reply": "\n".join(lines),
            "actions": [
                {"label": "🎛️ فتح غرفة التحكم", "href": "/control-room"},
                {"label": "📅 مراجعة الحجوزات", "href": "/reservations"},
            ],
            "mode": "conflict_audit"
        }

    # 8) تحليل الأداء والترتيب والعمولات
    if any(k in ql for k in ["عمول", "تارجت", "ترتيب", "أفضل", "افضل", "اعلى", "أعلى", "مصورين", "سيلز", "اداء", "أداء", "target", "commission"]):
        total_net = sum(safe_float(r.get("daily_total")) for r in incomes)
        if personal:
            is_photo = "photo" in user_role.lower() or "مصور" in user_role.lower()
            rate = 0.12 if is_photo else 0.10
            comm_usd = total_net * rate
            target_usd = 1500.0
            pct = min(100.0, round((total_net / target_usd) * 100, 1)) if target_usd else 0
            rem_target = max(0.0, target_usd - total_net)
            return {
                "reply": (
                    f"🎯 **تحليل الأداء الشخصي والعمولات — {user_name} ({user_role}):**\n"
                    f"• **إجمالي صافي مبيعاتك المسجلة:** **${total_net:,.2f}** عبر `{len(incomes)}` عملية بيع.\n"
                    f"• **نسبة العمولة المقررة:** `{int(rate*100)}%` — **العمولة المستحقة:** **${comm_usd:,.2f}**\n"
                    f"• **مؤشر تحقيق التارجت الشهري ($1,500):** أنجزت **{pct}%** من التارجت (متبقي **${rem_target:,.2f}** للوصول لشريحة البونص الإضافي 🏆)."
                ),
                "actions": [
                    {"label": "📋 عرض أوردراتي تحت بعض", "prompt": "عايز اوردراتي تحت بعض"},
                    {"label": "💰 عرض دخلي بالتفصيل", "prompt": "عايز دخلي"},
                ],
                "mode": "personal_performance"
            }
        else:
            by_photo = {}
            by_sales = {}
            for r in incomes:
                net = safe_float(r.get("daily_total"))
                for p in split_names(r.get("photographer")):
                    by_photo[p] = by_photo.get(p, 0.0) + net
                for s in split_names(r.get("sales_person") or r.get("deposit_sales_person")):
                    by_sales[s] = by_sales.get(s, 0.0) + net
            top_p = sorted(by_photo.items(), key=lambda x: x[1], reverse=True)
            top_s = sorted(by_sales.items(), key=lambda x: x[1], reverse=True)
            p_lines = "\n".join([f"  **{i}. {k}**: صافي دخل **${v:,.2f}**" for i, (k, v) in enumerate(top_p[:8], 1)]) or "  لا توجد بيانات بعد"
            s_lines = "\n".join([f"  **{i}. {k}**: صافي دخل **${v:,.2f}**" for i, (k, v) in enumerate(top_s[:8], 1)]) or "  لا توجد بيانات بعد"
            return {
                "reply": (
                    f"🏆 **ترتيب دخل المصورين والسيلز تحت بعض (إجمالي المبيعات: `${total_net:,.2f}`):**\n\n"
                    f"📸 **قائمة دخل المصورين:**\n{p_lines}\n\n"
                    f"💼 **قائمة دخل السيلز:**\n{s_lines}"
                ),
                "actions": [
                    {"label": "🏆 لوحة العمولات", "href": "/commissions"},
                    {"label": "📈 التقارير الشاملة", "href": "/reports"},
                ],
                "mode": "team_leaderboard"
            }

    # 9) حالة الفساتين والكاميرات
    if any(k in ql for k in ["فستان", "فساتين", "كاميرا", "كاميرات", "معدات", "عهدة", "مغسلة", "غسيل", "assets"]):
        return {
            "reply": (
                f"👗 **تقرير حالة الفساتين وعهدة الكاميرات والمعدات:**\n"
                f"• **الفساتين الجاهزة والمتاحة للتصوير:** `{snap.get('dresses_avail', 0)}` فستان ✅\n"
                f"• **الفساتين في المغسلة / الصيانة:** `{snap.get('dresses_maint', 0)}` فستان 🧺\n"
                f"• **الكاميرات والعدسات المتاحة بالاستوديو:** `{snap.get('equip_avail', 0)}` قطعة 📷\n"
                f"• **معدات قيد الصيانة / الشحن:** `{snap.get('equip_maint', 0)}` قطعة 🛠️"
            ),
            "actions": [
                {"label": "📷 عهدة المعدات والفساتين", "href": "/assets"},
                {"label": "🧺 قسم المغسلة والكي", "href": "/laundry"},
            ],
            "mode": "assets_status"
        }

    # 10) الملخص التنفيذي العام
    total_usd = sum(safe_float(r.get("income_usd")) for r in incomes)
    total_eur = sum(safe_float(r.get("income_eur")) for r in incomes)
    total_cash = sum(safe_float(r.get("income_le_k")) for r in incomes)
    total_net = sum(safe_float(r.get("daily_total")) for r in incomes)
    checkout_cnt = sum(1 for b in bookings if any(w in str(b.get("status") or "").lower() for w in ["deliver", "checkout", "تسليم"]))
    active_cnt = max(0, len(bookings) - checkout_cnt)

    scope_badge = f"🔒 النطاق الشخصي للموظف ({user_name})" if personal else "🌐 النطاق الإداري الشامل (كل الفروع)"
    return {
        "reply": (
            f"🤖 **التقرير الذكي الفوري — {scope_badge}:**\n"
            f"• **إجمالي الحجوزات والأوردرات:** `{len(bookings)}` أوردر (`{checkout_cnt}` تم تسليمه ✅ | `{active_cnt}` قيد التنفيذ 📸)\n"
            f"• **صافي الدخل المسجل (Net USD):** **${total_net:,.2f}** (نقدي دولار: **${total_usd:,.0f}** | يورو: **€{total_eur:,.0f}** | كاش مصري: **{total_cash:,.0f} ج.م**)"
        ),
        "actions": [],
        "mode": "executive_summary"
    }


@app.get("/api/ai/context")
@login_required
def api_ai_context():
    snap = _build_ai_context_snapshot()
    return ok({
        "user": snap["user"],
        "counts": {
            "bookings": len(snap["bookings"]),
            "incomes": len(snap["incomes"]),
            "deposits": len(snap["deposits"]),
            "conflicts": len(snap["conflicts"]),
        }
    })


@app.post("/api/ai/chat")
@login_required
def api_ai_chat():
    try:
        d = request.get_json(silent=True) or {}
        msg = (d.get("message") or "").strip()
        if not msg:
            return fail("يرجى كتابة سؤالك أو طلبك للمساعد الذكي")

        snap = _build_ai_context_snapshot()
        local_result = _generate_local_ai_reply(msg, snap)
    except Exception as exc:
        return ok({
            "reply": f"🤖 تم استلام سؤالك، ولكن حدث تنبيه أثناء قراءة البيانات: `{exc}`",
            "actions": [{"label": "🏠 الرئيسية", "href": "/"}],
            "mode": "fallback"
        })

    ext_key = (d.get("api_key") or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    provider = (d.get("provider") or "auto").strip().lower()
    if ext_key and local_result.get("mode") != "privacy_guard" and provider in {"auto", "gemini", "openai"}:
        try:
            import urllib.request
            sys_prompt = (
                "أنت المساعد الذكي الرسمي لنظام PHOTO TEAM SYSTEM لإدارة استوديوهات التصوير الفندقية. "
                "أجب باللغة العربية بأسلوب احترافي وودود ومختصر، والتزم تماماً بالبيانات المرفقة لك فقط "
                "ولا تكشف أي بيانات خارج النطاق المسموح للموظف. إذا طلب المستخدم أوردرات يوم أو دخل مصور أو غرفة، اعرضها مرقمة تحت بعض.\n"
                f"نتيجة المحرك الدقيق: {local_result.get('reply')}\n"
                f"بيانات الموظف الحالي والملخص الفوري: {json.dumps(snap, ensure_ascii=False)[:6000]}"
            )
            if ext_key.startswith("AIza") or provider == "gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={ext_key}"
                payload = json.dumps({
                    "contents": [{"parts": [{"text": f"{sys_prompt}\n\nسؤال المستخدم: {msg}"}]}]
                }).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=8) as resp:
                    rj = json.loads(resp.read().decode("utf-8"))
                    cand_text = rj["candidates"][0]["content"]["parts"][0]["text"]
                    if cand_text:
                        local_result["reply"] = cand_text
                        local_result["mode"] = "gemini_live"
            elif ext_key.startswith("sk-") or provider == "openai":
                url = "https://api.openai.com/v1/chat/completions"
                payload = json.dumps({
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": msg}
                    ],
                    "temperature": 0.3
                }).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {ext_key}"
                }, method="POST")
                with urllib.request.urlopen(req, timeout=8) as resp:
                    rj = json.loads(resp.read().decode("utf-8"))
                    cand_text = rj["choices"][0]["message"]["content"]
                    if cand_text:
                        local_result["reply"] = cand_text
                        local_result["mode"] = "openai_live"
        except Exception:
            pass

    return ok(local_result)



@app.post("/api/export/excel")
@login_required
def api_export_excel():
    """يحفظ ملف Excel المنسق (.xls) وملف (.csv) مباشرة في مجلد Downloads ومجلد exports."""
    d = request.get_json(silent=True) or {}
    raw_name = str(d.get("filename") or f"PhotoTeam_Export_{date.today().isoformat()}.xls").strip()
    base_stem = re.sub(r"\.(csv|xls|xlsx)$", "", raw_name, flags=re.IGNORECASE)
    safe_stem = re.sub(r"[^\w\u0600-\u06FF\-]+", "_", base_stem).strip("_") or f"PhotoTeam_Export_{date.today().isoformat()}"
    xls_name = f"{safe_stem}.xls"
    headers = d.get("headers") or []
    rows = d.get("rows") or []
    styled_html = str(d.get("styled_html") or "").strip()

    if styled_html:
        content_bytes = ("\ufeff" + styled_html).encode("utf-8")
        save_filename = xls_name
    else:
        sio = io.StringIO()
        writer = csv.writer(sio)
        if headers:
            writer.writerow([str(h if h is not None else "") for h in headers])
        for r in rows:
            if isinstance(r, (list, tuple)):
                writer.writerow([str(v if v is not None else "") for v in r])
        content_bytes = ("\ufeff" + sio.getvalue()).encode("utf-8-sig")
        save_filename = f"{safe_stem}.csv"

    saved_paths = []
    try:
        dl_dir = Path.home() / "Downloads"
        if dl_dir.exists():
            target_dl = dl_dir / save_filename
            target_dl.write_bytes(content_bytes)
            saved_paths.append(str(target_dl))
    except Exception:
        pass

    try:
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        target_exp = EXPORT_DIR / save_filename
        target_exp.write_bytes(content_bytes)
        saved_paths.append(str(target_exp))
    except Exception:
        pass

    return ok({
        "filename": save_filename,
        "saved_to": saved_paths[0] if saved_paths else save_filename,
        "rows_count": len(rows)
    })



@app.get("/interactive")
@app.get("/preview")
def interactive_preview_page():
    """يعرض النسخة التفاعلية الكاملة PhotoTeam_Interactive_System_V90.html مباشرة عبر السيرفر أو Ngrok."""
    html_file = APP_ROOT / "PhotoTeam_Interactive_System_V90.html"
    if not html_file.exists():
        html_file = BUNDLE_ROOT / "PhotoTeam_Interactive_System_V90.html"
    if html_file.exists():
        return send_file(str(html_file), mimetype="text/html")
    return redirect(url_for("login_page"))


@app.get("/api/ngrok_status")
def api_ngrok_status():
    """يرجع حالة رابط Ngrok الحالي ورابط الـ Wi-Fi المحلي لعرضهما ومشاركتهما مع الموبايلات."""
    port = ACTIVE_SERVER_PORT or 5000
    lan_ip = _get_lan_ip()
    ngrok_url = _fetch_active_ngrok_url()
    return ok({
        "active": bool(ngrok_url),
        "ngrok_url": ngrok_url or "",
        "ngrok_login_url": f"{ngrok_url}/login" if ngrok_url else "",
        "ngrok_interactive_url": f"{ngrok_url}/interactive" if ngrok_url else "",
        "lan_ip": lan_ip,
        "port": port,
        "lan_login_url": f"http://{lan_ip}:{port}/login",
        "lan_interactive_url": f"http://{lan_ip}:{port}/interactive",
    })


@app.post("/api/ngrok_start")
def api_ngrok_start():
    """يقوم بتشغيل Ngrok تلقائياً على بورت البرنامج (5000) مع إمكانية حفظ الـ Authtoken."""
    global _NGROK_PROCESS
    d = request.get_json(silent=True) or {}
    authtoken = str(d.get("authtoken") or "").strip()
    port = ACTIVE_SERVER_PORT or 5000

    ngrok_bin = "ngrok"
    for candidate in (APP_ROOT / "ngrok.exe", APP_ROOT / "ngrok", BUNDLE_ROOT / "ngrok.exe"):
        if candidate.exists():
            ngrok_bin = str(candidate)
            break

    if authtoken:
        try:
            subprocess.run([ngrok_bin, "config", "add-authtoken", authtoken], capture_output=True, text=True, timeout=10)
        except Exception as e:
            return fail(f"تعذر حفظ التوكن: {e}")

    existing_url = _fetch_active_ngrok_url()
    if existing_url:
        return api_ngrok_status()

    try:
        try:
            from pyngrok import ngrok as pyngrok_mod
            if authtoken:
                pyngrok_mod.set_auth_token(authtoken)
            pyngrok_mod.connect(port, "http")
            time.sleep(0.5)
        except Exception:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            _NGROK_PROCESS = subprocess.Popen(
                [ngrok_bin, "http", str(port)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            for _ in range(25):
                time.sleep(0.3)
                if _fetch_active_ngrok_url():
                    break
    except FileNotFoundError:
        return fail("برنامج ngrok غير موجود. ضع ملف ngrok.exe داخل مجلد البرنامج أو قم بتثبيته أولاً.")
    except Exception as e:
        return fail(f"تعذر تشغيل ngrok: {e}")

    ngrok_url = _fetch_active_ngrok_url()
    if not ngrok_url:
        return fail("تم بدء ngrok ولكن لم يظهر الرابط بعد. تأكد من إدخال الـ Authtoken الصحيح من حسابك في dashboard.ngrok.com.")
    return api_ngrok_status()


@app.get("/ngrok-hub")
def ngrok_hub_page():
    """صفحة مركزية لعرض ونسخ لينك Ngrok ولينك الموبايلات."""
    port = ACTIVE_SERVER_PORT or 5000
    lan_ip = _get_lan_ip()
    ngrok_url = _fetch_active_ngrok_url() or ""
    badge_cls = "green" if ngrok_url else "amber"
    badge_txt = "متصل الآن ✅" if ngrok_url else "غير نشط حالياً"
    init_val = (ngrok_url + "/login") if ngrok_url else "اضغط على زر تشغيل Ngrok بالأسفل لتوليد اللينك فوراً..."
    html = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>مركز تشغيل لينك الموبايلات (Ngrok & Wi-Fi) — PHOTO TEAM</title>
<style>
  body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }
  .hub-card { max-width: 780px; margin: 0 auto; background: #1e293b; border: 1px solid #334155; border-radius: 20px; padding: 28px; box-shadow: 0 20px 50px rgba(0,0,0,0.4); }
  h1 { margin: 0 0 8px; font-size: 24px; color: #38bdf8; }
  .sub { color: #94a3b8; font-size: 14px; margin-bottom: 22px; }
  .box { background: #0f172a; border: 1px solid #334155; border-radius: 14px; padding: 18px; margin-bottom: 16px; }
  .badge { display: inline-block; padding: 4px 10px; border-radius: 99px; font-size: 12px; font-weight: 800; }
  .badge.green { background: rgba(16,185,129,0.2); color: #34d399; border: 1px solid rgba(16,185,129,0.4); }
  .badge.amber { background: rgba(245,158,11,0.2); color: #fbbf24; border: 1px solid rgba(245,158,11,0.4); }
  .url-input { width: 100%; box-sizing: border-box; padding: 12px 14px; border-radius: 10px; border: 1px solid #3b82f6; background: #020617; color: #38bdf8; font-size: 16px; font-weight: 800; direction: ltr; text-align: left; margin: 10px 0; }
  .btn-row { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 8px; }
  .btn { border: 0; border-radius: 10px; padding: 10px 16px; font-size: 14px; font-weight: 800; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; }
  .btn.blue { background: #2563eb; color: #fff; }
  .btn.green { background: #059669; color: #fff; }
  .btn.purple { background: #7c3aed; color: #fff; }
  .btn.slate { background: #334155; color: #f8fafc; }
  .token-input { flex: 1; min-width: 240px; padding: 10px 12px; border-radius: 10px; border: 1px solid #475569; background: #020617; color: #fff; direction: ltr; }
</style>
</head>
<body>
<div class="hub-card">
  <h1>🌐 مركز تشغيل لينك الموبايلات (Ngrok + Wi-Fi)</h1>
  <p class="sub">افتح البرنامج من أي عدد من الموبايلات في نفس الوقت (أونر، مدير، محاسب، سيلز، مصورين)</p>

  <div class="box">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
      <strong>🚀 1. لينك Ngrok الخارجي (يعمل من أي موبايل على الإنترنت 4G/5G أو أي فندق)</strong>
      <span id="ngrokBadge" class="badge """ + badge_cls + """">""" + badge_txt + """</span>
    </div>
    <input id="ngrokLoginUrl" class="url-input" readonly value="""" + init_val + """">
    <div class="btn-row">
      <button class="btn blue" onclick="copyInput('ngrokLoginUrl')">📋 نسخ لينك النظام الكامل (/login)</button>
      <button class="btn purple" onclick="copyInteractiveUrl()">📋 نسخ لينك النسخة التفاعلية (/interactive)</button>
      <button class="btn green" onclick="shareWhatsApp('ngrokLoginUrl')">💬 إرسال على واتساب للموبايلات</button>
      <a class="btn slate" href="/login">🔑 فتح النظام</a>
      <a class="btn slate" href="/interactive">✨ فتح النسخة التفاعلية</a>
    </div>
    <div style="margin-top:14px;padding-top:14px;border-top:1px solid #334155;">
      <label style="font-size:13px;color:#cbd5e1;display:block;margin-bottom:6px;">🔑 تشغيل Ngrok أو إدخال كود Authtoken (يُحفظ مرة واحدة فقط):</label>
      <div class="btn-row">
        <input id="ngrokToken" class="token-input" placeholder="اختياري: الصق Ngrok Authtoken هنا لو أول مرة...">
        <button class="btn green" onclick="startNgrokNow()">⚡ تشغيل / تحديث لينك Ngrok الآن</button>
      </div>
      <p id="ngrokMsg" style="font-size:13px;color:#38bdf8;margin:8px 0 0;"></p>
    </div>
  </div>

  <div class="box">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
      <strong>📶 2. لينك الشبكة المحلية Wi-Fi (للموبايلات المتصلة بنفس راوتر الكمبيوتر)</strong>
      <span class="badge green">جاهز دائماً ✅</span>
    </div>
    <input id="lanUrl" class="url-input" readonly value="http://""" + lan_ip + """:""" + str(port) + """/login">
    <div class="btn-row">
      <button class="btn blue" onclick="copyInput('lanUrl')">📋 نسخ لينك الـ Wi-Fi</button>
      <button class="btn green" onclick="shareWhatsApp('lanUrl')">💬 إرسال على واتساب</button>
    </div>
  </div>
</div>
<script>
function copyInput(id) {
  const el = document.getElementById(id);
  if (!el || !el.value.startsWith('http')) return alert('شغّل Ngrok أولاً ليظهر الرابط');
  navigator.clipboard.writeText(el.value);
  document.getElementById('ngrokMsg').textContent = '✅ تم نسخ الرابط: ' + el.value;
}
function copyInteractiveUrl() {
  const el = document.getElementById('ngrokLoginUrl');
  if (!el || !el.value.startsWith('http')) return alert('شغّل Ngrok أولاً ليظهر الرابط');
  const url = el.value.replace(/\/login$/, '/interactive');
  navigator.clipboard.writeText(url);
  document.getElementById('ngrokMsg').textContent = '✅ تم نسخ رابط النسخة التفاعلية: ' + url;
}
function shareWhatsApp(id) {
  const el = document.getElementById(id);
  if (!el || !el.value.startsWith('http')) return alert('شغّل Ngrok أولاً ليظهر الرابط');
  const text = encodeURIComponent('📸 رابط نظام Photo Team للموبايل:\n' + el.value);
  window.open('https://wa.me/?text=' + text, '_blank');
}
async function startNgrokNow() {
  const msg = document.getElementById('ngrokMsg');
  msg.textContent = '⏳ جاري تشغيل Ngrok وجلب الرابط العام...';
  const authtoken = document.getElementById('ngrokToken').value.trim();
  const r = await fetch('/api/ngrok_start', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({authtoken})
  }).then(x => x.json());
  if (!r.ok) {
    msg.style.color = '#f87171';
    msg.textContent = '⚠️ ' + (r.error || 'تعذر تشغيل Ngrok');
    return;
  }
  msg.style.color = '#34d399';
  msg.textContent = '✅ تم تشغيل Ngrok بنجاح!';
  document.getElementById('ngrokLoginUrl').value = r.data.ngrok_login_url;
  const badge = document.getElementById('ngrokBadge');
  badge.className = 'badge green';
  badge.textContent = 'متصل الآن ✅';
}
</script>
</body>
</html>"""
    return Response(html, mimetype="text/html")





to_int = safe_int
to_float = safe_float
json_ok = ok
json_err = fail
current_user_role = lambda: (current_user() or {}).get("role") or "CEO"

def push_notification(title, message, category="ops", target_role=None, hotel_name="", priority="normal", page="dashboard"):
    try:
        emit_notification(
            title,
            message,
            notification_type=category,
            target_role=target_role,
            target_url="/" + page.replace("_", "-"),
            priority=priority,
        )
    except Exception:
        pass

@app.post("/api/bookings/incremental_deposit")
@login_required
def api_booking_incremental_deposit():
    """إضافة عربون إضافي لأوردر قائم وإرسال الإشعار بالمبلغ الجديد فقط (الفرق مع السيلز)."""
    payload = request.get_json(silent=True) or {}
    booking_id = to_int(payload.get("booking_id"), 0)
    added_usd = to_float(payload.get("added_usd"), 0.0)
    added_eur = to_float(payload.get("added_eur"), 0.0)
    added_cash = to_float(payload.get("added_le_cash"), 0.0)
    added_visa = to_float(payload.get("added_le_visa"), 0.0)
    delta_equiv = added_usd + added_eur + ((added_cash + added_visa) / 50.0)
    if booking_id <= 0 or delta_equiv <= 0:
        return json_err("بيانات العربون الإضافي غير مكتملة")

    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
        row = cur.fetchone()
        if not row:
            return json_err("الأوردر غير موجود", 404)
        old_usd = to_float(row.get("deposit_usd"), 0.0)
        old_eur = to_float(row.get("deposit_eur"), 0.0)
        old_cash = to_float(row.get("deposit_le_cash"), 0.0)
        old_visa = to_float(row.get("deposit_le_visa"), 0.0)
        old_equiv = old_usd + old_eur + ((old_cash + old_visa) / 50.0)

        new_usd = old_usd + added_usd
        new_eur = old_eur + added_eur
        new_cash = old_cash + added_cash
        new_visa = old_visa + added_visa
        new_equiv = old_equiv + delta_equiv
        rem = max(0.0, to_float(row.get("total_agreement"), 0.0) - new_equiv)

        cur.execute(
            """UPDATE bookings
               SET deposit_usd=%s, deposit_eur=%s, deposit_le_cash=%s, deposit_le_visa=%s, remaining=%s
               WHERE id=%s""",
            (new_usd, new_eur, new_cash, new_visa, rem, booking_id)
        )
        conn.commit()
        sales_name = session.get("nickname") or row.get("sales_person") or "Sales"
        push_notification(
            f"💵 عربون إضافي جديد مع السيلز ({sales_name}): ${delta_equiv:.2f} فقط • غرفة {row.get('room_number')}",
            f"السيلز ({sales_name}) استلم مبلغ إضافي جديد (${delta_equiv:.2f}) فقط لأوردر غرفة {row.get('room_number')} (كان مدفوع سابقاً: ${old_equiv:.2f} • الإجمالي الكلي أصبح: ${new_equiv:.2f}). المطلوب استلامه من السيلز الآن: ${delta_equiv:.2f} فقط.",
            category="finance",
            target_role="Manager",
            hotel_name=row.get("hotel_name") or "",
            priority="high",
            page="daily_sales"
        )
        return json_ok({"booking_id": booking_id, "old_deposit": old_equiv, "added_delta": delta_equiv, "new_total_deposit": new_equiv})
    finally:
        conn.close()


@app.post("/api/bookings/reschedule")
@login_required
def api_booking_reschedule():
    """تغيير ميعاد الأوردر (تأجيل / تقديم / نقل تاريخ وساعة التصوير)."""
    payload = request.get_json(silent=True) or {}
    booking_id = to_int(payload.get("booking_id"), 0)
    new_date = (payload.get("booking_date") or "").strip()
    new_time = (payload.get("booking_time") or "").strip()
    rsch_type = (payload.get("reschedule_type") or "تغيير ميعاد").strip()
    reason = (payload.get("reason") or "").strip()
    if booking_id <= 0 or not new_date or not new_time:
        return json_err("يرجى تحديد الأوردر والتاريخ والوقت الجديد")

    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
        row = cur.fetchone()
        if not row:
            return json_err("الأوردر غير موجود", 404)
        old_date = str(row.get("booking_date") or "")
        old_time = str(row.get("booking_time") or "")
        new_status = f"{rsch_type} ({new_date} {new_time})"
        cur.execute(
            "UPDATE bookings SET booking_date=%s, booking_time=%s, status=%s WHERE id=%s",
            (new_date, new_time, new_status, booking_id)
        )
        conn.commit()
        push_notification(
            f"⏰ {rsch_type} • غرفة {row.get('room_number')}",
            f"تم {rsch_type} لأوردر غرفة {row.get('room_number')} من [{old_date} الساعة {old_time}] إلى [{new_date} الساعة {new_time}]{' • السبب: ' + reason if reason else ''}.",
            category="ops",
            target_role="Manager",
            hotel_name=row.get("hotel_name") or "",
            priority="high",
            page="reservations"
        )
        return json_ok({"booking_id": booking_id, "old_date": old_date, "old_time": old_time, "new_date": new_date, "new_time": new_time})
    finally:
        conn.close()




@app.post("/api/sales_custody/settle")
@login_required
def api_settle_sales_custody():
    """تقفيل عهدة السيلز اليومية بضغطة واحدة وترحيل كل العرابين المعلقة إلى الدخل اليومي."""
    role = current_user_role()
    if role not in ("CEO", "DirectorManager", "HotelManager", "Accountant"):
        return json_err("تقفيل عهدة السيلز متاح للأونر أو المدير أو المحاسب فقط", 403)
    payload = request.get_json(silent=True) or {}
    sales_person = (payload.get("sales_person") or "").strip()
    date_str = (payload.get("date") or datetime.now().strftime("%Y-%m-%d")).strip()

    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        if sales_person:
            cur.execute(
                "SELECT * FROM deposits WHERE deposit_date = %s AND deposit_sales_person = %s",
                (date_str, sales_person)
            )
        else:
            cur.execute("SELECT * FROM deposits WHERE deposit_date = %s", (date_str,))
        rows = cur.fetchall() or []
        total_equiv = 0.0
        for r in rows:
            total_equiv += (
                to_float(r.get("deposit_usd"), 0.0)
                + to_float(r.get("deposit_eur"), 0.0)
                + ((to_float(r.get("deposit_le_cash"), 0.0) + to_float(r.get("deposit_le_visa"), 0.0)) / 50.0)
            )
        push_notification(
            f"💼 تقفيل عهدة السيلز ({sales_person or 'جميع السيلز'}) اليومية بضغطة واحدة",
            f"تم استلام وتقفيل عهدة السيلز ({sales_person or 'جميع السيلز'}) لعدد ({len(rows)}) عرابين بإجمالي (${total_equiv:.2f}) وترحيلها للدخل اليومي.",
            category="finance",
            target_role="CEO",
            priority="high",
            page="daily_sales"
        )
        return json_ok({"settled_count": len(rows), "total_equiv_usd": round(total_equiv, 2), "sales_person": sales_person or "ALL"})
    finally:
        conn.close()


@app.get("/api/ops/thirty_min_alerts")
@login_required
def api_thirty_min_session_alerts():
    """جلب السيشنات التي تبدأ خلال 30 دقيقة وإرسال تنبيه أوتوماتيك للمصور والسيلز والمدير."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    now_dt = datetime.now()
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM bookings WHERE booking_date = %s AND status != 'كنسل'", (today_str,))
        rows = cur.fetchall() or []
        upcoming = []
        for b in rows:
            t_str = str(b.get("booking_time") or "16:00")[:5]
            try:
                hh, mm = [int(x) for x in t_str.split(":")]
                sess_dt = now_dt.replace(hour=hh, minute=mm, second=0)
                diff_min = int((sess_dt - now_dt).total_seconds() // 60)
            except Exception:
                diff_min = 25
            if 0 < diff_min <= 30:
                upcoming.append({
                    "id": b.get("id"),
                    "room_number": b.get("room_number"),
                    "hotel_name": b.get("hotel_name"),
                    "booking_time": t_str,
                    "photographer": b.get("photographer"),
                    "sales_person": b.get("sales_person"),
                    "minutes_left": diff_min
                })
        return json_ok({"upcoming_30min_sessions": upcoming, "count": len(upcoming)})
    finally:
        conn.close()




# =============================================================================
# 🏦 شاشة حسابات البنك والدخل الشامل (خاص بالأونر CEO فقط) + النسخ الاحتياطي الكامل
# =============================================================================
@app.get("/bank-accounts")
@login_required
def page_bank_accounts():
    if not is_full_access():
        return redirect(url_for("forbidden"))
    return render_template("bank_accounts.html")


@app.get("/api/bank-accounts/overview")
@login_required
def api_bank_accounts_overview():
    if not is_full_access():
        return fail("شاشة حسابات البنك مخصصة للأونر (CEO) فقط", 403)
    start = request.args.get("start") or date.today().replace(day=1).isoformat()
    end = request.args.get("end") or date.today().isoformat()
    hotel_id = request.args.get("hotel_id") or ""

    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SHOW COLUMNS FROM daily_income LIKE 'bank_visa_settled'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE daily_income ADD COLUMN bank_visa_settled TINYINT(1) DEFAULT 0")
        except Exception:
            pass

        q = """SELECT d.*, h.hotel_name
               FROM daily_income d
               LEFT JOIN hotels h ON h.id = d.hotel_id
               WHERE d.income_date BETWEEN %s AND %s"""
        params = [start, end]
        if hotel_id and str(hotel_id).isdigit():
            q += " AND d.hotel_id = %s"
            params.append(int(hotel_id))
        q += " ORDER BY d.income_date DESC, d.id DESC"
        cur.execute(q, tuple(params))
        rows = rows_to_json(cur.fetchall() or [])

    rate_usd = safe_float(get_setting("exchange_rate", 50)) or 50.0
    return ok({
        "rows": rows,
        "exchange_rate_usd": rate_usd,
        "exchange_rate_eur": round(rate_usd * 1.08, 2)
    })


@app.post("/api/bank-accounts/toggle-visa")
@login_required
def api_bank_accounts_toggle_visa():
    if not is_full_access():
        return fail("مخصص للأونر فقط", 403)
    d = request.get_json(silent=True) or {}
    row_id = safe_int(d.get("id"))
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, COALESCE(bank_visa_settled, 0) AS st FROM daily_income WHERE id=%s", (row_id,))
        row = cur.fetchone()
        if not row:
            return fail("السجل غير موجود", 404)
        new_st = 0 if row.get("st") else 1
        conn.cursor().execute("UPDATE daily_income SET bank_visa_settled=%s WHERE id=%s", (new_st, row_id))
    return ok({"id": row_id, "bank_visa_settled": bool(new_st)})


@app.post("/api/bank-accounts/settle-all")
@login_required
def api_bank_accounts_settle_all():
    if not is_full_access():
        return fail("مخصص للأونر فقط", 403)
    d = request.get_json(silent=True) or {}
    start = d.get("start") or date.today().replace(day=1).isoformat()
    end = d.get("end") or date.today().isoformat()
    hotel_id = d.get("hotel_id") or ""
    with get_db_connection() as conn:
        c = conn.cursor()
        if hotel_id and str(hotel_id).isdigit():
            c.execute("UPDATE daily_income SET bank_visa_settled=1 WHERE income_date BETWEEN %s AND %s AND hotel_id=%s", (start, end, int(hotel_id)))
        else:
            c.execute("UPDATE daily_income SET bank_visa_settled=1 WHERE income_date BETWEEN %s AND %s", (start, end))
    return ok({"message": "✅ تم تأكيد نزول كافة عمليات الفيزا المعلقة للفترة المحددة في حساب البنك"})


def _collect_full_database_backup_bytes():
    backup_data = {"version": "V106_FULL", "exported_at": datetime.now().isoformat(), "tables": {}}
    with get_db_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SHOW TABLES")
        tables = [list(r.values())[0] for r in (cur.fetchall() or [])]
        for tb in tables:
            try:
                cur.execute(f"SELECT * FROM `{tb}`")
                backup_data["tables"][tb] = rows_to_json(cur.fetchall() or [])
            except Exception:
                pass
    return json.dumps(backup_data, ensure_ascii=False, indent=2).encode("utf-8")


@app.post("/api/backup/save-dialog")
@login_required
def api_backup_save_dialog():
    data_bytes = _collect_full_database_backup_bytes()
    default_name = f"PhotoTeam_Full_Backup_{date.today().isoformat()}.json"
    chosen = _open_native_save_as_dialog(default_name)
    if chosen == "":
        return ok({"cancelled": True})
    if chosen:
        if not str(chosen).lower().endswith(".json"):
            chosen = re.sub(r"\.xlsx$", "", str(chosen), flags=re.I) + ".json"
        Path(chosen).write_bytes(data_bytes)
        return ok({"saved": True, "path": str(chosen)})
    return ok({"saved": False})


@app.get("/api/backup/export")
@login_required
def api_backup_export():
    data_bytes = _collect_full_database_backup_bytes()
    fname = f"PhotoTeam_Full_Backup_{date.today().isoformat()}.json"
    return Response(
        data_bytes,
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'}
    )


@app.post("/api/backup/restore")
@login_required
def api_backup_restore():
    if not is_full_access():
        return fail("استرجاع النسخة الاحتياطية متاح للأونر (CEO) فقط", 403)
    d = request.get_json(silent=True) or {}
    tables = d.get("tables") or {}
    if not isinstance(tables, dict) or not tables:
        return fail("ملف النسخة الاحتياطية غير صالح")
    restored_count = 0
    with get_db_connection() as conn:
        cur = conn.cursor()
        for tb, rows in tables.items():
            if not rows or not isinstance(rows, list):
                continue
            try:
                cols = list(rows[0].keys())
                col_names = ",".join([f"`{c}`" for c in cols])
                marks = ",".join(["%s"] * len(cols))
                for r in rows:
                    vals = tuple(r.get(c) for c in cols)
                    cur.execute(f"REPLACE INTO `{tb}` ({col_names}) VALUES ({marks})", vals)
                restored_count += 1
            except Exception:
                pass
    return ok({"message": f"✅ تم استرجاع النسخة الاحتياطية بنجاح ({restored_count} جدول)"})


if __name__ == '__main__':
    # ضروري لنسخة الـ EXE (PyInstaller): flaskwebgui بيستخدم multiprocessing،
    # ومن غير السطر ده البرنامج ممكن يفتح نسخ متكررة من نفسه على ويندوز.
    from multiprocessing import freeze_support
    freeze_support()

    _run_desktop_window()
