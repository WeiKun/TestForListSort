#!/bin/bash
# Author: weikun
# Created Time: Fri 01 Mar 2019 11:45:45 PM CST

if [ ! -d "../cpython2.7/" ];then
    git clone https://github.com/WeiKun/cpython2.7.git ../cpython2.7
fi

rm python_s
srcpath='../cpython2.7/'
cpath=`pwd`
cd $srcpath
srcpath=`pwd`

#build 
cd $srcpath
make clean
./configure --enable-list-sort-optimization
make -j4
cd $cpath
ln -s ../cpython2.7/python python_s

#test
rm TestData.py
./python_s GenData.py
./python_s Test.py
