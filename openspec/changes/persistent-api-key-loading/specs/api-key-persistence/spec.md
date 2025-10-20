# API密钥持久化加载规格说明

## ADDED Requirements

### Requirement: 跨会话API密钥持久化显示
- **Description**: 系统 SHALL 在用户关闭浏览器后重新打开时，自动从后端数据库获取已保存的API密钥并在前端显示
- **Priority**: High

#### Scenario:
1. **Given**: 用户之前已配置并验证了API密钥（如DeepSeek）
2. **When**: 用户关闭浏览器后重新访问应用
3. **Then**: 系统自动从数据库加载API密钥并以遮蔽形式显示在对应输入框中
4. **And**: 验证状态根据数据库记录正确显示

#### Acceptance Criteria:
- API密钥 SHALL 在页面加载时从数据库自动获取
- API密钥 MUST 以遮蔽形式在前端显示（例如：sk-******************key）
- 验证状态 SHALL 根据数据库记录正确更新
- 用户体验 MUST 流畅，无需手动重新输入密钥

### Requirement: 前端API密钥异步加载机制
- **Description**: 前端 SHALL 支持从后端异步加载API密钥数据并正确填充到表单中
- **Priority**: Medium

#### Scenario:
1. **Given**: 页面开始加载但模板变量中没有API密钥数据
2. **When**: JavaScript执行异步API请求获取配置数据
3. **Then**: API密钥数据填充到对应的输入框中
4. **And**: 验证状态和UI元素正确更新

#### Acceptance Criteria:
- 前端 SHALL 在模板变量为空时发起异步请求
- API密钥数据 MUST 正确填充到对应的输入框
- 验证状态徽章 SHALL 正确显示（已验证/未验证）
- 加载过程 MUST 不影响用户体验

### Requirement: 现有遮蔽机制的兼容性
- **Description**: 系统 SHALL 在持久化加载时正确使用现有的API密钥遮蔽显示机制
- **Priority**: Medium

#### Scenario:
1. **Given**: 系统已有API密钥遮蔽显示功能（显示/隐藏按钮、遮蔽格式等）
2. **When**: 从数据库持久化加载API密钥到前端
3. **Then**: 加载的API密钥必须与现有遮蔽机制完全兼容
4. **And**: 显示/隐藏功能正常工作，遮蔽格式保持一致

#### Acceptance Criteria:
- 持久化加载的API密钥 SHALL 与现有遮蔽格式完全一致
- 显示/隐藏按钮 MUST 在持久化加载的密钥上正常工作
- 遮蔽机制 MUST 确保与现有功能无缝集成
- 用户体验 MUST 保持一致

## MODIFIED Requirements

### Requirement: 首页路由API密钥预加载
- **Description**: 系统 SHALL 修改首页路由，在渲染模板时预加载用户已保存的API密钥数据
- **Priority**: High

#### Scenario:
1. **Given**: 用户访问应用首页
2. **When**: 系统处理首页路由请求
3. **Then**: 系统从数据库查询用户已保存的API密钥
4. **And**: 将遮蔽后的API密钥数据传递给模板进行渲染

#### Acceptance Criteria:
- 首页路由 SHALL 查询用户已保存的API密钥
- API密钥 MUST 以遮蔽形式传递给模板
- 验证状态 SHALL 正确传递给模板
- 错误处理机制 MUST 完善

### Requirement: 前端表单智能初始化
- **Description**: 前端 SHALL 在表单初始化时支持多种数据源，确保API密钥数据的完整加载
- **Priority**: Medium

#### Scenario:
1. **Given**: 页面开始加载
2. **When**: 前端JavaScript开始执行表单初始化
3. **Then**: 首先检查模板变量中的API密钥数据
4. **And**: 如果模板变量为空，则通过异步API获取数据
5. **And**: 将获取的数据填充到表单中并更新UI状态

#### Acceptance Criteria:
- 表单初始化 SHALL 优先使用模板变量数据
- 异步API加载 MUST 作为备用机制
- 数据填充后 SHALL 更新所有相关的UI元素
- 初始化过程 MUST 不阻塞页面渲染