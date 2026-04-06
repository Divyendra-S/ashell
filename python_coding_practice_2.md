# Python Interview Coding Practice Guide (Part 2)

> Practical Python coding skills — functional style, standard library, real-world patterns.

---

## 1. Lambda, Map, Filter, Reduce

**Theory:** Python supports functional programming through first-class functions. Functions can be passed as arguments, returned from other functions, and assigned to variables.

- `lambda` creates small anonymous functions (single expression, no `def` needed)
- `map(fn, iterable)` applies `fn` to every element, returns an iterator
- `filter(fn, iterable)` keeps elements where `fn` returns `True`
- `reduce(fn, iterable)` collapses an iterable into a single value by applying `fn` cumulatively

```python
# Lambda — anonymous single-expression function
square = lambda x: x ** 2
classify = lambda x: "even" if x % 2 == 0 else "odd"

# Map — transform every element
nums = [1, 2, 3, 4, 5]
squared = list(map(lambda x: x ** 2, nums))       # [1, 4, 9, 16, 25]
cleaned = list(map(str.strip, ["  hi ", " bye"]))  # ["hi", "bye"]

# Map with multiple iterables — pairs up elements
sums = list(map(lambda x, y: x + y, [1, 2], [10, 20]))  # [11, 22]

# Filter — keep elements matching a condition
evens = list(filter(lambda x: x % 2 == 0, nums))  # [2, 4]
non_empty = list(filter(None, ["hi", "", "bye"]))  # filter(None, ...) removes falsy values

# Reduce — accumulate into a single result
from functools import reduce  # reduce was moved to functools in Python 3
total = reduce(lambda acc, x: acc + x, nums)        # 15
product = reduce(lambda acc, x: acc * x, nums)      # 120
maximum = reduce(lambda a, b: a if a > b else b, nums)  # 5

# Chaining: sum of squares of even numbers
result = reduce(
    lambda acc, x: acc + x,
    map(lambda x: x ** 2,
        filter(lambda x: x % 2 == 0, range(1, 11))
    )
)  # 220

# Same thing with a generator expression (often cleaner in Python)
result = sum(x ** 2 for x in range(1, 11) if x % 2 == 0)  # 220
```

---

## 2. Sorting with Custom Keys

**Theory:** `sorted()` returns a new sorted list. `.sort()` sorts in-place. Both accept `key=` (a function that extracts comparison value) and `reverse=` (bool). Python's sort is **stable** — equal elements keep their original order.

```python
# Sort tuples by second element
pairs = [(1, 'b'), (3, 'a'), (2, 'c')]
sorted(pairs, key=lambda x: x[1])  # [(3,'a'), (1,'b'), (2,'c')]

# Sort dicts by a field
employees = [
    {"name": "Alice", "age": 30, "salary": 70000},
    {"name": "Bob", "age": 25, "salary": 80000},
]
sorted(employees, key=lambda e: e["salary"], reverse=True)

# Sort by multiple keys: age first, then salary if age ties
sorted(employees, key=lambda e: (e["age"], e["salary"]))

# Negate for mixed ascending/descending (works for numbers)
# Sort by salary DESC, then name ASC for ties
sorted(employees, key=lambda e: (-e["salary"], e["name"]))

# Sort dict by values
scores = {"Alice": 88, "Bob": 95, "Charlie": 72}
sorted_scores = dict(sorted(scores.items(), key=lambda item: item[1], reverse=True))

# Sort strings by length, case-insensitive
sorted(["banana", "Apple", "fig"], key=lambda w: (len(w), w.lower()))

# operator module — faster alternative to lambda for attribute/item access
from operator import itemgetter, attrgetter
sorted(employees, key=itemgetter("salary"))  # same as key=lambda e: e["salary"]
```

---

## 3. Regular Expressions

**Theory:** The `re` module provides regex operations. Key functions:
- `re.search(pattern, string)` — find first match anywhere
- `re.match(pattern, string)` — match only at beginning
- `re.findall(pattern, string)` — return all matches as a list
- `re.sub(pattern, replacement, string)` — find and replace
- `re.split(pattern, string)` — split by pattern

A match object has `.group()` (the matched text), `.groups()` (captured groups), `.start()`/`.end()` (positions).

```python
import re

text = "My email is alice@example.com and phone is 123-456-7890"

# Find first match
match = re.search(r"\d{3}-\d{3}-\d{4}", text)
if match:
    print(match.group())  # "123-456-7890"

# Find all matches
numbers = re.findall(r"\d+", text)  # ["123", "456", "7890"]

# Search and replace
cleaned = re.sub(r"\d", "#", text)  # replaces each digit with #

# Split by pattern
parts = re.split(r"[,;\s]+", "one, two; three   four")  # ["one","two","three","four"]

# Extract emails
emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)

# Named groups — capture parts of a match with labels
pattern = r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"
match = re.search(pattern, "Today is 2025-01-15")
if match:
    print(match.group("year"))  # "2025"
    print(match.groups())       # ("2025", "01", "15")

# Validate patterns
def is_valid_email(email):
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email))

# Common patterns cheat sheet:
# Digits only:       r"^\d+$"
# Alphabetic only:   r"^[a-zA-Z]+$"
# URL:               r"https?://[^\s]+"
# Date (YYYY-MM-DD): r"^\d{4}-\d{2}-\d{2}$"
# Clean whitespace:  re.sub(r"\s+", " ", text).strip()
# Remove HTML tags:  re.sub(r"<[^>]+>", "", html_text)
```

---

## 4. Functional Programming in Python

**Theory:** Functional programming treats computation as evaluating mathematical functions. Core ideas:
- **Pure functions** — same input always gives same output, no side effects
- **Immutability** — don't mutate data, create new copies instead
- **Higher-order functions** — functions that take or return other functions
- **Composition** — combine small functions to build complex behavior

### Pure Functions vs Impure

```python
# IMPURE — mutates external state (side effect)
total = 0
def add_to_total(x):
    global total
    total += x  # modifies external variable
    return total

# PURE — no side effects, deterministic output
def add(a, b):
    return a + b  # same inputs always give same output
```

### Higher-Order Functions

**Theory:** A higher-order function either takes a function as argument or returns a function. `map`, `filter`, `sorted` are all higher-order functions.

```python
# Function that takes a function
def apply_to_all(fn, items):
    return [fn(item) for item in items]

apply_to_all(str.upper, ["hello", "world"])  # ["HELLO", "WORLD"]
apply_to_all(lambda x: x * 2, [1, 2, 3])    # [2, 4, 6]

# Function that returns a function
def multiplier(factor):
    return lambda x: x * factor

double = multiplier(2)
triple = multiplier(3)
double(5)   # 10
triple(5)   # 15
```

### Closures

**Theory:** A closure is a function that "remembers" variables from the scope where it was created, even after that scope has finished executing. The inner function captures the variable by reference.

```python
def make_counter():
    count = 0
    def increment():
        nonlocal count  # needed to modify the enclosed variable
        count += 1
        return count
    return increment

counter = make_counter()
counter()  # 1
counter()  # 2
counter()  # 3

# Practical: create validators
def make_range_checker(min_val, max_val):
    def check(value):
        return min_val <= value <= max_val
    return check

is_valid_age = make_range_checker(0, 150)
is_valid_score = make_range_checker(0, 100)
is_valid_age(25)    # True
is_valid_score(150) # False
```

### functools — Essential Functional Tools

**Theory:** The `functools` module provides tools for working with functions in a functional style.

```python
from functools import partial, reduce, lru_cache

# partial — "pre-fill" some arguments of a function
# Creates a new function with some args already set
def power(base, exp):
    return base ** exp

square = partial(power, exp=2)   # fixes exp=2
cube = partial(power, exp=3)     # fixes exp=3
square(5)  # 25
cube(3)    # 27

# Practical partial: configure a logger
import logging
debug_log = partial(logging.log, logging.DEBUG)
error_log = partial(logging.log, logging.ERROR)

# lru_cache — memoization decorator (caches results of expensive function calls)
# LRU = Least Recently Used — evicts oldest cached items when maxsize is reached
@lru_cache(maxsize=128)
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

fibonacci(100)  # instant — without cache this would take forever
fibonacci.cache_info()  # shows hits, misses, maxsize, currsize

# reduce — fold a list into a single value (covered in section 1)
```

### Composition and Pipelines (Functional Pattern)

**Theory:** Function composition means chaining functions so the output of one becomes the input of the next. Python doesn't have a built-in compose operator, but you can build one.

```python
from functools import reduce

# Compose: apply functions right to left — compose(f, g)(x) = f(g(x))
def compose(*fns):
    return reduce(lambda f, g: lambda x: f(g(x)), fns)

# Pipe: apply functions left to right (more readable)
def pipe(*fns):
    return reduce(lambda f, g: lambda x: g(f(x)), fns)

# Example: process text
clean = pipe(
    str.strip,
    str.lower,
    lambda s: s.replace("  ", " "),
)

clean("  Hello   World  ")  # "hello world"

# Practical pipeline: data processing
process_numbers = pipe(
    lambda nums: filter(lambda x: x > 0, nums),    # keep positives
    lambda nums: map(lambda x: x ** 2, nums),       # square them
    list,                                             # materialize
    sum,                                              # sum them up
)

process_numbers([-2, -1, 0, 1, 2, 3])  # 1 + 4 + 9 = 14
```

### Immutable Data Transformations

```python
# Instead of mutating, create new versions
# BAD (mutates original)
users = [{"name": "Alice", "active": False}, {"name": "Bob", "active": True}]
for u in users:
    u["active"] = True  # mutates original dicts!

# GOOD (creates new data)
activated = [{**u, "active": True} for u in users]
# Original `users` is unchanged

# Transform a dict without mutation
config = {"host": "localhost", "port": 8080, "debug": False}
production_config = {**config, "debug": False, "host": "prod.example.com"}
```

---

## 5. Exception Handling

**Theory:**
- `try` — code that might raise an exception
- `except` — handle specific exceptions
- `else` — runs ONLY if no exception was raised
- `finally` — ALWAYS runs (cleanup code)
- `raise` — throw an exception
- `raise ... from e` — chain exceptions (preserves original traceback)

```python
def divide(a, b):
    try:
        result = a / b
    except ZeroDivisionError:
        return None
    except TypeError as e:
        print(f"Invalid types: {e}")
        return None
    else:
        return result       # runs only on success
    finally:
        print("done")       # always runs

# Custom exceptions
class ValidationError(Exception):
    def __init__(self, field, message):
        self.field = field
        super().__init__(f"Validation error on '{field}': {message}")

def validate_age(age):
    if not isinstance(age, int) or age < 0:
        raise ValidationError("age", "must be a non-negative integer")
    return age

# Re-raise preserving traceback
try:
    int("abc")
except ValueError:
    raise  # re-raises the SAME exception

# Chain exceptions
try:
    open("missing.txt")
except FileNotFoundError as e:
    raise RuntimeError("Config missing") from e
    # Traceback shows both exceptions
```

---

## 6. File Handling

**Theory:** Always use `with open(...)` — it's a context manager that auto-closes the file even if an error occurs. Modes: `"r"` (read), `"w"` (write/overwrite), `"a"` (append). `csv` and `json` modules handle structured data.

```python
# Read/write text files
with open("file.txt", "w") as f:
    f.write("line 1\nline 2\n")

with open("file.txt") as f:
    for line in f:                  # memory-efficient line-by-line reading
        print(line.strip())

# CSV
import csv

with open("data.csv") as f:
    reader = csv.DictReader(f)      # each row is a dict with header keys
    for row in reader:
        print(row["name"], row["age"])

# JSON
import json

data = {"users": [{"name": "Alice", "age": 30}]}
with open("data.json", "w") as f:
    json.dump(data, f, indent=2)    # write dict as JSON

with open("data.json") as f:
    loaded = json.load(f)           # parse JSON back to dict

# String conversion (no file)
json_str = json.dumps(data)         # dict -> JSON string
parsed = json.loads(json_str)       # JSON string -> dict
```

---

## 7. Working with Dates

**Theory:**
- `datetime` — represents a specific date + time
- `date` — just a date (no time)
- `timedelta` — a duration (difference between two dates)
- `strftime` — format datetime as string (f = format)
- `strptime` — parse string into datetime (p = parse)

```python
from datetime import datetime, date, timedelta

now = datetime.now()
today = date.today()

# Formatting and parsing
now.strftime("%Y-%m-%d %H:%M")                          # "2025-01-15 14:30"
datetime.strptime("2025-01-15", "%Y-%m-%d")              # string -> datetime
# Common: %Y=year, %m=month, %d=day, %H=hour, %M=minute, %S=second

# Date arithmetic
tomorrow = today + timedelta(days=1)
delta = date(2025, 12, 31) - date(2025, 1, 1)
print(delta.days)  # 364

# Age calculator
def calculate_age(birth_str):
    birth = datetime.strptime(birth_str, "%Y-%m-%d").date()
    today = date.today()
    age = today.year - birth.year
    if (today.month, today.day) < (birth.month, birth.day):
        age -= 1
    return age
```

---

## 8. Dictionary Advanced

**Theory:** Dicts are O(1) for lookup/insert/delete (hash table). Since Python 3.7, dicts preserve insertion order. `defaultdict` auto-creates missing keys. `dict.get(key, default)` avoids KeyError.

```python
from collections import defaultdict, Counter

# Merging dicts
d1 = {"a": 1, "b": 2}
d2 = {"b": 3, "c": 4}
merged = {**d1, **d2}              # {"a":1, "b":3, "c":4} — d2 wins on conflicts
merged = d1 | d2                    # Python 3.9+ — same result

# Merge by summing duplicate keys
merged = dict(Counter(d1) + Counter(d2))  # {"a":1, "b":5, "c":4}

# Safe nested access
def deep_get(d, *keys, default=None):
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key, default)
        else:
            return default
    return d

config = {"db": {"credentials": {"user": "admin"}}}
deep_get(config, "db", "credentials", "user")   # "admin"
deep_get(config, "db", "missing", "key")         # None

# defaultdict — auto-creates values for missing keys
# defaultdict(list) creates an empty list for each new key
grouped = defaultdict(list)
for word in ["apple", "banana", "avocado"]:
    grouped[word[0]].append(word)
# {"a": ["apple", "avocado"], "b": ["banana"]}

# defaultdict(int) starts at 0 — perfect for counting
counts = defaultdict(int)
for char in "hello":
    counts[char] += 1

# Dict comprehension tricks
scores = {"Alice": 85, "Bob": 42, "Charlie": 91}
passed = {k: v for k, v in scores.items() if v >= 50}  # filter
inverted = {v: k for k, v in scores.items()}            # swap keys/values
d = dict(zip(["a", "b"], [1, 2]))                       # from two lists
```

---

## 9. Set Operations

**Theory:** Sets store unique elements and support O(1) membership testing. They support mathematical operations: union (`|`), intersection (`&`), difference (`-`), symmetric difference (`^`). `frozenset` is an immutable set (can be used as a dict key).

```python
a = {1, 2, 3, 4, 5}
b = {4, 5, 6, 7, 8}

a | b    # {1,2,3,4,5,6,7,8}  union — all elements
a & b    # {4, 5}              intersection — common elements
a - b    # {1, 2, 3}           difference — in a but not b
a ^ b    # {1,2,3,6,7,8}       symmetric diff — in one but not both

# Practical uses
required = {"name", "email", "age"}
provided = {"name", "email"}
missing = required - provided              # {"age"}

old_users = {"alice", "bob", "charlie"}
new_users = {"bob", "charlie", "eve"}
added = new_users - old_users              # {"eve"}
removed = old_users - new_users            # {"alice"}

# Remove duplicates preserving order
items = [3, 1, 4, 1, 5, 9, 2, 6, 5]
unique = list(dict.fromkeys(items))        # [3, 1, 4, 5, 9, 2, 6]
```

---

## 10. itertools

**Theory:** `itertools` provides memory-efficient iterator tools. They return iterators (lazy), so they don't build entire lists in memory. You often wrap them in `list()` to see results.

```python
from itertools import combinations, permutations, product, chain, groupby, islice, accumulate

# combinations — choose r items, order doesn't matter
list(combinations([1, 2, 3], 2))           # [(1,2), (1,3), (2,3)]

# permutations — all orderings of r items
list(permutations([1, 2, 3], 2))           # [(1,2), (1,3), (2,1), (2,3), (3,1), (3,2)]

# product — cartesian product (like nested for loops)
list(product(["red", "blue"], ["S", "M"]))  # [("red","S"), ("red","M"), ("blue","S"), ("blue","M")]
# product(range(3), repeat=2) = all pairs (0,0), (0,1), ..., (2,2)

# chain — combine multiple iterables into one flat stream
list(chain([1, 2], [3, 4], [5]))            # [1, 2, 3, 4, 5]
list(chain.from_iterable([[1,2],[3,4]]))    # [1, 2, 3, 4]  — flattens one level

# groupby — group CONSECUTIVE elements by a key
# IMPORTANT: data MUST be sorted by the grouping key first!
data = [("Eng", "Alice"), ("Eng", "Bob"), ("Mkt", "Charlie")]
for dept, members in groupby(data, key=lambda x: x[0]):
    print(dept, [m[1] for m in members])
# Eng ["Alice", "Bob"], Mkt ["Charlie"]

# accumulate — running totals
list(accumulate([1, 2, 3, 4]))              # [1, 3, 6, 10] — running sum
list(accumulate([3, 1, 4, 1, 5], max))      # [3, 3, 4, 4, 5] — running max

# islice — slice an iterator (can't use regular [] on iterators)
gen = (x**2 for x in range(100))
list(islice(gen, 5))                         # [0, 1, 4, 9, 16] — first 5 items
```

---

## 11. collections Module

**Theory:** Specialized containers that extend built-in dict/list/tuple with common patterns.

```python
from collections import Counter, deque, namedtuple, defaultdict, ChainMap

# Counter — count occurrences of elements
c = Counter("abracadabra")                  # Counter({"a":5, "b":2, "r":2, "c":1, "d":1})
c.most_common(2)                            # [("a", 5), ("b", 2)]
Counter("abc") + Counter("bcd")            # Counter({"b":2, "c":2, "a":1, "d":1})

# deque — double-ended queue with O(1) append/pop on BOTH ends
# (list is O(n) for insert(0, x) and pop(0))
d = deque([1, 2, 3])
d.appendleft(0)        # deque([0, 1, 2, 3])  — O(1) vs list insert(0,x) which is O(n)
d.popleft()            # 0  — O(1) vs list pop(0) which is O(n)
d.rotate(1)            # [3, 1, 2] — rotate right

# Fixed-size deque — auto-discards oldest when full
recent = deque(maxlen=3)
for i in range(5):
    recent.append(i)
# deque([2, 3, 4]) — only last 3 kept

# namedtuple — lightweight immutable "class" with named fields
Point = namedtuple("Point", ["x", "y"])
p = Point(3, 4)
print(p.x, p.y)       # 3 4 — access by name
print(p[0])            # 3 — also works by index
p._asdict()            # {"x": 3, "y": 4}

# ChainMap — search multiple dicts as one (first match wins)
defaults = {"color": "red", "size": "M"}
user_prefs = {"color": "blue"}
config = ChainMap(user_prefs, defaults)
config["color"]  # "blue" (from user_prefs)
config["size"]   # "M" (from defaults)
```

---

## 12. Enumerate, Zip, Unpacking

```python
# enumerate — get index + value in a loop
for i, fruit in enumerate(["apple", "banana"], start=1):
    print(f"{i}. {fruit}")  # 1. apple, 2. banana

# zip — pair up elements from multiple iterables
names, ages = ["Alice", "Bob"], [30, 25]
dict(zip(names, ages))                     # {"Alice": 30, "Bob": 25}
# zip stops at shortest; use zip_longest for padding:
from itertools import zip_longest
list(zip_longest([1,2,3], [10,20], fillvalue=0))  # [(1,10), (2,20), (3,0)]

# Unzip with zip(*)
pairs = [(1, "a"), (2, "b")]
nums, letters = zip(*pairs)                # (1, 2), ("a", "b")

# Star unpacking
first, *rest = [1, 2, 3, 4]               # first=1, rest=[2,3,4]
first, *middle, last = [1, 2, 3, 4, 5]    # middle=[2,3,4]

# Star in function calls and merging
args = [1, 2, 3]
sum_fn = lambda a, b, c: a + b + c
sum_fn(*args)                              # unpacks list as positional args

merged_list = [*[1,2], *[3,4]]            # [1, 2, 3, 4]
merged_dict = {**{"a": 1}, **{"b": 2}}    # {"a": 1, "b": 2}
```

---

## 13. Python Gotchas

**Theory:** These are tricky behaviors that interviewers love to test. They reveal deep understanding of Python's object model.

### Mutable default arguments

```python
# BUG: default list is created ONCE at function definition, shared across all calls
def append_to(element, target=[]):
    target.append(element)
    return target

append_to(1)  # [1]
append_to(2)  # [1, 2] — NOT [2]! Same list object reused.

# FIX: use None as default, create new list inside
def append_to(element, target=None):
    if target is None:
        target = []
    target.append(element)
    return target
```

### Late binding closures

```python
# BUG: lambda captures variable `i` by REFERENCE, not by value
functions = [lambda: i for i in range(5)]
[f() for f in functions]  # [4, 4, 4, 4, 4] — all see final value of i

# FIX: default argument captures current value
functions = [lambda i=i: i for i in range(5)]
[f() for f in functions]  # [0, 1, 2, 3, 4]
```

### Integer caching & `is` vs `==`

```python
# Python caches integers -5 to 256. `is` checks identity (same object), `==` checks value.
a, b = 256, 256
a is b   # True — cached, same object

a, b = 257, 257
a is b   # False in REPL — different objects
a == b   # True — ALWAYS use == for values

# Rule: use `is` only for None, True, False. Use `==` for everything else.
```

### List multiplication trap

```python
# BUG: creates 3 references to the SAME inner list
grid = [[0]] * 3
grid[0][0] = 1
print(grid)  # [[1], [1], [1]] — all changed!

# FIX: list comprehension creates independent lists
grid = [[0] for _ in range(3)]
grid[0][0] = 1
print(grid)  # [[1], [0], [0]]
```

### Modifying list while iterating

```python
# BUG: iterator skips elements when list changes size during iteration
nums = [2, 4, 6, 8]
for x in nums:
    if x % 2 == 0:
        nums.remove(x)
print(nums)  # [4, 8] — not empty!

# FIX: create a new list
nums = [x for x in nums if x % 2 != 0]
```

---

## 14. FastAPI

**Theory:** FastAPI is a modern Python web framework for building APIs. It uses type hints for automatic validation and documentation. Key concepts:
- **Path operations** — functions decorated with `@app.get()`, `@app.post()`, etc.
- **Pydantic models** — define request/response schemas using Python classes with type hints
- **Dependency injection** — FastAPI resolves function parameters automatically
- **Async support** — use `async def` for non-blocking I/O operations

```python
from fastapi import FastAPI, HTTPException, Query, Path
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI()

# --- Pydantic models for request/response validation ---
# BaseModel auto-validates data types and generates JSON schema

class Item(BaseModel):
    name: str
    price: float = Field(gt=0, description="Price must be positive")
    description: Optional[str] = None  # Optional field with default None

class ItemResponse(BaseModel):
    id: int
    name: str
    price: float

# --- In-memory store (replace with DB in real apps) ---
items_db: dict[int, dict] = {}
next_id = 1

# --- GET — Read ---
@app.get("/")
def root():
    return {"message": "Hello, World!"}

# Path parameter — {item_id} in URL maps to function arg
@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int = Path(ge=1)):  # Path() adds validation: >= 1
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"id": item_id, **items_db[item_id]}

# Query parameters — /items?skip=0&limit=10
@app.get("/items")
def list_items(skip: int = Query(0, ge=0), limit: int = Query(10, le=100)):
    all_items = [{"id": k, **v} for k, v in items_db.items()]
    return all_items[skip : skip + limit]

# --- POST — Create ---
@app.post("/items", response_model=ItemResponse, status_code=201)
def create_item(item: Item):  # Request body auto-parsed from JSON into Item model
    global next_id
    items_db[next_id] = item.model_dump()  # Pydantic model -> dict
    result = {"id": next_id, **items_db[next_id]}
    next_id += 1
    return result

# --- PUT — Update ---
@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    items_db[item_id] = item.model_dump()
    return {"id": item_id, **items_db[item_id]}

# --- DELETE ---
@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    del items_db[item_id]
    return {"message": "Deleted"}

# --- Async endpoint (for I/O-bound operations like DB calls, HTTP requests) ---
import httpx  # async HTTP client

@app.get("/external")
async def fetch_external():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.github.com")
        return response.json()

# Run with: uvicorn filename:app --reload
# Docs auto-generated at: http://localhost:8000/docs (Swagger UI)
```

### Pydantic Validation Deep Dive

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date

class User(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str
    age: int = Field(ge=0, le=150)
    bio: Optional[str] = None
    joined: date = Field(default_factory=date.today)

    # Custom validator — runs after type validation
    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v.lower()

# Valid
user = User(name="Alice", email="ALICE@example.com", age=30)
print(user.email)  # "alice@example.com" — lowercased by validator

# Invalid — raises ValidationError with details
# User(name="", email="bad", age=-1)

# Convert to dict / JSON
user.model_dump()                   # {"name": "Alice", "email": "alice@example.com", ...}
user.model_dump_json()              # JSON string
User.model_validate({"name": "Bob", "email": "bob@test.com", "age": 25})  # dict -> model
```

---

## 15. Multithreading Basics

**Theory:** Python's GIL (Global Interpreter Lock) means only one thread runs Python code at a time. So threads DON'T speed up CPU-bound work. But for I/O-bound work (network, files, DB), threads are great because they release the GIL while waiting. `ThreadPoolExecutor` is the modern, clean API.

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def fetch_page(url):
    time.sleep(1)  # simulate network delay
    return f"Content of {url}"

urls = [f"https://example.com/{i}" for i in range(10)]

# ThreadPoolExecutor manages a pool of threads
# max_workers = how many threads run concurrently
with ThreadPoolExecutor(max_workers=5) as executor:
    # map — results come in submission order
    results = list(executor.map(fetch_page, urls))  # ~2 sec for 10 URLs (5 at a time)

    # submit + as_completed — results come as they finish
    futures = {executor.submit(fetch_page, url): url for url in urls}
    for future in as_completed(futures):
        url = futures[future]
        result = future.result()  # blocks until this future is done

# For CPU-bound work, use ProcessPoolExecutor instead (spawns separate processes, bypasses GIL)
from concurrent.futures import ProcessPoolExecutor

def cpu_heavy(n):
    return sum(i * i for i in range(n))

with ProcessPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(cpu_heavy, [10**6] * 4))
```

---

## 16. Database Basics (sqlite3)

**Theory:** `sqlite3` is built into Python — no install needed. It stores the entire database in a single file (or `:memory:` for testing). Always use `?` placeholders to prevent SQL injection — NEVER use f-strings or string formatting in SQL queries.

```python
import sqlite3

# Connect and create table
conn = sqlite3.connect(":memory:")  # use "app.db" for a file
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        department TEXT,
        salary REAL
    )
""")

# INSERT — always use ? placeholders (prevents SQL injection)
cursor.execute("INSERT INTO employees (name, department, salary) VALUES (?, ?, ?)",
               ("Alice", "Engineering", 95000))

# Insert multiple rows
cursor.executemany("INSERT INTO employees (name, department, salary) VALUES (?, ?, ?)", [
    ("Bob", "Marketing", 72000),
    ("Charlie", "Engineering", 88000),
])
conn.commit()

# READ
cursor.execute("SELECT name, salary FROM employees WHERE department = ?", ("Engineering",))
rows = cursor.fetchall()           # [("Alice", 95000), ("Charlie", 88000)]

# Row factory — access columns by name instead of index
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT * FROM employees WHERE id = ?", (1,))
row = cursor.fetchone()
print(row["name"], row["salary"])  # Alice 95000.0

# UPDATE and DELETE
cursor.execute("UPDATE employees SET salary = ? WHERE name = ?", (100000, "Alice"))
cursor.execute("DELETE FROM employees WHERE name = ?", ("Bob",))
conn.commit()
conn.close()
```

---

## 17. Data Transformation

```python
from collections import defaultdict

# Transpose a matrix
matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
transposed = list(map(list, zip(*matrix)))
# [[1,4,7], [2,5,8], [3,6,9]]
# How it works: zip(*matrix) unpacks rows as args to zip, which groups by column position

# Group and aggregate
orders = [
    {"customer": "Alice", "amount": 25},
    {"customer": "Bob", "amount": 50},
    {"customer": "Alice", "amount": 50},
]

groups = defaultdict(list)
for order in orders:
    groups[order["customer"]].append(order["amount"])

summary = {k: {"total": sum(v), "avg": sum(v)/len(v)} for k, v in groups.items()}
# {"Alice": {"total": 75, "avg": 37.5}, "Bob": {"total": 50, "avg": 50}}

# Flatten nested dict
def flatten_dict(d, parent_key="", sep="."):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

flatten_dict({"a": 1, "b": {"c": 2, "d": {"e": 3}}})
# {"a": 1, "b.c": 2, "b.d.e": 3}

# Reshape: list of dicts <-> dict of lists
records = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
columns = {key: [r[key] for r in records] for key in records[0]}
# {"name": ["Alice", "Bob"], "age": [30, 25]}
```

---

## 18. Recursion (Simple)

**Theory:** Recursion = a function that calls itself. Every recursive function needs a **base case** (when to stop) and a **recursive case** (how to break the problem down). Python has a default recursion limit of 1000 (`sys.setrecursionlimit()` to change).

```python
import os

# Directory traversal — find all files matching an extension
def find_files(directory, extension):
    results = []
    for entry in os.listdir(directory):
        path = os.path.join(directory, entry)
        if os.path.isdir(path):
            results.extend(find_files(path, extension))  # recurse into subdirectory
        elif entry.endswith(extension):
            results.append(path)
    return results

# Deep flatten — works with any nesting depth
def deep_flatten(lst):
    result = []
    for item in lst:
        if isinstance(item, (list, tuple)):
            result.extend(deep_flatten(item))   # recurse into nested list
        else:
            result.append(item)
    return result

deep_flatten([1, [2, [3, [4]]]])  # [1, 2, 3, 4]

# Deep search — find all values for a key in nested data
def deep_find(data, target_key):
    results = []
    if isinstance(data, dict):
        for k, v in data.items():
            if k == target_key:
                results.append(v)
            results.extend(deep_find(v, target_key))
    elif isinstance(data, (list, tuple)):
        for item in data:
            results.extend(deep_find(item, target_key))
    return results

config = {"app": {"name": "MyApp"}, "servers": [{"name": "web1"}, {"name": "web2"}]}
deep_find(config, "name")  # ["MyApp", "web1", "web2"]
```

---

## 19. Python One-Liners

```python
# Flatten list of lists
flat = [x for sub in [[1,2],[3,4]] for x in sub]

# Palindrome check
is_palindrome = lambda s: s.lower() == s.lower()[::-1]

# FizzBuzz
fb = ["FizzBuzz" if i%15==0 else "Fizz" if i%3==0 else "Buzz" if i%5==0 else str(i) for i in range(1,101)]

# Most common element
from collections import Counter
most_common = Counter([1,2,2,3,3,3]).most_common(1)[0][0]

# Unique elements preserving order
unique = list(dict.fromkeys([3, 1, 4, 1, 5, 9, 2, 6, 5]))

# Sum of digits
digit_sum = lambda n: sum(int(d) for d in str(abs(n)))

# Chunk a list into groups of n
chunk = lambda lst, n: [lst[i:i+n] for i in range(0, len(lst), n)]

# Dict from alternating list
items = ["a", 1, "b", 2, "c", 3]
d = dict(zip(items[::2], items[1::2]))  # {"a":1, "b":2, "c":3}

# Check if prime
is_prime = lambda n: n > 1 and all(n % i for i in range(2, int(n**0.5) + 1))

# Random password
import random, string
pw = "".join(random.choices(string.ascii_letters + string.digits, k=16))

# Matrix transpose
transposed = list(map(list, zip(*matrix)))

# Remove falsy values
cleaned = list(filter(None, [0, "", None, "hi", [], [1]]))  # ["hi", [1]]

# Intersection of multiple lists
common = set.intersection(*map(set, [[1,2,3], [2,3,4], [3,4,5]]))  # {3}
```

---

## 20. Practice Problems

### Easy
1. Write a function to reverse each word in a sentence: `"hello world"` -> `"olleh dlrow"`
2. Count vowels, consonants, digits, and special chars in a string.
3. Find the second largest number in a list without sorting.
4. Remove duplicates from a list preserving order — do it in one line.
5. Given a string, return the top 3 most frequent characters (excluding spaces).

### Medium
6. Parse log lines (`"2025-01-15 14:30:22 ERROR msg"`) — return error count per hour.
7. Given a list of strings, group anagrams together.
8. Implement run-length encoding/decoding: `"AAABBC"` <-> `"3A2B1C"`
9. Write a function that deep-merges two nested dicts (recursive merge).
10. Sort version strings correctly: `["1.2.3", "1.0.0", "2.1.0", "1.2.10"]`

### Hard
11. Build a data pipeline using `pipe()` that reads a CSV string, filters rows, transforms values, and aggregates results — all using functional composition.
12. Write a schema validator: given a dict and a schema like `{"name": str, "age": int}`, return validation errors.
13. Build a FastAPI CRUD app for a todo list with Pydantic validation.

---

## Quick Reference

| Task | Tool |
|------|------|
| Transform every element | `map()` or list comprehension |
| Keep elements matching condition | `filter()` or comprehension with `if` |
| Accumulate into single value | `reduce()` |
| Count occurrences | `Counter` |
| Group by key | `defaultdict(list)` |
| Remove duplicates (ordered) | `dict.fromkeys()` |
| Sort by custom field | `sorted(key=lambda ...)` |
| Parse text patterns | `re` module |
| Date math | `datetime + timedelta` |
| Fast double-ended queue | `deque` |
| All combinations/permutations | `itertools` |
| Concurrent I/O | `ThreadPoolExecutor` |
| Concurrent CPU | `ProcessPoolExecutor` |
| Quick local database | `sqlite3` |
| Web APIs | `FastAPI` |

---

*Type out each example by hand. Understanding > memorization. Good luck!*
