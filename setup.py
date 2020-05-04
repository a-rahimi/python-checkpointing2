from distutils.core import setup
from Cython.Build import cythonize
import sys

setup(
    name="save_restore_generators",
    ext_modules=cythonize(
        "save_restore_generators.pyx", compiler_directives={"language_level": "3"}
    ),
    requires=["Cython"],
)

setup(
    name="calltrace",
    ext_modules=cythonize("calltrace.pyx", compiler_directives={"language_level": "3"}),
    requires=["Cython"],
)
