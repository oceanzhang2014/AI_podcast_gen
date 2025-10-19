@echo off
chcp 65001 >nul
title Git工具演示

cls
echo ========================================
echo          Git工具演示程序
echo ========================================
echo.
echo 欢迎使用RL Snake项目的Git管理工具！
echo.
echo 项目已成功推送到GitHub:
echo https://github.com/oceanzhang2014/rl_snake
echo.
echo ========================================
echo          可用的Git工具:
echo ========================================
echo.
echo 1. git_manager.bat   - 主管理界面（推荐）
echo 2. git_save.bat      - 快速保存并推送
echo 3. git_rollback.bat  - 版本回退工具
echo 4. git_push.bat      - 推送工具
echo 5. git_status.bat    - 状态查看
echo.
echo ========================================
echo          演示操作:
echo ========================================
echo.

set /p demo_choice="是否要演示Git状态查看? (y/N): "
if /i "%demo_choice%"=="y" (
    echo.
    echo 正在运行 git_status.bat...
    echo ----------------------------------------
    call "%~dp0git_status.bat"
    echo ----------------------------------------
    echo.
)

echo.
echo ========================================
echo          使用建议:
echo ========================================
echo.
echo • 日常使用: 运行 git_manager.bat
echo • 快速保存: 运行 git_save.bat "提交信息"  
echo • 查看状态: 运行 git_status.bat
echo • 版本回退: 运行 git_rollback.bat
echo.
echo • 详细说明请查看: Git使用说明.md
echo.

set /p open_manager="是否要打开Git管理界面? (y/N): "
if /i "%open_manager%"=="y" (
    call "%~dp0git_manager.bat"
) else (
    echo.
    echo 感谢使用Git管理工具！
    echo.
    echo 项目地址: https://github.com/oceanzhang2014/rl_snake
    echo 本地路径: %~dp0..
    echo.
)

pause
