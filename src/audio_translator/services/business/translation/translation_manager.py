"""
翻译管理器服务模块

此模块定义了翻译管理器服务，负责协调不同的翻译策略和命名规则，
提供统一的文件名翻译和格式化接口。
"""

import logging
from typing import Dict, List, Any, Optional
import time
import os

from ...core.base_service import BaseService
from ...core.service_factory import ServiceFactory
from ...core.interfaces import ITranslationStrategy, INamingRule
from .strategies.strategy_registry import StrategyRegistry
from .strategies.adapters.openai_adapter import OpenAIAdapter
from .strategies.adapters.anthropic_adapter import AnthropicAdapter
from .strategies.adapters.gemini_adapter import GeminiAdapter
from .strategies.adapters.alibaba_adapter import AlibabaAdapter
from .strategies.adapters.zhipu_adapter import ZhipuAdapter
from .strategies.adapters.volc_adapter import VolcAdapter
from .strategies.adapters.deepseek_adapter import DeepSeekAdapter
from .strategies.dynamic_strategy_loader import DynamicStrategyLoader
from .cache.cache_manager import CacheManager
from .context.context_processor import ContextProcessor

# 设置日志记录器
logger = logging.getLogger(__name__)

class TranslationManager(BaseService):
    """
    翻译管理器服务
    
    负责协调翻译策略和命名规则，为应用提供统一的翻译和命名接口。
    主要功能：
    - 管理翻译策略和命名规则
    - 执行文件名翻译
    - 应用命名规则生成最终文件名
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化翻译管理器
        
        Args:
            config: 翻译管理器配置
        """
        super().__init__('translation_manager_service', config)
        
        # 配置信息
        self.config = config or {}
        
        # 服务工厂，用于获取依赖服务
        self.service_factory = None
        
        # 翻译策略注册表
        self.strategy_registry = StrategyRegistry()
        
        # 缓存管理器
        self.cache_manager = CacheManager()
        
        # 上下文处理器
        self.context_processor = ContextProcessor()
        
        # 动态策略加载器
        config_dir = self.config.get('strategies_config_dir', None)
        plugins_dir = self.config.get('plugins_dir', None)
        self.strategy_loader = DynamicStrategyLoader(self.strategy_registry, config_dir, plugins_dir)
        
        # 默认翻译策略
        self.default_strategy = None
        
        # 默认命名规则
        self.default_rule = None
        
        # 性能指标
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # 加载默认配置
        self._load_default_config()
        
        # 命名规则注册表
        self._naming_rules: Dict[str, INamingRule] = {}
        
        # 依赖服务
        self._category_service = None
        self._ucs_service = None
    
    def initialize(self) -> bool:
        """
        初始化翻译管理器
        
        获取依赖服务，加载配置，注册默认策略和规则。
        
        Returns:
            初始化是否成功
        """
        try:
            # 获取服务工厂
            factory = ServiceFactory.get_instance()
            
            # 获取依赖服务
            self._category_service = factory.get_service('category_service')
            self._ucs_service = factory.get_service('ucs_service')
            
            # 加载默认配置
            self._load_default_config()
            
            # 注册默认策略和规则
            self._register_default_strategies()
            self._register_default_rules()
            
            # 从配置文件加载策略
            if self.config.get('load_from_config', True):
                config_file = self.config.get('strategies_config_file', None)
                loaded_count = self.strategy_loader.load_from_config(config_file)
                logger.info(f"从配置文件加载了 {loaded_count} 个策略")
                
            # 从插件目录加载策略
            if self.config.get('load_from_plugins', True):
                plugins_dir = self.config.get('plugins_dir', None)
                loaded_count = self.strategy_loader.load_from_directory(plugins_dir)
                logger.info(f"从插件目录加载了 {loaded_count} 个策略")
            
            # 初始化缓存管理器
            if self.cache_manager:
                try:
                    # 尝试调用initialize方法
                    if hasattr(self.cache_manager, 'initialize'):
                        self.cache_manager.initialize()
                    else:
                        # 如果没有initialize方法，直接调用_initialize_cache方法
                        logger.warning("CacheManager没有initialize方法，尝试调用_initialize_cache")
                        if hasattr(self.cache_manager, '_initialize_cache'):
                            self.cache_manager._initialize_cache()
                except Exception as cache_error:
                    # 如果初始化失败，创建一个新的缓存管理器
                    logger.warning(f"缓存管理器初始化失败: {cache_error}，创建新的缓存管理器")
                    self.cache_manager = CacheManager()
                    # 确保新的缓存管理器已初始化
                    self.cache_manager._initialize_cache()
            
            self.is_initialized = True
            logger.info("翻译管理器初始化成功")
            logger.info(f"可用策略: {', '.join(self.strategy_registry.list_strategies())}")
            return True
        except Exception as e:
            logger.error(f"翻译管理器初始化失败: {e}")
            return False
    
    def _load_default_config(self):
        """加载默认配置"""
        # 从配置中读取默认策略和规则
        self.default_strategy = self.config.get('default_strategy', 'openai')
        self.default_rule = self.config.get('default_rule', 'direct')
    
    def _register_default_strategies(self):
        """注册默认翻译策略"""
        try:
            # 获取配置信息
            strategies_config = self.config.get('strategies', {})
            
            # 注册OpenAI策略
            openai_config = strategies_config.get('openai', {})
            self.strategy_registry.register('openai', OpenAIAdapter(openai_config))
            
            # 注册Anthropic策略
            anthropic_config = strategies_config.get('anthropic', {})
            self.strategy_registry.register('anthropic', AnthropicAdapter(anthropic_config))
            
            # 注册Gemini策略
            gemini_config = strategies_config.get('gemini', {})
            self.strategy_registry.register('gemini', GeminiAdapter(gemini_config))
            
            # 注册阿里通义策略
            alibaba_config = strategies_config.get('alibaba', {})
            self.strategy_registry.register('alibaba', AlibabaAdapter(alibaba_config))
            
            # 注册智谱AI策略
            zhipu_config = strategies_config.get('zhipu', {})
            self.strategy_registry.register('zhipu', ZhipuAdapter(zhipu_config))
            
            # 注册Volc策略
            volc_config = strategies_config.get('volc', {})
            self.strategy_registry.register('volc', VolcAdapter(volc_config))
            
            # 注册DeepSeek策略
            deepseek_config = strategies_config.get('deepseek', {})
            self.strategy_registry.register('deepseek', DeepSeekAdapter(deepseek_config))
            
            # 设置默认策略
            default_strategy = self.config.get('default_strategy', 'openai')
            if self.strategy_registry.has(default_strategy):
                self.default_strategy = default_strategy
            elif self.strategy_registry.list_strategies():
                self.default_strategy = self.strategy_registry.list_strategies()[0]
            
            logger.info(f"成功注册{len(self.strategy_registry.list_strategies())}个翻译策略")
        except Exception as e:
            logger.error(f"注册默认翻译策略失败: {e}")
    
    def _register_default_rules(self):
        """注册默认命名规则"""
        # 这里将在后续实现中添加默认规则的注册
        pass
    
    def register_translation_strategy(self, name: str, strategy: ITranslationStrategy) -> bool:
        """
        注册翻译策略
        
        Args:
            name: 策略名称
            strategy: 策略实例
            
        Returns:
            注册是否成功
        """
        return self.strategy_registry.register(name, strategy)
    
    def register_naming_rule(self, name: str, rule: INamingRule) -> bool:
        """
        注册命名规则
        
        Args:
            name: 规则名称
            rule: 规则实例
            
        Returns:
            注册是否成功
        """
        try:
            self._naming_rules[name] = rule
            logger.info(f"成功注册命名规则: {name}")
            return True
        except Exception as e:
            logger.error(f"注册命名规则失败: {name}, {e}")
            return False
    
    def set_default_strategy(self, name: str) -> bool:
        """
        设置默认翻译策略
        
        Args:
            name: 策略名称
            
        Returns:
            设置是否成功
        """
        if self.strategy_registry.get(name):
            self.default_strategy = name
            # 更新配置
            self.config['default_strategy'] = name
            logger.info(f"设置默认翻译策略: {name}")
            return True
        logger.warning(f"设置默认翻译策略失败: 找不到策略 {name}")
        return False
    
    def set_default_rule(self, name: str) -> bool:
        """
        设置默认命名规则
        
        Args:
            name: 规则名称
            
        Returns:
            设置是否成功
        """
        if name in self._naming_rules:
            self.default_rule = name
            # 更新配置
            self.config['default_rule'] = name
            logger.info(f"设置默认命名规则: {name}")
            return True
        logger.warning(f"设置默认命名规则失败: 找不到规则 {name}")
        return False
    
    def get_translation_strategy(self, name: Optional[str] = None) -> Optional[ITranslationStrategy]:
        """
        获取翻译策略
        
        Args:
            name: 策略名称，如果为None则返回默认策略
            
        Returns:
            翻译策略实例，找不到则返回None
        """
        if name is None:
            name = self.default_strategy
        
        return self.strategy_registry.get(name)
    
    def get_naming_rule(self, name: Optional[str] = None) -> Optional[INamingRule]:
        """
        获取命名规则
        
        Args:
            name: 规则名称，如果为None则返回默认规则
            
        Returns:
            命名规则实例，找不到则返回None
        """
        if name is None:
            name = self.default_rule
        
        return self._naming_rules.get(name)
    
    def translate_file(self, file_path: str, strategy_name: Optional[str] = None, rule_name: Optional[str] = None) -> Dict[str, Any]:
        """
        翻译文件名并应用命名规则
        
        Args:
            file_path: 文件路径
            strategy_name: 翻译策略名称，如果为None则使用默认策略
            rule_name: 命名规则名称，如果为None则使用默认规则
            
        Returns:
            包含翻译结果和文件信息的字典
        """
        try:
            # 获取文件名和扩展名
            file_name = os.path.basename(file_path)
            name, ext = os.path.splitext(file_name)
            
            # 构建翻译上下文
            context = {
                'original_name': name,
                'extension': ext,
                'file_path': file_path
            }
            
            # 获取分类信息
            if self._category_service and self._category_service.is_available():
                cat_info = self._category_service.guess_category_with_fields(name)
                if cat_info:
                    context.update(cat_info)
            
            # 获取翻译策略
            strategy = self.get_translation_strategy(strategy_name)
            if not strategy:
                logger.error(f"翻译失败: 找不到策略 {strategy_name}")
                return {
                    'success': False,
                    'error': f"找不到翻译策略: {strategy_name}",
                    'original_name': name,
                    'translated_name': name,
                    'final_name': file_name
                }
            
            # 执行翻译
            translated = strategy.translate(name, context)
            context['translated_name'] = translated
            
            # 获取命名规则
            rule = self.get_naming_rule(rule_name)
            if not rule:
                logger.error(f"应用命名规则失败: 找不到规则 {rule_name}")
                return {
                    'success': True,
                    'original_name': name,
                    'translated_name': translated,
                    'final_name': translated + ext,
                    'context': context
                }
            
            # 验证上下文是否满足规则要求
            if not rule.validate(context):
                # 尝试填充缺失字段
                context = self._fill_missing_fields(rule, context)
            
            # 应用命名规则
            final_name = rule.format(context)
            
            # 返回结果
            return {
                'success': True,
                'original_name': name,
                'translated_name': translated,
                'final_name': final_name,
                'context': context
            }
        except Exception as e:
            logger.error(f"翻译文件失败: {file_path}, {e}")
            return {
                'success': False,
                'error': str(e),
                'original_name': os.path.basename(file_path),
                'translated_name': os.path.basename(file_path),
                'final_name': os.path.basename(file_path)
            }
    
    def _fill_missing_fields(self, rule: INamingRule, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        填充缺失的字段
        
        Args:
            rule: 命名规则
            context: 翻译上下文
            
        Returns:
            填充后的上下文
        """
        required_fields = rule.get_required_fields()
        for field in required_fields:
            if field not in context:
                # 特殊字段处理
                if field.startswith('category') and self._category_service and 'original_name' in context:
                    # 尝试获取分类信息
                    cat_info = self._category_service.guess_category_with_fields(context['original_name'])
                    if cat_info:
                        context.update(cat_info)
                else:
                    # 添加默认值
                    context[field] = f"未知{field}"
        
        return context
    
    def get_available_strategies(self) -> List[Dict[str, Any]]:
        """
        获取所有可用的翻译策略信息
        
        Returns:
            策略信息列表
        """
        strategies = []
        for name in self.strategy_registry.list_strategies():
            strategy = self.strategy_registry.get(name)
            metadata = self.strategy_registry.get_metadata(name)
            
            strategies.append({
                'name': name,
                'description': strategy.get_description(),
                'provider_type': strategy.get_provider_type(),
                'is_default': name == self.default_strategy,
                'metadata': metadata or {}
            })
            
        return strategies
    
    def get_available_rules(self) -> List[Dict[str, Any]]:
        """
        获取所有可用的命名规则信息
        
        Returns:
            规则信息列表
        """
        rules = []
        for name, rule in self._naming_rules.items():
            # 检查规则是否有获取描述的方法
            description = "命名规则"
            if hasattr(rule, 'get_description') and callable(getattr(rule, 'get_description')):
                description = rule.get_description()
                
            rules.append({
                'name': name,
                'description': description,
                'required_fields': rule.get_required_fields(),
                'is_default': name == self.default_rule
            })
        return rules
    
    def preview_filename(self, name: str, strategy_name: Optional[str] = None, rule_name: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        预览文件名翻译和格式化结果
        
        Args:
            name: 原始文件名
            strategy_name: 翻译策略名称
            rule_name: 命名规则名称
            context: 附加上下文信息
            
        Returns:
            预览结果
        """
        # 构建基础上下文
        ctx = context or {}
        
        # 分离文件名和扩展名
        import os
        name_part, ext_part = os.path.splitext(name)
        
        # 添加基本字段
        ctx.update({
            'original_name': name_part,
            'extension': ext_part
        })
        
        # 获取翻译策略
        strategy = self.get_translation_strategy(strategy_name)
        if not strategy:
            return {
                'success': False,
                'error': f"找不到翻译策略: {strategy_name}",
                'preview': name
            }
        
        # 执行翻译
        translated = strategy.translate(name_part, ctx)
        ctx['translated_name'] = translated
        
        # 获取命名规则
        rule = self.get_naming_rule(rule_name)
        if not rule:
            return {
                'success': False,
                'error': f"找不到命名规则: {rule_name}",
                'preview': translated + ext_part
            }
        
        # 验证上下文是否满足规则要求
        if not rule.validate(ctx):
            # 尝试填充缺失字段
            ctx = self._fill_missing_fields(rule, ctx)
        
        # 应用命名规则
        final_name = rule.format(ctx)
        
        return {
            'success': True,
            'original_name': name,
            'translated_name': translated,
            'preview': final_name,
            'context': ctx
        }
    
    def translate(self, text: str, strategy_name: str = None, context: Dict[str, Any] = None) -> str:
        """
        使用指定策略翻译文本
        
        Args:
            text: 要翻译的文本
            strategy_name: 策略名称，如果为None则使用默认策略
            context: 上下文信息
            
        Returns:
            翻译后的文本
            
        Raises:
            ValueError: 当策略不存在时
        """
        start_time = time.time()
        self.metrics["total_requests"] += 1
        
        try:
            # 使用指定策略或默认策略
            strategy_name = strategy_name or self.default_strategy
            strategy = self.strategy_registry.get(strategy_name)
            
            if not strategy:
                error_msg = f"策略不存在: {strategy_name}"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            # 准备上下文
            context = context or {}
            
            # 检查缓存是否存在译文
            if self.cache_manager and self.config.get('use_cache', True):
                cached_translation = self.cache_manager.get(text, context)
                if cached_translation:
                    logger.debug(f"使用缓存的翻译结果: {strategy_name}")
                    self.metrics["successful_requests"] += 1
                    self._update_response_time(time.time() - start_time)
                    return cached_translation
            
            # 预处理文本
            if self.context_processor:
                processed_text, updated_context = self.context_processor.preprocess(text, context)
            else:
                processed_text, updated_context = text, context
            
            # 检查是否需要分段处理
            max_length = strategy.get_capabilities().get('max_text_length', 4000)
            if len(processed_text) > max_length and self.context_processor:
                # 分段处理
                segments = self.context_processor.split_text(processed_text, updated_context)
                translations = []
                
                for segment_text, segment_context in segments:
                    segment_translation = strategy.translate(segment_text, segment_context)
                    translations.append(segment_translation)
                
                # 合并翻译结果
                translation = self.context_processor.merge_translations(
                    translations, 
                    [segment_context for _, segment_context in segments]
                )
            else:
                # 直接翻译
                translation = strategy.translate(processed_text, updated_context)
            
            # 后处理翻译结果
            if self.context_processor:
                translation = self.context_processor.postprocess(translation, updated_context)
            
            # 缓存翻译结果
            if self.cache_manager and self.config.get('use_cache', True):
                self.cache_manager.set(text, translation, context)
            
            # 更新指标
            self.metrics["successful_requests"] += 1
            self._update_response_time(time.time() - start_time)
            
            return translation
        except Exception as e:
            logger.error(f"翻译失败: {e}")
            self.metrics["failed_requests"] += 1
            raise
    
    def batch_translate(self, texts: List[str], strategy_name: str = None, context: Dict[str, Any] = None) -> List[str]:
        """
        批量翻译文本
        
        Args:
            texts: 要翻译的文本列表
            strategy_name: 策略名称，如果为None则使用默认策略
            context: 上下文信息
            
        Returns:
            翻译后的文本列表
        """
        results = []
        
        for text in texts:
            try:
                translation = self.translate(text, strategy_name, context)
                results.append(translation)
            except Exception as e:
                logger.error(f"批量翻译失败: {e}")
                # 在错误情况下返回原文
                results.append(text)
                
        return results
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        获取性能指标
        
        Returns:
            指标字典
        """
        metrics = self.metrics.copy()
        
        # 添加缓存指标
        if self.cache_manager:
            cache_metrics = self.cache_manager.get_metrics()
            metrics['cache'] = cache_metrics
            
        # 添加策略指标
        strategies_metrics = {}
        for name, strategy in self.strategy_registry.get_all_strategies().items():
            strategies_metrics[name] = strategy.get_metrics()
            
        metrics['strategies'] = strategies_metrics
        metrics['last_updated'] = time.time()
        
        return metrics
    
    def clear_cache(self, pattern: str = None) -> int:
        """
        清除缓存
        
        Args:
            pattern: 匹配模式，如果为None则清除所有缓存
            
        Returns:
            清除的条目数量
        """
        if self.cache_manager:
            return self.cache_manager.clear(pattern)
        return 0
    
    def _update_response_time(self, response_time: float) -> None:
        """
        更新平均响应时间
        
        Args:
            response_time: 响应时间（秒）
        """
        current_avg = self.metrics["average_response_time"]
        total_requests = self.metrics["successful_requests"] + self.metrics["failed_requests"]
        
        if total_requests == 1:
            # 第一个请求
            self.metrics["average_response_time"] = response_time
        else:
            # 使用移动平均值
            self.metrics["average_response_time"] = current_avg * 0.9 + response_time * 0.1 
    
    def get_strategy(self, strategy_name: str) -> Optional[ITranslationStrategy]:
        """
        获取指定名称的翻译策略
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            翻译策略对象，如果不存在则返回None
        """
        return self.strategy_registry.get(strategy_name) 