@echo off
title Debug Test Script

echo =================================
echo      调试测试脚本
echo =================================
echo.
echo 脚本开始执行...
echo.

echo 1. 显示基本环境信息:
echo    当前目录: %CD%
echo    脚本路径: %~dp0
echo    脚本名称: %~nx0
echo.

echo 2. 检查命令解释器:
echo    COMSPEC: %COMSPEC%
echo.

echo 3. 测试基本命令:
echo    当前时间: %time%
echo    当前日期: %date%
echo.

echo 4. 等待用户输入...
set /p user_input="请输入任意内容并按回车: "
echo 您输入了: %user_input%
echo.

echo 5. 测试文件操作...
echo 创建测试文件...
echo Test content > test_file.txt
echo 测试文件已创建。
echo.

echo 6. 脚本即将结束。
echo 按任意键退出...
pause >nul
echo.
echo 脚本正常结束。