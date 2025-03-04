"""File manager for audio files.

This module provides a file manager class for handling audio files.
It includes functionality for loading files from directories, filtering by file type,
and retrieving file metadata.
"""

import os
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Set

# 设置日志记录器
logger = logging.getLogger(__name__)

class FileManager:
    """Manages audio files for the application.
    
    This class handles operations related to audio files:
    - Loading files from directories
    - Filtering files by type
    - Getting file metadata
    - Tracking selected files
    
    Attributes:
        current_directory: Current working directory
        audio_extensions: Set of supported audio file extensions
        files: List of loaded files with metadata
        selected_files: List of currently selected file paths
    """
    
    def __init__(self):
        """Initialize the file manager."""
        # 当前目录，默认为用户主目录
        self.current_directory = Path(os.path.expanduser("~"))
        
        # 支持的音频文件类型
        self.audio_extensions = {'.wav', '.mp3', '.ogg', '.flac', '.aiff', '.m4a'}
        
        # 存储加载的文件列表 [(name, size_str, file_type, status, file_path), ...]
        self.files = []
        
        # 当前选中的文件
        self.selected_files = []
        
        logger.debug("FileManager initialized")
    
    def load_directory(self, directory: str) -> List[Tuple[str, str, str, str, str]]:
        """Load files from a directory.
        
        Args:
            directory: Directory path to load files from
            
        Returns:
            List of file metadata tuples (name, size_str, file_type, status, file_path)
        """
        try:
            directory_path = Path(directory)
            if not directory_path.exists() or not directory_path.is_dir():
                logger.error(f"目录不存在或不是有效目录: {directory}")
                return []
            
            # 更新当前目录
            self.current_directory = directory_path
            
            # 清空文件列表
            self.files = []
            
            # 加载目录中的文件
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                
                # 只处理文件
                if os.path.isfile(file_path):
                    # 获取文件扩展名
                    file_type = os.path.splitext(file)[1].lower()
                    
                    # 仅处理音频文件
                    if file_type in self.audio_extensions:
                        # 获取文件大小
                        size = os.path.getsize(file_path)
                        size_str = self._format_size(size)
                        
                        # 添加到文件列表
                        self.files.append((file, size_str, file_type, "未处理", file_path))
            
            # 按文件名排序
            self.files.sort(key=lambda x: x[0].lower())
            
            logger.info(f"已加载目录: {directory}, 共 {len(self.files)} 个文件")
            return self.files
            
        except Exception as e:
            logger.error(f"加载文件夹失败: {str(e)}", exc_info=True)
            return []
    
    def set_selected_files(self, file_paths: List[str]):
        """Set the currently selected files.
        
        Args:
            file_paths: List of selected file paths
        """
        self.selected_files = file_paths
        logger.debug(f"已选择 {len(self.selected_files)} 个文件")
    
    def get_files(self) -> List[Tuple[str, str, str, str, str]]:
        """Get all loaded files.
        
        Returns:
            List of file metadata tuples (name, size_str, file_type, status, file_path)
        """
        return self.files
    
    def get_selected_files(self) -> List[str]:
        """Get currently selected files.
        
        Returns:
            List of selected file paths
        """
        return self.selected_files
    
    def get_file_info(self, file_path: str) -> Optional[Tuple[str, str, str, str, str]]:
        """Get information about a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File metadata tuple (name, size_str, file_type, status, file_path) or None if not found
        """
        for file_info in self.files:
            if file_info[4] == file_path:
                return file_info
        return None
    
    def update_file_status(self, file_path: str, status: str):
        """Update the status of a file.
        
        Args:
            file_path: Path to the file
            status: New status string
        """
        for i, file_info in enumerate(self.files):
            if file_info[4] == file_path:
                # 创建新的元组，更新状态
                self.files[i] = (file_info[0], file_info[1], file_info[2], status, file_info[4])
                logger.debug(f"已更新文件状态: {file_path} -> {status}")
                break
    
    def add_supported_extension(self, extension: str):
        """Add a new supported file extension.
        
        Args:
            extension: File extension to add (including dot, e.g. '.wav')
        """
        if not extension.startswith('.'):
            extension = f'.{extension}'
        self.audio_extensions.add(extension.lower())
        logger.debug(f"已添加支持的文件类型: {extension}")
    
    def remove_supported_extension(self, extension: str):
        """Remove a supported file extension.
        
        Args:
            extension: File extension to remove (including dot, e.g. '.wav')
        """
        if not extension.startswith('.'):
            extension = f'.{extension}'
        if extension.lower() in self.audio_extensions:
            self.audio_extensions.remove(extension.lower())
            logger.debug(f"已移除支持的文件类型: {extension}")
    
    def get_supported_extensions(self) -> Set[str]:
        """Get all supported file extensions.
        
        Returns:
            Set of supported file extensions
        """
        return self.audio_extensions
    
    def _format_size(self, size: int) -> str:
        """Format file size for display.
        
        Args:
            size: File size in bytes
            
        Returns:
            Formatted size string
        """
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB" 