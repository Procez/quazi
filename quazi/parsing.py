from lark.lark import Lark
from lark.visitors import v_args, Transformer
from pprint import PrettyPrinter
import os
import ast

_path, _ = os.path.split(__file__)

with open(os.path.join(_path, 'grammar.lark')) as f:
    parser = Lark(f.read())

def grammar_parse(text):
    return parser.parse(
        ''.join([i.lstrip('    ').lstrip(' ') for i in text.splitlines() if i != ''])
    )

def types_fix(l, types):
    return [i for i in l if not isinstance(i, types)]

def comma_fix(l):
    return types_fix(l, Comma)

def divide_chunks(l, n): 
    for i in range(0, len(l), n):  
        yield l[i:i + n]

class QzObject:
    pass

class PyObject:
    @classmethod
    def convert(cls, obj):
        if isinstance(obj, (int, float, str, dict, QzObject)):
            return obj
        if isinstance(obj, list):
            return [cls.convert(i) for i in obj]
        return PyObject(obj)
    @classmethod
    def fix(cls, obj):
        while isinstance(obj, PyObject):
            obj = object.__getattribute__(obj, 'obj')
        return obj
    def __init__(self, obj):
        obj = PyObject.fix(obj)
        self.obj = obj
    def __getattr__(self, name):
        obj = object.__getattribute__(self, 'obj')
        return PyObject.convert(object.__getattribute__(obj, name))
    def __call__(self, *args, **kwargs):
        obj = object.__getattribute__(self, 'obj')
        argz = [PyObject.fix(i) for i in args]
        kwargz = {k: PyObject.fix(v) for k, v in kwargs.items()}
        return PyObject.convert(obj(*argz, **kwargz))
    def __seqcall__(self, args, kwargs):
        return self(*args, **kwargs)
    def __repr__(self):
        obj = object.__getattribute__(self, 'obj')
        return f'PyObject({obj!r})'

class Expr(QzObject):
    pass

class Helper(Expr):
    def __init__(self, value, exprs):
        self.value = value
        self.exprs = exprs
    def __repr__(self):
        return f"Helper({self.value!r}, {self.exprs!r})"

class AttributeExpr(Expr):
    def __init__(self, expr, attr):
        self.expr = expr
        self.attr = attr
    def __repr__(self):
        return f'AttributeExpr({self.expr!r}, {self.attr!r})'

class AssignExpr(Expr):
    def __init__(self, name, expr):
        self.names = name
        self.expr = expr
    def __repr__(self):
        return f'AssignExpr({self.names!r}, {self.expr!r})'

class FunctionExpr(Expr):
    def __init__(self, names, expr):
        self.names = names
        self.expr = expr
    def __repr__(self):
        return f'FunctionExpr({self.names!r}, {self.expr!r})'

class FunctionGet(Expr):
    def __init__(self, value, exprs):
        self.value = value
        self.exprs = exprs
    def __repr__(self):
        return f'FunctionGet({self.value!r}, {self.exprs!r})'

class FunctionCall(Expr):
    def __init__(self, fget):
        self.fget = fget
    def __repr__(self):
        return f'FunctionCall({self.fget})'

class FScope(Expr):
    def __init__(self, func):
        self.func = func
    def __repr__(self):
        return f'FScope({self.func})'

class NameExpr(Expr):
    def __init__(self, name):
        self.value = name
    def __repr__(self):
        return f'NameExpr({self.value!r})'

class NameUnpackExpr(Expr):
    def __init__(self, expr):
        self.expr = expr
    def __repr__(self):
        return f'NameUnpackExpr({self.expr!r})'

class FnameExpr(Expr):
    def __init__(self, name):
        self.value = name
    def __repr__(self):
        return f'FnameExpr({self.value!r})'

class CodeBlock(Expr):
    def __init__(self, exprs):
        self.exprs = comma_fix(exprs)
    def __repr__(self):
        return f'CodeBlock({self.exprs!r})'

class List(Expr):
    def __init__(self, exprs):
        self.exprs = comma_fix(exprs)
    def __repr__(self):
        return f'List({self.exprs!r})'

class PairsExpr(Expr):
    def __init__(self, exprs):
        self.exprs = comma_fix(exprs)
    def __repr__(self):
        return f'Pairs({self.exprs!r})'

class Tuple(Expr):
    def __init__(self, exprs):
        self.exprs = comma_fix(exprs)
    def __repr__(self):
        return f'Tuple({self.exprs!r})'

class Names(Expr, list):
    def __init__(self, exprs):
        exprs = comma_fix(exprs)
        list.__init__(self, exprs)
        self.exprs = exprs
    def __repr__(self):
        return f'Names({self.exprs!r})'

class Dict(Expr):
    def __init__(self, exprs):
        self.exprs = exprs
    def __repr__(self):
        return f'Dict({self.exprs!r})'

class ArgData:
    def __init__(self, args, kwargs):
        self.args = args
        self.kwargs = kwargs
    def __repr__(self):
        return f'ArgData({self.args!r}, {self.kwargs!r})'

class Comma: pass
class Scomma: pass

@v_args(inline=True)
class Tranny(Transformer):
    def function(self, names, expr):
        return FunctionExpr(names, expr)
    def fscope(self, func):
        return FScope(func)
    def fcall(self, fget):
        return FunctionCall(fget)
    def fget(self, expr):
        return expr
    def fgetbase(self, name, exprs):
        return FunctionGet(name, exprs)
    def fgetcode(self, *data):
        data = types_fix(data, (Names, Comma))
        args = []
        fget, _args, code = data
        if _args != None:
            args.extend(_args)
        args.append(code)
        return FunctionGet(fget.value, ArgData(fget.exprs.args + args, fget.exprs.kwargs))
    def decorator(self, dec, func):
        return FunctionGet(dec, ArgData([func], []))
    def argdata(self, *args):
        if hasattr(args[-1], 'data') and args[-1].data == 'innerdict':
            *args, innerdict = args
            innerdict = list(divide_chunks(comma_fix(innerdict.children), 2))
        else:
            innerdict = []
        args = comma_fix(args)
        return ArgData(args, innerdict)
    def opargdata(self, expr = None):
        return expr
    def jnames(self, *names):
        return Names(names)
    def name(self, name):
        return NameExpr(name.value)
    def name_unpack(self, expr):
        return NameUnpackExpr(expr)
    def string(self, text):
        return ast.literal_eval(text.children[0])
    def nstring(self, name, string):
        return FunctionGet(name, [string])
    def list(self, *exprs):
        return List(exprs)
    def tuple(self, *exprs):
        return Tuple(exprs)
    def dict(self, innerdict):
        exprs = innerdict.children
        return Dict(list(divide_chunks(comma_fix(exprs), 2)))
    def expr(self, value):
        return value
    stmt = expr
    def pairitem(self, *values):
        return values
    def pairs(self, *pairs):
        return PairsExpr(pairs)
    def helpers(self, value):
        return Helper(value.data, value.children)
    def codeblock(self, *exprs):
        return CodeBlock(exprs)
    def names(self, *exprs):
        return Names(exprs)
    def names_empty(self):
        return Names([])
    def assign(self, names, expr):
        return AssignExpr(names, expr)
    def fname(self, name):
        return FnameExpr(name.value)
    def attribute(self, expr, attr):
        return AttributeExpr(expr, attr)
    def comma(self):
        return Comma()
    def scomma(self):
        return Scomma()

    int, float = int, float

def parse(text):
    data = grammar_parse(text)
    return Tranny().transform(data).children

if __name__ == "__main__":
    data = parse('''
{1: 2: 3, 4: 5: 6: 7, 8: 9}
''')
    print(data)
