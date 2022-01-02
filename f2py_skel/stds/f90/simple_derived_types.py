#!/usr/bin/env python3
"""

Build F90 derived types support for f2py2e.

Copyright 2020 NumPy developers,
Permission to use, modify, and distribute this software is given under the
terms of the NumPy License.

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.

"""

from collections import namedtuple

fcpyfunc = {
    'c_double': "PyFloat_AsDouble",
    'c_float': "PyFloat_AsDouble",
}

fcpycode = {
    'c_float': 'f',
    'c_double': 'd',
}

FCPyConversionRow = namedtuple('FCPyConversionRow', ['fortran_isoc', 'ctype', 'py_type', 'py_conv', 'varname'], defaults = [None])

# These are sourced from:
# ISO_C_BINDINGS: https://gcc.gnu.org/onlinedocs/gfortran/ISO_005fC_005fBINDING.html
# Python Types: https://docs.python.org/3/c-api/arg.html
# Py_Conv: https://docs.python.org/3/c-api/
fcpyconv = [
    # Integers
    FCPyConversionRow(fortran_isoc = 'c_int',
                      ctype = 'int',
                      py_type = 'i',
                      py_conv = 'PyLong_FromLong'),
    FCPyConversionRow(fortran_isoc = 'c_short',
                      ctype = 'short int',
                      py_type = 'h',
                      py_conv = 'PyLong_FromLong'),
    FCPyConversionRow(fortran_isoc = 'c_long',
                      ctype = 'long int',
                      py_type = 'l',
                      py_conv = 'PyLong_FromLong'),
    FCPyConversionRow(fortran_isoc = 'c_long_long',
                      ctype = 'long long int',
                      py_type = 'L',
                      py_conv = 'PyLong_FromLongLong'),
    # TODO: Add int6 and other sizes
    # Evidently ISO_C_BINDINGs do not have unsigned integers
    # Floats
    FCPyConversionRow(fortran_isoc = 'c_float',
                      ctype = 'float',
                      py_type = 'f',
                      py_conv = 'PyFloat_AsDouble'),
    FCPyConversionRow(fortran_isoc = 'c_double',
                      ctype = 'double',
                      py_type = 'd',
                      py_conv = 'PyFloat_AsDouble'),
]

def find_typeblocks(pymod):
    """Return a list of type definitions

    Parameters
    ----------
    pymod : dict
        The python module dictionary.

    Returns
    -------
    ret : list
       This returns a list of module blocks
    """
    ret = []
    m = pymod.get('body')
    for blockdef in m:
        if blockdef['block'] == 'type':
            del blockdef['parent_body']
            ret.append(blockdef)
    return ret

def recursive_lookup(k, d):
    if k in d: return d[k]
    for v in d.values():
        if isinstance(v, dict):
            a = recursive_lookup(k, v)
            if a is not None: return a
    return None

def extract_typedat(typeblock):
    assert typeblock['block'] == 'type'
    typevars = []
    structname = typeblock['name']
    for vname in typeblock['varnames']:
        vfkind = typeblock['vars'][vname]['kindselector']['kind']
        tvar = [x for x in fcpyconv if x.fortran_isoc == vfkind][0]
        typevars.append(tvar._replace(varname = vname))
    return structname, typevars

def gen_typedecl(structname, tvars):
    vdefs = [''.join(f"{x.ctype} {x.varname};") for x in tvars]
    tdecl = f"""
    typedef struct {{
    {' '.join(vdefs)}
    }} {structname};
    """
    return tdecl

def gen_typefunc(structname, tvars):
    cline = []
    for idx,tv in enumerate(tvars):
        cline.append(f"xstruct->{tv.varname} = {tv.py_conv}(PyList_GetItem(vals, {idx}));\n\t\t")
    rvfunc = f"""
    int try_pyarr_from_{structname}({structname} *xstruct, PyObject *x_capi){{
            PyObject* dict;
            PyArg_ParseTuple(x_capi, "O", &dict);
            PyObject* vals = PyDict_Values(dict);
            {''.join(cline)}
            return 1;
            }}
    """
    return rvfunc

def gen_typeret(structname, tvars):
    """
    The return value is generated from:
        capi_buildvalue = Py_BuildValue(\"#returnformat#\"#return#);
    Mapping:
    returnformat -> retvardecl
    return -> dretlines
    """
    retvardecl = f"{{{','.join([f's:{x.py_type}' for x in tvars])}}}"
    dretlines = []
    for idx,tv in enumerate(tvars):
        # XXX: Ugly hack, this forces
        # capi_buildvalue = Py_BuildValue("#returnformat#","x", array.x,
        # "y", array.y,
        # "z", array.z # -> Note the missing ,
        # );
        dretlines.append(f"""{',' if idx==0 else ''}\
\t \"{tv.varname}\", array.{tv.varname}\
{'' if idx==len(tvars)-1 else ','}
        """)
    return retvardecl, ''.join(dretlines)

def buildhooks(pymod):
    # One structure and function for each derived type
    res = []
    # XXX: Get the type definitions in a sane way
    for typedet in pymod.get('body')[0]['body'][0]['body']:
        if typedet['block']!='type':
            continue
        sname, vardefs = extract_typedat(typedet)
        res.append('\n'.join([gen_typedecl(sname, vardefs), gen_typefunc(sname, vardefs)]))
        dretf, dret  = gen_typeret(sname, vardefs)
    # TODO: Document how these dictionary items get used in rules.py
    # TODO: The return values are based on the subroutine being considered, not
    # on the derived type
    ret = {
        'typedefs_derivedtypes': res,
        'derived_returnformat': dretf,
        'derived_return': dret
    }
    return ret
