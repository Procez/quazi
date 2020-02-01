import re
import sympy
import math

def replace_span(string, span, new):
    return string[:span[0]] + new + string[span[1] + 1:]

def get_span(match):
    return match.start(), match.end() - 1

def groups(match):
    count = 0
    output = []
    while True:
        try:
            output.append(match.group(count))
        except:
            break
        count += 1
    return output

compiled = re.compile(r'(([0-9]+\.)?[0-9]+)?([a-z]+)')

def math_fix(string, extras=False, namespace = {}):
    variables = set()
    def fix_var(var):
        var = groups(var)[0]
        if var in namespace:
            return var
        else:
            for i in var:
                if re.match('[a-zA-Z_]', i):
                    variables.add(i)
            return '{}'
    my_match = list(compiled.finditer(string))
    match = []
    for x in my_match:
        g = groups(x)
        if g[0] not in globals():
            match.append(x)
    new = compiled.sub(fix_var, string)
    for y, x in enumerate(match):
        y += 1
        g = groups(x)
        try:
         l = len(g[1])
        except:
         l = 0
        n = '(' + ' * '.join(g[0][l:]) + ')' if len(g[0][1:]) > 1 or (l == 0 and len(g[0][l:]) > 1) else g[0][l:]
        if l != 0:
            n = f'({g[1]} * {n})'
        else:
            n = n
        new = new.format(n, *(
        ['{}' for x in range( len(match) - y )]
        ))
    if extras:
        return new, variables
    return new

class Formula:
    def __init__(self, text):
        self.text, self.vars = math_fix(text, extras = True, namespace = math.__dict__)
        self.func = eval(f'lambda {", ".join(map(str, self.vars))}: {self.text}')
    def __repr__(self):
        return f'Formula({self.text!r})'
    def __str__(self):
        return repr(self)
    def simplify(self):
        return Formula(sympy.simplify(self.text))
    def __call__(self, *args):
        return self.func(*args)

if __name__ == "__main__":
    print(Formula('2x * 3')(5))                
