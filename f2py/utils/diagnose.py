#!/usr/bin/env python3
import os
import sys
import tempfile


def run_command(cmd):
    print('Running %r:' % (cmd))
    os.system(cmd)
    print('------')


def run():
    _path = os.getcwd()
    os.chdir(tempfile.gettempdir())
    print('------')
    print('os.name=%r' % (os.name))
    print('------')
    print('sys.platform=%r' % (sys.platform))
    print('------')
    print('sys.version:')
    print(sys.version)
    print('------')
    print('sys.prefix:')
    print(sys.prefix)
    print('------')
    print('sys.path=%r' % (':'.join(sys.path)))
    print('------')

    try:
        print('Found numpy version %r in %s' %
              (numpy.__version__, numpy.__file__))
    except Exception as msg:
        print('error:', msg)
        print('------')

    try:
        from f2py.frontend import f2py2e
        has_f2py2e = 1
    except ImportError:
        print('Failed to import f2py2e:', sys.exc_info()[1])
        has_f2py2e = 0

    try:
        import numpy.distutils
        has_numpy_distutils = 1
    except ImportError:
        print('Failed to import numpy_distutils:', sys.exc_info()[1])
        has_numpy_distutils = 0

    if has_f2py2e:
        try:
            print('Found f2py2e version %r in %s' %
                  (f2py2e.__version__.version, f2py2e.__file__))
        except Exception as msg:
            print('error:', msg)
            print('------')

    if has_numpy_distutils:
        try:
            print('Found numpy.distutils version %r in %r' % (
                numpy.__version__,
                numpy.distutils.__file__))
        except Exception as msg:
            print('error:', msg)
            print('------')
        try:
            if has_numpy_distutils == 2:
                print('Importing numpy.distutils.fcompiler ...', end=' ')
                import numpy.distutils.fcompiler as fcompiler
            else:
                print('Importing numpy_distutils.fcompiler ...', end=' ')
                import numpy_distutils.fcompiler as fcompiler
            print('ok')
            print('------')
            try:
                print('Checking availability of supported Fortran compilers:')
                fcompiler.show_fcompilers()
                print('------')
            except Exception as msg:
                print('error:', msg)
                print('------')
        except Exception as msg:
            print('error:', msg)
            print('------')
        try:
            print('Importing numpy.distutils.cpuinfo ...', end=' ')
            from numpy.distutils.cpuinfo import cpuinfo
            print('ok')
            print('------')
        except Exception as msg:
            print('error:', msg)
            print('------')
    os.chdir(_path)
if __name__ == "__main__":
    run()
