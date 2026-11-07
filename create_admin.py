import getpass
import hashlib
from database import init_db, get_db_connection

def h(p): return hashlib.sha256(p.encode("utf-8")).hexdigest()

if __name__ == "__main__":
    init_db()
    print("إنشاء حساب إدارة PHOTO TEAM")
    full_name = input("الاسم بالكامل [Administrator]: ").strip() or "Administrator"
    nickname = input("اللقب [Admin]: ").strip() or "Admin"
    username = input("اسم المستخدم [admin]: ").strip() or "admin"
    password = getpass.getpass("كلمة المرور: ").strip()
    if not password:
        raise SystemExit("كلمة المرور مطلوبة")
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO team_members
               (full_name,nickname,role,username,password_hash,is_active,access_type)
               VALUES (%s,%s,'CEO',%s,%s,1,'وصول كامل (Desktop + Mobile)')
               ON DUPLICATE KEY UPDATE full_name=VALUES(full_name), nickname=VALUES(nickname),
                 role='CEO', password_hash=VALUES(password_hash), is_active=1""",
            (full_name,nickname,username,h(password))
        )
    print("تم إنشاء/تحديث حساب الإدارة بنجاح.")
