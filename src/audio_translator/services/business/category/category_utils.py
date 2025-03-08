"""
分类工具函数模块

此模块提供分类相关的工具函数，用于分类数据的处理和操作。
"""

import re
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict

from .category import Category

# 设置日志记录器
logger = logging.getLogger(__name__)

def normalize_text(text: str) -> str:
    """
    规范化文本以便匹配
    
    去除特殊字符、转小写等
    
    Args:
        text: 原始文本
        
    Returns:
        规范化后的文本
    """
    # 去除特殊字符，保留字母、数字和空格
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    # 将多个空格替换为单个空格
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    计算两个文本的相似度
    
    Args:
        text1: 第一个文本
        text2: 第二个文本
        
    Returns:
        相似度分数（0-1）
    """
    # 规范化文本
    text1 = normalize_text(text1)
    text2 = normalize_text(text2)
    
    # 如果文本为空，返回0
    if not text1 or not text2:
        return 0.0
    
    # 拆分为词组
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    # 计算交集大小
    intersection = words1.intersection(words2)
    
    # 计算并集大小
    union = words1.union(words2)
    
    # 计算Jaccard相似度
    if not union:
        return 0.0
    
    return len(intersection) / len(union)

def calculate_category_match_score(filename: str, category: Category) -> Tuple[float, List[str]]:
    """
    计算文件名与分类的匹配分数
    
    Args:
        filename: 文件名
        category: 分类对象
        
    Returns:
        (匹配分数, 匹配理由列表)
    """
    score = 0.0
    reasons = []
    
    # 规范化文件名
    filename_lower = normalize_text(filename)
    filename_words = filename_lower.split()
    
    # 检查分类ID
    if category.cat_id.lower() in filename_lower:
        score += 30
        reasons.append(f"文件名包含分类ID: {category.cat_id}")
    
    # 检查主分类名称
    if category.name_en.lower() in filename_lower:
        score += 20
        reasons.append(f"文件名包含英文分类名: {category.name_en}")
    
    # 检查中文分类名称
    if category.name_zh in filename:
        score += 15
        reasons.append(f"文件名包含中文分类名: {category.name_zh}")
    
    # 检查子分类
    if category.subcategory and category.subcategory.lower() in filename_lower:
        score += 25
        reasons.append(f"文件名包含英文子分类: {category.subcategory}")
    
    if category.subcategory_zh and category.subcategory_zh in filename:
        score += 20
        reasons.append(f"文件名包含中文子分类: {category.subcategory_zh}")
    
    # 检查英文同义词
    for synonym in category.synonyms_en:
        if synonym.lower() in filename_lower:
            score += 15
            reasons.append(f"文件名包含英文同义词: {synonym}")
            break
    
    # 检查中文同义词
    for synonym in category.synonyms_zh:
        if synonym in filename:
            score += 15
            reasons.append(f"文件名包含中文同义词: {synonym}")
            break
    
    # 检查是否为文件名前两个词
    if len(filename_words) >= 2:
        first_two_words = ' '.join(filename_words[:2])
        if (category.name_en.lower() in first_two_words or 
            any(synonym.lower() in first_two_words for synonym in category.synonyms_en)):
            score += 10
            reasons.append(f"分类名或同义词出现在文件名前两个词中")
    
    return score, reasons

def filter_categories_by_keyword(categories: Dict[str, Category], 
                                keyword: str, 
                                threshold: float = 0.3) -> Dict[str, Category]:
    """
    根据关键字过滤分类
    
    Args:
        categories: 分类字典
        keyword: 关键字
        threshold: 相似度阈值
        
    Returns:
        过滤后的分类字典
    """
    if not keyword:
        return categories
    
    keyword = normalize_text(keyword)
    results = {}
    
    for cat_id, category in categories.items():
        # 检查分类ID
        if keyword.lower() in cat_id.lower():
            results[cat_id] = category
            continue
        
        # 检查英文名称
        name_en = normalize_text(category.get_full_name_en())
        if keyword in name_en:
            results[cat_id] = category
            continue
        
        # 检查中文名称
        name_zh = category.get_full_name_zh()
        if keyword in name_zh:
            results[cat_id] = category
            continue
        
        # 检查同义词
        for synonym in category.synonyms_en:
            if keyword in normalize_text(synonym):
                results[cat_id] = category
                break
        
        for synonym in category.synonyms_zh:
            if keyword in synonym:
                results[cat_id] = category
                break
        
        # 检查相似度
        similarity_en = calculate_text_similarity(keyword, name_en)
        similarity_zh = calculate_text_similarity(keyword, name_zh)
        
        if max(similarity_en, similarity_zh) >= threshold:
            results[cat_id] = category
    
    return results

def create_category_path(cat_id: str, base_path: str) -> str:
    """
    创建分类路径
    
    Args:
        cat_id: 分类ID
        base_path: 基础路径
        
    Returns:
        分类路径
    """
    import os
    cat_parts = cat_id.split('_')
    
    # 如果是两级分类
    if len(cat_parts) > 1:
        parent_id = cat_parts[0]
        return os.path.join(base_path, parent_id, cat_id)
    
    # 如果是一级分类
    return os.path.join(base_path, cat_id) 