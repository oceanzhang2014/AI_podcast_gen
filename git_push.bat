@echo off
echo ========================================
echo AI Podcast Generator - Git Push Script
echo ========================================
echo.

REM 检查是否在正确的目录
if not exist "app.py" (
    echo [ERROR] 请在项目根目录下运行此脚本
    echo [ERROR] 当前目录不包含 app.py 文件
    pause
    exit /b 1
)

echo [1/7] 检查当前 Git 状态...
git status
echo.

echo [2/7] 添加所有文件到暂存区...
git add .
if %errorlevel% neq 0 (
    echo [ERROR] Git add 失败
    pause
    exit /b 1
)
echo [SUCCESS] 所有文件已添加到暂存区

echo [3/7] 创建提交...
git commit -m "feat: 添加数据持久化功能 - admin用户表单保存和音频文件命名优化

- 添加OpenSpec提案 add-form-data-persistence
- 新增播客配置数据持久化功能
- 实现默认admin用户系统
- 改进音频文件命名为 admin_YYYYMMDD_HHMMSS.mp3 格式
- 自动保存和恢复表单配置
- 添加用户会话管理

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
if %errorlevel% neq 0 (
    echo [WARNING] 没有文件需要提交，继续推送...
) else (
    echo [SUCCESS] 提交创建成功
)

echo.
echo [4/7] 推送到远程仓库...
git push origin main
if %errorlevel% neq 0 (
    echo [ERROR] Git push 失败
    echo 请检查：
    echo 1. 网络连接是否正常
    echo 2. GitHub 仓库地址是否正确
    echo 3. 是否有推送权限
    pause
    exit /b 1
)
echo [SUCCESS] 推送成功！

echo.
echo [5/7] 显示当前分支信息...
git branch -a
echo.

echo [6/7] 显示远程仓库信息...
git remote -v
echo.

echo [7/7] 显示最近提交...
git log --oneline -5
echo.

echo ========================================
echo [SUCCESS] 项目已成功推送到 GitHub!
echo ========================================
echo.
echo GitHub 仓库地址: https://github.com/oceanzhang2014/AI_podcast_gen
echo.

pause