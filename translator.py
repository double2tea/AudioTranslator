import os
import re
import hashlib
import logging
import requests
import sys
import time
import json
import csv
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from ucs_parser import UCSParser

class Translator:
    """音效文件名翻译器"""
    
    def __init__(self, config):
        """初始化 GUI 应用"""
        self.config = config
        
        # 初始化logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # 添加处理器到logger
        self.logger.addHandler(console_handler)
        
        # 初始化其他属性
        self.service_config = self._get_service_config()
        self.categories = self._load_categories()  # 加载分类信息
        
        # 常用的正则表达式模式
        self.CLEAN_PATTERN = re.compile(r'[^\w\s-]')
        self.SPACE_PATTERN = re.compile(r'[-\s]+')
        self.EXTENSION_PATTERN = re.compile(r'\.(wav|mpogg|aif|aiff)$', re.IGNORECASE)
        self.FORMAT_PATTERN = re.compile(r'_wav$|_mp3$|_ogg$|_aif$|_aiff$', re.IGNORECASE)

        # 评分规则常量
        self.SCORE_RULES = {
            'EXACT_CATEGORY_SUBCATEGORY': 110,      # Category + SubCategory 完全匹配（正确顺序）
            'EXACT_CATEGORY_SUBCATEGORY_REVERSE': 100,  # Category + SubCategory 完全匹配（反序）
            'EXACT_SUBCATEGORY_SYNONYM': 90,        # SubCategory + Synonym 完全匹配 (提高权重)
            'EXACT_CATEGORY_SYNONYM': 60,           # Category + Synonym 完全匹配
            'PARTIAL_SUBCATEGORY': 40,              # SubCategory 部分匹配 (提高权重)
            'PARTIAL_CATEGORY': 25,                 # Category 部分匹配
            'PARTIAL_SYNONYM': 30,                  # Synonym 部分匹配 (提高权重)
            'CHINESE_MATCH': 15,                    # 中文匹配
            'POSITION_FIRST_WORD': 20,              # 首词匹配额外加分 (提高权重)
            'POSITION_EXACT_ORDER': 10,             # 精确顺序匹配额外加分 (提高权重)
            'ACTION_WORD_MATCH': 35,                # 动作词匹配 (新增)
            'VOICE_TYPE_MATCH': 25,                 # 声音类型匹配 (新增)
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

        self.VOICE_TYPES = {
            'male', 'female', 'child', 'old', 'young', 'human', 'creature', 'monster',
            'robot', 'mechanical', 'electronic', 'digital', 'synthetic'
        }
        
    def _load_categories(self) -> Dict[str, Dict]:
        """从 _categorylist.csv 加载分类数据"""
        categories = {}
        csv_path = Path(__file__).parent / "data" / "_categorylist.csv"
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cat_id = row['CatID']  # 使用预定义的CatID
                    categories[cat_id] = {
                        'name': row['Category'],
                        'name_zh': row['Category_zh'],
                        'subcategory': row['SubCategory'],
                        'subcategory_zh': row['SubCategory_zh'],
                        'CatID': cat_id,  # 存储完整的CatID
                        'synonyms': [s.strip() for s in str(row['Synonyms - Comma Separated']).split(',') if s.strip()],
                        'synonyms_zh': [s.strip() for s in str(row['Synonyms_zh']).split('、') if s.strip()],
                        'keywords': [s.strip() for s in str(row.get('Keywords', '')).split(',') if s.strip()],  # 关键词匹配
                        'parent_category': row.get('ParentCategory', ''),  # 父分类
                        'description': row.get('Explanations', '')  # 分类描述
                    }
                self.logger.info(f"成功加载 {len(categories)} 个分类")
            return categories
        except Exception as e:
            self.logger.error(f"加载分类数据失败: {str(e)}")
            return {}
    
    def set_offline_mode(self, enabled: bool = True):
        """设置离线模式"""
        self.offline_mode = enabled
    
    def _get_service_config(self) -> Dict[str, Any]:
        """获取当前翻译服务配置"""
        services = self.config.get("TRANSLATION_SERVICES", {})
        current_service = self.config.get("TRANSLATION_SERVICE")
        
        # 首先尝试使用当前选择的服务
        if current_service in services:
            config = services[current_service]
            if config.get("enabled", False) and config.get("api_key"):
                return config
        
        # 如果当前服务不可用，尝试其他已启用且配置了API密钥的服务
        for service_id, config in services.items():
            if config.get("enabled", False) and config.get("api_key"):
                # 更新当前服务
                self.config.set("TRANSLATION_SERVICE", service_id)
                logging.info(f"切换到可用的翻译服务: {service_id}")
                return config
        
        # 如果没有找到可用的服务，返回 None
        logging.warning("未找到可用的翻译服务")
        return None
    
    def load_translations(self):
        """已废弃的方法，保留空实现以保持兼容性"""
        pass
    
    def translate_filename(self, filename: str) -> str:
        """翻译音效文件名"""
        try:
            # 1. 预处理文件名
            name = self._preprocess_filename(filename)
            
            # 2. 分析文件名部分
            parts = self._analyze_filename(name)
            
            # 3. 使用 AI 一次性生成英文和中文描述
            descriptions = self._get_descriptions(name)
            if not descriptions:
                return filename
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
            category_info = self.categories.get(cat_id, {})
            result = f"{cat_id}_{category_info.get('subcategory_zh', '其他')}_{fx_name_formatted}_{zh_desc}_{parts.get('number', '001')}"
            
            return result
            
        except Exception as e:
            logging.error(f"翻译文件名失败: {str(e)}")
            return filename
    
    def _preprocess_filename(self, filename: str) -> str:
        """预处理文件名"""
        # 移除扩展名
        name = Path(filename).stem
        
        # 清理特殊字符
        name = re.sub(r'[^\w\s-]', '', name)
        
        # 标准化分隔符
        name = re.sub(r'[-\s]+', '_', name)
        
        return name.lower()
    
    def _analyze_filename(self, name: str) -> Dict[str, str]:
        """分析文件名各个部分"""
        parts = name.split('_')
        
        # 提取序号
        number = next((p for p in parts if p.isdigit()), None)
        number = f"{int(number):03d}" if number else None  # 改为 None 而不是默认值
        
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
        """智能猜测主类别，返回最匹配的 CatID"""
        try:
            # 输入验证
            if not parts:
                return 'SFXMisc'
            
            # 预处理文本
            text = ' '.join(parts).lower()
            if not text.strip():
                return 'SFXMisc'
            
            # 初始化匹配结果
            matches = []
            
            # 对每个分类进行评分
            for cat_id, info in self.categories.items():
                score = 0
                match_details = []
                
                # 获取分类信息
                category = info.get('name', '').lower()
                subcategory = info.get('subcategory', '').lower()
                synonyms = [syn.lower() for syn in info.get('synonyms', [])]
                synonyms_zh = info.get('synonyms_zh', [])
                
                # 1. Category + SubCategory 同时匹配
                if category in text and subcategory in text:
                    cat_pos = text.find(category)
                    sub_pos = text.find(subcategory)
                    if cat_pos < sub_pos:
                        score = self.SCORE_RULES['EXACT_CATEGORY_SUBCATEGORY']
                    else:
                        score = self.SCORE_RULES['EXACT_CATEGORY_SUBCATEGORY_REVERSE']
                
                # 2. SubCategory + Synonyms 完全匹配
                elif subcategory in text and any(syn in text for syn in synonyms):
                    score = self.SCORE_RULES['EXACT_SUBCATEGORY_SYNONYM']
                
                # 3. Category + Synonyms 匹配
                elif category in text and any(syn in text for syn in synonyms):
                    score = self.SCORE_RULES['EXACT_CATEGORY_SYNONYM']
                
                # 4. 单独匹配规则
                else:
                    if subcategory in text:
                        score += self.SCORE_RULES['PARTIAL_SUBCATEGORY']
                    if category in text:
                        score += self.SCORE_RULES['PARTIAL_CATEGORY']
                    for syn in synonyms:
                        if syn in text:
                            score += self.SCORE_RULES['PARTIAL_SYNONYM']
                    for syn_zh in synonyms_zh:
                        if syn_zh in text:
                            score += self.SCORE_RULES['CHINESE_MATCH']
                
                # 额外的精确匹配加分
                parts_set = set(parts)
                if subcategory in parts_set:
                    score += self.SCORE_RULES['POSITION_FIRST_WORD']
                if category in parts_set:
                    score += self.SCORE_RULES['POSITION_EXACT_ORDER']
                
                # 如果有匹配，记录结果
                if score > 0:
                    matches.append({
                        'cat_id': cat_id,
                        'score': score,
                        'info': info
                    })
            
            # 按分数排序
            matches.sort(key=lambda x: x['score'], reverse=True)
            
            # 返回最佳匹配或默认分类
            return matches[0]['cat_id'] if matches else 'SFXMisc'
            
        except Exception as e:
            return 'SFXMisc'

    def _resolve_multiple_matches(self, matches):
        """解决多个相同分数的匹配
        
        优先规则：
        1. 优先选择子分类更具体的（SubCategory 长度更长的）
        2. 如果子分类长度相同，选择 Category 更具体的
        3. 如果还是相同，选择 CatID 字母序靠前的
        """
        if not matches:
            return 'SFXMisc'
        
        # 按子分类长度排序
        matches.sort(key=lambda x: len(x['info'].get('subcategory', '')), reverse=True)
        
        # 获取最长子分类长度
        max_sub_len = len(matches[0]['info'].get('subcategory', ''))
        
        # 筛选出子分类长度相同的
        same_sub_len = [m for m in matches if len(m['info'].get('subcategory', '')) == max_sub_len]
        
        if len(same_sub_len) == 1:
            return same_sub_len[0]['cat_id']
        
        # 如果还有多个，按分类名长度排序
        same_sub_len.sort(key=lambda x: len(x['info'].get('name', '')), reverse=True)
        
        # 返回第一个匹配（如果分类名长度也相同，则按字母序）
        return same_sub_len[0]['cat_id']
    
    def _translate_parts_with_fallback(self, parts_info: Dict[str, Any]) -> Dict[str, str]:
        """带容错和降级机制的部分翻译
        
        Args:
            parts_info: 文件名各部分信息
            
        Returns:
            Dict[str, str]: 翻译后的各部分信息，如果翻译失败返回None
        """
        try:
            # 获取主类别信息
            main_cat = parts_info['main_category']
            category_info = self.categories.get(main_cat, {})
            
            # 使用 _batch_translate_words 进行批量翻译
            translations = self._batch_translate_words(parts_info['parts'])
            
            # 如果翻译失败
            if not translations:
                return None
            
            # 应用翻译结果
            translated_parts = self._apply_translations(parts_info, translations)
            
            # 获取分类信息
            mid_category = category_info.get('name_zh', '特效')
            sub_category = category_info.get('subcategory_zh', '其他')
            
            # 更新分类信息
            translated_parts.update({
                'mid_category': mid_category,
                'sub_category': sub_category,
                'main_category': main_cat
            })
            
            return translated_parts
            
        except Exception as e:
            self.logger.error(f"翻译部分失败: {str(e)}")
            return None

    def _format_request_data(self, text: str, prompt: str = None) -> dict:
        """统一格式化请求数据"""
        service = self.service_config
        if not service:
            raise Exception("未配置翻译服务")
        
        if not prompt:
            prompt = self._get_current_prompt()
        prompt = prompt.format(text=text)
        
        # 使用服务配置中的请求格式
        request_format = service.get("request_format", {
            "model": "{model}",
            "messages": [
                {"role": "system", "content": "{prompt}"},
                {"role": "user", "content": "{text}"}
            ]
        })
        
        # 替换模板中的变量
        return json.loads(json.dumps(request_format).format(
            model=service.get("current_model", "glm-4"),
            prompt=prompt,
            text=text
        ))

    def _translate_with_retries(self, text: str, prompt: str = None, max_retries: int = 3) -> Optional[str]:
        """带重试机制的翻译"""
        try:
            service = self.service_config
            if not service:
                raise Exception("未配置翻译服务")
            
            # 使用统一的请求格式化方法
            data = self._format_request_data(text, prompt)
            
            # 发送请求
            response = requests.post(
                service["api_url"],
                headers={
                    "Authorization": f"Bearer {service['api_key']}",
                    "Content-Type": "application/json"
                },
                json=data,
                timeout=10
            )
            
            if response.status_code != 200:
                result = response.json() if response.text else {"error": {"message": "无响应内容"}}
                
                # 特殊错误处理
                if service_id and "openrouter" in service_id and response.status_code == 402:
                    error_msg = result.get("error", {}).get("message", "")
                    if "credits" in error_msg.lower():
                        raise Exception("OpenRouter 额度不足，请充值或更换其他服务")
                
                # 其他错误
                error_msg = result.get("error", {}).get("message", response.text)
                raise Exception(f"API 请求失败 ({response.status_code}): {error_msg}")
            
            result = response.json()
            
            # 提取响应内容
            content = self._extract_response_content(result)
            if not content:
                raise Exception("无法从响应中提取翻译结果")
            
            return content.strip()
            
        except Exception as e:
            logging.error(f"翻译尝试失败: {str(e)}")
            return None
    
    def _switch_to_next_service(self):
        """切换到下一个可用的翻译服务"""
        try:
            services = self.config.get("TRANSLATION_SERVICES", {})
            current_service = self.config.get("TRANSLATION_SERVICE")
            
            # 获取所有启用的服务
            available_services = [
                service_id for service_id, service in services.items()
                if service.get("enabled", False) and service.get("api_key")
            ]
            
            if not available_services:
                raise ValueError("没有可用的翻译服务")
            
            # 找到当前服务的索引
            current_index = available_services.index(current_service) if current_service in available_services else -1
            
            # 切换到下一个服务
            next_index = (current_index + 1) % len(available_services)
            next_service = available_services[next_index]
            
            # 更新配置
            self.config.set("TRANSLATION_SERVICE", next_service)
            self.service_config = self._get_service_config()
            
            logging.info(f"切换到翻译服务: {next_service}")
            
        except Exception as e:
            logging.error(f"切换翻译服务失败: {e}")
            self.offline_mode = True  # 切换失败时进入离线模式
    
    def _basic_translation(self, text: str) -> str:
        """基本的文本处理，用于所有其他方法失败时
        
        Args:
            text: 要处理的文本
            
        Returns:
            str: 处理后的文本
        """
        # 1. 移除特殊字符
        text = re.sub(r'[^\w\s-]', '', text)
        
        # 2. 转换为小写
        text = text.lower()
        
        # 3. 替换连字符和空格
        text = re.sub(r'[-\s]+', '_', text)
        
        # 4. 处理常见的词缀
        common_prefixes = ['the_', 'a_', 'an_']
        for prefix in common_prefixes:
            if text.startswith(prefix):
                text = text[len(prefix):]
        
        common_suffixes = ['_sound', '_effect', '_sfx']
        for suffix in common_suffixes:
            if text.endswith(suffix):
                text = text[:-len(suffix)]
        
        return text
    
    def _optimize_translations(self, translations: List[str], category_info: Dict) -> List[str]:
        """优化翻译结果列表
        
        直接返回 AI 翻译结果，仅做基本清理：
        1. 移除空字符串
        2. 移除重复内容
        3. 限制最大长度为9个字
        """
        if not translations:
            return [category_info.get('subcategory_zh', '其他')]
        
        # 基本清理
        translations = [t.strip() for t in translations if t and t.strip()]
        
        # 如果没有有效翻译，使用分类信息
        if not translations:
            return [category_info.get('subcategory_zh', '其他')]
        
        # 取第一个翻译结果，限制长度
        result = translations[0][:9]
        
        return [result]
    
    def _join_translations(self, translations: List[str]) -> str:
        """连接翻译结果"""
        if not translations:
            return ""
        
        # 直接连接并限制总长度为12个字符
        result = "".join(translations)
        return result[:12] if len(result) > 12 else result
    
    def _translate_with_ai(self, text: str, max_retries=3, retry_delay=1) -> Optional[str]:
        """使用AI服务翻译文本"""
        try:
            if not self.service_config:
                logging.error("未配置翻译服务")
                return None
            
            for attempt in range(max_retries):
                try:
                    # 准备翻译请求
                    data = {
                        "model": self.service_config.get("current_model", "glm-4"),
                        "messages": [
                            {
                                "role": "system",
                                "content": self._get_current_prompt()
                            },
                            {
                                "role": "user",
                                "content": text
                            }
                        ],
                        "temperature": 0.5,
                        "top_p": 0.9,
                        "max_tokens": 50
                    }
                
                    # 发送请求
                    response = requests.post(
                        self.service_config["api_url"],
                        headers={
                            "Authorization": f"Bearer {self.service_config['api_key']}",
                            "Content-Type": "application/json"
                        },
                        json=data,
                        timeout=10
                    )
                
                    if response.status_code != 200:
                        raise ValueError(f"翻译请求失败: {response.text}")
                    
                    # 提取翻译结果
                    result = response.json()
                    if not result:
                        raise ValueError("空响应")
                    
                    # 尝试从不同的响应格式中提取结果
                    translated = None
                    if isinstance(result, dict):
                        # 检查常见的响应格式
                        if 'choices' in result and isinstance(result['choices'], list) and result['choices']:
                            choice = result['choices'][0]
                            if isinstance(choice, dict):
                                if 'message' in choice and isinstance(choice['message'], dict):
                                    translated = choice['message'].get('content')
                                elif 'text' in choice:
                                    translated = choice['text']
                        elif 'response' in result:
                            translated = result['response']
                        elif 'translation' in result:
                            translated = result['translation']
                        elif 'output' in result:
                            translated = result['output']
                    
                    if not translated:
                        raise ValueError(f"无法从响应中提取翻译结果: {result}")
                    
                    # 清理结果
                    translated = self._clean_translation(translated)
                    if not translated:
                        raise ValueError("清理后的翻译结果为空")
                    
                    return translated
                    
                except Exception as e:
                    logging.error(f"翻译尝试 {attempt + 1} 失败: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
            
            return None
        except Exception as e:
            logging.error(f"翻译尝试失败: {str(e)}")
            return None
    
    def _format_result(self, parts: Dict[str, str]) -> str:
        """格式化翻译结果为 UCS 标准的双语结构
        
        格式: CatID_分类子类_FXName_中文描述_序号
        """
        try:
            # 获取 CatID
            cat_id = parts.get('main_category', 'SFX')
            category_info = self.categories.get(cat_id)
            
            if not category_info:
                cat_id = 'SFX'
                category_info = self.categories.get(cat_id, {
                    'name': '特效音效',
                    'name_zh': '其他',
                    'subcategory': 'Effect',
                    'subcategory_zh': '其他'
                })
            
            # 获取分类中文名称
            cat_id_zh = category_info.get('subcategory_zh', '其他')
            
            # 构建英文名称（使用规范的驼峰式命名）
            en_words = parts.get('original_words', [])
            if isinstance(en_words, str):
                en_words = [en_words]
            
            # 规范化英文名称
            en_name = ''
            for word in en_words:
                word = word.strip().lower()
                # 移除常见的无意义词
                if word in self.COMMON_PREFIXES:
                    continue
                # 处理特殊缩写
                if word.upper() in self.SPECIAL_ABBR:
                    en_name += word.upper()
                else:
                    en_name += word.capitalize()
            
            # 构建中文描述
            zh_words = []
            
            # 1. 添加声音类型描述（如果有）
            voice_type_words = [w for w in parts.get('translated_words', []) 
                              if any(vt in w for vt in ['男性', '女性', '人声'])]
            if voice_type_words:
                zh_words.extend(voice_type_words[:1])  # 只使用第一个声音类型词
            
            # 2. 添加动作描述（如果有）
            action_words = [w for w in parts.get('translated_words', []) 
                           if w not in voice_type_words and w not in self.REDUNDANT_WORDS]
            if action_words:
                zh_words.extend(action_words)
            
            # 如果没有有效的翻译词，使用分类名称
            if not zh_words:
                zh_words = [category_info.get('subcategory_zh', '其他')]
            
            # 清理和优化中文描述
            zh_name = ''.join(zh_words)
            zh_name = re.sub(r'[的了着过]', '', zh_name)  # 移除语气词
            
            # 限制长度
            zh_name = zh_name[:12]
            
            # 获取序号
            number = parts.get('number', '001')
            
            # 构建最终结果
            result = f"{cat_id}_{cat_id_zh}_{en_name}_{zh_name}_{number}"
            
            # 确保结果是有效的文件名
            result = re.sub(r'[\s]+', '', result)  # 移除所有空白字符
            result = re.sub(r'_+', '_', result)    # 合并多个下划线
            result = result.strip('_')             # 移除首尾下划线
            
            return result
            
        except Exception as e:
            self.logger.error(f"格式化结果失败: {str(e)}")
            return f"SFX_其他_unknown_未知_{parts.get('number', '001')}"
    
    def _generate_fallback_name(self, text: str) -> str:
        """生成应急文件名,符合 UCS 标准的双语结构"""
        # 生成一个短的哈希值作为 FXName
        hash_value = hashlib.md5(text.encode()).hexdigest()[:8]
        
        # 使用默认值
        cat_id = 'SFXMisc'  # 默认使用 misc 分类
        cat_id_zh = '其他'  # 默认分类中文名
        
        # 构建双语描述
        en_name = f"Unknown{hash_value}"
        zh_name = "未知音效"
        
        # 生成序号
        number = "001"
        
        return f"{cat_id}_{cat_id_zh}_{en_name}_{zh_name}_{number}"

    def _clean_translation(self, translated: str) -> str:
        """清理翻译结果"""
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
        
        # 移除部分重复（一个词是另一个词的子串）并保持较长的词
        filtered_words = []
        for i, word in enumerate(unique_words):
            keep_word = True
            for j, other_word in enumerate(unique_words):
                if i != j:
                    if word in other_word and len(other_word) - len(word) <= 1:
                        # 如果当前词是其他词的子串，且长度相差不大，则保留较短的
                        keep_word = len(word) <= len(other_word)
                        break
            if keep_word:
                filtered_words.append(word)
        
        # 限制单个词的长度和总长度
        filtered_words = [w[:6] if len(w) > 6 else w for w in filtered_words]  # 放宽单词长度限制
        result = ''.join(filtered_words)
        
        # 确保总长度不超过12个字符
        if len(result) > 12:
            result = result[:12]
        
        # 如果结果为空，返回原始输入的前12个字符
        if not result:
            result = translated[:12]
        
        # 移除无意义短语
        result = re.sub(r'(请提供|具体|英文|需要|警告|完整).*', '', result)
        
        # 移除环境音效相关的冗余词
        env_words = ["环境", "嗡", "嗡鸣", "轻响"]
        for word in env_words:
            if result.startswith(word):
                result = result[len(word):]
        
        return result.strip()

    def translate_with_api(self, text: str) -> str:
        """使用 API 进行翻译"""
        try:
            # 获取当前服务配置
            service_id = self.config.get("TRANSLATION_SERVICE")
            services = self.config.get("TRANSLATION_SERVICES", {})
            
            if service_id not in services:
                raise Exception("翻译服务未配置")
            
            service = services[service_id]
            api_url = service.get("api_url", "").strip()
            api_key = service.get("api_key", "").strip()
            model = service.get("current_model", "")
            
            if not api_url or not api_key or not model:
                raise Exception("API 配置不完整")
            
            # 获取提示词
            prompt = self._get_current_prompt()
            prompt = prompt.format(text=text)
            
            # 获取请求格式模板并使用它
            request_format = service.get("request_format", {})
            data = json.loads(json.dumps(request_format).format(
                model=model,
                prompt=prompt,
                text=text
            ))
            
            # 发送请求
            response = requests.post(
                api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                json=data,
                timeout=30
            )
            
            if response.status_code != 200:
                result = response.json() if response.text else {"error": {"message": "无响应内容"}}
                
                # 特殊错误处理
                if "openrouter" in service_id and response.status_code == 402:
                    error_msg = result.get("error", {}).get("message", "")
                    if "credits" in error_msg.lower():
                        raise Exception("OpenRouter 额度不足，请充值或更换其他服务")
                
                # 其他错误
                error_msg = result.get("error", {}).get("message", response.text)
                raise Exception(f"API 请求失败 ({response.status_code}): {error_msg}")
            
            result = response.json()
            
            # 根据不同服务提取响应内容
            content = None
            if "bailian" in service_id:
                # 百炼 API 响应格式
                if "output" in result:
                    content = result["output"].get("text", "")
                elif "message" in result:
                    content = result["message"].get("content", "")
            else:
                # 标准响应格式
                if "choices" in result and result["choices"]:
                    message = result["choices"][0].get("message", {})
                    if message:
                        content = message.get("content")
                    if not content and "delta" in result["choices"][0]:
                        content = result["choices"][0]["delta"].get("content")
            
            if not content:
                raise Exception("无法从响应中提取翻译结果")
            
            return content.strip()
            
        except Exception as e:
            logging.error(f"API 翻译失败: {str(e)}")
            if "额度不足" in str(e):
                raise Exception(f"{str(e)}。建议切换到其他可用的翻译服务，如智谱 AI 或硅基流动。")
            raise Exception(f"翻译失败: {str(e)}")

    def batch_translate_filenames(self, filenames: List[str], batch_size: int = 10) -> List[str]:
        """批量翻译文件名
        
        Args:
            filenames: 要翻译的文件名列表
            batch_size: 每批处理的文件数量
            
        Returns:
            List[str]: 翻译后的文件名列表
        """
        results = []
        total_files = len(filenames)
        
        # 按批次处理文件
        for i in range(0, total_files, batch_size):
            batch = filenames[i:i + batch_size]
            
            # 1. 预处理所有文件名
            preprocessed = [(f, self._preprocess_filename(f)) for f in batch]
            
            # 2. 分析所有文件名
            analyzed = [(f, p, self._analyze_filename(p)) for f, p in preprocessed]
            
            # 3. 收集所有需要翻译的词
            all_words = set()
            for _, _, parts in analyzed:
                all_words.update(parts['parts'])
            
            # 4. 批量获取翻译
            translations = self._batch_translate_words(list(all_words))
            
            # 5. 处理每个文件
            for original, _, parts in analyzed:
                try:
                    # 使用已获取的翻译更新parts
                    parts_with_trans = self._apply_translations(parts, translations)
                    
                    # 格式化结果
                    result = self._format_result(parts_with_trans)
                    results.append(result)
                    
                except Exception as e:
                    logging.error(f"处理文件 {original} 失败: {e}")
                    results.append(self._generate_fallback_name(original))
            
            # 记录进度
            progress = min(100, (i + len(batch)) / total_files * 100)
            logging.info(f"批量翻译进度: {progress:.1f}% ({i + len(batch)}/{total_files})")
        
        return results

    def _batch_translate_words(self, words: List[str], chunk_size: int = 5) -> Dict[str, str]:
        """批量翻译词语
        
        Args:
            words: 需要翻译的词语列表
            chunk_size: 每次API请求的词语数量
            
        Returns:
            Dict[str, str]: 词语翻译映射
        """
        translations = {}
        api_calls = 0
        
        # 1. 首先使用分类匹配（最优先）
        for word in words:
            matched = False
            for cat_id, info in self.categories.items():
                # 检查英文同义词
                if word.lower() in [s.lower() for s in info.get('synonyms', [])]:
                    translations[word] = info['subcategory_zh']
                    logging.debug(f"分类匹配: {word} -> {info['subcategory_zh']}")
                    matched = True
                    break
                # 检查中文同义词
                if word in info.get('synonyms_zh', []):
                    translations[word] = info['subcategory_zh']
                    logging.debug(f"中文分类匹配: {word} -> {info['subcategory_zh']}")
                    matched = True
                    break
            if matched:
                continue
        
        # 2. 对未翻译的词语使用 AI 翻译
        untranslated = [w for w in words if w not in translations]
        if untranslated:
            try:
                # 记录需要AI翻译的词数
                logging.info(f"需要AI翻译的词数: {len(untranslated)}")
                
                # 分块处理
                for i in range(0, len(untranslated), chunk_size):
                    chunk = untranslated[i:i + chunk_size]
                    api_calls += 1
                    
                    try:
                        # 使用带重试机制的翻译
                        for word in chunk:
                            result = self._translate_with_retries(word)
                            if result:
                                translations[word] = result
                                logging.debug(f"AI翻译成功: {word} -> {result}")
                            else:
                                # 如果AI翻译失败，使用基本处理
                                basic_result = self._basic_translation(word)
                                translations[word] = basic_result
                                logging.debug(f"使用基本处理: {word} -> {basic_result}")
                    
                    except Exception as e:
                        logging.error(f"处理分块 {i//chunk_size + 1} 失败: {e}")
                        continue
                    
                logging.info(f"AI调用次数: {api_calls}")
                    
            except Exception as e:
                logging.error(f"AI批量翻译失败: {e}")
        
        return translations

    def _apply_translations(self, parts: Dict[str, Any], translations: Dict[str, str]) -> Dict[str, str]:
        """将翻译应用到文件名部分
        
        Args:
            parts: 文件名各部分信息
            translations: 翻译映射
            
        Returns:
            Dict[str, str]: 更新后的文件名部分信息
        """
        translated_words = []
        original_words = []
        
        for part in parts['parts']:
            original_words.append(part)
            translated = translations.get(part, self._basic_translation(part))
            translated_words.append(translated)
        
        # 获取分类信息
        main_cat = parts['main_category']
        category_info = self.categories.get(main_cat, {})
        mid_category = category_info.get('name_zh', '特效')
        sub_category = category_info.get('subcategory_zh', '其他')
        
        # 清理和优化翻译结果
        translated_words = self._optimize_translations(translated_words, category_info)
        
        return {
            'mid_category': mid_category,
            'sub_category': sub_category,
            'core_word': self._join_translations(translated_words),
            'original_words': original_words,
            'translated_words': translated_words,
            'number': parts['number'],
            'main_category': main_cat
        }

    def test_filename_matching(self, filename: str):
        """测试文件名匹配"""
        # 预处理文件名
        name = self._preprocess_filename(filename)
        # 分析文件名部分
        parts = self._analyze_filename(name)
        # 获取分类
        cat_id = self._guess_main_category(parts['parts'])
        # 获取翻译结果
        result = self.translate_filename(filename)
        
        return {
            'original': filename,
            'preprocessed': name,
            'parts': parts,
            'category_id': cat_id,
            'final_result': result
        }

    def _get_descriptions(self, text: str) -> Optional[Tuple[str, str]]:
        """一次性获取英文和中文描述"""
        prompt = self._get_current_prompt()
        
        result = self._translate_with_retries(text, prompt)
        if not result:
            return None
        
        try:
            lines = result.strip().split('\n')
            if len(lines) != 2:
                return None
            
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
            logging.error(f"解析翻译结果失败: {str(e)}")
            return None

    def _get_current_prompt(self) -> str:
        """获取当前使用的 prompt"""
        service = self.service_config
        if service:
            prompts = service.get('prompts', {})
            # 始终使用双语音效描述
            return prompts.get('双语音效描述', self.config.get_bilingual_description_prompt())
        return self.config.get_bilingual_description_prompt()

    def _extract_response_content(self, result: dict) -> Optional[str]:
        """统一提取响应内容"""
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
            logging.error(f"提取响应内容失败: {str(e)}")
            return None

def test_examples():
    """测试示例文件名"""
    # 创建翻译器实例
    translator = Translator(config)
    
    # 测试文件名列表
    filenames = [
        "turn_paper_fast_3",
        "human_male_death_1",
        "human_male_grunt_confused_2"
    ]
    
    # 测试每个文件名
    for filename in filenames:
        print(f"\n测试文件名: {filename}")
        result = translator.test_filename_matching(filename)
        print(f"原始文件名: {result['original']}")
        print(f"预处理后: {result['preprocessed']}")
        print(f"分析部分: {result['parts']}")
        print(f"匹配分类: {result['category_id']}")
        print(f"最终结果: {result['final_result']}")
        print("-" * 50)
