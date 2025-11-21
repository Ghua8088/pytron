from setuptools import setup, find_packages

setup(
    name="pytron",
    version="0.1.0",
    description="An Electron-like library for Python using pywebview",
    author="Antigravity",
    packages=find_packages(),
    install_requires=[
        "pywebview",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
