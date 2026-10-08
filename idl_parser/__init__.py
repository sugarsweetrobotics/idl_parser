"""OMG IDL parser.

Parse IDL files (or IDL text) into a tree of definition objects::

    from idl_parser import parser
    global_module = parser.IDLParser().load(idl_text)
    my_module = global_module.module_by_name('my_module')

Start from :class:`idl_parser.parser.IDLParser`; the result is an
:class:`idl_parser.module.IDLModule` holding the global scope.
"""
#from parser import IDLParser
__all__=['parser', 'exception']



    
    
