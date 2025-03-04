"""
自动分类对话框模块 - 提供音效文件自动分类进度界面

此模块提供了AutoCategorizeDialog类，用于显示自动分类进度对话框。
主要功能包括：
1. 显示分类进度
2. 实时更新分类结果
3. 支持取消操作
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional, Any, Union, Callable
import platform
from pathlib import Path
import logging
import threading
import time

# 设置日志记录器
logger = logging.getLogger(__name__)

class AutoCategorizeDialog:
    """自动分类对话框"""
    
    def __init__(self, parent: tk.Tk, files: List[str], category_manager: Any, 
                base_path: Union[str, Path]):
        """
        初始化自动分类对话框
        
        Args:
            parent: 父窗口对象
            files: 待分类的文件列表
            category_manager: 分类管理器对象
            base_path: 基础路径
        """
        self.parent = parent
        self.files = files
        self.category_manager = category_manager
        
        # 确保base_path是Path对象
        if isinstance(base_path, str):
            self.base_path = Path(base_path)
        else:
            self.base_path = base_path
        
        self.result = []
        self.is_running = False
        self.should_stop = False
        
        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("自动分类进度")
        self.dialog.geometry("600x400")
        self.dialog.minsize(500, 300)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 在macOS上设置透明标题栏
        if platform.system() == 'Darwin':
            self.dialog.tk.call('::tk::unsupported::MacWindowStyle', 'style',
                               self.dialog._w, 'moveableModal', 'closeBox')
        
        # 设置对话框在父窗口中居中
        self.center_dialog()
        
        # 设置网格布局
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=0)  # 标题行
        self.dialog.rowconfigure(1, weight=0)  # 进度条行
        self.dialog.rowconfigure(2, weight=1)  # 结果列表行
        self.dialog.rowconfigure(3, weight=0)  # 按钮行
        
        # 创建UI组件
        self.create_widgets()
        
        # 设置对话框关闭事件
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
    
    def center_dialog(self):
        """将对话框在父窗口中居中显示"""
        self.dialog.update_idletasks()
        
        # 获取父窗口和对话框的尺寸
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        
        dialog_width = self.dialog.winfo_width()
        dialog_height = self.dialog.winfo_height()
        
        # 计算居中位置
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        # 设置对话框位置
        self.dialog.geometry(f"+{x}+{y}")
    
    def create_widgets(self):
        """创建对话框UI组件"""
        # 创建标题标签
        title_frame = ttk.Frame(self.dialog, padding=(10, 10, 10, 5))
        title_frame.grid(row=0, column=0, sticky="ew")
        
        self.status_var = tk.StringVar(value=f"准备分类 {len(self.files)} 个文件...")
        ttk.Label(title_frame, textvariable=self.status_var, font=("", 12, "bold")).pack(side=tk.LEFT)
        
        # 创建进度条
        progress_frame = ttk.Frame(self.dialog, padding=(10, 5, 10, 10))
        progress_frame.grid(row=1, column=0, sticky="ew")
        
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            orient=tk.HORIZONTAL, 
            length=100, 
            mode='determinate',
            variable=self.progress_var
        )
        self.progress_bar.pack(fill=tk.X, expand=True)
        
        # 创建结果列表
        result_frame = ttk.Frame(self.dialog, padding=(10, 5, 10, 10))
        result_frame.grid(row=2, column=0, sticky="nsew")
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建结果列表
        self.result_list = tk.Listbox(
            result_frame,
            yscrollcommand=scrollbar.set,
            font=("", 10),
            selectmode=tk.EXTENDED
        )
        self.result_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 配置滚动条
        scrollbar.config(command=self.result_list.yview)
        
        # 创建按钮区域
        button_frame = ttk.Frame(self.dialog, padding=(10, 5, 10, 10))
        button_frame.grid(row=3, column=0, sticky="ew")
        
        # 创建按钮
        self.cancel_button = ttk.Button(button_frame, text="取消", command=self.cancel)
        self.cancel_button.pack(side=tk.RIGHT)
        
        self.finish_button = ttk.Button(button_frame, text="完成", command=self.finish, state=tk.DISABLED)
        self.finish_button.pack(side=tk.RIGHT, padx=(0, 5))
    
    def start_categorize(self):
        """开始自动分类处理"""
        if not self.files:
            self.status_var.set("没有文件需要分类")
            self.finish_button.config(state=tk.NORMAL)
            return
        
        # 设置状态
        self.is_running = True
        self.should_stop = False
        
        # 创建并启动分类线程
        self.categorize_thread = threading.Thread(target=self._categorize_files)
        self.categorize_thread.daemon = True
        self.categorize_thread.start()
    
    def _categorize_files(self):
        """在后台线程中执行分类处理"""
        total_files = len(self.files)
        processed = 0
        
        # 更新UI
        self.dialog.after(0, lambda: self.status_var.set(f"正在分类 {total_files} 个文件..."))
        
        # 处理每个文件
        for file_path in self.files:
            # 检查是否应该停止
            if self.should_stop:
                break
            
            try:
                # 获取文件名
                file_path = Path(file_path)
                filename = file_path.name
                
                # 猜测分类
                category = self.category_manager.guess_category(filename)
                
                # 移动文件
                moved_files = self.category_manager.move_files_to_category(
                    [str(file_path)], 
                    category, 
                    self.base_path
                )
                
                # 更新结果列表
                if moved_files:
                    moved_path = Path(moved_files[0])
                    cat_name = category.get('Category_zh', '')
                    subcat_name = category.get('subcategory_zh', '')
                    
                    result_text = f"{filename} -> {category.get('CatID', '')}: {cat_name}"
                    if subcat_name:
                        result_text += f" / {subcat_name}"
                    
                    # 添加到结果列表
                    self.dialog.after(0, lambda t=result_text: self.result_list.insert(tk.END, t))
                    
                    # 添加到结果
                    self.result.append(str(moved_path))
                
                # 更新进度
                processed += 1
                progress = (processed / total_files) * 100
                
                # 更新UI
                self.dialog.after(0, lambda p=progress: self.progress_var.set(p))
                self.dialog.after(0, lambda p=processed, t=total_files: 
                                 self.status_var.set(f"已处理: {p}/{t} 文件"))
                
                # 滚动到最新项
                self.dialog.after(0, lambda: self.result_list.see(tk.END))
                
                # 短暂暂停，避免UI冻结
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"分类文件失败 {file_path}: {e}")
                
                # 添加错误信息到结果列表
                error_text = f"错误: {filename} - {str(e)}"
                self.dialog.after(0, lambda t=error_text: self.result_list.insert(tk.END, t))
        
        # 更新UI状态
        self.dialog.after(0, self._on_categorize_complete)
    
    def _on_categorize_complete(self):
        """分类完成后的处理"""
        self.is_running = False
        
        if self.should_stop:
            self.status_var.set("分类已取消")
        else:
            self.status_var.set(f"分类完成，共处理 {len(self.files)} 个文件，成功移动 {len(self.result)} 个文件")
            
        # 启用完成按钮
        self.finish_button.config(state=tk.NORMAL)
        
        # 更改取消按钮为关闭
        self.cancel_button.config(text="关闭")
    
    def cancel(self):
        """取消分类处理"""
        if self.is_running:
            self.should_stop = True
            self.status_var.set("正在取消...")
            self.cancel_button.config(state=tk.DISABLED)
        else:
            self.dialog.destroy()
    
    def finish(self):
        """完成分类处理"""
        self.dialog.destroy()
    
    def show(self) -> List[str]:
        """
        显示对话框并开始分类处理
        
        Returns:
            成功移动的文件路径列表
        """
        # 开始分类处理
        self.dialog.after(100, self.start_categorize)
        
        # 等待对话框关闭
        self.parent.wait_window(self.dialog)
        return self.result 