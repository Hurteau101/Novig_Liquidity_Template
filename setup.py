from setuptools import setup, find_packages

setup(
    name="novig-liquidity",
    version="1.0.0",
    description="A Novig Wrapper with filtering and validation",
    author="Devon Hurteau",
    packages=["novig"],
    package_dir={"novig": "."},
    install_requires=[
        "aiohttp>=3.12.0",
        "redis>=6.4.0",
        "pydantic>=2.11.0",
        "requests>=2.32.0",
    ],
    python_requires='>=3.8',
)