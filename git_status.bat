@echo off
echo ========================================
echo AI Podcast Generator - Git Status Check
echo ========================================
echo.

REM 检查是否在正确的目录
if not exist "app.py" (
    echo [ERROR] 请在项目根目录下运行此脚本
    pause
    exit /b 1
)

echo [1/6] 检查 Git 状态...
git status --porcelain
echo.

echo [2/6] 检查未跟踪的文件...
git ls-files --others --exclude-standard
echo.

echo [3/6] 检查已修改的文件...
git diff --name-only
echo.

echo [4/6] 检查分支状态...
git branch
echo.

echo [5/6] 检查远程仓库...
git remote -v
echo.

echo [6/6] 检查最近提交...
git log --oneline -3
echo.

echo ========================================
echo [INFO] Git 状态检查完成
echo ========================================
echo.

pause