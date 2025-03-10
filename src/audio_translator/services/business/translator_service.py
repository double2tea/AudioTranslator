"""
翻译服务模块

此模块提供了音效文件名翻译服务，负责实现音效文件名的翻译和处理功能。
TranslatorService 作为服务层组件，提供了单词翻译、文件名翻译、批量翻译等核心功能。
"""

import re
import hashlib
import logging
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Set
import requests
import os

from ..core.base_service import BaseService
from ..infrastructure.config_service import ConfigService
from ..api.model_service import ModelService
from .ucs.ucs_service import UCSService

# 设置日志记录器
logger = logging.getLogger(__name__)

class TranslatorService(BaseService):
    """
    翻译服务类
    
    负责音效文件名的翻译和处理，提供单词翻译、文件名翻译、批量翻译等功能。
    
    Attributes:
        config_service: 配置服务实例
        ucs_service: UCS服务实例
        service_config: 当前翻译服务配置
        translation_cache: 翻译缓存
        offline_mode: 是否处于离线模式
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化翻译服务
        
        Args:
            config: 服务配置
        """
        super().__init__("translator_service", config)
        
        # 依赖服务
        self.config_service = None
        self.ucs_service = None
        self.service_factory = None  # 将由ServiceFactory设置
        
        # 初始化服务配置，确保属性存在
        self.service_config = {
            "api_key": "demo_key",
            "api_url": "https://api.example.com/translate",
            "enabled": True,
            "model": "gpt-3.5-turbo",
            "type": "openai",
            "timeout": 30,
            "temperature": 0.3,
            "current_model": "gpt-3.5-turbo"
        }
        
        # 翻译缓存
        self.translation_cache = {}
        self.cache_file = None
        
        # 离线模式
        self.offline_mode = False
        
        # API配置
        self.api_key = None
        self.model = None
        self.timeout = 30
        self.temperature = 0.3
        
        # 提示词模板
        self.prompt_template = self._get_default_prompt()
        
        # 分类提示
        self.SOUND_TYPES = {
            'ambience', 'impact', 'foley', 'dialogue', 'voice', 'music', 'sfx', 
            'effect', 'footstep', 'weapon', 'explosion', 'ui', 'vehicle', 'animal'
        }
        
        self.VOICE_TYPES = {
            'male', 'female', 'child', 'old', 'young', 'human', 'creature', 'monster',
            'robot', 'mechanical', 'electronic', 'digital', 'synthetic'
        }
        
        # 常用的正则表达式模式
        self.CLEAN_PATTERN = re.compile(r'[^\w\s-]')
        self.SPACE_PATTERN = re.compile(r'[-\s]+')
        self.EXTENSION_PATTERN = re.compile(r'\.(wav|mpogg|aif|aiff)$', re.IGNORECASE)
        self.FORMAT_PATTERN = re.compile(r'_wav$|_mp3$|_ogg$|_aif$|_aiff$', re.IGNORECASE)

        # 评分规则常量
        self.SCORE_RULES = {
            'EXACT_CATEGORY_SUBCATEGORY': 110,      # Category + SubCategory 完全匹配（正确顺序）
            'EXACT_CATEGORY_SUBCATEGORY_REVERSE': 100,  # Category + SubCategory 完全匹配（反序）
            'EXACT_SUBCATEGORY_SYNONYM': 90,        # SubCategory + Synonym 完全匹配
            'EXACT_CATEGORY_SYNONYM': 60,           # Category + Synonym 完全匹配
            'PARTIAL_SUBCATEGORY': 40,              # SubCategory 部分匹配
            'PARTIAL_CATEGORY': 25,                 # Category 部分匹配
            'PARTIAL_SYNONYM': 30,                  # Synonym 部分匹配
            'CHINESE_MATCH': 15,                    # 中文匹配
            'POSITION_FIRST_WORD': 20,              # 首词匹配额外加分
            'POSITION_EXACT_ORDER': 10,             # 精确顺序匹配额外加分
            'ACTION_WORD_MATCH': 35,                # 动作词匹配
            'VOICE_TYPE_MATCH': 25,                 # 声音类型匹配
        }

        # 常用词列表
        self.COMMON_PREFIXES = ['the', 'a', 'an', 'of', 'in', 'on', 'at', 'to']
        self.REDUNDANT_WORDS = ['的', '音效', '声音', '声效', '一个', '这个', '那个', '有点', '有些', '非常', '比较']
        self.SPECIAL_ABBR = ['UI', 'FX', 'SFX', 'VOX']
        
        # 添加动作词和声音类型词列表
        self.ACTION_WORDS = {
            'grunt', 'groan', 'moan', 'laugh', 'scream', 'shout', 'cry', 'whisper',
            'walk', 'run', 'jump', 'hit', 'slam', 'crash', 'break', 'crack',
            'open', 'close', 'slide', 'turn', 'spin', 'roll', 'drop', 'fall'
        }
    
    def initialize(self) -> bool:
        """
        初始化翻译服务
        
        获取必要的依赖服务并加载配置。
        
        Returns:
            初始化是否成功
        """
        try:
            # 获取配置服务
            if not self.config_service:
                if self.service_factory:
                    self.config_service = self.service_factory.get_service('config_service')
                
                if not self.config_service:
                    logger.error("无法获取配置服务")
                    return False
            
            # 获取UCS服务
            if not self.ucs_service:
                if self.service_factory:
                    self.ucs_service = self.service_factory.get_service("ucs_service")
                    
                if not self.ucs_service:
                    logger.warning("无法获取UCS服务，部分功能可能不可用")
            
            # 加载服务配置
            loaded_config = self._get_service_config()
            
            # 如果有新的配置，更新 service_config 而不是替换它
            if loaded_config:
                # 更新现有配置而不是替换
                self.service_config.update(loaded_config)
                logger.debug("已更新翻译服务配置")
            
            # 加载缓存
            self._load_translation_cache()
            
            self.is_initialized = True
            logger.info("翻译服务初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"翻译服务初始化失败: {e}")
            return False
    
    def shutdown(self) -> bool:
        """
        关闭翻译服务
        
        保存缓存并清理资源。
        
        Returns:
            关闭是否成功
        """
        try:
            # 保存翻译缓存
            self._save_translation_cache()
            
            logger.info("翻译服务已关闭")
            return True
            
        except Exception as e:
            logger.error(f"翻译服务关闭失败: {e}")
            return False
    
    def set_offline_mode(self, enabled: bool = True) -> None:
        """
        设置离线模式
        
        Args:
            enabled: 是否启用离线模式
        """
        self.offline_mode = enabled
        logger.info(f"离线模式已{'启用' if enabled else '禁用'}")
    
    def _get_service_config(self) -> Dict[str, Any]:
        """
        获取当前翻译服务配置
        
        Returns:
            当前翻译服务配置
        """
        # 默认配置项
        default_config = {
            "api_key": "demo_key",
            "api_url": "https://api.example.com/translate",
            "enabled": True,
            "model": "gpt-3.5-turbo",
            "type": "openai",
            "timeout": 30,
            "temperature": 0.3,
            "current_model": "gpt-3.5-turbo"
        }
        
        # 如果配置服务不可用，使用默认配置
        if not self.config_service:
            logger.warning("配置服务不可用，使用默认翻译配置")
            return default_config
            
        # 尝试从配置服务获取翻译服务配置
        services = self.config_service.get("TRANSLATION_SERVICES", {})
        current_service = self.config_service.get("TRANSLATION_SERVICE", "")
        
        # 如果没有配置任何服务，使用默认配置
        if not services:
            # 尝试创建默认服务配置
            try:
                default_services = {
                    "openai": {
                        "api_key": os.environ.get("OPENAI_API_KEY", ""),
                        "api_url": "https://api.openai.com/v1/chat/completions",
                        "enabled": True,
                        "model": "gpt-3.5-turbo",
                        "type": "openai",
                        "timeout": 30,
                        "temperature": 0.3,
                        "current_model": "gpt-3.5-turbo"
                    },
                    "zhipu": {
                        "api_key": os.environ.get("ZHIPU_API_KEY", ""),
                        "api_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                        "enabled": True,
                        "model": "glm-4",
                        "type": "zhipu",
                        "timeout": 30,
                        "temperature": 0.3,
                        "current_model": "glm-4"
                    }
                }
                
                # 保存默认服务配置
                self.config_service.set("TRANSLATION_SERVICES", default_services)
                self.config_service.set("TRANSLATION_SERVICE", "zhipu")
                
                # 获取更新后的服务配置
                services = self.config_service.get("TRANSLATION_SERVICES", {})
                current_service = "zhipu"
                
                logger.info("已创建默认翻译服务配置")
            except Exception as e:
                logger.error(f"创建默认翻译服务配置失败: {e}")
        
        # 首先尝试使用当前选择的服务
        if current_service and current_service in services:
            config = services[current_service]
            if config.get("enabled", False) and config.get("api_key"):
                # 确保配置中包含 api_url
                if "api_url" not in config:
                    if config.get("type") == "openai":
                        config["api_url"] = "https://api.openai.com/v1/chat/completions"
                    elif config.get("type") == "zhipu":
                        config["api_url"] = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
                    elif config.get("type") == "anthropic":
                        config["api_url"] = "https://api.anthropic.com/v1/messages"
                    elif config.get("type") == "gemini":
                        config["api_url"] = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
                    elif config.get("type") == "alibaba":
                        config["api_url"] = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
                    else:
                        config["api_url"] = "https://api.example.com/translate"
                
                # 设置当前模型
                if "current_model" not in config:
                    config["current_model"] = config.get("model", "gpt-3.5-turbo")
                
                return config
        
        # 如果当前服务不可用，尝试其他已启用且配置了API密钥的服务
        for service_id, config in services.items():
            if config.get("enabled", False) and config.get("api_key"):
                # 确保配置中包含 api_url
                if "api_url" not in config:
                    if config.get("type") == "openai":
                        config["api_url"] = "https://api.openai.com/v1/chat/completions"
                    elif config.get("type") == "zhipu":
                        config["api_url"] = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
                    elif config.get("type") == "anthropic":
                        config["api_url"] = "https://api.anthropic.com/v1/messages"
                    elif config.get("type") == "gemini":
                        config["api_url"] = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
                    elif config.get("type") == "alibaba":
                        config["api_url"] = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
                    else:
                        config["api_url"] = "https://api.example.com/translate"
                
                # 设置当前模型
                if "current_model" not in config:
                    config["current_model"] = config.get("model", "gpt-3.5-turbo")
                
                # 更新当前服务
                self.config_service.set("TRANSLATION_SERVICE", service_id)
                logger.info(f"切换到可用的翻译服务: {service_id}")
                return config
        
        # 如果没有找到可用的服务，返回默认配置，但设置离线模式
        logger.warning("未找到可用的翻译服务，使用离线模式")
        self.offline_mode = True
        
        # 返回一个默认配置，以便服务可以初始化
        return default_config
    
    def _load_translation_cache(self) -> None:
        """加载翻译缓存"""
        # 这里可以从文件或数据库加载缓存
        # 暂时使用空字典作为缓存
        self.translation_cache = {}
    
    def _save_translation_cache(self) -> None:
        """保存翻译缓存"""
        # 这里可以将缓存保存到文件或数据库
        # 暂时不做任何操作
        pass
    
    def translate_filename(self, filename: str, file_path: str = None) -> Dict[str, str]:
        """
        翻译音效文件名
        
        Args:
            filename: 原始文件名
            file_path: 文件路径，可选
            
        Returns:
            包含翻译结果的字典，格式为:
            {
                'original_name': 原文件名,
                'translated_name': 翻译后的文件名,
                'english_name': 英文描述,
                'chinese_name': 中文描述,
                'category_id': 分类ID,
                'file_path': 文件路径
            }
        """
        try:
            # 检查缓存
            cache_key = f"{filename}_{file_path}" if file_path else filename
            if cache_key in self.translation_cache:
                return self.translation_cache[cache_key]
                
            # 如果处于离线模式，返回简单的转换结果（不调用API）
            if self.offline_mode:
                logger.info(f"离线模式翻译文件名: {filename}")
                
                # 1. 预处理文件名
                name = self._preprocess_filename(filename)
                
                # 2. 分析文件名部分
                parts = self._analyze_filename(name)
                
                # 构建离线结果
                cat_id = parts.get('main_category', 'SFX')
                
                # 使用文件名作为直接翻译
                result = {
                    'original_name': filename,
                    'translated_name': filename,  # 离线模式下不修改文件名
                    'english_name': name,
                    'chinese_name': '离线模式未翻译',
                    'category_id': cat_id,
                    'file_path': file_path,
                    'translation': '离线模式未翻译'
                }
                self.translation_cache[cache_key] = result
                return result
            
            # 正常在线翻译流程
            # 1. 预处理文件名
            name = self._preprocess_filename(filename)
            
            # 2. 分析文件名部分
            parts = self._analyze_filename(name)
            
            # 3. 使用 AI 一次性生成英文和中文描述
            descriptions = self._get_descriptions(name)
            if not descriptions:
                # 返回包含原始文件名的结果
                result = {
                    'original_name': filename,
                    'translated_name': filename,
                    'english_name': '',
                    'chinese_name': '翻译失败',
                    'category_id': 'SFXMisc',
                    'file_path': file_path,
                    'translation': '翻译失败'  # 添加 translation 键
                }
                self.translation_cache[cache_key] = result
                return result
                
            fx_name, translated = descriptions
            
            # 4. 格式化 FXname（处理驼峰式命名）
            fx_name_formatted = ''
            words = fx_name.split()
            for word in words:
                # 只保留英文字母
                word = re.sub(r'[^a-zA-Z]', '', word)
                if not word:
                    continue
                # 处理特殊缩写
                if word.upper() in self.SPECIAL_ABBR:
                    fx_name_formatted += word.upper()
                else:
                    fx_name_formatted += word.capitalize()
            
            # 5. 处理中文描述（去除标点和多余字符）
            zh_desc = re.sub(r'[^\u4e00-\u9fff]', '', translated)  # 只保留中文字符
            zh_desc = zh_desc[:9]  # 限制长度
            
            # 6. 构建最终结果
            cat_id = parts.get('main_category', 'SFX')
            
            # 使用UCS服务获取分类信息
            category_info = {}
            if self.ucs_service:
                category_info = self.ucs_service.get_category(cat_id) or {}
            
            if not category_info:
                category_info = {'subcategory_zh': '其他'}
            
            # 构建返回结果
            result = {
                'original_name': filename,
                'translated_name': f"{cat_id}_{zh_desc}_{fx_name_formatted}_{translated}_{parts.get('sub_category', 'None')}",
                'english_name': fx_name,
                'chinese_name': translated,
                'category_id': cat_id,
                'file_path': file_path,
                'translation': translated  # 添加 translation 键
            }
            
            # 保存到缓存
            self.translation_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"翻译文件名失败: {e}")
            # 返回包含原始文件名的结果
            result = {
                'original_name': filename,
                'translated_name': filename,
                'english_name': '',
                'chinese_name': '翻译失败',
                'category_id': 'SFXMisc',
                'file_path': file_path,
                'translation': '翻译失败'  # 添加 translation 键
            }
            return result
    
    def _preprocess_filename(self, filename: str) -> str:
        """
        预处理文件名
        
        Args:
            filename: 原始文件名
            
        Returns:
            处理后的文件名
        """
        # 移除扩展名
        name = Path(filename).stem
        
        # 清理特殊字符
        name = re.sub(r'[^\w\s-]', '', name)
        
        # 标准化分隔符
        name = re.sub(r'[-\s]+', '_', name)
        
        return name.lower()
    
    def _analyze_filename(self, name: str) -> Dict[str, str]:
        """
        分析文件名各个部分
        
        Args:
            name: 预处理后的文件名
            
        Returns:
            文件名各部分信息的字典
        """
        parts = name.split('_')
        
        # 提取序号
        number = next((p for p in parts if p.isdigit()), None)
        number = f"{int(number):03d}" if number else None
        
        # 移除序号
        parts = [p for p in parts if not p.isdigit()]
        
        # 智能匹配主类别
        main_category = self._guess_main_category(parts)
        
        return {
            'parts': parts,
            'number': number,
            'main_category': main_category
        }

    def _guess_main_category(self, parts: list) -> str:
        """
        智能猜测主类别
        
        Args:
            parts: 文件名各部分
            
        Returns:
            最匹配的分类ID
        """
        # 这里的实现依赖于UCSService
        # 如果UCSService可用，则使用它进行分类匹配
        if self.ucs_service:
            return self.ucs_service.guess_category(' '.join(parts))
        
        # 如果UCSService不可用，返回默认分类
        return 'SFXMisc'
    
    def _get_descriptions(self, text: str) -> Optional[Tuple[str, str]]:
        """
        获取文本的英文和中文描述
        
        Args:
            text: 原始文本
            
        Returns:
            (英文描述, 中文描述)元组，如果失败则返回None
        """
        # 如果处于离线模式，使用基本翻译
        if self.offline_mode:
            return (text, "未翻译")
        
        prompt = self._get_current_prompt()
        
        # 使用API进行翻译
        result = self._translate_with_retries(text, prompt)
        if not result:
            return None
        
        try:
            # 如果结果是简单的单行文本（可能是测试环境中的模拟结果）
            if '\n' not in result and len(result) < 10:
                return (text, result)
                
            lines = result.strip().split('\n')
            if len(lines) < 2:
                # 如果返回的不是双行格式，尝试解析单行
                return (text, self._clean_translation(result))
            
            # 提取英文描述
            en_line = lines[0].replace('English:', '').replace('1.', '').strip()
            # 移除所有括号、标点等，只保留第一部分
            en_desc = re.sub(r'[\[\](),.]', '', en_line).split()[0].strip()
            
            # 提取中文描述
            zh_line = lines[1].replace('Chinese:', '').replace('2.', '').strip()
            # 移除所有括号、标点等，只保留中文字符
            zh_desc = ''.join(char for char in zh_line if '\u4e00' <= char <= '\u9fff')
            
            # 处理英文描述为驼峰式
            en_words = en_desc.split('_')  # 处理可能的下划线分隔
            fx_name = ''
            for word in en_words:
                word = re.sub(r'[^a-zA-Z]', '', word)  # 只保留英文字母
                if word:
                    if word.upper() in self.SPECIAL_ABBR:
                        fx_name += word.upper()
                    else:
                        fx_name += word.capitalize()
            
            # 限制中文描述长度
            zh_desc = zh_desc[:9]
            
            return (fx_name, zh_desc)
        except Exception as e:
            logger.error(f"解析翻译结果失败: {e}")
            return None
    
    def _translate_with_retries(self, text: str, prompt: str = None, max_retries: int = 3) -> Optional[str]:
        """
        带重试机制的翻译
        
        Args:
            text: 要翻译的文本
            prompt: 提示词
            max_retries: 最大重试次数
            
        Returns:
            翻译结果，如果失败则返回原文本
        """
        # 检查离线模式
        if self.offline_mode:
            logger.info(f"离线模式，跳过API翻译: {text}")
            # 在离线模式下，尝试返回一个基本的离线翻译（如果有的话）
            # 这里可以实现简单的离线翻译逻辑，如使用本地字典等
            # 暂时返回原文本作为"翻译结果"
            return text
            
        # 检查翻译缓存
        cache_key = f"{text}_{prompt or ''}"
        if cache_key in self.translation_cache:
            logger.debug(f"使用缓存翻译: {text}")
            return self.translation_cache[cache_key]
        
        # 检查UCS服务中是否有现成的翻译
        if self.ucs_service:
            ucs_translation = self.ucs_service.get_translation(text)
            if ucs_translation:
                logger.debug(f"使用UCS服务中的翻译: {text} -> {ucs_translation}")
                self.translation_cache[cache_key] = ucs_translation
                return ucs_translation
        
        # 尝试通过API翻译
        for attempt in range(max_retries):
            try:
                result = self._translate_with_api(text, prompt)
                if result:
                    # 保存到缓存
                    self.translation_cache[cache_key] = result
                    return result
            except Exception as e:
                logger.warning(f"翻译尝试 {attempt + 1} 失败: {e}")
                if attempt < max_retries - 1:
                    # 重试前等待一段时间
                    time.sleep(1 * (attempt + 1))
                    continue
                break
        
        # 如果所有尝试都失败，返回原文本
        logger.warning(f"翻译失败后返回原文本: {text}")
        
        # 所有API尝试失败后临时设置为离线模式，避免后续请求继续失败
        if not self.offline_mode:
            self.offline_mode = True
            logger.warning("翻译多次失败，已临时切换到离线模式")
            
        return text
    
    def _translate_with_api(self, text: str, prompt: str = None) -> Optional[str]:
        """
        使用API进行翻译
        
        Args:
            text: 要翻译的文本
            prompt: 提示词
            
        Returns:
            翻译结果，如果失败则返回None
        """
        # 检查离线模式 - 在离线模式下直接返回原文本
        if self.offline_mode:
            logger.debug(f"处于离线模式，跳过API请求: {text}")
            return text
            
        # 确保service_config存在且包含必要的属性
        if not hasattr(self, 'service_config') or not self.service_config:
            logger.error("未配置翻译服务")
            return text  # 在配置缺失时，也返回原文而不是None
        
        # 确保 service_config 包含必要的属性
        if 'api_url' not in self.service_config or 'api_key' not in self.service_config:
            logger.error("翻译服务配置不完整，缺少 api_url 或 api_key")
            self.offline_mode = True  # 配置不完整时设置为离线模式
            return text  # 返回原文
        
        try:
            # 准备请求数据
            data = self._format_request_data(text, prompt)
            
            # 发送请求
            logger.debug(f"正在发送API请求到: {self.service_config.get('api_url')}")
            response = requests.post(
                self.service_config.get("api_url", "https://api.example.com/translate"),
                headers={
                    "Authorization": f"Bearer {self.service_config.get('api_key', '')}",
                    "Content-Type": "application/json"
                },
                json=data,
                timeout=self.service_config.get("timeout", 10)
            )
            
            if response.status_code != 200:
                logger.error(f"API请求失败，状态码: {response.status_code}")
                raise ValueError(f"翻译请求失败: {response.text}")
            
            # 提取翻译结果
            result = response.json()
            content = self._extract_response_content(result)
            
            if not content:
                raise ValueError("无法从响应中提取翻译结果")
            
            logger.debug(f"API请求成功，获取到翻译结果")
            return content
            
        except Exception as e:
            logger.error(f"API 翻译失败: {e}")
            # 在API请求失败时，暂时设置为离线模式
            self.offline_mode = True
            return text  # 返回原文
    
    def _format_request_data(self, text: str, prompt: str = None) -> dict:
        """
        格式化请求数据
        
        Args:
            text: 要翻译的文本
            prompt: 提示词
            
        Returns:
            格式化后的请求数据
        """
        if not prompt:
            prompt = self._get_current_prompt()
        prompt = prompt.format(text=text)
        
        # 确保 service_config 存在
        if not hasattr(self, 'service_config') or not self.service_config:
            # 使用默认格式
            return {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text}
                ]
            }
        
        # 使用服务配置中的请求格式
        request_format = self.service_config.get("request_format", {
            "model": "{model}",
            "messages": [
                {"role": "system", "content": "{prompt}"},
                {"role": "user", "content": "{text}"}
            ]
        })
        
        # 替换模板中的变量
        try:
            return json.loads(json.dumps(request_format).format(
                model=self.service_config.get("current_model", "gpt-3.5-turbo"),
                prompt=prompt,
                text=text
            ))
        except Exception as e:
            logger.error(f"格式化请求数据失败: {e}")
            # 返回默认格式
            return {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text}
                ]
            }
    
    def _extract_response_content(self, result: dict) -> Optional[str]:
        """
        从响应中提取内容
        
        Args:
            result: API响应结果
            
        Returns:
            提取的内容，如果失败则返回None
        """
        try:
            # 1. 标准 OpenAI 格式
            if 'choices' in result and result['choices']:
                choice = result['choices'][0]
                if 'message' in choice and isinstance(choice['message'], dict):
                    return choice['message'].get('content')
                elif 'text' in choice:
                    return choice['text']
                elif 'delta' in choice:
                    return choice['delta'].get('content')
            
            # 2. 百炼 API 格式
            if 'output' in result:
                return result['output'].get('text', '')
            elif 'message' in result:
                return result['message'].get('content', '')
            
            # 3. 其他常见格式
            if 'response' in result:
                return result['response']
            elif 'translation' in result:
                return result['translation']
            
            return None
        except Exception as e:
            logger.error(f"提取响应内容失败: {e}")
            return None
    
    def _get_current_prompt(self) -> str:
        """
        获取当前使用的提示词
        
        Returns:
            当前提示词
        """
        if not self.service_config:
            # 如果没有服务配置，返回默认提示词
            return """As a sound effect expert, provide both English and Chinese descriptions for this sound effect.
Keep English under 25 characters and Chinese between 3-9 characters.

Focus on describing:
1. Sound source (what makes the sound)
2. Action/state (what's happening)
3. Quality/characteristics (how it sounds)

Examples:
- human_male_ah_question -> (male vocal question, 男声困惑询问)
- error_tonal -> (error alert tone, 电子错误提示)
- click_blip -> (sharp click blip, 清脆按键声)
- cloth_nylon_movement -> (nylon cloth movement, 尼龙布料摩擦)
- metal_door_slam -> (heavy metal door slam, 金属重门砰响)
- footstep_concrete -> (footsteps on concrete, 混凝土脚步)

Format: Return exactly two lines:
1. English: [english description]
2. Chinese: [chinese description]

Describe: {text}"""
            
        # 从服务配置中获取提示词
        prompts = self.service_config.get('prompts', {})
        # 始终使用双语音效描述
        return prompts.get('双语音效描述', self.config_service.get_bilingual_description_prompt())
    
    def _clean_translation(self, translated: str) -> str:
        """
        清理翻译结果
        
        Args:
            translated: 原始翻译结果
            
        Returns:
            清理后的翻译结果
        """
        # 移除空白字符
        translated = translated.strip()
        
        # 移除代码块标记
        translated = re.sub(r'```.*?```', '', translated, flags=re.DOTALL)
        
        # 移除括号内容
        translated = re.sub(r'[（(].*?[)）]', '', translated)
        
        # 移除多余的标点和解释
        translated = re.sub(r'[,，;；:：].*', '', translated)
        
        # 移除多余的空白字符
        translated = re.sub(r'\s+', '', translated)
        
        # 移除箭头和引号
        translated = re.sub(r'[""\'\'><→]', '', translated)
        
        # 移除英文注释
        translated = re.sub(r'//.*$', '', translated, flags=re.MULTILINE)
        
        # 移除文件扩展名和格式标记
        translated = re.sub(r'\.(wav|mp3|ogg|aif|aiff)$', '', translated, flags=re.IGNORECASE)
        translated = re.sub(r'_wav$|_mp3$|_ogg$|_aif$|_aiff$', '', translated, flags=re.IGNORECASE)
        
        # 移除常见的前缀
        prefixes = [
            "翻译:", "翻译结果:", "中文:", "结果:", "译文:", 
            "音效:", "声音:", "这是", "这个是", "请提供",
            "具体", "英文", "需要", "警告", "完整"
        ]
        for prefix in prefixes:
            if translated.startswith(prefix):
                translated = translated[len(prefix):].strip()
        
        # 移除常见的修饰词
        modifiers = [
            "的", "地", "得", "着", "了", "过", "很", "非常", "比较", 
            "有点", "一些", "一个", "具体", "英文", "需要", "警告", "完整"
        ]
        for modifier in modifiers:
            translated = translated.replace(modifier, '')
        
        # 移除声音相关的后缀词（仅当不是单独使用时）
        suffixes = ["声", "音效", "音", "声效", "效果", "声音", "元素"]
        for suffix in suffixes:
            if translated.endswith(suffix) and len(translated) > len(suffix):
                translated = translated[:-len(suffix)].strip()
        
        # 提取所有中文词
        words = re.findall(r'[\u4e00-\u9fff]+', translated)
        
        # 移除完全重复的词
        unique_words = []
        seen_words = set()
        for word in words:
            if word not in seen_words and len(word.strip()) > 0:
                unique_words.append(word)
                seen_words.add(word)
        
        # 限制长度
        result = ''.join(unique_words)
        if len(result) > 12:
            result = result[:12]
        
        # 如果结果为空，返回原始输入的前12个字符
        if not result:
            result = translated[:12]
        
        return result.strip()
    
    def batch_translate_filenames(self, filenames: List[str], batch_size: int = 10) -> List[str]:
        """
        批量翻译文件名
        
        Args:
            filenames: 文件名列表
            batch_size: 批处理大小
            
        Returns:
            翻译后的文件名列表
        """
        results = []
        total_files = len(filenames)
        
        # 按批次处理文件
        for i in range(0, total_files, batch_size):
            batch = filenames[i:i + batch_size]
            batch_results = []
            
            # 处理每个文件
            for filename in batch:
                try:
                    # 检查缓存
                    if filename in self.translation_cache:
                        batch_results.append(self.translation_cache[filename])
                        continue
                    
                    # 执行翻译
                    translated = self.translate_filename(filename)
                    batch_results.append(translated)
                    
                    # 更新缓存
                    self.translation_cache[filename] = translated
                    
                except Exception as e:
                    logger.error(f"批量翻译文件 {filename} 失败: {e}")
                    batch_results.append(filename)  # 使用原始文件名作为回退
            
            # 合并结果
            results.extend(batch_results)
            
            # 记录进度
            logger.info(f"批量翻译进度: {min(100, (i + len(batch)) / total_files * 100):.1f}% ({i + len(batch)}/{total_files})")
        
        return results
    
    def update_translation_cache(self, source: str, target: str) -> None:
        """
        更新翻译缓存
        
        Args:
            source: 源文本
            target: 目标文本
        """
        self.translation_cache[source] = target
        # 如果UCSService可用，同时更新UCS翻译
        if self.ucs_service:
            self.ucs_service.add_translation(source, target)
    
    def clear_cache(self) -> None:
        """清除翻译缓存"""
        self.translation_cache.clear()
        logger.info("翻译缓存已清除")
    
    def _get_default_prompt(self) -> str:
        """
        获取默认提示词模板
        
        Returns:
            默认提示词模板
        """
        return """
你是一个专业的音效文件命名翻译工具。请将给定的英文音效文件名翻译成简体中文。
你的任务是：
1. 准确理解音效文件名中描述的声音内容
2. 将描述翻译成专业、简洁的中文表达
3. 保持术语的专业性和一致性

规则：
- 保持翻译的简洁性，不要有多余解释
- 不要加入原文中不存在的内容
- 不要使用句号等标点符号
- 翻译风格要专业，适合音频工作者使用
- 当遇到特定术语时，使用对应的专业中文术语
- 只输出翻译结果，不要添加任何额外文字

示例：
"Door_wooden_open_creak.wav" -> "木门_打开_吱呀声"
"Footsteps_male_concrete_walk_slow.wav" -> "脚步声_男性_混凝土_行走_缓慢"
"UI_button_click_digital.wav" -> "UI_按钮_点击_数字化"
"Ambience_forest_night_crickets.wav" -> "环境_森林_夜晚_蟋蟀"
"Impact_metal_hit_resonant.wav" -> "撞击_金属_敲击_共振"
"Voice_female_scream_fear.wav" -> "人声_女性_尖叫_恐惧"

请保持音效名称的结构特点，使用下划线分隔不同的描述元素。
""" 