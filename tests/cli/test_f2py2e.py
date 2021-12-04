import textwrap
from pathlib import Path
from unittest.mock import patch
from collections import namedtuple

import pytest

import numpy as np
from numpy.testing import assert_, assert_equal, IS_PYPY

from .. import util
from f2py_skel.frontend import main as f2pycli

#########################
# CLI utils and classes #
#########################

PPaths = namedtuple("PPaths",
                    "finp, f90inp, pyf, wrap77, wrap90, cmodf")

def get_io_paths(fname_inp, mname="untitled"):
    """Takes in a temporary file for testing and returns the expected output and input paths

    Here expected output is essentially one of any of the possible generated
    files.

    ..note::

         Since this does not actually run f2py, none of these are guaranteed to
         exist, and module names are typically incorrect

    Parameters
    ----------
    fname_inp : str
                The input filename
    mname : str, optional
                The name of the module, untitled by default

    Returns
    -------
    genp : NamedTuple PPaths
            The possible paths which are generated, not all of which exist
    """
    bpath = Path(fname_inp)
    bstem = bpath.stem
    foutl = PPaths(
        finp = bpath.with_suffix(".f"),
        f90inp = bpath.with_suffix(".f90"),
        pyf = bpath.with_suffix(".pyf"),
        wrap77 = bpath.with_name(f"{mname}-f2pywrappers.f"),
        wrap90 = bpath.with_name(f"{mname}-f2pywrappers2.f90"),
        cmodf = bpath.with_name(f"{mname}module.c")
    )
    return foutl

##########################
# CLI Fixtures and Tests #
##########################

@pytest.fixture(scope="session")
def hello_world_f90(tmpdir_factory):
    """Generates a single f90 file for testing
    """
    fdat = textwrap.dedent("""
    function hi
      print*, "Hello World"
    end function
    """)
    fn = tmpdir_factory.getbasetemp() / "hello.f90"
    fn.write_text(fdat, encoding="ascii")
    return fn

def test_gen_pyf(capfd, hello_world_f90, monkeypatch):
    """Ensures that a signature file is generated via the CLI
    """
    ipath = Path(hello_world_f90)
    opath = Path(hello_world_f90).stem + ".pyf"
    monkeypatch.setattr("sys.argv", ["pytest", # doesn't get passed
                                     "-h", # Create a signature file
                                     str(opath),
                                     str(ipath)])

    with util.switchdir(ipath.parent):
        f2pycli() # Generate wrappers
        out, _ = capfd.readouterr()
        assert "Saving signatures to file" in out
        assert Path(f"{str(opath)}").exists()

def test_gen_pyf_no_overwrite(capfd, hello_world_f90, monkeypatch):
    """Ensures that the CLI refuses to overwrite signature files
    """
    ipath = Path(hello_world_f90)
    monkeypatch.setattr("sys.argv", ["pytest",
                                     "-h",
                                     "faker.pyf",
                                     str(ipath)])

    with util.switchdir(ipath.parent):
        Path("faker.pyf").write_text("Fake news", encoding="ascii")
        with pytest.raises(SystemExit):
            f2pycli() # Refuse to overwrite
    _, err = capfd.readouterr()
    assert "Use --overwrite-signature to overwrite" in err
