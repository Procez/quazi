import copy
from .execute import Execution, default, repr
from .parsing import Expr, AssignExpr, NameExpr
import traceback

def console(condition = lambda: True):
    print('[Quazi v1.0.0-alpha]\n')
    
    _globals = copy.copy(default)

    while condition():
        lines = []
        while True:
            if not lines:
                code = input('>>> ')
            else:
                code = input('... ')
            lines.append(code)
            if len(code) == 0 or code.endswith(';'):
                break

        code = '\n'.join(lines)
        executor = Execution(code, _globals, interactive = True)
        out = executor.execute()
        out = out.obj
        if isinstance(out, NameExpr):
            out = executor.get(out.value)
        elif isinstance(out, AssignExpr):
            out = out.expr
        elif isinstance(out, Expr):
            out = executor.evaluate(out, _globals, _globals)
        if out != None:
            print(repr(out))
