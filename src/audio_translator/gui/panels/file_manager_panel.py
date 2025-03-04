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
        columns = ("selection", "filename", "translated_name", "size", "type", "status")
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
        self.file_tree.heading("selection", text="选择", anchor="center")
        self.file_tree.heading("filename", text="文件名", anchor="w")
        self.file_tree.heading("translated_name", text="翻译结果", anchor="w")
        self.file_tree.heading("size", text="大小", anchor="w")
        self.file_tree.heading("type", text="类型", anchor="w")
        self.file_tree.heading("status", text="状态", anchor="w")
        
        self.file_tree.column("selection", width=40, minwidth=40, stretch=False, anchor="center")
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
        
        # 绑定点击选择列事件 - 使用 Button-1 而不是 ButtonRelease-1 以便更早捕获事件
        self.file_tree.bind("<Button-1>", self._on_treeview_click)
        
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
        
        # 重置所有项的选择标记
        for item_id in self.file_tree.get_children():
            values = list(self.file_tree.item(item_id, "values"))
            if len(values) >= 6:  # 确保有足够的值
                file_path = values[5]  # 第6个值是文件路径
                
                # 更新选择标记
                if item_id in selected_items:
                    values[0] = "✓"
                    self.selected_files.append(file_path)
                else:
                    values[0] = ""
                
                # 更新树项的值，但避免无限递归
                self.file_tree.item(item_id, values=values)
        
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
        加载指定目录的文件
        
        Args:
            directory: 要加载的目录路径
        """
        # 保存当前目录
        self.current_directory = Path(directory)
        
        # 清空文件树
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # 清空选中文件
        self.selected_files = []
        
        # 显示加载中提示
        self.file_tree.insert("", "end", text="正在加载...", values=("", "正在加载文件列表...", "", "", "", ""))
        
        # 更新状态栏
        self.status_dir_label.config(text=str(directory))
        self.status_count_label.config(text="文件: 加载中...")
        self.status_selected_label.config(text="选中: 0")
        
        # 异步加载文件
        if self.file_manager:
            self.file_manager.load_directory(
                directory, 
                callback=lambda files: self.after(0, lambda: self.on_files_loaded(files))
            )
        
        def on_files_loaded(files):
            # 清空加载提示
            for item in self.file_tree.get_children():
                self.file_tree.delete(item)
            
            # 批量加载文件数据
            for file_data in files:
                if file_data:
                    name, size, file_type, status, file_path = file_data
                    
                    # 插入文件到树视图 (直接使用FileManager返回的已格式化大小)
                    self.file_tree.insert(
                        "", "end", 
                        values=("", name, "", size, file_type, status, file_path)
                    )
            
            # 更新状态栏
            self._update_status_bar()
            
            # 应用列显示设置
            self._apply_column_settings()
            
            # 日志记录
            logger.info(f"已加载目录: {directory}，共 {len(files)} 个文件")
        
        self.on_files_loaded = on_files_loaded
    
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
            "selection": "选择",
            "filename": "文件名",
            "translated_name": "翻译结果",
            "size": "大小",
            "type": "类型",
            "status": "状态"
        }
        
        # 确保必选列不能取消选择
        required_columns = ["selection", "filename", "status"]
        
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
            "selection": "选择",
            "filename": "文件名",
            "translated_name": "翻译结果",
            "size": "大小",
            "type": "类型",
            "status": "状态"
        }
        
        for col in column_names:
            if col in self.column_visibility:
                if self.column_visibility[col].get():
                    # 获取原始宽度
                    if col == "selection":
                        self.file_tree.column(col, width=40, stretch=False, minwidth=40)
                    elif col == "size":
                        self.file_tree.column(col, width=70, stretch=True, minwidth=70)
                    elif col == "type":
                        self.file_tree.column(col, width=50, stretch=True, minwidth=50)
                    elif col == "status":
                        self.file_tree.column(col, width=80, stretch=True, minwidth=80)
                    else:
                        self.file_tree.column(col, width=200, stretch=True, minwidth=100)
                else:
                    # 隐藏列
                    self.file_tree.column(col, width=0, stretch=False)
        
        # 关闭对话框（如果有）
        if dialog:
            dialog.destroy()
    
    def _select_all_files(self) -> None:
        """选择所有文件"""
        # 获取所有项目ID
        all_items = self.file_tree.get_children()
        
        # 清空当前选择并重置列表
        self.selected_files = []
        
        # 选择所有可见项
        self.file_tree.selection_set(all_items)
        
        # 更新选择标记和收集文件路径
        for item_id in all_items:
            values = list(self.file_tree.item(item_id, "values"))
            if values and len(values) >= 6:
                file_path = values[5]
                values[0] = "✓"  # 更新选择标记
                
                # 更新树项的值
                self.file_tree.item(item_id, values=values)
                
                if file_path and file_path not in self.selected_files:
                    self.selected_files.append(file_path)
        
        # 更新UI状态
        self._update_ui_state()
        self._update_status_bar()
    
    def _invert_selection(self) -> None:
        """反转选择状态"""
        # 获取所有项和当前选中的项
        all_items = self.file_tree.get_children()
        selected_items = set(self.file_tree.selection())
        
        # 准备批量更新
        items_to_select = []
        items_with_new_values = []
        new_selected_files = []
        
        # 关闭树视图重绘以提高性能
        self.file_tree.config(selectmode='none')
        
        # 清空当前选择，避免触发选择事件
        self.file_tree.selection_remove(*all_items)
        
        # 处理所有项
        for item_id in all_items:
            values = list(self.file_tree.item(item_id, "values"))
            if len(values) >= 6:
                file_path = values[5]
                
                # 反转选择状态
                if item_id not in selected_items:
                    items_to_select.append(item_id)
                    values[0] = "✓"  # 更新选择标记
                    if file_path:
                        new_selected_files.append(file_path)
                else:
                    values[0] = ""  # 清除选择标记
                
                # 收集需要更新的项
                items_with_new_values.append((item_id, values))
        
        # 批量更新树项值
        for item_id, values in items_with_new_values:
            self.file_tree.item(item_id, values=values)
        
        # 批量应用选择
        if items_to_select:
            self.file_tree.selection_add(*items_to_select)
        
        # 恢复树视图的选择模式
        self.file_tree.config(selectmode='extended')
        
        # 更新选择列表
        self.selected_files = new_selected_files
        
        # 一次性更新UI状态
        self._update_ui_state()
        self._update_status_bar()
    
    def _deselect_all(self) -> None:
        """取消所有选择"""
        # 清空树视图选择
        for item_id in self.file_tree.selection():
            self.file_tree.selection_remove(item_id)
            
            # 清除选择标记
            values = list(self.file_tree.item(item_id, "values"))
            if len(values) >= 1:
                values[0] = ""
                self.file_tree.item(item_id, values=values)
        
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

    def _on_treeview_click(self, event) -> None:
        """处理树视图点击事件，特别是点击选择列的情况"""
        # 获取点击的区域和列
        region = self.file_tree.identify_region(event.x, event.y)
        column = self.file_tree.identify_column(event.x)
        item = self.file_tree.identify_row(event.y)
        
        # 只有在点击选择列时才进行特殊处理
        if column == "#1" and item and region == "cell":  # #1 表示第一列 (selection)
            # 切换选择状态，不清除其他选择
            if item in self.file_tree.selection():
                self._toggle_item_selection(item, add_to_selection=False)
            else:
                self._toggle_item_selection(item, add_to_selection=True)
            
            # 阻止默认的 Treeview 选择行为
            return "break"
        
        # 对于其他列，保持默认行为

    def _toggle_item_selection(self, item_id, add_to_selection=True) -> None:
        """
        切换单个项目的选择状态
        
        Args:
            item_id: 要切换选择状态的项ID
            add_to_selection: 是否将项添加到当前选择中，或者替换当前选择
        """
        values = list(self.file_tree.item(item_id, "values"))
        if len(values) >= 6:
            file_path = values[5]
            
            # 切换选择状态
            if values[0] == "✓":  # 已选中，取消选择
                values[0] = ""
                if file_path in self.selected_files:
                    self.selected_files.remove(file_path)
                
                # 从树视图选择中移除
                self.file_tree.selection_remove(item_id)
            else:  # 未选中，选中
                values[0] = "✓"
                if file_path and file_path not in self.selected_files:
                    self.selected_files.append(file_path)
                
                # 根据 add_to_selection 参数决定是否保留现有选择
                if not add_to_selection:
                    # 清除其他选择，只选择当前项
                    self.file_tree.selection_set(item_id)
                else:
                    # 添加到当前选择
                    self.file_tree.selection_add(item_id)
            
            # 更新树项的值
            self.file_tree.item(item_id, values=values)
            
            # 更新UI状态
            self._update_ui_state()
            self._update_status_bar() 