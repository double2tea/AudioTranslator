"""
分类选择对话框模块

此模块提供了CategorySelectionDialog类，用于显示分类选择对话框。
主要功能包括：
1. 显示分类层级结构
2. 提供分类搜索功能
3. 允许用户选择分类
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Dict, List, Any, Optional, Union
import platform

# 设置日志记录器
logger = logging.getLogger(__name__)

class CategorySelectionDialog:
    """
    分类选择对话框
    
    提供分类选择界面，包含搜索、分类树和高级选项。
    """
    
    # 深色主题配色
    COLORS = {
        'bg_dark': '#1E1E1E',      # 主背景色
        'bg_light': '#2D2D2D',     # 次要背景
        'fg': '#FFFFFF',           # 主文本色
        'fg_dim': '#AAAAAA',       # 次要文本
        'accent': '#007ACC',       # 强调色
        'border': '#3D3D3D',       # 边框色
        'hover': '#3D3D3D',        # 悬停色
        'selected': '#094771'      # 选中色
    }
    
    def __init__(self, parent, categories: List[Dict[str, Any]], 
                 files: List[str], initial_selection: str = None):
        """
        初始化分类选择对话框
        
        Args:
            parent: 父窗口
            categories: 分类列表，UI格式
            files: 要分类的文件列表
            initial_selection: 初始选中的分类ID
        """
        self.parent = parent
        self.categories = categories
        self.files = files
        self.initial_selection = initial_selection
        
        # 初始化结果
        self.result = None
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("选择分类")
        self.dialog.geometry("600x500")
        self.dialog.minsize(500, 400)
        self.dialog.configure(bg=self.COLORS['bg_dark'])
        
        # 设置模态对话框
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 设置图标
        try:
            self.dialog.iconbitmap('assets/icon.ico')
        except:
            pass
            
        # 设置关闭事件
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
        # 创建UI
        self.create_widgets()
        
        # 填充分类树
        self.populate_category_tree()
        
        # 如果有指定的初始选择，则选中它
        if self.initial_selection:
            self.select_initial_category()
            
    def create_widgets(self):
        """创建对话框UI组件"""
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 文件信息标签
        if len(self.files) == 1:
            file_label_text = f"选择文件 '{self.files[0].split('/')[-1]}' 的分类:"
        else:
            file_label_text = f"选择 {len(self.files)} 个文件的分类:"
            
        file_label = ttk.Label(main_frame, text=file_label_text, padding=(0, 0, 0, 10))
        file_label.pack(fill=tk.X)
        
        # 搜索框架
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        search_label = ttk.Label(search_frame, text="搜索:")
        search_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        search_button = ttk.Button(search_frame, text="搜索", command=self.on_search)
        search_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # 创建树形视图和滚动条框架
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建垂直滚动条
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建水平滚动条
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 创建树形视图
        self.tree = ttk.Treeview(
            tree_frame,
            columns=('id', 'name_en'),
            show='tree headings',
            selectmode='browse',
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )
        
        # 配置滚动条
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # 配置列
        self.tree.column('#0', width=40)  # 树形结构列
        self.tree.column('id', width=100)
        self.tree.column('name_en', width=150)
        
        # 配置标题
        self.tree.heading('id', text='ID')
        self.tree.heading('name_en', text='名称(英文)')
        
        # 放置树形视图
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 设置树形视图选择事件
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        
        # 创建详情框架
        details_frame = ttk.LabelFrame(main_frame, text="分类详情", padding=10)
        details_frame.pack(fill=tk.X, pady=(0, 10))
        
        # ID标签
        id_frame = ttk.Frame(details_frame)
        id_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(id_frame, text="ID:").pack(side=tk.LEFT, padx=(0, 5))
        self.id_var = tk.StringVar()
        ttk.Label(id_frame, textvariable=self.id_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 中文名标签
        name_zh_frame = ttk.Frame(details_frame)
        name_zh_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(name_zh_frame, text="中文名:").pack(side=tk.LEFT, padx=(0, 5))
        self.name_zh_var = tk.StringVar()
        ttk.Label(name_zh_frame, textvariable=self.name_zh_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 英文名标签
        name_en_frame = ttk.Frame(details_frame)
        name_en_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(name_en_frame, text="英文名:").pack(side=tk.LEFT, padx=(0, 5))
        self.name_en_var = tk.StringVar()
        ttk.Label(name_en_frame, textvariable=self.name_en_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 同义词标签
        synonyms_frame = ttk.Frame(details_frame)
        synonyms_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(synonyms_frame, text="同义词:").pack(side=tk.LEFT, padx=(0, 5), anchor='n')
        self.synonyms_var = tk.StringVar()
        ttk.Label(synonyms_frame, textvariable=self.synonyms_var, wraplength=350).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        
        # 高级选项框架
        advanced_frame = ttk.LabelFrame(main_frame, text="高级选项", padding=10)
        advanced_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 使用子分类选项
        self.use_subcategory_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            advanced_frame, 
            text="创建子分类文件夹",
            variable=self.use_subcategory_var
        ).pack(anchor=tk.W)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # 取消按钮
        cancel_btn = ttk.Button(button_frame, text="取消", command=self.on_cancel)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        # 确认按钮
        self.confirm_btn = ttk.Button(
            button_frame, 
            text="确认", 
            command=self.on_confirm,
            state=tk.DISABLED
        )
        self.confirm_btn.pack(side=tk.RIGHT, padx=5)
        
    def populate_category_tree(self, search_term: str = None):
        """
        填充分类树
        
        Args:
            search_term: 搜索关键词
        """
        # 清空树
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # 如果有搜索关键词，过滤分类
        displayed_categories = self.categories
        if search_term:
            displayed_categories = [cat for cat in self.categories if 
                                   search_term.lower() in cat['name_zh'].lower() or
                                   search_term.lower() in cat['name_en'].lower() or
                                   search_term.lower() in cat['id'].lower()]
            
        # 创建一个字典，记录已创建的父节点
        created_nodes = {}
        
        # 首先添加顶级分类
        for category in displayed_categories:
            cat_id = category['id']
            
            # 如果有父分类，检查是否需要创建父节点
            parent_id = category.get('parent_id', '')
            
            # 如果是顶级分类或者搜索模式
            if not parent_id or search_term:
                # 直接添加到根节点
                tree_id = self.tree.insert(
                    '', 
                    'end', 
                    iid=cat_id,
                    text='',
                    values=(cat_id, category['name_en'])
                )
                created_nodes[cat_id] = tree_id
            else:
                # 如果父节点不存在，可能是因为排序问题，先创建一个占位符
                if parent_id not in created_nodes:
                    # 查找父分类信息
                    parent_info = next((c for c in self.categories if c['id'] == parent_id), None)
                    
                    if parent_info:
                        parent_tree_id = self.tree.insert(
                            '', 
                            'end', 
                            iid=parent_id,
                            text='',
                            values=(parent_id, parent_info['name_en'])
                        )
                        created_nodes[parent_id] = parent_tree_id
                    else:
                        # 如果找不到父分类信息，添加到根节点
                        tree_id = self.tree.insert(
                            '', 
                            'end', 
                            iid=cat_id,
                            text='',
                            values=(cat_id, category['name_en'])
                        )
                        created_nodes[cat_id] = tree_id
                        continue
                
                # 添加作为子节点
                tree_id = self.tree.insert(
                    created_nodes[parent_id], 
                    'end', 
                    iid=cat_id,
                    text='',
                    values=(cat_id, category['name_en'])
                )
                created_nodes[cat_id] = tree_id
                
        # 展开所有节点
        for item in self.tree.get_children():
            self.tree.item(item, open=True)
            
    def select_initial_category(self):
        """选中初始分类"""
        if not self.initial_selection:
            return
            
        # 尝试选中指定的分类
        try:
            self.tree.selection_set(self.initial_selection)
            self.tree.see(self.initial_selection)
            self.update_category_details(self.initial_selection)
            self.confirm_btn.config(state=tk.NORMAL)
        except:
            logger.warning(f"无法选中初始分类: {self.initial_selection}")
    
    def update_category_details(self, cat_id: str):
        """
        更新分类详情显示
        
        Args:
            cat_id: 分类ID
        """
        # 查找选中的分类
        category = next((c for c in self.categories if c['id'] == cat_id), None)
        
        if not category:
            # 清空详情
            self.id_var.set("")
            self.name_zh_var.set("")
            self.name_en_var.set("")
            self.synonyms_var.set("")
            return
            
        # 更新详情显示
        self.id_var.set(category['id'])
        self.name_zh_var.set(category['name_zh'])
        self.name_en_var.set(category['name_en'])
        
        # 构建同义词字符串
        synonyms = []
        if 'synonyms_zh' in category and category['synonyms_zh']:
            synonyms.extend(category['synonyms_zh'])
        if 'synonyms_en' in category and category['synonyms_en']:
            synonyms.extend(category['synonyms_en'])
            
        self.synonyms_var.set(", ".join(synonyms))
        
        # 启用确认按钮
        self.confirm_btn.config(state=tk.NORMAL)
    
    def on_tree_select(self, event):
        """
        树形视图选择事件处理
        
        Args:
            event: 事件对象
        """
        selected = self.tree.selection()
        if not selected:
            return
            
        # 获取选中的分类ID
        cat_id = selected[0]
        
        # 更新详情显示
        self.update_category_details(cat_id)
    
    def on_search(self):
        """搜索按钮事件处理"""
        search_term = self.search_var.get().strip()
        self.populate_category_tree(search_term)
    
    def on_confirm(self):
        """确认按钮事件处理"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请选择一个分类")
            return
            
        # 获取选中的分类ID
        cat_id = selected[0]
        
        # 创建结果字典
        self.result = {
            'category_id': cat_id,
            'use_subcategory': self.use_subcategory_var.get()
        }
        
        # 关闭对话框
        self.dialog.destroy()
    
    def on_cancel(self):
        """取消按钮事件处理"""
        self.result = None
        self.dialog.destroy()
    
    def show(self) -> Optional[Dict[str, Any]]:
        """
        显示对话框并返回结果
        
        Returns:
            用户选择的分类信息，取消则返回None
        """
        # 使对话框居中
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # 等待对话框关闭
        self.parent.wait_window(self.dialog)
        
        return self.result 