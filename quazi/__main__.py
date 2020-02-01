import sys
from .execute import Execution
from .interactive import console

args = sys.argv[1:]

if args:
    with open(args[0]) as f:
        executor = Execution(f.read())
    executor.execute()
else:
    console()
