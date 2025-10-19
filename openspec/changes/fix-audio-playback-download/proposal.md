## Why
修复前端音频播放器无法播放生成的音频文件以及下载按钮下载HTML文件而非MP3文件的问题，提升用户体验。

## What Changes
- 修复音频播放器的URL设置和错误处理逻辑
- 改进下载功能的文件类型检测和URL生成
- 增强音频文件路由的安全性和MIME类型处理
- 添加音频文件存在性验证和错误处理
- **BREAKING**: 修改前端音频状态管理机制

## Impact
- Affected specs: audio-playback, file-download
- Affected code: app.py (音频路由), static/js/main.js (前端音频处理), templates/index.html (音频播放器UI)