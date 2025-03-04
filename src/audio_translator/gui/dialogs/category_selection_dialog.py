"""
分类选择对话框模块 - 提供音效文件分类选择界面

此模块提供了CategorySelectionDialog类，用于显示分类选择对话框。
主要功能包括：
1. 显示分类列表
2. 提供分类搜索功能
3. 支持分类选择和确认
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional, Any, Callable
import platform
from pathlib import Path
import logging

# 设置日志记录器
logger = logging.getLogger(__name__)

class CategorySelectionDialog:
    """分类选择对话框"""
    
    def __init__(self, parent: tk.Tk, categories: Dict[str, Any], files: List[str] = None):
        """
        初始化分类选择对话框
        
        Args:
            parent: 父窗口对象
            categories: 分类数据字典
            files: 待分类的文件列表
        """
        self.parent = parent
        self.categories = categories
        self.files = files or []
        self.result = None
        
        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("选择分类")
        self.dialog.geometry("800x600")
        self.dialog.minsize(600, 400)
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
        self.dialog.rowconfigure(0, weight=0)  # 搜索框行
        self.dialog.rowconfigure(1, weight=1)  # 树状视图行
        self.dialog.rowconfigure(2, weight=0)  # 按钮行
        
        # 创建UI组件
        self.create_widgets()
        
        # 填充分类数据
        self.populate_categories()
        
        # 绑定事件
        self.tree.bind("<Double-1>", lambda e: self.confirm_selection())
        self.tree.bind("<Return>", lambda e: self.confirm_selection())
        
        # 设置对话框关闭事件
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
        
        # 设置焦点到搜索框
        self.search_entry.focus_set()
    
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
        # 创建搜索框
        search_frame = ttk.Frame(self.dialog, padding=(10, 10, 10, 5))
        search_frame.grid(row=0, column=0, sticky="ew")
        
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 绑定搜索事件
        self.search_var.trace_add("write", lambda *args: self.search_categories())
        
        # 创建分类树状视图
        tree_frame = ttk.Frame(self.dialog, padding=(10, 5, 10, 10))
        tree_frame.grid(row=1, column=0, sticky="nsew")
        
        # 创建滚动条
        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 创建树状视图
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("catid", "name_zh", "name_en", "subcategory"),
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )
        
        # 设置列标题
        self.tree.heading("catid", text="分类ID")
        self.tree.heading("name_zh", text="中文名称")
        self.tree.heading("name_en", text="英文名称")
        self.tree.heading("subcategory", text="子分类")
        
        # 设置列宽度
        self.tree.column("catid", width=100, minwidth=80)
        self.tree.column("name_zh", width=150, minwidth=100)
        self.tree.column("name_en", width=150, minwidth=100)
        self.tree.column("subcategory", width=200, minwidth=150)
        
        # 配置滚动条
        scrollbar_y.config(command=self.tree.yview)
        scrollbar_x.config(command=self.tree.xview)
        
        # 放置树状视图
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 创建按钮区域
        button_frame = ttk.Frame(self.dialog, padding=(10, 5, 10, 10))
        button_frame.grid(row=2, column=0, sticky="ew")
        
        # 文件信息标签
        if self.files:
            file_info = f"已选择 {len(self.files)} 个文件"
            ttk.Label(button_frame, text=file_info).pack(side=tk.LEFT, padx=(0, 10))
        
        # 创建按钮
        ttk.Button(button_frame, text="取消", command=self.cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="确认", command=self.confirm_selection).pack(side=tk.RIGHT)
    
    def populate_categories(self):
        """填充分类数据到树状视图"""
        # 清空现有数据
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 添加分类数据
        for cat_id, category in self.categories.items():
            values = (
                cat_id,
                category.name_zh,
                category.name_en,
                f"{category.subcategory} ({category.subcategory_zh})" if category.subcategory else ""
            )
            
            self.tree.insert("", tk.END, values=values, tags=(cat_id,))
    
    def search_categories(self):
        """搜索分类"""
        query = self.search_var.get().strip().lower()
        
        # 清空现有数据
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 如果搜索关键词为空，显示所有分类
        if not query:
            self.populate_categories()
            return
        
        # 搜索匹配的分类
        for cat_id, category in self.categories.items():
            # 检查是否匹配
            if (query in cat_id.lower() or
                query in category.name_en.lower() or
                query in category.name_zh.lower() or
                (category.subcategory and query in category.subcategory.lower()) or
                (category.subcategory_zh and query in category.subcategory_zh.lower())):
                
                # 添加匹配的分类
                values = (
                    cat_id,
                    category.name_zh,
                    category.name_en,
                    f"{category.subcategory} ({category.subcategory_zh})" if category.subcategory else ""
                )
                
                self.tree.insert("", tk.END, values=values, tags=(cat_id,))
    
    def confirm_selection(self):
        """确认选择的分类"""
        # 获取选中的项
        selected_item = self.tree.selection()
        
        if not selected_item:
            return
        
        # 获取选中项的分类ID
        cat_id = self.tree.item(selected_item[0], "tags")[0]
        
        # 获取分类信息
        if cat_id in self.categories:
            category = self.categories[cat_id]
            self.result = category.to_dict()
            
            logger.info(f"已选择分类: {cat_id} - {category.name_zh} ({category.name_en})")
            
            # 关闭对话框
            self.dialog.destroy()
    
    def cancel(self):
        """取消选择"""
        self.result = None
        self.dialog.destroy()
    
    def show(self) -> Optional[Dict[str, Any]]:
        """
        显示对话框并等待用户操作
        
        Returns:
            选择的分类信息，如果取消则返回None
        """
        # 等待对话框关闭
        self.parent.wait_window(self.dialog)
        return self.result 