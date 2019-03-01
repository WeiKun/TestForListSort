#!/usr/bin/env python
# Author: weikun
# Created Time: Fri 01 Mar 2019 11:42:38 AM CST
import os
import random

funcs = []
def reg(key):
    def _reg(func):
        global funcs
        funcs.append((key, func))
        return func
    return _reg

@reg('float')
def float_list(n):
    random.seed(n)
    return [random.random() for _ in range(0,n)]

@reg('int')
def int_list(n):
    random.seed(n)
    return [int(2**31*random.random() - 2**30) for _ in range(0,n)]

@reg('long')
def long_list(n):
    random.seed(n)
    return int_list(n) + [2**64]

@reg('string')
def string_list(n):
    random.seed(n)
    return [str(random.random()) for _ in range(0,n)]

'''
@reg('string')
def string_list(n):
    random.seed(n)
    return latin_string_list(n) + ["\uffff"]
'''

@reg('heterogeneous')
def heterogeneous_list(n):
    return float_list(n) + [0]

def GenData(iterations, start_size, step, end_size):
    global funcs

    for label, func in funcs:
        path = 'TestData/%s' % label
        if not os.path.exists(path):
            os.makedirs(path) 

        for iteration in xrange(iterations):
            f = open(path + '/%05d' % (iteration, ), 'w+')
            for n in xrange(start_size, end_size, step):
                data = func(n)
                f.write(str(data) + '\n')

            f.close()

    return

if __name__ == '__main__':
    GenData(100, 1000, 100, 10000)

