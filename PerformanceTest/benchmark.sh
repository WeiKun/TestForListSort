#!/bin/bash
# Author: weikun
# Created Time: Fri 01 Mar 2019 10:12:56 PM CST
./python_r Test.py mark_r.py
./python_o Test.py mark_o.py

python benchmark.py mark_r mark_o
