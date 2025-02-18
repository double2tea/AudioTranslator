# 音效文件名翻译工具

## 项目概述
这是一个基于 Python 的音效文件名翻译工具，用于将英文音效文件名按照 UCS 规范翻译为中文。

## 核心功能
- 文件名翻译
- 多种翻译服务支持
- 词库管理
- 配置管理
- UCS规范解析

## 代码规范

### 文件组织
- GUI 相关代码放在根目录
- 核心功能代码放在 core 目录
- 配置文件和数据文件放在 data 目录

### 命名规范
- 类名使用 PascalCase
- 函数和变量使用 snake_case
- 常量使用 UPPER_CASE
- 私有成员以单下划线开头

### 注释规范
- 类和公共方法必须有文档字符串
- 复杂逻辑需要添加注释
- 使用 Google 风格的文档字符串

### 错误处理
- 使用具体的异常类型
- 记录错误日志
- 向用户提供友好的错误提示

### 界面设计
- 使用深色主题
- 保持界面简洁
- 提供清晰的用户反馈

### 配置管理
- 使用 JSON 格式存储配置
- 支持配置版本管理
- 提供默认配置

### 数据管理
- 使用 CSV 格式存储翻译数据
- 支持数据导入导出
- 实现数据缓存机制

## 开发注意事项
1. 保持代码模块化和可维护性
2. 确保异常处理完善
3. 注重用户体验
4. 保持配置灵活性
5. 确保数据安全性

# 配置管理规范

## 核心原则

1. 统一管理
   - 所有配置在 config.py 中定义
   - 通过 Config 类访问配置

2. 标准访问
   ```python
   from config import Config
   config = Config()
   
   # 获取/设置配置
   theme = config.get("UI_THEME")
   config.set("UI_THEME", "dark")
   ```

3. 错误处理
   ```python
   try:
       config.set("UI_THEME", theme)
   except Exception as e:
       logging.error(f"设置主题失败: {e}")
   ```

## 配置分类

1. UI配置
   - 主题
   - 颜色

2. 翻译配置
   - 服务设置
   - API密钥

3. 文件配置
   - 支持格式
   - 命名规则

## 最佳实践

1. 初始化配置
   ```python
   def __init__(self):
       self.config = Config()
       self.setup_config_listener()
       self.load_initial_config()
   ```

2. 配置变更处理
   ```python
   def on_config_change(self, event):
       try:
           if event.key == "UI_THEME":
               ThemeManager.change_theme(self.window, event.new_value)
           elif event.key == "TRANSLATION_SERVICE":
               self.load_services()
       except Exception as e:
           logging.error(f"配置处理失败: {e}")
   ```

3. 配置保存
   ```python
   def save_settings(self):
       try:
           self.config.save()
           logging.info("配置已保存")
       except Exception as e:
           logging.error(f"保存配置失败: {e}")
   ```

## 注意事项

1. 配置访问
   - 使用标准方法访问配置
   - 避免直接修改配置字典
   - 保持配置结构一致

2. 错误处理
   - 捕获所有配置相关异常
   - 记录详细错误日志
   - 提供用户友好提示

3. 配置监听
   - 及时响应配置变更
   - 保持界面状态同步
   - 避免循环更新

4. 性能考虑
   - 合理使用配置缓存
   - 避免频繁保存
   - 优化配置加载 