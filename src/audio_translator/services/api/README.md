# API服务 (API Services)

此目录包含与外部API集成的服务组件，负责与各种AI模型服务提供商进行通信。

## 包含的服务

- **ModelService**: 模型服务基类，定义了与AI模型交互的通用接口
- **providers/**: 各种AI服务提供商的具体实现
  - **openai/**: OpenAI服务实现
  - **anthropic/**: Anthropic (Claude) 服务实现
  - **gemini/**: Google Gemini服务实现
  - **volc/**: 火山引擎服务实现
  - **zhipu/**: 智谱AI服务实现
  - **alibaba/**: 阿里云百炼服务实现
  - **deepseek/**: DeepSeek服务实现

## 职责

- 提供与各种AI模型服务的统一接口
- 处理API认证和请求
- 管理API响应和错误处理
- 提供模型功能的抽象层 