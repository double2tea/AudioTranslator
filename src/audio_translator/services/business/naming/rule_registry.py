"""
规则注册表模块，用于管理和存储命名规则
"""
from typing import Dict, List, Any, Optional
import logging
from .naming_rule import INamingRule

logger = logging.getLogger(__name__)


class RuleRegistry:
    """
    命名规则注册表，负责管理和存储命名规则
    """
    
    def __init__(self):
        """初始化规则注册表"""
        self.rules: Dict[str, INamingRule] = {}
        self.rule_metadata: Dict[str, Dict[str, Any]] = {}
        self.default_rule = None
    
    def register_rule(self, name: str, rule: INamingRule, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        注册命名规则
        
        Args:
            name: 规则名称
            rule: 规则实例
            metadata: 规则元数据
            
        Returns:
            注册是否成功
        """
        try:
            # 如果规则已存在，返回失败
            if name in self.rules:
                logger.warning(f"规则已存在: {name}")
                return False
                
            self.rules[name] = rule
            
            # 设置元数据
            self.rule_metadata[name] = metadata or {
                'name': name,
                'description': rule.get_description() if hasattr(rule, 'get_description') else f"命名规则: {name}",
                'required_fields': rule.get_required_fields()
            }
            
            # 如果是第一个规则，设为默认
            if self.default_rule is None:
                self.default_rule = name
                
            logger.info(f"注册命名规则成功: {name}")
            return True
        except Exception as e:
            logger.error(f"注册命名规则失败: {name}, {e}")
            return False
    
    def unregister_rule(self, name: str) -> bool:
        """
        注销命名规则
        
        Args:
            name: 规则名称
            
        Returns:
            注销是否成功
        """
        if name not in self.rules:
            logger.warning(f"规则不存在: {name}")
            return False
            
        # 删除规则和元数据
        del self.rules[name]
        if name in self.rule_metadata:
            del self.rule_metadata[name]
            
        # 如果删除的是默认规则，重置默认规则
        if self.default_rule == name:
            self.default_rule = next(iter(self.rules)) if self.rules else None
            
        logger.info(f"注销命名规则成功: {name}")
        return True
    
    def get_rule(self, name: Optional[str] = None) -> Optional[INamingRule]:
        """
        获取命名规则
        
        Args:
            name: 规则名称，如果为None则返回默认规则
            
        Returns:
            规则实例，如果不存在则返回None
        """
        if name is None:
            name = self.default_rule
            
        if name is None:
            logger.warning("没有可用的规则")
            return None
            
        rule = self.rules.get(name)
        if rule is None:
            logger.warning(f"规则不存在: {name}")
            
        return rule
    
    def set_default_rule(self, name: str) -> bool:
        """
        设置默认命名规则
        
        Args:
            name: 规则名称
            
        Returns:
            设置是否成功
        """
        if name not in self.rules:
            logger.warning(f"规则不存在: {name}")
            return False
            
        self.default_rule = name
        logger.info(f"设置默认命名规则: {name}")
        return True
    
    def get_default_rule(self) -> Optional[str]:
        """
        获取默认规则名称
        
        Returns:
            默认规则名称，如果没有则返回None
        """
        return self.default_rule
    
    def get_available_rules(self) -> List[str]:
        """
        获取所有可用的命名规则名称
        
        Returns:
            规则名称列表
        """
        return list(self.rules.keys())
    
    def get_rule_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取规则元数据
        
        Args:
            name: 规则名称
            
        Returns:
            规则元数据，如果不存在则返回None
        """
        return self.rule_metadata.get(name) 