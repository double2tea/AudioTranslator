# 音频翻译器面板架构

本文档说明了音频翻译器应用程序中的面板架构设计。

## 面板基类

应用程序提供了两种类型的面板基类，根据不同需求选择合适的基类：

### SimplePanel

`SimplePanel` 是一个轻量级的面板基类，不依赖服务工厂，适用于简单UI组件：

```python
from ..base import SimplePanel

class MySimplePanel(SimplePanel):
    def __init__(self, parent):
        super().__init__(parent)
        # 初始化组件
        
    def _init_ui(self):
        # 创建UI组件
        pass
```

**适用场景**：
- 仅需要基本UI功能的面板
- 不需要访问应用服务的面板
- 轻量级、独立的功能模块

### ServicePanel

`ServicePanel` 是一个高级面板基类，支持服务工厂和事件回调，适用于需要访问应用服务的面板：

```python
from ..base import ServicePanel

class MyServicePanel(ServicePanel):
    def __init__(self, parent, service_factory):
        super().__init__(parent, service_factory, "my_panel_name")
        # 初始化组件
        
    def _create_ui(self):
        # 创建UI组件
        pass
        
    def _bind_events(self):
        # 绑定事件
        pass
```

**适用场景**：
- 需要访问应用服务的面板
- 需要配置管理的面板
- 需要事件回调机制的面板
- 复杂的功能模块

## 面板生命周期

### SimplePanel 生命周期
1. 初始化 (`__init__`)
2. 创建UI (`_init_ui`)
3. 显示 (`show`)
4. 隐藏 (`hide`)

### ServicePanel 生命周期
1. 初始化 (`__init__`)
2. 初始化 (`initialize`)：创建UI、绑定事件、加载配置
3. 激活 (`activate`)：准备面板的可见状态
4. 挂起 (`deactivate`)：暂停面板的活动状态
5. 销毁 (`destroy`)：清理资源

## 最佳实践

1. **选择合适的基类**
   - 如果面板不需要服务访问，使用 `SimplePanel`
   - 如果面板需要服务访问，使用 `ServicePanel`

2. **命名规范**
   - 面板类名应以 `Panel` 结尾
   - 面板配置键应使用面板名称作为前缀

3. **设计原则**
   - 每个面板应该只关注一个功能领域
   - 使用组合而不是继承来扩展面板功能
   - 使用事件机制进行面板间通信

4. **避免循环依赖**
   - 面板不应直接引用其他面板
   - 使用事件机制或服务进行交互 