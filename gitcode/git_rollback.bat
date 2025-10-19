@echo off
chcp 65001 >nul
echo ========================================
echo           Git 回退脚本
echo ========================================
echo.

:: 设置工作目录
cd /d "%~dp0.."

:: 检查是否是git仓库
if not exist ".git" (
    echo 错误: 当前目录不是Git仓库!
    pause
    exit /b 1
)

:: 显示最近的提交记录
echo 最近的提交记录:
echo ----------------------------------------
git log --oneline -10
echo ----------------------------------------
echo.

:: 选择回退类型
echo 请选择回退类型:
echo 1. 软回退 (保留工作区和暂存区的更改)
echo 2. 混合回退 (保留工作区的更改，清空暂存区) [默认]
echo 3. 硬回退 (丢弃所有更改，危险操作!)
echo 4. 回退到指定提交
echo 5. 取消操作
echo.

set /p choice="请输入选择 (1-5): "

if "%choice%"=="1" goto soft_reset
if "%choice%"=="2" goto mixed_reset
if "%choice%"=="3" goto hard_reset
if "%choice%"=="4" goto commit_reset
if "%choice%"=="5" goto cancel
if "%choice%"=="" goto mixed_reset

echo 无效选择，执行混合回退...
goto mixed_reset

:soft_reset
echo.
echo 执行软回退到上一个提交...
git reset --soft HEAD~1
goto end

:mixed_reset
echo.
echo 执行混合回退到上一个提交...
git reset --mixed HEAD~1
goto end

:hard_reset
echo.
echo 警告: 硬回退将丢失所有未提交的更改!
set /p confirm="确定要继续吗? (y/N): "
if /i not "%confirm%"=="y" goto cancel
echo 执行硬回退到上一个提交...
git reset --hard HEAD~1
goto end

:commit_reset
echo.
set /p commit_hash="请输入要回退到的提交哈希值: "
if "%commit_hash%"=="" (
    echo 未输入提交哈希值，取消操作。
    goto cancel
)
echo 回退到提交: %commit_hash%
git reset --mixed %commit_hash%
goto end

:cancel
echo.
echo 操作已取消。
goto end

:end
echo.
echo 回退操作完成!
echo.
echo 当前状态:
git status --short
echo.
echo ========================================
pause
