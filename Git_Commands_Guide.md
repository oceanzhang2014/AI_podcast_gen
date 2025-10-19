# Git 保存和推送命令指南

本文档提供了常用的Git保存和推送命令，适用于AI Podcast Generator项目。

## 🚀 快速开始

### 基本保存和推送流程

```bash
# 1. 检查当前状态
git status

# 2. 添加所有修改的文件
git add .

# 3. 提交更改（使用描述性的提交信息）
git commit -m "你的提交信息"

# 4. 推送到远程仓库
git push origin main
```

## 📋 详细命令说明

### 1. 查看状态

```bash
# 查看当前仓库状态
git status

# 查看简洁状态
git status --short

# 查看分支信息
git branch -a
```

### 2. 添加文件到暂存区

```bash
# 添加所有文件
git add .

# 添加特定文件
git add filename.ext

# 添加特定类型的文件
git add *.py
git add *.bat

# 添加修改的文件，不包括新文件
git add -u
```

### 3. 提交更改

```bash
# 基本提交
git commit -m "提交信息"

# 提交并显示详细状态
git commit -v -m "提交信息"

# 修改最后一次提交
git commit --amend -m "新的提交信息"

# 添加所有修改并提交
git commit -am "提交信息"
```

### 4. 推送到远程仓库

```bash
# 推送到指定分支
git push origin main

# 设置上游分支并推送
git push -u origin main

# 强制推送（谨慎使用）
git push -f origin main

# 推送所有分支
git push --all origin
```

## 🔧 高级命令

### 分支管理

```bash
# 创建新分支
git checkout -b new-feature

# 切换分支
git checkout main

# 合并分支
git merge new-feature

# 删除分支
git branch -d new-feature
```

### 查看历史

```bash
# 查看提交历史
git log

# 查看简洁历史
git log --oneline

# 查看最近10次提交
git log --oneline -10

# 查看图形化历史
git log --graph --oneline
```

### 撤销操作

```bash
# 撤销工作区的修改
git restore filename.ext

# 撤销暂存区的修改
git restore --staged filename.ext

# 回退到指定提交
git reset --hard commit-hash

# 回退到上一个提交
git reset --hard HEAD~1
```

## 🛠️ 项目特定命令

### AI Podcast Generator 项目

```bash
# 推送到主仓库
git push origin main https://github.com/oceanzhang2014/AI_podcast_gen.git

# 克隆项目
git clone https://github.com/oceanzhang2014/AI_podcast_gen.git

# 查看远程仓库
git remote -v

# 添加远程仓库
git remote add origin https://github.com/oceanzhang2014/AI_podcast_gen.git
```

### 使用Git管理工具

```bash
# 双击运行Git管理工具
Git管理工具.bat

# 命令行直接保存
Git管理工具.bat save "提交信息"

# 查看Git状态
Git管理工具.bat status
```

## 📝 提交信息规范

好的提交信息应该：

1. **清晰描述更改内容**
2. **使用现在时态**
3. **以动词开头**
4. **不超过50个字符（标题）**

### 提交信息示例

```bash
# 好的提交信息
git commit -m "添加用户认证功能"
git commit -m "修复音频播放bug"
git commit -m "更新Git管理工具"
git commit -m "添加新的AI角色配置选项"

# 详细的提交信息（多行）
git commit -m "重构TTS引擎代码

- 优化音频处理流程
- 添加错误处理机制
- 提升性能20%
- 修复内存泄漏问题"
```

## 🚨 常见问题解决

### 推送被拒绝

```bash
# 如果推送被拒绝，先拉取远程更改
git pull origin main

# 如果有冲突，解决冲突后
git add .
git commit -m "解决合并冲突"
git push origin main
```

### 合并冲突

```bash
# 查看冲突文件
git status

# 手动编辑冲突文件，删除冲突标记

# 添加解决后的文件
git add conflicted-file.ext

# 提交合并
git commit -m "解决合并冲突"
```

### 撤销错误的提交

```bash
# 撤销最后一次提交（保留更改）
git reset --soft HEAD~1

# 撤销最后一次提交（丢弃更改）
git reset --hard HEAD~1

# 如果已经推送，需要强制推送
git push -f origin main
```

## 📊 实用工作流程

### 日常开发流程

```bash
# 1. 开始工作前，拉取最新代码
git pull origin main

# 2. 进行开发工作...

# 3. 查看修改
git status

# 4. 添加并提交更改
git add .
git commit -m "添加新功能描述"

# 5. 推送到远程
git push origin main
```

### 功能开发流程

```bash
# 1. 创建功能分支
git checkout -b feature/new-feature

# 2. 开发功能...

# 3. 提交更改
git add .
git commit -m "实现新功能"

# 4. 切换回主分支
git checkout main

# 5. 合并功能分支
git merge feature/new-feature

# 6. 推送更改
git push origin main

# 7. 删除功能分支
git branch -d feature/new-feature
```

## 🔗 相关链接

- [GitHub 仓库](https://github.com/oceanzhang2014/AI_podcast_gen)
- [Git 官方文档](https://git-scm.com/doc)
- [Pro Git 书籍](https://git-scm.com/book)

---

**提示**: 定期保存和推送你的代码更改，避免丢失重要工作！