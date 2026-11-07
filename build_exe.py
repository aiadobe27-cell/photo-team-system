#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📸 PHOTO TEAM STUDIO V80 — أداة تحويل البرنامج إلى ملف تنفيذي (.EXE) مع الأيقونة الملكية
تعمل بضغطة زر واحدة على ويندوز وتنشئ ملف PhotoTeamStudio.exe + اختصار على سطح المكتب.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ICON_PATH = ROOT / "photo_team_icon.ico"
DIST_DIR = ROOT / "dist"
EXE_NAME = "PhotoTeamStudio"


def log(msg):
    print(msg, flush=True)


def ensure_requirements():
    log("📦 [1/4] جاري التأكد من تثبيت المكتبات وأداة PyInstaller...")
    pkgs = [
        "pyinstaller",
        "flask",
        "flask-cors",
        "mysql-connector-python",
        "bcrypt",
        "python-dotenv",
        "waitress",
        "pywebview",
        "pillow",
    ]
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=False)
    subprocess.run([sys.executable, "-m", "pip", "install", *pkgs], check=False)


def build_executable(onefile=True):
    log("🔨 [2/4] جاري بناء ملف الـ EXE ودمج الأيقونة والقوالب (قد يستغرق 1-2 دقيقة)...")
    sep = ";" if os.name == "nt" else ":"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        f"--name={EXE_NAME}",
        f"--add-data=templates{sep}templates",
        f"--add-data=static{sep}static",
        "--hidden-import=database",
        "--hidden-import=mysql.connector",
        "--hidden-import=mysql.connector.plugins.mysql_native_password",
        "--hidden-import=mysql.connector.plugins.caching_sha2_password",
        "--hidden-import=bcrypt",
        "--hidden-import=waitress",
        "--hidden-import=webview",
        "--hidden-import=flask_cors",
        "--hidden-import=dotenv",
    ]
    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    if ICON_PATH.exists():
        cmd.append(f"--icon={ICON_PATH}")
        cmd.append(f"--add-data=photo_team_icon.ico{sep}.")

    cmd.append("app.py")
    res = subprocess.run(cmd, cwd=str(ROOT))
    return res.returncode == 0


def copy_sidecar_files(onefile=True):
    log("📂 [3/4] جاري تجهيز مجلد المخرجات والملفات المساعدة...")
    target_dir = DIST_DIR if onefile else (DIST_DIR / EXE_NAME)
    target_dir.mkdir(parents=True, exist_ok=True)
    if ICON_PATH.exists():
        shutil.copy2(ICON_PATH, target_dir / "photo_team_icon.ico")
    env_file = ROOT / ".env"
    if env_file.exists():
        shutil.copy2(env_file, target_dir / ".env")
    (target_dir / "exports").mkdir(parents=True, exist_ok=True)


def create_desktop_shortcut(onefile=True):
    if os.name != "nt":
        return
    log("🖥️ [4/4] جاري إنشاء اختصار للبرنامج بالأيقونة على سطح المكتب (Desktop)...")
    exe_path = (DIST_DIR / f"{EXE_NAME}.exe") if onefile else (DIST_DIR / EXE_NAME / f"{EXE_NAME}.exe")
    if not exe_path.exists():
        return
    vbs_path = ROOT / "_create_shortcut.vbs"
    vbs_code = f"""
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = oWS.SpecialFolders("Desktop") & "\\PHOTO TEAM STUDIO V80.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{exe_path}"
oLink.WorkingDirectory = "{exe_path.parent}"
oLink.IconLocation = "{ICON_PATH}, 0"
oLink.Description = "PHOTO TEAM STUDIO V80 — Sapphire & Obsidian Dual-Mode System"
oLink.Save
"""
    try:
        vbs_path.write_text(vbs_code.strip(), encoding="utf-8")
        subprocess.run(["cscript", "//Nologo", str(vbs_path)], check=False)
    finally:
        if vbs_path.exists():
            vbs_path.unlink()


def main():
    os.chdir(str(ROOT))
    print("=" * 68)
    print("  📸 PHOTO TEAM STUDIO V80 — محول البرنامج إلى ملف EXE بالأيقونة")
    print("=" * 68)
    mode = "1"
    if len(sys.argv) > 1 and sys.argv[1] in ("1", "2"):
        mode = sys.argv[1]
    else:
        print("اختر نوع التحويل:")
        print("  [1] ملف EXE واحد مستقل شامل (PhotoTeamStudio.exe) — مستحسن")
        print("  [2] مجلد EXE سريع الفتح (PhotoTeamStudio/PhotoTeamStudio.exe)")
        try:
            ans = input("اختيارك (اضغط Enter لاختيار 1): ").strip()
            if ans in ("1", "2"):
                mode = ans
        except EOFError:
            mode = "1"

    onefile = (mode == "1")
    ensure_requirements()
    ok = build_executable(onefile=onefile)
    if ok:
        copy_sidecar_files(onefile=onefile)
        create_desktop_shortcut(onefile=onefile)
        exe_out = (DIST_DIR / f"{EXE_NAME}.exe") if onefile else (DIST_DIR / EXE_NAME / f"{EXE_NAME}.exe")
        print("\n" + "=" * 68)
        print("🎉 تم تحويل البرنامج إلى EXE بنجاح مع الأيقونة الملكية!")
        print(f"📍 مسار ملف الـ EXE الجاهز: {exe_out}")
        print("🖥️ كما تم وضع اختصار للبرنامج على سطح المكتب باسم: PHOTO TEAM STUDIO V80")
        print("=" * 68)
        if os.name == "nt" and DIST_DIR.exists():
            os.startfile(str(DIST_DIR))
    else:
        print("\n❌ حدث خطأ أثناء بناء الـ EXE. تأكد من تثبيت Python وإضافة خيار Add Python to PATH.")
        sys.exit(1)


if __name__ == "__main__":
    main()
