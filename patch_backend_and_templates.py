#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

ROOT = Path("/working_dir/c_0788515bf7bf9bd8/project_src")

# ============================================================================
# 1. PATCH app.py:
#    - Ensure team_members schema columns (phone_number, national_id, visa_card_number, access_type, session_active)
#    - Fix /api/auth/login (support username OR nickname, bcrypt + sha256 + plain)
#    - Fix /api/auth/register (work with 1/2/3+ word names, any phone/national_id, auto-create columns, set default permissions)
#    - Fix /api/auth/reset-password (work even if existing user had empty phone/national_id in DB, plus add /api/auth/change-password for logged-in users)
#    - Fix /api/deposits (LEFT JOIN bookings b ON b.id=d.booking_id and COALESCE(h.hotel_name, b.hotel) AS hotel_name, filter > 0)
#    - Upgrade /api/export/excel to save modern RTL styled Excel (.xls) & (.csv)
# ============================================================================
app_py_path = ROOT / "app.py"
app_code = app_py_path.read_text(encoding="utf-8")

old_auth_block_pattern = re.compile(
    r"# =============================================================================\n"
    r"# 📌 6\. كود تسجيل الدخول وإنشاء حساب جديد وتغيير كلمة السر \(Auth APIs\)\n"
    r"# =============================================================================.*?@app\.post\(\"/api/auth/logout\"\)",
    re.DOTALL
)

new_auth_block = '''# =============================================================================
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
    if not phone_number or len(re.sub(r"\\D", "", phone_number)) < 6:
        return fail("يرجى إدخال رقم هاتف صحيح")
    if not national_id or len(re.sub(r"\\D", "", national_id)) < 4:
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

    clean_phone = re.sub(r"\\D", "", phone_number)
    clean_nid = re.sub(r"\\D", "", national_id)

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
                db_phone = re.sub(r"\\D", "", str(u.get("phone_number") or ""))
                db_nid = re.sub(r"\\D", "", str(u.get("national_id") or ""))
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


@app.post("/api/auth/logout")'''

assert old_auth_block_pattern.search(app_code), "Auth block not found in app.py"
app_code = old_auth_block_pattern.sub(lambda m: new_auth_block, app_code, count=1)

# Now patch api_deposits in app.py so every deposit gets its true hotel_name from hotels OR bookings
old_deposits_block = '''    with get_db_connection() as conn:
        cur=conn.cursor(dictionary=True);cols=table_columns("deposits");date_col="deposit_date" if "deposit_date" in cols else None
        if not date_col:return ok([])
        join=" LEFT JOIN hotels h ON h.id=d.hotel_id" if "hotel_id" in cols else "";hotel_select="h.hotel_name" if "hotel_id" in cols else "NULL AS hotel_name"
        cur.execute(f"SELECT d.*,{hotel_select} FROM deposits d{join} WHERE d.`{date_col}` BETWEEN %s AND %s {w} {search_sql} ORDER BY d.`{date_col}` DESC,d.id DESC",tuple([start,end]+p+search_params));rows=rows_to_json(cur.fetchall())'''

new_deposits_block = '''    with get_db_connection() as conn:
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
        ]'''

assert old_deposits_block in app_code, "old_deposits_block not found in app.py"
app_code = app_code.replace(old_deposits_block, new_deposits_block, 1)

# Also patch api_export_excel in app.py so it supports saving rich HTML-based .xls AND .csv
old_export_block_pattern = re.compile(
    r"@app\.post\(\"/api/export/excel\"\)\n@login_required\ndef api_export_excel\(\):.*?return ok\(\{\n\s*\"filename\": safe_name,\n\s*\"saved_to\": saved_paths\[0\] if saved_paths else safe_name,\n\s*\"rows_count\": len\(rows\)\n\s*\}\)",
    re.DOTALL
)

new_export_block = '''@app.post("/api/export/excel")
@login_required
def api_export_excel():
    """يحفظ ملف Excel المنسق (.xls) وملف (.csv) مباشرة في مجلد Downloads ومجلد exports."""
    d = request.get_json(silent=True) or {}
    raw_name = str(d.get("filename") or f"PhotoTeam_Export_{date.today().isoformat()}.xls").strip()
    base_stem = re.sub(r"\\.(csv|xls|xlsx)$", "", raw_name, flags=re.IGNORECASE)
    safe_stem = re.sub(r"[^\\w\\u0600-\\u06FF\\-]+", "_", base_stem).strip("_") or f"PhotoTeam_Export_{date.today().isoformat()}"
    xls_name = f"{safe_stem}.xls"
    headers = d.get("headers") or []
    rows = d.get("rows") or []
    styled_html = str(d.get("styled_html") or "").strip()

    if styled_html:
        content_bytes = ("\\ufeff" + styled_html).encode("utf-8")
        save_filename = xls_name
    else:
        sio = io.StringIO()
        writer = csv.writer(sio)
        if headers:
            writer.writerow([str(h if h is not None else "") for h in headers])
        for r in rows:
            if isinstance(r, (list, tuple)):
                writer.writerow([str(v if v is not None else "") for v in r])
        content_bytes = ("\\ufeff" + sio.getvalue()).encode("utf-8-sig")
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
    })'''

assert old_export_block_pattern.search(app_code), "api_export_excel not found in app.py"
app_code = old_export_block_pattern.sub(lambda m: new_export_block, app_code, count=1)

app_py_path.write_text(app_code, encoding="utf-8")
print("✅ Patched app.py successfully")
