# 音效文件命名功能核心服务重构计划 [已完成 ✅]

## 1. 背景与目标

当前的音效文件命名相关功能分散在多个服务中，存在高耦合、难扩展的问题。本重构计划旨在提供清晰的接口定义和服务分层，为后续的命名规则增强功能奠定基础。

## 2. 现有问题分析

1. **功能耦合**：
   - `TranslatorService`同时负责翻译和命名逻辑
   - `UCSService`和`CategoryService`存在重叠功能
   - 缺乏明确的接口定义和责任边界

2. **扩展困难**：
   - 添加新的命名规则或翻译策略需要修改现有服务
   - 缺乏插件化机制
   - 测试难度大

3. **代码重复**：
   - `CategoryManager`和`CategoryService`中存在相似代码
   - 分类猜测逻辑在多处实现

## 3. 重构目标

1. 定义清晰的接口和抽象基类 [已完成 ✅]
2. 分离翻译策略和命名规则逻辑 [已完成 ✅]
3. 统一分类服务功能 [已完成 ✅]
4. 提供服务注册和发现机制 [已完成 ✅]
5. 确保向后兼容性 [已完成 ✅]

## 4. 核心接口设计 [已完成 ✅]

### 4.1 基础服务接口 [已完成 ✅]

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

class ITranslationStrategy(ABC):
    """翻译策略接口"""
    
    @abstractmethod
    def translate(self, text: str, context: Dict[str, Any] = None) -> str:
        """翻译文本内容"""
        pass
```

### 4.2 服务管理接口 [已完成 ✅]

```python
class IServiceRegistry(ABC):
    """服务注册接口"""
    
    @abstractmethod
    def register_service(self, service_name: str, service_instance: Any) -> bool:
        """注册服务"""
        pass
    
    @abstractmethod
    def get_service(self, service_name: str) -> Optional[Any]:
        """获取服务实例"""
        pass
    
    @abstractmethod
    def has_service(self, service_name: str) -> bool:
        """检查服务是否存在"""
        pass
```

## 5. 核心服务设计

### 5.1 服务注册中心 [已完成 ✅]

增强现有的`ServiceFactory`，支持更灵活的服务注册和发现：

```python
class ServiceFactory:
    """服务工厂类，负责服务的创建和管理"""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """初始化服务工厂"""
        self._services = {}
        self._services_config = {}
        
    def register_service(self, service_name: str, service_instance: Any) -> bool:
        """注册服务实例"""
        self._services[service_name] = service_instance
        return True
    
    def register_service_config(self, service_name: str, service_config: Dict[str, Any]) -> bool:
        """注册服务配置"""
        self._services_config[service_name] = service_config
        return True
    
    def get_service(self, service_name: str) -> Optional[Any]:
        """获取服务实例，如果不存在则尝试创建"""
        if service_name in self._services:
            return self._services[service_name]
            
        # 尝试创建服务
        if self._create_service(service_name):
            return self._services[service_name]
            
        return None
    
    def _create_service(self, service_name: str) -> bool:
        """创建服务实例"""
        # 实现服务创建逻辑
        pass
```

### 5.2 翻译管理器 [已完成 ✅]

创建中央翻译管理服务，协调翻译和命名规则：

```python
class TranslationManager:
    """翻译管理器，协调翻译策略和命名规则"""
    
    def __init__(self):
        """初始化翻译管理器"""
        self._translation_strategies = {}
        self._naming_rules = {}
        self._default_strategy = None
        self._default_rule = None
    
    def register_translation_strategy(self, name: str, strategy: ITranslationStrategy) -> bool:
        """注册翻译策略"""
        self._translation_strategies[name] = strategy
        return True
    
    def register_naming_rule(self, name: str, rule: INamingRule) -> bool:
        """注册命名规则"""
        self._naming_rules[name] = rule
        return True
    
    def set_default_strategy(self, name: str) -> bool:
        """设置默认翻译策略"""
        if name in self._translation_strategies:
            self._default_strategy = name
            return True
        return False
    
    def set_default_rule(self, name: str) -> bool:
        """设置默认命名规则"""
        if name in self._naming_rules:
            self._default_rule = name
            return True
        return False
    
    def translate_file(self, file_path: str, strategy_name: str = None, rule_name: str = None) -> Dict[str, Any]:
        """翻译文件名并应用命名规则"""
        # 实现文件翻译和命名逻辑
        pass
```

## 6. 服务迁移计划

### 6.1 分阶段迁移

为确保系统稳定性，建议按以下步骤进行迁移：

1. **创建新接口和基类** [已完成 ✅]
   - 实现`INamingRule`接口
   - 实现`ITranslationStrategy`接口
   - 增强`ServiceFactory`

2. **增强服务注册机制** [已完成 ✅]
   - 修改`service_factory.py`
   - 更新服务注册和发现逻辑
   - 添加配置管理支持

3. **创建中央管理器** [已完成 ✅]
   - 实现`TranslationManager`
   - 提供向后兼容接口
   - 确保适当的依赖注入

4. **重构现有服务** [已完成 ✅]
   - 将`TranslatorService`功能拆分到新接口
   - 保留原接口作为适配器
   - 添加日志和异常处理

### 6.2 向后兼容性 [已完成 ✅]

为确保现有代码继续工作，需要：

1. 保留所有公共方法签名不变
2. 在内部实现中使用新接口
3. 添加兼容层将新数据结构映射到旧格式
4. 添加详细日志以便调试

## 7. 文件结构变更 [已完成 ✅]

```
src/audio_translator/
├── services/
│   ├── core/
│   │   ├── interfaces.py             # 已完成：核心接口定义
│   │   ├── base_service.py           # 已完成：基础服务类
│   │   ├── service_factory.py        # 已完成：增强的服务工厂
│   │   └── service_registry.py       # 已完成：服务注册
│   ├── business/
│   │   ├── translation/              # 已完成：翻译相关服务
│   │   │   ├── __init__.py
│   │   │   ├── translation_manager.py   # 已完成：翻译管理器
│   │   │   ├── strategies/              # 已完成：策略相关
│   │   │   │   ├── __init__.py
│   │   │   │   ├── strategy_registry.py # 已完成：策略注册表
│   │   │   │   ├── model_service_adapter.py # 已完成：模型服务适配器
│   │   │   │   └── adapters/           # 已完成：适配器实现
│   │   │   ├── cache/                  # 已完成：缓存管理
│   │   │   │   ├── __init__.py
│   │   │   │   └── cache_manager.py    # 已完成：缓存管理器
│   │   │   └── context/                # 已完成：上下文处理
│   │   │       ├── __init__.py
│   │   │       └── context_processor.py # 已完成：上下文处理器
```

## 8. 测试策略 [已完成 ✅]

1. **单元测试**：
   - 为每个接口创建测试
   - 使用模拟对象隔离依赖
   - 测试边界条件和异常情况

2. **集成测试**：
   - 测试服务间交互
   - 验证配置加载
   - 检查资源管理

3. **向后兼容测试**：
   - 确保旧API仍然可用
   - 验证结果一致性
   - 测试错误处理

## 9. 风险与缓解 [已解决 ✅]

1. **风险**：服务依赖关系复杂，可能导致循环依赖
   - **缓解**：使用依赖注入和延迟加载

2. **风险**：重构可能引入新错误
   - **缓解**：全面的单元测试和集成测试

3. **风险**：性能可能受到影响
   - **缓解**：添加性能监控和缓存机制

4. **风险**：现有功能可能受到影响
   - **缓解**：保持API兼容性并添加回归测试

## 10. 实施时间线

1. **阶段一**：核心接口设计与实现（2天）[已完成 ✅]
2. **阶段二**：服务注册机制增强（1天）[已完成 ✅]
3. **阶段三**：翻译管理器实现（2天）[已完成 ✅]
4. **阶段四**：服务迁移与集成（2天）[已完成 ✅]
5. **阶段五**：测试与调优（1天）[已完成 ✅]

总计约需8个工作日完成，已于计划时间内全部完成。 