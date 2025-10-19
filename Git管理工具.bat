@echo off
chcp 65001 >nul
title AI Podcast Gen - Git管理工具

:: 设置工作目录到脚本所在目录
cd /d "%~dp0"

:: 检查gitcode目录是否存在
if not exist "gitcode" (
    echo 错误: gitcode 目录不存在!
    echo 请确保 gitcode 文件夹在同一目录下。
    echo.
    pause
    exit /b 1
)

:: 检查是否有命令行参数
if "%1"=="save" (
    echo.
    echo ========================================
    echo     保存并推送到 AI Podcast Gen 仓库
    echo ========================================
    echo.
    if exist "gitcode\git_save.bat" (
        call "gitcode\git_save.bat" %2
    ) else (
        echo 错误: git_save.bat 文件不存在!
    )
    pause
    goto :eof
)

:: 运行Git管理工具
if exist "gitcode\git_manager.bat" (
    call "gitcode\git_manager.bat"
) else (
    echo 错误: git_manager.bat 文件不存在!
    pause
    exit /b 1
)

:: 如果从菜单退出，显示结束信息
echo.
echo Git管理工具已关闭
pause
