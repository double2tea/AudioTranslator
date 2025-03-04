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

from ...managers.file_manager import FileManager
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
        current_directory: 当前显示的目录
        selected_files: 当前选中的文件列表
    """
    
    def __init__(self, parent: tk.Widget, file_manager: Optional[FileManager] = None):
        """
        初始化文件管理面板
        
        Args:
            parent: 父级窗口部件
            file_manager: 文件管理器实例，如果为None则创建新实例
        """
        # 先保存file_manager，因为我们需要在super().__init__之前定义它
        self.file_manager = file_manager
        
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
        
        # 滚动条
        y_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        
        x_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal")
        x_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # 创建树形视图
        columns = ("filename", "translated_name", "size", "type", "status")
        self.file_tree = ttk.Treeview(
            tree_frame, 
            columns=columns,
            show="headings",
            selectmode="extended",
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set
        )
        
        # 设置滚动条
        y_scrollbar.config(command=self.file_tree.yview)
        x_scrollbar.config(command=self.file_tree.xview)
        
        # 设置列标题和宽度
        self.file_tree.heading("filename", text="文件名", anchor="w")
        self.file_tree.heading("translated_name", text="翻译结果", anchor="w")
        self.file_tree.heading("size", text="大小", anchor="w")
        self.file_tree.heading("type", text="类型", anchor="w")
        self.file_tree.heading("status", text="状态", anchor="w")
        
        self.file_tree.column("filename", width=200, minwidth=100)
        self.file_tree.column("translated_name", width=200, minwidth=100)
        self.file_tree.column("size", width=70, minwidth=70)
        self.file_tree.column("type", width=50, minwidth=50)
        self.file_tree.column("status", width=80, minwidth=80)
        
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
        """绑定UI事件"""
        # 文件树选择事件
        self.file_tree.bind("<<TreeviewSelect>>", self._on_file_selected)
        
        # 文件树双击事件
        self.file_tree.bind("<Double-1>", self._on_file_double_click)
        
        # 文件树右键菜单
        self.file_tree.bind("<Button-3>", self._show_file_context_menu)
        
        # 列头点击事件 - 用于排序
        for col in ("filename", "translated_name", "size", "type", "status"):
            self.file_tree.heading(col, command=lambda _col=col: self._sort_files(_col))
        
        # 搜索框变更事件
        self.search_var.trace("w", self._on_search_change)
        
        # 过滤下拉框变更事件
        self.filter_var.trace("w", self._on_filter_change)
        
        # 工具栏按钮事件
        self.refresh_btn.config(command=self._refresh_files)
        
    def _on_file_selected(self, event) -> None:
        """处理文件选择事件"""
        # 获取当前选中的项
        selected_items = self.file_tree.selection()
        
        # 清空之前的选择
        self.selected_files = []
        
        # 添加新选择的文件
        for item_id in selected_items:
            values = self.file_tree.item(item_id, "values")
            if values and len(values) >= 5:  # 确保有足够的值
                file_path = values[4]  # 第5个值是文件路径
                if file_path and file_path not in self.selected_files:
                    self.selected_files.append(file_path)
        
        # 更新状态栏
        self._update_status_bar()
        
        # 根据选择状态启用/禁用按钮
        self._update_ui_state()
    
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
        # 临时实现，后续可以整合进更多的逻辑
        if not self.selected_files:
            return
            
        file_path = self.selected_files[0]
        # 使用系统默认程序打开文件的临时实现
        try:
            import platform
            import subprocess
            
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(('open', file_path))
            else:  # 假定是Linux或其他类Unix系统
                subprocess.call(('xdg-open', file_path))
                
            logger.info(f"已打开文件: {file_path}")
        except Exception as e:
            logger.error(f"打开文件失败: {str(e)}")
            messagebox.showerror("错误", f"无法打开文件: {str(e)}")
    
    def _copy_file_path(self) -> None:
        """复制所选文件的路径到剪贴板"""
        if not self.selected_files:
            return
            
        file_path = self.selected_files[0]
        self.clipboard_clear()
        self.clipboard_append(file_path)
        logger.debug(f"已复制路径到剪贴板: {file_path}")
    
    def _delete_selected_files(self) -> None:
        """删除选中的文件"""
        # 这个方法将在后续阶段实现
        pass
    
    def _translate_selected_files(self) -> None:
        """翻译选中的文件名"""
        # 这个方法将在后续阶段实现
        pass
    
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
        # 文件计数
        file_count = len(self.file_tree.get_children())
        self.status_count_label.config(text=f"文件: {file_count}")
        
        # 选中计数
        selected_count = len(self.selected_files)
        self.status_selected_label.config(text=f"选中: {selected_count}")
        
        # 当前目录
        if self.current_directory:
            dir_text = str(self.current_directory)
            # 如果路径太长，可以截断显示
            if len(dir_text) > 40:
                dir_text = "..." + dir_text[-40:]
            self.status_dir_label.config(text=dir_text)
    
    def load_directory(self, directory: str) -> None:
        """
        加载指定目录中的文件
        
        Args:
            directory: 要加载的目录路径
        """
        if not directory or not os.path.isdir(directory):
            messagebox.showwarning("警告", f"无效的目录: {directory}")
            return
        
        # 更新当前目录
        self.current_directory = directory
        
        # 清空文件树
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # 更新状态栏目录信息
        self.status_dir_label.config(text=f"目录: {os.path.basename(directory)}")
        
        # 显示加载提示
        self.file_tree.insert("", "end", text="正在加载...", values=("正在加载文件...", "", "", "", ""))
        
        # 使用文件管理器加载目录
        if self.file_manager:
            def on_files_loaded(files):
                # 清空加载提示
                for item in self.file_tree.get_children():
                    self.file_tree.delete(item)
                
                # 向树形视图添加文件
                for file_data in files:
                    # FileManager返回的是元组: (名称、大小、类型、状态、路径)
                    name, size, file_type, status, file_path = file_data
                    
                    # 翻译结果初始为空
                    translated_name = ""
                    
                    self.file_tree.insert(
                        "", "end",
                        values=(
                            name,          # 文件名
                            translated_name,  # 翻译结果
                            size,          # 文件大小
                            file_type,     # 文件类型
                            status,        # 状态
                            file_path      # 完整路径 (不显示但用于内部处理)
                        )
                    )
                
                # 应用列设置
                self._apply_column_settings()
                
                # 更新状态栏
                self._update_status_bar()
                
                logger.info(f"已加载目录: {directory}, 共 {len(files)} 个文件")
            
            # 异步加载文件
            self.file_manager.load_directory(directory, callback=on_files_loaded)
        else:
            messagebox.showerror("错误", "文件管理器未初始化")
            logger.error("文件管理器未初始化，无法加载目录")
    
    def _format_file_size(self, size_in_bytes: int) -> str:
        """格式化文件大小显示"""
        if size_in_bytes < 1024:
            return f"{size_in_bytes} B"
        elif size_in_bytes < 1024 * 1024:
            return f"{size_in_bytes/1024:.1f} KB"
        elif size_in_bytes < 1024 * 1024 * 1024:
            return f"{size_in_bytes/(1024*1024):.1f} MB"
        else:
            return f"{size_in_bytes/(1024*1024*1024):.1f} GB"
    
    def _show_column_settings(self) -> None:
        """显示列设置对话框"""
        # 创建对话框
        dialog = tk.Toplevel(self)
        dialog.title("列显示设置")
        dialog.geometry("300x200")
        dialog.transient(self)  # 设置为模态对话框
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # 创建列表框
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill="both", expand=True)
        
        # 列名和显示名称映射
        column_labels = {
            "filename": "文件名",
            "translated_name": "翻译结果",
            "size": "大小",
            "type": "类型",
            "status": "状态"
        }
        
        # 创建复选框
        for i, (col_id, label) in enumerate(column_labels.items()):
            cb = ttk.Checkbutton(frame, text=label, variable=self.column_visibility[col_id])
            cb.pack(anchor="w", pady=2)
            
            # 如果是必要列，禁用复选框 (文件名和翻译结果是必选的)
            if col_id in ["filename", "translated_name"]:
                cb.config(state="disabled")
        
        # 底部按钮
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill="x", pady=10)
        
        ttk.Button(button_frame, text="确定", command=lambda: self._apply_column_settings(dialog)).pack(side="right", padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side="right")
    
    def _apply_column_settings(self, dialog=None) -> None:
        """应用列设置"""
        # 更新树视图列的显示状态
        for col, var in self.column_visibility.items():
            if var.get():
                # 显示列
                self.file_tree.column(col, width=self.file_tree.column(col)['width'])
            else:
                # 隐藏列 (设置宽度为0)
                self.file_tree.column(col, width=0)
        
        # 关闭对话框（如果有）
        if dialog:
            dialog.destroy()
    
    def _select_all_files(self) -> None:
        """选择所有文件"""
        # 清空当前选择
        self.selected_files = []
        
        # 选择所有可见项
        for item_id in self.file_tree.get_children():
            self.file_tree.selection_add(item_id)
            
            # 获取文件路径并添加到选中列表
            values = self.file_tree.item(item_id, "values")
            if values and len(values) >= 5:  # 确保有足够的值
                file_path = values[4]  # 第5个值是文件路径
                if file_path and file_path not in self.selected_files:
                    self.selected_files.append(file_path)
        
        # 更新UI状态
        self._update_ui_state()
        self._update_status_bar()
    
    def _invert_selection(self) -> None:
        """反转选择状态"""
        # 获取所有项
        all_items = self.file_tree.get_children()
        
        # 获取当前选中的项
        selected_items = self.file_tree.selection()
        
        # 清空当前选择
        self.file_tree.selection_remove(*all_items)
        self.selected_files = []
        
        # 选择之前未选中的项
        for item_id in all_items:
            if item_id not in selected_items:
                self.file_tree.selection_add(item_id)
                
                # 获取文件路径并添加到选中列表
                values = self.file_tree.item(item_id, "values")
                if values and len(values) >= 5:
                    file_path = values[4]
                    if file_path and file_path not in self.selected_files:
                        self.selected_files.append(file_path)
        
        # 更新UI状态
        self._update_ui_state()
        self._update_status_bar()
    
    def _deselect_all(self) -> None:
        """取消所有选择"""
        # 清空树视图选择
        for item_id in self.file_tree.selection():
            self.file_tree.selection_remove(item_id)
        
        # 清空选中文件列表
        self.selected_files = []
        
        # 更新UI状态
        self._update_ui_state()
        self._update_status_bar()

    def get_selected_files(self) -> List[str]:
        """
        获取当前选中的文件列表
        
        Returns:
            包含所有选中文件路径的列表
        """
        return self.selected_files.copy()  # 返回副本以防止外部修改 