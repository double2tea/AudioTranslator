"""
自动分类对话框模块

此模块提供了自动分类文件的对话框，用于批量处理文件分类。
主要功能：
1. 显示文件分类预览
2. 允许用户确认或修改分类结果
3. 批量处理文件分类操作
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import threading
import time

# 设置日志记录器
logger = logging.getLogger(__name__)

class AutoCategorizeDialog:
    """
    自动分类对话框
    
    显示文件分类预览，并允许用户修改和确认分类结果。
    支持批量处理文件分类操作。
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
    
    def __init__(self, parent: tk.Tk, files: List[str], 
                 category_service, base_path: str):
        """
        初始化自动分类对话框
        
        Args:
            parent: 父窗口
            files: 要分类的文件列表
            category_service: 分类服务
            base_path: 目标基础路径
        """
        self.parent = parent
        self.files = files
        self.category_service = category_service
        self.base_path = base_path
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("自动分类")
        self.dialog.geometry("800x600")
        self.dialog.minsize(700, 500)
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
        
        # 初始化结果变量
        self.result = None
        
        # 文件分类结果
        self.file_categories = {}
        
        # 创建UI
        self.create_widgets()
        
        # 预分析文件
        self.analyze_files()
        
    def create_widgets(self):
        """创建UI组件"""
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 消息标签
        label = ttk.Label(
            main_frame, 
            text=f"即将自动分类 {len(self.files)} 个文件，请预览并确认分类结果",
            padding=(0, 0, 0, 10)
        )
        label.pack(fill=tk.X)
        
        # 创建Treeview
        columns = ('filename', 'category_id', 'category_name')
        self.tree = ttk.Treeview(main_frame, columns=columns, show='headings')
        
        # 设置列标题
        self.tree.heading('filename', text='文件名')
        self.tree.heading('category_id', text='分类ID')
        self.tree.heading('category_name', text='分类名称')
        
        # 设置列宽
        self.tree.column('filename', width=300)
        self.tree.column('category_id', width=100)
        self.tree.column('category_name', width=200)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 添加滚动条
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 进度条
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            main_frame, 
            orient=tk.HORIZONTAL, 
            mode='determinate',
            variable=self.progress_var
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        # 状态标签
        self.status_var = tk.StringVar(value="准备分析...")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.pack(fill=tk.X, pady=(0, 10))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # 取消按钮
        cancel_btn = ttk.Button(button_frame, text="取消", command=self.on_cancel)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        # 确认按钮
        self.confirm_btn = ttk.Button(
            button_frame, 
            text="确认并分类", 
            command=self.on_confirm,
            state=tk.DISABLED
        )
        self.confirm_btn.pack(side=tk.RIGHT, padx=5)
        
        # 修改分类按钮
        change_btn = ttk.Button(
            button_frame, 
            text="修改选中项分类", 
            command=self.on_change_category
        )
        change_btn.pack(side=tk.RIGHT, padx=5)
        
    def analyze_files(self):
        """预分析文件分类"""
        # 创建分析线程
        self.analysis_thread = threading.Thread(target=self._analyze_files_thread)
        self.analysis_thread.daemon = True
        self.analysis_thread.start()
        
    def _analyze_files_thread(self):
        """文件分析线程"""
        try:
            total_files = len(self.files)
            
            for i, file_path in enumerate(self.files):
                # 更新进度
                progress = (i / total_files) * 100
                self.progress_var.set(progress)
                
                # 更新状态
                filename = os.path.basename(file_path)
                self.status_var.set(f"正在分析: {filename}")
                
                # 猜测分类
                cat_id = self.category_service.guess_category(filename)
                
                # 获取分类信息
                category = self.category_service.get_category(cat_id)
                
                if category:
                    cat_name = category.get_display_name("zh")
                    
                    # 获取文件命名字段
                    naming_fields = self.category_service.get_naming_fields(filename, cat_id)
                    
                    # 存储分类结果
                    self.file_categories[file_path] = {
                        'cat_id': cat_id,
                        'cat_name': cat_name,
                        'naming_fields': naming_fields
                    }
                    
                    # 添加到树形视图
                    self.tree.insert(
                        '', 
                        'end', 
                        values=(filename, cat_id, cat_name)
                    )
                else:
                    # 如果找不到分类，使用默认分类
                    self.file_categories[file_path] = {
                        'cat_id': 'OTHER',
                        'cat_name': '其他',
                        'naming_fields': {}
                    }
                    
                    # 添加到树形视图
                    self.tree.insert(
                        '', 
                        'end', 
                        values=(filename, 'OTHER', '其他')
                    )
                
                # 短暂延迟，避免UI卡顿
                time.sleep(0.01)
            
            # 完成分析
            self.progress_var.set(100)
            self.status_var.set(f"分析完成，共 {total_files} 个文件")
            
            # 启用确认按钮
            self.confirm_btn.config(state=tk.NORMAL)
            
        except Exception as e:
            logger.error(f"分析文件时出错: {e}")
            self.status_var.set(f"分析出错: {e}")
    
    def on_change_category(self):
        """修改选中项的分类"""
        # 获取选中项
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选择要修改分类的文件")
            return
            
        # 获取选中的文件名
        selected_item = self.tree.item(selected[0])
        values = selected_item['values']
        filename = values[0]
        
        # 查找对应的文件路径
        file_path = None
        for path in self.files:
            if os.path.basename(path) == filename:
                file_path = path
                break
                
        if not file_path:
            messagebox.showerror("错误", "找不到选中的文件")
            return
            
        # 获取当前的分类信息
        current_cat = self.file_categories.get(file_path, {})
        current_cat_id = current_cat.get('cat_id', 'OTHER')
        
        # 获取所有分类
        categories = self.category_service.get_categories_for_ui()
        
        # 创建分类选择对话框
        from ..dialogs.category_selection_dialog import CategorySelectionDialog
        dialog = CategorySelectionDialog(
            self.dialog,
            categories=categories,
            files=[file_path],
            initial_selection=current_cat_id
        )
        
        # 显示对话框
        result = dialog.show()
        if not result:
            # 用户取消了选择
            return
            
        # 获取新的分类ID
        new_cat_id = result.get('category_id', 'OTHER')
        
        # 获取新的分类信息
        category = self.category_service.get_category(new_cat_id)
        if not category:
            messagebox.showerror("错误", f"找不到ID为 {new_cat_id} 的分类")
            return
            
        # 更新分类信息
        new_cat_name = category.get_display_name("zh")
        
        # 获取文件命名字段
        naming_fields = self.category_service.get_naming_fields(filename, new_cat_id)
        
        # 更新存储的分类结果
        self.file_categories[file_path] = {
            'cat_id': new_cat_id,
            'cat_name': new_cat_name,
            'naming_fields': naming_fields
        }
        
        # 更新树形视图
        self.tree.item(selected[0], values=(filename, new_cat_id, new_cat_name))
        
    def on_confirm(self):
        """确认分类操作"""
        # 禁用按钮，防止重复点击
        self.confirm_btn.config(state=tk.DISABLED)
        
        # 创建处理线程
        process_thread = threading.Thread(target=self._process_files_thread)
        process_thread.daemon = True
        process_thread.start()
        
    def _process_files_thread(self):
        """文件处理线程"""
        try:
            # 重置进度
            self.progress_var.set(0)
            
            # 执行分类
            processed_files = []
            total_files = len(self.files)
            
            for i, file_path in enumerate(self.files):
                # 更新进度
                progress = (i / total_files) * 100
                self.progress_var.set(progress)
                
                # 更新状态
                filename = os.path.basename(file_path)
                self.status_var.set(f"正在处理: {filename}")
                
                # 获取分类信息
                category_info = self.file_categories.get(file_path, {})
                cat_id = category_info.get('cat_id', 'OTHER')
                
                try:
                    # 移动文件到分类目录
                    target_path = self.category_service.move_file_to_category(
                        file_path, 
                        cat_id, 
                        self.base_path
                    )
                    
                    if target_path:
                        processed_files.append(target_path)
                        logger.info(f"文件已移动: {file_path} -> {target_path}")
                except Exception as e:
                    logger.error(f"移动文件失败 {file_path}: {e}")
                
                # 短暂延迟，避免UI卡顿
                time.sleep(0.01)
            
            # 完成处理
            self.progress_var.set(100)
            self.status_var.set(f"处理完成，共处理 {len(processed_files)}/{total_files} 个文件")
            
            # 延迟关闭对话框
            self.dialog.after(1000, self._close_with_result, processed_files)
            
        except Exception as e:
            logger.error(f"处理文件时出错: {e}")
            self.status_var.set(f"处理出错: {e}")
            # 重新启用确认按钮
            self.confirm_btn.config(state=tk.NORMAL)
    
    def _close_with_result(self, result):
        """设置结果并关闭对话框"""
        self.result = result
        self.dialog.destroy()
    
    def on_cancel(self):
        """取消操作"""
        self.result = None
        self.dialog.destroy()
    
    def show(self) -> Optional[List[str]]:
        """
        显示对话框并返回结果
        
        Returns:
            成功分类的文件列表，如果取消则返回None
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