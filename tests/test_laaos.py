import os

import pytest
import enum
import io
from laaos import Store, safe_load_str, safe_load, compact, new_dict, new_list, new_set, StrEnumHandler, \
    WeakEnumHandler, open_file_store


def create_memory_store(initial_data=None, type_handlers=None):
    code = io.StringIO()
    store = Store(code, initial_data=initial_data, type_handlers=type_handlers)
    return store.root, code


def test_creation():
    store, _ = create_memory_store()
    store.close()


def test_root_map():
    store, code = create_memory_store()
    store["test"] = 1
    assert store["test"] == 1
    del store["test"]
    store["another_test"] = 2
    assert store["another_test"] == 2
    assert "test" not in store

    assert len(store) == 1

    assert store == safe_load_str(code.getvalue())
    assert repr(store) == repr(safe_load_str(code.getvalue()))

    store.close()


def test_root_map_initial_data():
    store, code = create_memory_store(dict(a=2, b=3))
    assert store["a"] == 2
    assert store["b"] == 3
    assert "c" not in store

    assert store == safe_load_str(code.getvalue())
    assert repr(store) == repr(safe_load_str(code.getvalue()))

    store.close()


def test_map():
    store, code = create_memory_store()
    store["test"] = dict(a=2, b=3)
    assert store["test"] == dict(a=2, b=3)
    del store["test"]["a"]
    assert "a" not in store["test"]

    assert store == safe_load_str(code.getvalue())
    assert repr(store) == repr(safe_load_str(code.getvalue()))

    store.close()


def test_list():
    store, code = create_memory_store()
    store["list"] = [1, 2, 3]
    assert store["list"] == [1, 2, 3]

    store["list"].append(5)
    assert store["list"][-1] == 5

    del store["list"][0]

    assert store["list"] == [2, 3, 5]

    assert store == safe_load_str(code.getvalue())
    assert repr(store) == repr(safe_load_str(code.getvalue()))

    store.close()


def test_list_clear():
    store, code = create_memory_store()
    store["list"] = [1, 2, 3]
    assert store["list"] == [1, 2, 3]

    store["list"].clear()
    assert len(store["list"]) == 0

    assert store == safe_load_str(code.getvalue())
    assert repr(store) == repr(safe_load_str(code.getvalue()))

    store.close()


def test_set():
    store, code = create_memory_store()
    store["set"] = {1, 2, 3}
    assert store["set"] == {1, 2, 3}

    store["set"].add(5)

    assert 5 in store["set"]

    store["set"].discard(5)

    assert 5 not in store["set"]

    assert store == safe_load_str(code.getvalue())
    assert repr(store) == repr(safe_load_str(code.getvalue()))

    store.close()


def test_raise_on_slice():
    store, code = create_memory_store()
    store["list"] = [1, 2, 3]

    with pytest.raises(AssertionError):
        store["list"][0:1] = [[1]]

    store.close()


def test_raise_after_unlink():
    store, code = create_memory_store()
    store["list"] = [1, 2, 3]

    the_list = store["list"]
    the_list.append(5)

    store["list"] = None

    with pytest.raises(AssertionError):
        the_list.append(6)


def test_del_unknown():
    store, code = create_memory_store()
    store["list"] = []

    with pytest.raises(IndexError):
        del store["list"][1]

    with pytest.raises(KeyError):
        del store["set"]

    store.close()


def test_list_set_unknown():
    store, code = create_memory_store()
    store["list"] = []

    with pytest.raises(IndexError):
        store["list"][1] = 1


def test_nested_lists():
    store, code = create_memory_store(dict(lists=[[[]]]))
    store["lists"][0][0].append(1)

    assert store == safe_load_str(code.getvalue())
    assert repr(store) == repr(safe_load_str(code.getvalue()))

    store.close()


def test_fail_on_chained_assignment():
    store, code = create_memory_store()
    a = store["list"] = []
    a.append(1)

    assert a == [1]
    assert store["list"] == []
    assert a != store["list"]

    store.close()


def test_list_duplicate_on_multiple_assignments():
    store, code = create_memory_store()

    store["list"] = [1, 2]
    store["list2"] = store["list"]
    store["list"].append(3)

    assert 3 not in store["list2"]
    assert store["list"] != store["list2"]
    assert store == safe_load_str(code.getvalue())
    assert repr(store) == repr(safe_load_str(code.getvalue()))

    store.close()


def test_map_duplicate_on_multiple_assignments():
    store, code = create_memory_store()

    store["dict"] = dict(a=1)
    store["dict2"] = store["dict"]
    store["dict"]["b"] = 2

    assert store == safe_load_str(code.getvalue())
    assert repr(store) == repr(safe_load_str(code.getvalue()))

    store.close()


def test_relink_works():
    store, code = create_memory_store()

    store["dict"] = dict(a=1)
    a = store["dict"]

    del store["dict"]

    store["dict2"] = a
    store["dict2"]["b"] = 2

    assert store == safe_load_str(code.getvalue())
    assert repr(store) == repr(safe_load_str(code.getvalue()))

    store.close()


def test_compaction():
    compact("./laaos/test.py", "./laaos/test_compacted.py")


def test_create_file_store():
    store = open_file_store("test_create", suffix="", truncate=True)

    store["list"] = [1, 2]
    store["dict"] = dict(a=5, b=6)

    store.close()

    loaded_store = safe_load("./laaos/test_create.py")

    assert store == loaded_store


def test_append_file_store_edge_case():
    open("./laaos/test_append_edge.py", "w+")

    store = open_file_store("test_append_edge", suffix="")
    store.close()

    safe_load("./laaos/test_append_edge.py")


def test_append_file_store():
    open("./laaos/test_append.py", "w")
    os.remove("./laaos/test_append.py")

    store = open_file_store("test_append", suffix="")

    store["list"] = [1, 2]
    store["dict"] = dict(a=5, b=6)

    store.close()

    new_store = open_file_store("test_append", suffix="")

    assert store == new_store

    new_store["list"].append(3)
    new_store["dict"]["c"] = 10

    new_store.close()

    final_store = safe_load("./laaos/test_append.py")

    assert new_store == final_store


def test_can_passthrough_dict():
    store, code = create_memory_store()

    d = new_dict(store, "dict")
    d["a"] = 1

    assert store["dict"]["a"] == 1

    assert store == safe_load_str(code.getvalue())
    assert repr(store) == repr(safe_load_str(code.getvalue()))


def test_can_passthrough_list():
    store, code = create_memory_store()

    l = new_list(store, "list")
    l.append(1)

    assert store["list"] == [1]

    assert store == safe_load_str(code.getvalue())
    assert repr(store) == repr(safe_load_str(code.getvalue()))


def test_can_passthrough_set():
    store, code = create_memory_store()

    s = new_set(store, "set")
    s.add(1)

    assert store["set"] == {1}

    assert store == safe_load_str(code.getvalue())
    assert repr(store) == repr(safe_load_str(code.getvalue()))


def test_enum_str_handler():
    class A(enum.Enum):
        a = 1
        b = 2

    store, code = create_memory_store(type_handlers=[StrEnumHandler()])

    store[A.a] = A.b

    loaded = safe_load_str(code.getvalue())
    assert loaded == {"A.a": "A.b"}


class B(enum.Enum):
    a = 1
    b = 2


def test_enum_weak_handler():
    store, code = create_memory_store(type_handlers=[WeakEnumHandler()])

    store[B.a] = B.b

    loaded = safe_load_str(code.getvalue(), exposed_symbols=[B])
    assert loaded == store
