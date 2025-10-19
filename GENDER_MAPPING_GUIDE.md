# 前后端性别映射使用指南

## 概述

系统现在完美支持前端使用中文性别（"男性"、"女性"），后端使用英文性别（"male"、"female"）的无缝映射。

## 映射关系 🔄

### 前端 → 后端映射
```javascript
// 前端发送中文性别
"男性" → "male"
"女性" → "female"

// 前端也可以直接发送英文性别
"male" → "male"
"female" → "female"
```

### 后端 → 前端映射
```javascript
// 后端返回中文性别给前端
"male" → "男性"
"female" → "女性"
```

## API 使用方式

### 1. 请求时支持中文性别

**请求示例**:
```json
{
  "gender": "男性",  // 或者 "女性"
  "age": "年轻",
  "style": "文学风格",
  "character_name": "小明"
}
```

**或者使用英文**:
```json
{
  "gender": "male",  // 或者 "female"
  "age": "年轻",
  "style": "文学风格",
  "character_name": "小明"
}
```

### 2. 响应时返回中文性别

**响应示例**:
```json
{
  "success": true,
  "data": {
    "seed": "111",
    "description": "年轻男性 - 文学气质",
    "gender": "男性",        // 前端友好的中文格式
    "gender_backend": "male", // 后端实际使用的格式（供参考）
    "age": "年轻",
    "style": "文学风格",
    "character_name": "小明"
  }
}
```

### 3. 前端数据格式

**获取所有组合时的性别显示**:
```json
{
  "success": true,
  "data": {
    "性别选项": {
      "male": "男性",
      "female": "女性"
    },
    "性别映射": {
      "male": "男性",
      "female": "女性"
    },
    "所有组合": [
      {
        "年龄": "年轻",
        "风格": "文学风格",
        "支持性别": ["男性"],  // 中文显示
        "候选种子": [
          {
            "种子": "111",
            "描述": "年轻男性 - 文学气质",
            "性别": "male",
            "性别显示": "男性"  // 中文显示
          }
        ]
      }
    ],
    "声音偏好": {
      "男性": {
        "性别": "male",        // 后端键
        "性别显示": "男性",    // 前端显示
        "年龄风格组合": [...]
      }
    }
  }
}
```

## 前端实现示例

### React 组件示例

```jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

function VoiceSelectorWithChineseGender() {
  const [gender, setGender] = useState('男性');
  const [combinations, setCombinations] = useState([]);
  const [selectedCombo, setSelectedCombo] = useState(null);
  const [characterName, setCharacterName] = useState('');
  const [selectedSeed, setSelectedSeed] = useState(null);

  useEffect(() => {
    loadVoicePreferences();
  }, []);

  const loadVoicePreferences = async () => {
    try {
      const response = await axios.get('/api/all-voice-combinations');
      if (response.data.success) {
        const data = response.data.data;
        setCombinations(data.所有组合 || []);
      }
    } catch (error) {
      console.error('Failed to load voice preferences:', error);
    }
  };

  const handleSelectCombination = (combination) => {
    setSelectedCombination(combination);
  };

  const handleGenerateVoice = async () => {
    if (!selectedCombo || !characterName) {
      alert('请选择声音组合并输入角色名称');
      return;
    }

    try {
      const response = await axios.post('/api/voice-seed', {
        gender: gender,  // 直接使用中文性别
        age: selectedCombo.年龄,
        style: selectedCombo.风格,
        character_name: characterName
      });

      if (response.data.success) {
        setSelectedSeed(response.data.data);
        alert(`为角色 ${characterName} 选择了种子: ${response.data.data.seed}`);
      }
    } catch (error) {
      console.error('Failed to generate voice:', error);
      alert('生成声音失败');
    }
  };

  const filterCombinationsByGender = () => {
    if (gender === '全部') {
      return combinations;
    }
    return combinations.filter(combo => combo.支持性别.includes(gender));
  };

  const filteredCombinations = filterCombinationsByGender();

  return (
    <div className="voice-selector">
      <h2>声音选择器 (中文性别支持)</h2>

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
          <option value="全部">全部</option>
          <option value="男性">男性</option>
          <option value="女性">女性</option>
        </select>
      </div>

      <div className="combinations-grid">
        <h3>声音组合 ({filteredCombinations.length}个)</h3>
        {filteredCombinations.map((combo, index) => (
          <div
            key={index}
            className={`combination-card ${selectedCombo === combo ? 'selected' : ''}`}
            onClick={() => handleSelectCombination(combo)}
          >
            <h4>{combo.年龄} + {combo.风格}</h4>
            <p><strong>支持性别:</strong> {combo.支持性别.join(', ')}</p>
            <p><strong>候选种子:</strong> {combo.候选种子.length}个</p>
            {combo.候选种子[0] && (
              <p><strong>示例:</strong> {combo.候选种子[0].描述}</p>
            )}
          </div>
        ))}
      </div>

      {selectedCombo && (
        <div className="action-section">
          <h3>已选择: {selectedCombo.年龄} + {selectedCombo.风格}</h3>
          <p>性别: {gender} | 支持性别: {selectedCombo.支持性别.join(', ')}</p>
          <button onClick={handleGenerateVoice}>
            生成声音 (角色: {characterName})
          </button>
        </div>
      )}

      {selectedSeed && (
        <div className="result-section">
          <h4>生成结果:</h4>
          <p><strong>种子:</strong> {selectedSeed.seed}</p>
          <p><strong>描述:</strong> {selectedSeed.description}</p>
          <p><strong>性别:</strong> {selectedSeed.gender}</p>
          <p><strong>角色:</strong> {selectedSeed.character_name}</p>
        </div>
      )}
    </div>
  );
}

export default VoiceSelectorWithChineseGender;
```

### Vue.js 示例

```vue
<template>
  <div class="voice-selector">
    <h2>声音选择器</h2>

    <div class="form-group">
      <label>角色名称:</label>
      <input v-model="characterName" placeholder="请输入角色名称">
    </div>

    <div class="form-group">
      <label>性别:</label>
      <select v-model="selectedGender">
        <option value="全部">全部</option>
        <option value="男性">男性</option>
        <option value="女性">女性</option>
      </select>
    </div>

    <div class="combinations-list">
      <h3>声音组合 ({{ filteredCombinations.length }}个)</h3>

      <div
        v-for="(combo, index) in filteredCombinations"
        :key="index"
        class="combination-item"
        :class="{ selected: selectedCombo === combo }"
        @click="selectCombination(combo)"
      >
        <h4>{{ combo.年龄 }} + {{ combo.风格 }}</h4>
        <p><strong>支持性别:</strong> {{ combo.支持性别.join(', ') }}</p>
        <p><strong>候选种子:</strong> {{ combo.候选种子.length }}个</p>
        <p v-if="combo.候选种子[0]">
          <strong>示例:</strong> {{ combo.候选种子[0].描述 }}
        </p>
      </div>
    </div>

    <div v-if="selectedCombo" class="action-section">
      <h3>已选择: {{ selectedCombo.年龄 }} + {{ selectedCombo.风格 }}</h3>
      <button @click="generateVoice" :disabled="!characterName">
        生成声音
      </button>
    </div>

    <div v-if="generatedSeed" class="result-section">
      <h4>生成结果:</h4>
      <p><strong>种子:</strong> {{ generatedSeed.seed }}</p>
      <p><strong>描述:</strong> {{ generatedSeed.description }}</p>
      <p><strong>性别:</strong> {{ generatedSeed.gender }}</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      characterName: '',
      selectedGender: '全部',
      combinations: [],
      selectedCombo: null,
      generatedSeed: null
    };
  },

  computed: {
    filteredCombinations() {
      if (this.selectedGender === '全部') {
        return this.combinations;
      }
      return this.combinations.filter(combo =>
        combo.支持性别.includes(this.selectedGender)
      );
    }
  },

  async mounted() {
    await this.loadVoicePreferences();
  },

  methods: {
    async loadVoicePreferences() {
      try {
        const response = await axios.get('/api/all-voice-combinations');
        if (response.data.success) {
          this.combinations = response.data.data.所有组合 || [];
        }
      } catch (error) {
        console.error('Failed to load voice preferences:', error);
      }
    },

    selectCombination(combination) {
      this.selectedCombo = combination;
    },

    async generateVoice() {
      if (!this.selectedCombo || !this.characterName) {
        alert('请选择声音组合并输入角色名称');
        return;
      }

      try {
        const response = await axios.post('/api/voice-seed', {
          gender: this.selectedGender,  // 使用中文性别
          age: this.selectedCombo.年龄,
          style: this.selectedCombo.风格,
          character_name: this.characterName
        });

        if (response.data.success) {
          this.generatedSeed = response.data.data;
          alert(`为角色 ${this.characterName} 选择了种子: ${response.data.data.seed}`);
        }
      } catch (error) {
        console.error('Failed to generate voice:', error);
        alert('生成声音失败');
      }
    }
  }
};
</script>
```

## 最佳实践

### 1. 前端一致性
- **始终使用中文性别**: 在前端界面中统一显示"男性"、"女性"
- **API 请求**: 发送中文性别给后端，系统会自动转换
- **响应处理**: 接收响应中的中文性别字段

### 2. 错误处理
```javascript
// 性别映射错误处理
try {
  const response = await axios.post('/api/voice-seed', {
    gender: '男性',  // 前端使用中文
    // ... 其他参数
  });

  const gender = response.data.data.gender;  // 响应中的中文性别
  // 使用 gender 进行界面显示
} catch (error) {
  console.error('Voice generation failed:', error);
}
```

### 3. 性别筛选
```javascript
// 根据中文性别筛选组合
const maleCombinations = allCombinations.filter(combo =>
  combo.支持性别.includes('男性')
);

const femaleCombinations = allCombinations.filter(combo =>
  combo.支持性别.includes('女性')
);
```

### 4. 数据缓存
```javascript
// 缓存性别映射关系
const genderMapping = {
  '男性': 'male',
  '女性': 'female'
};

// 缓存所有组合数据
const cachedCombinations = null;

async function getCachedCombinations() {
  if (!cachedCombinations) {
    const response = await axios.get('/api/all-voice-combinations');
    cachedCombinations = response.data.data.所有组合;
  }
  return cachedCombinations;
}
```

## API 变更说明

### 更新的接口

1. **POST /api/voice-seed**
   - 输入: 支持 "男性"、"女性"、"male"、"female"
   - 输出: 返回中文性别字段 `gender`

2. **POST /api/voice-candidates**
   - 输入: 支持中文和英文性别
   - 输出: 返回中文性别字段 `gender`

3. **GET /api/all-voice-combinations**
   - 输出: 包含性别映射关系

### 向后兼容性

- **英文性别**: 系统继续支持使用 "male"、"female"
- **中文性别**: 新增支持 "男性"、"女性"
- **响应格式**: 优先返回中文性别，同时提供后端格式供参考

## 优势

1. **用户体验**: 前端显示完全中文化，符合中国用户习惯
2. **向后兼容**: 保持对英文性别的支持
3. **自动化映射**: 无需手动转换，系统自动处理
4. **类型安全**: 包含类型检查和错误处理
5. **调试友好**: 响应中包含后端格式，便于调试

现在前端可以完美使用中文性别"男性"、"女性"，系统会自动与后端的"male"、"female"进行映射！🎯