"""File manager for audio files.

This module provides a file manager class for handling audio files.
It includes functionality for loading files from directories, filtering by file type,
and retrieving file metadata.
"""

import os
import logging
import threading
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Set, Callable, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

# 设置日志记录器
logger = logging.getLogger(__name__)

class FileManager:
    """Manages audio files for the application.
    
    This class handles operations related to audio files:
    - Loading files from directories
    - Filtering files by type
    - Getting file metadata
    - Tracking selected files
    - Batch processing files
    
    Attributes:
        current_directory: Current working directory
        audio_extensions: Set of supported audio file extensions
        files: List of loaded files with metadata
        selected_files: List of currently selected file paths
        sorting_key: Current key for sorting files
        sorting_reverse: Whether sorting is in reverse order
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
        
        # 排序设置
        self.sorting_key = 0  # 默认按文件名排序
        self.sorting_reverse = False
        
        # 文件加载锁
        self._loading_lock = threading.Lock()
        
        # 文件加载回调
        self._loading_callback = None
        
        # 文件缓存
        self._file_cache = {}
        
        # 已终止标志，用于取消异步操作
        self._terminated = False
        
        logger.debug("FileManager initialized")
    
    def load_directory(self, directory: str, callback: Optional[Callable] = None) -> List[Tuple[str, str, str, str, str]]:
        """Load files from a directory.
        
        Args:
            directory: Directory path to load files from
            callback: Optional callback function to report progress
            
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
            self._loading_callback = callback
            
            # 异步加载大型目录
            if callback:
                threading.Thread(target=self._async_load_directory, args=(directory,), daemon=True).start()
                return []
            
            # 同步加载
            return self._load_directory_internal(directory)
            
        except Exception as e:
            logger.error(f"加载文件夹失败: {str(e)}", exc_info=True)
            return []
    
    def _async_load_directory(self, directory: str):
        """Asynchronously load directory contents.
        
        Args:
            directory: Directory path to load files from
        """
        with self._loading_lock:
            files = self._load_directory_internal(directory)
            if self._loading_callback:
                self._loading_callback(files)
    
    def _load_directory_internal(self, directory: str) -> List[Tuple[str, str, str, str, str]]:
        """Internal method to load directory contents.
        
        Args:
            directory: Directory path to load files from
            
        Returns:
            List of file metadata tuples
        """
        loaded_files = []
        
        try:
            # 获取目录中的所有文件
            file_paths = [os.path.join(directory, f) for f in os.listdir(directory) 
                         if os.path.isfile(os.path.join(directory, f))]
            
            # 使用线程池并行处理文件
            with ThreadPoolExecutor(max_workers=min(10, os.cpu_count() or 4)) as executor:
                future_to_path = {executor.submit(self._process_file, file_path): file_path 
                                for file_path in file_paths}
                
                for future in as_completed(future_to_path):
                    result = future.result()
                    if result:
                        loaded_files.append(result)
            
            # 应用当前排序规则
            loaded_files = self._sort_files(loaded_files)
            
            # 更新文件列表
            self.files = loaded_files
            
            logger.info(f"已加载目录: {directory}, 共 {len(self.files)} 个文件")
            return self.files
            
        except Exception as e:
            logger.error(f"内部加载文件夹失败: {str(e)}", exc_info=True)
            return []
    
    def _process_file(self, file_path: str) -> Optional[Tuple[str, str, str, str, str, str]]:
        """Process a single file to extract metadata.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File metadata tuple or None if not a supported audio file
        """
        try:
            # 检查缓存
            if str(file_path) in self._file_cache:
                return self._file_cache[str(file_path)]
                
            # 处理文件信息
            name = os.path.basename(file_path)
            file_type = os.path.splitext(name)[1].lower()
            
            # 检查是否为支持的音频文件
            if file_type not in self.audio_extensions:
                return None
            
            # 获取文件大小
            size = os.path.getsize(file_path)
            size_str = self._format_size(size)
            
            # 为每个文件分配唯一ID
            file_id = str(hash(file_path))
            
            # 添加翻译名称字段，初始为空字符串
            translated_name = ""
            
            # 缓存结果
            result = (file_id, name, size_str, file_type, translated_name, "未处理", file_path)
            self._file_cache[str(file_path)] = result
            
            return result
        except Exception as e:
            logger.debug(f"处理文件失败: {file_path}, 错误: {str(e)}")
            return None
    
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
    
    def get_file_info(self, file_path: str) -> Optional[Tuple[str, str, str, str, str, str]]:
        """Get information about a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File metadata tuple (name, size_str, file_type, status, file_path) or None if not found
        """
        # 从缓存中获取
        if file_path in self._file_cache:
            return self._file_cache[file_path]
            
        # 从文件列表中查找
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
                # 创建新的元组，更新状态，保留翻译结果
                self.files[i] = (file_info[0], file_info[1], file_info[2], 
                               status, file_info[4], file_info[5] if len(file_info) > 5 else "")
                logger.debug(f"已更新文件状态: {file_path} -> {status}")
                break
    
    def update_file_translation(self, file_path: str, translated_name: str) -> bool:
        """
        更新文件的翻译结果
        
        Args:
            file_path: 文件路径
            translated_name: 翻译后的名称
            
        Returns:
            是否更新成功
        """
        # 更新缓存
        for i, file_info in enumerate(self.files):
            if len(file_info) >= 5 and file_info[4] == file_path:
                # 更新翻译名称
                # 检查元组长度
                if len(file_info) >= 6:
                    # 已有翻译字段，创建新元组
                    updated_file_info = (
                        file_info[0],  # name
                        file_info[1],  # size
                        file_info[2],  # type
                        "已翻译",      # status
                        file_info[4],  # path
                        translated_name # translated_name
                    )
                else:
                    # 没有翻译字段，扩展元组
                    updated_file_info = file_info[:4] + ("已翻译", file_info[4], translated_name)
                
                # 更新列表项
                self.files[i] = updated_file_info
                
                # 更新缓存
                self._file_cache[file_path] = updated_file_info
                
                return True
                
        return False
    
    def batch_update_status(self, file_paths: List[str], status: str) -> int:
        """Update the status of multiple files at once.
        
        Args:
            file_paths: List of file paths to update
            status: New status string
            
        Returns:
            Number of files updated
        """
        count = 0
        
        # 创建文件路径到索引的映射以加快查找
        path_to_index = {file_info[4]: i for i, file_info in enumerate(self.files)}
        
        for path in file_paths:
            if path in path_to_index:
                index = path_to_index[path]
                file_info = self.files[index]
                # 更新状态，保留翻译结果
                self.files[index] = (file_info[0], file_info[1], file_info[2], 
                                  status, file_info[4], file_info[5] if len(file_info) > 5 else "")
                count += 1
        
        if count > 0:
            logger.debug(f"批量更新了 {count} 个文件状态为: {status}")
        
        return count
    
    def batch_update_translations(self, file_paths: List[str], translations: List[str]) -> int:
        """批量更新文件的翻译结果
        
        Args:
            file_paths: 要更新的文件路径列表
            translations: 对应的翻译结果列表
            
        Returns:
            更新的文件数量
        """
        if len(file_paths) != len(translations):
            logger.error("文件路径列表和翻译结果列表长度不一致")
            return 0
            
        count = 0
        
        # 创建文件路径到索引的映射以加快查找
        path_to_index = {file_info[4]: i for i, file_info in enumerate(self.files)}
        
        for path, translation in zip(file_paths, translations):
            if path in path_to_index:
                index = path_to_index[path]
                file_info = self.files[index]
                # 更新翻译结果，保留其他字段
                self.files[index] = (file_info[0], file_info[1], file_info[2], 
                                  file_info[3], file_info[4], translation)
                count += 1
        
        if count > 0:
            logger.debug(f"批量更新了 {count} 个文件的翻译结果")
        
        return count
    
    def filter_files(self, file_type: Optional[str] = None, status: Optional[str] = None) -> List[Tuple[str, str, str, str, str]]:
        """Filter files by type and/or status.
        
        Args:
            file_type: File extension to filter by (e.g. '.mp3')
            status: Status string to filter by
            
        Returns:
            Filtered list of file metadata tuples
        """
        result = self.files
        
        if file_type:
            if not file_type.startswith('.'):
                file_type = f'.{file_type}'
            result = [f for f in result if f[2].lower() == file_type.lower()]
        
        if status:
            result = [f for f in result if f[3] == status]
        
        return result
    
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
    
    def set_sorting(self, key_index: int, reverse: bool = False):
        """Set the sorting method for files.
        
        Args:
            key_index: Index to sort by (0=name, 1=size, 2=type, 3=status)
            reverse: Whether to sort in reverse order
        """
        self.sorting_key = key_index
        self.sorting_reverse = reverse
        
        # 重新排序文件列表
        self.files = self._sort_files(self.files)
    
    def _sort_files(self, file_list: List[Tuple[str, str, str, str, str, str]]) -> List[Tuple[str, str, str, str, str, str]]:
        """Sort files according to current sorting settings.
        
        Args:
            file_list: List of file metadata tuples to sort
            
        Returns:
            Sorted list of file metadata tuples
        """
        # 根据不同的排序键进行排序
        if self.sorting_key == 1:  # 按大小排序
            # 将大小字符串转换为数值进行排序
            def size_to_bytes(size_str):
                try:
                    value = float(size_str.split()[0])
                    unit = size_str.split()[1]
                    if unit == "KB":
                        return value * 1024
                    elif unit == "MB":
                        return value * 1024 * 1024
                    else:
                        return value
                except:
                    return 0
            
            return sorted(file_list, key=lambda x: size_to_bytes(x[1]), reverse=self.sorting_reverse)
        else:
            # 其他列直接按字符串排序
            # 处理可能存在的空字符串
            return sorted(file_list, key=lambda x: x[self.sorting_key].lower() if x[self.sorting_key] else "", reverse=self.sorting_reverse)
    
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
    
    def get_file_stats(self) -> Dict[str, int]:
        """Get statistics about loaded files.
        
        Returns:
            Dictionary with file statistics (total, by extension, by status)
        """
        stats = {
            'total': len(self.files),
            'by_extension': {},
            'by_status': {},
            'translated': sum(1 for file_info in self.files if len(file_info) > 5 and file_info[5])  # 统计已翻译文件数量
        }
        
        # 按扩展名统计
        for file_info in self.files:
            ext = file_info[2]
            if ext in stats['by_extension']:
                stats['by_extension'][ext] += 1
            else:
                stats['by_extension'][ext] = 1
        
        # 按状态统计
        for file_info in self.files:
            status = file_info[3]
            if status in stats['by_status']:
                stats['by_status'][status] += 1
            else:
                stats['by_status'][status] = 1
        
        return stats
    
    def get_file_property(self, file_id: str, property_name: str) -> Optional[str]:
        """获取文件的指定属性
        
        Args:
            file_id: 文件ID
            property_name: 属性名称（name, size, type, translated_name, status, path）
            
        Returns:
            属性值，如果不存在则返回None
        """
        try:
            # 定义属性索引映射
            property_map = {
                'id': 0,
                'name': 1,
                'size': 2,
                'type': 3,
                'translated_name': 4,
                'status': 5,
                'path': 6
            }
            
            # 检查属性名是否有效
            if property_name not in property_map:
                logger.error(f"请求的属性名称无效: {property_name}")
                return None
            
            # 找到对应的文件
            for file_info in self.files:
                if file_info[0] == file_id:
                    return file_info[property_map[property_name]]
            
            logger.warning(f"找不到ID为 {file_id} 的文件")
            return None
            
        except Exception as e:
            logger.error(f"获取文件属性失败: {str(e)}")
            return None
    
    def update_file_property(self, file_id: str, property_name: str, value: str) -> bool:
        """更新文件的指定属性
        
        Args:
            file_id: 文件ID
            property_name: 属性名称（name, translated_name, status）
            value: 新的属性值
            
        Returns:
            更新是否成功
        """
        try:
            # 定义可更新的属性索引映射
            property_map = {
                'name': 1,
                'translated_name': 4,
                'status': 5
            }
            
            # 检查属性名是否有效且可更新
            if property_name not in property_map:
                logger.error(f"请求的属性名称无效或不可更新: {property_name}")
                return False
            
            # 更新文件信息
            for i, file_info in enumerate(self.files):
                if file_info[0] == file_id:
                    # 创建一个新的元组，替换指定位置的值
                    new_info = list(file_info)
                    new_info[property_map[property_name]] = value
                    self.files[i] = tuple(new_info)
                    
                    # 更新缓存
                    file_path = file_info[6]
                    self._file_cache[str(file_path)] = tuple(new_info)
                    
                    logger.debug(f"已更新文件 {file_id} 的 {property_name} 为 {value}")
                    return True
            
            logger.warning(f"找不到ID为 {file_id} 的文件")
            return False
            
        except Exception as e:
            logger.error(f"更新文件属性失败: {str(e)}")
            return False 