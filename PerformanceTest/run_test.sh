#!/bin/bash
# Author: weikun
# Created Time: Fri 01 Mar 2019 09:20:10 AM CST
#
srcpath='../cpython2.7/'
cpath=`pwd`
cd $srcpath
srcpath=`pwd`
echo $srcpath
echo $cpath

#build origin cpython2.7###
cd $srcpath
make clean
./configure --enable-test-list-sort --enable-optimizations
make -j4
mv python python_r
cd $cpath
if [ -f "python_r" ];then
    rm python_r
fi
ln -s ../cpython2.7/python_r python_r


#build optimization cpython2.7###
cd $srcpath
make clean
./configure --enable-test-list-sort --enable-list-sort --enable-optimizations
make -j4
mv python python_o
cd $cpath
if [ -f "python_o" ];then
    rm python_o
fi
ln -s ../cpython2.7/python_o python_o

#test
#Gen Data
rm -rf TestData/
python GenData.py

sh benchmark.sh
