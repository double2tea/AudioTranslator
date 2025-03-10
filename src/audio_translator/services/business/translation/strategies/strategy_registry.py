"""
策略注册表模块

此模块提供了翻译策略的注册和管理功能，所有翻译策略都通过此注册表进行管理。
"""

import logging
from typing import Dict, List, Any, Optional, Type, Union

from ....core.interfaces import ITranslationStrategy

# 设置日志记录器
logger = logging.getLogger(__name__)

class StrategyRegistry:
    """
    翻译策略注册表
    
    管理所有翻译策略，提供注册、获取、列举策略的功能。
    """
    
    def __init__(self):
        """初始化策略注册表"""
        # 存储策略实例
        self.strategies: Dict[str, ITranslationStrategy] = {}
        # 存储策略元数据
        self.strategy_metadata: Dict[str, Dict[str, Any]] = {}
    
    def register(self, name: str, strategy: ITranslationStrategy, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        注册策略
        
        Args:
            name: 策略名称
            strategy: 策略实现
            metadata: 策略元数据
            
        Returns:
            注册是否成功
        """
        try:
            if name in self.strategies:
                logger.warning(f"策略已存在，将被覆盖: {name}")
                
            self.strategies[name] = strategy
            
            # 设置元数据
            self.strategy_metadata[name] = metadata or {
                "name": strategy.get_name(),
                "description": strategy.get_description(),
                "provider_type": strategy.get_provider_type(),
                "capabilities": strategy.get_capabilities()
            }
            
            logger.info(f"成功注册策略: {name}")
            return True
        except Exception as e:
            logger.error(f"注册策略失败: {name}, {str(e)}")
            return False
    
    def unregister(self, name: str) -> bool:
        """
        注销策略
        
        Args:
            name: 策略名称
            
        Returns:
            注销是否成功
        """
        try:
            if name not in self.strategies:
                logger.warning(f"注销策略失败: 找不到策略 {name}")
                return False
                
            del self.strategies[name]
            
            if name in self.strategy_metadata:
                del self.strategy_metadata[name]
                
            logger.info(f"成功注销策略: {name}")
            return True
        except Exception as e:
            logger.error(f"注销策略失败: {name}, {str(e)}")
            return False
    
    def get(self, name: str) -> Optional[ITranslationStrategy]:
        """
        获取策略
        
        Args:
            name: 策略名称
            
        Returns:
            策略实例，找不到则返回None
        """
        return self.strategies.get(name)
    
    def has(self, name: str) -> bool:
        """
        检查策略是否存在
        
        Args:
            name: 策略名称
            
        Returns:
            策略是否存在
        """
        return name in self.strategies
    
    def register_strategy(self, name_or_strategy: Union[str, ITranslationStrategy], strategy: Optional[ITranslationStrategy] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        注册翻译策略（register的别名方法）
        
        支持两种调用方式：
        1. register_strategy(strategy) - 直接传入策略对象，自动提取名称
        2. register_strategy(name, strategy, metadata) - 传入名称和策略对象
        
        Args:
            name_or_strategy: 策略名称或策略对象
            strategy: 翻译策略（如果第一个参数是名称）
            metadata: 策略元数据
            
        Returns:
            注册是否成功
        """
        # 处理只传入策略对象的情况
        if isinstance(name_or_strategy, ITranslationStrategy) and strategy is None:
            strategy = name_or_strategy
            name = strategy.get_name()
            return self.register(name, strategy, metadata)
        # 处理传入名称和策略对象的情况
        elif isinstance(name_or_strategy, str) and strategy is not None:
            return self.register(name_or_strategy, strategy, metadata)
        else:
            raise ValueError("参数类型错误，请检查调用方式")
    
    def get_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取策略元数据
        
        Args:
            name: 策略名称
            
        Returns:
            策略元数据，找不到则返回None
        """
        return self.strategy_metadata.get(name)
    
    def list_strategies(self) -> List[str]:
        """
        列出所有策略名称
        
        Returns:
            策略名称列表
        """
        return list(self.strategies.keys())
    
    def get_all_strategy_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有策略的元数据
        
        Returns:
            策略元数据字典，键为策略名称，值为元数据
        """
        return self.strategy_metadata.copy()
    
    def get_all_strategies(self) -> Dict[str, ITranslationStrategy]:
        """
        获取所有策略对象
        
        Returns:
            策略对象字典，键为策略名称，值为策略对象
        """
        return self.strategies.copy()
    
    def get_strategies_by_provider(self, provider_type: str) -> List[str]:
        """
        获取特定提供商类型的所有策略
        
        Args:
            provider_type: 提供商类型
            
        Returns:
            策略名称列表
        """
        return [
            name for name, metadata in self.strategy_metadata.items()
            if metadata.get("provider_type") == provider_type
        ] 