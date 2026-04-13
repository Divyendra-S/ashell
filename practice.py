
def palindrome_checker(str):
    string = "".join(str.split()).lower()
    start = 0
    last = len(string) - 1
    while start < last:
        if string[start] != string[last]:
            return False
        start += 1
        last -= 1    
    return True

print(palindrome_checker("yooy"))

def fib_list(n):
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return [0]
    if n == 1:
        return [0, 1]

    series = [0, 1]
    a, b = 0, 1 
    for _ in range(2, n + 1):
        a, b = b, a + b
        series.append(b)

    return series

print(fib_list(5))



def factorial(num):
    if num == 1:
        return 1
    
    return num * factorial(num-1)

print(factorial(4))    

def factorial_iterative(num):
    if num < 1:
        print("enter no. greater than 1")
        return
    result = 1
    for i in range(1, num + 1):
        result *= i
    return result    

print(factorial_iterative(4))



def reverse_string(str):
    reversed_str = ""
    for i in str:
        reversed_str = i + reversed_str
    return reversed_str


print(reverse_string("reverse"))


def vowel_counter(str):
    joined_str = "".join(str.split()).lower()
    vowels = ["a", "e", "i", "o", "u"]
    vowel_count = 0
    for i in joined_str:
        if i in vowels:
            vowel_count += 1
    return vowel_count


print(vowel_counter("cooper station"))


def vowel_counter_dict(str):
    joined_str = "".join(str.split()).lower()
    vowels_dict = {"a" : 0, "e" : 0, "i" : 0, "o" : 0, "u" : 0}
    for i, v in vowels_dict.items():
        print(f"{i}:{v}")
    for i in joined_str:
        if i in vowels_dict:
            vowels_dict[i] += 1
    return vowels_dict


print(vowel_counter_dict("cooper station"))



def find_duplicates(lst):
    seen = set()
    duplicate = set()
    for i in lst:
        if i in seen:
            duplicate.add(i)
        seen.add(i)
    return duplicate


print(find_duplicates(["duplicate", "yo", "duplicate", "another", "yo"]))



def two_sum(lst, target):
    seen = {}
    for i, num in enumerate(lst):
        compliment = target - i
        if compliment in seen:
            return [seen[compliment], i]
        seen[num] = i    
    return []




def anagram(str_one, str_two):
    if len(str_one) != len(str_two):
        return False

    freq = {}
    for i in str_one:
        if i in freq:
            freq[i] += 1
        else:            
            freq[i] = 1

    for i in str_two:
        if i in freq:
            freq[i] -= 1
        else:
            return False

    print(freq)
    
    return all([v == 0 for v in freq.values()])



print(anagram("yolo", "loyo"))




def string_compression(str):
    result = []
    count = 0

    for i in range(1, len(str)):
        if str[i] == str[i-1]:
            count += 1
        else:
            result.append(f"{str[i-1]}{count}")
            count = 1
    
    result.append(f"{str[-1]}{count}")              
    
    return "".join(result)


print(string_compression("aazzzziioo"))



def find_missing_no(lst):
    n = len(lst)
    expected_sum = n * (n + 1) // 2
    actual_sum = 0
    for i in lst:
        actual_sum += i 

    missing_num = expected_sum - actual_sum
    return missing_num



print(find_missing_no([0,1,2,3,4,5,6,8,9,10]))




def remove_duplicates(lst):
    result = []
    seen = set()
    for i in lst:
        if i in seen:
            continue
        else:
            seen.add(i)
            result.append(i)
    
    return result
    



print(remove_duplicates([1,2,2,3,2,5,6,5,4,5,6,6]))




def check_prime_number(n):
    if n < 2:
        return False

    if n == 2:
        return True

    if n % 2 == 0:
        return False

    for i in range(3, int(math.sqrt(n)) + 1, 2):
       if i % n == 0:
        return False

    return True





def flatten_list(lst):
    result = []
    for i in lst:
        if isinstance(i, list):
            result.extend(flatten_list(i))
        else:
            result.append(i)
    return result


def flatten_stack(lst):
    stack = list(lst)
    result = []
    while stack:
        item = stack.pop(0)
        if isinstance(item, list):
            stack = list(item) + stack
        else:
            result.append(item)
    return result





def reverse_strings(str):
    sentence_array = []
    current_word = ""
    for i in str:
        if i == " ":
            sentence_array.append(current_word)
            current_word = ""
        else:
            current_word += i
    if current_word:
        sentence_array.append(current_word)
    
    start, end = 0, len(sentence_array) - 1
    while start < end:
        sentence_array[start], sentence_array[end] = sentence_array[end], sentence_array[start]
        start += 1
        end -= 1
    
    return " ".join(sentence_array)






def balance_paranthesis(str):
    stack = []
    mappings = {')': '(', '}': '{', ']': '['}
    for i in str:
        if i in mappings:
            if not stack and stack[-1] != mappings[i]:
                return False
            stack.pop()
        else:
            stack.append(i)

    return len(stack) == 0








from collections import defaultdict

def group_anagrams(words):
    groups = defaultdict(list)
    
    for word in words:
        # sorted("eat") → ['a', 'e', 't']
        # tuple(['a', 'e', 't']) → ('a', 'e', 't')  — tuples can be dict keys
        key = tuple(sorted(word))
        groups[key].append(word)
    
    return list(groups.values())



def longest_prefix(lst):
    word = lst[0]
    for i in lst[1:]:
        while not i.startwith(word):
            word = word[:-1]
            if not prefix:
                return ""
    
    return word






def longest_prefix_another(lst):
    for i in range(len(lst[0])):
        char = lst[0][i]
        for s in lst[1:]:
            if i >= len(s) or s[i] != char:
                return lst[0][:i]
    
    return lst[0]







def roman_to_int(s):
    values = {
        'I': 1, 'V': 5, 'X': 10, 'L': 50,
        'C': 100, 'D': 500, 'M': 1000
    }
    count = 0
    for i in range(1, len(s)):
        if values[s[i]] > values[s[i-1]]:
            count -= values[s[i-1]]
        else:
            count += values[s[i-1]]
    
    count += values[s[-1]]

    return count





print(roman_to_int("MCMXCIV"))




def sliding_window(lst, k):
    start_lst = lst[:k]
    window_sum = sum(start_lst)
    max_sum = window_sum
    for i in range(k, len(lst)):
        window_sum += lst[i]
        window_sum -= lst[i - k]
        max_sum = max(max_sum, window_sum)
    
    return max_sum





def memoize(func):
    cache = {}
    def wrapper(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]
    
    return wrapper

@memoize
def expensive_function(n):
    result = 0
    for i in range(n):
        result += i ** 2
    
    return result




def power_set(lst):
    result = [[]]
    for i in lst:
        result += [subset + [i] for subset in result]
    return result