# 分类服务优化与整合计划 [已完成 ✅]

## 1. 背景与目标

当前项目中存在两个分类相关的组件：`CategoryService`和`CategoryManager`，它们之间存在功能重叠和职责不清的问题。本计划旨在整合和优化这两个组件，构建统一的分类服务体系，为命名规则增强功能提供基础。

## 2. 现状分析

### 2.1 现有组件对比

| 功能/特性 | CategoryService | CategoryManager |
|---------|----------------|----------------|
| 位置 | services/business/category_service.py | managers/category_manager.py |
| 职责 | 服务层分类管理 | UI层分类管理 |
| 分类数据加载 | ✓ | ✓ |
| 分类猜测算法 | ✓ | ✓ |
| 分类CRUD操作 | ✓ | 部分 |
| 文件夹创建 | ✓ | ✓ |
| UI交互 | ✗ | ✓ |
| 依赖BaseService | ✓ | ✗ |

### 2.2 主要问题

1. **代码重复**：
   - 分类数据结构在两个组件中重复定义
   - 分类加载逻辑重复实现
   - 分类猜测算法分别维护

2. **职责不清**：
   - `CategoryManager`混合了UI和业务逻辑
   - `CategoryService`未被充分利用
   - 数据流向不明确

3. **同步问题**：
   - 两个组件中的分类数据可能不同步
   - 缓存机制不统一
   - 更新逻辑分散

## 3. 优化目标 [已完成 ✅]

1. 明确职责分离，`CategoryService`专注业务逻辑，`CategoryManager`专注UI交互 [已完成 ✅]
2. 统一分类数据结构和存储 [已完成 ✅]
3. 改进分类猜测算法，提高准确性 [已完成 ✅]
4. 优化缓存机制，提升性能 [已完成 ✅]
5. 为命名规则增强功能提供必要的接口 [已完成 ✅]

## 4. 优化方案

### 4.1 分类数据结构统一 [已完成 ✅]

统一使用`Category`数据类：

```python
@dataclass
class Category:
    """分类数据结构"""
    cat_id: str
    name_en: str
    name_zh: str
    subcategory: str = ""
    subcategory_zh: str = ""
    synonyms_en: List[str] = None
    synonyms_zh: List[str] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.synonyms_en is None:
            self.synonyms_en = []
        if self.synonyms_zh is None:
            self.synonyms_zh = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'CatID': self.cat_id,
            'Category': self.name_en,
            'Category_zh': self.name_zh,
            'subcategory': self.subcategory,
            'subcategory_zh': self.subcategory_zh,
            'synonyms_en': self.synonyms_en,
            'synonyms_zh': self.synonyms_zh
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Category':
        """从字典创建分类对象"""
        return cls(
            cat_id=data.get('CatID', ''),
            name_en=data.get('Category', ''),
            name_zh=data.get('Category_zh', ''),
            subcategory=data.get('subcategory', ''),
            subcategory_zh=data.get('subcategory_zh', ''),
            synonyms_en=data.get('synonyms_en', []),
            synonyms_zh=data.get('synonyms_zh', [])
        )
    
    def get_full_name_en(self) -> str:
        """获取完整英文名称"""
        if self.subcategory:
            return f"{self.name_en} - {self.subcategory}"
        return self.name_en
    
    def get_full_name_zh(self) -> str:
        """获取完整中文名称"""
        if self.subcategory_zh:
            return f"{self.name_zh} - {self.subcategory_zh}"
        return self.name_zh
```

### 4.2 增强CategoryService [已完成 ✅]

重构`CategoryService`以提供更完整的功能：

```python
class CategoryService(BaseService):
    """分类服务类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化分类服务"""
        super().__init__('category_service', config)
        self.categories: Dict[str, Category] = {}
        self.data_dir = None
        self.categories_file = None
        self._match_cache: Dict[str, str] = {}
        self._initialize_paths()
        
        # 评分规则常量
        self.SCORE_RULES = {
            'EXACT_CATEGORY_SUBCATEGORY': 110,
            'EXACT_CATEGORY_SUBCATEGORY_REVERSE': 100,
            'EXACT_SUBCATEGORY_SYNONYM': 90,
            'EXACT_CATEGORY_SYNONYM': 60,
            'PARTIAL_SUBCATEGORY': 40,
            'PARTIAL_CATEGORY': 25,
            'PARTIAL_SYNONYM': 30,
            'CHINESE_MATCH': 15,
            'POSITION_FIRST_WORD': 20,
            'POSITION_EXACT_ORDER': 10,
        }
    
    def _initialize_paths(self):
        """初始化路径配置"""
        config_service = ServiceFactory.get_instance().get_service('config_service')
        if config_service:
            self.data_dir = Path(config_service.get_data_dir())
            self.categories_file = self.data_dir / "categories" / "_categorylist.csv"
        else:
            self.data_dir = Path('data')
            self.categories_file = self.data_dir / "_categorylist.csv"
    
    # ... 其他方法 ...
    
    def get_categories_for_naming(self) -> Dict[str, Dict[str, Any]]:
        """
        获取用于命名规则的分类数据
        
        Returns:
            用于命名规则的分类数据字典
        """
        naming_categories = {}
        for cat_id, category in self.categories.items():
            naming_categories[cat_id] = {
                'id': cat_id,
                'name_en': category.name_en,
                'name_zh': category.name_zh,
                'full_name_en': category.get_full_name_en(),
                'full_name_zh': category.get_full_name_zh()
            }
        return naming_categories
```

### 4.3 优化CategoryManager [已完成 ✅]

重构`CategoryManager`专注于UI交互：

```python
class CategoryManager:
    """分类管理器，负责分类的UI交互"""
    
    def __init__(self, parent: tk.Tk):
        """初始化分类管理器"""
        self.parent = parent
        self.category_service = None
        
        # UI相关变量
        self.auto_categorize_var = tk.BooleanVar(value=False)
        self.use_subcategory_var = tk.BooleanVar(value=True)
    
    def set_category_service(self, category_service: 'CategoryService'):
        """设置分类服务实例"""
        self.category_service = category_service
    
    def show_category_dialog(self, files: List[str]) -> Optional[Dict[str, Any]]:
        """显示分类选择对话框"""
        if not self.category_service:
            logger.error("分类服务未设置")
            return None
            
        dialog = CategorySelectionDialog(
            self.parent, 
            self.category_service.get_all_categories(),
            files=files
        )
        
        return dialog.show()
    
    def start_auto_categorize(self, files: List[str], base_path: Union[str, Path]) -> List[str]:
        """开始自动分类处理"""
        if not self.category_service:
            logger.error("分类服务未设置")
            return []
            
        dialog = AutoCategorizeDialog(
            self.parent,
            files=files,
            category_service=self.category_service,
            base_path=base_path
        )
        
        result = dialog.show()
        return result or []
    
    # ... 其他UI相关方法 ...
```

### 4.4 分类猜测算法优化 [已完成 ✅]

增强分类猜测算法：

```python
@lru_cache(maxsize=1000)
def guess_category(self, filename: str) -> str:
    """
    根据文件名智能猜测分类ID
    
    Args:
        filename: 文件名
        
    Returns:
        最匹配的分类ID
    """
    # 检查缓存
    if filename in self._match_cache:
        return self._match_cache[filename]
    
    # 预处理文件名
    filename_lower = filename.lower().replace('_', ' ')
    
    best_match = None
    max_score = 0
    
    # 词频分析
    words = filename_lower.split()
    word_scores = defaultdict(int)
    
    # 记录每个词的位置
    word_positions = {}
    for i, word in enumerate(words):
        word_positions[word] = i
    
    # 遍历所有分类
    for cat_id, category in self.categories.items():
        score = 0
        
        # 检查英文同义词
        for synonym in category.synonyms_en:
            synonym_lower = synonym.lower()
            if synonym_lower in filename_lower:
                score += self.SCORE_RULES['PARTIAL_SYNONYM']
                
                # 检查是否为首词
                if any(word.startswith(synonym_lower) for word in words[:2]):
                    score += self.SCORE_RULES['POSITION_FIRST_WORD']
        
        # 检查中文同义词
        for synonym in category.synonyms_zh:
            if synonym in filename:
                score += self.SCORE_RULES['CHINESE_MATCH']
        
        # 检查分类名称
        if category.name_en.lower() in filename_lower:
            score += self.SCORE_RULES['PARTIAL_CATEGORY']
            
            # 检查是否为首词
            cat_words = category.name_en.lower().split()
            if len(cat_words) > 0 and any(word.startswith(cat_words[0]) for word in words[:2]):
                score += self.SCORE_RULES['POSITION_FIRST_WORD']
            
        if category.name_zh in filename:
            score += self.SCORE_RULES['CHINESE_MATCH']
        
        # 检查子分类名称
        if category.subcategory and category.subcategory.lower() in filename_lower:
            score += self.SCORE_RULES['PARTIAL_SUBCATEGORY']
            
        if category.subcategory_zh and category.subcategory_zh in filename:
            score += self.SCORE_RULES['CHINESE_MATCH']
        
        # 检查分类ID
        if cat_id.lower() in filename_lower:
            score += self.SCORE_RULES['EXACT_CATEGORY_SUBCATEGORY']
        
        # 更新最佳匹配
        if score > max_score:
            max_score = score
            best_match = cat_id
    
    # 如果找到匹配
    if best_match:
        # 缓存结果
        self._match_cache[filename] = best_match
        return best_match
    
    # 如果没有匹配，返回默认分类
    return 'OTHER'
```

## 5. 命名规则接口扩展 [已完成 ✅]

为支持命名规则，添加以下接口：

```python
def get_naming_fields(self, cat_id: str) -> Dict[str, Any]:
    """
    获取用于命名的分类字段
    
    Args:
        cat_id: 分类ID
        
    Returns:
        包含命名所需字段的字典
    """
    if cat_id not in self.categories:
        return {
            'category_id': 'OTHER',
            'category': 'Other',
            'category_zh': '其他',
            'full_category': 'Other',
            'full_category_zh': '其他'
        }
    
    category = self.categories[cat_id]
    return {
        'category_id': cat_id,
        'category': category.name_en,
        'category_zh': category.name_zh,
        'subcategory': category.subcategory,
        'subcategory_zh': category.subcategory_zh,
        'full_category': category.get_full_name_en(),
        'full_category_zh': category.get_full_name_zh()
    }

def guess_category_with_fields(self, filename: str) -> Dict[str, Any]:
    """
    猜测分类并返回命名所需字段
    
    Args:
        filename: 文件名
        
    Returns:
        包含命名所需字段的字典
    """
    cat_id = self.guess_category(filename)
    return self.get_naming_fields(cat_id)
```

## 6. 迁移计划

### 6.1 分阶段迁移 [已完成 ✅]

1. **统一数据结构** [已完成 ✅]
   - 提取共同的`Category`数据类到单独的模块
   - 更新两个组件以使用统一的数据结构

2. **增强CategoryService** [已完成 ✅]
   - 实现增强的分类服务功能
   - 添加命名规则支持接口
   - 优化猜测算法

3. **优化CategoryManager** [已完成 ✅]
   - 移除重复的业务逻辑
   - 专注于UI交互
   - 使用`CategoryService`作为数据源

4. **更新依赖组件** [已完成 ✅]
   - 修改使用`CategoryManager`的UI组件
   - 确保`UCSService`与新的分类服务兼容
   - 调整其他依赖组件

### 6.2 测试重点 [已完成 ✅]

1. 分类数据加载和解析
2. 分类猜测算法准确性
3. UI交互功能
4. 命名规则支持接口
5. 性能和内存使用

## 7. 新文件结构 [已完成 ✅]

```
src/audio_translator/
├── services/
│   ├── business/
│   │   ├── category/
│   │   │   ├── __init__.py
│   │   │   ├── category.py               # 已完成：统一的Category数据类
│   │   │   ├── category_service.py       # 已完成：增强的分类服务
│   │   │   └── category_utils.py         # 已完成：通用工具函数
└── managers/
    └── category_manager.py               # 已完成：专注UI交互的管理器
```

## 8. 影响范围

### 8.1 直接影响 [已处理 ✅]

1. `CategoryService`和`CategoryManager`的调用者
2. 使用分类功能的UI组件
3. 依赖分类数据的服务（如`UCSService`）

### 8.2 间接影响 [已处理 ✅]

1. 文件管理功能
2. 翻译结果展示
3. 分类选择对话框

## 9. 实施时间线

1. **阶段一**：统一数据结构（1天）[已完成 ✅]
2. **阶段二**：增强CategoryService（2天）[已完成 ✅]
3. **阶段三**：优化CategoryManager（1天）[已完成 ✅]
4. **阶段四**：更新依赖组件（1天）[已完成 ✅]
5. **阶段五**：测试与调优（1天）[已完成 ✅]

总计约需6个工作日完成，已于计划时间内全部完成。

## 10. 风险与缓解 [已解决 ✅]

1. **风险**：重构可能影响现有功能
   - **缓解**：完善的单元测试和集成测试

2. **风险**：UI组件依赖旧实现
   - **缓解**：保持接口兼容性，必要时提供适配层

3. **风险**：分类猜测算法准确性降低
   - **缓解**：在测试中比较新旧算法，确保准确性不降低

4. **风险**：性能影响
   - **缓解**：优化缓存机制，监控性能指标 