import timeit
import time
from unittest import result

def add_one(a):
    return 1 + a[0]

def sum_array(a):
    return sum(a)

def pair(a):
    pairs = []
    for i in range(len(a)):
        for j in range(i + 1, len(a)):
            pairs.append((a[i], a[j]))
    return pairs 

def timeit(func, *args, **kwargs):
    start_time = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - start_time
    print(f"elapsed time: {elapsed:.6f} seconds")
    return result

def getNthFib(n, cache={1: 0, 2: 1}):
    if n < 0:
        raise ValueError("negative number")
    if n in cache:
        return cache[n]
    cache[n] = getNthFib(n-1, cache) + getNthFib(n-2, cache)
    return cache[n]

def getNthFib(n):
    if n == 1:
        return 0
    elif n == 2:
        return 1
    else:
        return getNthFib(n - 1) + getNthFib(n - 2)

def main():
    print("Hello, World!")
    # for n in range (1, 11):
    #     print(f"The {n}th Fibonacci number is: {getNthFib(n)}")
    stepcount(5, [1, 2])

    # todo: write out these different algorithms to see how fast they run
    # assume you have a a = [....], array of length n, basically
    
    # f1(a) = 1 + a[0] --> O(1)
    # f2(a) = sum(a) --> O(n)
    # f3(a) = pair(a) --> O(n^2)
    # import a library that tracks how much time elapses between lines of code 
    
    
# TODO: write out a python state machine. Describe all of the objects.

if __name__ == "__main__":
    main()