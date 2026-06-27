from pathlib import Path

from setuptools import setup


Path(".setuptools-build").mkdir(exist_ok=True)
Path(".setuptools-egg-info").mkdir(exist_ok=True)

setup()
