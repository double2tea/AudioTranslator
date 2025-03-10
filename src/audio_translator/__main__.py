"""
音效文件翻译器应用程序入口

此模块是应用程序的主入口点，负责初始化日志系统、初始化基础服务、加载配置并启动GUI界面。
"""

import os
import sys
import logging
import logging.handlers
import tkinter as tk
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入应用程序组件
from .gui.main_window import AudioTranslatorGUI
from .services.core.service_factory import ServiceFactory

def setup_logging():
    """
    设置日志系统
    
    创建日志目录并配置日志记录器，包括控制台和文件输出。
    """
    # 创建日志目录
    log_dir = project_root / "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # 创建日志文件名，包含日期
    log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 设置为DEBUG以捕获所有日志
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    
    # 创建文件处理器
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    
    # 添加处理器到根日志记录器
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # 设置第三方库的日志级别
    logging.getLogger('PIL').setLevel(logging.WARNING)
    
    # 设置应用程序的特定日志级别
    logging.getLogger('audio_translator.services.core.service_manager_service').setLevel(logging.DEBUG)
    logging.getLogger('audio_translator.services.infrastructure.config_service').setLevel(logging.DEBUG)
    
    logging.info("日志系统初始化完成")

def initialize_services():
    """
    初始化基础服务
    
    创建服务工厂并初始化所有基础服务。
    
    Returns:
        服务工厂实例
    """
    logging.info("开始初始化基础服务")
    
    # 使用ServiceFactory.get_instance()获取单例实例
    from .services.core.service_factory import ServiceFactory
    service_factory = ServiceFactory.get_instance()
    
    if service_factory.initialize_all_services():
        logging.info("基础服务初始化成功")
    else:
        logging.error("部分基础服务初始化失败")
    
    # 手动注册可能缺失的服务
    from .services.register_services import register_missing_services
    if register_missing_services(service_factory):
        logging.info("所有缺失服务已成功注册")
    else:
        logging.warning("部分缺失服务注册失败")
    
    return service_factory

def main():
    """
    应用程序主入口函数
    
    初始化日志系统，创建并初始化基础服务，创建主窗口并启动应用程序。
    """
    # 设置日志系统
    setup_logging()
    
    try:
        # 初始化基础服务
        service_factory = initialize_services()
        
        # 确保我们使用的是单例实例
        from .services.core.service_factory import ServiceFactory
        singleton_factory = ServiceFactory.get_instance()
        if singleton_factory != service_factory:
            logging.warning("检测到多个ServiceFactory实例，将使用单例实例")
            service_factory = singleton_factory
        
        # 创建主窗口
        root = tk.Tk()
        app = AudioTranslatorGUI(root, service_factory)
        
        # 启动应用程序
        logging.info("应用程序启动")
        root.mainloop()
        logging.info("应用程序关闭")
        
        # 关闭服务
        service_factory.shutdown_all_services()
        
    except Exception as e:
        logging.exception(f"应用程序发生错误: {e}")
        # 确保在发生错误时也尝试关闭服务
        try:
            if 'service_factory' in locals():
                service_factory.shutdown_all_services()
        except Exception as shutdown_error:
            logging.error(f"关闭服务时发生错误: {shutdown_error}")
        raise

if __name__ == "__main__":
    main() 