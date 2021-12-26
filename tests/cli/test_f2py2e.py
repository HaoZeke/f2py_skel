import textwrap, re, sys, subprocess, shlex
from pathlib import Path
from unittest.mock import patch
from collections import namedtuple

import pytest

import numpy as np
from numpy.testing import assert_, assert_equal, IS_PYPY

from .. import util
from f2py_skel.frontend import main as f2pycli

#############
# CLI utils and classes #
#############

PPaths = namedtuple("PPaths", "finp, f90inp, pyf, wrap77, wrap90, cmodf")


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
        finp=bpath.with_suffix(".f"),
        f90inp=bpath.with_suffix(".f90"),
        pyf=bpath.with_suffix(".pyf"),
        wrap77=bpath.with_name(f"{mname}-f2pywrappers.f"),
        wrap90=bpath.with_name(f"{mname}-f2pywrappers2.f90"),
        cmodf=bpath.with_name(f"{mname}module.c"),
    )
    return foutl


##############
# CLI Fixtures and Tests #
#############


@pytest.fixture(scope="session")
def hello_world_f90(tmpdir_factory):
    """Generates a single f90 file for testing"""
    fdat = util.getpath("tests", "src", "cli", "hiworld.f90").read_text()
    fn = tmpdir_factory.getbasetemp() / "hello.f90"
    fn.write_text(fdat, encoding="ascii")
    return fn


@pytest.fixture(scope="session")
def hello_world_f77(tmpdir_factory):
    """Generates a single f77 file for testing"""
    fdat = util.getpath("tests", "src", "cli", "hi77.f").read_text()
    fn = tmpdir_factory.getbasetemp() / "hello.f"
    fn.write_text(fdat, encoding="ascii")
    return fn


@pytest.fixture(scope="session")
def retreal_f77(tmpdir_factory):
    """Generates a single f77 file for testing"""
    fdat = util.getpath("tests", "src", "return_real", "foo77.f").read_text()
    fn = tmpdir_factory.getbasetemp() / "foo.f"
    fn.write_text(fdat, encoding="ascii")
    return fn


def test_gen_pyf(capfd, hello_world_f90, monkeypatch):
    """Ensures that a signature file is generated via the CLI
    CLI :: -h
    """
    ipath = Path(hello_world_f90)
    opath = Path(hello_world_f90).stem + ".pyf"
    monkeypatch.setattr(sys, "argv",
                        f"f2py -h {str(opath)} {str(ipath)}".split())

    with util.switchdir(ipath.parent):
        f2pycli()  # Generate wrappers
        out, _ = capfd.readouterr()
        assert "Saving signatures to file" in out
        assert Path(f"{str(opath)}").exists()

def test_gen_pyf_stdout(capfd, hello_world_f90, monkeypatch):
    """Ensures that a signature file can be dumped to stdout
    CLI :: -h
    """
    ipath = Path(hello_world_f90)
    monkeypatch.setattr(sys, "argv",
                        f"f2py -h stdout {str(ipath)}".split())
    with util.switchdir(ipath.parent):
        f2pycli()
        out, _ = capfd.readouterr()
        assert "Saving signatures to file \"./stdout\"" in out


def test_gen_pyf_no_overwrite(capfd, hello_world_f90, monkeypatch):
    """Ensures that the CLI refuses to overwrite signature files
    CLI :: -h without --overwrite-signature
    """
    ipath = Path(hello_world_f90)
    monkeypatch.setattr(sys, "argv", f"f2py -h faker.pyf {str(ipath)}".split())

    with util.switchdir(ipath.parent):
        Path("faker.pyf").write_text("Fake news", encoding="ascii")
        with pytest.raises(SystemExit):
            f2pycli()  # Refuse to overwrite
    _, err = capfd.readouterr()
    assert "Use --overwrite-signature to overwrite" in err


def test_f2py_skip(capfd, retreal_f77, monkeypatch):
    """Tests that functions can be skipped
    CLI :: skip:
    """
    foutl = get_io_paths(retreal_f77, mname="test")
    ipath = foutl.finp
    toskip = "t0 t4 t8 sd s8 s4"
    remaining = "td s0"
    monkeypatch.setattr(
        sys,
        "argv",
        f"f2py {str(ipath)} {str(foutl.pyf)} -m test skip: {toskip}".split(),
    )
    with util.switchdir(ipath.parent):
        f2pycli()
    out, err = capfd.readouterr()
    for skey in toskip.split():
        assert (
            f'buildmodule: Could not found the body of interfaced routine "{skey}". Skipping.'
            in err)
    for rkey in remaining.split():
        assert f'Constructing wrapper function "{rkey}"' in out


def test_f2py_only(capfd, retreal_f77, monkeypatch):
    """Test that functions can be kept by only:
    CLI :: only:
    """
    foutl = get_io_paths(retreal_f77, mname="test")
    ipath = foutl.finp
    toskip = "t0 t4 t8 sd s8 s4"
    tokeep = "td s0"
    monkeypatch.setattr(
        sys,
        "argv",
        f"f2py {str(ipath)} {str(foutl.pyf)} -m test only: {tokeep}".split(),
    )
    with util.switchdir(ipath.parent):
        f2pycli()
    out, err = capfd.readouterr()
    for skey in toskip.split():
        assert (
            f'buildmodule: Could not found the body of interfaced routine "{skey}". Skipping.'
            in err)
    for rkey in tokeep.split():
        assert f'Constructing wrapper function "{rkey}"' in out


def test_file_processing_switch():
    """Tests that it is possible to return to file processing mode
    CLI :: :
    BUG: numpy-gh #20520
    """
    pass


def test_mod_gen_f77(capfd, hello_world_f90, monkeypatch):
    """Checks the generation of files based on a module name
    CLI :: -m
    """
    MNAME = "hi"
    foutl = get_io_paths(hello_world_f90, mname=MNAME)
    ipath = foutl.f90inp
    monkeypatch.setattr(sys, "argv", f"f2py {str(ipath)} -m {MNAME}".split())
    with util.switchdir(ipath.parent):
        f2pycli()

    # Always generate C module
    assert Path.exists(foutl.cmodf)
    # File contains a function, check for F77 wrappers
    assert Path.exists(foutl.wrap77)


def test_lower_cmod(capfd, hello_world_f77, monkeypatch):
    """Lowers cases by flag or when -h is present
    CLI :: --[no-]lower
    """
    foutl = get_io_paths(hello_world_f77, mname="test")
    ipath = foutl.finp
    capshi = re.compile(r"HI\(\)")
    capslo = re.compile(r"hi\(\)")
    # Case I: --lower is passed
    monkeypatch.setattr(sys, "argv",
                        f"f2py {str(ipath)} -m test --lower".split())
    with util.switchdir(ipath.parent):
        f2pycli()
        out, _ = capfd.readouterr()
        assert capslo.search(out) is not None
        assert capshi.search(out) is None
    # Case II: --no-lower is passed
    monkeypatch.setattr(sys, "argv",
                        f"f2py {str(ipath)} -m test --no-lower".split())
    with util.switchdir(ipath.parent):
        f2pycli()
        out, _ = capfd.readouterr()
        assert capslo.search(out) is None
        assert capshi.search(out) is not None


def test_lower_sig(capfd, hello_world_f77, monkeypatch):
    """Lowers cases in signature files by flag or when -h is present
    CLI :: --[no-]lower -h
    """
    foutl = get_io_paths(hello_world_f77, mname="test")
    ipath = foutl.finp
    # Signature files
    capshi = re.compile(r"Block: HI")
    capslo = re.compile(r"Block: hi")
    # Case I: --lower is implied by -h
    # TODO: Clean up to prevent passing --overwrite-signature
    monkeypatch.setattr(
        sys,
        "argv",
        f"f2py {str(ipath)} -h {str(foutl.pyf)} -m test --overwrite-signature".
        split(),
    )
    with util.switchdir(ipath.parent):
        f2pycli()
        out, _ = capfd.readouterr()
        assert capslo.search(out) is not None
        assert capshi.search(out) is None

    # Case II: --no-lower overrides -h
    monkeypatch.setattr(
        sys,
        "argv",
        f"f2py {str(ipath)} -h {str(foutl.pyf)} -m test --overwrite-signature --no-lower"
        .split(),
    )
    with util.switchdir(ipath.parent):
        f2pycli()
        out, _ = capfd.readouterr()
        assert capslo.search(out) is None
        assert capshi.search(out) is not None

def test_build_dir(capfd, hello_world_f90, monkeypatch):
    """Ensures that the build directory can be specified
    CLI :: --build-dir
    """
    ipath = Path(hello_world_f90)
    mname = "blah"
    odir = "tttmp"
    opath = Path(hello_world_f90).parent / odir
    monkeypatch.setattr(sys, "argv", f"f2py -m {mname} {str(ipath)} --build-dir {odir}".split())

    with util.switchdir(ipath.parent):
        f2pycli()
    out, _ = capfd.readouterr()
    assert f"Wrote C/API module \"{mname}\" to file \"{odir}/{mname}module.c\"" in out

def test_overwrite(capfd, hello_world_f90, monkeypatch):
    """Ensures that the build directory can be specified
    CLI :: --overwrite-signature
    """
    ipath = Path(hello_world_f90)
    monkeypatch.setattr(sys, "argv", f"f2py -h faker.pyf {str(ipath)} --overwrite-signature".split())

    with util.switchdir(ipath.parent):
        Path("faker.pyf").write_text("Fake news", encoding="ascii")
        f2pycli()
    out, _ = capfd.readouterr()
    assert "Saving signatures to file" in out
    pass

def test_latexdoc(capfd, hello_world_f90, monkeypatch):
    """Ensures that TeX documentation is written out
    CLI :: --latex-doc
    """
    ipath = Path(hello_world_f90)
    mname = "blah"
    monkeypatch.setattr(sys, "argv", f"f2py -m {mname} {str(ipath)} --latex-doc".split())

    with util.switchdir(ipath.parent):
        f2pycli()
    out, _ = capfd.readouterr()
    assert f"Documentation is saved to file \"./{mname}module.tex\"" in out
    with util.switchdir(ipath.parent):
        otex = Path(f"./{mname}module.tex").open().read()
        assert "\\documentclass" in otex

def test_shortlatex(capfd, hello_world_f90, monkeypatch):
    """Ensures that truncated documentation is written out
    TODO: Test to ensure this has no effect without --latex-doc
    CLI :: --latex-doc --short-latex
    """
    ipath = Path(hello_world_f90)
    mname = "blah"
    monkeypatch.setattr(sys, "argv", f"f2py -m {mname} {str(ipath)} --latex-doc --short-latex".split())

    with util.switchdir(ipath.parent):
        f2pycli()
    out, _ = capfd.readouterr()
    assert f"Documentation is saved to file \"./{mname}module.tex\"" in out
    with util.switchdir(ipath.parent):
        otex = Path(f"./{mname}module.tex").open().read()
        assert "\\documentclass" not in otex

def test_restdoc(capfd, hello_world_f90, monkeypatch):
    """Ensures that RsT documentation is written out
    CLI :: --rest-doc
    """
    ipath = Path(hello_world_f90)
    mname = "blah"
    monkeypatch.setattr(sys, "argv", f"f2py -m {mname} {str(ipath)} --rest-doc".split())

    with util.switchdir(ipath.parent):
        f2pycli()
    out, _ = capfd.readouterr()
    assert f"ReST Documentation is saved to file \"./{mname}module.rest\"" in out
    with util.switchdir(ipath.parent):
        orst = Path(f"./{mname}module.rest").open().read()
        assert r".. -*- rest -*-" in orst

def test_debugcapi(capfd, hello_world_f90, monkeypatch):
    """Ensures that debugging wrappers are written
    CLI :: --debug-capi
    """
    ipath = Path(hello_world_f90)
    mname = "blah"
    monkeypatch.setattr(sys, "argv", f"f2py -m {mname} {str(ipath)} --debug-capi".split())

    with util.switchdir(ipath.parent):
        f2pycli()
        ocmod = Path(f"./{mname}module.c").open().read()
        assert r"#define DEBUGCFUNCS" in ocmod

@pytest.mark.slow
def test_debugcapi_bld(capfd, hello_world_f90, monkeypatch):
    """Ensures that debugging wrappers work
    CLI :: --debug-capi
    """
    ipath = Path(hello_world_f90)
    mname = "blah"
    monkeypatch.setattr(sys, "argv", f"f2py -m {mname} {str(ipath)} -c --debug-capi".split())

    with util.switchdir(ipath.parent):
        f2pycli()
        cmd_run = shlex.split("python -c \"import blah; blah.hi()\"")
        rout = subprocess.run(cmd_run, capture_output=True, encoding='UTF-8')
        eout = ' Hello World\n'
        eerr = textwrap.dedent("""\
debug-capi:Python C/API function blah.hi()
debug-capi:float hi=:output,hidden,scalar
debug-capi:hi=0
debug-capi:Fortran subroutine `f2pywraphi(&hi)'
debug-capi:hi=0
debug-capi:Building return value.
debug-capi:Python C/API function blah.hi: successful.
debug-capi:Freeing memory.
        """)
        assert rout.stdout == eout
        assert rout.stderr == eerr

def test_wrapfunc_def(capfd, hello_world_f90, monkeypatch):
    """Ensures that fortran subroutine wrappers for F77 are included by default
    CLI :: --[no]-wrap-functions
    """
    # Implied
    ipath = Path(hello_world_f90)
    mname = "blah"
    monkeypatch.setattr(sys, "argv", f"f2py -m {mname} {str(ipath)}".split())

    with util.switchdir(ipath.parent):
        f2pycli()
    out, _ = capfd.readouterr()
    assert r"Fortran 77 wrappers are saved to" in out

    # Explicit
    monkeypatch.setattr(sys, "argv", f"f2py -m {mname} {str(ipath)} --wrap-functions".split())

    with util.switchdir(ipath.parent):
        f2pycli()
    out, _ = capfd.readouterr()
    assert r"Fortran 77 wrappers are saved to" in out

def test_nowrapfunc(capfd, hello_world_f90, monkeypatch):
    """Ensures that fortran subroutine wrappers for F77 can be disabled
    CLI :: --no-wrap-functions
    """
    ipath = Path(hello_world_f90)
    mname = "blah"
    monkeypatch.setattr(sys, "argv", f"f2py -m {mname} {str(ipath)} --no-wrap-functions".split())

    with util.switchdir(ipath.parent):
        f2pycli()
    out, _ = capfd.readouterr()
    assert r"Fortran 77 wrappers are saved to" not in out

def test_inclpath():
    """Add to the include directories
    CLI :: --include-paths
    """
    pass

def test_inclpath():
    """Add to the include directories
    CLI :: --help-link
    """
    pass

def test_inclpath():
    """Check that Fortran-to-Python KIND specs can be passed
    CLI :: --f2cmap
    """
    pass

def test_quiet():
    """Reduce verbosity
    CLI :: --quiet
    """
    pass

def test_verbose():
    """Increase verbosity
    CLI :: --verbose
    """
    pass

def test_version():
    """Ensure version
    CLI :: -v
    """
    pass

def test_npdistop():
    """
    CLI :: -c
    """
    pass

# Numpy distutils flags
# TODO: These should be tested separately

def test_npd_fcompiler():
    """
    CLI :: -c --fcompiler
    """
    pass

def test_npd_compiler():
    """
    CLI :: -c --compiler
    """
    pass


def test_npd_help_fcompiler():
    """
    CLI :: -c --help-fcompiler
    """
    pass

def test_npd_f77exec():
    """
    CLI :: -c --f77exec
    """
    pass

def test_npd_f90exec():
    """
    CLI :: -c --f90exec
    """
    pass

def test_npd_f77flags():
    """
    CLI :: -c --f77flags
    """
    pass

def test_npd_f90flags():
    """
    CLI :: -c --f90flags
    """
    pass

def test_npd_opt():
    """
    CLI :: -c --opt
    """
    pass

def test_npd_arch():
    """
    CLI :: -c --arch
    """
    pass

def test_npd_noopt():
    """
    CLI :: -c --noopt
    """
    pass

def test_npd_noarch():
    """
    CLI :: -c --noarch
    """
    pass


def test_npd_debug():
    """
    CLI :: -c --debug
    """
    pass


def test_npd_link_auto():
    """
    CLI :: -c --link-<resource>
    """
    pass

def test_npd_lib():
    """
    CLI :: -c -L/path/to/lib/ -l<libname>
    """
    pass


def test_npd_define():
    """
    CLI :: -D<define>
    """
    pass

def test_npd_undefine():
    """
    CLI :: -U<name>
    """
    pass

def test_npd_incl():
    """
    CLI :: -I/path/to/include/
    """
    pass

def test_npd_linker():
    """
    CLI :: <filename>.o <filename>.so <filename>.a
    """
    pass
