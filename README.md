# Log as append-only source package

[![Build Status](https://travis-ci.org/BlackHC/laaos.svg?branch=master)](https://travis-ci.org/BlackHC/laaos)

Logs as append-only source: write your ML training results in Python without having to worry about crashes. Loading is a breeze: the logs are native Python code. The package supports unstructured data. The data can easily be imported into Jupyter Notebooks or elsewhere.

## Installation

To install using pip, use:

```
pip install blackhc.laaos
```

To run the tests, use:

```
python setup.py test
```

## Append-only source logs

Storing training results as Python dictionaries or JSON files is problematic because the formats are not append-only, 
which means that you have to rewrite the file every time something changes. (Or you only write results at the end, 
which does not play well with interruptions or intermediate failures.)

Alternatively, we can simply write the operations that create a structure to a file in an append-only fashion.
If the data structure itself is growing and not mutated, this only increases file-size by a constant factor.

The advantage of this library is that the file format is very simple: it's valid Python code.

The only requirement is that you only store primitive types, lists, sets, dicts and immutable types.

Custom wrappers can be added by registering `TypeHandler`s when creating a `Store`. See `WeakEnumHandler` and `StrEnumHandler`.

## Example

```python
from blackhc.laaos import create_file_store, safe_load_store
store = create_file_store('test', suffix='')

store['losses'] = []
losses = store['losses']

for i in range(1, 10):
    losses.append(1/i)

store.close()
```

The resulting file `laaos/test.py` contains valid Python code:

```python
store = {}
store['losses']=[]
store['losses'].append(1.0)
store['losses'].append(0.5)
store['losses'].append(0.3333333333333333)
store['losses'].append(0.25)
store['losses'].append(0.2)
store['losses'].append(0.16666666666666666)
store['losses'].append(0.14285714285714285)
store['losses'].append(0.125)
store['losses'].append(0.1111111111111111)
```

It can be loaded either with:

```python
form laaos.test import store
```

or with the more secure:

```python
safe_load('laaos/test.py')
```
