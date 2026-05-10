"""
Setup script for Morphic Agents module
"""

from setuptools import setup, find_packages

setup(
    name="morphic-agents",
    version="1.0.0",
    description="Concurrent Claude Code Agent orchestration for Morphic",
    author="Morphic Team",
    packages=find_packages(),
    install_requires=[
        "claude-agent-sdk>=0.1.0"
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
