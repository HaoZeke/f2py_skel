#!/usr/bin/env python3
"""

Build F90 derived types support for f2py2e.

Copyright 2020 NumPy developers,
Permission to use, modify, and distribute this software is given under the
terms of the NumPy License.

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.

"""

from collections import namedtuple
from f2py_skel.stds import auxfuncs as aux
from f2py_skel.stds.pyf import capi_maps as cm

FCPyConversionRow = namedtuple(
    'FCPyConversionRow',
    ['fortran_isoc', 'ctype', 'py_type', 'py_conv', 'varname'],
    defaults=[None])

# These are sourced from:
# ISO_C_BINDINGS: https://gcc.gnu.org/onlinedocs/gfortran/ISO_005fC_005fBINDING.html
# Python Types: https://docs.python.org/3/c-api/arg.html
# Py_Conv: https://docs.python.org/3/c-api/
fcpyconv = [
    # Integers
    # TODO: Use cfuncs.py versions
    FCPyConversionRow(fortran_isoc='c_int',
                      ctype='int',
                      py_type='i',
                      py_conv='PyLong_FromLong'),
    FCPyConversionRow(fortran_isoc='c_short',
                      ctype='short int',
                      py_type='h',
                      py_conv='PyLong_FromLong'),
    FCPyConversionRow(fortran_isoc='c_long',
                      ctype='long int',
                      py_type='l',
                      py_conv='PyLong_FromLong'),
    FCPyConversionRow(fortran_isoc='c_long_long',
                      ctype='long long int',
                      py_type='L',
                      py_conv='PyLong_FromLongLong'),
    # TODO: Add int6 and other sizes
    # Evidently ISO_C_BINDINGs do not have unsigned integers
    # Floats
    FCPyConversionRow(fortran_isoc='c_float',
                      ctype='float',
                      py_type='f',
                      py_conv='float_from_pyobj'),
    FCPyConversionRow(fortran_isoc='c_double',
                      ctype='double',
                      py_type='d',
                      py_conv='double_from_pyobj'),
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


def extract_typedat(typeblock):
    assert typeblock['block'] == 'type'
    typevars = []
    structname = typeblock['name']
    for vname in typeblock['varnames']:
        vfkind = typeblock['vars'][vname]['kindselector']['kind']
        tvar = [x for x in fcpyconv if x.fortran_isoc == vfkind][0]
        typevars.append(tvar._replace(varname=vname))
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
    cline = [
        f"{tv.py_conv}(&xstruct->{tv.varname}, PyList_GetItem(vals, {idx}), \"Error during conversion of {tv.varname} to {tv.ctype}\");\n\t "
        for idx, tv in enumerate(tvars)
    ]
    # TODO: Error out (or warn) if the wrong number of inputs were passed
    # Currently, this function always returns if possible, even when the input "type" is not compatible
    rvfunc = f"""
int {structname}_from_pyobj({structname} *xstruct, PyObject *x_capi){{
   PyObject* vals = PyDict_Values(x_capi);
   {''.join(cline)}
   return 1;
   }}
    """
    return rvfunc


def gen_typeret(structname, tvars, vname):
    """
    The return value is generated from:
        capi_buildvalue = Py_BuildValue(\"#returnformat#\"#return#);
    Mapping:
    returnformat -> retvardecl
    return -> dretlines

    Parameters
    ===========
    structname : string
         The name of the derived type
    tvars : list of namedtuple
         Conversion rules for derived type elements
    vname : string
         The name of the variable in the subprogram
    """
    retvardecl = f"{{{','.join([f's:{x.py_type}' for x in tvars])}}}"
    # XXX: Ugly hack, this forces
    # capi_buildvalue = Py_BuildValue("#returnformat#","x", array.x,
    # "y", array.y,
    # "z", array.z # -> Note the missing ,
    # );
    dretlines = [
        f"""{',' if idx==0 else ''}\
\t \"{tv.varname}\", {vname}.{tv.varname}\
{'' if idx==len(tvars)-1 else ','}
        """
        for idx, tv in enumerate(tvars)
    ]
    return retvardecl, ''.join(dretlines)


def buildhooks(pymod):
    # One structure and function for each derived type
    tdefs = []
    tfuncs = []
    needs = []
    # XXX: Get the type definitions in a sane way
    for pym in pymod.get('body'):
        for blk in pym['body']:
            for typedet in blk['body']:
                if typedet['block'] != 'type':
                    continue
                sname, vardefs = extract_typedat(typedet)
                needs.append([x.py_conv for x in vardefs])
                tdefs.append('\n'.join([gen_typedecl(sname, vardefs)]))
                tfuncs.append('\n'.join([gen_typefunc(sname, vardefs)]))
    # TODO: Document how these dictionary items get used in rules.py
    return {
        'typedefs_derivedtypedefs': tdefs,
        'typedefs_derivedtypefuncs': tfuncs,
        'need': needs
    }


def get_dtargs(rout_vars):
    return [var for var in rout_vars if rout_vars[var]['typespec'] == 'type']


def routine_rules(rout):
    args, depargs = aux.getargs2(rout)
    rettype = [
        x['typename'] for x in rout['vars'].values()
        if (x['typespec'] == 'type') and (
            ('inout' in x['intent']) or ('out' in x['intent']))
    ][0]
    dtargs = get_dtargs(rout['vars'])
    callf = ','.join([f"&{x}" for x in dtargs])
    if len(dtargs) < len(args):
        callf = callf + ','
    for typedet in rout.get('parent_block').get('body'):
        if typedet['block'] != 'type':
            continue
        if typedet['name'] == rettype:
            sname, vardefs = extract_typedat(typedet)
            # TODO: Determine which of the dependent arguments are used for the return
            dretf, dret = gen_typeret(sname, vardefs, depargs[0])
    return {
        'derived_returnformat': dretf,
        'derived_return': dret,
        'derived_argformat': ''.join(["O" for x in dtargs]),
        'derived_callfortran': callf
    }

def arg_rules(rout):
    args, depargs = aux.getargs2(rout)
    alltypes = [cm.getctype(rout['vars'][x]) for x in get_dtargs(rout['vars'])]
    lstring = []
    dstring = []
    pstring = []
    for arg in args:
        ctype = cm.getctype(rout['vars'][arg])
        if ctype not in alltypes:
            # These are processed for ParseTuple
            lstring.append([x.py_type for x in fcpyconv if x.ctype==ctype][0])
            dstring.append(f"&{arg}")
        else:
            lstring.append('O')
            dstring.append(f"&{arg}_capi")
            # Non derived types are processed in rules
            pstring.append(f"    /* Processing variable {arg} */")
            pstring.append(f"    f2py_success = {ctype}_from_pyobj(&{arg}, {arg}_capi);")
    fpyparse = f"""
    /* Parsing arguments */
    f2py_success = PyArg_ParseTuple(capi_args, \"{''.join(lstring)}\", {','.join(dstring)});
   """
    fpyobj = '\n'.join([fpyparse, '\n'.join(pstring)])
    return {
        'frompyobj': fpyobj
    }
