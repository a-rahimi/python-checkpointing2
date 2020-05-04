from distutils.core import setup
import setuptools
from Cython.Build import cythonize
import sys

setup(
    name="generator_checkpointing",
    version="0.0.0",
    ext_modules=cythonize(
        "generator_checkpointing/*.pyx", compiler_directives={"language_level": "3"}
    ),
    packages=["generator_checkpointing"],
    requires=["Cython"],
    python_requires='>=3.6',
)
