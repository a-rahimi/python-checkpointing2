from distutils.core import setup
import setuptools
from Cython.Build import cythonize
import sys

setup(
    name="function_checkpointing",
    version="0.0.0",
    ext_modules=cythonize(
        "function_checkpointing/*.pyx", compiler_directives={"language_level": "3"}
    ),
    packages=["function_checkpointing"],
    requires=["Cython"],
    python_requires='>=3.6',
)
