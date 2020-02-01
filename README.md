# Quazi
Welcome to Quazi, my esolang (esoteric programming language). Quazi is a language built on the principles of only expressions, and evaluation control. Here are some key principles of Quazi:
## Quazi Principles
| Principle  | Meaning |
| ------------- | ------------- |
| Evaluation Control  | You can control evaluation in Quazi. Functions can take in arguments which haven't been evaluated. Code blocks can be created and evaluated at will.  |
| Expression Only | Everything is an expression in Quazi. Code Blocks are expressions which return null if no return call is done, otherwise returning the value that was called with the return function. |
| Unlimited Freedom | Do whatever you want! Quazi gives you unlimited freedom to override builtin names, manage modules, and etc. Even `if` and `for` are functions. |
| Explicit Control Flow | Using the local function, you can create an immediately evaluated function object to control the flow. |
| Local Snapshots | If a function is inside another function, it takes a snapshot of its locals, and that's that. Each function's locals become separate from then, but the two functions can share a mutable object like a dictionary. |
| Full Python Access | You can access any Python object and communicate with Python through the `pyimport` function, to import Python modules. |
## Examples
A basic script.
```js
x = 5;
print(5)
```
Iterate from 0 to 4.
```js
for(i, range(5)) {
  print(i);
}
```
Print a value dependent on a condition.
```js
condition = true;
if (condition) {
  print(5);
} else {
  print(2);
}
```
Evaluate a code block.
```js
block = { print(2); print(3) };
?block
```
Greatest common demoninator.
```js
  
gcd = (x, y) => {
    if(y == 0) {
        return(x);
    };
    return(gcd(y, x % y));
};
print(gcd(96, 124));```
