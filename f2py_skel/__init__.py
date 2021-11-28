"""Skeleton Fortran to Python Interface Generator."""

from f2py_skel import frontend
from f2py_skel import __version__
# Helpers
from f2py_skel.utils.pathhelper import get_include
# Build tool
from f2py_skel.utils.npdist import compile
from f2py_skel.frontend.f2py2e import main

if __name__ == "__main__":
    sys.exit(main())
