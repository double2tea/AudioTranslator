# Audio Translator 配置目录

此目录包含 Audio Translator 应用程序的所有配置文件。

## 配置文件说明

- **app_config.json**: 应用程序主配置文件，包含基本设置、界面配置和翻译服务设置
- **services.json**: AI 服务配置文件，包含各种 AI 服务的连接信息和模型配置
- **strategies.json**: 翻译策略配置文件，定义各种翻译策略的参数和提示词模板

## 配置修改指南

1. **修改配置文件**:
   - 直接编辑 JSON 文件，或通过应用程序界面修改配置
   - 保持 JSON 格式有效，确保键名正确

2. **添加新配置**:
   - 需要添加新配置项时，确保遵循现有格式
   - 避免删除核心配置项

3. **备份机制**:
   - 系统会自动创建 `*_backup.json` 备份文件
   - 如果配置损坏，系统会自动尝试恢复备份

## 开发者须知

此目录是应用程序的主要配置存储位置。在代码中，请使用 `ConfigService` 访问这些配置，而不是直接读取文件。

```python
# 推荐的配置访问方式
from src.audio_translator.services.infrastructure.config_service import ConfigService

config_service = ConfigService()
config_service.initialize()

# 获取配置
value = config_service.get("SOME_KEY")

# 设置配置
config_service.set("SOME_KEY", "new_value")
``` 