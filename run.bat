@echo off
title Sistem Pendukung Keputusan AHP (Analytical Hierarchy Process)
echo =====================================================================
echo  MEMULAI APLIKASI SPK AHP (ANALYTICAL HIERARCHY PROCESS)
echo =====================================================================
echo.
echo Memeriksa instalasi Python...
python --version
if errorlevel 1 (
    echo [ERROR] Python tidak ditemukan di sistem. Silakan instal Python 3.
    pause
    exit /b
)

echo.
echo Menjalankan server aplikasi Flask...
echo Buka browser Anda di: http://127.0.0.1:5000
echo.
echo Akun Login:
echo - Admin: admin@ahp.com  ^| Password: admin123
echo - User:  user@ahp.com   ^| Password: user123
echo.
echo Tekan CTRL + C di jendela ini untuk menghentikan server.
echo =====================================================================
echo.

python app.py
pause
