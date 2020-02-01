from .parsing import *
from .formulas import Formula
import operator
import pprint
import copy
import inspect
import functools
import sys
import regex
from collections.abc import Iterable

operations = operator.__dict__
operations.update({
    'div': operator.truediv,
    'remainder': operator.mod
})

_format = regex.compile(r'\{(([^\{\}]+)|(?R))*+\}')

primitives = {
    str: {},
    int: {},
    float: {},
    dict: {
        'get': 'get',
    },
    list: {
        'get': '__getitem__',
    }
}

def unpack(names, value, single = False):
    if len(names) == 0:
        return {}
    if len(names) == 1 and ((not (len(names) == 2 and isinstance(names[-1], Scomma))) and not single):
        #SINGLE NAME | CANT BE TWO NAMES AND A COMMA UNLESS SINGLE
        return {names[0]: value}
    if len(names) > 1 and isinstance(names[-1], Scomma):
        names = names[:-1]
    out = {}
    extra = None
    if isinstance(names[-1], NameUnpackExpr):
        extra = names[-1].expr
        names = names[:-1]
    for n, v in zip(names, value):
        if isinstance(n, Iterable) and not isinstance(n, str) and isinstance(v, Iterable):
            out.update(unpack(n, v))
        else:
            out[n] = v
    if extra:
        out[extra] = value[len(names):]
    elif len(names) < len(value):
        raise ValueError(f'too many values to unpack (expected {len(names)})')
    elif len(names) > len(value):
        raise ValueError(f'not enough values to unpack (expected {len(names)}, got {len(value)})')
    return out

def to_str(obj, _str=str):
    if isinstance(obj, (dict, list, tuple, bool)) or obj in (None,):
        return repr(obj)
    if isinstance(obj, Instance):
        return f'<instance object at {hex(id(obj))}>'
    if isinstance(obj, Class):
        return f'<class object at {hex(id(obj))}>'
    return _str(obj)

def repr(obj, _repr=repr):
    if obj == None:
        return 'null'
    if type(obj) == bool:
        objstr = str(obj)
        return objstr[0].lower() + objstr[1:]
    if type(obj) == dict:
        out = ''
        for c, (k, v) in enumerate(obj.items()):
            c += 1
            out += f'{k}: {repr(v)}'
            if c != len(obj):
                out += ', '
        return f'[{out}]'
    if type(obj) == list:
        body = ', '.join(map(repr, obj))
        return f'[{body}]'
    if type(obj) == tuple:
        body = ', '.join(map(repr, obj))
        return f'({body})'
    if type(obj) in (Instance, Class):
        return to_str(obj)
    return _repr(obj)

class Code(QzObject):
    def __init__(self, exprs, _locals, _globals):
        self.exprs = exprs
        self.locals = _locals
        self.globals = _globals
        self.l = copy.copy(self.locals)

    def execute(self, catch = True):
        return Execution._execute(self.exprs, self.locals, self.globals, catch = catch)

    def __repr__(self):
        return f'Code({self.exprs!r}, {self.locals!r}, {self.globals!r})'


class Function(QzObject):
    def __init__(self, names, expr, _locals, _globals):
        self.names = names
        self.expr = expr
        self.locals = _locals
        self.globals = _globals

    def call(self, *args, _globals={}, _locals={}, catch = True):
        _locals.update(self.locals)
        _globals.update(self.globals)

        args = [Execution.evaluate(i, _globals, _locals) for i in args]
            
        _vars = {}
        
        for n, v in unpack(self.names, args, single = True).items():
            assign_single(n, v, _locals, _globals, _vars)
        
        _loc = {'__ref__': self}
        _loc.update(_globals)
        _loc.update(_locals)
        _loc.update(_vars)
        return Code(self.expr.exprs, _loc, _globals).execute(catch)

    def call_overwrite(self, *args, _globals, _locals=None, catch = True): #func = () => { foreach([1], (x) => { return(x) }) };
        if _locals == None:
            _locals = self.locals

        args = [Execution.evaluate(i, _globals, _locals) for i in args]

        _vars = {}
        for n, v in unpack(self.names, args, single = True).items():
            assign_single(n, v, _locals, _globals, _vars)
        
        _loc = {'__ref__': self}
        _loc.update(_globals)
        _loc.update(_locals)
        _loc.update(_vars)
        _locals.clear()
        _locals.update(_loc)
        return Code(self.expr.exprs, _locals, _globals).execute(catch)

    __call__ = call

class PyCall(QzObject):
    def __init__(self, func, args):
        self.func = func
        self.args = args
    def execute(self):
        args = []
        for i in self.args:
            while isinstance(i, PyObject):
                i = object.__getattribute__(i, 'obj')
            args.append(i)
        return self.func(*args)

class ReturnError(Exception):
    def __init__(self, *args):
        Exception.__init__(self, *args)
        self.value = self.args[0]

class Pairs:
    def __init__(self, pairs):
        self.pairs = pairs
    def __repr__(self):
        return f'Pairs({self.pairs})'
    def __str__(self):
        return repr(self)

class datafunc:
    def __init__(self, data, func):
        self.data = data
        self.func = func
    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

class data:
    def __init__(self, *data):
        self.data = data
    def __call__(self, func):
        return datafunc(self.data, func)

def do_return(obj):
    raise ReturnError(obj)


def do_pyimport(obj):
    return __import__(obj)

@data('unevaluated', 'unpythonify')
def do_local(args, _locals, _globals):
    args, kwargs = args.args, args.kwargs
    code, = args
    keys, vals = zip(*kwargs)
    return Execution.evaluate(FunctionGet(FunctionExpr(
        Names(keys),
        code
    ), ArgData(vals, [])), _locals, _globals)

@data('unevaluated', 'unpythonify')
def do_if(args, _locals, _globals):
    args = args.args
    conditions = []
    if len(args) == 3:
        condition, code, otherwise = args
    elif len(args) == 2:
        condition, code = args
        otherwise = None
    else:
        condition, code, *conditions = args
        if isinstance(conditions[-2], CodeBlock):
            otherwise = conditions[-1]
            conditions = conditions[:-1]
        else:
            otherwise = None
    _globals["__lastif__"] = Execution.evaluate(condition, _locals, _globals)
    if _globals["__lastif__"]:
        return Execution._execute(code.exprs, _locals, _globals, catch=False)
    if conditions:
        return do_if(conditions + [otherwise], _locals, _globals)
    if otherwise:
        Execution._execute(otherwise.exprs, _locals, _globals, catch=False)

@data('unevaluated', 'unpythonify')
def do_foreach(args, _locals, _globals):
    args = args.args
    seq, func = [Execution.evaluate(i, _locals, _globals) for i in args]
    if isinstance(seq, int):
        seq = range(seq)
    for i in seq:
        func.call_overwrite(i, _globals=_globals, _locals=_locals, catch = False)
    return i

@data('unevaluated', 'unpythonify')
def do_for(args, _locals, _globals):
    args = args.args
    func = FunctionExpr(Names([args[0]]), args[-1])
    return do_foreach([args[1], func], _locals, _globals)


@data('unevaluated', 'unpythonify')
def do_while(args, _locals, _globals):
    args = args.args
    condition, code = args
    while Execution.evaluate(condition, _locals, _globals):
        Execution._execute(code.exprs, _locals, _globals)

@data('unevaluated', 'unpythonify')
def do_until(args, _locals, _globals):
    args = args.args
    condition, code = args
    while not Execution.evaluate(condition, _locals, _globals):
        Execution._execute(code.exprs, _locals, _globals)

@data('unevaluated', 'unpythonify')
def do_fstring(args, _locals, _globals):
    args = args.args
    string, = args
    string = Execution.evaluate(string, _locals, _globals)
    match = list(_format.finditer(string))
    for i in match[::-1]:
        string = insert(i.start(), i.end(), string, str(Execution.evaluate(parse(i.group(1))[0], _locals, _globals)))
    return string

@data('unevaluated', 'unpythonify')
def do_class(args, _locals, _globals):
    args = args.args
    if len(args) == 1:
        *bases, code = [], args[0]
    else:
        *bases, code = args
    if isinstance(bases, Expr):
        bases = Execution.evaluate(bases, _locals, _globals)
    _loc = {}
    _loc.update(_locals)
    Execution._execute(code.exprs, _loc, _globals)
    new = {}
    for k, v in _loc.items():
        if k not in _locals or _locals[k] is not v:
            new[k] = v
    return Class(bases, new)

@data('unevaluated', 'unpythonify')
def do_switch(args, _locals, _globals):
    item, pairs = [Execution.evaluate(i, _locals, _globals) for i in args.args]
    pairs = pairs.pairs
    last = None
    success = False
    if len(pairs[-1]) == 1:
        *pairs, (default,) = pairs
    else:
        default = None
    for case, code in pairs:
        if (isinstance(case, Iterable) and code in case) or item == case:
            success = True
            last = Execution._execute(code.exprs, _locals, _globals)
    if not success and default:
        last = Execution._execute(default.exprs, _locals, _globals)
    return last

@data('unpythonify')
def do_print(*objs):
    print(' '.join(map(to_str, objs)))

def insert(start, end, origin, string):
  return origin[:start] + string + origin[end:]

class Class:
    def __init__(self, bases, dict):
        self.__bases__ = bases
        for i in bases:
            if isinstance(i, Class):
                self.__dict__.update(i.__dict__)
        self.__dict__.update(dict)
    def __new(self, inst, *args):
        self._new(inst, *args)

class Instance:
    def __init__(self, cls, *args):
        self.__dict__.update(cls.__dict__)
        for k, v in self.__dict__.items():
            if isinstance(v, Function):
                func = copy.copy(v)
                func.__inst__ = self
                self.__dict__[k] = func
        cls._Class__new(self, *args)

class extend:
    '''Extend a function with arguments'''

    def __init__(self, *args):
        '''Initialize this extension object.'''
        self.args = args

    def __call__(self, func):
        '''Decorate a function with this extension object, this extension's arguments are added to the function arguments.'''

        @functools.wraps(func)
        def new(*args, **kwargs):
            args = args + self.args
            func(*args, **kwargs)

        return new


default = {
    'return': PyObject(do_return),
    'pyimport': PyObject(do_pyimport),
    'print': PyObject(do_print),
    'if': PyObject(do_if),
    'foreach': PyObject(do_foreach),
    'for': PyObject(do_for),
    'range': PyObject(data('unpythonify')(range)),
    'while': PyObject(do_while),
    'until': PyObject(do_until),
    'exit': PyObject(sys.exit),
    'class': PyObject(do_class),
    'local': PyObject(do_local),
    'switch': PyObject(do_switch),

    'true': True,
    'false': False,
    'null': None,

    'f': PyObject(do_fstring),
    'm': PyObject(Formula)
}

def assign_single(name, val, _locals, _globals, _v = None):
    if _v == None:
        _v = _locals
    if isinstance(name, NameExpr):
        name = name.value
        _v[name] = val
    elif isinstance(name, AttributeExpr):
        expr = cls.evaluate(name.expr, _locals, _globals)
        object.__setattr__(expr, name.attr.value, val)
    return val

class LastExpression:
    def __init__(self, obj):
        self.obj = obj
    def __repr__(self):
        return f'LastExpression({self.obj})'

class Execution:
    def __init__(self, code, _globals = None, interactive = False):
        self.code = parse(code)
        if _globals == None:
            self.globals = copy.copy(default)
        else:
            self.globals = _globals
        self.interactive = interactive

    def get(self, name):
        return self.globals.get(name)

    @classmethod
    def evaluate(cls, expr, _locals, _globals):
        if isinstance(expr, (str, int, float)):
            return expr
        if isinstance(expr, PairsExpr):
            return Pairs([[cls.evaluate(x, _locals, _globals) for x in y] for y in expr.exprs])
        if isinstance(expr, AssignExpr):
            val = cls.evaluate(expr.expr, _locals, _globals)
            for n, v in unpack(expr.names, val).items():
                assign_single(n, v, _locals, _globals)
            return val
        if isinstance(expr, Helper):
            func = operations[expr.value]
            exprs = [cls.evaluate(i, _locals, _globals) for i in expr.exprs]
            return func(*exprs)
        if isinstance(expr, NameExpr):
            value = expr.value
            if value in _locals:
                return _locals[value]
            elif value in _globals:
                return _globals[value]
        if isinstance(expr, CodeBlock):
            return Code(expr.exprs, _locals, _globals)
        if isinstance(expr, FScope):
            expr.func._locals = _locals
            return expr.func
        if isinstance(expr, FunctionGet):
            func = cls.evaluate(expr.value, _locals, _globals)
            args = expr.exprs
            if isinstance(func, PyObject):
                if isinstance(PyObject.fix(func), datafunc):
                    out = func
                    if 'unevaluated' in func.obj.data:
                        out = out(args, _locals, _globals)
                    else:
                        out = out(*[cls.evaluate(i, _locals, _globals) for i in args.args], **{k: cls.evaluate(v, _locals, _globals) for k, v in args.kwargs})
                    if 'unpythonify' in func.obj.data:
                        out = PyObject.fix(out)
                    return out
                return PyObject.convert(func(*[cls.evaluate(i, _locals, _globals) for i in args.args], **{k: cls.evaluate(v, _locals, _globals) for k, v in args.kwargs}))
            if isinstance(func, Class):
                return Instance(func, *args)
            if hasattr(func, '__inst__'):
                args = (func.__inst__,) + args
            return func.call(*args.args, _locals = _locals, _globals = _globals)
        if isinstance(expr, FunctionCall):
            out = cls.evaluate(expr.fget, _locals, _globals)
            if isinstance(out, CodeBlock):
                out = Code(out.exprs, _locals, _globals)

            return out.execute()
        if isinstance(expr, FunctionExpr):
            if not isinstance(expr.expr, CodeBlock):
                return Function(expr.names, CodeBlock([FunctionCall(FunctionGet(NameExpr('return'), [expr.expr]))]),
                                _locals, _globals)
            return Function(expr.names, expr.expr, _locals, _globals)
        if isinstance(expr, AttributeExpr):
            obj = cls.evaluate(expr.expr, _locals, _globals)
            if type(obj) in primitives:
                attrs = primitives[type(obj)]
                attr = attrs[expr.attr.value]
                return PyObject(getattr(obj, attr))
            attr = expr.attr.value
            if isinstance(obj, PyObject) and attr == '__seqcall__':
                return PyObject(object.__getattribute__(obj, attr))
            return getattr(obj, attr)
        if isinstance(expr, List):
            return [cls.evaluate(i, _locals, _globals) for i in expr.exprs]
        if isinstance(expr, Tuple):
            return *(cls.evaluate(i, _locals, _globals) for i in expr.exprs),
        if isinstance(expr, Dict):
            return {k.value: cls.evaluate(v, _locals, _globals) for k, v in expr.exprs}
        if isinstance(expr, (Class, Instance)):
            return expr

    @classmethod
    def _execute(cls, body, _locals, _globals, catch=True, interactive = False):
        try:
            out = None
            for i in body:
                out = i
                if hasattr(i, 'data') and i.data == '_ambig':
                    out = i.children[0]
                if isinstance(i, Expr):
                    out = cls.evaluate(i, _locals, _globals)
                for k, v in _globals.items():
                    if k not in _locals:
                        _locals[k] = v
            if interactive:
                return LastExpression(out)
        except ReturnError as e:
            if not catch:
                raise
            return e.value

    def execute(self):
        return self._execute(self.code, self.globals, {}, interactive = self.interactive)
