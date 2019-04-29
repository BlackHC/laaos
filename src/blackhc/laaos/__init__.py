from collections.abc import MutableMapping, MutableSequence, MutableSet
from datetime import datetime
from typing import Iterator
from typing import TypeVar
from typing import List
from io import TextIOBase
import enum
import pprint

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


class TypeHandler:
    def supports(self, obj):
        return False

    def wrap(self, obj, wrap):
        return obj

    def repr(self, obj, repr, store):
        return obj


class WeakEnumHandler(TypeHandler):
    """Requires expose_symbols on safe_load."""
    def supports(self, obj):
        return isinstance(obj, enum.Enum)

    def wrap(self, obj, wrap):
        return obj

    def repr(self, obj: enum.Enum, repr, store):
        return f'{obj.__class__.__qualname__}.{obj.name}'


class StrEnumHandler(TypeHandler):
    """Requires custom handling on safe_load."""
    def supports(self, obj):
        return isinstance(obj, enum.Enum)

    def wrap(self, obj, wrap):
        return obj

    def repr(self, obj: enum.Enum, repr, store):
        return repr(str(obj))


class ToReprHandler(TypeHandler):
    """Convert anything to repr. This is a catch-all."""
    def supports(self, obj):
        return True

    def wrap(self, obj, wrap):
        return obj

    def repr(self, obj: enum.Enum, repr, store):
        return repr(str(obj))


class Store:
    def __init__(self, log: TextIOBase, initial_data=None, type_handlers=()):
        if initial_data is None:
            initial_data = {}

        self._type_handlers: List[TypeHandler] = type_handlers
        self._log = log
        self._root = StoreRoot(self, self._wrap(initial_data))
        StoreAccessable.link(self._root, 'store')
        if initial_data:
            Store.write(self, f'store = (\n{pprint.pformat(initial_data, width=160, compact=True)}\n)')
        else:
            Store.write(self, 'store = {}')

    def close(self):
        self._log.close()

    def _wrap(self, obj):
        if isinstance(obj, (int, float, complex, str, type(None), bool)):
            pass
        elif isinstance(obj, StoreAccessable) and obj._accessor is None:
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
            for type_handler in self._type_handlers:
                if type_handler.supports(obj):
                    return type_handler.wrap(obj, self._wrap)
            raise KeyError(f'{type(obj)} not supported for LAAOS!')
        return obj

    def _repr(self, obj):
        if isinstance(obj, (int, float, complex, str, type(None), bool)):
            return repr(obj)
        elif isinstance(obj, list):
            return '[' + ', '.join(self._repr(value) for value in obj) + ']'
        elif isinstance(obj, dict):
            return '{' + ', '.join(f'{self._repr(key)}: {self._repr(value)}' for key, value in obj.items()) + '}'
        elif isinstance(obj, set):
            return '{' + ', '.join(self._repr(value) for value in obj) + '}' if obj else 'set()'
        else:
            for type_handler in self._type_handlers:
                if type_handler.supports(obj):
                    return type_handler.repr(obj, self._repr, self)
        return repr(obj)

    @staticmethod
    def write(store: 'Store', text):
        store._log.write(text + '\n')
        store._log.flush()

    @staticmethod
    def wrap(store: 'Store', obj):
        return store._wrap(obj)

    @staticmethod
    def repr(store: 'Store', obj):
        return store._repr(obj)

    @property
    def root(self) -> 'StoreRoot':
        return self._root

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

    def _repr(self, obj):
        return Store.repr(self._store, obj)

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

    def new_set(self, initial_data=None):
        if initial_data is None:
            initial_data = set()
        return StoreSet(self._store, initial_data)

    def new_list(self, initial_data=None):
        if initial_data is None:
            initial_data = []
        return StoreList(self._store, initial_data)

    def new_dict(self, initial_data=None):
        if initial_data is None:
            initial_data = {}
        return StoreDict(self._store, initial_data)


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
            StoreAccessable.link(value, f'{self._accessor}[{self._repr(key)}]')

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
        self._write(f'{self._accessor}[{self._repr(key)}]={self._repr(value)}')

        StoreAccessable.link(value, f'{self._accessor}[{self._repr(key)}]')

    def __delitem__(self, key: KT) -> None:
        if key not in self._data:
            # Early out with the correct exception
            del self._data[key]

        self._check_accessor()
        StoreAccessable.unlink(self._data.get(key, None))

        del self._data[key]

        self._write(f'del {self._accessor}[{self._repr(key)}]')

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[T_co]:
        return iter(self._data)

    def __repr__(self) -> str:
        return self._repr(self._data)


class StoreRoot(StoreDict):
    def __init__(self, store: Store, initial_data):
        super().__init__(store, initial_data)

    def close(self):
        return self._store.close()


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
            StoreAccessable.link(value, f'{self._accessor}[{self._repr(key)}]')

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

        self._write(f'{self._accessor}.insert({self._repr(index)}, {self._repr(obj)})')

    def append(self, obj: T) -> None:
        self._check_accessor()

        obj = self._wrap(obj)
        self._seq.append(obj)

        self._write(f'{self._accessor}.append({self._repr(obj)})')

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

        self._write(f'{self._accessor}[{self._repr(key)}] = {self._repr(value)}')
        StoreAccessable.link(value, f'{self._accessor}[{self._repr(key)}]')

    def __delitem__(self, key) -> None:
        if not 0 <= key < len(self._seq):
            # Early out with the correct exception
            del self._seq[key]

        self._check_accessor()

        StoreAccessable.unlink(self._seq[key])
        del self._seq[key]
        Store.write(self._store, f'del {self._accessor}[{self._repr(key)}]')

    def __len__(self) -> int:
        return len(self._seq)

    def __repr__(self) -> str:
        return self._repr(self._seq)

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
        self._write(f'{self._accessor}.add({self._repr(x)})')

    def discard(self, x: T) -> None:
        self._check_accessor()

        self._set.discard(x)
        self._write(f'{self._accessor}.discard({self._repr(x)})')

    def __contains__(self, x: object) -> bool:
        return x in self._set

    def __len__(self) -> int:
        return len(self._set)

    def __iter__(self) -> Iterator[T_co]:
        return iter(self._set)

    def __repr__(self) -> str:
        return self._repr(self._set)


def create_file_store(store_name='results', suffix=None, ext='.py', prefix='laaos/', truncate=False,
                      **kwargs) -> StoreRoot:
    if suffix is None:
        suffix = time_generate_id()

    filename = f'{prefix}{store_name}{suffix}{ext}'
    log = open(filename, "at" if not truncate else "wt")

    store = Store(log, **kwargs)
    return store.root


def safe_load_str(code: str, expose_symbols=None):
    exposed_symbols = dict(__builtins__=dict(set=set))
    if expose_symbols is not None:
        exposed_symbols.update({symbol.__name__: symbol for symbol in expose_symbols})

    root = dict()
    exec(code, exposed_symbols, root)
    return root['store']


def safe_load(filename: str, expose_symbols=None):
    with open(filename, 'rt') as file:
        return safe_load_str(file.read(), expose_symbols=expose_symbols)


def compact(source_path: str, destination_path: str):
    source_store = safe_load(source_path)

    destination = open(destination_path, "wt")
    destination_store = Store(destination, initial_data=source_store)
    destination_store.close()
