# 命名规则服务开发计划 [下一步开发重点 🚀]

## 1. 背景与目标

为了支持音效文件的多样化命名需求，需要开发专门的命名规则服务。该服务将负责管理不同的命名规则、提供规则注册和选择机制，以及处理命名模板和字段格式化。

## 2. 核心需求

1. **多样化命名规则**：支持直接翻译、双语、UCS标准等多种命名规则
2. **自定义模板**：允许用户创建和配置自定义命名模板
3. **规则注册机制**：提供插件式架构，便于新规则的添加
4. **规则验证**：验证命名上下文是否符合规则要求
5. **与分类服务集成**：结合分类信息进行智能命名
6. **命名预览**：提供命名结果预览功能

## 3. 服务架构设计

### 3.1 INamingRule接口 [基础已完成 ✅]

所有命名规则必须实现的核心接口：

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

class INamingRule(ABC):
    """命名规则接口"""
    
    @abstractmethod
    def format(self, context: Dict[str, Any]) -> str:
        """格式化上下文为文件名"""
        pass
    
    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """获取规则所需的必填字段"""
        pass
    
    @abstractmethod
    def validate(self, context: Dict[str, Any]) -> bool:
        """验证上下文是否符合规则需求"""
        pass
```

### 3.2 NamingService类 [待实现 🔄]

命名服务核心类，负责管理命名规则：

```python
class NamingService(BaseService):
    """命名服务类，负责管理命名规则和模板"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化命名服务"""
        super().__init__('naming_service', config)
        self.rules: Dict[str, INamingRule] = {}
        self.default_rule = 'direct'
        self.category_service = None
    
    def initialize(self) -> bool:
        """初始化命名服务"""
        try:
            # 获取分类服务
            from ..core.service_factory import ServiceFactory
            factory = ServiceFactory.get_instance()
            self.category_service = factory.get_service('category_service')
            
            if not self.category_service or not self.category_service.is_available():
                logger.warning("分类服务不可用，部分命名规则可能无法正常工作")
            
            # 注册默认规则
            self._register_default_rules()
            
            # 加载自定义规则
            self._load_custom_rules()
            
            self.is_initialized = True
            return True
        except Exception as e:
            logger.error(f"初始化命名服务失败: {e}")
            return False
    
    def _register_default_rules(self):
        """注册默认命名规则"""
        # 直接翻译规则
        self.register_rule('direct', DirectNamingRule())
        
        # 双语规则
        self.register_rule('bilingual', BilingualNamingRule())
        
        # UCS标准规则
        ucs_rule = UCSNamingRule()
        if self.category_service:
            ucs_rule.set_category_service(self.category_service)
        self.register_rule('ucs_standard', ucs_rule)
        
        # 自定义规则
        self.register_rule('custom', CustomNamingRule())
    
    def _load_custom_rules(self):
        """加载自定义命名规则"""
        try:
            # 从配置加载自定义规则
            custom_rules = self.config.get('custom_rules', {})
            for rule_name, rule_config in custom_rules.items():
                rule_type = rule_config.get('type')
                
                if rule_type == 'template':
                    # 创建模板规则
                    template = rule_config.get('template', '{translated_name}')
                    rule = TemplateNamingRule(template)
                    self.register_rule(rule_name, rule)
                    
            logger.info(f"已加载 {len(custom_rules)} 个自定义命名规则")
                
        except Exception as e:
            logger.error(f"加载自定义命名规则失败: {e}")
    
    def register_rule(self, name: str, rule: INamingRule) -> bool:
        """注册命名规则"""
        try:
            self.rules[name] = rule
            return True
        except Exception as e:
            logger.error(f"注册命名规则失败: {name}, {e}")
            return False
    
    def get_rule(self, name: str = None) -> Optional[INamingRule]:
        """获取命名规则"""
        if name is None:
            name = self.default_rule
        return self.rules.get(name)
    
    def format_filename(self, rule_name: str, context: Dict[str, Any]) -> str:
        """使用指定规则格式化文件名"""
        rule = self.get_rule(rule_name)
        if rule is None:
            logger.warning(f"命名规则不存在: {rule_name}，使用默认规则")
            rule = self.get_rule()
        
        if not rule.validate(context):
            logger.warning(f"上下文验证失败，缺少必要字段")
            # 尝试填充缺失字段
            context = self._fill_missing_fields(rule, context)
        
        return rule.format(context)
    
    def _fill_missing_fields(self, rule: INamingRule, context: Dict[str, Any]) -> Dict[str, Any]:
        """尝试填充缺失字段"""
        required_fields = rule.get_required_fields()
        for field in required_fields:
            if field not in context:
                # 特殊字段处理
                if field.startswith('category') and self.category_service and 'original_name' in context:
                    # 尝试获取分类信息
                    cat_info = self.category_service.guess_category_with_fields(context['original_name'])
                    context.update(cat_info)
                else:
                    # 添加默认值
                    context[field] = f"未知{field}"
        return context
    
    def get_available_rules(self) -> List[str]:
        """获取所有可用的命名规则名称"""
        return list(self.rules.keys())
    
    def get_rule_description(self, rule_name: str) -> str:
        """获取命名规则描述"""
        rule = self.get_rule(rule_name)
        if hasattr(rule, 'get_description'):
            return rule.get_description()
        return f"命名规则: {rule_name}"
    
    def preview_filename(self, rule_name: str, context: Dict[str, Any]) -> str:
        """预览文件名格式化结果"""
        return self.format_filename(rule_name, context)
    
    def save_custom_rule(self, rule_name: str, rule_config: Dict[str, Any]) -> bool:
        """保存自定义命名规则"""
        try:
            # 更新配置
            if 'custom_rules' not in self.config:
                self.config['custom_rules'] = {}
            
            self.config['custom_rules'][rule_name] = rule_config
            
            # 创建并注册规则
            if rule_config.get('type') == 'template':
                template = rule_config.get('template', '{translated_name}')
                rule = TemplateNamingRule(template, rule_config.get('description', ''))
                self.register_rule(rule_name, rule)
            
            # 保存配置
            self._save_config()
            
            return True
        except Exception as e:
            logger.error(f"保存自定义命名规则失败: {rule_name}, {e}")
            return False
    
    def _save_config(self):
        """保存配置"""
        # 配置保存逻辑
        pass
```

## 4. 命名规则实现 [待实现 🔄]

### 4.1 DirectNamingRule（直接翻译规则）

```python
class DirectNamingRule(INamingRule):
    """直接翻译规则 - 使用翻译结果作为文件名"""
    
    def __init__(self, description: str = "直接翻译 - 使用翻译结果作为文件名"):
        self.description = description
    
    def format(self, context: Dict[str, Any]) -> str:
        """格式化翻译结果为文件名"""
        translated = context.get('translated_name', '')
        extension = context.get('extension', '')
        return f"{translated}{extension}"
    
    def get_required_fields(self) -> List[str]:
        """获取规则所需的必填字段"""
        return ['translated_name', 'extension']
    
    def validate(self, context: Dict[str, Any]) -> bool:
        """验证上下文是否符合规则需求"""
        return all(field in context for field in self.get_required_fields())
    
    def get_description(self) -> str:
        """获取规则描述"""
        return self.description
```

### 4.2 BilingualNamingRule（双语规则）

```python
class BilingualNamingRule(INamingRule):
    """双语规则 - 原文件名 + 分隔符 + 翻译名称"""
    
    def __init__(self, separator: str = " - ", 
                description: str = "双语模式 - 原文件名+分隔符+翻译结果"):
        self.separator = separator
        self.description = description
    
    def format(self, context: Dict[str, Any]) -> str:
        """格式化翻译结果为文件名"""
        original = context.get('original_name', '')
        translated = context.get('translated_name', '')
        extension = context.get('extension', '')
        
        return f"{original}{self.separator}{translated}{extension}"
    
    def get_required_fields(self) -> List[str]:
        """获取规则所需的必填字段"""
        return ['original_name', 'translated_name', 'extension']
    
    def validate(self, context: Dict[str, Any]) -> bool:
        """验证上下文是否符合规则需求"""
        return all(field in context for field in self.get_required_fields())
    
    def get_description(self) -> str:
        """获取规则描述"""
        return self.description
```

### 4.3 UCSNamingRule（UCS标准规则）

```python
class UCSNamingRule(INamingRule):
    """UCS标准命名规则 - 分类ID_分类名称_描述"""
    
    def __init__(self, description: str = "UCS标准 - 分类ID_分类名称_描述"):
        self.description = description
        self.category_service = None
    
    def set_category_service(self, category_service):
        """设置分类服务"""
        self.category_service = category_service
    
    def format(self, context: Dict[str, Any]) -> str:
        """格式化上下文为文件名"""
        category_id = context.get('category_id', 'OTHER')
        category_name = context.get('category', 'Other')
        translated = context.get('translated_name', '')
        extension = context.get('extension', '')
        
        # 格式化为UCS标准格式
        return f"{category_id}_{category_name}_{translated}{extension}"
    
    def get_required_fields(self) -> List[str]:
        """获取规则所需的必填字段"""
        return ['category_id', 'category', 'translated_name', 'extension']
    
    def validate(self, context: Dict[str, Any]) -> bool:
        """验证上下文是否符合规则需求"""
        return all(field in context for field in self.get_required_fields())
    
    def get_description(self) -> str:
        """获取规则描述"""
        return self.description
```

### 4.4 TemplateNamingRule（模板规则）

```python
class TemplateNamingRule(INamingRule):
    """模板命名规则 - 使用自定义模板格式化文件名"""
    
    def __init__(self, template: str, description: str = "自定义模板"):
        self.template = template
        self.description = description
        self._required_fields = self._extract_required_fields(template)
    
    def _extract_required_fields(self, template: str) -> List[str]:
        """从模板中提取必填字段"""
        import re
        # 匹配{field_name}格式的字段
        pattern = r'\{([a-zA-Z0-9_]+)\}'
        matches = re.findall(pattern, template)
        # 添加扩展名字段
        if 'extension' not in matches:
            matches.append('extension')
        return matches
    
    def format(self, context: Dict[str, Any]) -> str:
        """格式化上下文为文件名"""
        try:
            # 使用字符串格式化
            result = self.template.format(**context)
            # 添加扩展名（如果模板中没有包含）
            if '{extension}' not in self.template:
                result += context.get('extension', '')
            return result
        except KeyError as e:
            logger.error(f"模板格式化失败，缺少字段: {e}")
            return f"命名错误_{context.get('original_name', 'unknown')}"
    
    def get_required_fields(self) -> List[str]:
        """获取规则所需的必填字段"""
        return self._required_fields
    
    def validate(self, context: Dict[str, Any]) -> bool:
        """验证上下文是否符合规则需求"""
        return all(field in context for field in self.get_required_fields())
    
    def get_description(self) -> str:
        """获取规则描述"""
        return f"{self.description} ({self.template})"
```

## 5. 规则注册表 [待实现 🔄]

规则注册表负责管理命名规则的注册和获取：

```python
class RuleRegistry:
    """命名规则注册表"""
    
    def __init__(self):
        """初始化规则注册表"""
        self.rules: Dict[str, INamingRule] = {}
        self.default_rule = None
    
    def register_rule(self, name: str, rule: INamingRule) -> bool:
        """注册命名规则"""
        try:
            self.rules[name] = rule
            # 如果是第一个规则，设为默认
            if self.default_rule is None:
                self.default_rule = name
            return True
        except Exception as e:
            logger.error(f"注册命名规则失败: {name}, {e}")
            return False
    
    def get_rule(self, name: str = None) -> Optional[INamingRule]:
        """获取命名规则"""
        if name is None:
            name = self.default_rule
        return self.rules.get(name)
    
    def set_default_rule(self, name: str) -> bool:
        """设置默认命名规则"""
        if name in self.rules:
            self.default_rule = name
            return True
        return False
    
    def get_available_rules(self) -> List[str]:
        """获取所有可用的命名规则名称"""
        return list(self.rules.keys())
    
    def remove_rule(self, name: str) -> bool:
        """移除命名规则"""
        if name in self.rules:
            del self.rules[name]
            # 如果删除的是默认规则，重置默认规则
            if self.default_rule == name:
                self.default_rule = next(iter(self.rules)) if self.rules else None
            return True
        return False
```

## 6. 模板处理器 [待实现 🔄]

模板处理器负责解析和处理命名模板：

```python
class TemplateProcessor:
    """模板处理器，负责解析和处理命名模板"""
    
    def __init__(self):
        """初始化模板处理器"""
        self.template_cache = {}
    
    def process_template(self, template: str, context: Dict[str, Any]) -> str:
        """处理模板"""
        try:
            # 使用字符串格式化
            return template.format(**context)
        except KeyError as e:
            logger.error(f"模板处理失败，缺少字段: {e}")
            return f"模板错误_{e}"
    
    def extract_fields(self, template: str) -> List[str]:
        """从模板中提取字段"""
        import re
        # 匹配{field_name}格式的字段
        pattern = r'\{([a-zA-Z0-9_]+)\}'
        return re.findall(pattern, template)
    
    def validate_template(self, template: str) -> bool:
        """验证模板格式是否正确"""
        try:
            # 尝试使用空字典格式化，检查语法
            dummy_context = {}
            for field in self.extract_fields(template):
                dummy_context[field] = f"test_{field}"
            self.process_template(template, dummy_context)
            return True
        except Exception as e:
            logger.error(f"模板验证失败: {e}")
            return False
```

## 7. 规则验证器 [待实现 🔄]

规则验证器负责验证命名规则和上下文：

```python
class RuleValidator:
    """规则验证器，负责验证命名规则和上下文"""
    
    def validate_rule(self, rule: INamingRule) -> bool:
        """验证命名规则是否有效"""
        # 检查规则是否实现了所有必要的方法
        required_methods = ['format', 'get_required_fields', 'validate']
        for method in required_methods:
            if not hasattr(rule, method) or not callable(getattr(rule, method)):
                logger.error(f"规则验证失败，缺少方法: {method}")
                return False
        return True
    
    def validate_context(self, rule: INamingRule, context: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证上下文是否满足规则要求
        
        Returns:
            (是否有效, 缺失字段列表)
        """
        required_fields = rule.get_required_fields()
        missing_fields = [field for field in required_fields if field not in context]
        return len(missing_fields) == 0, missing_fields
```

## 8. 与分类服务集成 [待实现 🔄]

命名服务需要与分类服务集成，以获取分类信息：

```python
def integrate_with_category_service(self, category_service):
    """与分类服务集成"""
    self.category_service = category_service
    
    # 更新需要分类服务的规则
    for rule_name, rule in self.rules.items():
        if hasattr(rule, 'set_category_service'):
            rule.set_category_service(category_service)
```

## 9. UI组件 [待实现 🔄]

为命名服务提供UI组件，包括规则选择和预览：

```python
class NamingRuleDialog(tk.Toplevel):
    """命名规则选择对话框"""
    
    def __init__(self, parent, naming_service):
        super().__init__(parent)
        self.title("命名规则设置")
        self.naming_service = naming_service
        self.result = None
        
        # 创建UI组件
        self.create_widgets()
        
        # 居中显示
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # 设置模态
        self.transient(parent)
        self.grab_set()
    
    def create_widgets(self):
        """创建UI组件"""
        # 主框架
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 规则选择
        ttk.Label(main_frame, text="选择命名规则:").pack(anchor=tk.W, pady=(0, 5))
        
        # 规则列表
        self.rule_var = tk.StringVar()
        rules = self.naming_service.get_available_rules()
        rule_frame = ttk.Frame(main_frame)
        rule_frame.pack(fill=tk.X, pady=(0, 10))
        
        for rule_name in rules:
            description = self.naming_service.get_rule_description(rule_name)
            ttk.Radiobutton(
                rule_frame, 
                text=description,
                value=rule_name,
                variable=self.rule_var
            ).pack(anchor=tk.W, pady=2)
        
        # 设置默认值
        if rules:
            self.rule_var.set(rules[0])
        
        # 预览区域
        ttk.Label(main_frame, text="预览:").pack(anchor=tk.W, pady=(10, 5))
        
        self.preview_var = tk.StringVar(value="选择规则以预览结果")
        ttk.Label(main_frame, textvariable=self.preview_var).pack(anchor=tk.W, pady=(0, 10))
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="取消", command=self.cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="确定", command=self.confirm).pack(side=tk.RIGHT)
    
    def update_preview(self, context: Dict[str, Any]):
        """更新预览"""
        rule_name = self.rule_var.get()
        if rule_name:
            preview = self.naming_service.preview_filename(rule_name, context)
            self.preview_var.set(preview)
    
    def confirm(self):
        """确认选择"""
        self.result = self.rule_var.get()
        self.destroy()
    
    def cancel(self):
        """取消选择"""
        self.result = None
        self.destroy()
    
    def show(self) -> Optional[str]:
        """显示对话框并返回结果"""
        self.wait_window()
        return self.result
```

## 10. 实施计划

### 10.1 开发阶段 [待实施 🔄]

1. **阶段一**：核心接口和基础设施（2天）
   - 实现`INamingRule`接口
   - 创建`RuleRegistry`
   - 开发`TemplateProcessor`
   - 实现`RuleValidator`

2. **阶段二**：基础命名规则实现（2天）
   - 实现`DirectNamingRule`
   - 实现`BilingualNamingRule`
   - 实现`UCSNamingRule`
   - 实现`TemplateNamingRule`

3. **阶段三**：命名服务实现（2天）
   - 实现`NamingService`
   - 与分类服务集成
   - 添加配置管理

4. **阶段四**：UI组件开发（2天）
   - 实现命名规则选择对话框
   - 添加预览功能
   - 集成到主界面

5. **阶段五**：测试与优化（2天）
   - 单元测试
   - 集成测试
   - 性能优化

### 10.2 测试计划 [待实施 🔄]

1. **单元测试**：
   - 测试各个命名规则
   - 测试模板处理器
   - 测试规则验证器

2. **集成测试**：
   - 测试与分类服务的集成
   - 测试配置加载和保存
   - 测试UI组件

3. **用户测试**：
   - 测试不同命名场景
   - 验证命名结果
   - 收集用户反馈

## 11. 风险与缓解 [待评估 🔄]

1. **风险**：命名规则可能与现有文件命名冲突
   - **缓解**：添加命名冲突检测和处理

2. **风险**：用户可能创建无效的模板
   - **缓解**：添加模板验证和错误提示

3. **风险**：分类服务可能不可用
   - **缓解**：添加降级处理，使用默认分类

4. **风险**：性能问题
   - **缓解**：添加缓存机制，优化模板处理

## 12. 总结

命名规则服务将为音效文件命名提供灵活、可扩展的解决方案。通过与分类服务的集成，可以实现智能命名，提高工作效率。该服务的插件式架构也为未来添加新的命名规则提供了便利。