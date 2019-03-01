#!/usr/bin/env python
# Author: weikun
# Created Time: Thu 28 Feb 2019 11:21:11 AM CST
from GenData import funcs
import os, sys
import io, re
import tempfile
import ctypes

libc = ctypes.CDLL(None)

#This function allows us to benchmark the above types when they're in tuples
def tuplify(L):
    return [(x,) for x in L]


class STDOUT(object):
    def __init__(self):
        self.buff = ''
    
    def write(self, outStr):
        self.buff += outStr

original_stdout_fd = sys.stdout.fileno()
def run_benchmark():
    global funcs
    global original_stdout_fd
    scalar_times = {}
    tuple_times = {}
    for label, _ in funcs:
        path = 'TestData/%s/' % (label, )
        dataFiles = os.listdir(path)
        dataFiles.sort()
        
        scalar_times[label] = []
        tuple_times[label] = []

        for fname in dataFiles:
            total_scalar_time = 0
            total_tuple_time = 0
            with open(path + fname, 'r') as f:
                data = eval(f.readline())
                
                c_stdout = ctypes.c_void_p.in_dll(libc, 'stdout')
                libc.fflush(c_stdout)
                stdout = sys.stdout
                tfile1 = tempfile.TemporaryFile(mode='w')
                fd1 = tfile1.fileno()
                tfile2 = tempfile.TemporaryFile(mode='w+')
                #tfile2 = open('cache', 'w+')
                fd2 = tfile2.fileno()
                
                os.dup2(original_stdout_fd, fd1)
                sys.stdout.close()
                os.dup2(fd2, original_stdout_fd)
                
                tuplify(data).sort()
                data.sort()
                libc.fflush(c_stdout)
                
                tfile2.flush()
                tfile2.seek(0, io.SEEK_SET)
                buff = tfile2.read()

                sys.stdout.close()
                os.dup2(fd1, original_stdout_fd)
                sys.stdout = tfile1
                
                tuple_time, scalar_time = re.match('SORT TIME: (\d+)\nSORT TIME: (\d+)', buff.decode('utf-8')).groups()

                total_scalar_time += int(scalar_time)
                total_tuple_time += int(tuple_time)
        
            scalar_times[label].append(total_scalar_time)
            tuple_times[label].append(total_tuple_time)

    return scalar_times, tuple_times

if __name__ == '__main__':
    scalar_times, tuple_times = run_benchmark()
    s = 'scalar_times = %s\ntuple_times=%s' % (str(scalar_times), str(tuple_times))
    if len(sys.argv) >= 2:
        f = open(argv[1],'w+')
        f.write(s)
        f.close()
    else:
        print s


