@echo off
chcp 65001 >nul
echo ========================================
echo           Git 推送脚本
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

:: 检查远程仓库
git remote | findstr origin >nul
if errorlevel 1 (
    echo 添加远程仓库...
    git remote add origin https://github.com/oceanzhang2014/AI_podcast_gen.git
    echo.
)

:: 显示当前状态
echo 当前Git状态:
git status --short
echo.

:: 检查是否有未提交的更改
git diff-index --quiet HEAD --
if errorlevel 1 (
    echo 检测到未提交的更改。
    set /p auto_commit="是否自动提交这些更改? (y/N): "
    if /i "%auto_commit%"=="y" (
        set /p commit_msg="请输入提交信息: "
        if "!commit_msg!"=="" (
            set commit_msg=自动提交 - %date% %time%
        )
        echo 添加所有文件...
        git add .
        echo 提交更改...
        git commit -m "!commit_msg!"
    ) else (
        echo 请先提交更改后再推送。
        pause
        exit /b 1
    )
)

:: 获取当前分支
for /f "tokens=*" %%i in ('git branch --show-current') do set current_branch=%%i
if "%current_branch%"=="" set current_branch=main

echo.
echo 推送到远程仓库 (分支: %current_branch%)...

:: 尝试正常推送
git push origin %current_branch%

if errorlevel 1 (
    echo.
    echo 推送失败，可能的原因:
    echo 1. 远程仓库有新的提交
    echo 2. 分支不存在
    echo.
    echo 请选择操作:
    echo 1. 拉取远程更改并合并
    echo 2. 强制推送 (危险操作!)
    echo 3. 取消操作
    echo.
    
    set /p push_choice="请输入选择 (1-3): "
    
    if "!push_choice!"=="1" (
        echo 拉取远程更改...
        git pull origin %current_branch%
        if not errorlevel 1 (
            echo 重新推送...
            git push origin %current_branch%
        )
    ) else if "!push_choice!"=="2" (
        echo 警告: 强制推送将覆盖远程仓库的内容!
        set /p force_confirm="确定要继续吗? (y/N): "
        if /i "!force_confirm!"=="y" (
            echo 执行强制推送...
            git push -f origin %current_branch%
        ) else (
            echo 操作已取消。
        )
    ) else (
        echo 操作已取消。
    )
)

echo.
echo ========================================
echo           推送完成!
echo ========================================
pause
