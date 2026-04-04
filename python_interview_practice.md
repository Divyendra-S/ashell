# Python Interview Coding Practice — Basic to Advanced

---

## How to Approach Any Coding Problem

1. **Understand the problem** — Read it twice. Identify input, output, and edge cases.
2. **Think of examples** — Walk through 2-3 examples by hand.
3. **Identify the pattern** — Is it string manipulation? Math? Iteration? Recursion?
4. **Write pseudocode** — Plan before you code.
5. **Code it** — Keep it clean and readable.
6. **Test it** — Run through your examples mentally. Check edge cases.

---

## LEVEL 1 — Basics (Strings, Numbers, Loops)

### Concept: String Reversal & Palindrome

A **palindrome** reads the same forwards and backwards. E.g., `"madam"`, `"racecar"`.

**Approach:**
- Reverse the string and compare with original.
- Python gives you slicing: `s[::-1]` reverses a string.
- For case-insensitive check: convert to lowercase first, strip non-alphanumeric chars.

```python
# Quick way
def is_palindrome(s):
    s = s.lower()
    return s == s[::-1]

# Without slicing (using loop)
def is_palindrome_loop(s):
    s = s.lower()
    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    return True
```

**Key idea:** Two-pointer technique — compare from both ends moving inward.

---

### Concept: Fibonacci Series

Each number is the sum of the two before it: `0, 1, 1, 2, 3, 5, 8, 13, ...`

**Approaches:**
1. **Iterative** (best for interviews — O(n) time, O(1) space)
2. **Recursive** (simple but slow — O(2^n) without memoization)
3. **Recursive + Memoization** (O(n) time, O(n) space)

```python
# Iterative
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

# Recursive (slow)
def fib_recursive(n):
    if n <= 1:
        return n
    return fib_recursive(n - 1) + fib_recursive(n - 2)

# With memoization
from functools import lru_cache

@lru_cache(maxsize=None)
def fib_memo(n):
    if n <= 1:
        return n
    return fib_memo(n - 1) + fib_memo(n - 2)
```

**Key idea:** Swap variables technique (`a, b = b, a + b`) — very Pythonic and commonly asked.

---

### Concept: Factorial

Product of all positive integers up to n: `5! = 5 * 4 * 3 * 2 * 1 = 120`

```python
# Iterative
def factorial(n):
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result

# Recursive
def factorial_rec(n):
    if n <= 1:
        return 1
    return n * factorial_rec(n - 1)
```

---

## LEVEL 2 — Common Patterns (Lists, Dicts, Sets)

### Concept: Finding Duplicates

**Approach:** Use a `set` — sets only store unique values.

```python
def find_duplicates(lst):
    seen = set()
    duplicates = set()
    for item in lst:
        if item in seen:
            duplicates.add(item)
        seen.add(item)
    return list(duplicates)
```

**Key idea:** `set` lookups are O(1). Always think of sets when you need fast membership checks.

---

### Concept: Counting Frequency (Character/Word Count)

**Approach:** Use a dictionary or `collections.Counter`.

```python
from collections import Counter

def char_frequency(s):
    return dict(Counter(s))

# Manual way
def char_frequency_manual(s):
    freq = {}
    for char in s:
        freq[char] = freq.get(char, 0) + 1
    return freq
```

**Key idea:** `dict.get(key, default)` avoids KeyError. `Counter` is your best friend for frequency problems.

---

### Concept: Two Sum (Find Pair with Target Sum)

Given a list and a target, find two numbers that add up to the target.

**Approach:** Use a dictionary to store complements.

```python
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []
```

**Key idea:** Instead of brute force O(n^2), use a hash map for O(n). This pattern appears everywhere.

---

### Concept: Anagram Check

Two strings are anagrams if they have the same characters in different order.

```python
def is_anagram(s1, s2):
    return Counter(s1.lower()) == Counter(s2.lower())

# Without Counter
def is_anagram_sort(s1, s2):
    return sorted(s1.lower()) == sorted(s2.lower())
```

---

### Concept: List Flattening

Flatten a nested list like `[1, [2, [3, 4]], 5]` into `[1, 2, 3, 4, 5]`.

```python
def flatten(lst):
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result
```

**Key idea:** Recursion is natural when data is nested. Check `isinstance` to decide whether to recurse.

---

## LEVEL 3 — Intermediate (String Manipulation, Math, Logic)

### Concept: Prime Numbers

A prime number is only divisible by 1 and itself. Check up to sqrt(n).

```python
import math

def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(math.sqrt(n)) + 1):
        if n % i == 0:
            return False
    return True

# Generate primes up to n (Sieve of Eratosthenes)
def sieve(n):
    primes = [True] * (n + 1)
    primes[0] = primes[1] = False
    for i in range(2, int(math.sqrt(n)) + 1):
        if primes[i]:
            for j in range(i * i, n + 1, i):
                primes[j] = False
    return [i for i, is_p in enumerate(primes) if is_p]
```

**Key idea:** Only check up to sqrt(n) — if n has a factor larger than sqrt(n), it must also have one smaller.

---

### Concept: String Compression

`"aaabbc"` → `"a3b2c1"`

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
    result.append(f"{s[-1]}{count}")
    return "".join(result)
```

**Key idea:** Track current char and count. When char changes, flush to result. Don't forget the last group.

---

### Concept: FizzBuzz (Classic)

```python
def fizzbuzz(n):
    for i in range(1, n + 1):
        if i % 15 == 0:
            print("FizzBuzz")
        elif i % 3 == 0:
            print("Fizz")
        elif i % 5 == 0:
            print("Buzz")
        else:
            print(i)
```

**Key idea:** Check the most specific condition first (divisible by both 3 AND 5).

---

### Concept: Remove Duplicates While Preserving Order

```python
def remove_duplicates(lst):
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

# One-liner (Python 3.7+ dicts preserve order)
def remove_duplicates_v2(lst):
    return list(dict.fromkeys(lst))
```

---

### Concept: Reverse Words in a String

`"hello world python"` → `"python world hello"`

```python
def reverse_words(s):
    return " ".join(s.split()[::-1])
```

---

### Concept: Find Missing Number

Given list `[0, 1, 3, 4]` — find the missing number (2).

```python
def find_missing(nums):
    n = len(nums)
    expected_sum = n * (n + 1) // 2
    return expected_sum - sum(nums)
```

**Key idea:** Math formula `n*(n+1)/2` gives total sum. Subtract actual sum to find missing.

---

## LEVEL 4 — Advanced Patterns

### Concept: Matrix Operations

Rotate a matrix 90 degrees clockwise:

```python
def rotate_matrix(matrix):
    n = len(matrix)
    # Transpose
    for i in range(n):
        for j in range(i, n):
            matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]
    # Reverse each row
    for row in matrix:
        row.reverse()
    return matrix
```

**Key idea:** Transpose + Reverse rows = 90-degree clockwise rotation.

---

### Concept: Sliding Window (Max Sum of Subarray of Size K)

```python
def max_sum_subarray(arr, k):
    window_sum = sum(arr[:k])
    max_sum = window_sum
    for i in range(k, len(arr)):
        window_sum += arr[i] - arr[i - k]
        max_sum = max(max_sum, window_sum)
    return max_sum
```

**Key idea:** Instead of recalculating sum each time, slide the window — add new element, remove old one.

---

### Concept: Generators (Pythonic & Interview Favorite)

```python
def fibonacci_gen():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

# Usage
gen = fibonacci_gen()
first_10 = [next(gen) for _ in range(10)]
```

**Key idea:** `yield` makes a function a generator — it produces values lazily, one at a time.

---

### Concept: Decorators

```python
import time

def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        print(f"{func.__name__} took {time.time() - start:.4f}s")
        return result
    return wrapper

@timer
def slow_function():
    time.sleep(1)
```

**Key idea:** A decorator is a function that wraps another function. `@decorator` is syntactic sugar.

---

### Concept: List Comprehension Mastery

```python
# Flatten 2D list
flat = [x for row in matrix for x in row]

# Filter and transform
evens_squared = [x**2 for x in range(20) if x % 2 == 0]

# Dict comprehension
word_lengths = {word: len(word) for word in ["hello", "world"]}

# Nested comprehension
multiplication_table = [[i * j for j in range(1, 11)] for i in range(1, 11)]
```

---

### Concept: Recursion to Iteration Conversion

Many recursive problems can be converted to iterative using a stack:

```python
# Recursive
def sum_nested(lst):
    total = 0
    for item in lst:
        if isinstance(item, list):
            total += sum_nested(item)
        else:
            total += item
    return total

# Iterative with stack
def sum_nested_iter(lst):
    stack = list(lst)
    total = 0
    while stack:
        item = stack.pop()
        if isinstance(item, list):
            stack.extend(item)
        else:
            total += item
    return total
```

---

### Concept: Caching / Memoization

```python
# Manual memoization
def memoize(func):
    cache = {}
    def wrapper(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]
    return wrapper

@memoize
def expensive_calc(n):
    # some expensive computation
    return n ** n
```

---

## LEVEL 5 — Tricky Interview Favorites

### Concept: Roman to Integer / Integer to Roman

```python
def roman_to_int(s):
    values = {'I': 1, 'V': 5, 'X': 10, 'L': 50,
              'C': 100, 'D': 500, 'M': 1000}
    total = 0
    for i in range(len(s)):
        if i + 1 < len(s) and values[s[i]] < values[s[i + 1]]:
            total -= values[s[i]]
        else:
            total += values[s[i]]
    return total
```

**Key idea:** If a smaller value appears before a larger one, subtract it. Otherwise add.

---

### Concept: Valid Parentheses

Check if brackets are balanced: `"({[]})"` → True, `"({)}"` → False

```python
def is_valid(s):
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}
    for char in s:
        if char in mapping:
            if not stack or stack[-1] != mapping[char]:
                return False
            stack.pop()
        else:
            stack.append(char)
    return len(stack) == 0
```

**Key idea:** Use a stack. Push opening brackets. When closing bracket arrives, check if top of stack matches.

---

### Concept: Group Anagrams

```python
from collections import defaultdict

def group_anagrams(words):
    groups = defaultdict(list)
    for word in words:
        key = tuple(sorted(word))
        groups[key].append(word)
    return list(groups.values())
```

---

### Concept: Longest Common Prefix

```python
def longest_common_prefix(strs):
    if not strs:
        return ""
    prefix = strs[0]
    for s in strs[1:]:
        while not s.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ""
    return prefix
```

---

### Concept: Power Set (All Subsets)

```python
def power_set(lst):
    if not lst:
        return [[]]
    rest = power_set(lst[1:])
    return rest + [[lst[0]] + subset for subset in rest]
```

---

### Concept: Merge Two Sorted Lists

```python
def merge_sorted(l1, l2):
    result = []
    i = j = 0
    while i < len(l1) and j < len(l2):
        if l1[i] <= l2[j]:
            result.append(l1[i])
            i += 1
        else:
            result.append(l2[j])
            j += 1
    result.extend(l1[i:])
    result.extend(l2[j:])
    return result
```

---

## Quick Reference: Python Tricks for Interviews

| Trick | Example |
|---|---|
| Swap variables | `a, b = b, a` |
| Reverse string | `s[::-1]` |
| Check empty | `if not lst:` |
| Enumerate | `for i, val in enumerate(lst):` |
| Zip two lists | `for a, b in zip(l1, l2):` |
| Default dict value | `d.get(key, 0)` |
| Sort by key | `sorted(lst, key=lambda x: x[1])` |
| Any / All | `any(x > 5 for x in lst)` |
| Unpack | `first, *rest = [1,2,3,4]` |
| Walrus operator | `if (n := len(s)) > 10:` |
| f-strings | `f"Value is {x:.2f}"` |
| Ternary | `x = "yes" if condition else "no"` |

---

## Practice Problems

Solve these in order. I'll check your answers when you're ready.

### Basic
1. Write a function to check if a string is a palindrome (ignore spaces and case).
2. Write a function to return the nth Fibonacci number (iterative).
3. Write a function to find the factorial of a number.
4. Write a function to reverse a string without using slicing.
5. Write a function to count vowels in a string.

### Intermediate
6. Write a function to find all duplicates in a list.
7. Write a function that returns the two indices of numbers that add up to a target (Two Sum).
8. Write a function to check if two strings are anagrams.
9. Write FizzBuzz for numbers 1 to 100.
10. Write a function to compress a string (`"aabbcc"` → `"a2b2c2"`).
11. Write a function to find the missing number in a list of 0 to n.
12. Write a function to remove duplicates from a list while keeping order.
13. Write a function to check if a number is prime.
14. Write a function to flatten a nested list.
15. Write a function to reverse words in a sentence.

### Advanced
16. Write a function to check if parentheses are balanced.
17. Write a function to group a list of words by anagrams.
18. Write a function to find the longest common prefix in a list of strings.
19. Write a function to convert a Roman numeral string to an integer.
20. Write a generator that yields Fibonacci numbers infinitely.
21. Write a decorator that caches function results (memoization).
22. Write a function to find the max sum of any contiguous subarray of size k (sliding window).
23. Write a function to rotate a matrix 90 degrees clockwise.
24. Write a function to generate all subsets (power set) of a list.
25. Write a function to merge two sorted lists into one sorted list.

---

**Start with Problem 1 and work your way down. Send me your solution and I'll review it!**
