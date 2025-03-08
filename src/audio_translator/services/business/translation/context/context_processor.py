"""
翻译上下文处理模块，提供文本预处理、后处理和上下文感知的翻译支持。

主要功能：
1. 文本预处理：在翻译前对文本进行处理，如去除多余空格、标准化格式等
2. 文本后处理：在翻译后对结果进行处理，如恢复格式、替换保留词等
3. 上下文管理：维护翻译过程中的上下文信息，提高翻译一致性
4. 分段处理：将长文本分段处理，然后合并结果
5. 特定领域处理：针对不同领域(音频、技术、学术等)的翻译优化
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple, Callable

# 设置日志记录器
logger = logging.getLogger(__name__)

class ContextProcessor:
    """翻译上下文处理器，负责翻译过程中的文本处理和上下文管理"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化上下文处理器
        
        Args:
            config: 配置信息，包含以下选项：
                - max_segment_length: 文本分段的最大长度
                - preserve_patterns: 需要在翻译中保留的模式列表(正则表达式)
                - domain_specific_rules: 不同领域的特定处理规则
                - post_processors: 后处理器配置
        """
        self.config = config or {}
        self.max_segment_length = self.config.get('max_segment_length', 4000)
        self.preserve_patterns = self.config.get('preserve_patterns', [])
        self.domain_specific_rules = self.config.get('domain_specific_rules', {})
        
        # 编译保留模式正则表达式
        self.preserve_pattern_regexes = []
        for pattern in self.preserve_patterns:
            try:
                self.preserve_pattern_regexes.append(re.compile(pattern))
            except re.error as e:
                logger.warning(f"无效的正则表达式模式 '{pattern}': {str(e)}")
        
        # 初始化预处理器和后处理器
        self.preprocessors = self._initialize_preprocessors()
        self.postprocessors = self._initialize_postprocessors()
        
        # 翻译上下文
        self.context = {}
        
        # 翻译历史
        self.translation_history = []
        self.max_history_size = self.config.get('max_history_size', 100)
        
        # 外部服务依赖
        self.category_service = None
        self.naming_service = None
        
        logger.info("上下文处理器初始化完成")
    
    def set_category_service(self, service):
        """设置分类服务"""
        self.category_service = service
        
    def set_naming_service(self, service):
        """设置命名服务"""
        self.naming_service = service
    
    def build_context(self, file_path: str, text: str = None, domain: str = None) -> Dict[str, Any]:
        """
        根据文件路径和可选的文本构建翻译上下文
        
        Args:
            file_path: 文件路径
            text: 要翻译的文本，如果不提供则使用文件内容
            domain: 文本领域，如果不提供则尝试推断
            
        Returns:
            翻译上下文字典
        """
        # 创建基础上下文
        context = {
            'source_file': file_path,
            'timestamp': self._get_timestamp(),
            'source_text': text
        }
        
        # 添加文件信息
        file_info = self._extract_file_info(file_path)
        context.update(file_info)
        
        # 设置领域
        if domain:
            context['domain'] = domain
        elif 'file_extension' in file_info:
            # 基于文件扩展名推断领域
            domain_mapping = {
                'mp3': 'audio',
                'wav': 'audio',
                'flac': 'audio',
                'm4a': 'audio',
                'ogg': 'audio',
                'py': 'code',
                'js': 'code',
                'java': 'code',
                'cpp': 'code',
                'c': 'code',
                'h': 'code',
                'txt': 'text',
                'md': 'text',
                'doc': 'document',
                'docx': 'document',
                'pdf': 'document',
                'xls': 'spreadsheet',
                'xlsx': 'spreadsheet',
                'csv': 'spreadsheet',
                'ppt': 'presentation',
                'pptx': 'presentation'
            }
            context['domain'] = domain_mapping.get(file_info.get('file_extension', '').lower(), 'general')
        
        # 添加分类信息(如果有CategoryService)
        if self.category_service:
            try:
                # 尝试猜测分类
                category_info = self.category_service.guess_category(file_path)
                if category_info:
                    context['category'] = category_info
                    
                # 如果有文本和分类，尝试获取命名字段
                if text and category_info:
                    fields = self.category_service.guess_category_with_fields(text, category_info)
                    if fields:
                        context['naming_fields'] = fields
            except Exception as e:
                logger.error(f"获取分类信息时出错: {str(e)}")
        
        # 添加命名信息(如果有NamingService)
        if self.naming_service:
            try:
                naming_context = self.naming_service.analyze_filename(file_path)
                if naming_context:
                    context['naming_context'] = naming_context
            except Exception as e:
                logger.error(f"分析文件名时出错: {str(e)}")
        
        # 更新缓存的上下文
        self._update_context(context)
        
        return context
    
    def _extract_file_info(self, file_path: str) -> Dict[str, Any]:
        """提取文件信息"""
        import os
        import pathlib
        
        # 初始化结果
        info = {}
        
        # 路径分析
        path = pathlib.Path(file_path)
        
        # 基本文件信息
        info['file_name'] = path.name
        info['file_stem'] = path.stem
        info['file_extension'] = path.suffix.lstrip('.')
        info['parent_directory'] = str(path.parent)
        
        # 文件状态信息(如果文件存在)
        if path.exists():
            try:
                stats = path.stat()
                info['file_size'] = stats.st_size
                info['last_modified'] = stats.st_mtime
                info['is_file'] = path.is_file()
                info['is_directory'] = path.is_dir()
            except Exception as e:
                logger.warning(f"获取文件状态信息失败: {str(e)}")
        
        return info
    
    def _initialize_preprocessors(self) -> List[Callable]:
        """初始化文本预处理器列表"""
        preprocessors = [
            self._normalize_whitespace,
            self._extract_preserve_patterns,
            self._apply_domain_specific_preprocessing
        ]
        
        # 添加自定义预处理器
        custom_preprocessors = self.config.get('custom_preprocessors', [])
        for preprocessor_config in custom_preprocessors:
            if callable(preprocessor_config.get('function')):
                preprocessors.append(preprocessor_config['function'])
        
        return preprocessors
    
    def _initialize_postprocessors(self) -> List[Callable]:
        """初始化文本后处理器列表"""
        postprocessors = [
            self._restore_preserve_patterns,
            self._normalize_line_endings,
            self._apply_domain_specific_postprocessing
        ]
        
        # 添加自定义后处理器
        custom_postprocessors = self.config.get('custom_postprocessors', [])
        for postprocessor_config in custom_postprocessors:
            if callable(postprocessor_config.get('function')):
                postprocessors.append(postprocessor_config['function'])
        
        return postprocessors
    
    def preprocess(self, text: str, context: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
        """
        文本预处理
        
        Args:
            text: 原始文本
            context: 翻译上下文
            
        Returns:
            处理后的文本和更新的上下文
        """
        processed_text = text
        updated_context = context.copy() if context else {}
        
        # 更新内部上下文
        self._update_context(updated_context)
        
        # 应用所有预处理器
        for preprocessor in self.preprocessors:
            try:
                processed_text, updated_context = preprocessor(processed_text, updated_context)
            except Exception as e:
                logger.error(f"预处理器 {preprocessor.__name__} 发生错误: {str(e)}")
        
        return processed_text, updated_context
    
    def postprocess(self, text: str, context: Dict[str, Any] = None) -> str:
        """
        文本后处理
        
        Args:
            text: 翻译后的文本
            context: 翻译上下文
            
        Returns:
            处理后的文本
        """
        processed_text = text
        context = context or {}
        
        # 应用所有后处理器
        for postprocessor in self.postprocessors:
            try:
                processed_text = postprocessor(processed_text, context)
            except Exception as e:
                logger.error(f"后处理器 {postprocessor.__name__} 发生错误: {str(e)}")
        
        # 更新翻译历史
        self._update_translation_history(context.get('source_text', ''), processed_text)
        
        return processed_text
    
    def split_text(self, text: str, context: Dict[str, Any] = None) -> List[Tuple[str, Dict[str, Any]]]:
        """
        将长文本分割成多个片段处理
        
        Args:
            text: 原始文本
            context: 翻译上下文
            
        Returns:
            处理后的文本片段和上下文的列表
        """
        if not text:
            return []
            
        # 如果文本小于最大片段长度，直接返回
        if len(text) <= self.max_segment_length:
            preprocessed_text, updated_context = self.preprocess(text, context)
            return [(preprocessed_text, updated_context)]
        
        segments = []
        # 按段落分割文本
        paragraphs = self._split_paragraphs(text)
        
        current_segment = []
        current_length = 0
        segment_index = 0
        
        for para in paragraphs:
            # 如果当前段落加上已有内容超过最大长度，且已有内容不为空
            if current_length + len(para) > self.max_segment_length and current_segment:
                # 处理当前片段
                segment_text = "\n\n".join(current_segment)
                segment_context = context.copy() if context else {}
                segment_context.update({
                    'segment_index': segment_index,
                    'is_segment': True,
                    'total_segments': None  # 先设置为None，后面更新
                })
                
                preprocessed_text, updated_context = self.preprocess(segment_text, segment_context)
                segments.append((preprocessed_text, updated_context))
                
                # 重置当前片段
                current_segment = []
                current_length = 0
                segment_index += 1
            
            # 如果段落本身超过最大长度
            if len(para) > self.max_segment_length:
                # 将段落进一步分割为句子
                sentences = self._split_sentences(para)
                temp_segment = []
                temp_length = 0
                
                for sentence in sentences:
                    # 如果句子加上已有内容超过最大长度，且已有内容不为空
                    if temp_length + len(sentence) > self.max_segment_length and temp_segment:
                        # 处理当前临时片段
                        segment_text = " ".join(temp_segment)
                        segment_context = context.copy() if context else {}
                        segment_context.update({
                            'segment_index': segment_index,
                            'is_segment': True,
                            'total_segments': None
                        })
                        
                        preprocessed_text, updated_context = self.preprocess(segment_text, segment_context)
                        segments.append((preprocessed_text, updated_context))
                        
                        # 重置临时片段
                        temp_segment = []
                        temp_length = 0
                        segment_index += 1
                    
                    # 处理超长句子
                    if len(sentence) > self.max_segment_length:
                        # 简单地按最大长度切分
                        for i in range(0, len(sentence), self.max_segment_length):
                            chunk = sentence[i:i + self.max_segment_length]
                            segment_context = context.copy() if context else {}
                            segment_context.update({
                                'segment_index': segment_index,
                                'is_segment': True,
                                'is_partial_sentence': True,
                                'total_segments': None
                            })
                            
                            preprocessed_text, updated_context = self.preprocess(chunk, segment_context)
                            segments.append((preprocessed_text, updated_context))
                            segment_index += 1
                    else:
                        # 添加句子到临时片段
                        temp_segment.append(sentence)
                        temp_length += len(sentence) + 1  # +1 是为了空格
                
                # 处理剩余的临时片段
                if temp_segment:
                    segment_text = " ".join(temp_segment)
                    segment_context = context.copy() if context else {}
                    segment_context.update({
                        'segment_index': segment_index,
                        'is_segment': True,
                        'total_segments': None
                    })
                    
                    preprocessed_text, updated_context = self.preprocess(segment_text, segment_context)
                    segments.append((preprocessed_text, updated_context))
                    segment_index += 1
            else:
                # 添加段落到当前片段
                current_segment.append(para)
                current_length += len(para) + 2  # +2 是为了换行符
        
        # 处理剩余的段落
        if current_segment:
            segment_text = "\n\n".join(current_segment)
            segment_context = context.copy() if context else {}
            segment_context.update({
                'segment_index': segment_index,
                'is_segment': True,
                'total_segments': None
            })
            
            preprocessed_text, updated_context = self.preprocess(segment_text, segment_context)
            segments.append((preprocessed_text, updated_context))
        
        # 更新片段总数
        total_segments = len(segments)
        for i, (text, ctx) in enumerate(segments):
            ctx['total_segments'] = total_segments
        
        return segments
    
    def merge_translations(self, translations: List[str], contexts: List[Dict[str, Any]]) -> str:
        """
        合并多个翻译片段为一个完整的翻译
        
        Args:
            translations: 翻译片段列表
            contexts: 上下文列表
            
        Returns:
            合并后的翻译
        """
        if not translations:
            return ""
            
        # 只有一个片段时直接返回
        if len(translations) == 1:
            return self.postprocess(translations[0], contexts[0])
        
        # 按片段索引排序
        sorted_pairs = sorted(
            zip(translations, contexts), 
            key=lambda pair: pair[1].get('segment_index', 0)
        )
        
        # 单独处理并合并每个片段
        processed_segments = []
        for text, context in sorted_pairs:
            # 处理每个片段
            processed_text = self.postprocess(text, context)
            processed_segments.append(processed_text)
        
        # 根据片段标识选择合并方式
        is_partial_sentence = any(
            ctx.get('is_partial_sentence', False) for ctx in contexts
        )
        
        if is_partial_sentence:
            # 直接连接部分句子片段
            result = "".join(processed_segments)
        else:
            # 用换行符连接正常片段
            result = "\n\n".join(processed_segments)
        
        return result
    
    def _normalize_whitespace(self, text: str, context: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """标准化空白字符"""
        normalized = re.sub(r'\s+', ' ', text)
        normalized = normalized.strip()
        return normalized, context
    
    def _extract_preserve_patterns(self, text: str, context: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """提取并保存需要在翻译中保留的模式"""
        preserved_items = []
        processed_text = text
        
        # 查找并替换所有需要保留的模式
        for i, pattern in enumerate(self.preserve_pattern_regexes):
            matches = pattern.findall(processed_text)
            for j, match in enumerate(matches):
                placeholder = f"__PRESERVED_{i}_{j}__"
                processed_text = processed_text.replace(match, placeholder, 1)
                preserved_items.append((placeholder, match))
        
        # 更新上下文
        preserved_context = context.copy()
        preserved_context['preserved_items'] = preserved_items
        
        return processed_text, preserved_context
    
    def _restore_preserve_patterns(self, text: str, context: Dict[str, Any]) -> str:
        """恢复保留的模式"""
        if not context or 'preserved_items' not in context:
            return text
            
        result = text
        for placeholder, original in context['preserved_items']:
            result = result.replace(placeholder, original)
            
        return result
    
    def _normalize_line_endings(self, text: str, context: Dict[str, Any]) -> str:
        """标准化行尾"""
        return text.replace('\r\n', '\n')
    
    def _apply_domain_specific_preprocessing(self, text: str, context: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """应用领域特定的预处理规则"""
        domain = context.get('domain', 'general')
        rules = self.domain_specific_rules.get(domain, {}).get('preprocessing', [])
        
        processed_text = text
        for rule in rules:
            if 'pattern' in rule and 'replacement' in rule:
                try:
                    pattern = re.compile(rule['pattern'])
                    processed_text = pattern.sub(rule['replacement'], processed_text)
                except re.error as e:
                    logger.warning(f"域特定预处理规则错误: {str(e)}")
        
        return processed_text, context
    
    def _apply_domain_specific_postprocessing(self, text: str, context: Dict[str, Any]) -> str:
        """应用领域特定的后处理规则"""
        domain = context.get('domain', 'general')
        rules = self.domain_specific_rules.get(domain, {}).get('postprocessing', [])
        
        processed_text = text
        for rule in rules:
            if 'pattern' in rule and 'replacement' in rule:
                try:
                    pattern = re.compile(rule['pattern'])
                    processed_text = pattern.sub(rule['replacement'], processed_text)
                except re.error as e:
                    logger.warning(f"域特定后处理规则错误: {str(e)}")
        
        return processed_text
    
    def _update_context(self, context: Dict[str, Any]) -> None:
        """更新内部上下文"""
        # 更新内部上下文，但不覆盖传入的上下文
        merged_context = {**self.context, **context}
        
        # 从合并后的上下文中更新内部状态
        self.context = merged_context
    
    def _update_translation_history(self, source: str, translation: str) -> None:
        """更新翻译历史记录"""
        # 添加到历史记录
        self.translation_history.append({
            'source': source,
            'translation': translation,
            'timestamp': self._get_timestamp()
        })
        
        # 限制历史记录大小
        if len(self.translation_history) > self.max_history_size:
            self.translation_history = self.translation_history[-self.max_history_size:]
    
    def _get_timestamp(self) -> float:
        """获取当前时间戳"""
        import time
        return time.time()
    
    def _split_paragraphs(self, text: str) -> List[str]:
        """将文本分割为段落"""
        # 按连续两个或更多换行符分割
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _split_sentences(self, text: str) -> List[str]:
        """将文本分割为句子"""
        # 简单的按句号、问号、感叹号分割
        sentences = re.split(r'([.!?])\s+', text)
        
        # 重新组合句子，确保每个句子都包含结束标点
        result = []
        i = 0
        while i < len(sentences):
            if i + 1 < len(sentences) and sentences[i + 1] in ['.', '!', '?']:
                result.append(sentences[i] + sentences[i + 1])
                i += 2
            else:
                result.append(sentences[i])
                i += 1
        
        return [s.strip() for s in result if s.strip()]
    
    def get_translation_history(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        获取翻译历史记录
        
        Args:
            limit: 返回的最大记录数
            
        Returns:
            翻译历史记录列表
        """
        if limit is None or limit >= len(self.translation_history):
            return self.translation_history
        return self.translation_history[-limit:]
    
    def clear_history(self) -> None:
        """清除翻译历史记录"""
        self.translation_history = []
    
    def get_context(self) -> Dict[str, Any]:
        """获取当前上下文"""
        return self.context.copy()
    
    def set_context(self, context: Dict[str, Any]) -> None:
        """设置当前上下文"""
        self.context = context.copy() if context else {}
    
    def clear_context(self) -> None:
        """清除当前上下文"""
        self.context = {}
        
    def validate_context(self, context: Dict[str, Any], required_fields: List[str] = None) -> bool:
        """
        验证上下文是否包含所需字段
        
        Args:
            context: 上下文字典
            required_fields: 必需的字段列表，如果为None则使用默认必需字段
            
        Returns:
            验证是否通过
        """
        if not context:
            logger.warning("上下文为空")
            return False
            
        # 默认必需字段
        default_required = ['source_file']
        required = required_fields or default_required
        
        # 检查必需字段
        missing_fields = [field for field in required if field not in context]
        
        if missing_fields:
            logger.warning(f"上下文缺少必需字段: {', '.join(missing_fields)}")
            return False
            
        return True
    
    def fill_missing_fields(self, context: Dict[str, Any], default_values: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        填充缺失的上下文字段
        
        Args:
            context: 上下文字典
            default_values: 默认值字典，如果为None则使用内部默认值
            
        Returns:
            填充后的上下文
        """
        if not context:
            return context
            
        # 复制上下文
        filled_context = context.copy()
        
        # 基本默认值
        base_defaults = {
            'domain': 'general',
            'source_language': 'en',
            'target_language': 'zh',
            'preserve_formatting': True,
            'quality_preference': 'high'
        }
        
        # 合并默认值
        defaults = {**base_defaults, **(default_values or {})}
        
        # 填充缺失字段
        for key, value in defaults.items():
            if key not in filled_context:
                filled_context[key] = value
        
        # 特殊处理：如果文件名信息存在但源文件不存在
        if 'file_name' in filled_context and 'source_file' not in filled_context:
            # 尝试根据文件名推断源文件路径
            filled_context['source_file'] = filled_context['file_name']
        
        # 特殊处理：如果扩展名存在但域不存在，尝试推断域
        if 'file_extension' in filled_context and 'domain' not in filled_context:
            ext = filled_context['file_extension'].lower()
            # 域映射
            domain_map = {
                'mp3': 'audio',
                'wav': 'audio',
                'flac': 'audio',
                'm4a': 'audio',
                'ogg': 'audio',
                'py': 'code',
                'js': 'code',
                'java': 'code',
                'cpp': 'code',
                'txt': 'text',
                'md': 'text',
                'doc': 'document',
                'docx': 'document',
                'pdf': 'document'
            }
            filled_context['domain'] = domain_map.get(ext, 'general')
        
        # 特殊处理：如果源文本不存在且源文件存在，尝试读取源文件（仅文本类型）
        if 'source_text' not in filled_context and 'source_file' in filled_context:
            # 仅处理可能是文本文件的类型
            text_extensions = ['txt', 'md', 'py', 'js', 'java', 'cpp', 'c', 'h', 'html', 'xml', 'json', 'csv']
            file_ext = filled_context.get('file_extension', '').lower()
            
            if file_ext in text_extensions:
                try:
                    import os
                    if os.path.exists(filled_context['source_file']):
                        with open(filled_context['source_file'], 'r', encoding='utf-8') as f:
                            filled_context['source_text'] = f.read()
                            logger.info(f"从文件加载源文本: {filled_context['source_file']}")
                except Exception as e:
                    logger.warning(f"无法从文件加载源文本: {str(e)}")
        
        return filled_context 