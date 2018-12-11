import pytest

import io
from blackhc.laaos import Store, safe_load_store_str


def test_creation():
    code = io.StringIO()

    store = Store(code)
    store.close()


def test_root_map():
    code = io.StringIO()

    store = Store(code)
    store['test'] = 1
    assert store['test'] == 1
    del store['test']
    store['another_test'] = 2
    assert store['another_test'] == 2
    assert 'test' not in store

    assert len(store) == 1

    assert store == safe_load_store_str(code.getvalue())
    assert repr(store) == repr(safe_load_store_str(code.getvalue()))

    store.close()


def test_root_map_initial_data():
    code = io.StringIO()

    store = Store(code, dict(a=2, b=3))
    assert store['a'] == 2
    assert store['b'] == 3
    assert 'c' not in store

    assert store == safe_load_store_str(code.getvalue())
    assert repr(store) == repr(safe_load_store_str(code.getvalue()))

    store.close()


def test_map():
    code = io.StringIO()

    store = Store(code)
    store['test'] = dict(a=2, b=3)
    assert store['test'] == dict(a=2, b=3)
    del store['test']['a']
    assert 'a' not in store['test']

    assert store == safe_load_store_str(code.getvalue())
    assert repr(store) == repr(safe_load_store_str(code.getvalue()))

    store.close()


def test_list():
    code = io.StringIO()

    store = Store(code)
    store['list'] = [1, 2, 3]
    assert store['list'] == [1, 2, 3]

    store['list'].append(5)
    assert store['list'][-1] == 5

    del store['list'][0]

    assert store['list'] == [2, 3, 5]

    assert store == safe_load_store_str(code.getvalue())
    assert repr(store) == repr(safe_load_store_str(code.getvalue()))

    store.close()


def test_list_clear():
    code = io.StringIO()

    store = Store(code)
    store['list'] = [1, 2, 3]
    assert store['list'] == [1, 2, 3]

    store['list'].clear()
    assert len(store['list']) == 0

    assert store == safe_load_store_str(code.getvalue())
    assert repr(store) == repr(safe_load_store_str(code.getvalue()))

    store.close()


def test_set():
    code = io.StringIO()

    store = Store(code)
    store['set'] = {1, 2, 3}
    assert store['set'] == {1, 2, 3}

    store['set'].add(5)

    assert 5 in store['set']

    store['set'].discard(5)

    assert 5 not in store['set']

    assert store == safe_load_store_str(code.getvalue())
    assert repr(store) == repr(safe_load_store_str(code.getvalue()))

    store.close()


def test_raise_on_slice():
    code = io.StringIO()

    store = Store(code)
    store['list'] = [1, 2, 3]

    with pytest.raises(AssertionError):
        store['list'][0:1] = [[1]]

    store.close()


def test_raise_after_unlink():
    code = io.StringIO()

    store = Store(code)
    store['list'] = [1, 2, 3]

    the_list = store['list']
    the_list.append(5)

    store['list'] = None

    with pytest.raises(AssertionError):
        the_list.append(6)


def test_del_unknown():
    code = io.StringIO()

    store = Store(code)
    store['list'] = []

    with pytest.raises(IndexError):
        del store['list'][1]

    with pytest.raises(KeyError):
        del store['set']

    store.close()


def test_list_set_unknown():
    code = io.StringIO()

    store = Store(code)
    store['list'] = []

    with pytest.raises(IndexError):
        store['list'][1] = 1


def test_nested_lists():
    code = io.StringIO()

    store = Store(code, dict(lists=[[[]]]))
    store['lists'][0][0].append(1)

    assert store == safe_load_store_str(code.getvalue())
    assert repr(store) == repr(safe_load_store_str(code.getvalue()))

    store.close()


def test_fail_on_chained_assignment():
    code = io.StringIO()

    store = Store(code)
    a = store['list'] = []
    a.append(1)

    assert a == [1]
    assert store['list'] == []
    assert a != store['list']

    store.close()


def test_list_duplicate_on_multiple_assignments():
    code = io.StringIO()

    store = Store(code)

    store['list'] = [1, 2]
    store['list2'] = store['list']
    store['list'].append(3)

    assert 3 not in store['list2']
    assert store['list'] != store['list2']
    assert store == safe_load_store_str(code.getvalue())
    assert repr(store) == repr(safe_load_store_str(code.getvalue()))

    store.close()


def test_map_duplicate_on_multiple_assignments():
    code = io.StringIO()

    store = Store(code)

    store['dict'] = dict(a=1)
    store['dict2'] = store['dict']
    store['dict']['b'] = 2

    assert store == safe_load_store_str(code.getvalue())
    assert repr(store) == repr(safe_load_store_str(code.getvalue()))

    store.close()


def test_relink_works():
    code = io.StringIO()

    store = Store(code)

    store['dict'] = dict(a=1)
    a = store['dict']

    del store['dict']

    store['dict2'] = a
    store['dict2']['b'] = 2

    assert store == safe_load_store_str(code.getvalue())
    assert repr(store) == repr(safe_load_store_str(code.getvalue()))

    store.close()
