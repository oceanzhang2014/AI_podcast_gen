# 精确种子映射系统使用指南

## 概述

系统现在完全基于 `voice_preferences.json` 中的种子对照表进行精确匹配。前端可以获取 age + style 的组合，系统会根据 gender + age + style 的完全匹配来选择种子，如果有多个候选则随机选取。

## 核心特性 ✅

### 1. 精确匹配系统
- **gender + age + style**: 三个条件必须完全匹配
- **候选种子**: 显示所有符合条件的种子供随机选择
- **角色一致性**: 同一角色始终使用相同的种子

### 2. 随机选择机制
- **单候选**: 直接选择唯一匹配的种子
- **多候选**: 从匹配的种子中随机选择
- **缓存机制**: 确保角色音色一致性

### 3. 灵活扩展
- **JSON 配置**: 只需在 JSON 文件中添加新种子
- **无需代码修改**: 添加种子后系统自动识别
- **中文显示**: 所有选项使用中文描述

## JSON 文件结构

### 种子对照表格式

```json
{
  "种子对照表": {
    "种子数字": {
      "gender": "male|female",
      "age": "年轻|中年|其他",
      "style": "风格名称",
      "description": "中文描述"
    }
  }
}
```

### 示例条目

```json
{
  "种子对照表": {
    "2": {
      "gender": "female",
      "age": "年轻",
      "style": "情感风格",
      "description": "年轻女性 - 情感丰富"
    },
    "111": {
      "gender": "male",
      "age": "年轻",
      "style": "文学风格",
      "description": "年轻男性 - 文学气质"
    }
  }
}
```

## 扩展新种子

### 1. 添加单个种子

在 `voice_preferences.json` 的 `种子对照表` 中添加新条目：

```json
{
  "种子对照表": {
    "2001": {
      "gender": "female",
      "age": "年轻",
      "style": "可爱风格",
      "description": "年轻女性 - 可爱甜美"
    }
  }
}
```

### 2. 添加多个候选种子

为同一组合添加多个种子以支持随机选择：

```json
{
  "种子对照表": {
    "2": {
      "gender": "female",
      "age": "年轻",
      "style": "情感风格",
      "description": "年轻女性 - 情感丰富"
    },
    "2002": {
      "gender": "female",
      "age": "年轻",
      "style": "情感风格",
      "description": "年轻女性 - 情感丰富变体"
    },
    "2003": {
      "gender": "female",
      "age": "年轻",
      "style": "情感风格",
      "description": "年轻女性 - 情感丰富变体2"
    }
  }
}
```

这样当请求 `female + 年轻 + 情感风格` 时，系统会从种子 [2, 2002, 2003] 中随机选择。

### 3. 更新声音偏好结构（可选）

为了保持一致性，同时更新 `声音偏好` 部分：

```json
{
  "声音偏好": {
    "情感风格": {
      "description": "情感丰富，表现力强",
      "female": {
        "年轻": {
          "seed": [2, 2002, 2003],
          "description": "年轻女性 - 情感丰富（多版本）"
        }
      }
    }
  }
}
```

## API 使用方式

### 1. 获取声音偏好（age + style 组合）

**请求**: `GET /api/voice-preferences`

**响应示例**:
```json
{
  "success": true,
  "data": {
    "声音偏好": {
      "女性": {
        "性别": "female",
        "年龄风格组合": [
          {
            "年龄": "年轻",
            "风格": "情感风格",
            "候选种子": [
              {"种子": "2", "描述": "年轻女性 - 情感丰富", "年龄": "年轻", "风格": "情感风格"},
              {"种子": "2002", "描述": "年轻女性 - 情感丰富变体", "年龄": "年轻", "风格": "情感风格"}
            ],
            "候选数量": 2
          }
        ]
      }
    }
  }
}
```

### 2. 获取特定种子（随机选择）

**请求**: `POST /api/voice-seed`

**请求体**:
```json
{
  "gender": "female",
  "age": "年轻",
  "style": "情感风格",
  "character_name": "小红"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "seed": "2002",
    "description": "年轻女性 - 情感丰富变体",
    "gender": "female",
    "age": "年轻",
    "style": "情感风格",
    "character_name": "小红",
    "personality_used": "年轻 情感风格"
  }
}
```

### 3. 获取所有候选种子

**请求**: `POST /api/voice-candidates`

**请求体**:
```json
{
  "gender": "female",
  "age": "年轻",
  "style": "情感风格"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "candidates": [
      {
        "seed": "2",
        "description": "年轻女性 - 情感丰富",
        "gender": "female",
        "age": "年轻",
        "style": "情感风格"
      },
      {
        "seed": "2002",
        "description": "年轻女性 - 情感丰富变体",
        "gender": "female",
        "age": "年轻",
        "style": "情感风格"
      }
    ],
    "count": 2,
    "filters": {
      "gender": "female",
      "age": "年轻",
      "style": "情感风格"
    }
  }
}
```

### 4. 获取某性别的所有组合

**请求**: `GET /api/voice-combinations/female`

**响应示例**:
```json
{
  "success": true,
  "data": {
    "gender": "female",
    "combinations": [
      {
        "年龄": "年轻",
        "风格": "情感风格",
        "候选种子": ["2", "2002", "2003"],
        "描述": ["年轻女性 - 情感丰富", "年轻女性 - 情感丰富变体", "年轻女性 - 情感丰富变体2"]
      }
    ],
    "total_combinations": 1
  }
}
```

## 前端集成示例

### React 组件示例

```jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

function VoiceSelectorWithRandomSelection() {
  const [preferences, setPreferences] = useState(null);
  const [selectedGender, setSelectedGender] = useState('');
  const [availableCombinations, setAvailableCombinations] = useState([]);
  const [selectedCombination, setSelectedCombination] = useState(null);
  const [characterName, setCharacterName] = useState('');
  const [selectedSeed, setSelectedSeed] = useState(null);

  // 加载声音偏好
  useEffect(() => {
    loadVoicePreferences();
  }, []);

  // 根据性别加载可用组合
  useEffect(() => {
    if (selectedGender) {
      loadAvailableCombinations(selectedGender);
    }
  }, [selectedGender]);

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

  const loadAvailableCombinations = async (gender) => {
    try {
      const response = await axios.get(`/api/voice-combinations/${gender}`);
      if (response.data.success) {
        setAvailableCombinations(response.data.data.combinations);
      }
    } catch (error) {
      console.error('Failed to load combinations:', error);
    }
  };

  const handleSelectVoice = async () => {
    if (!selectedGender || !selectedCombination || !characterName) {
      alert('请完整填写选择信息');
      return;
    }

    try {
      const response = await axios.post('/api/voice-seed', {
        gender: selectedGender,
        age: selectedCombination.年龄,
        style: selectedCombination.风格,
        character_name: characterName
      });

      if (response.data.success) {
        setSelectedSeed(response.data.data);
        alert(`为角色 ${characterName} 随机选择了种子: ${response.data.data.seed}`);
      }
    } catch (error) {
      console.error('Failed to select voice:', error);
      alert('选择声音失败');
    }
  };

  const handleShowCandidates = async () => {
    if (!selectedGender || !selectedCombination) return;

    try {
      const response = await axios.post('/api/voice-candidates', {
        gender: selectedGender,
        age: selectedCombination.年龄,
        style: selectedCombination.风格
      });

      if (response.data.success) {
        const candidates = response.data.data.candidates;
        alert(`候选种子: ${candidates.map(c => c.seed).join(', ')} (${candidates.length}个)`);
      }
    } catch (error) {
      console.error('Failed to get candidates:', error);
    }
  };

  if (!preferences) {
    return <div>加载中...</div>;
  }

  return (
    <div className="voice-selector">
      <h3>声音选择器 (支持随机选择)</h3>

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
        <div className="form-group">
          <label>年龄+风格组合:</label>
          <select
            value={selectedCombination ? `${selectedCombination.年龄}+${selectedCombination.风格}` : ''}
            onChange={(e) => {
              const [age, style] = e.target.value.split('+');
              const combination = availableCombinations.find(c => c.年龄 === age && c.风格 === style);
              setSelectedCombination(combination);
            }}
          >
            <option value="">请选择组合</option>
            {availableCombinations.map((combo, index) => (
              <option key={index} value={`${combo.年龄}+${combo.风格}`}>
                {combo.年龄} + {combo.风格} ({combo.候选种子.length}个候选)
              </option>
            ))}
          </select>
        </div>
      )}

      {selectedCombination && (
        <div className="combination-info">
          <p><strong>选择组合:</strong> {selectedCombination.年龄} + {selectedCombination.风格}</p>
          <p><strong>候选种子:</strong> {selectedCombination.候选种子.map(s => s.种子).join(', ')}</p>
          <p><strong>候选数量:</strong> {selectedCombination.候选种子.length}</p>
        </div>
      )}

      <div className="button-group">
        <button onClick={handleShowCandidates} disabled={!selectedCombination}>
          查看候选种子
        </button>
        <button onClick={handleSelectVoice} disabled={!selectedGender || !selectedCombination || !characterName}>
          随机选择种子
        </button>
      </div>

      {selectedSeed && (
        <div className="selected-seed">
          <h4>已选择种子:</h4>
          <p><strong>种子:</strong> {selectedSeed.seed}</p>
          <p><strong>描述:</strong> {selectedSeed.description}</p>
          <p><strong>角色:</strong> {selectedSeed.character_name}</p>
        </div>
      )}
    </div>
  );
}

export default VoiceSelectorWithRandomSelection;
```

## 最佳实践

### 1. 种子编号建议

- **范围**: 使用 4-5 位数字避免冲突
- **分类**: 按性别或风格分配编号范围
  - 女性: 2000-2999
  - 男性: 3000-3999
- **记录**: 维护种子编号使用记录

### 2. 描述规范

- **格式**: 年龄 + 性别 - 特征描述
- **一致性**: 相同特征的描述保持一致
- **详细性**: 提供足够详细的特征说明

### 3. 随机选择策略

- **单一角色**: 使用缓存确保一致性
- **批量创建**: 不同角色可使用不同种子
- **种子池**: 为重要组合提供多个候选

### 4. 测试验证

- **添加种子后**: 运行测试脚本验证功能
- **前端集成**: 测试 API 接口响应
- **音频生成**: 验证新种子音频质量

## 系统优势

### 1. 完全可控
- **用户控制**: 通过 JSON 文件完全控制种子映射
- **灵活扩展**: 无需修改代码即可添加新种子
- **透明性**: 种子选择逻辑完全透明

### 2. 随机性 + 一致性
- **随机选择**: 支持从多个候选中随机选择
- **角色一致性**: 同一角色始终使用相同种子
- **多样性**: 为相同特征提供多种音色选择

### 3. 开发友好
- **API 完整**: 提供完整的 API 接口
- **文档完善**: 详细的使用说明和示例
- **测试充分**: 全面的测试验证

现在您可以随时在 `voice_preferences.json` 中添加新种子，系统会自动识别并提供随机选择功能！