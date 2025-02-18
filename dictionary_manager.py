# dictionary_manager.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
import json
import csv
import os
from datetime import datetime
from theme_manager import ThemeManager
import sys

class SimpleTranslationStore:
    def __init__(self):
        self.translations = []

    def add_translation(self, source, target):
        self.translations.append({
            'source': source,
            'target': target,
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

    def get_all_translations(self):
        return self.translations

    def delete_translation(self, source):
        self.translations = [t for t in self.translations if t['source'] != source]

class DictionaryManagerWindow:
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

    def __init__(self, parent=None, translation_database=None):
        self.parent = parent
        self.translation_database = translation_database or SimpleTranslationStore()
        self.status_var = tk.StringVar(value="就绪")
        self.setup_window()
        self.create_widgets()
        self.load_dictionary()

    def setup_window(self):
        """创建并配置窗口"""
        self.window = tk.Toplevel(self.parent)
        
        # 设置 macOS 窗口样式
        if sys.platform == 'darwin':
            try:
                # 设置为模态对话框
                self.window.transient(self.parent)
                self.window.grab_set()
                
                # 移除窗口样式设置，使用系统默认样式
                
                # 绑定关闭事件
                self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
                self.window.bind('<Escape>', lambda e: self.on_closing())
                
                # 禁用调整大小
                self.window.resizable(False, False)
            except Exception as e:
                logging.warning(f"设置 macOS 窗口样式失败: {e}")
        
        self.window.title("词库管理")
        self.window.geometry("800x600")
        self.window.minsize(600, 400)
        
        # 使用 ThemeManager 设置主题
        ThemeManager.setup_dialog_theme(self.window)

    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        self.main_frame = ttk.Frame(self.window, padding=15)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 工具栏
        toolbar = ttk.Frame(self.main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(toolbar, text="导入", command=self.import_dictionary).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="导出", command=self.export_dictionary).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="删除选中", command=self.delete_selected).pack(side=tk.LEFT, padx=5)

        # 词库列表
        list_frame = ttk.Frame(self.main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("原文", "译文", "更新时间")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=200)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 状态栏
        status_bar = ttk.Label(self.main_frame, textvariable=self.status_var)
        status_bar.pack(fill=tk.X, pady=(10, 0))

    def load_dictionary(self):
        """加载词库数据"""
        try:
            # 清空现有数据
            for item in self.tree.get_children():
                self.tree.delete(item)

            # 加载数据
            translations = self.translation_database.get_all_translations()
            for trans in translations:
                self.tree.insert("", "end", values=(
                    trans['source'],
                    trans['target'],
                    trans['updated_at']
                ))

            self.status_var.set(f"已加载 {len(translations)} 个条目")

        except Exception as e:
            logging.error(f"加载词库失败: {e}")
            messagebox.showerror("错误", f"加载词库失败: {str(e)}")

    def delete_selected(self):
        """删除选中的条目"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要删除的条目")
            return

        if not messagebox.askyesno("确认", "确定要删除选中的条目吗？"):
            return

        try:
            for item in selected:
                values = self.tree.item(item)['values']
                self.translation_database.delete_translation(values[0])

            self.load_dictionary()
            self.status_var.set(f"已删除 {len(selected)} 个条目")

        except Exception as e:
            logging.error(f"删除条目失败: {e}")
            messagebox.showerror("错误", f"删除条目失败: {str(e)}")

    def import_dictionary(self):
        """导入词库"""
        file_path = filedialog.askopenfilename(
            title="选择词库文件",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # 跳过表头

                count = 0
                for row in reader:
                    if len(row) >= 2:
                        self.translation_database.add_translation(row[0], row[1])
                        count += 1

            self.load_dictionary()
            self.status_var.set(f"成功导入 {count} 个条目")

        except Exception as e:
            logging.error(f"导入词库失败: {e}")
            messagebox.showerror("错误", f"导入失败: {str(e)}")

    def export_dictionary(self):
        """导出词库"""
        file_path = filedialog.asksaveasfilename(
            title="保存词库文件",
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )

        if not file_path:
            return

        try:
            translations = self.translation_database.get_all_translations()
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["原文", "译文", "更新时间"])
                for trans in translations:
                    writer.writerow([
                        trans['source'],
                        trans['target'],
                        trans['updated_at']
                    ])

            self.status_var.set(f"成功导出 {len(translations)} 个条目")

        except Exception as e:
            logging.error(f"导出词库失败: {e}")
            messagebox.showerror("错误", f"导出失败: {str(e)}")

    def on_closing(self):
        """处理窗口关闭事件"""
        try:
            # 释放窗口
            self.window.grab_release()
            # 销毁窗口
            self.window.destroy()
        except Exception as e:
            logging.error(f"关闭窗口失败: {e}")
            # 强制销毁
            try:
                self.window.destroy()
            except:
                pass

    def run(self):
        """运行词库管理器"""
        try:
            # 如果是 Toplevel 窗口，等待窗口关闭
            self.window.wait_window()
        except Exception as e:
            logging.error(f"运行词库管理器失败: {e}")
            messagebox.showerror("错误", f"运行词库管理器失败: {e}")

def main():
    """独立运行时的入口点"""
    try:
        logging.basicConfig(level=logging.INFO)
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        app = DictionaryManagerWindow(root)
        root.mainloop()
    except Exception as e:
        logging.error(f"启动词库管理器失败: {e}")
        messagebox.showerror("错误", f"启动词库管理器失败: {e}")

if __name__ == "__main__":
    main()