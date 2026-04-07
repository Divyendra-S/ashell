# Python Interview Coding Mastery — Complete Theory & Practice Guide

---

## How to Approach Any Coding Problem

Before diving into concepts, internalize this framework. Every interview problem follows the same mental process:

### Step 1: Understand the Problem

Read the problem twice. On the first read, get the gist. On the second read, identify:

- **Input** — What data are you given? What type? What size?
- **Output** — What exactly should you return? A number? A list? A boolean?
- **Constraints** — Are there size limits? Time limits? Can values be negative?
- **Edge cases** — What happens with empty input? Single element? All same values?

### Step 2: Think in Examples

Walk through 2-3 examples by hand. Include:

- A normal case
- A small case (1-2 elements)
- An edge case (empty, all duplicates, negative numbers)

Write these down. They become your test cases later.

### Step 3: Identify the Pattern

Ask yourself:

- Is this a **search** problem? → Think hash maps, binary search
- Is this a **counting** problem? → Think dictionaries, Counter
- Is this a **comparison** problem? → Think sorting, two pointers
- Is this a **building** problem? → Think recursion, dynamic programming
- Is this a **sequential** problem? → Think sliding window, stacks

### Step 4: Write Pseudocode

Don't jump to code. Write plain English steps first. This catches logical errors early.

### Step 5: Code It

Keep it clean. Use descriptive variable names. Don't try to be clever — be clear.

### Step 6: Test It

Run your examples through the code mentally. Trace each variable. Check your edge cases.

---

## Understanding Time & Space Complexity (Big O)

Before we get into problems, you MUST understand Big O. Interviewers care about this as much as correctness.

### What is Big O?

Big O describes how your algorithm's performance **scales** as input grows. It answers: "If I double my input size, how much slower does this get?"

### Common Complexities (Best to Worst)

| Big O | Name | Example | Feel |
|-------|------|---------|------|
| O(1) | Constant | Dictionary lookup | Instant, no matter the size |
| O(log n) | Logarithmic | Binary search | Cuts problem in half each step |
| O(n) | Linear | Single loop through list | Touch each element once |
| O(n log n) | Linearithmic | Merge sort, Tim sort | Best possible general sort |
| O(n²) | Quadratic | Nested loops | Every element compared to every other |
| O(2^n) | Exponential | Naive recursion (Fibonacci) | Doubles with each new element |
| O(n!) | Factorial | Generating all permutations | Absolutely massive |

### How to Determine Complexity

**Rule 1:** Count your loops.

```python
# O(n) — one loop
for item in lst:
    print(item)

# O(n²) — nested loops over SAME data
for i in lst:
    for j in lst:
        print(i, j)

# O(n * m) — nested loops over DIFFERENT data
for i in list_a:      # n items
    for j in list_b:  # m items
        print(i, j)
```

**Rule 2:** Drop constants and lower terms.

```python
# This is O(n), NOT O(3n)
for item in lst:    # n
    pass
for item in lst:    # n
    pass
for item in lst:    # n
    pass
# Total: 3n → O(n)
```

**Rule 3:** Dictionary/set operations are O(1).

```python
my_dict = {}
my_dict["key"] = "value"    # O(1)
"key" in my_dict             # O(1)
my_set = set()
my_set.add(5)                # O(1)
5 in my_set                  # O(1)
```

**Rule 4:** Sorting is O(n log n).

```python
sorted(my_list)  # O(n log n)
my_list.sort()   # O(n log n)
```

### Space Complexity

Same idea, but for memory. If you create a new list of size n, that's O(n) space. If you only use a few variables, that's O(1) space.

```python
# O(1) space — only using a counter variable
def sum_list(lst):
    total = 0
    for num in lst:
        total += num
    return total

# O(n) space — creating a new list
def double_list(lst):
    return [x * 2 for x in lst]
```

---

## LEVEL 1 — Basics (Strings, Numbers, Loops)

---

### 1.1 String Reversal & Palindromes

#### Theory

A **string** in Python is an immutable sequence of characters. "Immutable" means once created, you cannot change individual characters — you must create a new string.

```python
s = "hello"
# s[0] = "H"    # ERROR! Strings are immutable
s = "H" + s[1:]  # Create a NEW string → "Hello"
```

A **palindrome** is a word, phrase, or sequence that reads the same forwards and backwards. Examples: `"madam"`, `"racecar"`, `"A man a plan a canal Panama"` (ignoring spaces and case).

#### Approach 1: Slicing

Python slicing syntax is `s[start:stop:step]`. When step is -1, it reverses:

```python
s = "hello"
print(s[::-1])    # "olleh"
print(s[1:4])     # "ell" (index 1, 2, 3)
print(s[::2])     # "hlo" (every 2nd char)
```

**How slicing works internally:** `s[::-1]` means "start from end, go to beginning, step backwards by 1." Python creates a NEW string with characters in reverse order. Time: O(n). Space: O(n) because a new string is created.

```python
def is_palindrome(s):
    s = s.lower()
    return s == s[::-1]

# Test
print(is_palindrome("Madam"))    # True
print(is_palindrome("hello"))    # False
print(is_palindrome("racecar"))  # True
```

#### Approach 2: Two Pointers

The **two-pointer technique** uses two indices that move toward each other. This is a fundamental pattern that appears in many problems.

```python
def is_palindrome_two_pointer(s):
    s = s.lower()
    left = 0
    right = len(s) - 1
    
    while left < right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    
    return True
```

**Why two pointers?** Instead of creating a reversed copy (O(n) space), we compare characters in-place using O(1) extra space. The trade-off: same O(n) time, but less memory.

**Visual walkthrough with "racecar":**

```
Step 1:  r a c e c a r
         ^           ^
         left=0   right=6    r == r ✓

Step 2:  r a c e c a r
           ^       ^
           left=1  right=5   a == a ✓

Step 3:  r a c e c a r
             ^   ^
             left=2 right=4  c == c ✓

Step 4:  r a c e c a r
               ^
           left=3 right=3    left NOT < right → STOP

Return True
```

#### Handling Real-World Palindromes

Interview problems often want you to ignore spaces, punctuation, and case:

```python
def is_palindrome_clean(s):
    # Keep only letters and digits, convert to lowercase
    cleaned = ""
    for char in s:
        if char.isalnum():     # checks if letter or digit
            cleaned += char.lower()
    
    return cleaned == cleaned[::-1]

# Or more Pythonically:
def is_palindrome_clean_v2(s):
    cleaned = "".join(c.lower() for c in s if c.isalnum())
    return cleaned == cleaned[::-1]

# Test
print(is_palindrome_clean("A man, a plan, a canal: Panama"))  # True
print(is_palindrome_clean("race a car"))                       # False
```

**Key methods to know:**

- `str.isalnum()` → True if character is letter or digit
- `str.isalpha()` → True if character is a letter
- `str.isdigit()` → True if character is a digit
- `str.lower()` → returns lowercase version
- `str.upper()` → returns uppercase version

---

### 1.2 Fibonacci Series

#### Theory

The Fibonacci sequence starts with 0 and 1, and each subsequent number is the sum of the two preceding numbers:

```
Index:  0  1  2  3  4  5  6  7   8   9   10
Value:  0  1  1  2  3  5  8  13  21  34  55
```

Mathematical definition:

```
F(0) = 0
F(1) = 1
F(n) = F(n-1) + F(n-2)  for n > 1
```

This is interesting because it naturally lends itself to recursion, but the naive recursive solution is terribly inefficient.

#### Approach 1: Iterative (BEST for interviews)

```python
def fibonacci(n):
    """Return the nth Fibonacci number. F(0)=0, F(1)=1, ..."""
    if n <= 1:
        return n
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

# What happens step by step for fibonacci(6):
# Start: a=0, b=1
# i=2:   a=1, b=0+1=1     → F(2) = 1
# i=3:   a=1, b=1+1=2     → F(3) = 2
# i=4:   a=2, b=1+2=3     → F(4) = 3
# i=5:   a=3, b=2+3=5     → F(5) = 5
# i=6:   a=5, b=3+5=8     → F(6) = 8
```

**Time: O(n), Space: O(1)** — This is optimal.

**The Python swap trick:** `a, b = b, a + b` works because Python evaluates the RIGHT side completely before assigning. It's equivalent to:

```python
temp = a + b
a = b
b = temp
```

But the tuple unpacking version is cleaner and more Pythonic.

#### Approach 2: Recursive (Understand why it's slow)

```python
def fib_recursive(n):
    if n <= 1:
        return n
    return fib_recursive(n - 1) + fib_recursive(n - 2)
```

**Why this is O(2^n):** Each call spawns TWO more calls. For `fib(5)`:

```
                    fib(5)
                   /      \
              fib(4)       fib(3)
             /    \        /    \
         fib(3)  fib(2)  fib(2) fib(1)
         /   \    /  \    /  \
     fib(2) fib(1) fib(1) fib(0) fib(1) fib(0)
      / \
  fib(1) fib(0)
```

Notice `fib(3)` is calculated twice, `fib(2)` three times. This redundant work explodes as n grows. `fib(30)` makes over a million calls. `fib(50)` would take hours.

#### Approach 3: Recursive + Memoization

**Memoization** means "remember results you've already computed." Store them in a cache (dictionary) and look up before recalculating.

```python
# Manual memoization — understand how it works
def fib_memo(n, cache=None):
    if cache is None:
        cache = {}
    
    if n in cache:
        return cache[n]
    
    if n <= 1:
        return n
    
    cache[n] = fib_memo(n - 1, cache) + fib_memo(n - 2, cache)
    return cache[n]

# Using Python's built-in decorator
from functools import lru_cache

@lru_cache(maxsize=None)
def fib_lru(n):
    if n <= 1:
        return n
    return fib_lru(n - 1) + fib_lru(n - 2)
```

**Time: O(n), Space: O(n)** — Each value computed only once and stored.

**How `@lru_cache` works:** It's a decorator (we'll cover decorators later) that wraps your function with a dictionary. Before calling your function, it checks "have I seen these arguments before?" If yes, returns cached result. If no, calls function and caches result. `maxsize=None` means unlimited cache.

#### Generating the whole sequence

```python
def fib_sequence(n):
    """Return first n Fibonacci numbers as a list."""
    if n <= 0:
        return []
    if n == 1:
        return [0]
    
    seq = [0, 1]
    for _ in range(2, n):
        seq.append(seq[-1] + seq[-2])
    return seq

print(fib_sequence(10))  # [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
```

---

### 1.3 Factorial

#### Theory

The factorial of n (written as n!) is the product of all positive integers from 1 to n:

```
0! = 1  (by definition)
1! = 1
5! = 5 × 4 × 3 × 2 × 1 = 120
10! = 3,628,800
```

Factorials grow VERY fast. 20! = 2,432,902,008,176,640,000. Python handles big integers natively (no overflow like in C/Java), which is a common interview talking point.

#### Iterative

```python
def factorial(n):
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result

# Trace for factorial(5):
# result = 1
# i=2: result = 1 * 2 = 2
# i=3: result = 2 * 3 = 6
# i=4: result = 6 * 4 = 24
# i=5: result = 24 * 5 = 120
```

#### Recursive

```python
def factorial_rec(n):
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n <= 1:      # Base case
        return 1
    return n * factorial_rec(n - 1)   # Recursive case

# Call stack for factorial_rec(4):
# factorial_rec(4) → 4 * factorial_rec(3)
#                         → 3 * factorial_rec(2)
#                               → 2 * factorial_rec(1)
#                                     → returns 1  (base case)
#                               → returns 2 * 1 = 2
#                         → returns 3 * 2 = 6
#                   → returns 4 * 6 = 24
```

**Understanding Recursion:** Every recursive function needs:

1. **Base case** — when to STOP recursing (prevents infinite loop)
2. **Recursive case** — the function calls itself with a SMALLER problem
3. **Progress** — each call must move TOWARD the base case

**Python's recursion limit:** By default, Python allows ~1000 recursive calls. For `factorial_rec(1001)`, you'd get a `RecursionError`. This is why iterative solutions are often preferred.

```python
import sys
print(sys.getrecursionlimit())    # 1000
sys.setrecursionlimit(5000)       # You CAN increase it, but shouldn't rely on this
```

#### Using math module

```python
import math
print(math.factorial(5))   # 120 — C-optimized, fastest option
```

---

### 1.4 Reversing a String (Without Slicing)

#### Why this is asked

Interviewers want to see if you understand iteration and string building, not just Python shortcuts.

```python
# Method 1: Loop building a new string
def reverse_string(s):
    reversed_str = ""
    for char in s:
        reversed_str = char + reversed_str  # prepend each character
    return reversed_str

# Trace for "hello":
# ""       → "h"
# "h"      → "eh"
# "eh"     → "leh"
# "leh"    → "lleh"
# "lleh"   → "olleh"
```

**Note on performance:** String concatenation in a loop creates a new string each time (because strings are immutable). For large strings, this is O(n²). Better approach:

```python
# Method 2: Build a list, then join (O(n))
def reverse_string_fast(s):
    chars = []
    for char in s:
        chars.append(char)
    chars.reverse()
    return "".join(chars)

# Method 3: Using list() and reversed()
def reverse_string_builtin(s):
    return "".join(reversed(s))
```

**Why list + join is faster:** Lists are mutable, so `.append()` is O(1) amortized. Joining at the end is one O(n) operation. Total: O(n) vs O(n²) for string concatenation.

---

### 1.5 Counting Vowels

```python
def count_vowels(s):
    vowels = set("aeiouAEIOU")  # set for O(1) lookup
    count = 0
    for char in s:
        if char in vowels:
            count += 1
    return count

# Pythonic one-liner
def count_vowels_v2(s):
    return sum(1 for char in s if char.lower() in "aeiou")

# Test
print(count_vowels("Hello World"))    # 3 (e, o, o)
print(count_vowels("Python"))         # 1 (o)
```

**Why use a set instead of a string for vowels?** Checking `char in "aeiou"` scans the string linearly — O(k) where k is the string length. Checking `char in set("aeiou")` is O(1) hash lookup. For this specific case the difference is trivial (only 5 vowels), but the PRINCIPLE matters for interviews.

---

## LEVEL 2 — Common Patterns (Lists, Dicts, Sets)

---

### 2.1 Python Data Structures Deep Dive

Before tackling problems, understand the three workhorses:

#### Lists

Ordered, mutable, allow duplicates. Backed by a dynamic array internally.

```python
lst = [1, 2, 3, 4, 5]

# Common operations and their complexity:
lst[0]            # O(1) — index access
lst.append(6)     # O(1) amortized — add to end
lst.insert(0, 0)  # O(n) — must shift all elements right
lst.pop()         # O(1) — remove from end
lst.pop(0)        # O(n) — remove from front, shift all left
5 in lst          # O(n) — must scan entire list
lst.sort()        # O(n log n)
len(lst)          # O(1) — Python tracks length
```

#### Dictionaries (Hash Maps)

Unordered key-value pairs (ordered by insertion since Python 3.7). Keys must be hashable (immutable).

```python
d = {"apple": 3, "banana": 5}

# Common operations — ALL O(1) average:
d["apple"]              # Access — O(1)
d["cherry"] = 7         # Insert — O(1)
"apple" in d            # Membership check — O(1)
del d["apple"]          # Delete — O(1)
d.get("grape", 0)       # Safe access with default — O(1)
d.keys()                # View of keys
d.values()              # View of values
d.items()               # View of (key, value) pairs
```

**How hash maps work (simplified):** Python computes a hash of the key (a number), uses it to find a slot in an internal array, and stores the value there. Lookup is instant because you compute the hash → jump directly to the slot. This is why keys must be immutable — if a key changed after being hashed, you'd never find it again.

#### Sets

Unordered, no duplicates. Like a dict with only keys.

```python
s = {1, 2, 3, 4, 5}

# Common operations — ALL O(1) average:
s.add(6)          # Add element
s.remove(3)       # Remove (raises error if missing)
s.discard(3)      # Remove (no error if missing)
5 in s            # Membership check — O(1)
s1 & s2           # Intersection
s1 | s2           # Union
s1 - s2           # Difference
s1 ^ s2           # Symmetric difference (in one but not both)
```

---

### 2.2 Finding Duplicates

#### Theory

The brute force approach compares every element with every other element — O(n²). Using a set brings this down to O(n) because set lookups are O(1).

```python
# Brute force — O(n²) — DON'T do this in an interview
def find_duplicates_brute(lst):
    duplicates = []
    for i in range(len(lst)):
        for j in range(i + 1, len(lst)):
            if lst[i] == lst[j] and lst[i] not in duplicates:
                duplicates.append(lst[i])
    return duplicates

# Optimal — O(n) time, O(n) space
def find_duplicates(lst):
    seen = set()
    duplicates = set()
    for item in lst:
        if item in seen:       # O(1) check
            duplicates.add(item)
        seen.add(item)
    return list(duplicates)

# Using Counter — also O(n)
from collections import Counter

def find_duplicates_counter(lst):
    counts = Counter(lst)
    return [item for item, count in counts.items() if count > 1]

# Test
print(find_duplicates([1, 2, 3, 2, 4, 5, 1]))  # [1, 2]
```

**Why two sets?** `seen` tracks what we've encountered. `duplicates` collects items we've seen more than once. We use a set for `duplicates` too, so if an item appears 5 times, it only ends up in our result once.

---

### 2.3 Counting Frequency

#### Theory

Frequency counting is one of the most common patterns in coding interviews. The core idea: iterate through data, count occurrences using a dictionary.

```python
# Manual approach — understand this first
def char_frequency(s):
    freq = {}
    for char in s:
        if char in freq:
            freq[char] += 1
        else:
            freq[char] = 1
    return freq

# Cleaner with dict.get()
def char_frequency_v2(s):
    freq = {}
    for char in s:
        freq[char] = freq.get(char, 0) + 1
    return freq

# Using defaultdict — auto-creates missing keys
from collections import defaultdict

def char_frequency_v3(s):
    freq = defaultdict(int)    # missing keys default to 0
    for char in s:
        freq[char] += 1
    return dict(freq)

# Using Counter — most Pythonic
from collections import Counter

def char_frequency_v4(s):
    return dict(Counter(s))

# Test
print(char_frequency("mississippi"))
# {'m': 1, 'i': 4, 's': 4, 'p': 2}
```

**`dict.get(key, default)` explained:**

```python
d = {"a": 1}
d.get("a", 0)    # Returns 1 (key exists)
d.get("b", 0)    # Returns 0 (key missing, use default)
d.get("b")       # Returns None (no default specified)
d["b"]           # Raises KeyError! 
```

This is why `get` is preferred — it never crashes.

**Counter extras:**

```python
c = Counter("abracadabra")
# Counter({'a': 5, 'b': 2, 'r': 2, 'c': 1, 'd': 1})

c.most_common(3)       # [('a', 5), ('b', 2), ('r', 2)]
c.most_common(1)[0]    # ('a', 5)  — most frequent element

# Counter arithmetic
c1 = Counter("aab")
c2 = Counter("abb")
print(c1 + c2)    # Counter({'a': 3, 'b': 3})
print(c1 - c2)    # Counter({'a': 1})
```

---

### 2.4 Two Sum

#### Theory

This is one of the most famous interview problems (LeetCode #1). Given a list of numbers and a target, find two numbers that add up to the target. Return their indices.

**Key insight:** If you need `a + b = target`, then `b = target - a`. So for each number, you ask: "Have I already seen its complement?"

```python
# Brute force — O(n²)
def two_sum_brute(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []

# Optimal — O(n) using hash map
def two_sum(nums, target):
    seen = {}     # value → index
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []

# Walkthrough: two_sum([2, 7, 11, 15], 9)
# i=0, num=2: complement=7, seen={} → not found → seen={2:0}
# i=1, num=7: complement=2, seen={2:0} → FOUND! → return [0, 1]
```

**Why this is O(n):** We traverse the list once. Each step does an O(1) dictionary lookup and an O(1) dictionary insertion. Total: O(n).

**`enumerate()` explained:**

```python
fruits = ["apple", "banana", "cherry"]

# Without enumerate:
for i in range(len(fruits)):
    print(i, fruits[i])

# With enumerate (cleaner):
for i, fruit in enumerate(fruits):
    print(i, fruit)

# Output:
# 0 apple
# 1 banana
# 2 cherry

# You can set starting index:
for i, fruit in enumerate(fruits, start=1):
    print(i, fruit)
# 1 apple
# 2 banana
# 3 cherry
```

---

### 2.5 Anagram Check

#### Theory

Two strings are **anagrams** if they contain exactly the same characters in the same quantities, but possibly in a different order.

- "listen" and "silent" → anagrams
- "hello" and "world" → not anagrams
- "aabb" and "abab" → anagrams

**Core insight:** Two strings are anagrams if and only if their character frequency counts are identical.

```python
# Method 1: Sorting — O(n log n)
def is_anagram_sort(s1, s2):
    return sorted(s1.lower()) == sorted(s2.lower())

# Why this works: if two strings have the same characters,
# sorting them produces the same result.
# sorted("listen") → ['e', 'i', 'l', 'n', 's', 't']
# sorted("silent") → ['e', 'i', 'l', 'n', 's', 't']

# Method 2: Counter — O(n)
from collections import Counter

def is_anagram(s1, s2):
    return Counter(s1.lower()) == Counter(s2.lower())

# Method 3: Manual frequency count — O(n)
def is_anagram_manual(s1, s2):
    if len(s1) != len(s2):     # Quick early exit
        return False
    
    freq = {}
    for char in s1.lower():
        freq[char] = freq.get(char, 0) + 1
    for char in s2.lower():
        freq[char] = freq.get(char, 0) - 1
    
    return all(v == 0 for v in freq.values())

# Test
print(is_anagram("Listen", "Silent"))    # True
print(is_anagram("hello", "world"))      # False
```

**Method 3 explained:** Count up for s1, count down for s2. If all counts end at 0, they have identical character distributions.

---

### 2.6 List Flattening

#### Theory

A nested list like `[1, [2, [3, 4]], 5]` has lists inside lists. "Flattening" means producing a single-level list: `[1, 2, 3, 4, 5]`.

This is a natural **recursion** problem because the nesting can be arbitrarily deep.

```python
def flatten(lst):
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(flatten(item))  # recurse into sublists
        else:
            result.append(item)           # add non-list items
    return result

# Trace for flatten([1, [2, [3, 4]], 5]):
# item=1       → not list → append 1           result=[1]
# item=[2,[3,4]] → is list → flatten it:
#   item=2      → not list → append 2          inner=[2]
#   item=[3,4]  → is list → flatten it:
#     item=3    → not list → append 3          inner=[3]
#     item=4    → not list → append 4          inner=[3,4]
#     return [3,4]
#   → extend with [3,4]                       inner=[2,3,4]
#   return [2,3,4]
# → extend with [2,3,4]                       result=[1,2,3,4]
# item=5       → not list → append 5          result=[1,2,3,4,5]

# Test
print(flatten([1, [2, [3, 4]], 5]))          # [1, 2, 3, 4, 5]
print(flatten([[1, 2], [3, [4, [5, 6]]]]))  # [1, 2, 3, 4, 5, 6]
```

**`isinstance()` explained:**

```python
isinstance(5, int)          # True
isinstance("hi", str)       # True
isinstance([1,2], list)     # True
isinstance(5, (int, float)) # True — check multiple types
```

**`extend()` vs `append()`:**

```python
lst = [1, 2]
lst.append([3, 4])     # [1, 2, [3, 4]]  — adds the LIST as one element
lst = [1, 2]
lst.extend([3, 4])     # [1, 2, 3, 4]    — adds each ITEM from the list
```

#### Iterative version using a stack

```python
def flatten_iter(lst):
    stack = list(lst)       # copy the list into a stack
    result = []
    while stack:
        item = stack.pop(0) # take from front to preserve order
        if isinstance(item, list):
            # Put the list's items back at the front
            stack = list(item) + stack
        else:
            result.append(item)
    return result
```

---

## LEVEL 3 — Intermediate (String Manipulation, Math, Logic)

---

### 3.1 Prime Numbers

#### Theory

A **prime number** is a natural number greater than 1 that has no positive divisors other than 1 and itself.

- Primes: 2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, ...
- Not primes: 4 (2×2), 6 (2×3), 9 (3×3), 15 (3×5)
- **2 is the only even prime** — every other even number is divisible by 2
- **1 is NOT prime** — by definition

**Why only check up to √n?** If `n = a × b`, then one of `a` or `b` must be ≤ √n. If both were > √n, then `a × b > n`, which is a contradiction. So if no factor is found up to √n, the number is prime.

Example: Is 36 prime? √36 = 6. Check 2,3,4,5,6. 36/2=18 → not prime.
Example: Is 37 prime? √37 ≈ 6.08. Check 2,3,4,5,6. None divide 37 → prime!

```python
import math

def is_prime(n):
    if n < 2:
        return False
    if n == 2:
        return True          # 2 is prime
    if n % 2 == 0:
        return False         # Even numbers > 2 are not prime
    
    for i in range(3, int(math.sqrt(n)) + 1, 2):  # Only check odd numbers
        if n % i == 0:
            return False
    return True

# Test
print(is_prime(2))     # True
print(is_prime(17))    # True
print(is_prime(15))    # False (3×5)
print(is_prime(1))     # False
```

#### Sieve of Eratosthenes

When you need ALL primes up to n, checking each number individually is O(n√n). The **Sieve** is much faster at O(n log log n).

**How it works:**

1. Create a boolean list from 0 to n, all set to True
2. Mark 0 and 1 as not prime
3. Starting from 2, mark all multiples of 2 as not prime
4. Move to next unmarked number (3), mark its multiples
5. Continue until √n

```python
def sieve_of_eratosthenes(n):
    if n < 2:
        return []
    
    is_prime = [True] * (n + 1)
    is_prime[0] = is_prime[1] = False
    
    for i in range(2, int(math.sqrt(n)) + 1):
        if is_prime[i]:
            # Mark all multiples of i as not prime
            # Start from i*i because smaller multiples are already marked
            for j in range(i * i, n + 1, i):
                is_prime[j] = False
    
    return [i for i, prime in enumerate(is_prime) if prime]

# Visual walkthrough for sieve(20):
# Start: [F, F, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T]
#                                                        indices 0-20
# i=2: mark 4,6,8,10,12,14,16,18,20
# i=3: mark 9,15 (6,12,18 already marked by 2)
# i=4: already marked, skip
# Remaining True indices: [2, 3, 5, 7, 11, 13, 17, 19]

print(sieve_of_eratosthenes(30))
# [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
```

---

### 3.2 String Compression

#### Theory

Compress a string by replacing consecutive repeated characters with the character followed by its count. This is a simplified version of **Run-Length Encoding (RLE)**.

```
"aaabbc"     → "a3b2c1"
"aabbcc"     → "a2b2c2"
"abcd"       → "a1b1c1d1"
"aaaaaaa"    → "a7"
```

**The pattern:** Walk through the string, keeping track of the current character and how many times it repeats. When the character changes, flush the count to the result.

```python
def compress(s):
    if not s:
        return ""
    
    result = []
    count = 1
    
    for i in range(1, len(s)):
        if s[i] == s[i - 1]:
            count += 1
        else:
            result.append(f"{s[i-1]}{count}")
            count = 1
    
    # Don't forget the LAST group!
    result.append(f"{s[-1]}{count}")
    
    return "".join(result)

# Trace for "aaabbc":
# i=1: s[1]='a' == s[0]='a' → count=2
# i=2: s[2]='a' == s[1]='a' → count=3
# i=3: s[3]='b' != s[2]='a' → append "a3", count=1
# i=4: s[4]='b' == s[3]='b' → count=2
# i=5: s[5]='c' != s[4]='b' → append "b2", count=1
# After loop: append "c1"
# Result: "a3b2c1"
```

**Common variation:** Only return compressed if it's shorter than original:

```python
def compress_smart(s):
    compressed = compress(s)
    return compressed if len(compressed) < len(s) else s
```

---

### 3.3 FizzBuzz

#### Theory

FizzBuzz is a classic warm-up problem that tests basic conditional logic. For numbers 1 to n:

- If divisible by 3 AND 5: print "FizzBuzz"
- If divisible by 3 only: print "Fizz"
- If divisible by 5 only: print "Buzz"
- Otherwise: print the number

**Key insight:** Check the most specific condition first. If you check `% 3` before `% 15`, you'll print "Fizz" for 15 instead of "FizzBuzz".

```python
def fizzbuzz(n):
    result = []
    for i in range(1, n + 1):
        if i % 15 == 0:        # divisible by BOTH 3 and 5
            result.append("FizzBuzz")
        elif i % 3 == 0:
            result.append("Fizz")
        elif i % 5 == 0:
            result.append("Buzz")
        else:
            result.append(str(i))
    return result

# Alternative: string building approach (more extensible)
def fizzbuzz_v2(n):
    result = []
    for i in range(1, n + 1):
        s = ""
        if i % 3 == 0:
            s += "Fizz"
        if i % 5 == 0:
            s += "Buzz"
        result.append(s or str(i))
    return result

# Why v2 is better: easy to extend
# Want to add "Jazz" for multiples of 7? Just add:
# if i % 7 == 0: s += "Jazz"
```

**The `s or str(i)` trick:** In Python, an empty string is "falsy". So if `s` is empty (number not divisible by 3 or 5), `s or str(i)` returns `str(i)`.

---

### 3.4 Remove Duplicates Preserving Order

#### Theory

`set()` removes duplicates but doesn't preserve order. We need both: uniqueness AND original order.

```python
# Method 1: Set + list
def remove_duplicates(lst):
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

# Method 2: Dict trick (Python 3.7+)
# Dictionaries preserve insertion order, and keys are unique
def remove_duplicates_v2(lst):
    return list(dict.fromkeys(lst))

# How dict.fromkeys works:
# dict.fromkeys([3, 1, 2, 1, 3]) → {3: None, 1: None, 2: None}
# list({3: None, 1: None, 2: None}) → [3, 1, 2]

# Test
print(remove_duplicates([3, 1, 4, 1, 5, 9, 2, 6, 5, 3]))
# [3, 1, 4, 5, 9, 2, 6]
```

---

### 3.5 Reverse Words in a String

#### Theory

Reverse the order of words, not the characters within words.

```
"hello world python" → "python world hello"
"  the  sky is   blue  " → "blue is sky the"
```

```python
# Method 1: Simple split and reverse
def reverse_words(s):
    return " ".join(s.split()[::-1])

# How this works:
# "hello world python"
# .split() → ["hello", "world", "python"]   (splits on whitespace)
# [::-1]   → ["python", "world", "hello"]   (reverses list)
# " ".join → "python world hello"            (joins with space)

# split() without arguments splits on ANY whitespace and removes empties:
"  hello   world  ".split()      # ["hello", "world"]
"  hello   world  ".split(" ")   # ['', '', 'hello', '', '', 'world', '', '']
# Always use split() without args for word splitting!

# Method 2: Manual approach (if interviewer says no split/join)
def reverse_words_manual(s):
    words = []
    current_word = ""
    for char in s:
        if char == " ":
            if current_word:
                words.append(current_word)
                current_word = ""
        else:
            current_word += char
    if current_word:
        words.append(current_word)
    
    # Reverse the words list
    left, right = 0, len(words) - 1
    while left < right:
        words[left], words[right] = words[right], words[left]
        left += 1
        right -= 1
    
    return " ".join(words)
```

---

### 3.6 Find the Missing Number

#### Theory

Given a list containing n distinct numbers from 0 to n, find the one that's missing.

Example: `[0, 1, 3, 4]` → missing is 2. The list has 4 elements, so n=4, and numbers should be 0,1,2,3,4.

**Mathematical approach:** The sum of 0 to n is `n*(n+1)/2`. Subtract actual sum to find missing.

```python
def find_missing(nums):
    n = len(nums)
    expected_sum = n * (n + 1) // 2
    actual_sum = sum(nums)
    return expected_sum - actual_sum

# Why n = len(nums)?
# If we have numbers 0 to n with one missing, the list has n elements.
# Example: [0, 1, 3, 4] has 4 elements, n=4, expected: 0+1+2+3+4=10
# Actual: 0+1+3+4=8. Missing: 10-8=2 ✓

# XOR approach (bit manipulation) — O(1) space, no overflow risk
def find_missing_xor(nums):
    xor = 0
    for i in range(len(nums) + 1):
        xor ^= i
    for num in nums:
        xor ^= num
    return xor

# Why XOR works: a ^ a = 0, a ^ 0 = a
# XOR all indices AND all values: every number cancels except the missing one.
```

---

## LEVEL 4 — Advanced Patterns

---

### 4.1 Matrix Operations

#### Theory

A **matrix** is a 2D list (list of lists). Matrices are indexed as `matrix[row][col]`.

```python
matrix = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
]
# matrix[0][0] = 1  (top-left)
# matrix[1][2] = 6  (row 1, col 2)
# matrix[2][1] = 8  (row 2, col 1)
```

#### Transpose

**Transpose** swaps rows and columns: `matrix[i][j]` becomes `matrix[j][i]`.

```python
# Before:          After transpose:
# 1 2 3            1 4 7
# 4 5 6            2 5 8
# 7 8 9            3 6 9

def transpose(matrix):
    n = len(matrix)
    for i in range(n):
        for j in range(i + 1, n):    # j starts at i+1 to avoid double-swapping
            matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]
    return matrix
```

**Why `j` starts at `i + 1`:** If we swap (0,1) and later swap (1,0), we'd undo the first swap. We only need to swap each pair once, so we handle the upper triangle.

#### 90° Clockwise Rotation

**Key formula:** Transpose + Reverse each row = 90° clockwise rotation.

```python
def rotate_90_clockwise(matrix):
    n = len(matrix)
    
    # Step 1: Transpose
    for i in range(n):
        for j in range(i + 1, n):
            matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]
    
    # Step 2: Reverse each row
    for row in matrix:
        row.reverse()
    
    return matrix

# Visual:
# Original:     Transpose:    Reverse rows:
# 1 2 3         1 4 7         7 4 1
# 4 5 6    →    2 5 8    →    8 5 2
# 7 8 9         3 6 9         9 6 3
```

**Other rotations:**

- 90° counter-clockwise: Transpose + Reverse each column
- 180°: Reverse each row, then reverse each column (or just reverse the entire matrix)

---

### 4.2 Sliding Window

#### Theory

The **sliding window** pattern is used when you need to find/calculate something among contiguous subarrays or substrings of a fixed size.

**Core idea:** Instead of recalculating from scratch for each window, "slide" the window by removing the element leaving the window and adding the element entering it.

```
Array: [1, 3, 5, 2, 8, 1, 4]
Window size k=3

Window 1: [1, 3, 5]       sum = 9
Window 2:    [3, 5, 2]     sum = 10  (= 9 - 1 + 2)
Window 3:       [5, 2, 8]  sum = 15  (= 10 - 3 + 8)
Window 4:          [2, 8, 1] sum = 11 (= 15 - 5 + 1)
Window 5:             [8, 1, 4] sum = 13 (= 11 - 2 + 4)
```

```python
def max_sum_subarray(arr, k):
    if len(arr) < k:
        return None
    
    # Calculate sum of first window
    window_sum = sum(arr[:k])
    max_sum = window_sum
    
    # Slide the window
    for i in range(k, len(arr)):
        window_sum += arr[i]       # add new element entering window
        window_sum -= arr[i - k]   # remove element leaving window
        max_sum = max(max_sum, window_sum)
    
    return max_sum

# Time: O(n) — single pass
# Without sliding window: O(n*k) — recalculate sum for each window

# Test
print(max_sum_subarray([1, 3, 5, 2, 8, 1, 4], 3))  # 15 (subarray [5,2,8])
```

**When to use sliding window:**

- "Find max/min/average of subarray of size k"
- "Find longest substring with at most k distinct characters"
- "Find smallest subarray with sum ≥ target"

---

### 4.3 Generators

#### Theory

A **generator** is a function that produces values one at a time, using `yield` instead of `return`. It's like a lazy iterator — it doesn't compute all values upfront, but generates them on demand.

**Why generators matter:**

1. **Memory efficient** — don't store entire sequence in memory
2. **Can represent infinite sequences** — you can't have an infinite list
3. **Pipeline-friendly** — chain generators for data processing

```python
# Regular function — computes ALL values, stores in list
def get_squares_list(n):
    result = []
    for i in range(n):
        result.append(i ** 2)
    return result
# For n=1,000,000 this creates a list of 1M items in memory

# Generator — computes one value at a time
def get_squares_gen(n):
    for i in range(n):
        yield i ** 2
# For n=1,000,000 this uses almost no memory
```

**How `yield` works:**

When Python hits `yield`, it:

1. Returns the value
2. **Pauses** the function's state (all local variables preserved)
3. On next call to `next()`, **resumes** from where it paused

```python
def count_up_to(n):
    i = 1
    while i <= n:
        yield i
        i += 1

gen = count_up_to(5)
print(next(gen))    # 1 (function runs until first yield, pauses)
print(next(gen))    # 2 (resumes, runs until next yield, pauses)
print(next(gen))    # 3
print(next(gen))    # 4
print(next(gen))    # 5
# print(next(gen))  # StopIteration! Generator is exhausted

# Most common: use in a for loop
for num in count_up_to(5):
    print(num)    # 1, 2, 3, 4, 5
```

#### Infinite Fibonacci Generator

```python
def fibonacci_gen():
    a, b = 0, 1
    while True:         # Infinite loop — but that's fine for generators
        yield a
        a, b = b, a + b

# Get first 10 Fibonacci numbers
gen = fibonacci_gen()
first_10 = [next(gen) for _ in range(10)]
print(first_10)    # [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]

# You can keep going:
next_5 = [next(gen) for _ in range(5)]
print(next_5)      # [55, 89, 144, 233, 377]
```

#### Generator Expressions

Like list comprehensions, but with parentheses instead of brackets:

```python
# List comprehension — creates entire list in memory
squares_list = [x**2 for x in range(1000000)]

# Generator expression — creates values on demand
squares_gen = (x**2 for x in range(1000000))

# Use generator when you only need to iterate once
total = sum(x**2 for x in range(1000000))    # No extra [] needed inside sum()
```

---

### 4.4 Decorators

#### Theory

A **decorator** is a function that takes another function and extends its behavior without modifying it. It's a powerful pattern for adding cross-cutting concerns like logging, timing, caching, authentication.

**Understanding the building blocks:**

```python
# Step 1: Functions are objects in Python
def greet():
    return "Hello!"

# You can assign functions to variables
say_hi = greet
print(say_hi())    # "Hello!"

# Step 2: Functions can take other functions as arguments
def call_twice(func):
    func()
    func()

def say_hello():
    print("Hello!")

call_twice(say_hello)
# Hello!
# Hello!

# Step 3: Functions can return functions
def create_greeter(name):
    def greeter():
        return f"Hello, {name}!"
    return greeter

greet_alice = create_greeter("Alice")
print(greet_alice())    # "Hello, Alice!"
```

**Now, decorators:**

```python
# A decorator wraps a function with additional behavior
def timer(func):
    import time
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)      # Call the original function
        elapsed = time.time() - start
        print(f"{func.__name__} took {elapsed:.4f}s")
        return result
    return wrapper

# Using the decorator
@timer
def slow_function():
    import time
    time.sleep(1)
    return "done"

result = slow_function()
# Output: slow_function took 1.0012s

# @timer is syntactic sugar for:
# slow_function = timer(slow_function)
```

**`*args` and `**kwargs` explained:**

```python
# *args captures positional arguments as a tuple
def func(*args):
    print(args)

func(1, 2, 3)        # (1, 2, 3)

# **kwargs captures keyword arguments as a dictionary
def func(**kwargs):
    print(kwargs)

func(a=1, b=2)       # {'a': 1, 'b': 2}

# Together, they accept ANY combination of arguments
def func(*args, **kwargs):
    print(f"args: {args}, kwargs: {kwargs}")

func(1, 2, name="Alice")
# args: (1, 2), kwargs: {'name': 'Alice'}
```

#### Practical Decorators

```python
# Logging decorator
def log_calls(func):
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        print(f"{func.__name__} returned {result}")
        return result
    return wrapper

@log_calls
def add(a, b):
    return a + b

add(3, 5)
# Calling add with args=(3, 5), kwargs={}
# add returned 8

# Retry decorator
def retry(max_attempts=3):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    print(f"Attempt {attempt+1} failed: {e}")
        return wrapper
    return decorator

@retry(max_attempts=3)
def unreliable_api_call():
    import random
    if random.random() < 0.7:
        raise ConnectionError("Network failed")
    return "Success!"
```

---

### 4.5 List Comprehension Mastery

#### Theory

List comprehensions are a concise way to create lists. They're not just syntactic sugar — they're actually **faster** than equivalent for loops because Python optimizes them internally.

**Basic syntax:** `[expression for item in iterable if condition]`

```python
# Standard loop vs comprehension
# Loop:
squares = []
for x in range(10):
    squares.append(x ** 2)

# Comprehension:
squares = [x ** 2 for x in range(10)]
# [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
```

#### Filtering

```python
# Only even squares
even_squares = [x**2 for x in range(20) if x % 2 == 0]
# [0, 4, 16, 36, 64, 100, 144, 196, 256, 324]

# Filter strings
words = ["hello", "Hi", "hey", "world", "HELP"]
h_words = [w for w in words if w.lower().startswith("h")]
# ["hello", "Hi", "hey", "HELP"]
```

#### Nested Comprehensions

```python
# Flatten a 2D list
matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
flat = [x for row in matrix for x in row]
# [1, 2, 3, 4, 5, 6, 7, 8, 9]

# Reading order: for row in matrix → for x in row → x
# Equivalent loop:
flat = []
for row in matrix:
    for x in row:
        flat.append(x)

# Multiplication table
table = [[i * j for j in range(1, 6)] for i in range(1, 6)]
# [[1, 2, 3, 4, 5],
#  [2, 4, 6, 8, 10],
#  [3, 6, 9, 12, 15],
#  [4, 8, 12, 16, 20],
#  [5, 10, 15, 20, 25]]
```

#### Dict and Set Comprehensions

```python
# Dict comprehension
word_lengths = {word: len(word) for word in ["hello", "world", "python"]}
# {'hello': 5, 'world': 5, 'python': 6}

# Invert a dictionary (swap keys and values)
original = {"a": 1, "b": 2, "c": 3}
inverted = {v: k for k, v in original.items()}
# {1: 'a', 2: 'b', 3: 'c'}

# Set comprehension
unique_lengths = {len(word) for word in ["cat", "dog", "fish", "bird"]}
# {3, 4}
```

#### If-Else in Comprehensions

```python
# if-else goes BEFORE 'for' (it's part of the expression)
labels = ["even" if x % 2 == 0 else "odd" for x in range(6)]
# ['even', 'odd', 'even', 'odd', 'even', 'odd']

# Filter (if only) goes AFTER 'for'
evens = [x for x in range(10) if x % 2 == 0]
# [0, 2, 4, 6, 8]
```

---

### 4.6 Recursion to Iteration Conversion

#### Theory

Any recursive function can be converted to iterative using an explicit **stack**. This is important because: (a) Python has a recursion limit, (b) iterative solutions use less memory (no call stack overhead), (c) interviewers love seeing you convert between the two.

**The pattern:**

1. Replace function calls with pushing to a stack
2. Replace the recursive base case with the loop's termination condition
3. Process items by popping from the stack

```python
# Recursive sum of nested list
def sum_nested_rec(lst):
    total = 0
    for item in lst:
        if isinstance(item, list):
            total += sum_nested_rec(item)     # recursive call
        else:
            total += item
    return total

# Iterative equivalent using a stack
def sum_nested_iter(lst):
    stack = list(lst)      # initialize stack with all items
    total = 0
    while stack:
        item = stack.pop()
        if isinstance(item, list):
            stack.extend(item)     # push sub-items onto stack
        else:
            total += item
    return total

# Test
nested = [1, [2, [3, 4]], [5, [6]]]
print(sum_nested_rec(nested))     # 21
print(sum_nested_iter(nested))    # 21
```

**Why does the stack work?** In recursion, the system call stack stores intermediate states. When we use our own stack, we're doing the same thing explicitly.

---

### 4.7 Caching / Memoization

#### Theory

**Memoization** stores the results of expensive function calls and returns the cached result when the same inputs occur again. It trades space (memory for cache) for time (avoid re-computation).

**When to use:** When a function is pure (same inputs always give same outputs) and called repeatedly with the same arguments.

```python
# Build your own memoization decorator
def memoize(func):
    cache = {}
    
    def wrapper(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]
    
    return wrapper

@memoize
def expensive_function(n):
    """Simulate expensive computation."""
    print(f"Computing for {n}...")
    result = 0
    for i in range(n):
        result += i ** 2
    return result

# First call: actually computes
print(expensive_function(1000))    # "Computing for 1000..." then result

# Second call: returns cached result (no "Computing..." message)
print(expensive_function(1000))    # Just the result, no computation

# How cache looks internally:
# {(1000,): 332833500}
```

**Python's built-in: `@lru_cache`**

```python
from functools import lru_cache

@lru_cache(maxsize=128)      # Cache last 128 unique inputs
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)

# maxsize=None → unlimited cache
# maxsize=128 → evicts least recently used when full (LRU = Least Recently Used)

# Check cache stats
print(fib.cache_info())
# CacheInfo(hits=8, misses=11, maxsize=128, currsize=11)

# Clear cache
fib.cache_clear()
```

---

## LEVEL 5 — Tricky Interview Favorites

---

### 5.1 Roman Numeral to Integer

#### Theory

Roman numerals use these symbols:

| Symbol | Value |
|--------|-------|
| I | 1 |
| V | 5 |
| X | 10 |
| L | 50 |
| C | 100 |
| D | 500 |
| M | 1000 |

**Rule:** Normally, symbols are added left to right. But when a smaller value appears BEFORE a larger value, you SUBTRACT the smaller.

- `VI` = 5 + 1 = 6
- `IV` = 5 - 1 = 4
- `IX` = 10 - 1 = 9
- `XL` = 50 - 10 = 40
- `MCMXCIV` = 1000 + (1000-100) + (100-10) + (5-1) = 1994

```python
def roman_to_int(s):
    values = {
        'I': 1, 'V': 5, 'X': 10, 'L': 50,
        'C': 100, 'D': 500, 'M': 1000
    }
    
    total = 0
    for i in range(len(s)):
        # If current value is less than next value, subtract
        if i + 1 < len(s) and values[s[i]] < values[s[i + 1]]:
            total -= values[s[i]]
        else:
            total += values[s[i]]
    
    return total

# Trace for "MCMXCIV" (1994):
# M(1000): next is C(100), 1000 > 100   → +1000 = 1000
# C(100):  next is M(1000), 100 < 1000  → -100  = 900
# M(1000): next is X(10),  1000 > 10    → +1000 = 1900
# X(10):   next is C(100), 10 < 100     → -10   = 1890
# C(100):  next is I(1),   100 > 1      → +100  = 1990
# I(1):    next is V(5),   1 < 5        → -1    = 1989
# V(5):    no next                       → +5    = 1994

# Test
print(roman_to_int("III"))       # 3
print(roman_to_int("LVIII"))     # 58
print(roman_to_int("MCMXCIV"))   # 1994
```

---

### 5.2 Valid Parentheses

#### Theory

Given a string containing just `()`, `{}`, `[]`, determine if the input is valid. A string is valid if:

1. Every opening bracket has a matching closing bracket of the same type
2. Brackets are closed in the correct order (no interleaving)

Valid: `"()"`, `"()[]{}"`, `"({[]})"`, `"([{}])"` 
Invalid: `"(]"`, `"({)}"`, `"((("`, `")"`

**This is a classic stack problem.** The key insight: the most recently opened bracket must be closed first (LIFO — Last In, First Out).

```python
def is_valid_parentheses(s):
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}
    
    for char in s:
        if char in mapping:
            # It's a closing bracket
            if not stack or stack[-1] != mapping[char]:
                return False
            stack.pop()
        else:
            # It's an opening bracket
            stack.append(char)
    
    return len(stack) == 0    # Stack should be empty if all matched

# Trace for "({[]})":
# char='(' → opening → stack=['(']
# char='{' → opening → stack=['(', '{']
# char='[' → opening → stack=['(', '{', '[']
# char=']' → closing → mapping[']']='[' → stack[-1]='[' → match! pop → ['(', '{']
# char='}' → closing → mapping['}']='[' → stack[-1]='{' → match! pop → ['(']
# char=')' → closing → mapping[')']='(' → stack[-1]='(' → match! pop → []
# Stack empty → True ✓

# Trace for "({)}":
# char='(' → opening → stack=['(']
# char='{' → opening → stack=['(', '{']
# char=')' → closing → mapping[')']='(' → stack[-1]='{' → NO match → False ✗
```

**Why a stack?** Brackets must nest properly. The most recently opened bracket must close first. This is exactly LIFO behavior, which is what a stack provides.

---

### 5.3 Group Anagrams

#### Theory

Given a list of strings, group the ones that are anagrams of each other.

Input: `["eat", "tea", "tan", "ate", "nat", "bat"]`
Output: `[["eat", "tea", "ate"], ["tan", "nat"], ["bat"]]`

**Key insight:** All anagrams, when sorted, produce the same key. "eat" sorted = "aet", "tea" sorted = "aet", "ate" sorted = "aet". So we can use the sorted version as a dictionary key.

```python
from collections import defaultdict

def group_anagrams(words):
    groups = defaultdict(list)
    
    for word in words:
        # sorted("eat") → ['a', 'e', 't']
        # tuple(['a', 'e', 't']) → ('a', 'e', 't')  — tuples can be dict keys
        key = tuple(sorted(word))
        groups[key].append(word)
    
    return list(groups.values())

# Walkthrough:
# "eat" → key=('a','e','t') → groups = {('a','e','t'): ["eat"]}
# "tea" → key=('a','e','t') → groups = {('a','e','t'): ["eat", "tea"]}
# "tan" → key=('a','n','t') → groups = {('a','e','t'): ["eat", "tea"],
#                                         ('a','n','t'): ["tan"]}
# "ate" → key=('a','e','t') → groups = {('a','e','t'): ["eat", "tea", "ate"],
#                                         ('a','n','t'): ["tan"]}
# "nat" → key=('a','n','t') → groups = {('a','e','t'): ["eat", "tea", "ate"],
#                                         ('a','n','t'): ["tan", "nat"]}
# "bat" → key=('a','b','t') → adds new group

# Result: [["eat", "tea", "ate"], ["tan", "nat"], ["bat"]]
```

**`defaultdict` explained:**

```python
from collections import defaultdict

# Regular dict — raises KeyError for missing keys
d = {}
d["missing"]           # KeyError!
d["key"].append(1)     # KeyError!

# defaultdict — auto-creates missing keys with a default value
d = defaultdict(list)     # missing keys get empty list []
d["key"].append(1)        # Works! d = {"key": [1]}

d = defaultdict(int)      # missing keys get 0
d["count"] += 1           # Works! d = {"count": 1}

d = defaultdict(set)      # missing keys get empty set
d["group"].add("item")    # Works! d = {"group": {"item"}}
```

---

### 5.4 Longest Common Prefix

#### Theory

Find the longest common prefix string among an array of strings.

Input: `["flower", "flow", "flight"]` → Output: `"fl"`
Input: `["dog", "racecar", "car"]` → Output: `""` (no common prefix)

**Approach:** Start with the first string as the prefix. Compare it with each subsequent string, shortening the prefix until it matches.

```python
def longest_common_prefix(strs):
    if not strs:
        return ""
    
    prefix = strs[0]
    
    for s in strs[1:]:
        while not s.startswith(prefix):
            prefix = prefix[:-1]      # Shorten prefix by one character
            if not prefix:
                return ""
    
    return prefix

# Trace for ["flower", "flow", "flight"]:
# prefix = "flower"
# s = "flow":
#   "flow".startswith("flower")? No → prefix = "flowe"
#   "flow".startswith("flowe")?  No → prefix = "flow"
#   "flow".startswith("flow")?   Yes → continue
# s = "flight":
#   "flight".startswith("flow")? No → prefix = "flo"
#   "flight".startswith("flo")?  No → prefix = "fl"
#   "flight".startswith("fl")?   Yes → continue
# Return "fl"
```

#### Alternative: Vertical scanning

```python
def longest_common_prefix_v2(strs):
    if not strs:
        return ""
    
    for i in range(len(strs[0])):
        char = strs[0][i]
        for s in strs[1:]:
            if i >= len(s) or s[i] != char:
                return strs[0][:i]
    
    return strs[0]

# This checks character by character across all strings simultaneously
# More efficient when strings have very different lengths
```

---

### 5.5 Power Set (All Subsets)

#### Theory

The **power set** of a set is the set of all possible subsets, including the empty set and the set itself.

Power set of `[1, 2, 3]`:
`[[], [1], [2], [3], [1,2], [1,3], [2,3], [1,2,3]]`

A set with n elements has 2^n subsets. Why? For each element, you have 2 choices: include it or don't.

```python
# Recursive approach
def power_set(lst):
    if not lst:
        return [[]]           # Base case: empty set has one subset (itself)
    
    first = lst[0]
    rest_subsets = power_set(lst[1:])   # Get all subsets WITHOUT first element
    
    # Each subset either includes first or doesn't
    with_first = [[first] + subset for subset in rest_subsets]
    
    return rest_subsets + with_first

# Trace for power_set([1, 2]):
# power_set([1, 2])
#   first = 1
#   rest_subsets = power_set([2])
#     first = 2
#     rest_subsets = power_set([])
#       return [[]]
#     with_first = [[2]]
#     return [[], [2]]
#   with_first = [[1], [1, 2]]
#   return [[], [2], [1], [1, 2]]

# Iterative approach
def power_set_iter(lst):
    result = [[]]
    for item in lst:
        # For each existing subset, create a new one that includes this item
        result += [subset + [item] for subset in result]
    return result

# Trace for [1, 2, 3]:
# Start: [[]]
# item=1: result += [[1]]           → [[], [1]]
# item=2: result += [[2], [1,2]]    → [[], [1], [2], [1,2]]
# item=3: result += [[3],[1,3],[2,3],[1,2,3]] → all 8 subsets
```

---

### 5.6 Merge Two Sorted Lists

#### Theory

Given two lists that are already sorted, merge them into a single sorted list. This is a fundamental operation used in merge sort.

**Two-pointer approach:** Compare elements from both lists, always taking the smaller one.

```python
def merge_sorted(l1, l2):
    result = []
    i = j = 0     # Two pointers
    
    # Compare and take the smaller element
    while i < len(l1) and j < len(l2):
        if l1[i] <= l2[j]:
            result.append(l1[i])
            i += 1
        else:
            result.append(l2[j])
            j += 1
    
    # One list might have remaining elements
    result.extend(l1[i:])
    result.extend(l2[j:])
    
    return result

# Trace for merge_sorted([1, 3, 5], [2, 4, 6]):
# i=0,j=0: l1[0]=1 vs l2[0]=2 → take 1 → i=1      result=[1]
# i=1,j=0: l1[1]=3 vs l2[0]=2 → take 2 → j=1      result=[1,2]
# i=1,j=1: l1[1]=3 vs l2[1]=4 → take 3 → i=2      result=[1,2,3]
# i=2,j=1: l1[2]=5 vs l2[1]=4 → take 4 → j=2      result=[1,2,3,4]
# i=2,j=2: l1[2]=5 vs l2[2]=6 → take 5 → i=3      result=[1,2,3,4,5]
# i=3: loop ends (i >= len(l1))
# extend with l2[2:] = [6]                           result=[1,2,3,4,5,6]

# Test
print(merge_sorted([1, 3, 5, 7], [2, 4, 6, 8]))
# [1, 2, 3, 4, 5, 6, 7, 8]

# Time: O(n + m), Space: O(n + m)
```

---

## Quick Reference: Python Tricks for Interviews

### Variable Swapping

```python
a, b = b, a                  # Swap two variables
a, b, c = c, a, b            # Rotate three variables
```

### String Tricks

```python
s[::-1]                       # Reverse a string
s.strip()                     # Remove whitespace from both ends
s.lstrip("0")                 # Remove leading zeros
"".join(sorted(s))            # Sort characters in a string
s.count("a")                  # Count occurrences of 'a'
s.replace("old", "new")       # Replace all occurrences
s.startswith("prefix")        # Check prefix
s.endswith("suffix")          # Check suffix
s.isdigit()                   # Check if all digits
s.isalpha()                   # Check if all letters
s.isalnum()                   # Check if all letters or digits
```

### List Tricks

```python
if not lst:                   # Check if list is empty
first, *rest = [1, 2, 3, 4]  # first=1, rest=[2,3,4]
*start, last = [1, 2, 3, 4]  # start=[1,2,3], last=4
lst[-1]                       # Last element
lst[-2:]                      # Last two elements
```

### Iteration Tricks

```python
for i, val in enumerate(lst):        # Index + value
for a, b in zip(list1, list2):       # Parallel iteration
for key, val in d.items():           # Dict iteration
for i in range(len(lst)-1, -1, -1):  # Reverse iteration by index
```

### Sorting Tricks

```python
sorted(lst)                          # Returns new sorted list
lst.sort()                           # Sorts in place
sorted(lst, reverse=True)            # Descending
sorted(lst, key=lambda x: x[1])      # Sort by second element
sorted(lst, key=len)                 # Sort by length
sorted(lst, key=str.lower)           # Case-insensitive sort
```

### Useful Built-ins

```python
any(x > 5 for x in lst)    # True if ANY element satisfies condition
all(x > 0 for x in lst)    # True if ALL elements satisfy condition
min(lst)                    # Minimum value
max(lst, key=len)           # Maximum by custom key
sum(lst)                    # Sum of elements
abs(-5)                     # Absolute value → 5
divmod(17, 5)               # (3, 2) → quotient and remainder
```

### F-String Formatting

```python
x = 3.14159
f"{x:.2f}"        # "3.14"      — 2 decimal places
f"{x:10.2f}"      # "      3.14" — right-aligned, width 10
f"{42:05d}"       # "00042"     — zero-padded
f"{1000000:,}"    # "1,000,000" — comma separator
f"{'hi':>10}"     # "        hi" — right-aligned
f"{'hi':<10}"     # "hi        " — left-aligned
f"{'hi':^10}"     # "    hi    " — centered
```

### Ternary Expression

```python
x = "yes" if condition else "no"

# Chained ternary (use sparingly)
grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "F"
```

### Walrus Operator `:=` (Python 3.8+)

Assigns AND returns a value in one expression:

```python
# Without walrus:
n = len(data)
if n > 10:
    print(f"Too long: {n}")

# With walrus:
if (n := len(data)) > 10:
    print(f"Too long: {n}")

# Useful in while loops:
while (line := input("Enter text: ")) != "quit":
    print(f"You said: {line}")
```

---

## Practice Problems Checklist

Use this to track your progress:

### Basic (Level 1-2)
1. Check if string is palindrome (ignore spaces and case)
2. Return nth Fibonacci number (iterative)
3. Find factorial of a number
4. Reverse a string without slicing
5. Count vowels in a string

### Intermediate (Level 3)
6. Find all duplicates in a list
7. Two Sum — return indices
8. Check if two strings are anagrams
9. FizzBuzz for 1 to 100
10. String compression
11. Find missing number in 0 to n
12. Remove duplicates preserving order
13. Check if number is prime
14. Flatten a nested list
15. Reverse words in a sentence

### Advanced (Level 4-5)
16. Check if parentheses are balanced
17. Group words by anagrams
18. Find longest common prefix
19. Roman numeral to integer
20. Infinite Fibonacci generator
21. Memoization decorator
22. Max sum subarray of size k (sliding window)
23. Rotate matrix 90° clockwise
24. Generate power set
25. Merge two sorted lists

---

*Every concept above can be understood by reading the theory and tracing through the examples step by step. When you practice, don't just read — trace each example on paper, then try writing the solution from memory.*