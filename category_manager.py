import os
import logging
import tkinter as tk
from tkinter import ttk
from pathlib import Path
import csv
from theme_manager import ThemeManager
import sys

class CategoryManager:
    """音效文件分类管理器"""
    
    # 深色主题配色
    COLORS = {
        'bg_dark': '#1A1A1A',      # 主背景色
        'bg_light': '#2A2A2A',     # 次要背景色
        'fg': '#FFFFFF',           # 主文本色
        'fg_dim': '#B0B0B0',       # 次要文本色
        'accent': '#0D7377',       # 强调色
        'border': '#333333',       # 边框色
        'hover': '#353535',        # 悬停色
        'selected': '#14445C'      # 选中色
    }
    
    def __init__(self, parent_window):
        self.parent = parent_window
        self.categories = {}
        self.load_categories()
        self.auto_categorize = tk.BooleanVar(value=True)  # 默认启用自动分类
        
    def load_categories(self):
        """从 _categorylist.csv 加载分类数据"""
        try:
            csv_path = Path(__file__).parent / "data" / "_categorylist.csv"
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cat_id = row['CatID']
                    self.categories[cat_id] = {
                        'Category': row['Category'],
                        'Category_zh': row['Category_zh'],
                        'subcategory': row['SubCategory'],
                        'subcategory_zh': row['SubCategory_zh'],
                        'CatID': cat_id,
                        'synonyms': [s.strip() for s in str(row['Synonyms - Comma Separated']).split(',') if s.strip()],
                        'synonyms_zh': [s.strip() for s in str(row['Synonyms_zh']).split('、') if s.strip()]
                    }
        except Exception as e:
            logging.error(f"加载分类数据失败: {str(e)}")
            
    def guess_category(self, filename):
        """智能猜测文件的分类"""
        try:
            # 预处理文件名
            name = Path(filename).stem.lower()
            text = ' '.join(name.split('_'))
            
            # 使用评分系统进行匹配
            best_match = None
            max_matches = 0
            
            for cat_id, cat_info in self.categories.items():
                matches = 0
                
                # 检查英文同义词
                for synonym in cat_info['synonyms']:
                    if synonym.lower().strip() in text:
                        matches += 2
                
                # 检查中文同义词
                for synonym in cat_info['synonyms_zh']:
                    if synonym in text:
                        matches += 2
                
                # 检查分类名和子分类名
                name = cat_info['Category'].lower()
                subcategory = cat_info['subcategory'].lower()
                
                if name and name in text:
                    matches += 3
                if subcategory and subcategory in text:
                    matches += 3
                    
                # 检查CatID
                if cat_id.lower() in text:
                    matches += 4
                
                # 更新最佳匹配
                if matches > max_matches:
                    max_matches = matches
                    best_match = cat_id
            
            # 如果没有找到匹配，返回 Other 分类
            if not best_match or max_matches == 0:
                return {
                    'Category': 'Other',
                    'Category_zh': '其他',
                    'subcategory': 'Manual',
                    'subcategory_zh': '待分类',
                    'CatID': 'Other'
                }
            
            return self.categories[best_match]
            
        except Exception as e:
            logging.error(f"猜测分类失败: {str(e)}")
            # 出错时返回 Other 分类
            return {
                'Category': 'Other',
                'Category_zh': '其他',
                'subcategory': 'Manual',
                'subcategory_zh': '待分类',
                'CatID': 'Other'
            }
    
    def show_category_dialog(self, files):
        """显示分类选择对话框"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("选择音效分类")
        dialog.geometry("800x600")
        dialog.minsize(600, 400)
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # 设置 macOS 窗口样式
        if sys.platform == 'darwin':
            try:
                # 移除窗口样式设置，使用系统默认样式
                dialog.protocol("WM_DELETE_WINDOW", lambda: self._close_dialog(dialog))
                dialog.bind('<Escape>', lambda e: self._close_dialog(dialog))
            except Exception as e:
                logging.warning(f"设置 macOS 窗口样式失败: {e}")
        
        # 使用 ThemeManager 设置主题
        ThemeManager.setup_dialog_theme(dialog)
        
        # 创建主框架
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建分类选择区域
        category_frame = ttk.LabelFrame(
            main_frame,
            text="选择分类",
            padding=10
        )
        category_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建搜索框
        search_frame = ttk.Frame(category_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(
            search_frame,
            text="搜索:"
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        search_var = tk.StringVar()
        search_entry = ttk.Entry(
            search_frame,
            textvariable=search_var
        )
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 创建分类列表
        tree_frame = ttk.Frame(category_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建并配置树形列表
        tree = ttk.Treeview(
            tree_frame,
            columns=("CatID", "中文名", "英文名", "子分类"),
            show="headings",
            selectmode='browse'
        )
        
        # 配置列
        for col, text, width in [
            ("CatID", "分类ID", 100),
            ("中文名", "中文名称", 150),
            ("英文名", "英文名称", 150),
            ("子分类", "子分类", 150)
        ]:
            tree.heading(col, text=text)
            tree.column(col, width=width, anchor='w')
        
        # 添加滚动条
        yscroll = ttk.Scrollbar(
            tree_frame,
            orient=tk.VERTICAL,
            command=tree.yview
        )
        xscroll = ttk.Scrollbar(
            tree_frame,
            orient=tk.HORIZONTAL,
            command=tree.xview
        )
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        
        # 布局
        tree.grid(row=0, column=0, sticky='nsew')
        yscroll.grid(row=0, column=1, sticky='ns')
        xscroll.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        # 填充分类数据
        all_items = []
        for cat_id, info in self.categories.items():
            item = (
                cat_id,
                info['Category_zh'],
                info['Category'],
                info['subcategory_zh']
            )
            all_items.append(item)
            tree.insert("", tk.END, values=item)
            
        # 搜索功能
        def filter_items(*args):
            search_text = search_var.get().lower()
            tree.delete(*tree.get_children())
            for item in all_items:
                if any(search_text in str(value).lower() for value in item):
                    tree.insert("", tk.END, values=item)
                    
        search_var.trace('w', filter_items)
        
        # 创建按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 添加确认和取消按钮
        result = {'category': None}
        
        def on_confirm():
            selection = tree.selection()
            if selection:
                item = tree.item(selection[0])
                cat_id = item['values'][0]
                result['category'] = self.categories[cat_id]
            self._close_dialog(dialog)
        
        def on_cancel():
            self._close_dialog(dialog)
        
        ttk.Button(
            btn_frame,
            text="确认",
            command=on_confirm,
            style='Accent.TButton'
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="取消",
            command=on_cancel
        ).pack(side=tk.RIGHT)
        
        # 设置初始焦点到搜索框
        search_entry.focus_set()
        
        # 等待对话框关闭
        dialog.wait_window()
        return result['category']
    
    def _close_dialog(self, dialog):
        """关闭对话框"""
        try:
            dialog.grab_release()
            dialog.destroy()
        except Exception as e:
            logging.error(f"关闭对话框失败: {e}")
            try:
                dialog.destroy()
            except:
                pass
    
    def create_category_folder(self, base_path, category):
        """创建分类文件夹"""
        if not category:
            return None
            
        folder_name = f"{category['Category']}_{category['Category_zh']}"
        folder_path = Path(base_path) / folder_name
        folder_path.mkdir(exist_ok=True)
        return folder_path
    
    def get_category_by_id(self, cat_id):
        """根据分类ID获取分类信息"""
        return self.categories.get(cat_id)
        
    def move_files_to_category(self, files, base_path):
        """将文件移动到对应的分类文件夹"""
        if not files:
            return []
            
        moved_files = []
        other_files = []  # 存储无法匹配的文件
        
        for file in files:
            try:
                # 智能猜测分类
                category = self.guess_category(file)
                
                # 创建分类文件夹
                folder_path = self.create_category_folder(base_path, category)
                if not folder_path:
                    continue
                    
                # 如果启用了子分类，创建子分类文件夹
                if hasattr(self.parent, 'use_subcategory') and self.parent.use_subcategory.get():
                    if category.get('subcategory') and category.get('subcategory_zh'):
                        sub_folder = folder_path / f"{category['subcategory']}_{category['subcategory_zh']}"
                        sub_folder.mkdir(exist_ok=True)
                        folder_path = sub_folder
                    
                # 移动文件
                source = Path(file)
                target = folder_path / source.name
                
                # 如果目标文件已存在，添加数字后缀
                counter = 1
                while target.exists():
                    stem = target.stem
                    if '_' in stem:
                        base = stem.rsplit('_', 1)[0]
                    else:
                        base = stem
                    target = folder_path / f"{base}_{counter}{target.suffix}"
                    counter += 1
                
                # 移动文件
                source.rename(target)
                moved_files.append(str(target))
                
                # 如果是 Other 分类，记录到待处理列表
                if category['Category'] == 'Other':
                    other_files.append(str(target))
                
            except Exception as e:
                logging.error(f"移动文件失败 {file}: {str(e)}")
                
        # 如果有文件被归类到 Other，显示提示信息
        if other_files:
            tk.messagebox.showinfo(
                "待分类文件提示",
                f"有 {len(other_files)} 个文件无法自动匹配分类，已移动到 Other 文件夹等待手动分类。\n" +
                f"文件位置：{Path(other_files[0]).parent}"
            )
                
        return moved_files
    
    def start_auto_categorize(self, files, base_path):
        """开始自动分类"""
        if not files:
            return []
            
        # 显示进度对话框
        dialog = tk.Toplevel(self.parent)
        dialog.title("自动分类进度")
        dialog.geometry("400x150")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # 设置主题
        ThemeManager.setup_dialog_theme(dialog)
        
        # 创建进度显示
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="正在自动分类...").pack()
        
        progress = ttk.Progressbar(frame, mode='determinate', length=300)
        progress.pack(pady=10)
        
        status_label = ttk.Label(frame, text="")
        status_label.pack()
        
        # 更新进度的函数
        def update_progress(current, total, filename):
            progress['value'] = (current / total) * 100
            status_label['text'] = f"处理: {filename}"
            dialog.update()
        
        # 开始处理文件
        moved_files = []
        total_files = len(files)
        
        try:
            for i, file in enumerate(files, 1):
                # 更新进度
                update_progress(i, total_files, Path(file).name)
                
                # 智能猜测分类
                category = self.guess_category(file)
                if not category:
                    continue
                    
                # 创建分类文件夹
                folder_path = self.create_category_folder(base_path, category)
                if not folder_path:
                    continue
                    
                # 移动文件
                source = Path(file)
                target = folder_path / source.name
                
                # 如果目标文件已存在，添加数字后缀
                counter = 1
                while target.exists():
                    stem = target.stem
                    if '_' in stem:
                        base = stem.rsplit('_', 1)[0]
                    else:
                        base = stem
                    target = folder_path / f"{base}_{counter}{target.suffix}"
                    counter += 1
                
                # 移动文件
                source.rename(target)
                moved_files.append(str(target))
                
        except Exception as e:
            logging.error(f"自动分类失败: {str(e)}")
        finally:
            dialog.destroy()
            
        # 显示结果
        tk.messagebox.showinfo("完成", f"自动分类完成\n成功处理: {len(moved_files)}/{total_files} 个文件")
        
        return moved_files
    
    def get_auto_categorize_var(self):
        """获取自动分类选项变量"""
        return self.auto_categorize 