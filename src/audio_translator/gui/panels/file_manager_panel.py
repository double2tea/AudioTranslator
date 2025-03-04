"""
文件管理面板模块

此模块提供了FileManagerPanel类，用于显示和管理音频文件列表，
并支持翻译结果显示、文件选择和编辑等功能。

主要功能包括:
1. 显示文件列表，包括原文件名和翻译结果
2. 支持单选和多选文件
3. 提供右键菜单和工具栏操作
4. 支持状态显示和统计信息
"""

import os
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Optional, List, Tuple, Union, Callable
from pathlib import Path
import threading
import queue
import time

from ...managers.file_manager import FileManager
from ...services.business.translator_service import TranslatorService
from ...utils.ui_utils import create_tooltip, ScrollableFrame
from ...utils.events import EventManager, Event
from ..base import SimplePanel

# 设置日志记录器
logger = logging.getLogger(__name__)

class FileManagerPanel(SimplePanel):
    """
    文件管理面板
    
    用于显示和管理音频文件列表，包括文件名、翻译结果、类型和状态。
    支持文件选择、右键菜单操作和状态更新。
    
    Attributes:
        file_manager: 文件管理器实例
        translator_service: 翻译服务实例
        current_directory: 当前显示的目录
        selected_files: 当前选中的文件列表
    """
    
    def __init__(self, parent: tk.Widget, file_manager: Optional[FileManager] = None,
                 translator_service: Optional[TranslatorService] = None):
        """
        初始化文件管理面板
        
        Args:
            parent: 父级窗口部件
            file_manager: 文件管理器实例，如果为None则创建新实例
            translator_service: 翻译服务实例，用于翻译文件名
        """
        # 先保存file_manager，因为我们需要在super().__init__之前定义它
        self.file_manager = file_manager
        
        # 保存翻译服务实例
        self.translator_service = translator_service
        
        # 当前目录和选中的文件
        self.current_directory = ""
        self.selected_files = []
        
        # 翻译状态跟踪
        self.translated_count = 0
        
        # 列显示设置
        self.column_visibility = {
            "filename": tk.BooleanVar(value=True),
            "translated_name": tk.BooleanVar(value=True),
            "size": tk.BooleanVar(value=False),  # 默认隐藏
            "type": tk.BooleanVar(value=False),  # 默认隐藏
            "status": tk.BooleanVar(value=True)
        }
        
        # UI 变量
        self.search_var = tk.StringVar()
        self.filter_var = tk.StringVar(value="全部")
        
        # 异步处理控制标志
        self._processing_active = False
        
        # 调用父类初始化方法 - 只传递parent参数
        super().__init__(parent)
        
        # 初始化UI
        self._init_ui()
        
        # 绑定事件处理
        self._bind_events()
        
        # 更新状态栏
        self._update_status_bar()
        
    def _init_ui(self) -> None:
        """初始化用户界面"""
        # 设置panel布局
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)  # 文件树占最大空间
        
        # 创建工具栏
        self._create_toolbar()
        
        # 创建文件树视图
        self._create_file_tree()
        
        # 创建状态栏
        self._create_status_bar()
        
    def _create_toolbar(self) -> None:
        """创建工具栏"""
        # 工具栏框架
        self.toolbar = ttk.Frame(self)
        self.toolbar.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # 刷新按钮
        self.refresh_btn = ttk.Button(self.toolbar, text="刷新", width=8)
        self.refresh_btn.pack(side=tk.LEFT, padx=2)
        create_tooltip(self.refresh_btn, "刷新文件列表")
        
        # 全选按钮
        self.select_all_btn = ttk.Button(self.toolbar, text="全选", width=8, command=self._select_all_files)
        self.select_all_btn.pack(side=tk.LEFT, padx=2)
        create_tooltip(self.select_all_btn, "选择所有文件")
        
        # 反选按钮
        self.invert_select_btn = ttk.Button(self.toolbar, text="反选", width=8, command=self._invert_selection)
        self.invert_select_btn.pack(side=tk.LEFT, padx=2)
        create_tooltip(self.invert_select_btn, "反转选择状态")
        
        # 取消选择按钮
        self.deselect_all_btn = ttk.Button(self.toolbar, text="取消选择", width=8, command=self._deselect_all)
        self.deselect_all_btn.pack(side=tk.LEFT, padx=2)
        create_tooltip(self.deselect_all_btn, "取消所有选择")
        
        # 分隔符
        ttk.Separator(self.toolbar, orient="vertical").pack(side=tk.LEFT, padx=5, fill="y")
        
        # 编辑翻译按钮
        self.edit_btn = ttk.Button(self.toolbar, text="编辑翻译", width=8, state="disabled", command=self._edit_translation)
        self.edit_btn.pack(side=tk.LEFT, padx=2)
        create_tooltip(self.edit_btn, "编辑已选文件的翻译")
        
        # 翻译按钮
        self.translate_btn = ttk.Button(self.toolbar, text="翻译", width=8, state="disabled", command=self._translate_selected_files)
        self.translate_btn.pack(side=tk.LEFT, padx=2)
        create_tooltip(self.translate_btn, "翻译已选中的文件")
        
        # 分隔符
        ttk.Separator(self.toolbar, orient="vertical").pack(side=tk.LEFT, padx=5, fill="y")
        
        # 列显示设置按钮
        self.columns_btn = ttk.Button(self.toolbar, text="列显示", width=8, command=self._show_column_settings)
        self.columns_btn.pack(side=tk.LEFT, padx=2)
        create_tooltip(self.columns_btn, "设置显示的列")
        
        # 右侧区域 - 搜索和过滤
        self.search_frame = ttk.Frame(self.toolbar)
        self.search_frame.pack(side=tk.RIGHT, padx=2)
        
        # 过滤下拉框
        ttk.Label(self.search_frame, text="过滤:").pack(side=tk.LEFT)
        self.filter_combo = ttk.Combobox(
            self.search_frame, 
            textvariable=self.filter_var,
            values=["全部", "未翻译", "已翻译", "翻译中", "翻译失败"],
            width=10,
            state="readonly"
        )
        self.filter_combo.pack(side=tk.LEFT, padx=2)
        
        # 搜索框
        ttk.Label(self.search_frame, text="搜索:").pack(side=tk.LEFT, padx=(5, 0))
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var, width=15)
        self.search_entry.pack(side=tk.LEFT, padx=2)
        
        # 清除搜索按钮
        self.clear_search_btn = ttk.Button(self.search_frame, text="×", width=2, 
                                          command=lambda: self.search_var.set(""))
        self.clear_search_btn.pack(side=tk.LEFT)
        create_tooltip(self.clear_search_btn, "清除搜索")
        
    def _create_file_tree(self) -> None:
        """创建文件树视图"""
        # 容器框架
        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # 创建水平和垂直滚动条
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        vsb.grid(row=0, column=1, sticky="ns")
        
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        hsb.grid(row=1, column=0, sticky="ew")
        
        # 创建树视图
        self.file_tree = ttk.Treeview(
            tree_frame,
            columns=("select", "name", "size", "type", "translated_name", "status"),
            show="headings",
            selectmode="extended",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
        )
        
        # 配置滚动条
        vsb.config(command=self.file_tree.yview)
        hsb.config(command=self.file_tree.xview)
        
        # 配置列标题和宽度
        self.file_tree.heading("select", text="选择")
        self.file_tree.heading("name", text="文件名")
        self.file_tree.heading("size", text="大小")
        self.file_tree.heading("type", text="类型")
        self.file_tree.heading("translated_name", text="翻译名称")
        self.file_tree.heading("status", text="状态")
        
        # 设置列宽度
        self.file_tree.column("select", width=50, minwidth=50)
        self.file_tree.column("name", width=300, minwidth=200)
        self.file_tree.column("size", width=80, minwidth=80)
        self.file_tree.column("type", width=60, minwidth=60)
        self.file_tree.column("translated_name", width=300, minwidth=200)
        self.file_tree.column("status", width=100, minwidth=80)
        
        # 设置标签颜色
        self.file_tree.tag_configure("loading", background="#f0f0f0")
        self.file_tree.tag_configure("selected", background="#CCE8FF")
        self.file_tree.tag_configure("translated", background="#E0FFE0")
        self.file_tree.tag_configure("error", background="#FFE0E0")
        
        # 注意：所有事件绑定都在_bind_events方法中统一处理，这里不再绑定事件
        
        # 放置树形视图
        self.file_tree.grid(row=0, column=0, sticky="nsew")
        
        # 根据当前设置应用列可见性
        for col in self.column_visibility:
            if not self.column_visibility[col].get():
                self.file_tree.column(col, width=0, stretch=False)
        
        # 创建文件树右键菜单
        self._create_file_context_menu()
        
    def _create_file_context_menu(self) -> None:
        """创建文件树的右键菜单"""
        self.file_context_menu = tk.Menu(self, tearoff=0)
        self.file_context_menu.add_command(label="打开", command=self._open_selected_file)
        self.file_context_menu.add_command(label="复制路径", command=self._copy_file_path)
        self.file_context_menu.add_separator()
        self.file_context_menu.add_command(label="翻译", command=self._translate_selected_files, state="disabled")
        self.file_context_menu.add_command(label="编辑翻译", command=self._edit_translation, state="disabled")
        self.file_context_menu.add_separator()
        self.file_context_menu.add_command(label="删除", command=self._delete_selected_files)
    
    def _create_status_bar(self) -> None:
        """创建状态栏"""
        self.status_bar = ttk.Frame(self)
        self.status_bar.grid(row=2, column=0, sticky="ew", padx=5, pady=(0, 5))
        
        # 文件计数标签
        self.status_count_label = ttk.Label(self.status_bar, text="文件: 0")
        self.status_count_label.pack(side=tk.LEFT, padx=5)
        
        # 选择计数标签
        self.status_selected_label = ttk.Label(self.status_bar, text="选中: 0")
        self.status_selected_label.pack(side=tk.LEFT, padx=5)
        
        # 翻译状态标签 - 将在后续阶段添加实现
        self.status_translated_label = ttk.Label(self.status_bar, text="已翻译: 0")
        self.status_translated_label.pack(side=tk.LEFT, padx=5)
        
        # 当前目录标签
        self.status_dir_label = ttk.Label(self.status_bar, text="")
        self.status_dir_label.pack(side=tk.RIGHT, padx=5)
    
    def _bind_events(self) -> None:
        """绑定事件处理函数"""
        # 绑定排序相关事件
        for col in ("name", "size", "type", "translated_name", "status"):
            self.file_tree.heading(col, command=lambda _col=col: self._sort_files(_col))
        
        # 绑定搜索框变化事件
        self.search_var.trace_add("write", self._on_search_change)
        
        # 绑定筛选下拉框变化事件
        self.filter_var.trace_add("write", self._on_filter_change)
        
        # 绑定树视图点击事件 - 这是实现无需修饰键进行多选的关键
        self.file_tree.bind("<Button-1>", self._on_tree_click)
        
        # 文件树选择事件 - 仅用于更新UI状态
        self.file_tree.bind("<<TreeviewSelect>>", self._on_file_selected)
        
        # 文件树双击事件
        self.file_tree.bind("<Double-1>", self._on_file_double_click)
        
        # 文件树右键菜单
        self.file_tree.bind("<Button-3>", self._show_file_context_menu)
        
        # 工具栏按钮事件
        self.refresh_btn.config(command=self._refresh_files)
        
    def _on_file_selected(self, event) -> None:
        """处理文件选择事件"""
        try:
            # 获取当前选中的项
            selected_items = self.file_tree.selection()
            
            # 清空之前的选择
            self.selected_files = []
            
            # 处理所有项的选择状态
            for item_id in selected_items:
                # 从item_id中提取文件ID
                if item_id.startswith("item_"):
                    file_id = item_id[5:]  # 移除'item_'前缀
                    self.selected_files.append(file_id)
                    
                    # 设置选中样式和标记
                    self.file_tree.item(item_id, tags=("file", "selected"))
                    
                    # 更新选择列显示
                    values = list(self.file_tree.item(item_id, "values"))
                    values[0] = "✓"  # 添加选择标记
                    self.file_tree.item(item_id, values=values)
            
            # 清除未选中项的样式
            for item_id in self.file_tree.get_children():
                if item_id not in selected_items:
                    # 移除选中样式
                    self.file_tree.item(item_id, tags=("file",))
                    
                    # 清除选择标记
                    values = list(self.file_tree.item(item_id, "values"))
                    values[0] = ""
                    self.file_tree.item(item_id, values=values)
            
            # 更新状态栏
            self._update_status_bar()
            
            # 更新UI状态
            self._update_ui_state()
            
        except Exception as e:
            logger.error(f"处理文件选择事件时出错: {str(e)}")
    
    def _update_ui_state(self) -> None:
        """根据当前状态更新UI组件状态"""
        has_selected = len(self.selected_files) > 0
        
        # 更新工具栏按钮状态
        self.edit_btn.config(state="normal" if has_selected else "disabled")
        self.translate_btn.config(state="normal" if has_selected else "disabled")
        
        # 更新右键菜单项状态
        if has_selected:
            self.file_context_menu.entryconfig("翻译", state="normal")
            self.file_context_menu.entryconfig("编辑翻译", state="normal")
        else:
            self.file_context_menu.entryconfig("翻译", state="disabled")
            self.file_context_menu.entryconfig("编辑翻译", state="disabled")
    
    def _on_file_double_click(self, event) -> None:
        """处理文件双击事件"""
        self._open_selected_file()
    
    def _open_selected_file(self) -> None:
        """打开选中的文件"""
        # 获取选中文件的路径
        selected_paths = self.get_selected_file_paths()
        
        if not selected_paths:
            return
            
        file_path = selected_paths[0]
        logger.info(f"正在打开文件: {file_path}")
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            messagebox.showerror("错误", f"文件不存在: {file_path}")
            return
            
        # 使用系统默认程序打开文件
        try:
            import platform
            import subprocess
            
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', file_path], check=True)
            else:  # 假定是Linux或其他类Unix系统
                subprocess.run(['xdg-open', file_path], check=True)
                
            logger.info(f"已打开文件: {file_path}")
        except Exception as e:
            logger.error(f"打开文件失败: {str(e)}")
            messagebox.showerror("错误", f"打开文件失败: {str(e)}")
    
    def _copy_file_path(self) -> None:
        """复制选中文件的路径到剪贴板"""
        selected_paths = self.get_selected_file_paths()
        
        if not selected_paths:
            messagebox.showinfo("提示", "请先选择文件")
            return
            
        # 将路径复制到剪贴板
        paths_text = "\n".join(selected_paths)
        self.clipboard_clear()
        self.clipboard_append(paths_text)
        
        # 更新状态
        file_count = len(selected_paths)
        self.update_status(f"已复制 {file_count} 个文件路径到剪贴板")
    
    def _delete_selected_files(self) -> None:
        """删除选中的文件"""
        # 这个方法将在后续阶段实现
        pass
    
    def _translate_selected_files(self) -> None:
        """翻译选中的文件"""
        # 确保有翻译服务
        if not self.translator_service:
            logger.error("翻译服务不可用")
            self.update_status("翻译失败: 翻译服务不可用")
            return
            
        # 初始化翻译计数
        self.translated_count = 0
        total_files = len(self.selected_files)
        
        # 更新状态
        self.update_status(f"正在翻译 {total_files} 个文件...")
        
        # 创建进度对话框
        progress_dialog = tk.Toplevel(self)
        progress_dialog.title("翻译进度")
        progress_dialog.geometry("400x150")
        progress_dialog.transient(self)  # 设置为顶层窗口的子窗口
        progress_dialog.grab_set()  # 模态对话框
        
        # 添加进度标签
        progress_label = ttk.Label(progress_dialog, text="正在准备翻译...")
        progress_label.pack(pady=10)
        
        # 进度条
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(
            progress_dialog, orient="horizontal", length=350, mode="determinate", 
            variable=progress_var
        )
        progress_bar.pack(pady=10, padx=20)
        
        # 取消按钮和状态变量
        self._translation_cancelled = False
        cancel_button = ttk.Button(
            progress_dialog, text="取消", 
            command=lambda: self._cancel_translation()
        )
        cancel_button.pack(pady=10)
        
        def cancel_translation():
            self._translation_cancelled = True
            progress_label.config(text="正在取消翻译...")
            cancel_button.config(state="disabled")
            
        def update_progress(i, file_id, result):
            if self._translation_cancelled:
                progress_dialog.destroy()
                self.update_status("翻译已取消")
                return
                
            # 更新进度
            progress = (i + 1) / total_files * 100
            progress_var.set(progress)
            
            # 更新标签
            file_name = self.file_manager.get_file_property(file_id, "name")
            progress_label.config(text=f"正在翻译 ({i+1}/{total_files}): {file_name}")
            
            # 更新树视图中的翻译结果
            if result and 'translated_name' in result:
                translated_name = result['translated_name']
                # 更新文件管理器中的翻译结果
                self.file_manager.update_file_property(file_id, "translated_name", translated_name)
                
                # 更新树视图
                for item_id in self.file_tree.get_children():
                    if self.file_tree.item(item_id, 'values')[0] == file_id:
                        values = list(self.file_tree.item(item_id, 'values'))
                        # 更新translated_name列
                        values[4] = translated_name  # 假设translated_name是第5列 (索引4)
                        self.file_tree.item(item_id, values=values)
                        break
                
                # 增加翻译计数
                self.translated_count += 1
            
            # 如果是最后一个文件
            if i == total_files - 1:
                progress_dialog.destroy()
                self.update_status(f"翻译完成: {self.translated_count}/{total_files} 个文件已翻译")
                self._update_status_bar()  # 更新状态栏
            
        # 创建一个线程来执行翻译任务
        def translate_thread():
            try:
                for i, file_id in enumerate(self.selected_files):
                    if self._translation_cancelled:
                        break
                        
                    # 获取文件信息
                    file_name = self.file_manager.get_file_property(file_id, "name")
                    file_path = self.file_manager.get_file_property(file_id, "path")
                    
                    # 翻译文件名
                    result = self.translator_service.translate_filename(file_name, file_path)
                    
                    # 在主线程中更新UI
                    self.after(10, lambda i=i, file_id=file_id, result=result: update_progress(i, file_id, result))
                    
                    # 添加短暂延迟以避免API速率限制
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f"翻译过程中发生错误: {str(e)}")
                # 在主线程中处理错误
                self.after(10, lambda: messagebox.showerror("翻译错误", f"翻译过程中发生错误: {str(e)}"))
                self.after(10, lambda: progress_dialog.destroy())
        
        # 启动翻译线程
        import threading
        import time
        translation_thread = threading.Thread(target=translate_thread)
        translation_thread.daemon = True
        translation_thread.start()
    
    def _edit_translation(self) -> None:
        """编辑已翻译的文件名"""
        # 这个方法将在后续阶段实现
        pass
    
    def _show_file_context_menu(self, event) -> None:
        """
        显示文件右键菜单
        
        Args:
            event: 右键点击事件
        """
        # 确保在右键点击项上显示菜单
        item = self.file_tree.identify_row(event.y)
        if item:
            # 如果点击的是新项，更新选择
            if item not in self.file_tree.selection():
                self.file_tree.selection_set(item)
                self._on_file_selected(None)  # 手动触发选择事件
            
            # 显示上下文菜单
            self.file_context_menu.post(event.x_root, event.y_root)
    
    def _refresh_files(self) -> None:
        """刷新文件列表"""
        if self.current_directory and self.file_manager:
            self.load_directory(self.current_directory)
    
    def _sort_files(self, column) -> None:
        """
        按列排序文件
        
        Args:
            column: 要排序的列名
        """
        # 这个方法将在后续阶段实现
        pass
    
    def _on_search_change(self, *args) -> None:
        """处理搜索框变更事件"""
        # 这个方法将在后续阶段实现
        pass
    
    def _on_filter_change(self, *args) -> None:
        """处理过滤选择变更事件"""
        # 这个方法将在后续阶段实现
        pass
    
    def _update_status_bar(self) -> None:
        """更新状态栏信息"""
        # 目录信息
        if self.current_directory:
            self.status_dir_label.config(text=str(self.current_directory))
        else:
            self.status_dir_label.config(text="未选择目录")
            
        # 文件计数
        if hasattr(self, "file_manager") and self.file_manager:
            total_files = len(self.file_manager.files)
            self.status_count_label.config(text=f"文件: {total_files}")
        else:
            self.status_count_label.config(text="文件: 0")
            
        # 选中文件计数
        if self.selected_files:
            self.status_selected_label.config(text=f"选中: {len(self.selected_files)}")
        else:
            self.status_selected_label.config(text="选中: 0")
            
        # 翻译计数
        if hasattr(self, "translated_count") and self.translated_count > 0:
            self.status_translated_label.config(text=f"已翻译: {self.translated_count}")
        else:
            self.status_translated_label.config(text="已翻译: 0")
    
    def update_status(self, message: str) -> None:
        """
        更新状态栏消息
        
        Args:
            message: 状态消息
        """
        # 更新状态栏消息标签
        if hasattr(self, "status_message_label") and self.status_message_label:
            self.status_message_label.config(text=message)
        
        # 记录日志
        logger.info(message)
    
    def load_directory(self, directory: str) -> None:
        """加载指定目录中的文件
        
        Args:
            directory: 要加载的目录路径
        """
        # 初始化当前目录
        self.current_directory = directory
        
        # 清空文件树
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # 清空选中文件
        self.selected_files = []
        
        # 显示加载中的提示
        self.file_tree.insert("", "end", values=("", "正在加载...", "", "", "", ""), tags=("loading",))
        
        # 更新状态栏
        self.update_status(f"正在加载目录: {directory}")
        
        # 使用文件管理器加载文件
        self.file_manager.load_directory(directory, self.on_files_loaded)
    
    def on_files_loaded(self, files):
        """文件加载完成后的回调
        
        Args:
            files: 加载的文件列表
        """
        # 清空当前树视图
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # 添加文件到树视图
        self._insert_files_to_tree(files)
        
        # 更新状态栏
        self.update_status(f"已加载 {len(files)} 个文件")
        self._update_status_bar()
        
        # 应用列设置
        self._apply_column_settings()
        
        # 记录日志
        logger.info(f"已加载 {len(files)} 个文件")

    def _insert_files_to_tree(self, files):
        """将文件插入到树视图中
        
        Args:
            files: 文件列表
        """
        for file_info in files:
            # 解包文件信息
            file_id, name, size, file_type, translated_name, status, file_path = file_info
            
            # 添加到树视图 - 选择列应为空，将file_id存储在iid中
            item_id = self.file_tree.insert(
                "", "end", 
                iid=f"item_{file_id}",  # 使用唯一ID作为树项ID
                values=("", name, size, file_type, translated_name, status),  # 选择列为空
                tags=("file",)
            )
    
    def _show_column_settings(self) -> None:
        """显示列设置对话框"""
        # 创建对话框
        dialog = tk.Toplevel(self)
        dialog.title("列显示设置")
        dialog.geometry("300x250")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.focus_set()
        
        # 添加说明标签
        ttk.Label(dialog, text="选择要显示的列：", padding=10).pack(anchor="w")
        
        # 添加列选择复选框
        column_names = {
            "select": "选择",
            "name": "文件名",
            "size": "大小",
            "type": "类型",
            "translated_name": "翻译名称",
            "status": "状态"
        }
        
        # 确保必选列不能取消选择
        required_columns = ["select", "name", "status"]
        
        # 创建复选框
        checkboxes = {}
        for col, label in column_names.items():
            var = tk.BooleanVar(value=True)
            
            # 如果列已经存在于当前设置中，则使用当前值
            if col in self.column_visibility:
                var.set(self.column_visibility[col].get())
            
            # 创建复选框
            cb = ttk.Checkbutton(dialog, text=label, variable=var)
            cb.pack(anchor="w", padx=20, pady=3)
            checkboxes[col] = var
            
            # 如果是必选列，则禁用复选框
            if col in required_columns:
                cb.config(state="disabled")
                var.set(True)
        
        # 按钮框架
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, pady=10)
        
        # 确定按钮
        apply_btn = ttk.Button(
            btn_frame, 
            text="确定", 
            command=lambda: self._apply_column_settings(dialog, checkboxes)
        )
        apply_btn.pack(side=tk.RIGHT, padx=10)
        
        # 取消按钮
        cancel_btn = ttk.Button(
            btn_frame, 
            text="取消", 
            command=dialog.destroy
        )
        cancel_btn.pack(side=tk.RIGHT, padx=5)
    
    def _apply_column_settings(self, dialog=None, new_settings=None) -> None:
        """应用列显示设置"""
        # 如果提供了新设置，则更新当前的列可见性设置
        if new_settings:
            self.column_visibility = new_settings
        
        # 应用列可见性设置到树形视图
        column_names = {
            "select": "选择",
            "name": "文件名",
            "size": "大小",
            "type": "类型",
            "translated_name": "翻译名称",
            "status": "状态"
        }
        
        for col in column_names:
            if col in self.column_visibility:
                if self.column_visibility[col].get():
                    # 获取原始宽度
                    if col == "select":
                        self.file_tree.column(col, width=50, stretch=False, minwidth=50)
                    elif col == "size":
                        self.file_tree.column(col, width=80, stretch=True, minwidth=80)
                    elif col == "type":
                        self.file_tree.column(col, width=60, stretch=True, minwidth=60)
                    elif col == "status":
                        self.file_tree.column(col, width=100, stretch=True, minwidth=80)
                    elif col == "translated_name":
                        self.file_tree.column(col, width=300, stretch=True, minwidth=200)
                    else:  # name
                        self.file_tree.column(col, width=300, stretch=True, minwidth=200)
                else:
                    # 隐藏列
                    self.file_tree.column(col, width=0, stretch=False)
        
        # 关闭对话框（如果有）
        if dialog:
            dialog.destroy()
    
    def _select_all_files(self) -> None:
        """选择所有文件"""
        all_items = self.file_tree.get_children()
        
        if not all_items:
            return
            
        # 检查是否已经全选
        current_selected = self.file_tree.selection()
        if len(current_selected) == len(all_items):
            # 检查是否所有项都有选择标记
            all_selected = True
            for item_id in all_items:
                values = self.file_tree.item(item_id, "values")
                if values[0] != "✓":
                    all_selected = False
                    break
                    
            if all_selected:
                # 已经全选，无需执行
                logger.debug("所有文件已经选中，无需再次执行全选")
                return
        
        # 为了防止在处理过程中触发选择事件，先关闭选择模式
        self.file_tree.config(selectmode='none')
        
        # 定义处理函数
        def process_item(item_id, values):
            # 更新选择标记
            if len(values) >= 1:
                # 如果已经选中，不需要修改
                if values[0] == "✓":
                    return False, values
                
                values[0] = "✓"  # 更新选择标记
                return True, values
            return False, values
        
        # 收集文件ID
        new_selected_files = []
        for item_id in all_items:
            # 从item_id中提取文件ID
            if item_id.startswith("item_"):
                file_id = item_id[5:]  # 移除'item_'前缀
                if file_id and file_id not in new_selected_files:
                    new_selected_files.append(file_id)
        
        # 更新选中文件列表
        self.selected_files = new_selected_files
        
        # 标记所有项为选中状态
        for item_id in all_items:
            # 更新视觉样式
            self.file_tree.item(item_id, tags=("file", "selected"))
            
            # 更新选择列显示
            values = list(self.file_tree.item(item_id, "values"))
            values[0] = "✓"  # 添加选择标记
            self.file_tree.item(item_id, values=values)
            
            # 添加到选择集合
            self.file_tree.selection_add(item_id)
        
        # 恢复选择模式
        self.file_tree.config(selectmode='extended')
        
        # 更新状态栏
        self._update_status_bar()
        
        # 更新UI状态
        self._update_ui_state()
    
    def _invert_selection(self) -> None:
        """反转选择状态"""
        all_items = self.file_tree.get_children()
        selected_items = set(self.file_tree.selection())
        
        if not all_items:
            return
            
        # 为了防止在处理过程中触发选择事件，先关闭选择模式
        self.file_tree.config(selectmode='none')
        
        # 清空当前选择，避免触发选择事件
        self.file_tree.selection_remove(*all_items)
        
        # 要选择的项目列表
        items_to_select = []
        new_selected_files = []
        
        # 预先收集要选择的项目和文件ID
        for item_id in all_items:
            # 判断是否需要反转选择状态
            was_selected = item_id in selected_items
            should_select = not was_selected
            
            # 获取当前值和更新状态
            values = list(self.file_tree.item(item_id, "values"))
            is_checked = values[0] == "✓" if values and len(values) >= 1 else False
            
            # 如果当前值的状态和树视图选择状态不一致，以值的状态为准
            if is_checked != was_selected:
                should_select = not is_checked
            
            # 更新选择标记
            if should_select:
                values[0] = "✓"
                
                # 提取文件ID并添加到新的选择列表
                if item_id.startswith("item_"):
                    file_id = item_id[5:]  # 移除'item_'前缀
                    if file_id and file_id not in new_selected_files:
                        new_selected_files.append(file_id)
                        
                # 添加到待选择列表
                items_to_select.append(item_id)
                
                # 设置选中样式
                self.file_tree.item(item_id, tags=("file", "selected"))
            else:
                values[0] = ""
                # 清除选中样式
                self.file_tree.item(item_id, tags=("file",))
            
            # 更新树项值
            self.file_tree.item(item_id, values=values)
        
        # 更新选择状态
        if items_to_select:
            self.file_tree.selection_add(*items_to_select)
        
        # 更新选中文件列表
        self.selected_files = new_selected_files
        
        # 恢复选择模式
        self.file_tree.config(selectmode='extended')
        
        # 更新状态栏
        self._update_status_bar()
        
        # 更新UI状态
        self._update_ui_state()
    
    def _deselect_all(self) -> None:
        """取消选择所有文件"""
        # 获取所有项
        all_items = self.file_tree.get_children()
        
        if not all_items:
            return
            
        # 检查是否已经全部取消选择
        if not self.selected_files and not self.file_tree.selection():
            logger.debug("没有选中的文件，无需执行取消选择")
            return
        
        # 为了防止在处理过程中触发选择事件，先关闭选择模式
        self.file_tree.config(selectmode='none')
        
        # 清空选中文件列表
        self.selected_files = []
        
        # 取消所有选择
        self.file_tree.selection_remove(*all_items)
        
        # 重置所有项的选择标记和样式
        for item_id in all_items:
            # 清除选择标记
            values = list(self.file_tree.item(item_id, "values"))
            if len(values) >= 1:
                values[0] = ""  # 清除选择标记
                self.file_tree.item(item_id, values=values)
                
            # 清除选中样式
            self.file_tree.item(item_id, tags=("file",))
        
        # 恢复选择模式
        self.file_tree.config(selectmode='extended')
        
        # 更新状态栏
        self._update_status_bar()
        
        # 更新UI状态
        self._update_ui_state()

    def _process_items_async(self, items: List[Any], process_func: Callable[[Any], bool],
                         title: str = "处理中", description: str = "正在处理项目...", 
                         batch_size: int = 20, finish_callback: Optional[Callable[[Dict[Any, bool]], None]] = None) -> None:
        """
        异步批量处理项目，显示进度对话框，支持取消操作
        
        Args:
            items: 要处理的项目列表
            process_func: 处理单个项目的函数，接收一个项目参数，返回布尔值表示成功或失败
            title: 进度对话框标题
            description: 进度对话框描述
            batch_size: 每批处理的项目数量
            finish_callback: 处理完成后的回调函数，接收处理结果字典
        """
        if not items:
            return
        
        # 进度对话框类
        class ProgressDialog(tk.Toplevel):
            """进度对话框，支持取消操作"""
            
            def __init__(self, parent, title="处理中", description="请稍候...", 
                        value=0, maximum=100, cancelable=True):
                super().__init__(parent)
                
                self.title(title)
                self.resizable(False, False)
                self.transient(parent)
                self.grab_set()
                
                self.cancel_requested = False
                
                # 居中显示
                window_width, window_height = 300, 120
                position_x = parent.winfo_rootx() + (parent.winfo_width() - window_width) // 2
                position_y = parent.winfo_rooty() + (parent.winfo_height() - window_height) // 2
                self.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
                
                # 创建界面元素
                self.frame = ttk.Frame(self, padding=10)
                self.frame.pack(fill=tk.BOTH, expand=True)
                
                self.description_label = ttk.Label(self.frame, text=description)
                self.description_label.pack(fill=tk.X, pady=(0, 10))
                
                self.progress_var = tk.IntVar(value=value)
                self.maximum = maximum
                
                self.progress_bar = ttk.Progressbar(
                    self.frame, 
                    orient=tk.HORIZONTAL, 
                    length=280, 
                    mode='determinate',
                    variable=self.progress_var,
                    maximum=maximum
                )
                self.progress_bar.pack(fill=tk.X, pady=(0, 10))
                
                self.progress_text = ttk.Label(self.frame, text=self._get_progress_text())
                self.progress_text.pack(fill=tk.X)
                
                if cancelable:
                    self.cancel_button = ttk.Button(self.frame, text="取消", command=self._cancel)
                    self.cancel_button.pack(pady=(10, 0))
                
                # 禁止关闭按钮
                self.protocol("WM_DELETE_WINDOW", lambda: None)
            
            def _get_progress_text(self):
                """获取进度文本"""
                percentage = int((self.progress_var.get() / self.maximum) * 100) if self.maximum > 0 else 0
                return f"{self.progress_var.get()}/{self.maximum} ({percentage}%)"
            
            def update(self, value=None, description=None):
                """更新进度对话框"""
                if value is not None:
                    self.progress_var.set(value)
                    self.progress_text.config(text=self._get_progress_text())
                
                if description is not None:
                    self.description_label.config(text=description)
            
            def _cancel(self):
                """请求取消操作"""
                self.cancel_requested = True
                if hasattr(self, 'cancel_button'):
                    self.cancel_button.config(text="正在取消...", state=tk.DISABLED)
            
            def show(self):
                """显示对话框"""
                self.deiconify()
                self.lift()
                self.focus_force()
                self.update_idletasks()
            
            def close(self):
                """关闭对话框"""
                self.grab_release()
                self.destroy()
        
        # 创建进度对话框
        progress_dialog = ProgressDialog(
            self, 
            title=title,
            description=description,
            value=0,
            maximum=len(items),
            cancelable=True
        )
        
        # 存储处理结果
        results: Dict[Any, bool] = {}
        processed_count = 0
        cancel_requested = False
        progress_dialog.show()
        
        def update_progress():
            """更新进度对话框"""
            nonlocal processed_count
            progress_dialog.update(
                value=processed_count,
                description=f"{description} ({processed_count}/{len(items)})"
            )
        
        def check_cancel():
            """检查是否请求取消"""
            nonlocal cancel_requested
            if progress_dialog.cancel_requested:
                cancel_requested = True
                return True
            return False
        
        def process_batch():
            """处理一批项目"""
            nonlocal processed_count, cancel_requested
            
            start_index = processed_count
            end_index = min(start_index + batch_size, len(items))
            
            for i in range(start_index, end_index):
                if check_cancel():
                    break
                    
                item = items[i]
                try:
                    result = process_func(item)
                    results[item] = result
                except Exception as e:
                    logger.error(f"处理项目时出错: {str(e)}")
                    results[item] = False
                
                processed_count += 1
                
                # 在主线程中更新进度
                self.after(0, update_progress)
            
            # 继续处理下一批或完成
            if processed_count < len(items) and not cancel_requested:
                self.after(10, process_batch)  # 稍微延迟，让UI有机会更新
            else:
                # 完成处理
                finish_processing()
        
        def finish_processing():
            """完成处理，关闭进度对话框，执行回调"""
            progress_dialog.close()
            
            if cancel_requested:
                self.update_status(f"操作已取消: 已处理 {processed_count}/{len(items)} 项")
            else:
                success_count = sum(1 for result in results.values() if result)
                self.update_status(f"操作完成: {success_count} 成功, {len(results) - success_count} 失败")
            
            # 执行完成回调
            if finish_callback is not None:
                finish_callback(results)
        
        # 启动第一批处理
        self.after(50, process_batch)

    def get_selected_files(self) -> List[str]:
        """
        获取当前选中的文件ID列表
        
        Returns:
            包含所有选中文件ID的列表
        """
        return self.selected_files.copy()  # 返回副本以防止外部修改
    
    def get_selected_file_paths(self) -> List[str]:
        """
        获取当前选中的文件路径列表
        
        Returns:
            包含所有选中文件路径的列表
        """
        if not self.selected_files or not self.file_manager:
            return []
            
        paths = []
        for file_id in self.selected_files:
            path = self.file_manager.get_file_property(file_id, "path")
            if path:
                paths.append(path)
        
        return paths

    def _on_tree_click(self, event) -> None:
        """处理树视图点击事件，特别是点击选择列的情况"""
        try:
            # 获取点击的区域和列
            region = self.file_tree.identify_region(event.x, event.y)
            column = self.file_tree.identify_column(event.x)
            item = self.file_tree.identify_row(event.y)
            
            # 只处理有效的点击
            if not item:
                return
                
            # 检查是否按住了Command/Ctrl键（多选修饰符）
            is_multi_select = (event.state & 0x0004) != 0  # Ctrl key on Windows/Linux
            if event.state & 0x0008:  # Command key on macOS
                is_multi_select = True
                
            # 如果点击选择列，切换选择状态
            if column == "#1" and region == "cell":  # #1 表示第一列 (select)
                # 无需使用修饰键，直接切换选择状态
                current_values = self.file_tree.item(item, "values")
                is_selected = current_values[0] == "✓" if len(current_values) > 0 else False
                
                # 切换选择状态，始终保留现有选择
                self._toggle_item_selection(item, add_to_selection=True)
                
                # 阻止默认的 Treeview 选择行为
                return "break"
            
            # 对于其他列的点击，允许直接多选
            elif region in ["tree", "cell"]:
                # 获取树项的值
                values = self.file_tree.item(item, "values")
                is_selected = values[0] == "✓" if len(values) > 0 else False
                
                # 切换选择状态，始终保留现有选择
                if is_selected:
                    # 如果已选中，取消选择
                    self._toggle_item_selection(item, add_to_selection=True)
                else:
                    # 如果未选中，添加到选择
                    self._toggle_item_selection(item, add_to_selection=True)
                
                # 阻止默认行为
                return "break"
                
        except Exception as e:
            logger.error(f"处理树视图点击时出错: {str(e)}")

    def _toggle_item_selection(self, item_id, add_to_selection=True) -> None:
        """
        切换单个项目的选择状态
        
        Args:
            item_id: 要切换选择状态的项ID
            add_to_selection: 是否将项添加到当前选择中，或者替换当前选择
        """
        try:
            # 从item_id中提取文件ID
            if item_id.startswith("item_"):
                file_id = item_id[5:]  # 移除'item_'前缀
            else:
                # 如果是旧格式或特殊条目，尝试从values获取
                values = list(self.file_tree.item(item_id, "values"))
                if not values or len(values) < 2:  # 需要至少有名称列
                    return
                
                # 获取文件名，尝试查找对应的文件ID
                name = values[1]
                if not name or name == "正在加载...":
                    return
                    
                # 查找匹配的文件ID
                found = False
                for file_info in self.file_manager.files:
                    if len(file_info) >= 2 and file_info[1] == name:
                        file_id = file_info[0]
                        found = True
                        break
                        
                if not found:
                    return
            
            # 如果文件ID为空，则跳过
            if not file_id:
                return
            
            # 检查文件ID是否在已选中列表中
            is_selected = file_id in self.selected_files
            
            # 直接多选模式：add_to_selection始终为True，不清除现有选择
            # 即使设置为False，也不清除其他选择
            
            # 切换选择状态
            if is_selected:  # 已选中，取消选择
                if file_id in self.selected_files:
                    self.selected_files.remove(file_id)
                
                # 从树视图选择中移除
                self.file_tree.selection_remove(item_id)
                
                # 移除选中标签
                self.file_tree.item(item_id, tags=("file",))
                
                # 更新选择列的显示
                values = list(self.file_tree.item(item_id, "values"))
                values[0] = ""  # 清除选择标记
                self.file_tree.item(item_id, values=values)
            else:  # 未选中，选中
                if file_id not in self.selected_files:
                    self.selected_files.append(file_id)
                
                # 添加到现有选择，不管add_to_selection参数如何
                self.file_tree.selection_add(item_id)
                
                # 添加选中标签
                self.file_tree.item(item_id, tags=("file", "selected"))
                
                # 更新选择列的显示
                values = list(self.file_tree.item(item_id, "values"))
                values[0] = "✓"  # 添加选择标记
                self.file_tree.item(item_id, values=values)
            
            # 更新状态栏
            self._update_status_bar()
            
            # 更新UI状态
            self._update_ui_state()
        except Exception as e:
            logger.error(f"切换选择状态时出错: {str(e)}")

    def _on_translate_selected(self) -> None:
        """处理点击翻译选中按钮的事件"""
        # 确保有选中的文件
        if not self.selected_files:
            messagebox.showinfo("提示", "请先选择需要翻译的文件")
            return
            
        # 确保有可用的翻译服务
        if not self.translator_service:
            messagebox.showerror("错误", "翻译服务不可用")
            return
            
        # 翻译选中的文件
        self._translate_selected_files()
        
    def _cancel_translation(self) -> None:
        """取消翻译操作"""
        self._translation_cancelled = True

    def _on_open_directory(self) -> None:
        """处理点击打开目录按钮的事件"""
        # 这个方法将在后续阶段实现
        pass

    def _on_batch_rename(self) -> None:
        """处理点击批量重命名按钮的事件"""
        # 这个方法将在后续阶段实现
        pass

    def _on_edit_categories(self) -> None:
        """处理点击编辑分类按钮的事件"""
        # 这个方法将在后续阶段实现
        pass 