import typing, types
import sys, warnings, importlib


class PathDeprecationLoader(types.ModuleType):
    """
    Based off of:
     https://github.com/tensorflow/tensorflow/blob/v2.2.0/tensorflow/python/util/lazy_lloader.py
     https://docs.python.org/3/library/importlib.html
    Lazily import a module, this allows for throwing warnings when deprecated locations are used.

    Usage:
    # __init__.py
    crackfortran = PathDeprecationLoader("crackfortran", "f2py_skel.frontend.crackfortran", warning="DO NOT USE")
    # Callee
    from f2py_skel import crackfortran
    from crackfortran import markinnerspaces

    .. note::

       In its current implementation

           from f2py_skel.crackfortran import markinnerspaces

       Will fail, since crackfortran is a statement, not really a module.

    """
    def __init__(self,
                 local_name: str,
                 name: str,
                 warnmsg: typing.Optional[str] = None):
        self._local_name = local_name
        self._warnmsg = warnmsg
        self._parent_scope = globals()

        super(PathDeprecationLoader, self).__init__(name)

        self._module = self._lload()

    def _lload(self) -> types.ModuleType:
        """Load the module"""
        module = importlib.import_module(self.__name__)
        sys.modules[self._local_name] = module
        self._parent_scope[self._local_name] = module

        # Emit a warning if one was specified
        if self._warnmsg:
            warnings.warn(self._warnmsg, PendingDeprecationWarning)
            # Make sure to only warn once.
            self._warnmsg = None

        self._module = module
        return module

    def __getattr__(self, item):  # type: ignore[no-untyped-def]
        return getattr(self._module, item)

    def __hasattr__(self, item):  # type: ignore[no-untyped-def]
        return hasattr(self._module, item)

    def __dir__(self) -> typing.List[str]:
        return dir(self._module)
