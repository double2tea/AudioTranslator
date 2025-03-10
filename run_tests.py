#!/usr/bin/env python
"""
运行测试脚本

此脚本用于运行AudioTranslator应用程序的单元测试和集成测试。
"""

import os
import sys
import unittest
import argparse
from pathlib import Path

def run_tests(test_type='all', pattern=None, verbosity=2):
    """
    运行测试
    
    Args:
        test_type: 测试类型，可选值为'unit'、'integration'或'all'
        pattern: 测试文件模式，如'test_*.py'
        verbosity: 测试输出详细程度
    
    Returns:
        测试结果
    """
    if pattern is None:
        pattern = 'test_*.py'
    
    # 设置项目根目录
    root_dir = Path(__file__).resolve().parent
    
    # 添加项目根目录到Python路径
    sys.path.insert(0, str(root_dir))
    
    # 确保 src 目录也在 Python 路径中
    src_dir = root_dir / 'src'
    if src_dir.exists() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    
    # 打印当前 Python 路径，用于调试
    print("Python 路径:")
    for path in sys.path:
        print(f"  - {path}")
    
    # 创建测试加载器
    loader = unittest.TestLoader()
    
    # 根据测试类型确定目录
    if test_type == 'unit':
        test_dirs = [root_dir / 'tests' / 'unit']
    elif test_type == 'integration':
        test_dirs = [root_dir / 'tests' / 'integration']
    else:  # 'all'
        test_dirs = [
            root_dir / 'tests' / 'unit',
            root_dir / 'tests' / 'integration'
        ]
    
    # 加载测试套件
    suite = unittest.TestSuite()
    for test_dir in test_dirs:
        if test_dir.exists():
            test_suite = loader.discover(
                start_dir=str(test_dir),
                pattern=pattern
            )
            suite.addTest(test_suite)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=verbosity)
    return runner.run(suite)

if __name__ == '__main__':
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='运行AudioTranslator测试')
    parser.add_argument(
        '--type', 
        choices=['unit', 'integration', 'all'], 
        default='all',
        help='测试类型：unit(单元测试)、integration(集成测试)或all(所有测试)'
    )
    parser.add_argument(
        '--pattern', 
        type=str,
        help='测试文件模式，如"test_service*.py"'
    )
    parser.add_argument(
        '--verbosity', 
        type=int,
        default=2,
        help='输出详细程度（0-2）'
    )
    
    args = parser.parse_args()
    
    # 运行测试
    print(f"正在运行{args.type}测试...")
    result = run_tests(args.type, args.pattern, args.verbosity)
    
    # 退出状态码
    sys.exit(not result.wasSuccessful()) 