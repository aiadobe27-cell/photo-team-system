# =============================================================================
# 📌 ملف قاعدة البيانات (database.py):
# - DB_CONFIG: إعدادات الاتصال بقاعدة البيانات (الاسم، المستخدم، كلمة السر)
# - _ensure_core_tables: جداول الفنادق، الموظفين، الحجوزات، العرابين، والدخل اليومي
# - _ensure_support_tables: جداول الخزنة (treasury_transactions)، الشات (internal_chat_messages)، ملاحظات الدخل (daily_income_notes)، والعمولات
# =============================================================================
import os
from contextlib import contextmanager

import mysql.connector
from mysql.connector import Error

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


# يمكن تغيير بيانات الاتصال بدون تعديل الكود عن طريق Environment Variables.
DB_CONFIG = {
    "host": os.getenv("PHOTOTEAM_DB_HOST", "localhost"),
    "port": int(os.getenv("PHOTOTEAM_DB_PORT", "3306")),
    "database": os.getenv("PHOTOTEAM_DB_NAME", "phototeam"),
    "user": os.getenv("PHOTOTEAM_DB_USER", "phototeam"),
    "password": os.getenv("PHOTOTEAM_DB_PASSWORD", "1234"),
    "charset": "utf8mb4",
    "use_unicode": True,
}


def _server_config():
    cfg = dict(DB_CONFIG)
    cfg.pop("database", None)
    return cfg


def ensure_database_exists():
    """إنشاء قاعدة البيانات نفسها إذا لم تكن موجودة."""
    conn = None
    try:
        conn = mysql.connector.connect(**_server_config())
        cur = conn.cursor()
        db_name = DB_CONFIG["database"].replace("`", "")
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        conn.commit()
        cur.close()
    finally:
        if conn and conn.is_connected():
            conn.close()


_DB_POOL = None

def _get_pooled_or_direct_connection():
    global _DB_POOL
    if _DB_POOL is None:
        try:
            from mysql.connector import pooling
            _DB_POOL = pooling.MySQLConnectionPool(
                pool_name="phototeam_pool",
                pool_size=16,
                pool_reset_session=True,
                **DB_CONFIG,
            )
        except Exception:
            _DB_POOL = False
    if _DB_POOL:
        try:
            return _DB_POOL.get_connection()
        except Exception:
            pass
    return mysql.connector.connect(**DB_CONFIG)


@contextmanager
def get_db_connection():
    """اتصال MySQL سريع وآمن عبر Connection Pool مع Commit/Rollback وإغلاق تلقائي."""
    connection = None
    try:
        try:
            connection = _get_pooled_or_direct_connection()
        except Error as exc:
            # 1049 = Unknown database
            if getattr(exc, "errno", None) == 1049:
                ensure_database_exists()
                connection = _get_pooled_or_direct_connection()
            else:
                raise

        if not connection.is_connected():
            raise RuntimeError("تعذر فتح اتصال بقاعدة البيانات")

        yield connection
        connection.commit()
    except Exception:
        if connection and connection.is_connected():
            connection.rollback()
        raise
    finally:
        if connection and connection.is_connected():
            connection.close()


def _column_exists(cursor, table_name, column_name):
    cursor.execute(f"SHOW COLUMNS FROM `{table_name}` LIKE %s", (column_name,))
    return cursor.fetchone() is not None


def _ensure_column(cursor, table_name, column_name, definition):
    if not _column_exists(cursor, table_name, column_name):
        cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` {definition}")
        return True
    return False


def _table_exists(cursor, table_name):
    cursor.execute("SHOW TABLES LIKE %s", (table_name,))
    return cursor.fetchone() is not None


def _ensure_core_tables(cursor):
    """الجداول التي تعتمد عليها كل شاشات النظام."""
    statements = [
        """
        CREATE TABLE IF NOT EXISTS hotels (
            id INT AUTO_INCREMENT PRIMARY KEY,
            hotel_name VARCHAR(150) NOT NULL,
            parent_hotel_id INT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS team_members (
            id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(150) NOT NULL,
            nickname VARCHAR(100) NOT NULL,
            role VARCHAR(50) NOT NULL,
            commission_rate DECIMAL(5,2) DEFAULT 0.00,
            national_id VARCHAR(50),
            visa_card_number VARCHAR(50),
            base_salary DECIMAL(10,2) DEFAULT 0.00,
            hotel_id INT,
            username VARCHAR(50) UNIQUE,
            password_hash VARCHAR(255),
            is_active BOOLEAN DEFAULT 1,
            access_type VARCHAR(100) DEFAULT 'وصول كامل (Desktop + Mobile)',
            phone_number VARCHAR(20) DEFAULT NULL,
            last_login DATETIME DEFAULT NULL,
            session_active INT DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            hotel VARCHAR(150) DEFAULT 'الفندق الرئيسي',
            booking_date DATE DEFAULT NULL,
            nationality VARCHAR(50),
            room_number VARCHAR(50) NOT NULL,
            phone_number VARCHAR(50) DEFAULT '',
            booking_time VARCHAR(50),
            session_details TEXT,
            clothing LONGTEXT,
            deposit_usd DECIMAL(12,2) DEFAULT 0.00,
            deposit_eur DECIMAL(12,2) DEFAULT 0.00,
            deposit_le_cash DECIMAL(12,2) DEFAULT 0.00,
            deposit_le_visa DECIMAL(12,2) DEFAULT 0.00,
            total_agreement DECIMAL(12,2) DEFAULT 0.00,
            remaining DECIMAL(12,2) DEFAULT 0.00,
            sales_person VARCHAR(100),
            photographer VARCHAR(255),
            photographer_id INT DEFAULT NULL,
            status VARCHAR(50) DEFAULT 'انتظار',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_bookings_date (booking_date),
            INDEX idx_bookings_room (room_number),
            INDEX idx_bookings_hotel (hotel),
            INDEX idx_bookings_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS deposits (
            id INT AUTO_INCREMENT PRIMARY KEY,
            booking_id INT DEFAULT NULL,
            hotel_id INT DEFAULT NULL,
            room_number VARCHAR(50) NOT NULL,
            deposit_sales_person VARCHAR(100),
            deposit_usd DECIMAL(12,2) DEFAULT 0.00,
            deposit_eur DECIMAL(12,2) DEFAULT 0.00,
            deposit_le_visa DECIMAL(12,2) DEFAULT 0.00,
            deposit_le_cash DECIMAL(12,2) DEFAULT 0.00,
            deposit_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_deposits_room (room_number),
            INDEX idx_deposits_date (deposit_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS daily_income (
            id INT AUTO_INCREMENT PRIMARY KEY,
            hotel_id INT NOT NULL DEFAULT 1,
            booking_id INT DEFAULT NULL,
            room_number VARCHAR(50),
            sales_person VARCHAR(100),
            photographer VARCHAR(255),
            deposit_usd DECIMAL(12,2) DEFAULT 0.00,
            deposit_eur DECIMAL(12,2) DEFAULT 0.00,
            deposit_le_visa DECIMAL(12,2) DEFAULT 0.00,
            deposit_le_cash DECIMAL(12,2) DEFAULT 0.00,
            income_usd DECIMAL(12,2) DEFAULT 0.00,
            income_eur DECIMAL(12,2) DEFAULT 0.00,
            income_le_m DECIMAL(12,2) DEFAULT 0.00,
            income_le_k DECIMAL(12,2) DEFAULT 0.00,
            le_to_usd DECIMAL(12,4) DEFAULT 0.00,
            order_exchange_rate DECIMAL(12,4) DEFAULT 0.00,
            deposit_applied DECIMAL(12,2) DEFAULT 0.00,
            daily_total DECIMAL(12,2) DEFAULT 0.00,
            cost_dress DECIMAL(12,2) DEFAULT 0.00,
            cost_usb DECIMAL(12,2) DEFAULT 0.00,
            cost_album DECIMAL(12,2) DEFAULT 0.00,
            cost_total DECIMAL(12,2) DEFAULT 0.00,
            income_date DATE DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_income_date (income_date),
            INDEX idx_income_hotel (hotel_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS dress_inventory (
            id INT AUTO_INCREMENT PRIMARY KEY,
            hotel_id INT NOT NULL DEFAULT 1,
            dress_type VARCHAR(50) NOT NULL,
            custom_type_name VARCHAR(100),
            color VARCHAR(50) DEFAULT '-',
            size_category VARCHAR(50) DEFAULT 'صغير',
            quantity INT NOT NULL DEFAULT 1,
            status VARCHAR(100) DEFAULT 'متاح',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS equipment_inventory (
            id INT AUTO_INCREMENT PRIMARY KEY,
            hotel_id INT NOT NULL DEFAULT 1,
            equipment_type VARCHAR(50) NOT NULL,
            brand VARCHAR(50) DEFAULT '',
            model_name VARCHAR(100) NOT NULL,
            serial_number VARCHAR(100) DEFAULT '-',
            photo_path VARCHAR(255) DEFAULT '',
            quantity INT NOT NULL DEFAULT 1,
            status VARCHAR(100) DEFAULT 'متاح',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS laundry_tracker (
            id INT AUTO_INCREMENT PRIMARY KEY,
            hotel_id INT NOT NULL DEFAULT 1,
            log_date DATE NOT NULL,
            dress_count INT NOT NULL DEFAULT 0,
            galabeya_count INT NOT NULL DEFAULT 0,
            dress_cleaning_price DECIMAL(10,2) DEFAULT 50.00,
            galabeya_cleaning_price DECIMAL(10,2) DEFAULT 30.00,
            total_cost DECIMAL(10,2) DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_laundry_date (log_date),
            INDEX idx_laundry_hotel (hotel_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS system_settings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            setting_key VARCHAR(100) UNIQUE NOT NULL,
            setting_value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS user_hotel_permissions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            hotel_id INT NOT NULL,
            can_view BOOLEAN DEFAULT 1,
            can_edit BOOLEAN DEFAULT 0,
            UNIQUE KEY uq_user_hotel (user_id, hotel_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS employee_permissions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            permission_key VARCHAR(100) NOT NULL,
            UNIQUE KEY uq_employee_permission (user_id, permission_key)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS roles (
            id INT AUTO_INCREMENT PRIMARY KEY,
            role_key VARCHAR(50) NOT NULL UNIQUE,
            role_name VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS employee_roles (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            role_id INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_employee_role (user_id, role_id),
            INDEX idx_employee_roles_user (user_id),
            INDEX idx_employee_roles_role (role_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    ]

    for statement in statements:
        cursor.execute(statement)


def _ensure_support_tables(cursor):
    """جداول الشاشات المالية والعمولات والأصول والمغسلة والتقارير."""
    statements = [
        """
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
        """,
        """
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
        """,
        """
        CREATE TABLE IF NOT EXISTS internal_chat_messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            channel VARCHAR(20) NOT NULL DEFAULT 'team',
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
        """,
        """
        CREATE TABLE IF NOT EXISTS treasury_transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tx_date DATE NOT NULL,
            tx_month VARCHAR(7) NOT NULL,
            tx_type VARCHAR(15) NOT NULL DEFAULT 'EXPENSE',
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
        """,
        """
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
        """,
        """
        CREATE TABLE IF NOT EXISTS system_notifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(100) NOT NULL,
            message TEXT NOT NULL,
            status VARCHAR(20) DEFAULT 'Pending',
            related_sales_person VARCHAR(100),
            amount DECIMAL(12,2) DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS employee_transfers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id INT NOT NULL,
            from_hotel_id INT,
            to_hotel_id INT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS currency_rates (
            id INT AUTO_INCREMENT PRIMARY KEY,
            rate_date DATE UNIQUE NOT NULL,
            egp_to_usd DECIMAL(12,4) NOT NULL,
            egp_to_eur DECIMAL(12,4) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS booking_dresses (
            id INT AUTO_INCREMENT PRIMARY KEY,
            booking_id INT NOT NULL,
            dress_type VARCHAR(50),
            custom_name VARCHAR(100),
            color VARCHAR(50),
            size_category VARCHAR(50),
            quantity INT DEFAULT 1
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS commissions_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id INT NOT NULL,
            booking_id INT,
            role_type VARCHAR(20) NOT NULL,
            gross_amount DECIMAL(12,2) DEFAULT 0.00,
            cost_deducted DECIMAL(12,2) DEFAULT 0.00,
            net_amount DECIMAL(12,2) DEFAULT 0.00,
            commission_rate DECIMAL(5,2) DEFAULT 0.00,
            commission_amount_usd DECIMAL(12,2) DEFAULT 0.00,
            exchange_rate DECIMAL(12,4) DEFAULT 1.0000,
            commission_amount_egp DECIMAL(12,2) DEFAULT 0.00,
            calculation_date DATE DEFAULT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS bonus_records (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id INT NOT NULL,
            target_amount DECIMAL(12,2) NOT NULL,
            achieved_amount DECIMAL(12,2) NOT NULL,
            bonus_amount_egp DECIMAL(12,2) NOT NULL,
            month_year VARCHAR(7) NOT NULL,
            status VARCHAR(20) DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS bank_payroll_exports (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id INT NOT NULL,
            full_name VARCHAR(150) NOT NULL,
            bodaga_code VARCHAR(50),
            visa_card_number VARCHAR(50) NOT NULL,
            total_commission_egp DECIMAL(12,2) DEFAULT 0.00,
            bonus_egp DECIMAL(12,2) DEFAULT 0.00,
            deductions_egp DECIMAL(12,2) DEFAULT 0.00,
            net_salary_egp DECIMAL(12,2) NOT NULL,
            period_start DATE NOT NULL,
            period_end DATE NOT NULL,
            hotel_id INT,
            exported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS booking_costs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            booking_id INT NOT NULL,
            cost_dress DECIMAL(12,2) DEFAULT 0.00,
            cost_usb DECIMAL(12,2) DEFAULT 0.00,
            cost_album DECIMAL(12,2) DEFAULT 0.00,
            cost_total DECIMAL(12,2) DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS laundry_details (
            id INT AUTO_INCREMENT PRIMARY KEY,
            booking_id INT NOT NULL,
            dress_count INT DEFAULT 0,
            galabeya_count INT DEFAULT 0,
            transferred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS system_audit_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            action_type VARCHAR(50) NOT NULL,
            affected_table VARCHAR(50) NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS inventory_transfers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            item_type VARCHAR(20) NOT NULL,
            item_id INT NOT NULL,
            from_hotel_id INT NOT NULL,
            to_hotel_id INT NOT NULL,
            transferred_by VARCHAR(100),
            transfer_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(20) DEFAULT 'Completed'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS maintenance_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            item_type VARCHAR(20) NOT NULL,
            item_id INT NOT NULL,
            issue_description TEXT,
            cost DECIMAL(12,2) DEFAULT 0.00,
            sent_date DATE NOT NULL,
            return_date DATE,
            status VARCHAR(50) DEFAULT 'In Maintenance'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS order_cancellations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            booking_id INT NOT NULL,
            room_number VARCHAR(50),
            refund_amount DECIMAL(12,2) NOT NULL,
            currency VARCHAR(10) DEFAULT 'USD',
            reason TEXT,
            cancelled_by VARCHAR(100),
            cancellation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS bonus_targets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            role VARCHAR(50) NOT NULL,
            target_threshold DECIMAL(12,2) NOT NULL,
            bonus_reward_egp DECIMAL(12,2) NOT NULL,
            is_active BOOLEAN DEFAULT 1
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS employee_deductions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_name VARCHAR(100) NOT NULL,
            deduction_date DATE NOT NULL,
            amount_egp DECIMAL(12,2) NOT NULL,
            type VARCHAR(50) DEFAULT 'خصم / جزاء إداري',
            reason VARCHAR(255)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS closures_master (
            id INT AUTO_INCREMENT PRIMARY KEY,
            hotel_id VARCHAR(50) DEFAULT 'الكل',
            role_type VARCHAR(50) NOT NULL,
            employee_name VARCHAR(100) NOT NULL,
            month_str VARCHAR(10) NOT NULL,
            period_text VARCHAR(100) NOT NULL,
            total_usd DECIMAL(12,2) NOT NULL,
            total_egp DECIMAL(12,2) NOT NULL,
            closure_date DATETIME NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS archive_closure_details (
            id INT AUTO_INCREMENT PRIMARY KEY,
            closure_id INT,
            role_type VARCHAR(50) NOT NULL,
            employee_name VARCHAR(100) NOT NULL,
            period_text VARCHAR(100) NOT NULL,
            record_date VARCHAR(50) NOT NULL,
            item_name VARCHAR(255) NOT NULL,
            amount_usd DECIMAL(12,2) DEFAULT 0.00,
            amount_egp DECIMAL(12,2) DEFAULT 0.00,
            closure_timestamp DATETIME NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS salaries_paid_archive (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_name VARCHAR(100) NOT NULL,
            month_str VARCHAR(10) NOT NULL,
            period_text VARCHAR(100) NOT NULL,
            net_amount_egp DECIMAL(12,2) NOT NULL,
            paid_date DATETIME NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS employee_bonuses (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_name VARCHAR(100) NOT NULL,
            bonus_date DATE NOT NULL,
            amount_egp DECIMAL(12,2) NOT NULL,
            reason VARCHAR(255)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS system_audit_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_role VARCHAR(50),
            action_type VARCHAR(100),
            description TEXT,
            log_time DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            log_id INT AUTO_INCREMENT PRIMARY KEY,
            hotel_id INT NOT NULL DEFAULT 1,
            user_name VARCHAR(100) NOT NULL,
            action_type VARCHAR(50) NOT NULL,
            details TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS coin_safe_transactions (
            transaction_id INT AUTO_INCREMENT PRIMARY KEY,
            hotel_id INT NOT NULL DEFAULT 1,
            user_id INT NOT NULL DEFAULT 1,
            user_name VARCHAR(100) NOT NULL,
            transaction_type ENUM('IN','OUT') NOT NULL DEFAULT 'IN',
            amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS daily_income_adjustments (
            adjustment_id INT AUTO_INCREMENT PRIMARY KEY,
            hotel_id INT NOT NULL DEFAULT 1,
            transaction_id INT NOT NULL,
            adjustment_date DATE NOT NULL,
            impact_amount DECIMAL(12,2) NOT NULL,
            reason VARCHAR(255) NOT NULL,
            created_by VARCHAR(100) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS asset_maintenance_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            hotel_id INT NOT NULL DEFAULT 1,
            asset_type VARCHAR(50) NOT NULL,
            asset_id INT NOT NULL,
            item_description VARCHAR(200) NOT NULL,
            issue_reason VARCHAR(255) NOT NULL,
            repair_center VARCHAR(150) DEFAULT 'صيانة داخلية',
            repair_cost DECIMAL(12,2) DEFAULT 0.00,
            sent_date VARCHAR(50) NOT NULL,
            return_date VARCHAR(50) DEFAULT 'قيد الصيانة',
            status VARCHAR(50) DEFAULT 'قيد الصيانة',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS asset_incident_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            hotel_id INT NOT NULL DEFAULT 1,
            asset_type VARCHAR(50) NOT NULL,
            asset_id INT NOT NULL,
            item_description VARCHAR(200) NOT NULL,
            responsible_person VARCHAR(100) NOT NULL,
            damage_description VARCHAR(255) NOT NULL,
            estimated_damage_cost DECIMAL(12,2) DEFAULT 0.00,
            incident_date VARCHAR(50) NOT NULL,
            photo_path VARCHAR(255) DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    ]

    for statement in statements:
        cursor.execute(statement)


def _migrate_existing_schema(cursor):
    """تحديث قواعد البيانات القديمة بدون حذف بيانات المستخدم."""
    # bookings: توحيد أسماء الأعمدة المستخدمة حالياً في ReservationWindow.
    booking_columns = {
        "hotel": "VARCHAR(150) DEFAULT 'الفندق الرئيسي'",
        "booking_date": "DATE DEFAULT NULL",
        "phone_number": "VARCHAR(50) DEFAULT ''",
        "clothing": "LONGTEXT",
        "deposit_le_cash": "DECIMAL(12,2) DEFAULT 0.00",
        "deposit_le_visa": "DECIMAL(12,2) DEFAULT 0.00",
        "total_agreement": "DECIMAL(12,2) DEFAULT 0.00",
        "remaining": "DECIMAL(12,2) DEFAULT 0.00",
        "status": "VARCHAR(50) DEFAULT 'انتظار'",
        "photographer_id": "INT DEFAULT NULL",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    }
    for name, definition in booking_columns.items():
        _ensure_column(cursor, "bookings", name, definition)

    # نسخ البيانات القديمة إلى الأسماء الجديدة عند وجود الأعمدة القديمة.
    legacy_pairs = [
        ("dress_rent", "clothing", "(`clothing` IS NULL OR `clothing` = '')"),
        ("deposit_egp", "deposit_le_cash", "(`deposit_le_cash` IS NULL OR `deposit_le_cash` = 0)"),
        ("total_agreed", "total_agreement", "(`total_agreement` IS NULL OR `total_agreement` = 0)"),
        ("remaining_amount", "remaining", "(`remaining` IS NULL OR `remaining` = 0)"),
        ("booking_status", "status", "(`status` IS NULL OR `status` = '' OR `status` = 'انتظار')"),
    ]
    for old_col, new_col, empty_condition in legacy_pairs:
        if _column_exists(cursor, "bookings", old_col):
            cursor.execute(
                f"UPDATE bookings SET `{new_col}` = `{old_col}` "
                f"WHERE {empty_condition} AND `{old_col}` IS NOT NULL"
            )

    if _column_exists(cursor, "bookings", "created_at"):
        cursor.execute(
            "UPDATE bookings SET booking_date = DATE(created_at) "
            "WHERE booking_date IS NULL AND created_at IS NOT NULL"
        )

    # daily_income: بعض النسخ القديمة لا تحتوي hotel_id/created_at.
    daily_columns = {
        "hotel_id": "INT NOT NULL DEFAULT 1",
        "booking_id": "INT DEFAULT NULL",
        "room_number": "VARCHAR(50)",
        "photographer": "VARCHAR(255)",
        "deposit_usd": "DECIMAL(12,2) DEFAULT 0.00",
        "deposit_eur": "DECIMAL(12,2) DEFAULT 0.00",
        "deposit_le_visa": "DECIMAL(12,2) DEFAULT 0.00",
        "deposit_le_cash": "DECIMAL(12,2) DEFAULT 0.00",
        "order_exchange_rate": "DECIMAL(12,4) DEFAULT 0.00",
        "bank_visa_settled": "TINYINT(1) DEFAULT 0",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    }
    for name, definition in daily_columns.items():
        _ensure_column(cursor, "daily_income", name, definition)

    # بقية الأعمدة التي تضيفها الشاشات عند الحاجة.
    team_columns = {
        "base_salary": "DECIMAL(10,2) DEFAULT 0.00",
        "access_type": "VARCHAR(100) DEFAULT 'وصول كامل (Desktop + Mobile)'",
        "phone_number": "VARCHAR(20) DEFAULT NULL",
        "last_login": "DATETIME DEFAULT NULL",
        "session_active": "INT DEFAULT 1",
    }
    for name, definition in team_columns.items():
        _ensure_column(cursor, "team_members", name, definition)

    dress_columns = {
        "hotel_id": "INT NOT NULL DEFAULT 1",
        "custom_type_name": "VARCHAR(100) DEFAULT NULL",
    }
    for name, definition in dress_columns.items():
        _ensure_column(cursor, "dress_inventory", name, definition)

    equipment_columns = {
        "hotel_id": "INT NOT NULL DEFAULT 1",
        "serial_number": "VARCHAR(100) DEFAULT '-'",
        "photo_path": "VARCHAR(255) DEFAULT ''",
    }
    for name, definition in equipment_columns.items():
        _ensure_column(cursor, "equipment_inventory", name, definition)

    _ensure_column(cursor, "laundry_tracker", "hotel_id", "INT NOT NULL DEFAULT 1")
    _ensure_column(cursor, "employee_deductions", "type", "VARCHAR(50) DEFAULT 'خصم / جزاء إداري'")
    _ensure_column(cursor, "closures_master", "hotel_id", "VARCHAR(50) DEFAULT 'الكل'")
    _ensure_column(cursor, "archive_closure_details", "closure_id", "INT DEFAULT NULL")



def _ensure_ultra_tables(cursor):
    """جداول/أعمدة نسخة الويب الاحترافية مع الحفاظ على توافق البرنامج القديم."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS booking_activity (
            id INT AUTO_INCREMENT PRIMARY KEY,
            booking_id INT NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            title VARCHAR(150) NOT NULL,
            details TEXT,
            user_id INT DEFAULT NULL,
            event_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_booking_activity_booking (booking_id),
            INDEX idx_booking_activity_time (event_time)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generated_reports (
            id INT AUTO_INCREMENT PRIMARY KEY,
            report_type VARCHAR(80) NOT NULL,
            period_start DATE DEFAULT NULL,
            period_end DATE DEFAULT NULL,
            hotel_id INT DEFAULT NULL,
            generated_by INT DEFAULT NULL,
            details TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # أعمدة تستخدمها الشاشات القديمة والجديدة معاً.
    for name, definition in {
        "booking_id": "INT DEFAULT NULL",
        "hotel_id": "INT DEFAULT NULL",
    }.items():
        _ensure_column(cursor, "deposits", name, definition)

    for name, definition in {
        "le_to_usd": "DECIMAL(12,4) DEFAULT 0.00",
        "deposit_applied": "DECIMAL(12,2) DEFAULT 0.00",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    }.items():
        _ensure_column(cursor, "daily_income", name, definition)

    for name, definition in {
        "national_id": "VARCHAR(50) DEFAULT NULL",
        "visa_card_number": "VARCHAR(50) DEFAULT NULL",
        "branch_code": "VARCHAR(50) DEFAULT NULL",
        "nbe_type": "VARCHAR(50) DEFAULT 'ON US بطاقات'",
        "sheet_nickname": "VARCHAR(100) DEFAULT NULL",
    }.items():
        _ensure_column(cursor, "team_members", name, definition)

    # ========================= BOOM / Operations OS =========================
    # Workflow منفصل حتى يظل status القديم متوافقاً مع البرنامج الأصلي.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS booking_workflow (
            id INT AUTO_INCREMENT PRIMARY KEY,
            booking_id INT NOT NULL,
            stage_key VARCHAR(50) NOT NULL,
            stage_label VARCHAR(100) NOT NULL,
            stage_status VARCHAR(30) DEFAULT 'pending',
            notes TEXT,
            started_at DATETIME DEFAULT NULL,
            completed_at DATETIME DEFAULT NULL,
            updated_by INT DEFAULT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_booking_stage (booking_id, stage_key),
            INDEX idx_workflow_booking (booking_id),
            INDEX idx_workflow_status (stage_status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS booking_checklist (
            id INT AUTO_INCREMENT PRIMARY KEY,
            booking_id INT NOT NULL,
            item_key VARCHAR(80) NOT NULL,
            item_label VARCHAR(160) NOT NULL,
            is_done BOOLEAN DEFAULT 0,
            completed_by INT DEFAULT NULL,
            completed_at DATETIME DEFAULT NULL,
            notes VARCHAR(255) DEFAULT '',
            UNIQUE KEY uq_booking_check (booking_id, item_key),
            INDEX idx_check_booking (booking_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operations_tasks (
            id INT AUTO_INCREMENT PRIMARY KEY,
            hotel_id INT DEFAULT NULL,
            booking_id INT DEFAULT NULL,
            task_type VARCHAR(60) DEFAULT 'general',
            priority VARCHAR(20) DEFAULT 'normal',
            title VARCHAR(180) NOT NULL,
            details TEXT,
            assigned_to INT DEFAULT NULL,
            due_at DATETIME DEFAULT NULL,
            status VARCHAR(30) DEFAULT 'open',
            created_by INT DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME DEFAULT NULL,
            INDEX idx_tasks_status (status),
            INDEX idx_tasks_due (due_at),
            INDEX idx_tasks_hotel (hotel_id),
            INDEX idx_tasks_booking (booking_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shift_handover_notes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            hotel_id INT DEFAULT NULL,
            shift_date DATE NOT NULL,
            shift_name VARCHAR(50) DEFAULT 'عام',
            note TEXT NOT NULL,
            priority VARCHAR(20) DEFAULT 'normal',
            created_by INT DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            resolved_at DATETIME DEFAULT NULL,
            INDEX idx_handover_date (shift_date),
            INDEX idx_handover_hotel (hotel_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_followups (
            id INT AUTO_INCREMENT PRIMARY KEY,
            booking_id INT NOT NULL,
            followup_type VARCHAR(50) NOT NULL,
            status VARCHAR(30) DEFAULT 'pending',
            scheduled_at DATETIME DEFAULT NULL,
            sent_at DATETIME DEFAULT NULL,
            channel VARCHAR(30) DEFAULT 'whatsapp',
            message TEXT,
            created_by INT DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_follow_booking (booking_id),
            INDEX idx_follow_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hotel_closing_sessions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            hotel_id INT NOT NULL,
            closing_date DATE NOT NULL,
            expected_usd DECIMAL(12,2) DEFAULT 0,
            expected_eur DECIMAL(12,2) DEFAULT 0,
            expected_egp_cash DECIMAL(12,2) DEFAULT 0,
            expected_egp_visa DECIMAL(12,2) DEFAULT 0,
            actual_usd DECIMAL(12,2) DEFAULT 0,
            actual_eur DECIMAL(12,2) DEFAULT 0,
            actual_egp_cash DECIMAL(12,2) DEFAULT 0,
            actual_egp_visa DECIMAL(12,2) DEFAULT 0,
            variance_note TEXT,
            status VARCHAR(30) DEFAULT 'open',
            closed_by INT DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            closed_at DATETIME DEFAULT NULL,
            UNIQUE KEY uq_hotel_closing (hotel_id, closing_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory_transfer_requests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            asset_type VARCHAR(30) NOT NULL,
            asset_id INT NOT NULL,
            from_hotel_id INT NOT NULL,
            to_hotel_id INT NOT NULL,
            quantity INT DEFAULT 1,
            reason VARCHAR(255) DEFAULT '',
            status VARCHAR(30) DEFAULT 'completed',
            requested_by INT DEFAULT NULL,
            approved_by INT DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME DEFAULT NULL,
            INDEX idx_transfer_asset (asset_type, asset_id),
            INDEX idx_transfer_hotels (from_hotel_id, to_hotel_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)



def _seed_nbe_roster_employees(cursor):
    """حذف الـ 52 موظفاً الذين تمت إضافتهم مؤخراً من شيت البنك والإبقاء على الموظفين القدامى فقط."""
    try:
        cursor.execute("DELETE FROM team_members WHERE username LIKE 'nbe_%'")
        nids = ['30111053100156', '30406192701679', '30107102701635', '28710182703152', '30109262701316', '28401282800195', '29906121301251', '29909182702991', '29806150400353', '30211112700558', '30012251700659', '29410272701515', '30307042500413', '30507063100155', '29809152107431', '29901172600278', '30207012700715', '30411143100132', '27010090201074', '28311252800591', '29604223100033', '28401068800412', '30102221701099', '28701152107131', '30210012709756', '29910121500332', '30201012411251', '28801040101495', '30509033100277', '29509012706714', '30612170400135', '30207012700731', '30807202608278', '29807281700332', '29612212701615', '29609182700391', '30003041202312', '29909013100273', '29906061600912', '30611080400318', '29204281701375', '28912102703876', '30304142702014', '30011022700517', '28105308800719', '30006222701352', '27206022700072', '30305242700198', '27506171100391', '30812012714792', '29904101602457', '28807302801092']
        if nids:
            marks = ",".join(["%s"] * len(nids))
            cursor.execute(f"DELETE FROM team_members WHERE national_id IN ({marks})", tuple(nids))
    except Exception:
        pass


def _seed_defaults(cursor):
    role_rows = [
        ("CEO", "CEO / مدير عام"),
        ("Manager", "Manager / مدير"),
        ("Photographer", "Photographer / مصور"),
        ("Sales", "Sales / مبيعات"),
        ("Accountant", "Accountant / حسابات"),
        ("Reviewer", "Reviewer / مراجعة"),
    ]
    for role_key, role_name in role_rows:
        cursor.execute(
            "INSERT INTO roles (role_key,role_name) VALUES (%s,%s) "
            "ON DUPLICATE KEY UPDATE role_name=VALUES(role_name)",
            (role_key, role_name),
        )

    # Keep every legacy employee role while enabling additional roles.
    aliases = {
        "ceo":"CEO","admin":"CEO","administrator":"CEO","owner":"CEO","مدير عام":"CEO","المدير العام":"CEO",
        "manager":"Manager","hotel_manager":"Manager","مدير":"Manager","مدير فندق":"Manager",
        "photographer":"Photographer","مصور":"Photographer",
        "sales":"Sales","سيلز":"Sales","مبيعات":"Sales",
        "accountant":"Accountant","محاسب":"Accountant","حسابات":"Accountant",
        "reviewer":"Reviewer","مراجع":"Reviewer","مراجعة":"Reviewer",
    }
    cursor.execute("SELECT id,role FROM team_members WHERE role IS NOT NULL AND role<>''")
    for uid, old_role in cursor.fetchall():
        role_key = aliases.get(str(old_role or '').strip().lower())
        if not role_key:
            continue
        cursor.execute("SELECT id FROM roles WHERE role_key=%s LIMIT 1", (role_key,))
        rr = cursor.fetchone()
        if rr:
            cursor.execute("INSERT IGNORE INTO employee_roles (user_id,role_id) VALUES (%s,%s)", (uid, rr[0]))

    cursor.execute("SELECT COUNT(*) FROM hotels")
    row = cursor.fetchone()
    if not row or int(row[0] or 0) == 0:
        cursor.execute("INSERT INTO hotels (hotel_name) VALUES (%s)", ("الفندق الرئيسي",))

    defaults = {
        "exchange_rate": "50.0",
        "sales_bonus_target": "5000",
        "sales_bonus_pct": "2",
        "photo_bonus_target": "5000",
        "photo_bonus_pct": "2",
        "manager_bonus_target": "20000",
        "manager_bonus_pct": "1",
        "hotel_bonus_target": "20000",
        "hotel_bonus_pct": "2",
        "dress_cleaning_price": "50",
        "galabeya_cleaning_price": "30",
        "session_alert_minutes": "60",
        "remaining_alert_usd": "1",
        "auto_followup_enabled": "1",
        "company_display_name": "PHOTO TEAM",
        "company_tagline": "Professional Photography Operations",
        "default_checkout_status": "Delivered",
    }
    for key, value in defaults.items():
        cursor.execute(
            "INSERT INTO system_settings (setting_key, setting_value) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE setting_value = setting_value",
            (key, value),
        )


def init_db():
    """إنشاء/ترقية الهيكل النهائي لقاعدة بيانات PHOTO TEAM بدون حذف البيانات القديمة."""
    ensure_database_exists()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        _ensure_core_tables(cursor)
        _ensure_support_tables(cursor)
        _migrate_existing_schema(cursor)
        _ensure_ultra_tables(cursor)
        _seed_defaults(cursor)
        _seed_nbe_roster_employees(cursor)
        conn.commit()
        cursor.close()
    print("✅ PHOTO TEAM database is ready and migrated successfully.")


if __name__ == "__main__":
    init_db()
