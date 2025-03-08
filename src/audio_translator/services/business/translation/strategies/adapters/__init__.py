"""
翻译策略适配器包

包含各种API服务的适配器实现，将ModelService适配为ITranslationStrategy接口。
"""

from .openai_adapter import OpenAIAdapter
from .anthropic_adapter import AnthropicAdapter
from .gemini_adapter import GeminiAdapter
from .alibaba_adapter import AlibabaAdapter
from .zhipu_adapter import ZhipuAdapter
from .volc_adapter import VolcAdapter
from .deepseek_adapter import DeepSeekAdapter

__all__ = [
    'OpenAIAdapter',
    'AnthropicAdapter',
    'GeminiAdapter',
    'AlibabaAdapter',
    'ZhipuAdapter',
    'VolcAdapter',
    'DeepSeekAdapter',
] 