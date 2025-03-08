import os
import tkinter as tk
from tkinter import ttk, messagebox
import logging
import json
import pkg_resources
from pathlib import Path

from audio_translator.services.business.translation.translation_manager import TranslationManager
from audio_translator.ui.translation_strategy_ui import create_translation_strategy_window

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AudioTranslatorApp:
    """音频翻译器应用程序"""
    
    def __init__(self, root):
        """初始化应用"""
        self.root = root
        self.root.title("音频翻译器")
        self.root.geometry("900x600")
        
        # 加载配置
        self.config = self._load_config()
        
        # 初始化翻译管理器
        self.translation_manager = TranslationManager(self.config)
        self.translation_manager.initialize()
        
        # 创建主界面框架
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建菜单
        self._create_menu()
        
        # 创建主界面
        self._create_main_ui()
    
    def _load_config(self):
        """加载配置"""
        try:
            # 使用基于包的路径
            package_path = Path(pkg_resources.resource_filename('audio_translator', ''))
            config_path = package_path / 'config' / 'strategies' / 'strategies.json'
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"配置文件不存在: {config_path}")
                return {}
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return {}
    
    def _create_menu(self):
        """创建菜单"""
        menubar = tk.Menu(self.root)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="文件", menu=file_menu)
        
        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="翻译策略配置", command=self._open_translation_strategy_window)
        tools_menu.add_command(label="清除缓存", command=self._clear_cache)
        menubar.add_cascade(label="工具", menu=tools_menu)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="关于", command=self._show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)
        
        self.root.config(menu=menubar)
    
    def _create_main_ui(self):
        """创建主界面"""
        # 创建标题
        ttk.Label(self.main_frame, text="音频翻译器", font=("Arial", 16)).pack(pady=10)
        
        # 创建标签页控件
        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建翻译标签页
        translate_frame = ttk.Frame(notebook, padding=10)
        notebook.add(translate_frame, text="翻译")
        self._create_translate_tab(translate_frame)
        
        # 创建文件管理标签页
        files_frame = ttk.Frame(notebook, padding=10)
        notebook.add(files_frame, text="文件管理")
        self._create_files_tab(files_frame)
        
        # 创建设置标签页
        settings_frame = ttk.Frame(notebook, padding=10)
        notebook.add(settings_frame, text="设置")
        self._create_settings_tab(settings_frame)
        
        # 创建状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(side=tk.BOTTOM, fill=tk.X)
    
    def _create_translate_tab(self, parent):
        """创建翻译标签页"""
        # 创建上下分割的框架
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill=tk.BOTH, expand=True)
        
        bottom_frame = ttk.Frame(parent)
        bottom_frame.pack(fill=tk.X, pady=10)
        
        # 在上方框架中创建左右分割
        input_frame = ttk.LabelFrame(top_frame, text="源文本", padding=5)
        input_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        output_frame = ttk.LabelFrame(top_frame, text="翻译结果", padding=5)
        output_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 创建输入文本框
        self.input_text = tk.Text(input_frame, wrap=tk.WORD)
        self.input_text.pack(fill=tk.BOTH, expand=True)
        
        # 创建输出文本框
        self.output_text = tk.Text(output_frame, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        # 创建控制区域
        control_frame = ttk.Frame(bottom_frame)
        control_frame.pack(fill=tk.X)
        
        # 创建翻译策略选择
        ttk.Label(control_frame, text="翻译策略:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.strategy_var = tk.StringVar()
        self.strategy_combo = ttk.Combobox(control_frame, textvariable=self.strategy_var, state="readonly", width=20)
        self.strategy_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self._update_strategy_list()
        
        # 创建源语言和目标语言选择
        ttk.Label(control_frame, text="源语言:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.source_lang_var = tk.StringVar(value="auto")
        self.source_lang_combo = ttk.Combobox(control_frame, textvariable=self.source_lang_var, state="readonly", width=10)
        self.source_lang_combo["values"] = ["auto", "en", "zh", "ja", "fr", "de", "es", "it", "ru"]
        self.source_lang_combo.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(control_frame, text="目标语言:").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.target_lang_var = tk.StringVar(value="zh")
        self.target_lang_combo = ttk.Combobox(control_frame, textvariable=self.target_lang_var, state="readonly", width=10)
        self.target_lang_combo["values"] = ["zh", "en", "ja", "fr", "de", "es", "it", "ru"]
        self.target_lang_combo.grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)
        
        # 创建翻译按钮
        self.translate_button = ttk.Button(control_frame, text="翻译", command=self._translate)
        self.translate_button.grid(row=0, column=6, padx=10, pady=5, sticky=tk.E)
        
        # 创建清空按钮
        self.clear_button = ttk.Button(control_frame, text="清空", command=self._clear_text)
        self.clear_button.grid(row=0, column=7, padx=5, pady=5, sticky=tk.E)
    
    def _create_files_tab(self, parent):
        """创建文件管理标签页"""
        # 先显示一个简单提示
        ttk.Label(parent, text="文件管理功能正在开发中...").pack(pady=50)
    
    def _create_settings_tab(self, parent):
        """创建设置标签页"""
        # 先显示一个简单提示
        ttk.Label(parent, text="设置功能正在开发中...").pack(pady=50)
    
    def _update_strategy_list(self):
        """更新策略列表"""
        strategies = self.translation_manager.get_all_strategies()
        strategy_names = [s["name"] for s in strategies]
        
        self.strategy_combo["values"] = strategy_names
        
        # 选择默认策略
        default_strategy = self.translation_manager.default_strategy
        if default_strategy in strategy_names:
            self.strategy_var.set(default_strategy)
        elif strategy_names:
            self.strategy_var.set(strategy_names[0])
    
    def _translate(self):
        """执行翻译"""
        input_text = self.input_text.get(1.0, tk.END).strip()
        if not input_text:
            messagebox.showwarning("警告", "请输入要翻译的文本")
            return
            
        strategy_name = self.strategy_var.get()
        if not strategy_name:
            messagebox.showwarning("警告", "请先选择一个策略")
            return
            
        source_lang = self.source_lang_var.get()
        target_lang = self.target_lang_var.get()
        
        # 准备上下文
        context = {
            "source_lang": source_lang,
            "target_lang": target_lang
        }
        
        try:
            # 更新状态
            self.status_var.set("正在翻译...")
            self.root.update_idletasks()
            
            # 执行翻译
            translation = self.translation_manager.translate(input_text, strategy_name, context)
            
            # 更新输出文本框
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(tk.END, translation)
            
            # 更新状态
            self.status_var.set("翻译完成")
        except Exception as e:
            messagebox.showerror("错误", f"翻译失败: {e}")
            self.status_var.set("翻译失败")
    
    def _clear_text(self):
        """清空文本框"""
        self.input_text.delete(1.0, tk.END)
        self.output_text.delete(1.0, tk.END)
        self.status_var.set("就绪")
    
    def _open_translation_strategy_window(self):
        """打开翻译策略配置窗口"""
        strategy_window = create_translation_strategy_window(self.translation_manager)
        
        # 确保窗口模态
        strategy_window.transient(self.root)
        strategy_window.grab_set()
        self.root.wait_window(strategy_window)
        
        # 更新策略列表
        self._update_strategy_list()
    
    def _clear_cache(self):
        """清除缓存"""
        try:
            count = self.translation_manager.clear_cache()
            messagebox.showinfo("成功", f"已清除 {count} 个缓存条目")
        except Exception as e:
            messagebox.showerror("错误", f"清除缓存失败: {e}")
    
    def _show_about(self):
        """显示关于对话框"""
        messagebox.showinfo(
            "关于音频翻译器",
            "音频翻译器 v1.0\n\n"
            "支持多种翻译策略和音频处理功能\n"
            "©2024 CherryHQ. 保留所有权利。"
        )


def main():
    """应用程序入口"""
    try:
        root = tk.Tk()
        app = AudioTranslatorApp(root)
        root.mainloop()
    except Exception as e:
        logger.error(f"应用程序启动失败: {e}")
        messagebox.showerror("错误", f"应用程序启动失败: {e}")


if __name__ == "__main__":
    main() 