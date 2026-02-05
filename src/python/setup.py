from setuptools import setup, find_packages

setup(
    name="ods-e",
    version="0.1.0",
    description="Open Data Schema for Energy - validation and transformation library",
    long_description=open("../../README.md").read(),
    long_description_content_type="text/markdown",
    author="Asoba Corporation",
    author_email="support@asoba.co",
    url="https://github.com/AsobaCloud/odse",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "jsonschema>=4.0.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ods-e=ods_e.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="energy, solar, iot, data, schema, validation",
)
