"""Skeleton Fortran to Python Interface Generator."""

__all__ = ['run_main', 'compile', 'get_include']

from f2py_skel import frontend
from f2py_skel import __version__
# Helpers
from f2py_skel.utils.pathhelper import get_include
# Build tool
from f2py_skel.utils.npdist import compile
from f2py_skel.frontend.f2py2e import main

run_main = frontend.f2py2e.run_main

if __name__ == "__main__":
    sys.exit(main())

# Deprecated
from f2py_skel.utils.deprecationhelpers import PathDeprecationLoader, PathDeprecations
# crackfortran = PathDeprecationLoader("crackfortran", "f2py_skel.frontend.crackfortran", warnmsg="DO NOT USE")
PathDeprecations()
