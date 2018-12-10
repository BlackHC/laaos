# Log as append-only source package

[![Build Status](https://travis-ci.org/BlackHC/laaos.svg?branch=master)](https://travis-ci.org/BlackHC/laaos)

Idea is to
```
from blackhc.laaos import create_file_store
```
and be able to create append-only source logs that can easily be imported into Jupyter Notebooks and elsewhere.

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

Storing results as Python dictionaries or JSON files is problematic because the formats are not append-only, which means
that either 
