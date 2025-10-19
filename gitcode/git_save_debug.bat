@echo off
chcp 65001 >nul
echo ========================================
echo       Git 保存脚本 (调试版本)
echo ========================================
echo.

echo 脚本开始执行...
echo 脚本位置: %~dp0
echo 当前目录: %CD%
echo.

:: 设置工作目录
cd /d "%~dp0.."
echo 切换到工作目录: %CD%
echo.

echo 检查Git是否可用...
git --version
if errorlevel 1 (
    echo Git命令执行失败!
    echo 请检查Git安装。
    pause
    exit /b 1
) else (
    echo Git命令可用。
)
echo.

echo 检查当前Git状态...
git status
echo.

echo 调试信息显示完毕。
echo 这是简化版本，用于调试闪退问题。
echo.
pause
echo 脚本正常结束。