@echo off
chcp 65001 >nul
echo ========================================
echo           Git 状态查看
echo ========================================
echo.

:: 设置工作目录
cd /d "%~dp0.."

:: 检查是否是git仓库
if not exist ".git" (
    echo 当前目录不是Git仓库
    echo 运行 git_save.bat 来初始化仓库
    pause
    exit /b 1
)

:: 显示基本状态
echo 当前Git状态:
echo ----------------------------------------
git status
echo.

:: 显示分支信息
echo 分支信息:
echo ----------------------------------------
git branch -a
echo.

:: 显示远程仓库信息
echo 远程仓库:
echo ----------------------------------------
git remote -v
echo.

:: 显示最近的提交记录
echo 最近的提交记录:
echo ----------------------------------------
git log --oneline -5
echo.

:: 显示未跟踪的文件
echo 未跟踪的文件:
echo ----------------------------------------
git ls-files --others --exclude-standard
echo.

:: 显示已修改但未暂存的文件
echo 已修改但未暂存的文件:
echo ----------------------------------------
git diff --name-only
echo.

:: 显示已暂存但未提交的文件
echo 已暂存但未提交的文件:
echo ----------------------------------------
git diff --cached --name-only
echo.

echo ========================================
pause
