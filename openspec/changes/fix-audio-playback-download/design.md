## Context
项目是一个AI播客生成器，用户可以生成自定义的播客音频文件。当前生成的音频文件可以正常保存到服务器，但前端播放器无法播放，下载按钮下载的是HTML文件而不是MP3文件。

## Goals / Non-Goals
- Goals:
  - 修复音频播放器功能，使其能正常播放生成的音频文件
  - 修复下载功能，确保下载正确的MP3文件
  - 改进错误处理和用户反馈
- Non-Goals:
  - 不修改音频生成逻辑
  - 不改变文件存储结构

## Decisions
- Decision: 在前端音频URL设置前添加文件存在性验证
  - Reason: 避免设置无效的音频URL导致播放器错误
  - Implementation: 在设置audioPlayer.src前通过HEAD请求验证文件可访问性

- Decision: 改进下载按钮的download属性设置
  - Reason: 确保浏览器下载正确的文件类型和文件名
  - Implementation: 动态设置download属性为正确的MP3文件名

- Decision: 增强后端音频路由的错误处理
  - Reason: 提供更清晰的错误信息，便于调试
  - Implementation: 添加详细的日志记录和适当的HTTP状态码

## Risks / Trade-offs
- [Risk] 增加的文件验证请求可能影响性能
  - Mitigation: 使用异步验证，避免阻塞用户界面
- [Trade-off] 更严格的错误处理可能暴露系统信息
  - Mitigation: 只在生产环境显示用户友好的错误信息

## Migration Plan
1. 首先修复后端路由的MIME类型和错误处理
2. 然后修复前端的音频URL设置和验证逻辑
3. 最后改进下载功能和用户反馈
4. 回滚计划：保留原始代码的备份，可快速回滚到当前状态

## Open Questions
- 是否需要添加音频文件的缓存机制？
- 如何处理大文件的下载超时问题？
- 是否需要支持其他音频格式？