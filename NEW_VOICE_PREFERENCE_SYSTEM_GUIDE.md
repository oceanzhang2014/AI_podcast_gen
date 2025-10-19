# 新声音偏好系统使用指南

## 概述 🎯

系统已完成重大升级，现在支持基于**风格分类**的声音选择模式。前端用户可以：

1. **年龄选择**：从 `voice_preferences.json` 的 "年龄选项" 中选择
2. **声音偏好选择**：从 "声音偏好" 分类中选择
3. **精确匹配**：通过 性别 + 年龄 + 声音偏好 在种子对照表中匹配候选

## 🎨 新前端界面设计

### 界面布局建议

```
┌─────────────────────────────────────────────────────────┐
│                   角色声音配置                           │
├─────────────────────────────────────────────────────────┤
│ 角色名称: [输入框: 小明]                                │
│ 性    别: [下拉选择: 男性/女性]                          │
│ 年    龄: [下拉选择: 年轻/中年/其他]                     │
│ 声音风格: [分类选择: 文学风格/温柔风格/...]               │
├─────────────────────────────────────────────────────────┤
│ 匹配结果: [显示匹配的种子和描述]                        │
└─────────────────────────────────────────────────────────┘
```

### 前端选择流程

1. **性别选择** (男性/女性)
2. **年龄选择** (年轻/中年/其他)
3. **风格选择** (从9种声音偏好分类中选择)
4. **自动匹配** 系统根据 性别+年龄+风格 精确匹配种子

## 📋 声音偏好分类

### 可用风格选项

| 风格分类 | 描述 | 适用性别 | 适用年龄 |
|---------|------|----------|----------|
| **文学风格** | 知性文雅，适合朗读文学作品 | 男性 | 年轻 |
| **温柔风格** | 温和柔软，亲切自然 | 男性 | 年轻 |
| **专业风格** | 专业稳重，适合正式场合 | 男性 | 中年 |
| **港式风格** | 港式发音，独特魅力 | 男性 | 中年 |
| **深沉风格** | 低沉有力，权威感强 | 男性 | 中年 |
| **情感风格** | 情感丰富，表现力强 | 女性 | 年轻 |
| **深情风格** | 深情动人，温暖感人 | 女性 | 中年 |
| **清澈风格** | 清澈纯净，清晰明亮 | 女性 | 中年 |
| **平静风格** | 平静宁静，安详舒适 | 女性 | 中年 |

## 🔧 API 接口使用

### 1. 获取所有声音选项

```javascript
// GET /api/all-voice-combinations
const response = await fetch('/api/all-voice-combinations');
const data = await response.json();

// 响应结构
{
  "success": true,
  "data": {
    "声音偏好": {
      "文学风格": {
        "description": "知性文雅，适合朗读文学作品",
        "适用组合": [...]
      },
      // ... 其他风格
    },
    "性别选项": {"male": "男性", "female": "女性"},
    "年龄选项": {"年轻": "年轻", "中年": "中年", "其他": "其他"},
    "所有组合": [
      {
        "年龄": "年轻",
        "年龄显示": "年轻",
        "风格": "文学风格",
        "风格描述": "知性文雅，适合朗读文学作品",
        "支持性别": ["男性"],
        "候选种子": [{"种子": "111", "描述": "年轻男性 - 文学气质"}]
      },
      // ... 其他组合
    ],
    "统计信息": {
      "总风格数": 9,
      "总种子数": 9,
      "所有组合数": 9
    }
  }
}
```

### 2. 生成角色声音

```javascript
// POST /api/voice-seed
const response = await fetch('/api/voice-seed', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    gender: "男性",           // 前端使用中文
    age: "年轻",             // 年龄选项
    style: "文学风格",       // 声音偏好分类
    character_name: "小明"
  })
});

const result = await response.json();

// 响应示例
{
  "success": true,
  "data": {
    "seed": "111",
    "description": "年轻男性 - 文学气质",
    "gender": "男性",        // 前端友好的中文格式
    "age": "年轻",
    "style": "文学风格",
    "character_name": "小明"
  }
}
```

## 🎯 前端实现示例

### React 组件

```jsx
import React, { useState, useEffect } from 'react';

function VoicePreferenceSelector() {
  const [characterName, setCharacterName] = useState('');
  const [gender, setGender] = useState('男性');
  const [age, setAge] = useState('年轻');
  const [style, setStyle] = useState('');
  const [voiceData, setVoiceData] = useState(null);
  const [selectedSeed, setSelectedSeed] = useState(null);
  const [loading, setLoading] = useState(false);

  // 加载声音偏好数据
  useEffect(() => {
    loadVoicePreferences();
  }, []);

  const loadVoicePreferences = async () => {
    try {
      const response = await fetch('/api/all-voice-combinations');
      const result = await response.json();
      if (result.success) {
        setVoiceData(result.data);
      }
    } catch (error) {
      console.error('Failed to load voice preferences:', error);
    }
  };

  // 获取可用风格选项
  const getAvailableStyles = () => {
    if (!voiceData) return [];

    const allCombos = voiceData.所有组合 || [];
    return allCombos
      .filter(combo =>
        combo.支持性别.includes(gender) &&
        combo.年龄显示 === age
      )
      .map(combo => ({
        style: combo.风格,
        description: combo.风格描述,
        candidates: combo.候选种子
      }));
  };

  // 生成声音
  const handleGenerateVoice = async () => {
    if (!characterName || !style) {
      alert('请填写角色名称并选择声音风格');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/voice-seed', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          gender,
          age,
          style,
          character_name: characterName
        })
      });

      const result = await response.json();
      if (result.success) {
        setSelectedSeed(result.data);
      } else {
        alert('生成声音失败');
      }
    } catch (error) {
      console.error('Voice generation failed:', error);
      alert('生成声音失败');
    } finally {
      setLoading(false);
    }
  };

  const availableStyles = getAvailableStyles();

  return (
    <div className="voice-preference-selector">
      <h2>角色声音配置</h2>

      {/* 基本信息输入 */}
      <div className="form-section">
        <div className="form-group">
          <label>角色名称:</label>
          <input
            type="text"
            value={characterName}
            onChange={(e) => setCharacterName(e.target.value)}
            placeholder="请输入角色名称"
          />
        </div>

        <div className="form-group">
          <label>性别:</label>
          <select value={gender} onChange={(e) => setGender(e.target.value)}>
            <option value="男性">男性</option>
            <option value="女性">女性</option>
          </select>
        </div>

        <div className="form-group">
          <label>年龄:</label>
          <select value={age} onChange={(e) => setAge(e.target.value)}>
            {voiceData?.年龄选项 && Object.entries(voiceData.年龄选项).map(([key, value]) => (
              <option key={key} value={value}>{value}</option>
            ))}
          </select>
        </div>
      </div>

      {/* 声音风格选择 */}
      <div className="style-section">
        <h3>声音风格选择</h3>
        <div className="style-grid">
          {availableStyles.map((styleOption) => (
            <div
              key={styleOption.style}
              className={`style-card ${style === styleOption.style ? 'selected' : ''}`}
              onClick={() => setStyle(styleOption.style)}
            >
              <h4>{styleOption.style}</h4>
              <p>{styleOption.description}</p>
              <small>可选种子: {styleOption.candidates.length}个</small>
            </div>
          ))}
        </div>

        {availableStyles.length === 0 && (
          <p className="no-styles">暂无可用的声音风格选项</p>
        )}
      </div>

      {/* 生成按钮 */}
      <div className="action-section">
        <button
          onClick={handleGenerateVoice}
          disabled={!characterName || !style || loading}
          className="generate-btn"
        >
          {loading ? '生成中...' : '生成声音'}
        </button>
      </div>

      {/* 结果显示 */}
      {selectedSeed && (
        <div className="result-section">
          <h3>生成结果</h3>
          <div className="result-card">
            <p><strong>角色:</strong> {selectedSeed.character_name}</p>
            <p><strong>种子:</strong> {selectedSeed.seed}</p>
            <p><strong>性别:</strong> {selectedSeed.gender}</p>
            <p><strong>年龄:</strong> {selectedSeed.age}</p>
            <p><strong>风格:</strong> {selectedSeed.style}</p>
            <p><strong>描述:</strong> {selectedSeed.description}</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default VoicePreferenceSelector;
```

## 🔄 系统工作流程

### 完整匹配流程

```
用户选择: 男性 + 年轻 + 文学风格
    ↓
系统查找: voice_preferences.json 种子对照表
    ↓
精确匹配: gender="male", age="年轻", style="文学风格"
    ↓
找到种子: seed="111", description="年轻男性 - 文学气质"
    ↓
返回结果: 种子111 及描述信息
```

### 数据流程图

```
voice_preferences.json
    ├── 声音偏好 (分类描述)
    ├── 性别选项 (前端显示映射)
    ├── 年龄选项 (前端显示映射)
    └── 种子对照表 (精确匹配数据)
            ↓
    chattts_engine.py
    ├── get_voice_preferences_for_frontend()
    ├── get_candidates_by_preference()
    └── _find_seed_from_preferences()
            ↓
    app.py
    ├── map_frontend_gender_to_backend()
    └── map_backend_gender_to_frontend()
            ↓
    前端界面
    ├── 中文化显示
    ├── 分类选择
    └── 实时匹配
```

## 📊 数据结构详解

### 前端数据结构

```json
{
  "声音偏好": {
    "风格名称": {
      "description": "风格描述",
      "适用组合": [
        {
          "性别": "male/female",
          "性别显示": "男性/女性",
          "年龄": "年轻/中年/其他",
          "年龄显示": "年轻/中年/其他",
          "候选种子": [
            {
              "种子": "种子编号",
              "描述": "种子描述"
            }
          ]
        }
      ]
    }
  },
  "所有组合": [
    {
      "年龄": "年龄值",
      "年龄显示": "年龄显示值",
      "风格": "风格名称",
      "风格描述": "风格描述",
      "支持性别": ["性别显示1", "性别显示2"],
      "候选种子": [...]
    }
  ]
}
```

## ✨ 系统优势

1. **用户友好**
   - 完全中文化界面
   - 直观的分类选择
   - 清晰的描述信息

2. **精确匹配**
   - 性别 + 年龄 + 风格三重匹配
   - 基于JSON配置的种子管理
   - 一致性保证

3. **灵活扩展**
   - 易于添加新风格
   - 支持多种子候选
   - 配置驱动的设计

4. **前后端分离**
   - 中文性别映射
   - RESTful API设计
   - 前端友好的数据格式

## 🚀 快速开始

1. **查看可用选项**
   ```bash
   curl http://localhost:5000/api/all-voice-combinations
   ```

2. **创建角色声音**
   ```bash
   curl -X POST http://localhost:5000/api/voice-seed \
     -H "Content-Type: application/json" \
     -d '{
       "gender": "男性",
       "age": "年轻",
       "style": "文学风格",
       "character_name": "小明"
     }'
   ```

3. **运行测试验证**
   ```bash
   python test_new_voice_preference_system.py
   ```

## 📝 更新日志

### v2.0.0 - 风格分类系统
- ✅ 实现基于风格分类的声音选择
- ✅ 支持年龄选择功能
- ✅ 完善性别+年龄+风格精确匹配
- ✅ 前端中文化支持
- ✅ 新增测试验证脚本

### v1.0.0 - 基础系统
- ✅ ChatTTS引擎集成
- ✅ 基础种子选择
- ✅ JSON配置支持

---

现在前端用户可以享受基于风格分类的直观声音选择体验！🎉