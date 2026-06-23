from setuptools import setup, find_packages

setup(
    name="displayctl",
    version="1.1.0",
    description="Multi-monitor display mode controller",
    long_description=open("README.md").read() if __import__("os").path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="Displayctl Maintainer",
    author_email="maintainer@displayctl.dev",
    url="https://github.com/displayctl/displayctl",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0",
        "rich>=10.0",
    ],
    extras_require={
        "wayland": ["pyinotify"],
        "dev": ["pytest", "pytest-mock"],
    },
    entry_points={
        "console_scripts": [
            "displayctl=displayctl.cli:main",
            "displayctl-gui=displayctl.gui:run_gui",
        ],
        "gui_scripts": [
            "displayctl-gui=displayctl.gui:run_gui",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Desktop Environment :: Screen Capture",
    ],
)
