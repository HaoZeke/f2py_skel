#!/usr/bin/env python3
"""

Build F90 derived types support for f2py2e.

Copyright 2020 NumPy developers,
Permission to use, modify, and distribute this software is given under the
terms of the NumPy License.

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.

"""


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
        if blockdef['block']=='type':
            del blockdef['parent_body']
            ret.append(blockdef)
    return ret

def buildhooks(pymod):
    res = []
    for typedet in pymod.get('body')[0]['body'][0]['body']:
        defs = []
        for var in [x for x in typedet.get('vars') if 'kindselector' in typedet['vars'][x].keys()]:
            if 'c_' not in  typedet['vars'][var]['kindselector']['kind']:
                continue
            else:
                vdef = f"""\
            {typedet['vars'][var]['kindselector']['kind'].replace('c_','')} {var};
            """
                defs.append(vdef)
        if len(defs)>0:
            res.append(f"""
    typedef struct {{
    {''.join(defs)}
    }} {typedet['name']};
    """)
    ret = {'typedefs_derivedtypes': res}
    return ret
