@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
echo ========================================
echo           Git 保存脚本
echo ========================================
echo.

:: 检查Git是否安装
git --version >nul 2>&1
if errorlevel 1 (
    echo 错误: Git 未安装或未添加到系统路径!
    echo 请先安装 Git: https://git-scm.com/
    echo.
    pause
    exit /b 1
)

:: 设置工作目录
cd /d "%~dp0.."
echo 当前工作目录: %CD%
echo.

:: 检查是否是git仓库
if not exist ".git" (
    echo 初始化Git仓库...
    git init
    if errorlevel 1 (
        echo 错误: Git 仓库初始化失败!
        pause
        exit /b 1
    )
    echo Git 仓库初始化成功。
    echo.
)

:: 检查远程仓库
git remote | findstr origin >nul
if errorlevel 1 (
    echo 添加远程仓库...
    git remote add origin https://github.com/oceanzhang2014/AI_podcast_gen.git
    if errorlevel 1 (
        echo 错误: 添加远程仓库失败!
        pause
        exit /b 1
    )
    echo 远程仓库添加成功。
    echo.
)

:: 显示当前状态
echo 当前Git状态:
git status --short
echo.

:: 获取提交信息
if "%~1"=="" (
    set /p commit_msg="请输入提交信息: "
) else (
    set commit_msg=%~1
)

if "%commit_msg%"=="" (
    set commit_msg=自动保存 - %date% %time%
)

echo.
echo 添加所有文件到暂存区...
git add .
if errorlevel 1 (
    echo 警告: git add 命令执行失败，但继续执行...
)

echo.
echo 提交更改...
git commit -m "%commit_msg%"
if errorlevel 1 (
    echo 警告: 没有需要提交的更改，或提交失败。
    echo 继续尝试推送...
)

echo.
echo 推送到远程仓库...
git push -u origin main

if errorlevel 1 (
    echo.
    echo 推送失败，尝试强制推送...
    git push -f origin main
    if errorlevel 1 (
        echo.
        echo 错误: 推送失败! 可能的原因:
        echo 1. 网络连接问题
        echo 2. 认证失败 (需要设置GitHub访问权限)
        echo 3. 分支名称不匹配
        echo.
        echo 请检查:
        echo - 是否已配置Git用户信息
        echo - 是否有GitHub访问权限
        echo - 远程仓库地址是否正确
        echo.
    )
)

echo.
echo ========================================
echo           操作完成!
echo ========================================
echo 当前工作目录: %CD%
echo 远程仓库: https://github.com/oceanzhang2014/AI_podcast_gen.git
echo.
pause
