"""
分类服务使用示例

此示例演示了如何使用优化后的分类服务进行文件分类操作。
包括：
- 初始化分类服务
- 加载分类数据
- 猜测文件分类
- 移动文件到分类目录
- 使用分类管理器进行UI交互
"""

import os
import sys
import tkinter as tk
from pathlib import Path
import logging

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入分类服务
from src.audio_translator.services.business.category import CategoryService
from src.audio_translator.managers.category_manager import CategoryManager

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def setup_example():
    """创建示例环境"""
    # 创建测试目录
    os.makedirs('examples/test_files', exist_ok=True)
    os.makedirs('examples/test_output', exist_ok=True)
    
    # 创建一些测试文件
    test_files = [
        'examples/test_files/explosion_loud_bang.wav',
        'examples/test_files/footsteps_walking_concrete.wav',
        'examples/test_files/rain_heavy_water_dripping.wav',
        'examples/test_files/UI_button_click_soft.wav',
        'examples/test_files/ambient_forest_birds.wav'
    ]
    
    # 创建空文件
    for file_path in test_files:
        with open(file_path, 'w') as f:
            f.write('Test file')
    
    return test_files

def example_basic_usage(test_files):
    """基本用法示例"""
    print("\n=== 基本用法示例 ===")
    
    # 初始化分类服务
    service = CategoryService()
    
    # 初始化服务
    if not service.initialize():
        logger.error("无法初始化分类服务")
        return
    
    # 获取所有分类
    categories = service.get_all_categories()
    print(f"加载了 {len(categories)} 个分类")
    
    # 获取特定分类
    cat_id = 'EXPL'
    explosion_cat = service.get_category(cat_id)
    if explosion_cat:
        print(f"\n获取分类信息: {cat_id}")
        print(f"  - 名称(中): {explosion_cat.name_zh}")
        print(f"  - 名称(英): {explosion_cat.name_en}")
        print(f"  - 同义词(中): {', '.join(explosion_cat.synonyms_zh)}")
    
    # 猜测分类
    print("\n猜测文件分类:")
    for file_path in test_files:
        filename = os.path.basename(file_path)
        cat_id = service.guess_category(filename)
        category = service.get_category(cat_id)
        display_name = category.get_display_name() if category else "未知"
        
        print(f"  - {filename} -> {cat_id}: {display_name}")
    
    # 获取分类字段
    print("\n提取文件名中的分类字段:")
    filename = 'footsteps_walking_concrete.wav'
    cat_id = service.guess_category(filename)
    fields = service.get_naming_fields(filename, cat_id)
    
    print(f"  - 文件: {filename}")
    print(f"  - 分类: {cat_id}")
    print(f"  - 字段:")
    for key, value in fields.items():
        print(f"    * {key}: {value}")
    
    # 创建分类目录
    output_dir = 'examples/test_output'
    print(f"\n在 {output_dir} 创建分类目录:")
    
    if service.create_category_directories(output_dir):
        print("  - 分类目录创建成功")
    else:
        print("  - 分类目录创建失败")
    
    # 移动文件到分类目录
    print("\n移动文件到分类目录:")
    for file_path in test_files:
        filename = os.path.basename(file_path)
        cat_id = service.guess_category(filename)
        
        try:
            target_path = service.move_file_to_category(file_path, cat_id, output_dir)
            if target_path:
                print(f"  - {filename} -> {target_path}")
        except Exception as e:
            print(f"  - 移动失败 {filename}: {e}")
    
    print("\n基本用法示例完成")

def example_ui_integration():
    """UI集成示例"""
    print("\n=== UI集成示例 ===")
    print("启动Tkinter窗口...")
    
    # 创建Tkinter窗口
    root = tk.Tk()
    root.title("分类服务示例")
    root.geometry("600x400")
    
    # 初始化分类服务
    service = CategoryService()
    service.initialize()
    
    # 初始化分类管理器
    manager = CategoryManager(root)
    manager.set_category_service(service)
    
    # 创建UI元素
    frame = tk.Frame(root, padx=20, pady=20)
    frame.pack(fill=tk.BOTH, expand=True)
    
    tk.Label(frame, text="分类服务UI集成示例", font=("", 14, "bold")).pack(pady=(0, 20))
    
    # 创建按钮
    btn_show_dialog = tk.Button(
        frame, 
        text="打开分类选择对话框", 
        command=lambda: show_category_dialog(manager)
    )
    btn_show_dialog.pack(pady=10)
    
    btn_auto_categorize = tk.Button(
        frame, 
        text="打开自动分类对话框", 
        command=lambda: show_auto_categorize_dialog(manager)
    )
    btn_auto_categorize.pack(pady=10)
    
    btn_search = tk.Button(
        frame, 
        text="搜索分类(关键词: 'explosion')", 
        command=lambda: search_categories(manager)
    )
    btn_search.pack(pady=10)
    
    # 创建关闭按钮
    tk.Button(frame, text="关闭", command=root.destroy).pack(pady=20)
    
    # 启动主循环
    root.mainloop()
    
    print("UI集成示例完成")

def show_category_dialog(manager):
    """显示分类选择对话框"""
    # 创建一些测试文件路径
    test_files = [
        'examples/test_files/explosion_loud_bang.wav',
        'examples/test_files/footsteps_walking_concrete.wav'
    ]
    
    # 显示对话框
    result = manager.show_category_dialog(test_files)
    
    if result:
        print(f"选择的分类: {result}")
    else:
        print("用户取消了选择")

def show_auto_categorize_dialog(manager):
    """显示自动分类对话框"""
    # 创建一些测试文件
    test_files = setup_example()
    
    # 显示对话框
    result = manager.start_auto_categorize(test_files, 'examples/test_output')
    
    if result:
        print(f"成功分类 {len(result)} 个文件")
    else:
        print("用户取消了分类")

def search_categories(manager):
    """搜索分类"""
    keyword = 'explosion'
    results = manager.search_categories(keyword)
    
    print(f"搜索结果 (关键词: '{keyword}'):")
    for category in results:
        print(f"  - {category['id']}: {category['name_zh']} ({category['name_en']})")

if __name__ == "__main__":
    print("=== 分类服务示例 ===")
    
    # 设置示例环境
    test_files = setup_example()
    
    # 运行基本用法示例
    example_basic_usage(test_files)
    
    # 运行UI集成示例
    try:
        example_ui_integration()
    except Exception as e:
        print(f"UI示例出错: {e}")
    
    print("\n示例结束") 