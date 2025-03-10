import logging
import sys
import os
from pathlib import Path

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入需要测试的类
from src.audio_translator.services.core.service_manager_service import ServiceManagerService

def test_service_manager_config_path():
    """测试ServiceManagerService是否使用了正确的配置路径"""
    logger.info("=== 测试服务管理器配置路径 ===")
    
    # 创建ServiceManagerService实例
    service_manager = ServiceManagerService()
    
    # 获取配置路径
    config_path = service_manager.config_path
    logger.info(f"服务管理器配置路径: {config_path}")
    
    # 获取项目级配置目录
    project_root = Path(__file__).resolve().parent.parent
    expected_config_path = project_root / "src" / "config" / "services.json"
    logger.info(f"期望的配置路径: {expected_config_path}")
    
    # 检查配置路径是否正确
    if str(config_path) == str(expected_config_path):
        logger.info("✅ 服务管理器使用了正确的项目级配置路径")
    else:
        logger.error(f"❌ 服务管理器使用了错误的配置路径: {config_path}")
        logger.error(f"期望的配置路径: {expected_config_path}")
    
    # 检查配置文件是否存在
    if config_path.exists():
        logger.info(f"✅ 配置文件存在: {config_path}")
    else:
        logger.error(f"❌ 配置文件不存在: {config_path}")

if __name__ == "__main__":
    # 执行测试
    test_service_manager_config_path() 