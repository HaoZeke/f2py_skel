import pytest
import textwrap
from pathlib import Path
from unittest.mock import patch

import numpy as np
from numpy.testing import assert_, assert_equal, IS_PYPY

from .. import util
from f2py_skel.frontend import main as f2pycli

@pytest.fixture(scope="session")
def hello_world_f90(tmpdir_factory):
    """Generates a single f90 file for testing
    """
    fdat = textwrap.dedent("""
    program main
      print*, "Hello World"
    end program main
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
