@echo off
title Setup Custom Domain - Employee Directory Portal
echo ========================================================
echo   Configuring Local Domain: employeedirectoryportal
echo ========================================================
echo.

net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo [ERROR] Administrator privileges required.
    echo Please RIGHT-CLICK this file and select "Run as administrator".
    echo.
    pause
    exit /b 1
)

findstr /I "employeedirectoryportal" "%windir%\System32\drivers\etc\hosts" >nul
if %errorLevel% EQU 0 (
    echo [OK] Domain 'employeedirectoryportal' is already registered in your hosts file!
) else (
    echo 127.0.0.1 employeedirectoryportal employeedirectoryportal.local >> "%windir%\System32\drivers\etc\hosts"
    echo [SUCCESS] Added 127.0.0.1 employeedirectoryportal to %windir%\System32\drivers\etc\hosts
)

echo.
echo ========================================================
echo You can now open the portal in your browser at:
echo   http://employeedirectoryportal:5000
echo ========================================================
echo.
pause
