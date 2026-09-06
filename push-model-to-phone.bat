@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo   Sahaya - Copy Gemma 4 On-Device Model to Phone
echo ============================================================
echo.

set ADB="C:\Users\Ritvik Bhat\AppData\Local\Android\Sdk\platform-tools\adb.exe"
if not exist %ADB% (
    set ADB=adb
)

set MODEL="C:\Users\Ritvik Bhat\Downloads\gemma-4-E2B-it.litertlm"
if not exist %MODEL% (
    echo [ERROR] Model file not found at: %MODEL%
    echo Please make sure gemma-4-E2B-it.litertlm is located in your Downloads folder.
    pause
    exit /b 1
)

echo Checking for connected phone...
%ADB% devices
echo.

echo 1. Creating target directory on phone...
%ADB% shell mkdir -p /sdcard/Android/data/com.sahaya.app/files/models/

echo 2. Pushing gemma-4-E2B-it.litertlm to phone (2.5 GB, please wait 30-60 seconds)...
%ADB% push %MODEL% /sdcard/Android/data/com.sahaya.app/files/models/gemma-4-E2B-it.litertlm

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to push model file. Make sure your phone is unlocked and USB debugging is enabled.
    pause
    exit /b %ERRORLEVEL%
)

echo 3. Setting read/write permissions for app access...
%ADB% shell chmod -R 777 /sdcard/Android/data/com.sahaya.app/files/models/

echo.
echo 4. Verifying model file on phone:
%ADB% shell ls -lh /sdcard/Android/data/com.sahaya.app/files/models/gemma-4-E2B-it.litertlm

echo.
echo ============================================================
echo   SUCCESS: Model file copied and permissions set!
echo   Sahaya can now run on-device inference completely offline.
echo ============================================================
pause
