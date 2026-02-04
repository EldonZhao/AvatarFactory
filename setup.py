"""
Setup configuration for AvatarFactory package.
"""

from setuptools import find_packages, setup

# Read README
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="avatarfactory",
    version="0.1.0",
    description="A Persona Factory for social platforms",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="AvatarFactory Team",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "anthropic>=0.39.0",
        "pydantic>=2.9.2",
        "pyyaml>=6.0.2",
        "python-dotenv>=1.0.1",
        "typer[all]>=0.12.5",
        "rich>=13.9.4",
        "aiofiles>=24.1.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.3.3",
            "pytest-asyncio>=0.24.0",
            "black>=24.10.0",
            "ruff>=0.7.4",
        ],
    },
    entry_points={
        "console_scripts": [
            "avatarfactory=avatarfactory.cli:app",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
