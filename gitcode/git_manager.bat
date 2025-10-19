@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Git 管理工具

:main_menu
cls
echo ========================================
echo           Git 管理工具
echo ========================================
echo.
echo 项目路径: %~dp0..
echo GitHub仓库: https://github.com/oceanzhang2014/AI_podcast_gen
echo.
echo 请选择操作:
echo.
echo 1. 保存并推送到GitHub (git_save)
echo 2. 回退版本 (git_rollback)
echo 3. 仅推送到远程 (git_push)
echo 4. 查看Git状态 (git_status)
echo 5. 克隆远程仓库
echo 6. 分支管理
echo 7. 查看提交历史
echo 8. 退出
echo.

set /p choice="请输入选择 (1-8): "

if "%choice%"=="1" goto save_and_push
if "%choice%"=="2" goto rollback
if "%choice%"=="3" goto push_only
if "%choice%"=="4" goto check_status
if "%choice%"=="5" goto clone_repo
if "%choice%"=="6" goto branch_management
if "%choice%"=="7" goto view_history
if "%choice%"=="8" goto exit
if "%choice%"=="" goto main_menu

echo 无效选择，请重新输入。
pause
goto main_menu

:save_and_push
echo.
echo 执行保存并推送操作...
cmd /c "%~dp0git_save.bat"
pause
goto main_menu

:rollback
echo.
echo 执行版本回退操作...
cmd /c "%~dp0git_rollback.bat"
pause
goto main_menu

:push_only
echo.
echo 执行推送操作...
cmd /c "%~dp0git_push.bat"
pause
goto main_menu

:check_status
echo.
echo 查看Git状态...
cmd /c "%~dp0git_status.bat"
pause
goto main_menu

:clone_repo
echo.
echo 克隆远程仓库...
set /p clone_path="请输入克隆目标路径 (留空使用当前目录): "
if "%clone_path%"=="" set clone_path=.
git clone https://github.com/oceanzhang2014/AI_podcast_gen.git "%clone_path%"
pause
goto main_menu

:branch_management
cls
echo ========================================
echo           分支管理
echo ========================================
echo.
cd /d "%~dp0.."
echo 当前分支:
git branch
echo.
echo 所有分支 (包括远程):
git branch -a
echo.
echo 1. 创建新分支
echo 2. 切换分支
echo 3. 删除分支
echo 4. 合并分支
echo 5. 返回主菜单
echo.
set /p branch_choice="请选择操作 (1-5): "

if "%branch_choice%"=="1" (
    set /p new_branch="请输入新分支名称: "
    git checkout -b !new_branch!
) else if "%branch_choice%"=="2" (
    set /p switch_branch="请输入要切换的分支名称: "
    git checkout !switch_branch!
) else if "%branch_choice%"=="3" (
    set /p delete_branch="请输入要删除的分支名称: "
    git branch -d !delete_branch!
) else if "%branch_choice%"=="4" (
    set /p merge_branch="请输入要合并的分支名称: "
    git merge !merge_branch!
) else if "%branch_choice%"=="5" (
    goto main_menu
)

pause
goto branch_management

:view_history
cls
echo ========================================
echo           提交历史
echo ========================================
echo.
cd /d "%~dp0.."
echo 最近20次提交:
git log --oneline -20
echo.
echo 详细信息请使用: git log
pause
goto main_menu

:exit
echo.
echo 感谢使用Git管理工具!
pause
goto :eof
