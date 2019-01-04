from collections.abc import MutableMapping, MutableSequence, MutableSet
from datetime import datetime
from typing import Iterator
from typing import TypeVar
from io import TextIOBase

T = TypeVar('T')  # Any type.
KT = TypeVar('KT')  # Key type.
VT = TypeVar('VT')  # Value type.
T_co = TypeVar('T_co', covariant=True)  # Any type covariant containers.
V_co = TypeVar('V_co', covariant=True)  # Any type covariant containers.
VT_co = TypeVar('_VT_co', covariant=True)  # Value type covariant containers.


def time_generate_id():
    now = datetime.now()
    id = now.strftime('%Y-%m-%d-%H%M%S')
    return '_' + id


def can_iter(obj):
    try:
        iter(obj)
    except TypeError:
        return False
    else:
        return True


def try_str_encoding(obj, wrap):
    return str(obj)


class Store(MutableMapping):
    def __init__(self, log: TextIOBase, initial_data=None, encoder=None):
        if initial_data is None:
            initial_data = {}

        self._encoder = encoder
        self._log = log
        self._root = StoreDict(self, self._wrap(initial_data))
        StoreAccessable.link(self._root, 'store')
        Store.write(self, f'store = {self._root!r}')

    def close(self):
        self._log.close()

    def _wrap(self, obj):
        if isinstance(obj, (int, float, complex, str, type(None), bool)):
            pass
        elif isinstance(obj, (list, StoreList)):
            obj = StoreList(self, [self._wrap(value) for value in obj])
        elif isinstance(obj, (dict, StoreDict)):
            obj = StoreDict(self, {key: self._wrap(value) for key, value in obj.items()})
        elif isinstance(obj, (set, StoreSet)):
            obj = StoreSet(self, {self._wrap(value) for value in obj})
        elif can_iter(obj):
            obj = StoreList(self, [self._wrap(value) for value in iter(obj)])
        else:
            if self._encoder:
                encoded_obj = self._encoder(obj, self._wrap)
                if encoded_obj is not obj:
                    obj = self._wrap(encoded_obj)
                    return obj
            raise KeyError(f'{type(obj)} not supported for LAAOS!')
        return obj

    @staticmethod
    def write(store: 'Store', text):
        store._log.write(text + '\n')
        store._log.flush()

    @staticmethod
    def wrap(store: 'Store', obj):
        return store._wrap(obj)

    def __setitem__(self, k: KT, v: VT) -> None:
        self._root[k] = v

    def __delitem__(self, v: KT) -> None:
        del self._root[v]

    def __getitem__(self, k: KT) -> VT_co:
        return self._root[k]

    def __len__(self) -> int:
        return len(self._root)

    def __iter__(self) -> Iterator[T_co]:
        return iter(self._root)

    def __repr__(self):
        return repr(self._root)


class StoreAccessable(object):
    def __init__(self, store: Store):
        self._store = store
        self._accessor = None

    def _check_accessor(self):
        assert self._accessor is not None, ('You tried to mutate a store collection after it has been unlinked!\n\n'
                                            'This triggers an exception because it would be too hard to figure out how '
                                            'to rewrite this into something executable.')

    def _wrap(self, obj):
        return Store.wrap(self._store, obj)

    def _write(self, text):
        return Store.write(self._store, text)

    def _unlink(self):
        self._accessor = None

    def _link(self, accessor):
        self._accessor = accessor

    @staticmethod
    def unlink(obj):
        if isinstance(obj, StoreAccessable):
            obj._unlink()

    @staticmethod
    def link(obj, accessor):
        if isinstance(obj, StoreAccessable):
            obj._link(accessor)


class StoreDict(MutableMapping, StoreAccessable):
    def __init__(self, store: Store, initial_data):
        super().__init__(store)
        self._data = {}
        self._data.update(initial_data)

    def _unlink(self):
        super()._unlink()
        for value in self._data.values():
            StoreAccessable.unlink(value)

    def _link(self, accessor):
        super()._link(accessor)
        for key, value in self._data.items():
            StoreAccessable.link(value, f'{self._accessor}[{key!r}]')

    def __getitem__(self, key: KT) -> VT_co:
        return self._data[key]

    def __setitem__(self, key: KT, value: VT) -> None:
        self._check_accessor()

        old_value = self._data.get(key, None)
        if old_value is value:
            return

        StoreAccessable.unlink(old_value)

        value = self._wrap(value)
        self._data[key] = value
        self._write(f'{self._accessor}[{key!r}]={value!r}')

        StoreAccessable.link(value, f'{self._accessor}[{key!r}]')

    def __delitem__(self, key: KT) -> None:
        if key not in self._data:
            # Early out with the correct exception
            del self._data[key]

        self._check_accessor()
        StoreAccessable.unlink(self._data.get(key, None))

        del self._data[key]

        self._write(f'del {self._accessor}[{key!r}]')

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[T_co]:
        return iter(self._data)

    def __repr__(self) -> str:
        return repr(self._data)


class StoreList(MutableSequence, StoreAccessable):
    def __init__(self, store, seq: list):
        super().__init__(store)
        self._seq = list(seq)

    def _unlink(self):
        super()._unlink()
        for value in self._seq:
            StoreAccessable.unlink(value)

    def _link(self, accessor):
        super()._link(accessor)
        for key, value in enumerate(self._seq):
            StoreAccessable.link(value, f'{self._accessor}[{key!r}]')

    def clear(self) -> None:
        self._check_accessor()
        for value in self._seq:
            StoreAccessable.unlink(value)
        self._seq.clear()
        self._write(f'{self._accessor}.clear()')

    def insert(self, index: int, obj: T) -> None:
        self._check_accessor()

        obj = self._wrap(obj)
        self._seq.insert(index, obj)

        self._write(f'{self._accessor}.insert({index!r}, {obj!r})')

    def append(self, obj: T) -> None:
        self._check_accessor()

        obj = self._wrap(obj)
        self._seq.append(obj)

        self._write(f'{self._accessor}.append({obj!r})')

    def __getitem__(self, key) -> T:
        return self._seq[key]

    def __setitem__(self, key, value) -> None:
        assert not isinstance(key, slice), "Slices are not supported for lists in the store!"
        if not 0 <= key < len(self._seq):
            # Early out with the correct exception
            self._seq[key] = value

        self._check_accessor()

        old_value = self._seq[key]
        if old_value is value:
            return

        StoreAccessable.unlink(old_value)

        value = self._wrap(value)
        self._seq[key] = value

        self._write(f'{self._accessor}[{key!r}] = {value!r}')
        StoreAccessable.link(value, f'{self._accessor}[{key!r}]')

    def __delitem__(self, key) -> None:
        if not 0 <= key < len(self._seq):
            # Early out with the correct exception
            del self._seq[key]

        self._check_accessor()

        StoreAccessable.unlink(self._seq[key])
        del self._seq[key]
        Store.write(self._store, f'del {self._accessor}[{key!r}]')

    def __len__(self) -> int:
        return len(self._seq)

    def __repr__(self) -> str:
        return repr(self._seq)

    def __eq__(self, other):
        if isinstance(other, StoreList):
            return self._seq == other._seq
        return self._seq == other


class StoreSet(MutableSet, StoreAccessable):
    def __init__(self, store: Store, initial_data):
        super().__init__(store)
        self._set = set(initial_data)

    def add(self, x: T) -> None:
        self._check_accessor()

        self._set.add(x)
        self._write(f'{self._accessor}.add({x!r})')

    def discard(self, x: T) -> None:
        self._check_accessor()

        self._set.discard(x)
        self._write(f'{self._accessor}.discard({x!r})')

    def __contains__(self, x: object) -> bool:
        return x in self._set

    def __len__(self) -> int:
        return len(self._set)

    def __iter__(self) -> Iterator[T_co]:
        return iter(self._set)

    def __repr__(self) -> str:
        return repr(self._set)


def create_file_store(store_name='results', suffix=None, prefix='laaos/', **kwargs) -> Store:
    if suffix is None:
        suffix = time_generate_id()

    filename = f'{prefix}{store_name}{suffix}.py'
    log = open(filename, "at")

    return Store(log, **kwargs)


def safe_load_store_str(code: str):
    root = dict()
    exec(code, dict(__builtins__=dict()), root)
    return root['store']


def safe_load_store(filename: str):
    with open(filename, 'rt') as file:
        return safe_load_store_str(file.read())
