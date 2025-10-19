# 前端声音偏好集成指南

## 概述

系统现在支持通过 JSON 配置文件管理声音偏好，前端可以通过 API 接口获取所有可用的声音选项，并根据性别、年龄和风格确定合适的种子。

## API 接口

### 1. 获取声音偏好列表

**接口**: `GET /api/voice-preferences`

**响应示例**:
```json
{
  "success": true,
  "data": {
    "声音偏好": {
      "文学风格": {
        "description": "知性文雅，适合朗读文学作品",
        "选项": [
          {
            "性别": "male",
            "年龄": "年轻",
            "种子": 111,
            "描述": "年轻男性 - 文学气质"
          }
        ]
      },
      "温柔风格": {
        "description": "温和柔软，亲切自然",
        "选项": [
          {
            "性别": "male",
            "年龄": "年轻",
            "种子": 333,
            "描述": "年轻男性 - 温柔体贴"
          },
          {
            "性别": "female",
            "年龄": "年轻",
            "种子": 2,
            "描述": "年轻女性 - 情感丰富温柔"
          },
          {
            "性别": "female",
            "年龄": "其他",
            "种子": 3333,
            "描述": "女性 - 平静温柔"
          }
        ]
      }
    },
    "性别选项": {
      "male": "男性",
      "female": "女性"
    }
  },
  "timestamp": "2025-10-19T08:30:00.000Z"
}
```

### 2. 获取特定种子

**接口**: `POST /api/voice-seed`

**请求体**:
```json
{
  "gender": "female",
  "age": "年轻",
  "style": "温柔风格",
  "character_name": "李丽"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "seed": "2",
    "description": "年轻女性 - 情感丰富温柔",
    "gender": "female",
    "age": "年轻",
    "style": "温柔风格",
    "character_name": "李丽",
    "personality_used": "年轻 温柔风格"
  },
  "timestamp": "2025-10-19T08:30:00.000Z"
}
```

## 前端实现示例

### JavaScript/Axios 示例

```javascript
// 获取声音偏好列表
async function getVoicePreferences() {
  try {
    const response = await axios.get('/api/voice-preferences');
    if (response.data.success) {
      return response.data.data;
    } else {
      throw new Error(response.data.error);
    }
  } catch (error) {
    console.error('Failed to get voice preferences:', error);
    return null;
  }
}

// 获取特定种子
async function getVoiceSeed(gender, age, style, characterName) {
  try {
    const response = await axios.post('/api/voice-seed', {
      gender: gender,
      age: age,
      style: style,
      character_name: characterName
    });

    if (response.data.success) {
      return response.data.data;
    } else {
      throw new Error(response.data.error);
    }
  } catch (error) {
    console.error('Failed to get voice seed:', error);
    return null;
  }
}

// 使用示例
async function exampleUsage() {
  // 1. 获取所有声音偏好
  const preferences = await getVoicePreferences();

  if (preferences) {
    console.log('可用声音风格:', Object.keys(preferences.声音偏好));
    console.log('性别选项:', preferences.性别选项);

    // 2. 为角色选择声音
    const characterName = "李丽";
    const gender = "female";
    const age = "年轻";
    const style = "温柔风格";

    const seedInfo = await getVoiceSeed(gender, age, style, characterName);

    if (seedInfo) {
      console.log(`角色 ${characterName} 的种子:`, seedInfo.seed);
      console.log(`描述:`, seedInfo.description);
    }
  }
}
```

### React 组件示例

```jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

function VoiceSelector({ onVoiceSelect }) {
  const [preferences, setPreferences] = useState(null);
  const [selectedGender, setSelectedGender] = useState('');
  const [selectedStyle, setSelectedStyle] = useState('');
  const [selectedAge, setSelectedAge] = useState('');
  const [characterName, setCharacterName] = useState('');

  useEffect(() => {
    // 加载声音偏好
    loadVoicePreferences();
  }, []);

  const loadVoicePreferences = async () => {
    try {
      const response = await axios.get('/api/voice-preferences');
      if (response.data.success) {
        setPreferences(response.data.data);
      }
    } catch (error) {
      console.error('Failed to load voice preferences:', error);
    }
  };

  const getAvailableOptions = () => {
    if (!preferences || !selectedGender) return [];

    const allOptions = [];
    Object.entries(preferences.声音偏好).forEach(([style, styleData]) => {
      styleData.选项.forEach(option => {
        if (option.性别 === selectedGender) {
          allOptions.push({
            style: style,
            age: option.年龄,
            seed: option.种子,
            description: option.描述
          });
        }
      });
    });

    return allOptions;
  };

  const handleConfirmSelection = async () => {
    if (!selectedGender || !selectedStyle || !characterName) {
      alert('请填写完整的选择信息');
      return;
    }

    try {
      const response = await axios.post('/api/voice-seed', {
        gender: selectedGender,
        age: selectedAge,
        style: selectedStyle,
        character_name: characterName
      });

      if (response.data.success) {
        onVoiceSelect && onVoiceSelect(response.data.data);
        alert(`已为角色 ${characterName} 选择种子: ${response.data.data.seed}`);
      }
    } catch (error) {
      console.error('Failed to get voice seed:', error);
      alert('选择声音失败');
    }
  };

  if (!preferences) {
    return <div>加载中...</div>;
  }

  const availableOptions = getAvailableOptions();
  const uniqueStyles = [...new Set(availableOptions.map(opt => opt.style))];
  const uniqueAges = [...new Set(availableOptions.map(opt => opt.age))];

  return (
    <div className="voice-selector">
      <h3>声音选择器</h3>

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
        <select value={selectedGender} onChange={(e) => setSelectedGender(e.target.value)}>
          <option value="">请选择性别</option>
          {Object.entries(preferences.性别选项).map(([key, value]) => (
            <option key={key} value={key}>{value}</option>
          ))}
        </select>
      </div>

      {selectedGender && (
        <>
          <div className="form-group">
            <label>声音风格:</label>
            <select value={selectedStyle} onChange={(e) => setSelectedStyle(e.target.value)}>
              <option value="">请选择风格</option>
              {uniqueStyles.map(style => (
                <option key={style} value={style}>{style}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>年龄:</label>
            <select value={selectedAge} onChange={(e) => setSelectedAge(e.target.value)}>
              <option value="">请选择年龄</option>
              {uniqueAges.map(age => (
                <option key={age} value={age}>{age}</option>
              ))}
            </select>
          </div>
        </>
      )}

      {selectedStyle && selectedAge && (
        <div className="selected-info">
          <p>
            选择了: {preferences.性别选项[selectedGender]} - {selectedAge} - {selectedStyle}
          </p>
        </div>
      )}

      <button onClick={handleConfirmSelection} disabled={!selectedGender || !selectedStyle || !characterName}>
        确认选择
      </button>
    </div>
  );
}

export default VoiceSelector;
```

## 声音风格对照表

### 可用风格列表

| 风格名称 | 描述 | 适用性别 | 适用年龄 | 种子 |
|---------|------|---------|---------|------|
| 文学风格 | 知性文雅，适合朗读文学作品 | 男性 | 年轻 | 111 |
| 温柔风格 | 温和柔软，亲切自然 | 男性/女性 | 年轻/其他 | 333/2/3333 |
| 专业风格 | 专业稳重，适合正式场合 | 男性/女性 | 中年/其他 | 666/1111 |
| 港式风格 | 港式发音，独特魅力 | 男性 | 中年 | 7777 |
| 深沉风格 | 低沉有力，权威感强 | 男性 | 中年 | 9999 |
| 情感风格 | 情感丰富，表现力强 | 女性 | 年轻 | 2 |
| 深情风格 | 深情动人，温暖感人 | 女性 | 中年 | 4 |
| 清澈风格 | 清澈纯净，清晰明亮 | 女性 | 中年 | 1111 |
| 平静风格 | 平静宁静，安详舒适 | 女性 | 中年 | 3333 |

### 前端显示建议

1. **性别选择**: 使用下拉菜单显示 "男性" 和 "女性"
2. **风格选择**: 根据选择的性别动态显示可用的风格
3. **年龄选择**: 根据性别和风格组合显示可用的年龄选项
4. **预览功能**: 可以播放示例音频让用户预览效果
5. **角色管理**: 为不同角色保存声音设置

## 错误处理

### 常见错误类型

1. `tts_unavailable`: TTS 引擎不可用
2. `validation_error`: 请求参数验证失败
3. `server_error`: 服务器内部错误

### 错误处理示例

```javascript
try {
  const seedInfo = await getVoiceSeed(gender, age, style, characterName);
  // 处理成功结果
} catch (error) {
  if (error.response) {
    const { error_type, error } = error.response.data;

    switch (error_type) {
      case 'tts_unavailable':
        showError('语音服务暂时不可用，请稍后重试');
        break;
      case 'validation_error':
        showError('请求参数不正确，请检查输入');
        break;
      case 'server_error':
        showError('服务器错误，请稍后重试');
        break;
      default:
        showError('未知错误');
    }
  } else {
    showError('网络错误，请检查连接');
  }
}
```

## 最佳实践

1. **缓存声音偏好**: 前端可以缓存声音偏好列表，避免重复请求
2. **预加载选项**: 在页面加载时获取声音偏好，提升用户体验
3. **输入验证**: 在发送请求前验证用户输入的有效性
4. **用户反馈**: 提供清晰的加载状态和错误提示
5. **响应式设计**: 确保在移动设备上也能良好使用

## 更新和维护

- JSON 配置文件 `voice_preferences.json` 可以在不修改代码的情况下更新声音偏好
- 新增声音风格只需在 JSON 文件中添加相应配置
- 前端会自动获取最新的配置，无需更新代码