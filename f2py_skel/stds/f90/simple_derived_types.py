#!/usr/bin/env python3
"""

Build F90 derived types support for f2py2e.

Copyright 2020 NumPy developers,
Permission to use, modify, and distribute this software is given under the
terms of the NumPy License.

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.

"""

cmapipy = {
    'c_double': "PyFloat_AsDouble",
    'c_float': "PyFloat_AsDouble",
}


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
    breakpoint()
    ret = []
    m = pymod.get('body')
    for blockdef in m:
        if blockdef['block'] == 'type':
            del blockdef['parent_body']
            ret.append(blockdef)
    return ret


def buildhooks(pymod):
    res = []
    for typedet in pymod.get('body')[0]['body'][0]['body']:
        defs = []
        cstruct_var = []
        pyc_conv_fn = []
        for var in [
                x for x in typedet.get('vars')
                if 'kindselector' in typedet['vars'][x].keys()
        ]:
            if 'c_' not in typedet['vars'][var]['kindselector']['kind']:
                continue
            else:
                vkind = typedet['vars'][var]['kindselector']['kind']
                ckind = vkind.replace('c_', '')
                vdef = f"{ckind} {var};"
                cstruct_var.append(var)
                pyc_conv_fn.append(cmapipy.get(vkind))
                defs.append(vdef)
        if len(defs) > 0:
            cline = []
            structname = typedet['name']
            for i in range(len(defs)):
                cline.append(
                    f"xstruct->{cstruct_var[i]} = {pyc_conv_fn[i]}(PyList_GetItem(vals, {i}));\n            "
                )
            res.append(f"""
    typedef struct {{
    {''.join(defs)}
    }} {structname};
    int try_pyarr_from_{structname}({structname} *xstruct, PyObject *x_capi){{
            PyObject* dict;
            PyArg_ParseTuple(x_capi, "O", &dict);
            PyObject* vals = PyDict_Values(dict);
            {''.join(cline)}
            return 1;
            }}
    """)
    ret = {'typedefs_derivedtypes': res}
    return ret
