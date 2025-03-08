"""
命名服务模块，提供文件命名规则管理和应用功能
"""
from typing import Dict, List, Any, Optional, Tuple
import os
import logging
import json
from pathlib import Path

from ...core.base_service import BaseService
from ...core.service_factory import ServiceFactory
from .naming_rule import INamingRule
from .rule_registry import RuleRegistry
from .rule_validator import RuleValidator
from .template_processor import TemplateProcessor
from .rules import (
    DirectNamingRule,
    BilingualNamingRule,
    UCSNamingRule,
    TemplateNamingRule,
)

logger = logging.getLogger(__name__)


class NamingService(BaseService):
    """
    命名服务类，负责管理命名规则和模板
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化命名服务
        
        Args:
            config: 服务配置
        """
        super().__init__('naming_service', config)
        self.rule_registry = RuleRegistry()
        self.rule_validator = RuleValidator()
        self.template_processor = TemplateProcessor()
        self.category_service = None
        self.config_service = None
        self.custom_rules_file = None
    
    def initialize(self) -> bool:
        """
        初始化命名服务
        
        Returns:
            初始化是否成功
        """
        try:
            # 获取依赖服务
            factory = ServiceFactory.get_instance()
            self.category_service = factory.get_service('category_service')
            self.config_service = factory.get_service('config_service')
            
            # 初始化路径
            self._initialize_paths()
            
            # 注册默认规则
            self._register_default_rules()
            
            # 加载自定义规则
            self._load_custom_rules()
            
            self.is_initialized = True
            logger.info("命名服务初始化成功")
            return True
        except Exception as e:
            logger.error(f"初始化命名服务失败: {e}")
            return False
    
    def _initialize_paths(self) -> None:
        """初始化路径配置"""
        if self.config_service:
            data_dir = Path(self.config_service.get_data_dir())
            self.custom_rules_file = data_dir / "naming" / "custom_rules.json"
            
            # 确保目录存在
            os.makedirs(self.custom_rules_file.parent, exist_ok=True)
        else:
            logger.warning("配置服务不可用，使用默认路径")
            self.custom_rules_file = Path('data/naming/custom_rules.json')
            os.makedirs(self.custom_rules_file.parent, exist_ok=True)
    
    def _register_default_rules(self) -> None:
        """注册默认命名规则"""
        # 直接翻译规则
        direct_rule = DirectNamingRule()
        self.rule_registry.register_rule('direct', direct_rule)
        
        # 双语规则
        bilingual_rule = BilingualNamingRule()
        self.rule_registry.register_rule('bilingual', bilingual_rule)
        
        # UCS标准规则
        ucs_rule = UCSNamingRule()
        if self.category_service:
            ucs_rule.set_category_service(self.category_service)
        self.rule_registry.register_rule('ucs', ucs_rule)
        
        # 设置默认规则
        self.rule_registry.set_default_rule('direct')
        
        logger.info("已注册默认命名规则")
    
    def _load_custom_rules(self) -> None:
        """加载自定义命名规则"""
        if not self.custom_rules_file or not self.custom_rules_file.exists():
            logger.info("没有找到自定义规则文件")
            return
            
        try:
            with open(self.custom_rules_file, 'r', encoding='utf-8') as f:
                custom_rules = json.load(f)
                
            for rule_name, rule_config in custom_rules.items():
                rule_type = rule_config.get('type')
                
                if rule_type == 'template':
                    # 创建模板规则
                    template = rule_config.get('template', '{translated_name}')
                    description = rule_config.get('description')
                    rule = TemplateNamingRule(template, description)
                    self.rule_registry.register_rule(rule_name, rule)
                    
            logger.info(f"已加载 {len(custom_rules)} 个自定义命名规则")
                
        except Exception as e:
            logger.error(f"加载自定义命名规则失败: {e}")
    
    def _save_custom_rules(self) -> bool:
        """
        保存自定义命名规则
        
        Returns:
            保存是否成功
        """
        if not self.custom_rules_file:
            logger.error("未设置自定义规则文件路径")
            return False
            
        try:
            # 获取所有规则
            rules = self.rule_registry.get_available_rules()
            
            # 过滤出自定义规则（非默认规则）
            default_rules = ['direct', 'bilingual', 'ucs']
            custom_rules = {name: self.rule_registry.get_rule_metadata(name) 
                           for name in rules if name not in default_rules}
            
            # 保存到文件
            with open(self.custom_rules_file, 'w', encoding='utf-8') as f:
                json.dump(custom_rules, f, ensure_ascii=False, indent=2)
                
            logger.info(f"已保存 {len(custom_rules)} 个自定义命名规则")
            return True
        except Exception as e:
            logger.error(f"保存自定义命名规则失败: {e}")
            return False
    
    def register_rule(self, name: str, rule: INamingRule) -> bool:
        """
        注册命名规则
        
        Args:
            name: 规则名称
            rule: 规则实例
            
        Returns:
            注册是否成功
        """
        # 验证规则
        if not self.rule_validator.validate_rule(rule):
            logger.error(f"规则验证失败: {name}")
            return False
            
        # 注册规则
        success = self.rule_registry.register_rule(name, rule)
        
        # 如果是自定义规则，保存到文件
        if success and name not in ['direct', 'bilingual', 'ucs']:
            self._save_custom_rules()
            
        return success
    
    def unregister_rule(self, name: str) -> bool:
        """
        注销命名规则
        
        Args:
            name: 规则名称
            
        Returns:
            注销是否成功
        """
        # 不允许注销默认规则
        if name in ['direct', 'bilingual', 'ucs']:
            logger.error(f"不能注销默认规则: {name}")
            return False
            
        # 注销规则
        success = self.rule_registry.unregister_rule(name)
        
        # 保存更改
        if success:
            self._save_custom_rules()
            
        return success
    
    def get_rule(self, name: Optional[str] = None) -> Optional[INamingRule]:
        """
        获取命名规则
        
        Args:
            name: 规则名称，如果为None则返回默认规则
            
        Returns:
            规则实例，如果不存在则返回None
        """
        return self.rule_registry.get_rule(name)
    
    def set_default_rule(self, name: str) -> bool:
        """
        设置默认命名规则
        
        Args:
            name: 规则名称
            
        Returns:
            设置是否成功
        """
        return self.rule_registry.set_default_rule(name)
    
    def get_available_rules(self) -> List[str]:
        """
        获取所有可用的命名规则名称
        
        Returns:
            规则名称列表
        """
        return self.rule_registry.get_available_rules()
    
    def get_rule_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取规则元数据
        
        Args:
            name: 规则名称
            
        Returns:
            规则元数据，如果不存在则返回None
        """
        return self.rule_registry.get_rule_metadata(name)
    
    def format_filename(self, rule_name: Optional[str], context: Dict[str, Any]) -> str:
        """
        使用指定规则格式化文件名
        
        Args:
            rule_name: 规则名称，如果为None则使用默认规则
            context: 命名上下文
            
        Returns:
            格式化后的文件名
        """
        # 获取规则
        rule = self.get_rule(rule_name)
        if rule is None:
            logger.warning(f"规则不存在: {rule_name}，使用默认规则")
            rule = self.get_rule()
            
        if rule is None:
            logger.error("没有可用的规则")
            return context.get('original_name', 'unknown')
        
        # 验证上下文
        if not rule.validate(context):
            logger.warning(f"上下文验证失败，缺少必要字段")
            # 尝试修复上下文
            context = self.rule_validator.suggest_fixes(rule, context)
        
        # 格式化文件名
        return rule.format(context)
    
    def preview_filename(self, rule_name: Optional[str], context: Dict[str, Any]) -> str:
        """
        预览文件名格式化结果
        
        Args:
            rule_name: 规则名称，如果为None则使用默认规则
            context: 命名上下文
            
        Returns:
            预览结果
        """
        return self.format_filename(rule_name, context)
    
    def create_template_rule(self, name: str, template: str, description: Optional[str] = None) -> bool:
        """
        创建模板规则
        
        Args:
            name: 规则名称
            template: 模板字符串
            description: 规则描述
            
        Returns:
            创建是否成功
        """
        # 验证模板
        if not self.template_processor.validate_template(template):
            logger.error(f"模板验证失败: {template}")
            return False
            
        # 创建规则
        rule = TemplateNamingRule(template, description)
        
        # 注册规则
        return self.register_rule(name, rule)
    
    def extract_context_from_filename(self, filename: str) -> Dict[str, Any]:
        """
        从文件名提取上下文信息
        
        Args:
            filename: 文件名
            
        Returns:
            上下文信息
        """
        context = {}
        
        # 提取原始文件名
        context['original_name'] = os.path.splitext(filename)[0]
        
        # 提取扩展名
        ext = os.path.splitext(filename)[1]
        context['extension'] = ext
        
        # 尝试提取分类信息
        if self.category_service and hasattr(self.category_service, 'guess_category_with_fields'):
            try:
                cat_info = self.category_service.guess_category_with_fields(filename)
                context.update(cat_info)
            except Exception as e:
                logger.warning(f"获取分类信息失败: {e}")
        
        return context 