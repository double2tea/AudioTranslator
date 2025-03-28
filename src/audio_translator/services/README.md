# 服务层 (Services Layer)

此目录包含应用程序的所有服务组件，按照职责和功能进行分层组织。

## 目录结构

- **core/**: 核心服务，包含服务基础架构和管理组件
- **api/**: API服务，包含与外部AI模型服务提供商的集成
- **infrastructure/**: 基础设施服务，包含底层功能支持
- **business/**: 业务服务，包含核心业务逻辑实现

## 设计原则

服务层采用分层架构设计，遵循以下原则：

1. **关注点分离**: 每个服务目录专注于特定类型的功能
2. **依赖方向**: 依赖关系从上到下，业务层依赖基础设施层和API层，而不是反向
3. **接口一致性**: 所有服务继承自BaseService，提供一致的接口
4. **可扩展性**: 服务工厂模式使得添加新服务变得简单
5. **可测试性**: 服务之间的清晰边界使得单元测试更加容易

## 服务注册和使用

所有服务通过ServiceFactory进行注册和获取，确保单例模式和依赖注入的正确实现。 