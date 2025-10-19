@echo off
chcp 65001 >nul
echo ========================================
echo           Git 保存脚本
echo ========================================
echo.

:: 添加调试信息
echo 脚本开始执行...
echo 脚本位置: %~dp0
echo 当前目录: %CD%
echo.

:: 检查Git是否安装，尝试常见路径并添加到PATH
set GIT_FOUND=0
set GIT_EXE_PATH=

echo 正在查找Git安装...

if exist "D:\app\aidrawing\Git\mingw64\bin\git.exe" (
    set GIT_EXE_PATH=D:\app\aidrawing\Git\mingw64\bin\git.exe
    set GIT_FOUND=1
    echo 找到Git: D:\app\aidrawing\Git\mingw64\bin\git.exe
) else if exist "C:\Program Files\Git\bin\git.exe" (
    set GIT_EXE_PATH=C:\Program Files\Git\bin\git.exe
    set GIT_FOUND=1
    echo 找到Git: C:\Program Files\Git\bin\git.exe
) else if exist "C:\Program Files (x86)\Git\bin\git.exe" (
    set GIT_EXE_PATH=C:\Program Files (x86)\Git\bin\git.exe
    set GIT_FOUND=1
    echo 找到Git: C:\Program Files (x86)\Git\bin\git.exe
) else (
    echo 尝试使用系统PATH中的git...
    git --version >nul 2>&1
    if not errorlevel 1 (
        set GIT_FOUND=1
        echo Git已在系统PATH中找到
    )
)

if "%GIT_FOUND%"=="0" (
    echo 错误: Git 未安装或未找到!
    echo 请先安装 Git: https://git-scm.com/
    echo.
    echo 或检查以下路径是否包含Git:
    echo - D:\app\aidrawing\Git\mingw64\bin\git.exe
    echo - C:\Program Files\Git\bin\git.exe
    echo - C:\Program Files (x86)\Git\bin\git.exe
    echo.
    echo 按任意键退出...
    pause >nul
    exit /b 1
)

echo Git版本信息:
git --version
echo.

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

:: 获取当前分支名称
for /f "tokens=*" %%i in ('git branch --show-current 2^>nul') do set current_branch=%%i
if "%current_branch%"=="" set current_branch=master

echo 当前分支: %current_branch%

:: 尝试推送到当前分支
git push -u origin %current_branch%

if errorlevel 1 (
    echo.
    echo 推送失败，尝试强制推送...
    git push -f origin %current_branch%
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
        echo 当前分支: %current_branch%
        echo 远程仓库: origin
        echo.
    )
)

echo.
echo ========================================
echo           操作完成!
echo ========================================
echo 当前工作目录: %CD%
echo 远程仓库: https://github.com/oceanzhang2014/AI_podcast_gen.git
echo 分支: %current_branch%
echo.
echo 按任意键退出...
pause >nul
echo 脚本执行完毕。
