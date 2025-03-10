import os
import importlib
import inspect
import logging
import json
import yaml
import pkg_resources
from typing import Dict, Any, List, Type, Optional
from pathlib import Path

from .strategy_registry import StrategyRegistry 
from ....core.interfaces import ITranslationStrategy
from .model_service_adapter import ModelServiceAdapter

logger = logging.getLogger(__name__)

class DynamicStrategyLoader:
    """动态策略加载器，用于从配置文件或插件目录加载翻译策略"""
    
    def __init__(self, registry: StrategyRegistry, config_dir: str = None, plugins_dir: str = None):
        """
        初始化动态策略加载器
        
        Args:
            registry: 策略注册表实例
            config_dir: 配置文件目录，默认为项目根目录下的config
            plugins_dir: 插件目录，默认为包内的plugins/strategies
        """
        self.registry = registry
        
        # 使用基于包的路径
        self.package_path = Path(pkg_resources.resource_filename('audio_translator', ''))
        
        # 配置文件目录 - 使用与ConfigService一致的路径
        if config_dir:
            self.config_dir = config_dir
        else:
            # 使用与ConfigService相同的配置目录计算方式
            # 简化路径计算，直接使用相对路径
            # 从当前文件所在目录开始向上找，直到找到src/config目录
            current_file = Path(__file__).resolve()
            project_root = current_file.parent
            
            # 向上寻找直到找到src目录
            while project_root.name != "src" and project_root != project_root.parent:
                project_root = project_root.parent
                
            # 项目级配置目录
            config_path = project_root / "config"
            
            if config_path.exists():
                self.config_dir = str(config_path)
                logger.info(f"使用项目级配置目录: {self.config_dir}")
            else:
                # 回退到包内配置目录
                self.config_dir = str(self.package_path / 'config' / 'strategies')
                logger.warning(f"项目级配置目录不存在，回退到包内配置: {self.config_dir}")
            
        # 插件目录
        if plugins_dir:
            self.plugins_dir = plugins_dir
        else:
            self.plugins_dir = str(self.package_path / 'plugins' / 'strategies')
            
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
            # 尝试从项目级配置目录加载
            project_config_file = os.path.join(self.config_dir, 'strategies.json')
            
            if os.path.exists(project_config_file):
                config_file = project_config_file
                logger.info(f"使用项目级策略配置文件: {config_file}")
            else:
                # 尝试查找包内策略配置
                package_config_dir = str(self.package_path / 'config' / 'strategies')
                package_config_file = os.path.join(package_config_dir, 'strategies.json')
                
                if os.path.exists(package_config_file):
                    config_file = package_config_file
                    logger.info(f"使用包内策略配置文件: {config_file}")
                else:
                    logger.warning(f"策略配置文件不存在: 项目级({project_config_file})或包内({package_config_file})")
                    return 0
            
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
                # 复制配置并添加必要的字段
                config_copy = dict(strategy_config)
                
                # 确保配置中包含策略名称
                if 'name' not in config_copy:
                    config_copy['name'] = strategy_name
                
                # 创建和注册策略实例
                if strategy_type in ['openai', 'anthropic', 'gemini', 'alibaba', 'zhipu', 'volc', 'deepseek']:
                    # 针对内置适配器类使用register方法
                    adapter_class = self._get_adapter_class(strategy_type)
                    if adapter_class:
                        adapter_instance = adapter_class(config_copy)
                        registered = self.registry.register(strategy_name, adapter_instance)
                        if registered:
                            self.loaded_strategies[strategy_name] = adapter_instance
                            loaded_count += 1
                            logger.info(f"已成功加载策略: {strategy_name} (类型: {strategy_type})")
                else:
                    logger.error(f"不支持的策略类型: {strategy_type}")
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
        
    def _get_adapter_class(self, adapter_type: str):
        """
        获取适配器类
        
        Args:
            adapter_type: 适配器类型（如openai, anthropic等）
            
        Returns:
            适配器类，如果找不到则返回None
        """
        # 转换格式，例如 "openai" -> "openai_adapter" 模块, "OpenAIAdapter" 类
        module_path = f"audio_translator.services.business.translation.strategies.adapters.{adapter_type}_adapter"
        
        # 支持两种类名格式：大写驼峰式如OpenAIAdapter和首字母大写如OpenaiAdapter
        class_names = [
            f"{adapter_type.upper()}Adapter",  # OpenAIAdapter
            f"{adapter_type.capitalize()}Adapter"  # OpenaiAdapter
        ]
        
        try:
            # 动态导入适配器模块
            module = importlib.import_module(module_path)
            
            # 尝试获取各种格式的适配器类
            for class_name in class_names:
                try:
                    adapter_class = getattr(module, class_name)
                    return adapter_class
                except AttributeError:
                    continue
                
            # 如果上面都没找到，尝试更智能的查找方式
            for attr_name in dir(module):
                if attr_name.lower() == f"{adapter_type.lower()}adapter":
                    return getattr(module, attr_name)
                    
            logger.error(f"在模块 {module_path} 中找不到适配器类 {adapter_type}Adapter")
            return None
            
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