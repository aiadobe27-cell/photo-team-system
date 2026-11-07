@echo off
chcp 65001 >nul
title PHOTO TEAM - Run Ngrok Mobile Link (Port 5000)
cd /d "%~dp0"
echo ====================================================================
echo   PHOTO TEAM SYSTEM - Starting Ngrok Mobile Link Server (Port 5000)
echo   جاري تشغيل السيرفر وفتح لينك Ngrok للموبايلات...
echo ====================================================================
python run_ngrok.py
pause
