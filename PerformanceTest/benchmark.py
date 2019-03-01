#!/usr/bin/env python
# Author: weikun
# Created Time: Fri 01 Mar 2019 04:53:01 PM CST
import sys
from GenData import funcs
print sys.argv[1], sys.argv[2]
mark_r = __import__(sys.argv[1])
mark_o = __import__(sys.argv[2])

allScalar = {}
allTuple = {}
for label, _ in funcs:
    print label, ':'
    allScalar[label] = []
    allTuple[label] = []
    for OriginTime, OptimizeTime in zip(mark_r.scalar_times[label], mark_o.scalar_times[label]):
        print OptimizeTime, OriginTime, float(OptimizeTime) / OriginTime, 1 - float(OptimizeTime) / OriginTime
        allScalar[label].append(float(OptimizeTime) / OriginTime)
    
    for OriginTime, OptimizeTime in zip(mark_r.tuple_times[label], mark_o.tuple_times[label]):
        print OptimizeTime, OriginTime, float(OptimizeTime) / OriginTime, 1 - float(OptimizeTime) / OriginTime
        allTuple[label].append(float(OptimizeTime) / OriginTime)
    
for label, _ in funcs:
    print label, ': ', sum(allScalar[label]) / len(allScalar[label]), 1 - sum(allScalar[label]) / len(allScalar[label])
    print label, ' - tuple: ', sum(allTuple[label]) / len(allTuple[label]), 1 - sum(allTuple[label]) / len(allTuple[label])
