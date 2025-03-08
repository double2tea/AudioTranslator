import os
import importlib
import inspect
import logging
import json
import yaml
from typing import Dict, Any, List, Type, Optional

from ..strategies.strategy_registry import StrategyRegistry 
from ..strategies.base_strategy import ITranslationStrategy
from ..strategies.model_service_adapter import ModelServiceAdapter

logger = logging.getLogger(__name__)

class DynamicStrategyLoader:
    """动态策略加载器，用于从配置文件或插件目录加载翻译策略"""
    
    def __init__(self, registry: StrategyRegistry, config_dir: str = None, plugins_dir: str = None):
        """
        初始化动态策略加载器
        
        Args:
            registry: 策略注册表实例
            config_dir: 配置文件目录，默认为./config/strategies
            plugins_dir: 插件目录，默认为./plugins/strategies
        """
        self.registry = registry
        self.config_dir = config_dir or os.path.join('.', 'config', 'strategies')
        self.plugins_dir = plugins_dir or os.path.join('.', 'plugins', 'strategies')
        self.loaded_strategies = {}  # 类型: Dict[str, ITranslationStrategy]
        
    def load_from_config(self, config_file: str = None) -> int:
        """
        从配置文件加载策略
        
        Args:
            config_file: 配置文件路径，如果为None则使用默认路径
            
        Returns:
            加载的策略数量
        """
        if config_file is None:
            config_file = os.path.join(self.config_dir, 'strategies.json')
            
        if not os.path.exists(config_file):
            logger.warning(f"策略配置文件不存在: {config_file}")
            return 0
            
        try:
            # 根据文件扩展名决定解析方式
            if config_file.endswith('.json'):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            elif config_file.endswith(('.yaml', '.yml')):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
            else:
                logger.error(f"不支持的配置文件格式: {config_file}")
                return 0
                
            # 加载策略
            return self._load_strategies_from_config(config)
        except Exception as e:
            logger.error(f"加载策略配置文件失败: {e}")
            return 0
            
    def _load_strategies_from_config(self, config: Dict[str, Any]) -> int:
        """
        从配置字典加载策略
        
        Args:
            config: 策略配置字典
            
        Returns:
            加载的策略数量
        """
        strategies_config = config.get('strategies', {})
        loaded_count = 0
        
        for strategy_name, strategy_config in strategies_config.items():
            if 'type' not in strategy_config:
                logger.warning(f"策略配置缺少'type'字段: {strategy_name}")
                continue
                
            strategy_type = strategy_config['type']
            try:
                # 尝试加载策略适配器
                adapter_class = self._get_adapter_class(strategy_type)
                if adapter_class:
                    adapter_instance = adapter_class(strategy_config)
                    self.registry.register_strategy(adapter_instance)
                    self.loaded_strategies[strategy_name] = adapter_instance
                    loaded_count += 1
                    logger.info(f"已成功加载策略: {strategy_name} (类型: {strategy_type})")
            except Exception as e:
                logger.error(f"加载策略失败 {strategy_name}: {e}")
                
        return loaded_count
        
    def load_from_directory(self, directory: str = None) -> int:
        """
        从插件目录加载策略
        
        Args:
            directory: 插件目录，如果为None则使用默认路径
            
        Returns:
            加载的策略数量
        """
        if directory is None:
            directory = self.plugins_dir
            
        if not os.path.exists(directory):
            logger.warning(f"插件目录不存在: {directory}")
            return 0
            
        # 获取所有Python文件
        plugin_files = [f for f in os.listdir(directory) if f.endswith('.py') and not f.startswith('__')]
        
        # 加载每个插件
        loaded_count = 0
        for plugin_file in plugin_files:
            try:
                module_name = plugin_file[:-3]  # 移除.py扩展名
                module_path = os.path.join(directory, plugin_file)
                
                # 动态导入模块
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                if spec is None or spec.loader is None:
                    logger.warning(f"无法加载插件模块: {module_path}")
                    continue
                    
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 查找策略类
                strategies = self._find_strategy_classes(module)
                for strategy_class in strategies:
                    try:
                        strategy_instance = strategy_class()
                        self.registry.register_strategy(strategy_instance)
                        self.loaded_strategies[strategy_instance.get_name()] = strategy_instance
                        loaded_count += 1
                        logger.info(f"已成功加载插件策略: {strategy_instance.get_name()} (文件: {plugin_file})")
                    except Exception as e:
                        logger.error(f"实例化策略失败 {strategy_class.__name__}: {e}")
            except Exception as e:
                logger.error(f"加载插件失败 {plugin_file}: {e}")
                
        return loaded_count
        
    def _find_strategy_classes(self, module) -> List[Type[ITranslationStrategy]]:
        """
        在模块中查找实现了ITranslationStrategy接口的类
        
        Args:
            module: 导入的模块
            
        Returns:
            策略类列表
        """
        strategy_classes = []
        
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                obj != ITranslationStrategy and 
                obj != ModelServiceAdapter and
                issubclass(obj, ITranslationStrategy)):
                strategy_classes.append(obj)
                
        return strategy_classes
        
    def _get_adapter_class(self, adapter_type: str) -> Optional[Type[ModelServiceAdapter]]:
        """
        获取适配器类
        
        Args:
            adapter_type: 适配器类型
            
        Returns:
            适配器类
        """
        # 构建适配器导入路径
        module_path = f"audio_translator.services.business.translation.strategies.adapters.{adapter_type}_adapter"
        class_name = f"{adapter_type.capitalize()}Adapter"
        
        try:
            # 动态导入适配器模块
            module = importlib.import_module(module_path)
            # 获取适配器类
            adapter_class = getattr(module, class_name)
            return adapter_class
        except (ImportError, AttributeError) as e:
            logger.error(f"加载适配器类失败 {adapter_type}: {e}")
            return None
            
    def unload_strategy(self, strategy_name: str) -> bool:
        """
        卸载策略
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            是否成功卸载
        """
        if strategy_name in self.loaded_strategies:
            if self.registry.unregister_strategy(strategy_name):
                del self.loaded_strategies[strategy_name]
                logger.info(f"已成功卸载策略: {strategy_name}")
                return True
        logger.warning(f"策略未加载或卸载失败: {strategy_name}")
        return False
        
    def reload_all(self) -> int:
        """
        重新加载所有策略
        
        Returns:
            加载的策略数量
        """
        # 卸载所有策略
        for strategy_name in list(self.loaded_strategies.keys()):
            self.unload_strategy(strategy_name)
            
        # 重新加载配置文件
        config_count = self.load_from_config()
        
        # 重新加载插件目录
        plugin_count = self.load_from_directory()
        
        return config_count + plugin_count
        
    def get_loaded_strategies(self) -> Dict[str, ITranslationStrategy]:
        """
        获取所有已加载的策略
        
        Returns:
            已加载的策略字典
        """
        return self.loaded_strategies.copy()
        
    def check_updates(self) -> Dict[str, Any]:
        """
        检查策略更新
        
        Returns:
            更新信息，包括新增、移除和变更的策略
        """
        # 实现策略更新检查逻辑
        # 这里可以检查配置文件和插件目录的变更
        # TODO: 实现策略版本比较和更新检测
        return {
            'added': [],
            'removed': [],
            'updated': []
        } 