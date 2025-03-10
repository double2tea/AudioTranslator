"""
文件操作服务模块

此模块提供文件操作的基础服务，包括文件读写、目录操作、文件移动等功能。
作为应用程序的基础服务之一，为其他组件提供文件操作支持。
"""

import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union, Set

from ..core.base_service import BaseService

# 设置日志记录器
logger = logging.getLogger(__name__)

class FileService(BaseService):
    """
    文件操作服务
    
    提供基本的文件操作功能，包括：
    - 文件读写
    - 目录创建和管理
    - 文件移动和复制
    - 文件信息获取
    
    此服务作为应用程序的基础服务之一，为其他组件提供文件操作支持。
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化文件服务
        
        Args:
            config: 服务配置
        """
        super().__init__("file_service", config)
        self.temp_directory = None
        self.cache_directory = None
    
    def initialize(self) -> bool:
        """
        初始化文件服务
        
        创建必要的临时目录和缓存目录。
        
        Returns:
            初始化是否成功
        """
        try:
            # 获取应用数据目录，优先使用配置中的 app.data_dir，其次使用 app_data_dir，最后使用默认路径
            app_data_dir = None
            
            # 优先检查 app.data_dir (测试环境使用)
            if self.config and self.config.get('app') and 'data_dir' in self.config['app']:
                app_data_dir = self.config['app']['data_dir']
            # 其次检查直接的 app_data_dir 配置
            elif self.config and 'app_data_dir' in self.config:
                app_data_dir = self.config['app_data_dir']
            # 最后使用默认位置
            else:
                app_data_dir = os.path.join(os.path.expanduser("~"), ".audio_translator")
            
            # 创建应用数据目录（如果不存在）
            os.makedirs(app_data_dir, exist_ok=True)
            
            # 创建临时目录和缓存目录
            self.temp_directory = os.path.join(app_data_dir, "temp")
            self.cache_directory = os.path.join(app_data_dir, "cache")
            
            os.makedirs(self.temp_directory, exist_ok=True)
            os.makedirs(self.cache_directory, exist_ok=True)
            
            # 保存应用数据目录
            self.app_data_dir = app_data_dir
            
            self.is_initialized = True
            logger.info(f"文件服务初始化成功，应用数据目录: {app_data_dir}")
            return True
            
        except Exception as e:
            logger.error(f"文件服务初始化失败: {str(e)}")
            return False
    
    def shutdown(self) -> bool:
        """
        关闭文件服务
        
        清理临时文件。
        
        Returns:
            关闭是否成功
        """
        try:
            # 清理临时目录
            if self.temp_directory and os.path.exists(self.temp_directory):
                self._clear_directory(self.temp_directory)
                
            self.is_initialized = False
            logger.info("文件服务已关闭")
            return True
        
        except Exception as e:
            logger.error(f"文件服务关闭失败: {str(e)}")
            return False
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        获取文件信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件信息字典，包含大小、修改时间等
        """
        try:
            file_stat = os.stat(file_path)
            file_type = os.path.splitext(file_path)[1].lower()
            
            return {
                "exists": True,
                "is_file": os.path.isfile(file_path),
                "is_dir": os.path.isdir(file_path),
                "size": file_stat.st_size,
                "size_formatted": self._format_size(file_stat.st_size),
                "created": file_stat.st_ctime,
                "modified": file_stat.st_mtime,
                "accessed": file_stat.st_atime,
                "type": file_type,
                "path": file_path,
                "name": os.path.basename(file_path)
            }
            
        except FileNotFoundError:
            return {"exists": False}
        except Exception as e:
            logger.error(f"获取文件信息失败: {str(e)}")
            return {"exists": False, "error": str(e)}
    
    def list_files(self, directory: str, 
                  filter_extensions: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
        """
        列出目录中的文件
        
        Args:
            directory: 目录路径
            filter_extensions: 文件扩展名过滤集合，如 {'.mp3', '.wav'}
            
        Returns:
            文件信息列表
        """
        results = []
        
        try:
            if not os.path.exists(directory) or not os.path.isdir(directory):
                logger.warning(f"目录不存在或不是有效目录: {directory}")
                return []
                
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                
                # 仅处理文件
                if not os.path.isfile(file_path):
                    continue
                    
                # 扩展名过滤
                if filter_extensions:
                    extension = os.path.splitext(filename)[1].lower()
                    if extension not in filter_extensions:
                        continue
                
                # 获取文件信息
                file_info = self.get_file_info(file_path)
                results.append(file_info)
                
            # 按文件名排序
            results.sort(key=lambda x: x.get("name", "").lower())
            return results
            
        except Exception as e:
            logger.error(f"列出文件失败: {str(e)}")
            return []
    
    def create_directory(self, path: str) -> bool:
        """
        创建目录
        
        Args:
            path: 目录路径
            
        Returns:
            创建是否成功
        """
        try:
            os.makedirs(path, exist_ok=True)
            logger.debug(f"创建目录: {path}")
            return True
        except Exception as e:
            logger.error(f"创建目录失败: {str(e)}")
            return False
    
    def copy_file(self, source: str, destination: str) -> bool:
        """
        复制文件
        
        Args:
            source: 源文件路径
            destination: 目标文件路径
            
        Returns:
            复制是否成功
        """
        try:
            # 确保目标目录存在
            dest_dir = os.path.dirname(destination)
            if dest_dir:
                os.makedirs(dest_dir, exist_ok=True)
                
            shutil.copy2(source, destination)
            logger.debug(f"复制文件: {source} -> {destination}")
            return True
        except Exception as e:
            logger.error(f"复制文件失败: {str(e)}")
            return False
    
    def move_file(self, source: str, destination: str) -> bool:
        """
        移动文件
        
        Args:
            source: 源文件路径
            destination: 目标文件路径
            
        Returns:
            移动是否成功
        """
        try:
            # 确保目标目录存在
            dest_dir = os.path.dirname(destination)
            if dest_dir:
                os.makedirs(dest_dir, exist_ok=True)
                
            shutil.move(source, destination)
            logger.debug(f"移动文件: {source} -> {destination}")
            return True
        except Exception as e:
            logger.error(f"移动文件失败: {str(e)}")
            return False
    
    def delete_file(self, path: str) -> bool:
        """
        删除文件
        
        Args:
            path: 文件路径
            
        Returns:
            删除是否成功
        """
        try:
            if os.path.exists(path):
                if os.path.isfile(path):
                    os.unlink(path)
                    logger.debug(f"删除文件: {path}")
                    return True
                else:
                    logger.warning(f"不是文件: {path}")
                    return False
            else:
                logger.warning(f"文件不存在: {path}")
                return False
        except Exception as e:
            logger.error(f"删除文件失败: {str(e)}")
            return False
    
    def get_temp_directory(self) -> str:
        """
        获取临时目录路径
        
        Returns:
            临时目录路径
        """
        return self.temp_directory
    
    def get_cache_directory(self) -> str:
        """
        获取缓存目录路径
        
        Returns:
            缓存目录路径
        """
        return self.cache_directory
    
    def create_temp_file(self, prefix: str = "temp", suffix: str = "") -> str:
        """
        创建临时文件
        
        Args:
            prefix: 文件名前缀
            suffix: 文件名后缀
            
        Returns:
            临时文件路径
        """
        import tempfile
        fd, path = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=self.temp_directory)
        os.close(fd)
        return path
    
    def _clear_directory(self, directory: str) -> bool:
        """
        清空目录
        
        Args:
            directory: 要清空的目录路径
            
        Returns:
            清空是否成功
        """
        try:
            if not os.path.exists(directory):
                return True
                
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isfile(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    
            return True
            
        except Exception as e:
            logger.error(f"清空目录失败: {directory}, 错误: {str(e)}")
            return False
    
    def get_data_dir(self) -> str:
        """
        获取应用数据目录
        
        Returns:
            应用数据目录路径
        """
        return self.app_data_dir
    
    def _format_size(self, size: int) -> str:
        """
        格式化文件大小
        
        Args:
            size: 文件大小（字节）
            
        Returns:
            格式化后的大小字符串
        """
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB" 