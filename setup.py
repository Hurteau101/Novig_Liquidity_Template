from setuptools import setup, find_packages

with open("requirements.txt", encoding="utf-8-sig") as f:
    requirements = f.read().splitlines()

setup(
    name="novig-liquidity",
    version="1.0.0",
    description="A Novig Wrapper with filtering and validation",
    author="Devon Hurteau",
    packages=find_packages(),
    install_requires=requirements,
    python_requires='>=3.8',
)