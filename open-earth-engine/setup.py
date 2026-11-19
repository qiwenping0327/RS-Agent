from setuptools import setup, find_packages

setup(
    name="open-earth-engine",
    version="0.1.0",
    description="OpenEarthAgent - Unified Tool-Enhanced Geospatial Agent Framework",
    author="PilotDeck Team",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "asyncio",
        "httpx",
        "numpy",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-asyncio",
        ],
        "gdal": [
            "rasterio",
            "geopandas",
            "shapely",
            "fiona",
            "pyproj",
        ],
        "s3": [
            "aioboto3",
        ],
    },
    entry_points={
        "console_scripts": [
            "open-earth-engine=open_earth_engine.__main__:run_cli",
        ],
    },
)
