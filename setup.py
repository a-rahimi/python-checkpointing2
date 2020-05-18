from distutils.core import setup
import setuptools
from Cython.Build import cythonize
import sys

debuggable_object = False
if debuggable_object:
    import os
    os.environ['CFLAGS'] = '-g -O0'

setup(
    name="function_checkpointing",
    version="0.0.0",
    ext_modules=cythonize(
        "function_checkpointing/*.pyx", compiler_directives={"language_level": "3"},
    ),
    packages=["function_checkpointing"],
    requires=["Cython"],
    python_requires=">=3.6, <=3.7",
)
