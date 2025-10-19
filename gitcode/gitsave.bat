@echo off
title Git Save Script (Simple Version)
echo ========================================
echo           Git 保存脚本
echo ========================================
echo.

echo Script started...
echo Script location: %~dp0
echo Current directory: %CD%
echo.

echo Changing to parent directory...
cd /d "%~dp0.."
echo Working directory: %CD%
echo.

echo Checking if this is a git repository...
if exist ".git" (
    echo This is a git repository.
) else (
    echo This is NOT a git repository.
)
echo.

echo Checking git installation...
git --version
if errorlevel 1 (
    echo Git command failed!
    echo Git may not be installed or not in PATH.
    echo.
    echo Common Git locations:
    echo - D:\app\aidrawing\Git\mingw64\bin\git.exe
    echo - C:\Program Files\Git\bin\git.exe
    echo - C:\Program Files (x86)\Git\bin\git.exe
    echo.
) else (
    echo Git command successful!
)
echo.

echo Script completed successfully.
echo Press any key to exit...
pause >nul
echo Goodbye!