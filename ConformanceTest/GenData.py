#!/usr/bin/env python
# Author: weikun
# Created Time: Thu 28 Feb 2019 10:21:06 AM CST
import random

funcs = []

def float_list(n):
    random.seed(n)
    return [random.random() for _ in range(0,n)]
funcs.append(('float',float_list))

def small_int_list(n):
    random.seed(n)
    return [int(2**31*random.random() - 2**30) for _ in range(0,n)]
funcs.append(('small_int',small_int_list))

def int_list(n):
    random.seed(n)
    return small_int_list(n) + [2**64]
funcs.append(('int',int_list))

def latin_string_list(n):
    random.seed(n)
    return [str(random.random()) for _ in range(0,n)]
funcs.append(('latin_string',latin_string_list))

def string_list(n):
    random.seed(n)
    return latin_string_list(n) + ["\uffff"]
funcs.append(('string',string_list))

def heterogeneous_list(n):
    return float_list(n) + [0]
funcs.append(('heterogeneous',heterogeneous_list))

#This function allows us to benchmark the above types when they're in tuples
def tuplify(L):
    return [(x,) for x in L]

strings = []
strings.append('data = [');

for key, func in funcs:
    for _ in xrange(10):
        l = func(20)
        strings.append('    {');
        strings.append("        'unsorted' : %s," % (str(l), ))
        l.sort()
        strings.append("        'sorted' : %s," % (str(l), ))
        strings.append('    },');

strings.append(']');
f = open('TestData.py', 'w')
f.write('\n'.join(strings))
f.close()
