# 前端所有组合显示指南

## 概述

系统现在支持前端显示 `voice_preferences.json` 中**所有种子**的**不同 age + style 组合**。前端可以获取完整的组合列表，包括每个组合支持哪些性别以及有多少个候选种子。

## 当前 JSON 中的所有组合

基于当前的 `voice_preferences.json`，系统识别出以下所有唯一的 age + style 组合：

### 男性组合 (5个)
1. **年轻 + 文学风格** - 支持: male - 1个候选种子 (111)
2. **年轻 + 温柔风格** - 支持: male - 1个候选种子 (333)
3. **中年 + 专业风格** - 支持: male - 1个候选种子 (666)
4. **中年 + 港式风格** - 支持: male - 1个候选种子 (7777)
5. **中年 + 深沉风格** - 支持: male - 1个候选种子 (9999)

### 女性组合 (4个)
1. **年轻 + 情感风格** - 支持: female - 1个候选种子 (2)
2. **中年 + 深情风格** - 支持: female - 1个候选种子 (4)
3. **中年 + 清澈风格** - 支持: female - 1个候选种子 (1111)
4. **中年 + 平静风格** - 支持: female - 1个候选种子 (3333)

## API 接口

### 1. 获取所有组合

**接口**: `GET /api/all-voice-combinations`

**响应示例**:
```json
{
  "success": true,
  "data": {
    "所有组合": [
      {
        "年龄": "年轻",
        "风格": "文学风格",
        "候选种子": [
          {
            "种子": "111",
            "描述": "年轻男性 - 文学气质",
            "性别": "male"
          }
        ],
        "支持性别": ["male"]
      },
      {
        "年龄": "年轻",
        "风格": "情感风格",
        "候选种子": [
          {
            "种子": "2",
            "描述": "年轻女性 - 情感丰富",
            "性别": "female"
          }
        ],
        "支持性别": ["female"]
      }
    ],
    "按性别分类": {
      "男性": {
        "性别": "male",
        "年龄风格组合": [
          {
            "年龄": "年轻",
            "风格": "文学风格",
            "候选种子": [{"种子": "111", "描述": "年轻男性 - 文学气质", "性别": "male"}],
            "候选数量": 1,
            "总候选数": 1
          }
        ]
      },
      "女性": {
        "性别": "female",
        "年龄风格组合": [
          {
            "年龄": "年轻",
            "风格": "情感风格",
            "候选种子": [{"种子": "2", "描述": "年轻女性 - 情感丰富", "性别": "female"}],
            "候选数量": 1,
            "总候选数": 1
          }
        ]
      }
    },
    "性别选项": {
      "male": "男性",
      "female": "女性"
    },
    "统计信息": {
      "总组合数": 9,
      "总种子数": 9,
      "男性组合数": 5,
      "女性组合数": 4
    }
  }
}
```

### 2. 获取特定性别的组合

**接口**: `GET /api/voice-combinations/{gender}`

**示例**: `GET /api/voice-combinations/female`

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
        "候选种子": ["2"],
        "描述": ["年轻女性 - 情感丰富"]
      },
      {
        "年龄": "中年",
        "风格": "深情风格",
        "候选种子": ["4"],
        "描述": ["中年女性 - 深情动人"]
      }
    ],
    "total_combinations": 4
  }
}
```

## 前端实现示例

### React 组件示例 - 显示所有组合

```jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

function AllVoiceCombinationsDisplay() {
  const [allCombinations, setAllCombinations] = useState([]);
  const [filteredCombinations, setFilteredCombinations] = useState([]);
  const [selectedGender, setSelectedGender] = useState('all');
  const [selectedCombination, setSelectedCombination] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAllCombinations();
  }, []);

  useEffect(() => {
    filterCombinations();
  }, [selectedGender, allCombinations]);

  const loadAllCombinations = async () => {
    try {
      const response = await axios.get('/api/all-voice-combinations');
      if (response.data.success) {
        setAllCombinations(response.data.data.所有组合);
        setLoading(false);
      }
    } catch (error) {
      console.error('Failed to load combinations:', error);
      setLoading(false);
    }
  };

  const filterCombinations = () => {
    if (selectedGender === 'all') {
      setFilteredCombinations(allCombinations);
    } else {
      const filtered = allCombinations.filter(combo =>
        combo.支持性别.includes(selectedGender)
      );
      setFilteredCombinations(filtered);
    }
  };

  const handleSelectCombination = (combination) => {
    setSelectedCombination(combination);
  };

  const handleGenerateVoice = async () => {
    if (!selectedCombination) {
      alert('请先选择一个声音组合');
      return;
    }

    // 选择支持该组合的性别之一
    const availableGenders = selectedCombination.支持性别;
    const selectedGender = availableGenders[0]; // 选择第一个可用的性别

    try {
      const response = await axios.post('/api/voice-seed', {
        gender: selectedGender,
        age: selectedCombination.年龄,
        style: selectedCombination.风格,
        character_name: '测试角色'
      });

      if (response.data.success) {
        alert(`成功选择种子: ${response.data.data.seed}`);
      }
    } catch (error) {
      console.error('Failed to generate voice:', error);
      alert('生成声音失败');
    }
  };

  if (loading) {
    return <div>加载中...</div>;
  }

  return (
    <div className="all-combinations-display">
      <h2>所有声音组合 (来自 JSON 种子)</h2>

      <div className="filter-section">
        <label>性别筛选:</label>
        <select value={selectedGender} onChange={(e) => setSelectedGender(e.target.value)}>
          <option value="all">全部</option>
          <option value="male">仅男性</option>
          <option value="female">仅女性</option>
        </select>
        <span>显示 {filteredCombinations.length} / {allCombinations.length} 个组合</span>
      </div>

      <div className="combinations-grid">
        {filteredCombinations.map((combo, index) => (
          <div
            key={index}
            className={`combination-card ${selectedCombination === combo ? 'selected' : ''}`}
            onClick={() => handleSelectCombination(combo)}
          >
            <h4>{combo.年龄} + {combo.风格}</h4>

            <div className="gender-info">
              <strong>支持性别:</strong> {combo.支持性别.join(', ')}
            </div>

            <div className="seeds-info">
              <strong>候选种子:</strong> {combo.候选种子.length}个
              <div className="seed-list">
                {combo.候选种子.map((seed, seedIndex) => (
                  <div key={seedIndex} className="seed-item">
                    <span className="seed-number">种子 {seed.种子}</span>
                    <span className="seed-gender">({seed.性别})</span>
                  </div>
                ))}
              </div>
            </div>

            {combo.候选种子[0] && (
              <div className="description">
                {combo.候选种子[0].描述}
              </div>
            )}
          </div>
        ))}
      </div>

      {selectedCombination && (
        <div className="action-section">
          <h3>已选择: {selectedCombination.年龄} + {selectedCombination.风格}</h3>
          <button onClick={handleGenerateVoice}>
            生成测试声音
          </button>
        </div>
      )}
    </div>
  );
}

export default AllVoiceCombinationsDisplay;
```

### 分性别显示组件

```jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

function GenderSpecificVoiceDisplay() {
  const [gender, setGender] = useState('male');
  const [combinations, setCombinations] = useState([]);
  const [statistics, setStatistics] = useState({});

  useEffect(() => {
    if (gender) {
      loadGenderCombinations();
    }
  }, [gender]);

  const loadGenderCombinations = async () => {
    try {
      const response = await axios.get(`/api/voice-combinations/${gender}`);
      if (response.data.success) {
        setCombinations(response.data.data.combinations);
      }

      // Also get statistics
      const allResponse = await axios.get('/api/all-voice-combinations');
      if (allResponse.data.success) {
        setStatistics(allResponse.data.data.统计信息);
      }
    } catch (error) {
      console.error('Failed to load combinations:', error);
    }
  };

  const getDisplayName = (gender) => {
    return gender === 'male' ? '男性' : '女性';
  };

  return (
    <div className="gender-specific-display">
      <h2>分性别声音组合</h2>

      <div className="gender-selector">
        <label>选择性别:</label>
        <select value={gender} onChange={(e) => setGender(e.target.value)}>
          <option value="male">男性</option>
          <option value="female">女性</option>
        </select>
      </div>

      <div className="statistics">
        <h3>统计信息</h3>
        <p>总组合数: {statistics.总组合数}</p>
        <p>总种子数: {statistics.总种子数}</p>
        <p>男性组合数: {statistics.男性组合数}</p>
        <p>女性组合数: {statistics.女性组合数}</p>
      </div>

      <div className="combinations-list">
        <h3>{getDisplayName(gender)}声音组合 ({combinations.length}个)</h3>
        {combinations.map((combo, index) => (
          <div key={index} className="combination-item">
            <h4>{combo.年龄} + {combo.风格}</h4>
            <p><strong>候选种子:</strong> {combo.候选种子.join(', ')}</p>
            {combo.描述 && combo.描述.length > 0 && (
              <p><strong>描述:</strong> {combo.描述[0]}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default GenderSpecificVoiceDisplay;
```

## 组合选择流程

### 1. 显示所有组合
```javascript
// 获取所有 age + style 组合
const response = await fetch('/api/all-voice-combinations');
const { 所有组合 } = response.data.data;

// 显示所有组合供用户选择
// 每个组合显示: 年龄 + 风格 + 支持性别 + 候选种子数
```

### 2. 用户选择组合
```javascript
// 用户选择了 "年轻 + 情感风格"
const selectedCombo = {
  "年龄": "年轻",
  "风格": "情感风格",
  "支持性别": ["female"],
  "候选种子": [{"种子": "2", "性别": "female"}]
};
```

### 3. 确定性别和生成种子
```javascript
// 从支持性别中选择一个 (或让用户选择)
const gender = selectedCombo.支持性别[0]; // "female"

// 生成种子
const seedResponse = await fetch('/api/voice-seed', {
  method: 'POST',
  body: JSON.stringify({
    gender: gender,
    age: selectedCombo.年龄,
    style: selectedCombo.风格,
    character_name: '角色名称'
  })
});
```

## 扩展 JSON 时的自动更新

当您在 `voice_preferences.json` 中添加新种子时，前端会自动显示新的组合：

### 添加新种子示例

```json
{
  "种子对照表": {
    "2001": {
      "gender": "male",
      "age": "年轻",
      "style": "幽默风格",
      "description": "年轻男性 - 幽默风趣"
    },
    "2002": {
      "gender": "female",
      "age": "年轻",
      "style": "幽默风格",
      "description": "年轻女性 - 幽默风趣"
    },
    "2003": {
      "gender": "male",
      "age": "年轻",
      "style": "幽默风格",
      "description": "年轻男性 - 幽默变体"
    }
  }
}
```

### 前端自动显示

添加上述种子后，前端会自动显示：
- **年轻 + 幽默风格** - 支持: [male, female] - 3个候选种子 (2001, 2002, 2003)

## 前端显示建议

### 1. 组合卡片设计
- 显示年龄 + 风格组合名称
- 显示支持的性别标签
- 显示候选种子数量
- 显示简要描述

### 2. 筛选和排序
- 按性别筛选
- 按年龄排序 (年轻 → 中年 → 其他)
- 按候选种子数量排序

### 3. 交互设计
- 点击组合查看详细信息
- 显示所有候选种子列表
- 支持快速预览和选择

### 4. 统计信息显示
- 总组合数
- 按性别分组的组合数
- 总种子数

## 优势

1. **完全覆盖**: 显示 JSON 中的所有种子组合
2. **自动更新**: 添加新种子后前端自动显示
3. **灵活筛选**: 支持按性别筛选组合
4. **详细统计**: 提供完整的统计信息
5. **随机选择**: 支持从多个候选中随机选择

现在前端可以完美显示 `voice_preferences.json` 中所有种子的不同 age + style 组合！🎯