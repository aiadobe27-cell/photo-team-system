# -*- coding: utf-8 -*-
"""
====================================================================
  📸 PHOTO TEAM SYSTEM — مشغل لينك الموبايلات عبر Ngrok (Port 5000)
====================================================================
- يشغل سيرفر البرنامج على البورت الثابت 5000 لكل الموبايلات (0.0.0.0:5000).
- يبحث عن ngrok.exe أو يثبت pyngrok تلقائياً ويفتح لينك Ngrok العام.
- إذا لم يكن لديك Authtoken في Ngrok بعد، يمكنك لصقه مباشرة في النافذة أو في المتصفح،
  كما يوفر رابطاً سحابياً احتياطياً فورياً بدون حساب عند الحاجة.
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def get_lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def fetch_ngrok_public_url() -> str | None:
    for api_port in (4040, 4041, 4042):
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{api_port}/api/tunnels")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
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


def find_ngrok_binary() -> str | None:
    for candidate in (ROOT / "ngrok.exe", ROOT / "ngrok"):
        if candidate.exists():
            return str(candidate)
    which_bin = shutil.which("ngrok")
    if which_bin:
        return which_bin
    return None


def ensure_pyngrok_installed() -> bool:
    try:
        import pyngrok  # noqa: F401
        return True
    except ImportError:
        print("  ⏳ جاري تجهيز مكتبة pyngrok تلقائياً لأول مرة...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "pyngrok", "--quiet"],
                timeout=90,
                check=False,
            )
            import pyngrok  # noqa: F401
            return True
        except Exception:
            return False


def start_ngrok_tunnel(port: int, authtoken: str = "") -> str | None:
    existing = fetch_ngrok_public_url()
    if existing:
        return existing

    ngrok_bin = find_ngrok_binary()
    if ngrok_bin:
        if authtoken:
            try:
                subprocess.run([ngrok_bin, "config", "add-authtoken", authtoken], capture_output=True, text=True, timeout=10)
            except Exception:
                pass
        try:
            subprocess.Popen(
                [ngrok_bin, "http", str(port)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            for _ in range(25):
                time.sleep(0.4)
                url = fetch_ngrok_public_url()
                if url:
                    return url
        except Exception:
            pass

    if ensure_pyngrok_installed():
        try:
            from pyngrok import ngrok as pyngrok_mod
            if authtoken:
                pyngrok_mod.set_auth_token(authtoken)
            tunnel = pyngrok_mod.connect(port, "http")
            return tunnel.public_url
        except Exception as e:
            err_str = str(e)
            if "authtoken" in err_str.lower() or "authentication" in err_str.lower():
                print("\n  ⚠️ تنبيه من Ngrok: يحتاج Ngrok إلى كود Authtoken مجاني (مرة واحدة فقط).")
                print("  🔗 احصل عليه في ثانية من: https://dashboard.ngrok.com/get-started/your-authtoken")
            else:
                print(f"  ⚠️ تنبيه Ngrok: {e}")
    return fetch_ngrok_public_url()


def main():
    os.environ["PHOTOTEAM_SERVER_ONLY"] = "1"
    from app import app, _free_local_port

    port = _free_local_port(5000)
    lan_ip = get_lan_ip()

    def run_server():
        try:
            from waitress import serve
            serve(app, host="0.0.0.0", port=port, threads=16)
        except Exception:
            app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(1.0)

    print("=" * 70)
    print("  📸 PHOTO TEAM SYSTEM — مشغل لينك الموبايلات عبر Ngrok (Port 5000)")
    print("=" * 70)
    print(f"  [1] لينك الكمبيوتر المحلي   : http://127.0.0.1:{port}/login")
    print(f"  [2] لينك موبايلات الـ Wi-Fi  : http://{lan_ip}:{port}/login")
    print(f"  [3] صفحة نسخ اللينك والتحكم : http://127.0.0.1:{port}/ngrok-hub")
    print("-" * 70)

    print("  ⏳ جاري تشغيل Ngrok على بورت", port, "...")
    ngrok_url = start_ngrok_tunnel(port)

    try:
        webbrowser.open(f"http://127.0.0.1:{port}/ngrok-hub")
    except Exception:
        pass

    if not ngrok_url:
        print("\n  🔑 لتفعيل لينك Ngrok العام الآن:")
        print("  - افتح الرابط: https://dashboard.ngrok.com/get-started/your-authtoken")
        print("  - انسخ الـ Authtoken والصقه هنا بالأسفل ثم اضغط Enter (يُحفظ للأبد):")
        try:
            user_token = input("  👉 Authtoken (أو اضغط Enter للتخطي): ").strip()
            if user_token:
                # تنظيف التوكن لو المستخدم نسخ الأمر كامل مثل ngrok config add-authtoken XXX
                user_token = re.sub(r"^.*add-authtoken\s+", "", user_token).strip()
                ngrok_url = start_ngrok_tunnel(port, user_token)
        except EOFError:
            pass

    if ngrok_url:
        print("\n" + "=" * 70)
        print("  ✅ تم تشغيل لينك Ngrok بنجاح! ابعت اللينك ده لأي موبايل:")
        print(f"  🌐 لينك النظام الكامل للموبايلات : {ngrok_url}/login")
        print(f"  ✨ لينك النسخة التفاعلية المباشرة : {ngrok_url}/interactive")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print(f"  📶 السيرفر شغال الآن! يمكنك فتح صفحة التحكم في المتصفح:")
        print(f"     http://127.0.0.1:{port}/ngrok-hub")
        print("=" * 70)

    print("  ⚠️ اترك هذه النافذة مفتوحة طوال فترة استخدام الموبايلات للينك.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
