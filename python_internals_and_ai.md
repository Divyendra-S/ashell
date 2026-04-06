# Python Internals & AI/ML Interview Preparation Guide

A thorough Q&A reference for Python + AI interviews. Each question includes a detailed explanation and code examples where applicable.

---

# Part 1: Python Internals

---

## 1. GIL (Global Interpreter Lock)

**Q: What is the GIL, why does it exist, and how does it affect concurrency?**

**A:** The GIL is a mutex in CPython that allows only one thread to hold control of the Python interpreter at any time. This means only one thread can execute Python bytecode at once, even on multi-core machines.

**Why it exists:** CPython's memory management (reference counting) is not thread-safe. Without the GIL, simultaneous reference count modifications from multiple threads would cause race conditions, leading to memory leaks or premature deallocation.

**Impact on threading vs multiprocessing:**

- **Threading:** Multiple threads exist but only one runs Python bytecode at a time. Useful for I/O-bound tasks (network requests, file I/O) because the GIL is released during I/O operations.
- **Multiprocessing:** Each process has its own Python interpreter and GIL. True parallelism is achieved, making it suitable for CPU-bound tasks.

```python
import threading
import multiprocessing
import time

def cpu_bound_work(n):
    """Simulate CPU-bound task."""
    total = 0
    for i in range(n):
        total += i * i
    return total

# Threading — GIL limits this to one core
def with_threads():
    threads = []
    start = time.time()
    for _ in range(4):
        t = threading.Thread(target=cpu_bound_work, args=(10_000_000,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    print(f"Threads: {time.time() - start:.2f}s")

# Multiprocessing — bypasses GIL, uses multiple cores
def with_processes():
    processes = []
    start = time.time()
    for _ in range(4):
        p = multiprocessing.Process(target=cpu_bound_work, args=(10_000_000,))
        processes.append(p)
        p.start()
    for p in processes:
        p.join()
    print(f"Processes: {time.time() - start:.2f}s")

# For CPU-bound work, multiprocessing will be ~4x faster on a 4-core machine.
# For I/O-bound work, threading is often sufficient and lighter weight.
```

**When it matters:** The GIL only matters for CPU-bound multi-threaded code. If your workload is I/O-bound (web scraping, API calls, database queries), threading works fine because the GIL is released during I/O waits.

**Note:** CPython 3.13+ introduced a free-threaded build (PEP 703) that can disable the GIL experimentally.

---

## 2. Memory Management & Garbage Collection

**Q: How does Python manage memory? Explain reference counting and the garbage collector.**

**A:** Python uses a combination of **reference counting** and a **cyclic garbage collector**.

**Reference counting:** Every object has a count of how many references point to it. When this count drops to zero, the memory is immediately freed.

```python
import sys

a = [1, 2, 3]
print(sys.getrefcount(a))  # 2 (a + the temporary ref from getrefcount)

b = a                       # refcount increases
print(sys.getrefcount(a))  # 3

del b                       # refcount decreases
print(sys.getrefcount(a))  # 2
```

**Circular references** are the weakness of reference counting:

```python
class Node:
    def __init__(self):
        self.ref = None

a = Node()
b = Node()
a.ref = b
b.ref = a   # circular reference

del a
del b
# refcount of both objects is still 1 (they reference each other)
# reference counting alone cannot free these
```

**Generational garbage collector:** Python's `gc` module handles circular references. It uses three generations (0, 1, 2). New objects start in generation 0. If they survive a collection cycle, they move to the next generation. Higher generations are collected less frequently (the assumption is that long-lived objects are less likely to become garbage).

```python
import gc

# Force a collection
gc.collect()

# Check thresholds — (700, 10, 10) by default
# Meaning: gen-0 collects after 700 allocations - deallocations,
# gen-1 after 10 gen-0 collections, gen-2 after 10 gen-1 collections
print(gc.get_threshold())

# Disable GC (sometimes done for performance-critical sections)
gc.disable()
# ... performance-critical code ...
gc.enable()

# See what the collector found
gc.set_debug(gc.DEBUG_STATS)
gc.collect()
```

**Weak references** (`weakref` module) let you reference an object without increasing its refcount, allowing it to be garbage collected.

```python
import weakref

class MyObj:
    pass

obj = MyObj()
weak = weakref.ref(obj)
print(weak())    # <__main__.MyObj object>

del obj
print(weak())    # None — object was collected
```

---

## 3. Mutable vs Immutable Types

**Q: What are mutable and immutable types in Python? What are the deeper implications?**

**A:**

- **Immutable:** `int`, `float`, `str`, `tuple`, `frozenset`, `bytes` — once created, their contents cannot change.
- **Mutable:** `list`, `dict`, `set`, `bytearray`, custom objects — contents can be modified in place.

**Deep implications:**

1. **Function arguments:** Mutable defaults are shared across calls (a classic gotcha).
2. **Hashability:** Only immutable objects can be dictionary keys or set members (they need a stable hash).
3. **Thread safety:** Immutable objects are inherently thread-safe.
4. **Copy behavior:** Assigning a mutable object creates a reference, not a copy.

```python
# Gotcha: mutable default argument
def append_to(element, target=[]):
    target.append(element)
    return target

print(append_to(1))  # [1]
print(append_to(2))  # [1, 2] — same list object!

# Fix: use None as default
def append_to_fixed(element, target=None):
    if target is None:
        target = []
    target.append(element)
    return target
```

**Tuples containing mutable objects:**

A tuple is immutable — you cannot change which objects it references. But if those objects are themselves mutable, their contents can change.

```python
t = ([1, 2], [3, 4])
# t[0] = [5, 6]   # TypeError — can't reassign tuple element
t[0].append(3)     # Works! The list itself is mutable
print(t)            # ([1, 2, 3], [3, 4])

# This means such a tuple is NOT hashable:
# hash(t)  # TypeError: unhashable type: 'list'
```

**Hashability rule:** An object is hashable if it has a `__hash__` method and its hash value never changes during its lifetime. Immutable containers are only hashable if all their elements are also hashable.

```python
hash((1, 2, 3))          # Works — tuple of immutables
# hash((1, [2, 3]))      # TypeError — tuple contains a list
hash(frozenset({1, 2}))  # Works
```

---

## 4. `is` vs `==`

**Q: What is the difference between `is` and `==`?**

**A:**

- `==` checks **value equality** — calls `__eq__`.
- `is` checks **identity** — whether two references point to the exact same object in memory (compares `id()`).

```python
a = [1, 2, 3]
b = [1, 2, 3]

print(a == b)   # True  — same value
print(a is b)   # False — different objects in memory
```

**Integer caching (small integer pool):** CPython caches integers from -5 to 256. Any variable assigned a value in this range points to the same cached object.

```python
a = 256
b = 256
print(a is b)   # True — cached

a = 257
b = 257
print(a is b)   # False in the REPL — different objects
# (Note: in a single compiled script, the compiler may optimize this to True)
```

**String interning:** CPython automatically interns strings that look like identifiers (alphanumeric + underscores). Other strings may or may not be interned depending on the compilation unit.

```python
a = "hello"
b = "hello"
print(a is b)   # True — interned

a = "hello world"
b = "hello world"
print(a is b)   # May be False in the REPL (not a valid identifier)

# You can force interning:
import sys
a = sys.intern("hello world")
b = sys.intern("hello world")
print(a is b)   # True
```

**Best practice:** Always use `==` for value comparisons. Use `is` only for singletons like `None`, `True`, `False`:

```python
x = None
if x is None:      # Correct
    pass
if x == None:      # Works but discouraged (can be overridden by __eq__)
    pass
```

---

## 5. Deep Copy vs Shallow Copy

**Q: What is the difference between deep copy and shallow copy?**

**A:**

- **Shallow copy:** Creates a new object but inserts references to the same child objects.
- **Deep copy:** Creates a new object and recursively copies all child objects.

```python
import copy

original = [[1, 2, 3], [4, 5, 6]]

# Shallow copy
shallow = copy.copy(original)
# Also: shallow = original[:] or list(original)

# Deep copy
deep = copy.deepcopy(original)

# Modify a nested list
original[0].append(99)

print(original)  # [[1, 2, 3, 99], [4, 5, 6]]
print(shallow)   # [[1, 2, 3, 99], [4, 5, 6]] — inner list is shared!
print(deep)      # [[1, 2, 3], [4, 5, 6]]     — fully independent
```

Visual breakdown:

```
original ──> [ ref_A, ref_B ]
                │        │
shallow  ──> [ ref_A, ref_B ]    # new outer list, SAME inner lists
                │        │
              [1,2,3]  [4,5,6]

deep     ──> [ ref_C, ref_D ]    # new outer list, NEW inner lists
                │        │
              [1,2,3]  [4,5,6]   # independent copies
```

**When each matters:**

- Shallow copy is fine when the container holds only immutable objects (ints, strings, tuples of immutables).
- Deep copy is needed when you have nested mutable structures and want full independence.
- `deepcopy` handles circular references correctly (it keeps a memo dict to avoid infinite recursion).

```python
# Circular reference handled by deepcopy
a = [1, 2]
a.append(a)        # a references itself
b = copy.deepcopy(a)
print(b[2] is b)   # True — deepcopy preserved the circular structure
print(b[2] is a)   # False — it's a copy, not the original
```

---

## 6. `__init__` vs `__new__`

**Q: What is the difference between `__init__` and `__new__`? How is an object created?**

**A:**

- `__new__` is the **constructor** — it creates and returns a new instance. It is a static method (implicitly) that takes the class as its first argument.
- `__init__` is the **initializer** — it sets up the already-created instance. It takes `self` (the instance created by `__new__`).

The lifecycle is: `__new__` creates the object, then `__init__` initializes it.

```python
class MyClass:
    def __new__(cls, *args, **kwargs):
        print(f"__new__ called, cls={cls}")
        instance = super().__new__(cls)
        return instance

    def __init__(self, value):
        print(f"__init__ called, self={self}")
        self.value = value

obj = MyClass(42)
# Output:
# __new__ called, cls=<class '__main__.MyClass'>
# __init__ called, self=<__main__.MyClass object at 0x...>
```

**Key difference:** `__new__` can return an instance of a different class (in which case `__init__` won't be called). `__init__` must return `None`.

**Singleton pattern using `__new__`:**

```python
class Singleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, value=None):
        # Note: __init__ is called every time Singleton() is called
        if value is not None:
            self.value = value

a = Singleton(1)
b = Singleton(2)
print(a is b)       # True — same instance
print(a.value)      # 2 — __init__ was called again with value=2
```

**When to override `__new__`:**

- Implementing singletons or object caching (flyweight pattern).
- Subclassing immutable types (`int`, `str`, `tuple`) where you need to control the value at creation time (since you can't modify them in `__init__`).

```python
class UpperStr(str):
    def __new__(cls, value):
        return super().__new__(cls, value.upper())

s = UpperStr("hello")
print(s)       # HELLO
print(type(s)) # <class '__main__.UpperStr'>
```

---

## 7. MRO (Method Resolution Order)

**Q: What is MRO and how does Python resolve method calls in multiple inheritance?**

**A:** MRO determines the order in which base classes are searched when looking for a method. Python uses the **C3 linearization** algorithm, which guarantees:

1. Children come before parents.
2. The order of parents in the class definition is preserved.
3. A consistent ordering exists (or Python raises a `TypeError`).

```python
class A:
    def method(self):
        print("A")

class B(A):
    def method(self):
        print("B")

class C(A):
    def method(self):
        print("C")

class D(B, C):
    pass

# Diamond inheritance: D -> B -> C -> A
print(D.__mro__)
# (<class 'D'>, <class 'B'>, <class 'C'>, <class 'A'>, <class 'object'>)

D().method()  # "B" — found in B first
```

**`super()` follows the MRO, not the parent class:**

```python
class A:
    def method(self):
        print("A.method")

class B(A):
    def method(self):
        print("B.method")
        super().method()  # next in MRO, not necessarily A

class C(A):
    def method(self):
        print("C.method")
        super().method()

class D(B, C):
    def method(self):
        print("D.method")
        super().method()

D().method()
# D.method
# B.method
# C.method   <-- super() in B goes to C, not A!
# A.method
```

This is **cooperative multiple inheritance**. Each class calls `super()`, which follows the MRO chain. This is why `super()` in `B` calls `C.method()` — because in the context of `D`, the MRO is D -> B -> C -> A.

**When C3 linearization fails:**

```python
# class X(B, A): pass  # where B inherits from A
# This would fail if it violates the C3 rules
# Python raises TypeError: Cannot create a consistent method resolution order
```

---

## 8. Metaclasses

**Q: What are metaclasses in Python?**

**A:** A metaclass is the "class of a class." Just as a class defines how instances behave, a metaclass defines how classes behave. In Python, `type` is the default metaclass.

```python
# These are equivalent:
class MyClass:
    x = 10

MyClass = type('MyClass', (), {'x': 10})

print(type(MyClass))  # <class 'type'>
print(type(int))      # <class 'type'>
```

**The relationship:** `type` is an instance of itself and also a subclass of `object`. `object` is an instance of `type`. This is bootstrapped at the C level.

**Creating a custom metaclass:**

```python
class ValidatedMeta(type):
    def __new__(mcs, name, bases, namespace):
        # Enforce that all classes using this metaclass must have a 'validate' method
        if 'validate' not in namespace and name != 'ValidatedBase':
            raise TypeError(f"{name} must define a 'validate' method")
        return super().__new__(mcs, name, bases, namespace)

class ValidatedBase(metaclass=ValidatedMeta):
    pass

class User(ValidatedBase):
    def validate(self):
        return bool(self.name)

# class BadModel(ValidatedBase):
#     pass
# TypeError: BadModel must define a 'validate' method
```

**Practical use cases:**

- ORMs (Django models use metaclasses to turn class attributes into database columns).
- API frameworks that register classes automatically.
- Enforcing coding contracts/interfaces.
- Singleton implementation.

**`__init_subclass__` (Python 3.6+) is often a simpler alternative:**

```python
class Plugin:
    _registry = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        Plugin._registry[cls.__name__] = cls

class PDFPlugin(Plugin):
    pass

class CSVPlugin(Plugin):
    pass

print(Plugin._registry)
# {'PDFPlugin': <class '__main__.PDFPlugin'>, 'CSVPlugin': <class '__main__.CSVPlugin'>}
```

---

## 9. Descriptors Protocol

**Q: What are descriptors and how does `@property` work under the hood?**

**A:** A descriptor is any object that defines `__get__`, `__set__`, or `__delete__`. Descriptors are the mechanism behind properties, methods, static methods, class methods, and `super()`.

- **Data descriptor:** Defines `__set__` and/or `__delete__` (takes priority over instance `__dict__`).
- **Non-data descriptor:** Defines only `__get__` (instance `__dict__` takes priority).

```python
class Verbose:
    """A descriptor that logs access."""
    def __set_name__(self, owner, name):
        self.name = name
        self.private_name = f'_{name}'

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        value = getattr(obj, self.private_name, None)
        print(f"Getting {self.name}: {value}")
        return value

    def __set__(self, obj, value):
        print(f"Setting {self.name} to {value}")
        setattr(obj, self.private_name, value)

    def __delete__(self, obj):
        print(f"Deleting {self.name}")
        delattr(obj, self.private_name)

class Person:
    name = Verbose()
    age = Verbose()

p = Person()
p.name = "Alice"    # Setting name to Alice
p.age = 30          # Setting age to 30
print(p.name)       # Getting name: Alice \n Alice
```

**How `@property` works — it is a descriptor:**

```python
# This:
class Circle:
    def __init__(self, radius):
        self._radius = radius

    @property
    def radius(self):
        return self._radius

    @radius.setter
    def radius(self, value):
        if value < 0:
            raise ValueError("Radius must be non-negative")
        self._radius = value

# Is equivalent to:
class Circle:
    def __init__(self, radius):
        self._radius = radius

    def _get_radius(self):
        return self._radius

    def _set_radius(self, value):
        if value < 0:
            raise ValueError("Radius must be non-negative")
        self._radius = value

    radius = property(_get_radius, _set_radius)
```

**Lookup order:** For `obj.attr`:
1. Data descriptors from `type(obj).__mro__`
2. Instance `__dict__`
3. Non-data descriptors from `type(obj).__mro__`

---

## 10. Context Managers

**Q: How do context managers work? What are `__enter__` and `__exit__`?**

**A:** A context manager is an object that defines `__enter__` (called at the start of the `with` block) and `__exit__` (called at the end, even if an exception occurs).

```python
class Timer:
    def __enter__(self):
        import time
        self.start = time.perf_counter()
        return self  # this is bound to the 'as' variable

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        self.elapsed = time.perf_counter() - self.start
        print(f"Elapsed: {self.elapsed:.4f}s")
        return False  # do not suppress exceptions

with Timer() as t:
    sum(range(1_000_000))
# Elapsed: 0.0234s
```

**Exception handling in `__exit__`:**

```python
class SuppressErrors:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is ValueError:
            print(f"Suppressed ValueError: {exc_val}")
            return True  # returning True suppresses the exception
        return False      # other exceptions propagate

with SuppressErrors():
    raise ValueError("oops")  # suppressed
print("Continues normally")

# with SuppressErrors():
#     raise TypeError("oops")  # NOT suppressed, propagates
```

**`contextlib.contextmanager` — create context managers from generators:**

```python
from contextlib import contextmanager

@contextmanager
def temp_directory():
    import tempfile, shutil, os
    dirpath = tempfile.mkdtemp()
    print(f"Created {dirpath}")
    try:
        yield dirpath           # everything before yield = __enter__
    finally:
        shutil.rmtree(dirpath)  # everything after yield = __exit__
        print(f"Cleaned up {dirpath}")

with temp_directory() as d:
    print(f"Working in {d}")
```

---

## 11. Iterators vs Generators

**Q: What is the iterator protocol? How do generators differ from iterators?**

**A:** The **iterator protocol** requires two methods:

- `__iter__()` — returns the iterator object itself.
- `__next__()` — returns the next value or raises `StopIteration`.

An **iterable** is anything with `__iter__()` that returns an iterator.

```python
class Countdown:
    def __init__(self, start):
        self.start = start

    def __iter__(self):
        return CountdownIterator(self.start)

class CountdownIterator:
    def __init__(self, current):
        self.current = current

    def __iter__(self):
        return self

    def __next__(self):
        if self.current <= 0:
            raise StopIteration
        self.current -= 1
        return self.current + 1

for n in Countdown(5):
    print(n, end=" ")  # 5 4 3 2 1
```

**Generators** are a simpler way to create iterators:

```python
def countdown(start):
    while start > 0:
        yield start
        start -= 1

for n in countdown(5):
    print(n, end=" ")  # 5 4 3 2 1
```

**Generator expressions** (lazy list comprehensions):

```python
# List comprehension — creates all values in memory
squares_list = [x**2 for x in range(1_000_000)]

# Generator expression — lazy, one value at a time
squares_gen = (x**2 for x in range(1_000_000))
```

**`yield from`** delegates to a sub-generator:

```python
def flatten(nested):
    for item in nested:
        if isinstance(item, list):
            yield from flatten(item)  # delegate recursively
        else:
            yield item

print(list(flatten([1, [2, [3, 4], 5], 6])))
# [1, 2, 3, 4, 5, 6]
```

**Key differences:**
- Generators are iterators (they implement the protocol automatically).
- Generators are lazy — they compute values on demand, saving memory.
- Generator state is suspended and resumed at each `yield`.
- You can only iterate through a generator once.

---

## 12. `*args` and `**kwargs`

**Q: How do `*args`, `**kwargs`, and the various parameter types work?**

**A:**

- `*args` collects extra positional arguments into a tuple.
- `**kwargs` collects extra keyword arguments into a dict.

```python
def example(*args, **kwargs):
    print(f"args: {args}")
    print(f"kwargs: {kwargs}")

example(1, 2, 3, name="Alice", age=30)
# args: (1, 2, 3)
# kwargs: {'name': 'Alice', 'age': 30}
```

**Argument unpacking:**

```python
def add(a, b, c):
    return a + b + c

args = (1, 2, 3)
print(add(*args))  # 6

kwargs = {'a': 1, 'b': 2, 'c': 3}
print(add(**kwargs))  # 6
```

**Positional-only parameters (PEP 570, Python 3.8+):**

Parameters before `/` are positional-only:

```python
def greet(name, /, greeting="Hello"):
    return f"{greeting}, {name}!"

greet("Alice")                  # OK
greet("Alice", greeting="Hi")  # OK
# greet(name="Alice")           # TypeError — name is positional-only
```

**Keyword-only parameters (PEP 3102):**

Parameters after `*` (or after `*args`) are keyword-only:

```python
def connect(host, port, *, timeout=10, retries=3):
    print(f"Connecting to {host}:{port}, timeout={timeout}")

connect("localhost", 8080, timeout=30)  # OK
# connect("localhost", 8080, 30)        # TypeError — timeout is keyword-only
```

**Full parameter order:**

```python
def full_example(pos_only, /, normal, *, kw_only):
    pass

# pos_only  — positional-only (before /)
# normal    — positional or keyword
# kw_only   — keyword-only (after *)
```

---

## 13. Closures and the Late Binding Gotcha

**Q: What are closures? What is the late binding trap?**

**A:** A **closure** is a function that captures variables from its enclosing scope. The function "closes over" those variables and retains access to them even after the enclosing function has returned.

```python
def make_multiplier(factor):
    def multiply(x):
        return x * factor  # 'factor' is captured from enclosing scope
    return multiply

double = make_multiplier(2)
triple = make_multiplier(3)

print(double(5))  # 10
print(triple(5))  # 15

# The closure captures the variable:
print(double.__closure__[0].cell_contents)  # 2
```

**The late binding gotcha:** Closures capture **variables**, not **values**. The variable is looked up at call time, not at definition time.

```python
# THE BUG:
functions = []
for i in range(5):
    functions.append(lambda: i)

print([f() for f in functions])
# [4, 4, 4, 4, 4] — all return 4, the final value of i!
```

All the lambdas close over the same variable `i`. By the time they are called, the loop has finished and `i` is 4.

**Fixes:**

```python
# Fix 1: Default argument (captures the value at definition time)
functions = []
for i in range(5):
    functions.append(lambda i=i: i)
print([f() for f in functions])  # [0, 1, 2, 3, 4]

# Fix 2: Use a factory function (creates a new scope each iteration)
def make_func(val):
    return lambda: val

functions = [make_func(i) for i in range(5)]
print([f() for f in functions])  # [0, 1, 2, 3, 4]

# Fix 3: functools.partial
from functools import partial
functions = [partial(lambda x: x, i) for i in range(5)]
print([f() for f in functions])  # [0, 1, 2, 3, 4]
```

---

## 14. Name Mangling

**Q: What is name mangling? What is the difference between `_var` and `__var`?**

**A:**

- `_var` — **convention only**. Signals "this is internal/private." Python does nothing special; it is purely a hint to other programmers.
- `__var` (double leading underscore) — **name mangling**. Python rewrites the name to `_ClassName__var` to avoid accidental collisions in subclasses.
- `__var__` (double leading and trailing) — **dunder/magic methods**. Reserved for Python's special protocol methods. No mangling.

```python
class Parent:
    def __init__(self):
        self._protected = "accessible but 'internal'"
        self.__private = "name-mangled"

class Child(Parent):
    def __init__(self):
        super().__init__()
        self.__private = "child's own version"

obj = Child()

# The name mangling in action:
print(obj.__dict__)
# {'_protected': "accessible but 'internal'",
#  '_Parent__private': 'name-mangled',
#  '_Child__private': "child's own version"}

print(obj._protected)       # Works fine
# print(obj.__private)      # AttributeError
print(obj._Parent__private) # "name-mangled" — still accessible if you know the mangled name
print(obj._Child__private)  # "child's own version"
```

**Why name mangling exists:** It prevents accidental overriding in subclasses. It is NOT a security feature — you can always access the mangled name. It is a namespace collision avoidance mechanism.

---

## 15. `__slots__`

**Q: What does `__slots__` do and when should you use it?**

**A:** By default, Python stores instance attributes in a per-instance `__dict__` (a dictionary). `__slots__` replaces this with a fixed set of slots, using a more compact internal structure.

```python
class WithDict:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class WithSlots:
    __slots__ = ('x', 'y')
    def __init__(self, x, y):
        self.x = x
        self.y = y

import sys

d = WithDict(1, 2)
s = WithSlots(1, 2)

print(sys.getsizeof(d) + sys.getsizeof(d.__dict__))  # ~200 bytes
print(sys.getsizeof(s))                                # ~56 bytes

# Cannot add arbitrary attributes with __slots__:
d.z = 3    # Works
# s.z = 3  # AttributeError: 'WithSlots' object has no attribute 'z'
```

**Benefits:**
- 40-50% less memory per instance (no per-instance `__dict__`).
- Slightly faster attribute access.

**Restrictions:**
- Cannot add attributes not listed in `__slots__`.
- Cannot use `__slots__` with multiple inheritance if more than one parent has non-empty slots (unless carefully designed).
- Subclasses still get a `__dict__` unless they also define `__slots__`.
- No `__weakref__` by default (add it to slots if needed).

**When to use:** When you have many instances (millions) of a class with a fixed set of attributes (e.g., data points, nodes in a graph).

---

## 16. Python Bytecode

**Q: How does Python execute code? What is bytecode?**

**A:** Python is a compiled-then-interpreted language:

1. Source code (`.py`) is compiled to **bytecode** (`.pyc` files in `__pycache__/`).
2. The CPython virtual machine (a stack-based VM) executes the bytecode.

```python
import dis

def add(a, b):
    return a + b

dis.dis(add)
# Output:
#   2           0 LOAD_FAST                0 (a)
#               2 LOAD_FAST                1 (b)
#               4 BINARY_ADD
#               6 RETURN_VALUE
```

**Examining code objects:**

```python
def example(x):
    y = x + 1
    return y * 2

code = example.__code__
print(code.co_varnames)   # ('x', 'y')
print(code.co_consts)     # (None, 1, 2)
print(code.co_stacksize)  # 2
print(code.co_code)       # raw bytecode bytes
```

**`.pyc` files:**
- Stored in `__pycache__/` with names like `module.cpython-312.pyc`.
- Contain a magic number (Python version), timestamp, source size, and the marshalled code object.
- Python checks if the `.pyc` is up to date before using it.

**`compile()` built-in:**

```python
source = "print('hello')"
code = compile(source, '<string>', 'exec')
exec(code)  # hello

dis.dis(code)
# Shows the bytecode for the compiled source
```

**Why this matters:** Understanding bytecode helps you reason about performance, understand how Python optimizations work (e.g., constant folding, peephole optimizations), and debug complex issues.

---

## 17. `asyncio`

**Q: How does asyncio work? When should you use it vs threading?**

**A:** `asyncio` is Python's framework for **cooperative multitasking** using an event loop. Coroutines voluntarily yield control (at `await` points), allowing other coroutines to run.

```python
import asyncio

async def fetch_data(url, delay):
    print(f"Fetching {url}...")
    await asyncio.sleep(delay)  # simulates I/O — yields control here
    print(f"Done fetching {url}")
    return f"Data from {url}"

async def main():
    # Run concurrently using tasks
    tasks = [
        asyncio.create_task(fetch_data("api/users", 2)),
        asyncio.create_task(fetch_data("api/posts", 1)),
        asyncio.create_task(fetch_data("api/comments", 3)),
    ]
    results = await asyncio.gather(*tasks)
    print(results)

asyncio.run(main())
# Total time: ~3 seconds (not 6), because they run concurrently
```

**Key concepts:**

- **Coroutine:** A function defined with `async def`. Calling it returns a coroutine object (doesn't execute until awaited).
- **`await`:** Suspends the coroutine and gives control back to the event loop.
- **Event loop:** The central scheduler that runs coroutines and callbacks.
- **Task:** A wrapper that schedules a coroutine to run concurrently.

**asyncio vs threading:**

| Aspect | asyncio | threading |
|--------|---------|-----------|
| Concurrency model | Cooperative (explicit `await`) | Preemptive (OS switches) |
| GIL impact | Not affected (single-threaded) | Limited by GIL |
| Best for | High-concurrency I/O (thousands of connections) | Simpler I/O parallelism |
| Overhead | Very low (no OS threads) | Higher (OS thread per task) |
| Debugging | Easier (deterministic switching) | Harder (race conditions) |

```python
# Async context manager and iterator examples:

async def async_generator():
    for i in range(5):
        await asyncio.sleep(0.1)
        yield i

async def main():
    async for value in async_generator():
        print(value)

    # Async context manager
    # async with aiohttp.ClientSession() as session:
    #     async with session.get(url) as response:
    #         data = await response.json()
```

---

## 18. Type Hints and the `typing` Module

**Q: How do type hints work in Python? Are they enforced at runtime?**

**A:** Type hints are **annotations** — they are metadata for tools (mypy, pyright, IDEs) and are **NOT enforced at runtime** by default.

```python
def greet(name: str, times: int = 1) -> str:
    return (f"Hello, {name}! " * times).strip()

# This runs fine despite the wrong types — Python does not check:
result = greet(42, "three")  # no runtime error from annotations
```

**Common typing constructs:**

```python
from typing import (
    List, Dict, Tuple, Set, Optional, Union,
    Callable, Iterator, Generator,
    TypeVar, Generic, Protocol, Literal,
    TypeAlias, TypeGuard
)

# Basic container types (Python 3.9+ can use list[int] directly)
def process(items: list[int]) -> dict[str, int]:
    return {str(i): i for i in items}

# Optional = Union[X, None]
def find_user(user_id: int) -> Optional[str]:
    return None

# Union types (Python 3.10+ can use X | Y)
def parse(value: int | str) -> str:
    return str(value)

# Callable
def apply(func: Callable[[int, int], int], a: int, b: int) -> int:
    return func(a, b)

# TypeVar and Generic
T = TypeVar('T')

class Stack(Generic[T]):
    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> T:
        return self._items.pop()

stack: Stack[int] = Stack()
stack.push(1)

# Protocol (structural subtyping / duck typing for type checkers)
class Drawable(Protocol):
    def draw(self) -> None: ...

class Circle:
    def draw(self) -> None:
        print("Drawing circle")

def render(shape: Drawable) -> None:
    shape.draw()

render(Circle())  # OK — Circle has draw(), satisfies the Protocol

# Literal
def set_mode(mode: Literal["read", "write"]) -> None:
    pass
```

**Runtime access to annotations:**

```python
import typing

def example(x: int, y: str) -> bool:
    pass

print(typing.get_type_hints(example))
# {'x': <class 'int'>, 'y': <class 'str'>, 'return': <class 'bool'>}
```

---

## 19. LEGB Rule

**Q: What is the LEGB rule? How does Python resolve variable names?**

**A:** LEGB stands for the scope resolution order:

1. **L — Local:** Inside the current function.
2. **E — Enclosing:** Inside any enclosing function (for closures).
3. **G — Global:** At the module level.
4. **B — Built-in:** Python's built-in names (`len`, `print`, `range`, etc.).

```python
x = "global"

def outer():
    x = "enclosing"

    def inner():
        x = "local"
        print(x)  # "local" — found at L

    inner()
    print(x)  # "enclosing" — found at L (outer's local)

outer()
print(x)  # "global" — found at G
```

**`global` and `nonlocal`:**

```python
count = 0

def increment():
    global count        # refers to the module-level 'count'
    count += 1

increment()
print(count)  # 1

def outer():
    value = 10
    def inner():
        nonlocal value  # refers to 'value' in 'outer'
        value += 1
    inner()
    print(value)  # 11

outer()
```

**Common gotcha — UnboundLocalError:**

```python
x = 10

def broken():
    print(x)  # UnboundLocalError!
    x = 20    # This assignment makes Python treat x as local in the entire function

# Python decides at compile time whether a variable is local or global.
# Since x is assigned inside broken(), Python treats it as local
# throughout the entire function — including the print before the assignment.
```

---

## 20. Python's Data Model (Dunder Methods)

**Q: What is the Python data model? How do you make custom objects behave like built-in types?**

**A:** Python's data model is the set of special ("dunder") methods that let you hook into language features. By implementing these methods, your objects can support operators, iteration, context management, comparison, and more.

```python
class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    # String representations
    def __repr__(self):
        return f"Vector({self.x}, {self.y})"

    def __str__(self):
        return f"({self.x}, {self.y})"

    # Arithmetic operators
    def __add__(self, other):
        return Vector(self.x + other.x, self.y + other.y)

    def __mul__(self, scalar):
        return Vector(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar):
        return self.__mul__(scalar)

    # Comparison
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))

    # Make it behave like a sequence
    def __len__(self):
        return 2

    def __getitem__(self, index):
        if index == 0: return self.x
        if index == 1: return self.y
        raise IndexError

    def __iter__(self):
        yield self.x
        yield self.y

    # Absolute value (magnitude)
    def __abs__(self):
        return (self.x**2 + self.y**2) ** 0.5

    # Boolean conversion
    def __bool__(self):
        return abs(self) > 0

    # Callable
    def __call__(self, scale):
        return Vector(self.x * scale, self.y * scale)

v1 = Vector(3, 4)
v2 = Vector(1, 2)

print(v1 + v2)      # (4, 6)
print(3 * v1)        # (9, 12)
print(abs(v1))       # 5.0
print(len(v1))       # 2
print(v1[0])         # 3
print(list(v1))      # [3, 4]
print(v1(10))        # (30, 40)
```

**Key categories of dunder methods:**
- **Creation/destruction:** `__new__`, `__init__`, `__del__`
- **String/repr:** `__str__`, `__repr__`, `__format__`
- **Comparison:** `__eq__`, `__lt__`, `__le__`, `__gt__`, `__ge__` (use `@functools.total_ordering` for convenience)
- **Arithmetic:** `__add__`, `__sub__`, `__mul__`, `__truediv__`, and their `r` and `i` variants
- **Container:** `__len__`, `__getitem__`, `__setitem__`, `__delitem__`, `__contains__`
- **Attribute access:** `__getattr__`, `__setattr__`, `__delattr__`, `__getattribute__`
- **Callable:** `__call__`
- **Context manager:** `__enter__`, `__exit__`
- **Hashing:** `__hash__`

---

## 21. `@property`, `@staticmethod`, `@classmethod`

**Q: What are the differences between these decorators?**

**A:**

```python
class Temperature:
    def __init__(self, celsius):
        self._celsius = celsius

    @property
    def celsius(self):
        """Getter — accessed like an attribute, not a method call."""
        return self._celsius

    @celsius.setter
    def celsius(self, value):
        if value < -273.15:
            raise ValueError("Below absolute zero!")
        self._celsius = value

    @property
    def fahrenheit(self):
        """Computed property."""
        return self._celsius * 9/5 + 32

    @classmethod
    def from_fahrenheit(cls, f):
        """Alternative constructor. Receives the class, not an instance.
        Works correctly with subclasses."""
        return cls((f - 32) * 5/9)

    @staticmethod
    def is_valid(value):
        """Utility function. No access to instance or class.
        Logically belongs to the class but doesn't need self or cls."""
        return value >= -273.15

# Usage:
t = Temperature(100)
print(t.celsius)       # 100 — property getter (no parentheses)
print(t.fahrenheit)    # 212.0 — computed property
t.celsius = 0          # property setter
# t.celsius = -300     # ValueError

t2 = Temperature.from_fahrenheit(32)  # classmethod as factory
print(t2.celsius)      # 0.0

print(Temperature.is_valid(-500))  # False — staticmethod
```

**When to use each:**

- `@property` — When you want attribute-style access with validation, computation, or lazy loading. Replaces Java-style getters/setters.
- `@classmethod` — Alternative constructors, or methods that need to work with the class hierarchy (polymorphic constructors).
- `@staticmethod` — Utility functions that logically belong to the class but don't need access to instance or class state. Could be a standalone function but makes more sense grouped with the class.

---

## 22. `with` Statement Internals

**Q: How does the `with` statement work internally?**

**A:** The `with` statement is syntactic sugar for a `try`/`finally` pattern using the context manager protocol.

```python
# This:
with expr as var:
    body

# Translates roughly to:
manager = expr
var = manager.__enter__()
try:
    body
except BaseException as exc:
    if not manager.__exit__(type(exc), exc, exc.__traceback__):
        raise  # re-raise if __exit__ returns falsy
else:
    manager.__exit__(None, None, None)
```

**Exception handling details:**

`__exit__` receives three arguments: `(exc_type, exc_val, exc_tb)`. If no exception occurred, all three are `None`. If `__exit__` returns `True`, the exception is suppressed.

```python
class ManagedResource:
    def __enter__(self):
        print("Acquiring resource")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Releasing resource")
        if exc_type is not None:
            print(f"Exception caught: {exc_type.__name__}: {exc_val}")
        # return True to suppress, False/None to propagate
        return False

# Multiple context managers (Python 3.1+ for single line, 3.10+ with parenthesized):
with open("a.txt") as f1, open("b.txt") as f2:
    pass

# Python 3.10+ parenthesized:
with (
    open("a.txt") as f1,
    open("b.txt") as f2,
):
    pass
```

**`contextlib` utilities:**

```python
from contextlib import suppress, redirect_stdout, ExitStack

# suppress — cleaner than try/except/pass
with suppress(FileNotFoundError):
    os.remove("nonexistent.txt")

# ExitStack — dynamic number of context managers
with ExitStack() as stack:
    files = [stack.enter_context(open(f)) for f in filenames]
```

---

## 23. Monkey Patching

**Q: What is monkey patching? When is it useful and what are the dangers?**

**A:** Monkey patching is dynamically modifying a class or module at runtime.

```python
# Original class
class Calculator:
    def add(self, a, b):
        return a + b

# Monkey patch: add a new method
Calculator.subtract = lambda self, a, b: a - b

calc = Calculator()
print(calc.subtract(10, 3))  # 7

# Monkey patch: replace an existing method
original_add = Calculator.add
Calculator.add = lambda self, a, b: original_add(self, a, b) + 0.0001  # floating point version
```

**Useful for testing (mocking):**

```python
# In production code:
import requests

def get_user(user_id):
    response = requests.get(f"https://api.example.com/users/{user_id}")
    return response.json()

# In tests — monkey patch requests.get:
def mock_get(url):
    class MockResponse:
        def json(self):
            return {"id": 1, "name": "Test User"}
    return MockResponse()

# Using unittest.mock (the proper way):
from unittest.mock import patch

with patch('requests.get', side_effect=mock_get):
    user = get_user(1)
    print(user)  # {'id': 1, 'name': 'Test User'}
```

**Dangers:**

1. **Breaks expectations** — other code relying on the original behavior will break silently.
2. **Hard to debug** — the modification is invisible in the source code.
3. **Fragile** — library updates may break the patch.
4. **Order-dependent** — multiple patches can conflict.
5. **Not thread-safe** — patching during execution can cause race conditions.

**When it is appropriate:** Testing/mocking, hot-fixing production bugs temporarily, compatibility shims.

---

## 24. Duck Typing

**Q: What is duck typing? What are EAFP and LBYL?**

**A:** "If it walks like a duck and quacks like a duck, it's a duck." In Python, you don't check an object's type — you check whether it has the methods/attributes you need.

```python
# Duck typing — we don't care about the type, only the interface:
class Duck:
    def quack(self):
        return "Quack!"

class Person:
    def quack(self):
        return "I'm quacking like a duck!"

def make_it_quack(thing):
    print(thing.quack())  # works for any object with a quack() method

make_it_quack(Duck())    # Quack!
make_it_quack(Person())  # I'm quacking like a duck!
```

**EAFP vs LBYL:**

- **EAFP (Easier to Ask Forgiveness than Permission)** — Pythonic. Try the operation and handle exceptions.
- **LBYL (Look Before You Leap)** — Check conditions before acting.

```python
# LBYL style (less Pythonic):
if hasattr(obj, 'read'):
    data = obj.read()
else:
    raise TypeError("Object is not readable")

# EAFP style (Pythonic):
try:
    data = obj.read()
except AttributeError:
    raise TypeError("Object is not readable")
```

**`Protocol` class — duck typing for static type checkers:**

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Readable(Protocol):
    def read(self) -> str: ...

class FileWrapper:
    def read(self) -> str:
        return "file data"

class StringWrapper:
    def read(self) -> str:
        return "string data"

def process(source: Readable) -> str:
    return source.read()

# Both work — structural subtyping, no explicit inheritance needed
process(FileWrapper())
process(StringWrapper())

# runtime_checkable allows isinstance checks:
print(isinstance(FileWrapper(), Readable))  # True
```

---

## 25. Abstract Base Classes

**Q: What are ABCs and when should you use them?**

**A:** ABCs let you define interfaces that subclasses must implement. They bridge duck typing and explicit contracts.

```python
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def area(self) -> float:
        """Subclasses MUST implement this."""
        pass

    @abstractmethod
    def perimeter(self) -> float:
        pass

    def describe(self):
        """Concrete method — inherited by subclasses."""
        return f"Shape with area={self.area():.2f} and perimeter={self.perimeter():.2f}"

class Circle(Shape):
    def __init__(self, radius):
        self.radius = radius

    def area(self):
        import math
        return math.pi * self.radius ** 2

    def perimeter(self):
        import math
        return 2 * math.pi * self.radius

# shape = Shape()  # TypeError: Can't instantiate abstract class Shape
c = Circle(5)
print(c.describe())  # Shape with area=78.54 and perimeter=31.42
```

**Abstract properties and class methods:**

```python
class Serializable(ABC):
    @property
    @abstractmethod
    def serialized(self) -> str:
        pass

    @classmethod
    @abstractmethod
    def deserialize(cls, data: str) -> 'Serializable':
        pass
```

**Using `register()` for virtual subclasses:**

```python
from collections.abc import Sized

class MyCollection:
    def __len__(self):
        return 42

# MyCollection doesn't inherit from Sized, but it implements __len__
print(isinstance(MyCollection(), Sized))  # True — because collections.abc uses __subclasshook__
```

**When to use ABCs vs Protocol:**

- Use **ABCs** when you control the class hierarchy and want to enforce a contract via inheritance.
- Use **Protocol** when you want structural typing (duck typing that type checkers can verify) without requiring inheritance.

---

---

# Part 2: AI/ML Interview Questions

---

## 1. Supervised vs Unsupervised vs Reinforcement Learning

**Q: What are the three main categories of machine learning?**

**A:**

**Supervised learning:** The model learns from labeled data (input-output pairs). It learns a mapping from inputs to outputs.

- **Classification:** Output is a category. Examples: spam detection, image classification, sentiment analysis.
- **Regression:** Output is a continuous value. Examples: house price prediction, temperature forecasting.
- Algorithms: Linear/logistic regression, decision trees, random forests, SVMs, neural networks.

**Unsupervised learning:** The model finds patterns in unlabeled data — no predefined output.

- **Clustering:** Group similar data points (K-means, DBSCAN, hierarchical clustering).
- **Dimensionality reduction:** Reduce features while preserving structure (PCA, t-SNE, UMAP).
- **Anomaly detection:** Find outliers (Isolation Forest).
- **Association rules:** Find co-occurring items (market basket analysis).

**Reinforcement learning:** An agent learns by interacting with an environment, receiving rewards or penalties.

- The agent takes actions in an environment, observes the new state, and receives a reward signal.
- Goal: maximize cumulative reward over time.
- Examples: Game playing (AlphaGo, Atari), robotics, recommendation systems, RLHF for LLMs.
- Key concepts: state, action, reward, policy, value function, exploration vs exploitation.

**Semi-supervised learning** is a hybrid — uses a small amount of labeled data with a large amount of unlabeled data.

**Self-supervised learning** (used in modern LLMs) generates labels from the data itself (e.g., predicting the next token, masked language modeling).

---

## 2. Bias-Variance Tradeoff

**Q: What is the bias-variance tradeoff?**

**A:** The prediction error of a model can be decomposed into three parts:

**Error = Bias^2 + Variance + Irreducible Noise**

- **Bias:** Error from overly simplistic assumptions. High bias means the model underfits — it misses relevant patterns. Example: fitting a straight line to quadratic data.

- **Variance:** Error from sensitivity to small fluctuations in training data. High variance means the model overfits — it captures noise as if it were signal. Example: a decision tree with no depth limit memorizing every training point.

- **Irreducible noise:** Random error inherent in the data that no model can eliminate.

**The tradeoff:**
- Simple models (few parameters): high bias, low variance.
- Complex models (many parameters): low bias, high variance.
- The goal is to find the sweet spot that minimizes total error.

**How to balance:**
- **Increase model complexity** if underfitting (high bias).
- **Regularization** (L1/L2), **dropout**, **more training data**, or **reduce model complexity** if overfitting (high variance).
- Use **cross-validation** to estimate the tradeoff.
- **Ensemble methods** (bagging reduces variance, boosting reduces bias).

**Visual intuition:** Imagine throwing darts at a target.
- Low bias, low variance: darts clustered at the bullseye.
- Low bias, high variance: darts scattered around the bullseye.
- High bias, low variance: darts clustered but off-center.
- High bias, high variance: darts scattered and off-center.

---

## 3. Overfitting and Underfitting

**Q: What are overfitting and underfitting? How do you prevent them?**

**A:**

**Overfitting:** The model learns the training data too well — including noise and outliers. It performs great on training data but poorly on unseen data. Signs: high training accuracy, low validation accuracy.

**Underfitting:** The model is too simple to capture the underlying patterns. It performs poorly on both training and validation data. Signs: low training accuracy, low validation accuracy.

**Prevention techniques for overfitting:**

1. **L1 Regularization (Lasso):** Adds the absolute value of weights to the loss function. Encourages sparsity (drives some weights to exactly zero) — useful for feature selection.

   `Loss = Original Loss + lambda * sum(|w_i|)`

2. **L2 Regularization (Ridge):** Adds the squared value of weights to the loss function. Penalizes large weights, encouraging small, distributed weights.

   `Loss = Original Loss + lambda * sum(w_i^2)`

3. **Dropout:** During training, randomly set a fraction of neurons to zero at each step. Forces the network to not rely on any single neuron. At inference, all neurons are active (weights scaled accordingly).

4. **Early stopping:** Monitor validation loss during training. Stop when validation loss starts increasing even though training loss is still decreasing. The point where validation loss is minimized is the ideal stopping point.

5. **Data augmentation:** Create modified copies of training data (rotate, flip, crop images; synonym replacement for text). Increases effective training set size.

6. **Cross-validation:** Use k-fold CV to get a more reliable estimate of model performance.

7. **Reduce model complexity:** Fewer layers/neurons, shallower trees, fewer features.

8. **More training data:** Often the most effective solution when available.

**Prevention for underfitting:** Increase model complexity, add features, reduce regularization, train longer.

---

## 4. Neural Networks Basics

**Q: Explain the basics of neural networks — perceptrons, activation functions, and backpropagation.**

**A:**

**Perceptron (single neuron):** Takes inputs, multiplies each by a weight, sums them, adds a bias, and passes the result through an activation function.

`output = activation(w1*x1 + w2*x2 + ... + wn*xn + b)`

**Activation functions — introduce non-linearity (without them, a deep network collapses to a single linear transformation):**

- **ReLU (Rectified Linear Unit):** `f(x) = max(0, x)`. Most commonly used in hidden layers. Fast to compute, helps with vanishing gradient. Downside: "dying ReLU" problem (neurons that always output 0).

- **Sigmoid:** `f(x) = 1 / (1 + e^(-x))`. Output range (0, 1). Used for binary classification output. Problem: vanishing gradients for very large/small inputs.

- **Softmax:** Converts a vector of values to a probability distribution (sums to 1). Used as the output layer for multi-class classification.

  `softmax(z_i) = e^(z_i) / sum(e^(z_j))`

- **Tanh:** `f(x) = (e^x - e^(-x)) / (e^x + e^(-x))`. Output range (-1, 1). Zero-centered (unlike sigmoid).

**Backpropagation — how neural networks learn:**

1. **Forward pass:** Input flows through the network, producing a prediction.
2. **Compute loss:** Compare prediction to true label using a loss function.
3. **Backward pass:** Using the chain rule of calculus, compute the gradient of the loss with respect to every weight in the network. Gradients flow backward from the output to the input.
4. **Update weights:** Adjust weights in the direction that reduces the loss (gradient descent).

**Intuition:** Backpropagation answers: "How much did each weight contribute to the error?" Then adjusts each weight proportionally. It is repeated for many batches over many epochs until the loss converges.

---

## 5. Convolutional Neural Networks (CNNs)

**Q: What are CNNs and how do they work?**

**A:** CNNs are neural networks designed for grid-like data (images, time series). They use **convolution** operations to automatically learn spatial hierarchies of features.

**Key operations:**

1. **Convolution:** A small filter (kernel), e.g. 3x3, slides across the input. At each position, it computes the element-wise product and sums the result, producing a feature map. Each filter detects a specific pattern (edges, textures, shapes).

   - Early layers learn low-level features (edges, corners).
   - Deeper layers learn high-level features (faces, objects).

2. **Pooling (subsampling):** Reduces spatial dimensions while retaining important information.
   - **Max pooling:** Takes the maximum value in each patch (e.g., 2x2).
   - **Average pooling:** Takes the average.
   - Reduces computation, provides translation invariance.

3. **Fully connected layers:** After convolution and pooling, the feature maps are flattened and passed through dense layers for classification.

**Typical architecture:**
```
Input -> [Conv -> ReLU -> Pool] x N -> Flatten -> Dense -> Output
```

**Key concepts:**
- **Stride:** How far the filter moves at each step.
- **Padding:** Adding zeros around the input to control output size ("same" vs "valid").
- **Channels:** Input images have channels (RGB = 3). Each conv layer produces multiple output channels (one per filter).

**Use cases:** Image classification, object detection (YOLO, Faster R-CNN), semantic segmentation, medical imaging, video analysis.

**Famous architectures:** LeNet, AlexNet, VGG, ResNet (introduced skip connections), Inception, EfficientNet.

---

## 6. RNNs and LSTMs

**Q: What are RNNs? Why do LSTMs exist?**

**A:**

**Recurrent Neural Networks (RNNs)** process sequential data by maintaining a hidden state that gets updated at each time step. The output at each step depends on the current input and the previous hidden state.

```
h_t = activation(W_hh * h_{t-1} + W_xh * x_t + b)
```

**The vanishing gradient problem:** When backpropagating through many time steps, gradients are multiplied by the same weight matrix repeatedly. If the weights are small, gradients shrink exponentially (vanish) — the network cannot learn long-range dependencies. If weights are large, gradients explode.

**LSTM (Long Short-Term Memory)** solves this with a gating mechanism:

- **Cell state (C_t):** A "conveyor belt" that runs through the entire sequence with minimal modifications. Information can flow unchanged for long distances.
- **Forget gate:** Decides what to throw away from the cell state. `f_t = sigmoid(W_f * [h_{t-1}, x_t] + b_f)`
- **Input gate:** Decides what new information to store. `i_t = sigmoid(W_i * [h_{t-1}, x_t] + b_i)`
- **Output gate:** Decides what to output. `o_t = sigmoid(W_o * [h_{t-1}, x_t] + b_o)`

**Why it works:** The cell state allows gradients to flow back through time without vanishing — the forget gate can learn to keep the gradient pathway open.

**GRU (Gated Recurrent Unit):** A simplified variant with two gates (reset and update) instead of three. Often performs comparably to LSTM with fewer parameters.

**Use cases (before transformers dominated):** Language modeling, machine translation, speech recognition, time series prediction.

**Limitations:** Still sequential (can't parallelize well), and transformers have largely replaced them for most NLP tasks due to the attention mechanism.

---

## 7. Transformers and Attention Mechanism

**Q: How do transformers work? Why did they replace RNNs?**

**A:**

**The core insight:** Attention lets the model look at all positions in the input simultaneously, weighting them by relevance to the current computation. No sequential processing needed.

**Self-attention mechanism:**

For each token, compute three vectors:
- **Query (Q):** "What am I looking for?"
- **Key (K):** "What do I contain?"
- **Value (V):** "What information do I provide?"

```
Attention(Q, K, V) = softmax(Q * K^T / sqrt(d_k)) * V
```

The dot product of Q and K measures similarity. Divide by `sqrt(d_k)` for stable gradients. Softmax gives attention weights (probabilities). Multiply by V to get the weighted combination of values.

**Multi-head attention:** Run multiple attention operations in parallel (each "head" has its own Q, K, V projections). Each head can attend to different types of relationships (syntactic, semantic, positional). Outputs are concatenated and linearly projected.

**Transformer architecture (original paper: "Attention Is All You Need"):**

- **Encoder:** Stack of identical layers, each with multi-head self-attention + feed-forward network + layer normalization + residual connections.
- **Decoder:** Similar stack but with masked self-attention (can't see future tokens) + cross-attention to encoder output.

**Positional encoding:** Since transformers have no inherent notion of sequence order (unlike RNNs), position information is added via sinusoidal functions or learned embeddings.

**Why transformers replaced RNNs:**
1. **Parallelizable:** All tokens processed simultaneously (RNNs are sequential).
2. **Long-range dependencies:** Direct attention between any two tokens regardless of distance.
3. **Scalability:** Training scales much better with hardware (GPUs/TPUs).
4. **Performance:** Superior results on virtually all NLP benchmarks.

**Variants:**
- **Encoder-only:** BERT (bidirectional, good for classification, NER).
- **Decoder-only:** GPT (autoregressive, good for generation).
- **Encoder-decoder:** T5, BART (good for translation, summarization).

---

## 8. Large Language Models (LLMs)

**Q: How do LLMs work?**

**A:**

LLMs are large transformer-based models trained on massive text corpora to predict the next token. They learn rich representations of language that enable few-shot and zero-shot capabilities.

**How they generate text:**
1. Input text is split into **tokens** (subword units, not words).
2. The model processes all tokens in parallel to produce probability distributions over the next token.
3. A token is sampled from that distribution.
4. The selected token is appended to the input, and the process repeats (autoregressive generation).

**Tokenization methods:**

- **BPE (Byte Pair Encoding):** Start with individual characters. Repeatedly merge the most frequent pair. Results in a vocabulary of subwords. Used by GPT models.
- **WordPiece:** Similar to BPE but uses likelihood to choose merges. Used by BERT.
- **SentencePiece:** Language-agnostic, works on raw text (no pre-tokenization needed).

**Sampling strategies (controlling generation):**

- **Temperature:** Scales logits before softmax. Lower temperature (e.g., 0.1) makes the distribution sharper (more deterministic). Higher temperature (e.g., 1.5) makes it more uniform (more creative/random). Temperature = 0 is equivalent to greedy (always pick the top token).

- **Top-k sampling:** Only consider the k most probable tokens. Filters out unlikely tokens but k is a fixed number regardless of the actual distribution.

- **Top-p (nucleus) sampling:** Consider the smallest set of tokens whose cumulative probability exceeds p (e.g., 0.9). Dynamically adapts the number of candidates — narrow distributions get fewer options, broad distributions get more.

**Context window:** The maximum number of tokens the model can process at once. Modern models range from 4K to 1M+ tokens. Longer context windows require techniques like RoPE, ALiBi, or ring attention.

**Training pipeline for modern LLMs:**
1. **Pre-training:** Next-token prediction on massive text data.
2. **Supervised fine-tuning (SFT):** Train on curated instruction-following examples.
3. **RLHF/RLAIF:** Reinforcement learning from human/AI feedback to align outputs with human preferences.

---

## 9. RAG (Retrieval Augmented Generation)

**Q: What is RAG and why is it useful?**

**A:**

RAG combines a retrieval system with a generative LLM. Instead of relying solely on the model's parametric knowledge (which can be outdated or incorrect), RAG retrieves relevant documents at query time and includes them in the prompt.

**Architecture:**

```
User Query
    |
    v
[Embedding Model] -> Query Vector
    |
    v
[Vector Database] -> Top-K relevant chunks
    |
    v
[Prompt Construction] = System prompt + Retrieved chunks + User query
    |
    v
[LLM] -> Grounded response
```

**Why RAG is useful:**
1. **Reduces hallucinations:** The model answers based on retrieved facts, not just its training data.
2. **Up-to-date information:** Retrieval source can be updated without retraining.
3. **Domain-specific knowledge:** Index proprietary documents without fine-tuning.
4. **Verifiability:** You can show the source documents alongside the answer.
5. **Cost-effective:** Cheaper than fine-tuning for knowledge injection.

**Chunking strategies (how to split documents for indexing):**

- **Fixed-size chunks:** Split every N characters/tokens with optional overlap. Simple but may split sentences.
- **Sentence-based:** Split on sentence boundaries. Preserves meaning but variable sizes.
- **Paragraph/section-based:** Use document structure (headers, paragraphs). Best preserves context.
- **Semantic chunking:** Use embeddings to detect topic shifts and split accordingly.
- **Recursive character splitting:** Try large chunks first, recursively split if too big (LangChain's default).

**Key considerations:**
- **Chunk size:** Too small loses context, too large dilutes relevance. Typical: 256-1024 tokens.
- **Overlap:** Adjacent chunks share some text to avoid losing information at boundaries. Typical: 10-20%.
- **Retrieval method:** Dense retrieval (embeddings), sparse retrieval (BM25), or hybrid.
- **Reranking:** Use a cross-encoder to rerank initial retrieval results for higher precision.

---

## 10. Embeddings

**Q: What are embeddings and how are they used in AI?**

**A:**

Embeddings are dense vector representations of data (words, sentences, images, etc.) in a continuous vector space where similar items are close together. They capture semantic meaning in numerical form.

**Word2Vec intuition:**

Two architectures:
- **CBOW (Continuous Bag of Words):** Predict the center word from surrounding context words.
- **Skip-gram:** Predict surrounding context words from the center word.

The trained weight matrix becomes the embedding table. Famous property: `king - man + woman ≈ queen` (vector arithmetic captures relationships).

**Sentence/document embeddings:**

- **Average word embeddings:** Simple but loses word order.
- **SBERT (Sentence-BERT):** Fine-tuned BERT model that produces meaningful sentence embeddings.
- **Modern embedding models:** `text-embedding-3-small/large` (OpenAI), `all-MiniLM-L6-v2` (open source), Cohere Embed, Voyage AI.

**Vector databases — purpose-built for similarity search:**

- **FAISS (Facebook AI Similarity Search):** Library for efficient similarity search. Supports various index types (flat, IVF, HNSW). Runs locally, very fast. Not a database (no persistence layer built-in, though you can save/load indices).

- **ChromaDB:** Open-source embedding database. Simple API, good for prototyping. Can run in-memory or with persistence.

- **Pinecone:** Managed cloud vector database. Handles scaling, replication, filtering. Production-ready with minimal ops.

- **Others:** Weaviate (GraphQL API, hybrid search), Qdrant (Rust-based, high performance), Milvus (scalable, distributed).

**Similarity metrics:**
- **Cosine similarity:** Measures angle between vectors. Most common for text. Range: -1 to 1.
- **Euclidean distance:** L2 distance in vector space.
- **Dot product:** Equivalent to cosine similarity for normalized vectors.

**Use cases:** Semantic search, recommendation systems, RAG retrieval, clustering, anomaly detection, deduplication.

---

## 11. Fine-tuning vs Prompt Engineering

**Q: When should you fine-tune vs use prompt engineering?**

**A:**

**Prompt engineering — modifying the input to get better outputs (no model changes):**

- **Zero-shot:** Just ask the question directly.
- **Few-shot:** Provide examples in the prompt to guide the format/style.
- **Chain-of-thought (CoT):** Ask the model to "think step by step."
- **System prompts:** Set the persona, constraints, and output format.
- **Structured output:** Ask for JSON, use function calling, or provide a schema.

**When prompt engineering is enough:**
- The task is within the model's existing capabilities.
- You need flexibility to change behavior without retraining.
- You have limited training data.
- Quick iteration is important.

**Fine-tuning — training the model further on your specific data:**

- **Full fine-tuning:** Update all model weights. Expensive, requires significant compute.
- **LoRA (Low-Rank Adaptation):** Only train small, low-rank matrices added to existing weights. Dramatically reduces compute and memory. Typically trains 0.1-1% of total parameters.
- **QLoRA:** LoRA applied to a quantized (4-bit) model. Enables fine-tuning large models on consumer hardware.
- **Adapter methods:** Insert small trainable modules between frozen layers.

**When to fine-tune:**
- You need a specific output format/style consistently.
- Domain-specific language or jargon that the base model handles poorly.
- Improved performance on a narrow task.
- Reducing prompt length (the behavior is baked in, not prompted).
- Cost optimization at scale (shorter prompts = cheaper inference).

**Decision framework:**
1. Start with prompt engineering (cheapest, fastest iteration).
2. Try RAG if the model needs specific knowledge.
3. Fine-tune if prompt engineering and RAG aren't sufficient for style/format/performance.
4. Full fine-tune only for major domain shifts or when you need maximum performance.

---

## 12. Common ML Libraries

**Q: What are the key ML libraries and how are they used?**

**A:**

**scikit-learn — classical ML:**

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report

# Typical workflow:
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Pipeline chains preprocessing and model together
pipe = Pipeline([
    ('scaler', StandardScaler()),
    ('clf', RandomForestClassifier(n_estimators=100, random_state=42))
])

pipe.fit(X_train, y_train)
predictions = pipe.predict(X_test)
print(classification_report(y_test, predictions))

# Cross-validation
scores = cross_val_score(pipe, X, y, cv=5, scoring='accuracy')
print(f"CV Accuracy: {scores.mean():.3f} +/- {scores.std():.3f}")
```

**PyTorch — deep learning:**

```python
import torch
import torch.nn as nn
import torch.optim as optim

# Tensors — similar to numpy arrays but with GPU support and autograd
x = torch.tensor([1.0, 2.0, 3.0], requires_grad=True)
y = (x ** 2).sum()
y.backward()        # compute gradients
print(x.grad)       # tensor([2., 4., 6.])

# Define a model
class SimpleNet(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, output_dim)
        )

    def forward(self, x):
        return self.layers(x)

model = SimpleNet(784, 128, 10)
optimizer = optim.Adam(model.parameters(), lr=0.001)
criterion = nn.CrossEntropyLoss()

# Training loop
for epoch in range(num_epochs):
    for batch_x, batch_y in dataloader:
        optimizer.zero_grad()
        output = model(batch_x)
        loss = criterion(output, batch_y)
        loss.backward()
        optimizer.step()
```

**TensorFlow/Keras:**

Keras (now integrated into TensorFlow) provides a higher-level API. TensorFlow is production-oriented with strong deployment tooling (TF Serving, TF Lite). PyTorch has become the dominant research framework; TensorFlow remains common in production.

**Hugging Face Transformers:**

```python
from transformers import pipeline

# Sentiment analysis in 3 lines:
classifier = pipeline("sentiment-analysis")
result = classifier("I love this product!")
print(result)  # [{'label': 'POSITIVE', 'score': 0.9998}]
```

---

## 13. Evaluation Metrics

**Q: What metrics do you use to evaluate ML models and when?**

**A:**

**Confusion matrix** (for binary classification):

```
                 Predicted Positive    Predicted Negative
Actual Positive       TP                    FN
Actual Negative       FP                    TN
```

**Key metrics:**

- **Accuracy** = (TP + TN) / Total. Misleading with imbalanced classes (99% accuracy on 99/1 split means nothing).

- **Precision** = TP / (TP + FP). "Of all predicted positives, how many are actually positive?" Use when false positives are costly (e.g., spam detection — don't want to lose real email).

- **Recall (Sensitivity)** = TP / (TP + FN). "Of all actual positives, how many did we catch?" Use when false negatives are costly (e.g., cancer detection — don't want to miss cancer).

- **F1 Score** = 2 * (Precision * Recall) / (Precision + Recall). Harmonic mean of precision and recall. Use when you need a single metric that balances both, especially with imbalanced classes.

- **AUC-ROC (Area Under the Receiver Operating Characteristic Curve):** Plots TPR (recall) vs FPR at various threshold settings. AUC = 1.0 is perfect, 0.5 is random. Useful for comparing models across all thresholds. Not ideal for heavily imbalanced datasets (use AUC-PR instead).

**When to use which:**

| Scenario | Metric |
|----------|--------|
| Balanced classes, general performance | Accuracy |
| Imbalanced classes | F1, AUC-PR |
| Cost of false positive is high | Precision |
| Cost of false negative is high | Recall |
| Model comparison across thresholds | AUC-ROC |
| Regression | MSE, MAE, RMSE, R-squared |

**Regression metrics:**
- **MSE** (Mean Squared Error): Penalizes large errors more.
- **MAE** (Mean Absolute Error): More robust to outliers.
- **R-squared**: Proportion of variance explained (1.0 = perfect, 0 = predicts the mean).

---

## 14. Feature Engineering

**Q: What is feature engineering and what are common techniques?**

**A:**

Feature engineering is transforming raw data into features that better represent the underlying problem, improving model performance.

**Encoding categorical variables:**

- **Label encoding:** Map categories to integers (0, 1, 2, ...). Use for ordinal data (low/medium/high) or tree-based models.
- **One-hot encoding:** Create binary columns for each category. Use for nominal data with few categories. Avoids implying an ordinal relationship.
- **Target encoding:** Replace category with the mean of the target variable. Powerful but risk of data leakage (use cross-validation encoding).
- **Embedding:** For high-cardinality categories (e.g., zip codes), learn dense vector representations within a neural network.

**Normalization and standardization:**

- **Standardization (Z-score):** `z = (x - mean) / std`. Centers at 0, unit variance. Best for algorithms assuming normally distributed data (logistic regression, SVM, neural networks).
- **Min-Max normalization:** `x_norm = (x - min) / (max - min)`. Scales to [0, 1]. Sensitive to outliers.
- **Robust scaling:** Uses median and IQR. Better with outliers.

**Feature selection:**

- **Filter methods:** Statistical tests (chi-squared, correlation, mutual information). Fast, model-agnostic.
- **Wrapper methods:** Use model performance to evaluate feature subsets (forward selection, backward elimination). Accurate but slow.
- **Embedded methods:** Feature importance from the model itself (L1 regularization, tree feature importances).
- **Dimensionality reduction:** PCA, t-SNE (for visualization), UMAP.

**Other techniques:**
- **Polynomial features:** Create interaction terms (x1*x2) and powers.
- **Binning:** Convert continuous to categorical (age groups).
- **Log/power transforms:** Handle skewed distributions.
- **Domain-specific features:** Date -> day of week, hour; text -> TF-IDF, n-grams; images -> HOG features.

---

## 15. Train/Test/Validation Split

**Q: Why do we split data and how?**

**A:**

- **Training set (60-80%):** Used to train the model. The model learns patterns from this data.
- **Validation set (10-20%):** Used to tune hyperparameters and make modeling decisions. Prevents optimizing directly on the test set.
- **Test set (10-20%):** Used only once, at the very end, to estimate real-world performance. Never use it to make modeling decisions.

**Why:** If you evaluate on training data, you get an overly optimistic estimate (the model has seen this data). The test set simulates unseen data.

**Cross-validation (k-fold):**

Split data into k folds. Train on k-1 folds, validate on 1 fold. Repeat k times, each fold serving as validation once. Average the k performance scores.

```
Fold 1: [Val] [Train] [Train] [Train] [Train]
Fold 2: [Train] [Val] [Train] [Train] [Train]
Fold 3: [Train] [Train] [Val] [Train] [Train]
Fold 4: [Train] [Train] [Train] [Val] [Train]
Fold 5: [Train] [Train] [Train] [Train] [Val]
```

**Benefits:** Uses all data for both training and validation. More reliable estimate, especially with small datasets. Standard: k=5 or k=10.

**Stratified splitting:** Preserves the class distribution in each split. Critical for imbalanced datasets. If 10% of data is positive, each fold should also be ~10% positive.

```python
from sklearn.model_selection import StratifiedKFold

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
for train_idx, val_idx in skf.split(X, y):
    X_train, X_val = X[train_idx], X[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]
```

**Time series caveat:** Never randomly split time series data. Use time-based splits (train on past, validate/test on future) to avoid data leakage.

---

## 16. Gradient Descent

**Q: How does gradient descent work? What are the variants?**

**A:**

Gradient descent is an optimization algorithm that iteratively adjusts model parameters to minimize a loss function. At each step, compute the gradient (slope) of the loss with respect to each parameter and move in the opposite direction.

`w_new = w_old - learning_rate * gradient`

**Variants:**

- **Batch gradient descent:** Compute gradient using the entire training set. Stable but slow for large datasets and requires the whole dataset in memory.

- **Stochastic gradient descent (SGD):** Compute gradient using a single random sample. Fast updates, noisy (high variance), can escape local minima. Rarely used in pure form.

- **Mini-batch gradient descent:** Compute gradient using a small batch (e.g., 32, 64, 128 samples). The standard approach. Balances stability and speed. Benefits from GPU parallelism.

**Learning rate:**

- Too high: overshoots the minimum, loss diverges.
- Too low: converges very slowly, may get stuck.
- **Learning rate scheduling:** Reduce LR over time (step decay, cosine annealing, warm-up).

**Adam optimizer (Adaptive Moment Estimation):**

The most commonly used optimizer. Combines two ideas:
1. **Momentum:** Use an exponential moving average of past gradients (helps navigate ravines and accelerate convergence).
2. **Adaptive learning rates:** Each parameter gets its own learning rate based on the magnitude of its recent gradients (parameters with large gradients get smaller LR and vice versa).

Includes bias correction for the early steps. Default hyperparameters (lr=0.001, beta1=0.9, beta2=0.999) work well for most cases.

**Other optimizers:** SGD with momentum, AdaGrad, RMSProp, AdamW (Adam with decoupled weight decay — now the default for training LLMs).

---

## 17. Loss Functions

**Q: What are common loss functions and when do you use them?**

**A:**

A loss function measures how far the model's prediction is from the true value. Training minimizes this function.

**Regression losses:**

- **MSE (Mean Squared Error):** `L = mean((y_pred - y_true)^2)`. Penalizes large errors heavily (squared). Sensitive to outliers. Most common for regression.

- **MAE (Mean Absolute Error):** `L = mean(|y_pred - y_true|)`. Linear penalty. More robust to outliers. Gradient is constant, which can make optimization harder near the minimum.

- **Huber Loss:** Combines MSE and MAE. Behaves like MSE for small errors (smooth, differentiable) and MAE for large errors (robust to outliers).

**Classification losses:**

- **Binary Cross-Entropy (Log Loss):** For binary classification.
  `L = -[y * log(p) + (1-y) * log(1-p)]`
  Heavily penalizes confident wrong predictions (predicting 0.01 when truth is 1). Use with sigmoid output.

- **Categorical Cross-Entropy:** For multi-class classification.
  `L = -sum(y_i * log(p_i))` across all classes.
  Use with softmax output. `y_i` is one-hot encoded.

- **Sparse Categorical Cross-Entropy:** Same as categorical but accepts integer labels instead of one-hot vectors. More memory efficient.

**When to use which:**

| Task | Loss Function | Output Activation |
|------|--------------|-------------------|
| Regression | MSE or MAE | Linear (none) |
| Binary classification | Binary cross-entropy | Sigmoid |
| Multi-class (one label) | Categorical cross-entropy | Softmax |
| Multi-label (multiple labels) | Binary cross-entropy per label | Sigmoid per output |
| Regression with outliers | Huber or MAE | Linear |

**Special loss functions:** Contrastive loss (learning embeddings), triplet loss (face recognition), focal loss (handles class imbalance), hinge loss (SVMs).

---

## 18. Transfer Learning

**Q: What is transfer learning and how does it work?**

**A:**

Transfer learning uses a model trained on a large, general dataset as the starting point for a new, related task. The idea is that features learned on one task (e.g., ImageNet) transfer to another (e.g., medical imaging).

**Why it works:** Early layers of neural networks learn general features (edges, textures, basic language patterns) that are useful across many tasks. Only the later layers are task-specific.

**Approach:**

1. **Take a pretrained model** (e.g., ResNet trained on ImageNet, BERT trained on BookCorpus + Wikipedia).
2. **Remove/replace the final layer(s)** to match your task's output.
3. **Freeze early layers** (don't update their weights) — they already have good general features.
4. **Train later layers** on your specific dataset.
5. **Optional: unfreeze and fine-tune** the entire model with a very small learning rate.

**Practical strategy:**

- **Small dataset, similar domain:** Freeze most layers, train only the head. Risk of overfitting with few examples.
- **Small dataset, different domain:** Freeze early layers (they're still useful), retrain later layers.
- **Large dataset, similar domain:** Fine-tune the entire network starting from pretrained weights.
- **Large dataset, different domain:** Pretrained weights still provide a better starting point than random initialization.

**In NLP (modern approach):**

```
Large pretrained LLM (GPT, BERT, LLaMA)
    |
    v
Fine-tune on task-specific data (or use LoRA for efficiency)
    |
    v
Task-specific model (sentiment, NER, summarization, etc.)
```

Transfer learning is why modern AI is so capable — instead of training from scratch, we build on top of massive pretrained models.

---

## 19. NLP Basics

**Q: What are the fundamental concepts in NLP?**

**A:**

**Tokenization — splitting text into units:**
- **Word tokenization:** Split on whitespace/punctuation. Simple but doesn't handle compound words, contractions well.
- **Subword tokenization:** BPE, WordPiece, SentencePiece. Used by modern LLMs. Handles unknown words by breaking them into known subword units.
- **Character tokenization:** Each character is a token. Very small vocabulary but very long sequences.

**Text preprocessing (traditional NLP):**

- **Stemming:** Reduce words to their stem by removing suffixes. Crude but fast. "running" -> "run", "better" -> "better" (fails). Porter Stemmer is common.
- **Lemmatization:** Reduce words to their dictionary form (lemma) using linguistic knowledge. "running" -> "run", "better" -> "good". More accurate but slower. Uses POS tags.
- **Stop word removal:** Remove common words (the, is, at, which). Useful for bag-of-words models, but modern models often keep them.

**Feature representations:**

- **Bag of Words (BoW):** Represent text as a vector of word counts. Loses word order. Sparse, high-dimensional.

- **TF-IDF (Term Frequency - Inverse Document Frequency):**
  - TF: How often a term appears in a document.
  - IDF: How rare a term is across all documents. `log(N / df)`.
  - TF-IDF = TF * IDF. Words that are frequent in a document but rare overall get high scores.
  - Better than BoW for information retrieval — common words are downweighted.

- **N-grams:** Contiguous sequences of n tokens. Bigrams ("New York"), trigrams ("New York City"). Captures some word order and context. Used in language models, feature engineering.

**Modern NLP has largely moved to:**
- Pretrained transformer models (BERT, GPT) that learn contextual representations.
- These subsume most traditional preprocessing — they handle raw text and learn what matters.
- However, understanding the fundamentals helps with debugging, custom pipelines, and interview knowledge.

---

## 20. Responsible AI

**Q: What are the key concerns in responsible AI?**

**A:**

**Bias in training data:**

Models learn from data, and data reflects historical biases. If a hiring model is trained on historical hiring decisions that favored certain demographics, it will perpetuate that bias. Types:
- **Selection bias:** Training data doesn't represent the real population.
- **Measurement bias:** Features are proxies for protected attributes (zip code correlates with race).
- **Historical bias:** Past data reflects societal inequities.
- **Representation bias:** Underrepresentation of minority groups.

**Fairness:**

Multiple (often conflicting) mathematical definitions:
- **Demographic parity:** Equal prediction rates across groups.
- **Equal opportunity:** Equal true positive rates across groups.
- **Calibration:** Equal precision across groups.
- **Individual fairness:** Similar individuals get similar predictions.

It is mathematically proven that you cannot satisfy all fairness criteria simultaneously (except in trivial cases).

**Hallucinations in LLMs:**

LLMs generate text that sounds authoritative but is factually incorrect. Types:
- **Intrinsic hallucination:** Contradicts the source material.
- **Extrinsic hallucination:** Claims that can't be verified from any source — the model fabricates information (fake citations, non-existent APIs, incorrect statistics).

**Mitigation strategies:**

1. **For bias:**
   - Audit training data for representation.
   - Use fairness metrics during evaluation.
   - Apply debiasing techniques (resampling, adversarial training, calibration).
   - Diverse teams in development.

2. **For hallucinations:**
   - RAG — ground outputs in retrieved documents.
   - Constrained generation — structured outputs, function calling.
   - Chain-of-thought — explicit reasoning reduces some errors.
   - Human-in-the-loop — review critical outputs.
   - Confidence calibration — model expresses uncertainty.
   - Fine-tuning on high-quality data.

3. **General practices:**
   - Transparency — document model capabilities and limitations.
   - Evaluation on diverse benchmarks — not just accuracy but also fairness, robustness, toxicity.
   - Red teaming — adversarial testing before deployment.
   - Monitoring — track model performance and fairness metrics in production.
   - Consent and privacy — handle personal data responsibly (GDPR, data minimization).
   - Interpretability — use techniques (SHAP, LIME, attention visualization) to understand model decisions.

---

*End of guide. Review each section, understand the "why" behind each concept, and practice explaining these topics in your own words.*
