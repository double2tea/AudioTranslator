#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup, find_packages

# 读取requirements.txt文件
def read_requirements():
    with open('requirements.txt') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

# 读取README文件
def read_readme():
    with open('README.md', encoding='utf-8') as f:
        return f.read()

setup(
    name="audio_translator",
    version="1.0.0",
    description="音频文件翻译器，支持多种AI模型进行音频内容翻译",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="CherryHQ",
    author_email="contact@cherryhq.com",
    url="https://github.com/CherryHQ/audio-translator",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    package_data={
        "audio_translator": [
            "config/**/*.json",
            "plugins/**/*.py",
        ],
    },
    entry_points={
        "console_scripts": [
            "audio-translator=audio_translator.app:main",
        ],
        "audio_translator.translation_strategies": [
            "simple_custom=audio_translator.plugins.strategies.custom_strategy:SimpleCustomStrategy",
        ],
    },
    python_requires=">=3.8",
    install_requires=read_requirements(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Utilities",
    ],
    keywords="audio, translation, ai, openai, anthropic, gemini",
) 