"""
核心接口定义模块

此模块定义了应用程序中核心服务组件的接口，提供了服务间交互的标准契约。
这些接口确保了系统组件之间的低耦合和可扩展性。
"""

import abc
from typing import Dict, List, Any, Optional

class INamingRule(abc.ABC):
    """
    命名规则接口
    
    定义命名规则的标准接口，所有具体的命名规则实现必须遵循此接口。
    命名规则负责将翻译和分类信息转换为文件名。
    """
    
    @abc.abstractmethod
    def format(self, context: Dict[str, Any]) -> str:
        """
        格式化上下文为文件名
        
        Args:
            context: 包含翻译信息、分类信息等的上下文数据
            
        Returns:
            格式化后的文件名
        """
        pass
    
    @abc.abstractmethod
    def get_required_fields(self) -> List[str]:
        """
        获取规则所需的必填字段
        
        Returns:
            字段名称列表
        """
        pass
    
    @abc.abstractmethod
    def validate(self, context: Dict[str, Any]) -> bool:
        """
        验证上下文是否符合规则需求
        
        Args:
            context: 上下文数据
            
        Returns:
            验证是否通过
        """
        pass

class ITranslationStrategy(abc.ABC):
    """
    翻译策略接口
    
    定义翻译策略的标准接口，所有具体的翻译策略实现必须遵循此接口。
    翻译策略负责将文本从一种语言翻译为另一种语言。
    """
    
    @abc.abstractmethod
    def get_name(self) -> str:
        """
        获取策略名称
        
        Returns:
            策略名称
        """
        pass
    
    @abc.abstractmethod
    def get_description(self) -> str:
        """
        获取策略描述
        
        Returns:
            策略描述
        """
        pass
    
    @abc.abstractmethod
    def get_provider_type(self) -> str:
        """
        获取提供商类型
        
        Returns:
            提供商类型标识符
        """
        pass
    
    @abc.abstractmethod
    def translate(self, text: str, context: Dict[str, Any] = None) -> str:
        """
        翻译文本
        
        Args:
            text: 要翻译的文本
            context: 翻译上下文信息
            
        Returns:
            翻译后的文本
        """
        pass
    
    @abc.abstractmethod
    def batch_translate(self, texts: List[str], context: Dict[str, Any] = None) -> List[str]:
        """
        批量翻译文本
        
        Args:
            texts: 要翻译的文本列表
            context: 翻译上下文信息
            
        Returns:
            翻译后的文本列表
        """
        pass
    
    @abc.abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """
        测试连接状态
        
        Returns:
            连接状态信息
        """
        pass
    
    @abc.abstractmethod
    def get_config_schema(self) -> Dict[str, Any]:
        """
        获取配置模式描述
        
        Returns:
            描述配置项的结构和验证规则的字典
        """
        pass
    
    @abc.abstractmethod
    def update_config(self, config: Dict[str, Any]) -> bool:
        """
        更新策略配置
        
        Args:
            config: 新的配置信息
            
        Returns:
            更新是否成功
        """
        pass
    
    @abc.abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """
        获取策略能力信息
        
        Returns:
            描述策略支持的能力和限制的字典
        """
        pass
    
    @abc.abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """
        获取策略性能指标
        
        Returns:
            描述策略性能指标的字典
        """
        pass

class IServiceRegistry(abc.ABC):
    """
    服务注册接口
    
    定义服务注册和发现的标准接口，提供统一的服务管理机制。
    """
    
    @abc.abstractmethod
    def register_service(self, service_name: str, service_instance: Any) -> bool:
        """
        注册服务
        
        Args:
            service_name: 服务名称
            service_instance: 服务实例
            
        Returns:
            注册是否成功
        """
        pass
    
    @abc.abstractmethod
    def get_service(self, service_name: str) -> Optional[Any]:
        """
        获取服务实例
        
        Args:
            service_name: 服务名称
            
        Returns:
            服务实例，不存在则返回None
        """
        pass
    
    @abc.abstractmethod
    def has_service(self, service_name: str) -> bool:
        """
        检查服务是否存在
        
        Args:
            service_name: 服务名称
            
        Returns:
            服务是否存在
        """
        pass 