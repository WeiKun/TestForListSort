#!/usr/bin/env python
# Author: weikun
# Created Time: Thu 28 Feb 2019 10:21:22 AM CST
import TestData

for i, dataNode in enumerate(TestData.data):
    unsorted = dataNode['unsorted']
    unsorted.sort()
    if (unsorted != dataNode['sorted']):
        print 'ERROR!!!! %d' % (i, )
        break
else:
    print 'Success!!!!'
        
