# Python List Sort优化
## 来源
在Python中，list的排序时，采用的是归并排序算法（有优化）。不过由于本次优化并不是在排序算法上进行，因此不细表。

在实现细节上，显然排序时会不断调用compare函数，以py2.7为例，普通情况下，Python-List在sort时调用的标准函数是PyObject_RichCompareBool

```c
/* Return -1 if error; 1 if v op w; 0 if not (v op w). */
int
PyObject_RichCompareBool(PyObject *v, PyObject *w, int op)
{
    PyObject *res;
    int ok;

    /* Quick result when objects are the same.
       Guarantees that identity implies equality. */
    if (v == w) {
        if (op == Py_EQ)
            return 1;
        else if (op == Py_NE)
            return 0;
    }

    res = PyObject_RichCompare(v, w, op);
    if (res == NULL)
        return -1;
    if (PyBool_Check(res))
        ok = (res == Py_True);
    else
        ok = PyObject_IsTrue(res);
    Py_DECREF(res);
    return ok;
}

/* Return:
   NULL for exception;
   some object not equal to NotImplemented if it is implemented
     (this latter object may not be a Boolean).
*/
PyObject *
PyObject_RichCompare(PyObject *v, PyObject *w, int op)
{
    PyObject *res;

    assert(Py_LT <= op && op <= Py_GE);
    if (Py_EnterRecursiveCall(" in cmp"))
        return NULL;

    /* If the types are equal, and not old-style instances, try to
       get out cheap (don't bother with coercions etc.). */
    if (v->ob_type == w->ob_type && !PyInstance_Check(v)) {
        cmpfunc fcmp;
        richcmpfunc frich = RICHCOMPARE(v->ob_type);
        /* If the type has richcmp, try it first.  try_rich_compare
           tries it two-sided, which is not needed since we've a
           single type only. */
        if (frich != NULL) {
            res = (*frich)(v, w, op);
            if (res != Py_NotImplemented)
                goto Done;
            Py_DECREF(res);
        }
        /* No richcmp, or this particular richmp not implemented.
           Try 3-way cmp. */
        fcmp = v->ob_type->tp_compare;
        if (fcmp != NULL) {
            int c = (*fcmp)(v, w);
            c = adjust_tp_compare(c);
            if (c == -2) {
                res = NULL;
                goto Done;
            }
            res = convert_3way_to_object(op, c);
            goto Done;
        }
    }

    /* Fast path not taken, or couldn't deliver a useful result. */
    res = do_richcmp(v, w, op);
Done:
    Py_LeaveRecursiveCall();
    return res;
}

```
可以看到，正常情况下的compare流程：

1. 先判断两个对象是不是同类型，如果是就尝试使用tp_richcompare或者tp_compare进行compare
2. 如果1失败，就判断是不是继承关系，如果是就用父类的的tp_richcompare或进行compare
3. 如果2失败，那么就尝试用其中一个对象的tp_richcompare或进行compare（先用第一个，如果没有再试试另一个）
4. 如果3失败，那么就尝试用tp_compare进行compare
5. 如果4还失败就尝试特殊判断（例如如果一方为None就一定小于其他，比较双方的类型name字符串，比较双方类型的地址）。

在实际的项目中，需要sort的list里的元素都是同类型的，也就是走上述compare流程的第一步就返回了。所以如果我们能针对第一步进行优化，就可以优化绝大多数sort的场景。

## python3的优化
python3的[bpo-28685更新](https://github.com/python/cpython/commit/1e34da49ef22004ca25c517b3f07c6d25f083ece)中就提供了一种优化方案。其方式很简单，就是提前判断list里的对象是不是同一个类型，如果是就提前准备好compare函数而不调用通用的PyObject_RichCompareBool函数，这样做：
- 一来可以避免PyObject_RichCompareBool里的判断跟运算
- 二来可以避免每次判断都先把结果记入一个PyBool变量然后又要在PyObject_RichCompareBool结尾把结果从PyBool变量里取出来。

具体实现是这样的：
1. 先遍历list里所有元素，判断是否是同一个类型，如果是则标记keys_are_all_same_type为1，如果类型为tuple并且tuple的第一个元素也为也为同一个类型(类似[(1,), (2,), (3,)])则标记keys_are_in_tuples为1(这是另一个优化方案，下面再讲)

```c
        int keys_are_in_tuples = (lo.keys[0]->ob_type == &PyTuple_Type &&
                                  Py_SIZE(lo.keys[0]) > 0);

        PyTypeObject* key_type = (keys_are_in_tuples ?
                                  PyTuple_GET_ITEM(lo.keys[0], 0)->ob_type :
                                  lo.keys[0]->ob_type);

        int keys_are_all_same_type = 1;
        int strings_are_latin = 1;
        int ints_are_bounded = 1;

        /* Prove that assumption by checking every key. */
        for (i=0; i < saved_ob_size; i++) {

            if (keys_are_in_tuples &&
                !(lo.keys[i]->ob_type == &PyTuple_Type && Py_SIZE(lo.keys[i]) != 0)) {
                keys_are_in_tuples = 0;
                keys_are_all_same_type = 0;
                break;
            }

            /* Note: for lists of tuples, key is the first element of the tuple
             * lo.keys[i], not lo.keys[i] itself! We verify type-homogeneity
             * for lists of tuples in the if-statement directly above. */
            PyObject *key = (keys_are_in_tuples ?
                             PyTuple_GET_ITEM(lo.keys[i], 0) :
                             lo.keys[i]);

            if (key->ob_type != key_type) {
                keys_are_all_same_type = 0;
                break;
            }

            if (key_type == &PyLong_Type) {
                if (ints_are_bounded && Py_ABS(Py_SIZE(key)) > 1)
                    ints_are_bounded = 0;
            }
            else if (key_type == &PyUnicode_Type){
                if (strings_are_latin &&
                    PyUnicode_KIND(key) != PyUnicode_1BYTE_KIND)
                strings_are_latin = 0;
            }
        }
```

2. 如果keys_are_all_same_type为1则设置ms.key_compare为指定的判断函数，否则设置为safe_object_compare

```c
        /* Choose the best compare, given what we now know about the keys. */
        if (keys_are_all_same_type) {

            if (key_type == &PyUnicode_Type && strings_are_latin) {
                ms.key_compare = unsafe_latin_compare;
            }
            else if (key_type == &PyLong_Type && ints_are_bounded) {
                ms.key_compare = unsafe_long_compare;
            }
            else if (key_type == &PyFloat_Type) {
                ms.key_compare = unsafe_float_compare;
            }
            else if ((ms.key_richcompare = key_type->tp_richcompare) != NULL) {
                ms.key_compare = unsafe_object_compare;
            }
            else {
                ms.key_compare = safe_object_compare;
            }
        }
        else {
            ms.key_compare = safe_object_compare;
        }

```

3. 如果keys_are_in_tuples为1则置key_compare为unsafe_tuple_compare，并且如果tuple首元素类型不为tuple则置ms.tuple_elem_compare为2中的ms.key_compare，否则为safe_object_compare(跟2的逻辑类似，不过利用了2中代码)
```c
        if (keys_are_in_tuples) {
            /* Make sure we're not dealing with tuples of tuples
             * (remember: here, key_type refers list [key[0] for key in keys]) */
            if (key_type == &PyTuple_Type)
                ms.tuple_elem_compare = safe_object_compare;
            else
                ms.tuple_elem_compare = ms.key_compare;

            ms.key_compare = unsafe_tuple_compare;
        }
```

4. 然后在宏ISLT的定义上用ms->key_compare替代PyObject_RichCompareBool，当然safe_object_compare实际调用的也是PyObject_RichCompareBool，也就是如果list内的类型是各自不同的，会退化成PyObject_RichCompareBool甚至更差(多了一层调用)

具体再看tuple里的进一步优化方案
```c
static int
unsafe_tuple_compare(PyObject *v, PyObject *w, MergeState *ms)
{
    PyTupleObject *vt, *wt;
    Py_ssize_t i, vlen, wlen;
    int k;

    /* Modified from Objects/tupleobject.c:tuplerichcompare, assuming: */
    assert(v->ob_type == w->ob_type);
    assert(v->ob_type == &PyTuple_Type);
    assert(Py_SIZE(v) > 0);
    assert(Py_SIZE(w) > 0);

    vt = (PyTupleObject *)v;
    wt = (PyTupleObject *)w;

    vlen = Py_SIZE(vt);
    wlen = Py_SIZE(wt);

    for (i = 0; i < vlen && i < wlen; i++) {
        k = PyObject_RichCompareBool(vt->ob_item[i], wt->ob_item[i], Py_EQ);
        if (k < 0)
            return -1;
        if (!k)
            break;
    }

    if (i >= vlen || i >= wlen)
        return vlen < wlen;

    if (i == 0)
        return ms->tuple_elem_compare(vt->ob_item[i], wt->ob_item[i], ms);
    else
        return PyObject_RichCompareBool(vt->ob_item[i], wt->ob_item[i], Py_LT);
}
```
如果tuple的第一个元素就不一样，那么就用tuple_elem_compare进行判断，否则还是用PyObject_RichCompareBool，这样只要tuple的一个元素不一样就会得到一定的优化提升，否则依然退化成PyObject_RichCompareBool的略差版本(多了调用跟判断)。

根据官方更新时附上的[Benchmarks](https://github.com/python/cpython/pull/582)：

Type                        | Percent improvement on random lists
---                         |   ---
heterogeneous               | -1.5%
float                       | 48%
bounded int                 | 48.4%
latin string                | 32.7%
general int                 | 17.2%
general string              | 9.2%
tuples of float             | 63.2%
tuples of bounded int       | 64.8%
tuples of latin string      | 55.8%
tuples of general int       | 50.3%
tuples of general string    | 44.1%
tuples of heterogeneous     | 41.5%

[单击就送测试代码](https://github.com/embg/python-fastsort-benchmark.git)

## 对python2.7的移植

基于最新的python2.7.15来设计移植
移植后的代码在https://github.com/WeiKun/cpython2.7.git

### 异同比较
首先比较python2.7跟python3在list的sort操作中的差异
1. python2.7的sort可以携带cmp函数而python3的不行
2. python2.7与python3的类型略有不同，除了整形跟字符串都有迭代修改

### 修改各级参数
对诸多对compare变量作为函数参数进行传递的函数进行修改，改为传递MergeState的指针

```c
- binarysort(PyObject **lo, PyObject **hi, PyObject **start, PyObject *compare)
+ binarysort(MergeState *ms, PyObject **lo, PyObject **hi, PyObject **start)

- count_run(PyObject **lo, PyObject **hi, PyObject *compare, int *descending)
+ count_run(MergeState *ms, PyObject **lo, PyObject **hi, int *descending)

- gallop_left(PyObject *key, PyObject **a, Py_ssize_t n, Py_ssize_t hint, PyObject *compare)
+ gallop_left(MergeState *ms, PyObject *key, PyObject **a, Py_ssize_t n, Py_ssize_t hint)

= gallop_right(PyObject *key, PyObject **a, Py_ssize_t n, Py_ssize_t hint, PyObject *compare)
+ gallop_right(MergeState *ms, PyObject *key, PyObject **a, Py_ssize_t n, Py_ssize_t hint)
```

### 修改MergeState结构体
在MergeState中加入成员变量存储优化时用到的函数指针

```c
typedef struct s_MergeState MergeState;

struct s_MergeState {
    ......
    ......
    ......
    /* This is the function we will use to compare two keys,
     * even when none of our special cases apply and we have to use
     * safe_object_compare. */
    int (*key_compare)(PyObject *, PyObject *, MergeState *);

    /* This function is used by unsafe_object_compare to optimize comparisons
     * when we know our list is type-homogeneous but we can't assume anything else.
     * In the pre-sort check it is set equal to key->ob_type->tp_richcompare */
    PyObject *(*key_richcompare)(PyObject *, PyObject *, int);

    /* This function is used by unsafe_tuple_compare to compare the first elements
     * of tuples. It may be set to safe_object_compare, but the idea is that hopefully
     * we can assume more, and use one of the special-case compares. */
    int (*tuple_elem_compare)(PyObject *, PyObject *, MergeState *);
};
```

### 修改ISLT宏

```c
#ifdef FAST_LIST_SORT
    #define ISLT(X, Y) ((ms->compare == NULL) ? \
                (*(ms->key_compare))(X, Y, ms) : \
                islt(X, Y, ms->compare))
#else
    #define ISLT(X, Y) ((ms->compare == NULL) ? \
                 PyObject_RichCompareBool(X, Y, Py_LT) :                \
                islt(X, Y, ms->compare))
#endif /*FAST_LIST_SORT*/
```

### 修改sort流程
在sort流程里加入类型一致性检查跟对key_compare的赋值，用预编译选项包起来

```
#ifdef FAST_LIST_SORT
    /* The pre-sort check: here's where we decide which compare function to use.
     * How much optimization is safe? We test for homogeneity with respect to
     * several properties that are expensive to check at compare-time, and
     * set ms appropriately. */
    if (!compare && saved_ob_size > 1) {
        /* Assume the first element is representative of the whole list. */
        int keys_are_in_tuples = (saved_ob_item[0]->ob_type == &PyTuple_Type &&
                                  Py_SIZE(saved_ob_item[0]) > 0);

        PyTypeObject* key_type = (keys_are_in_tuples ?
                                  PyTuple_GET_ITEM(saved_ob_item[0], 0)->ob_type :
                                  saved_ob_item[0]->ob_type);

        int keys_are_all_same_type = 1;

        /* Prove that assumption by checking every key. */
        for (i=0; i < saved_ob_size; i++) {

            if (keys_are_in_tuples &&
                !(saved_ob_item[i]->ob_type == &PyTuple_Type && Py_SIZE(saved_ob_item[i]) != 0)) {
                keys_are_in_tuples = 0;
                keys_are_all_same_type = 0;
                break;
            }

            /* Note: for lists of tuples, key is the first element of the tuple
             * saved_ob_item[i], not saved_ob_item[i] itself! We verify type-homogeneity
             * for lists of tuples in the if-statement directly above. */
            key = keys_are_in_tuples ? PyTuple_GET_ITEM(saved_ob_item[i], 0) : saved_ob_item[i];

            if (key->ob_type != key_type) {
                keys_are_all_same_type = 0;
                break;
            }
        }

        /* Choose the best compare, given what we now know about the keys. */
        if (keys_are_all_same_type) {
            if (key_type == &PyString_Type) {
                ms.key_compare = unsafe_string_compare;
            }
            else if (key_type == &PyInt_Type) {
                ms.key_compare = unsafe_int_compare;
            }
            else if (key_type == &PyFloat_Type) {
				ms.key_compare = unsafe_float_compare;
            }
            else if ((ms.key_richcompare = key_type->tp_richcompare) != NULL) {
                ms.key_compare = unsafe_object_compare;
            }
            else {
                ms.key_compare = safe_object_compare;
            }
        }
        else {
            ms.key_compare = safe_object_compare;
        }

        if (keys_are_in_tuples) {
            /* Make sure we're not dealing with tuples of tuples
             * (remember: here, key_type refers list [key[0] for key in keys]) */
            if (key_type == &PyTuple_Type)
                ms.tuple_elem_compare = safe_object_compare;
            else
                ms.tuple_elem_compare = ms.key_compare;

            ms.key_compare = unsafe_tuple_compare;
        }
    }
#endif /*FAST_LIST_SORT*/
    /* End of pre-sort check: ms is now set properly! */
```


### 添加compare
针对需要优化的类型，逐个添加unsafe_compare方法
经过权衡，放弃了对unicode/long的优化，实现了针对string/int/float/tuple/object的优化


## 测试
测试代码在https://github.com/WeiKun/TestForListSort.git

### 一致性验证测试
首先在每一个unsafe_compare函数的返回处加入assert判断是否与PyObject_RichCompareBool结果是否一致，这样方便在实际项目中进行部分验证。

然后预先随机构造足够多的测试数据，然后乱序，用原python生成如下格式数据
```python
data = (
    {
      'unsorted' : [3, 2, 1], 
      'sorted' : [1, 2, 3], 
    },
)

```
再用新python来进行测试，验证sort之后的数据跟sorted的一致
具体在https://github.com/WeiKun/TestForListSort.git的ConformanceTest的run_test.sh中


### 性能测试
1. 首先采用如下的代码段来输出每次sort的指令周期数
--enable-list-sort
```c
unsigned start_low, start_high, end_low, end_high;
__asm__ __volatile__("rdtsc" : "=a" (start_low), "=d" (start_high));

/*正文*/

__asm__ __volatile__("rdtsc" : "=a" (end_low), "=d" (end_high));
printf("SORT TIME: %lu\n", (((uint64_t)end_high << 32) | end_low) - (((uint64_t)start_high << 32) | start_low));
```

2. 然后通过重定向标准输出来获取每次sort的指令周期数

具体代码在PerformanceTest/Test.py中，利用了os.dup2来置换stdout的fd，否则单纯对stdout进行重新赋值无法让C代码的printf部分重定向。


3. 最后汇总性能指标输出

Type                        | Percent improvement on random lists
---                         |   ---
float                       | 35.77%
int                         | 42.48%
string                      | 24.49%
heterogeneous               | -10.46%
tuples of float             | 26.53%
tuples of int               | 33.39%
tuples of string            | 25.31%
tuples of heterogeneous     | 13.46%

具体测试流程在https://github.com/WeiKun/TestForListSort.git的PerformanceTest的run_test.sh中
