#!/usr/bin/env python3
"""

Build F90 derived types support for f2py2e.

Copyright 2020 NumPy developers,
Permission to use, modify, and distribute this software is given under the
terms of the NumPy License.

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.

"""

fcpyfunc = {
    'c_double': "PyFloat_AsDouble",
    'c_float': "PyFloat_AsDouble",
}

fcpycode = {
    'c_float': 'f',
    'c_double': 'd',
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
    dret = []
    dretf = []
    for typedet in pymod.get('body')[0]['body'][0]['body']:
        defs = []
        fkinds = []
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
                fkinds.append(vkind)
                ckind = vkind.replace('c_', '')
                vdef = f"{ckind} {var};"
                cstruct_var.append(var)
                pyc_conv_fn.append(fcpyfunc.get(vkind))
                defs.append(vdef)
        if len(defs) > 0:
            cline = []
            structname = typedet['name']
            # XXX: Ugly hack, this forces
            # capi_buildvalue = Py_BuildValue("{s:f,s:f,s:f}","x", array.x,
            # "y", array.y,
            # "z", array.z -> Note the missing ,
            # );
            for i in range(len(defs)):
                dretf.append(f"s:{fcpycode.get(fkinds[i])}")
                # TODO: Stop harcoding array
                dret.append(f"""{',' if i==0 else ''}\
\t \"{cstruct_var[i]}\", array.{cstruct_var[i]}{'' if i==len(defs)-1 else ','}
                """)
                # TODO: Stop hardcoding vals
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
    # TODO: Document how these dictionary items get used in rules.py
    ret = {
        'typedefs_derivedtypes': res,
        'derived_returnformat': f"{{{','.join(dretf)}}}",
        'derived_return': dret
    }
    return ret
