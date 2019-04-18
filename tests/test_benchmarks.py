import pytest

import io
from blackhc.laaos import Store, safe_load_str
import time


@pytest.mark.parametrize("n", [
    (10**3),
    (10**4),
    (10**5),
    (10**6),
])
def test_n(n):
    print(f'\n-----{n} items-----')
    code = io.StringIO()

    start_time = time.monotonic()
    store = Store(code).root

    store['losses'] = []
    losses = store['losses']

    for i in range(n):
        losses.append(i)

    end_time = time.monotonic()
    write_duration = end_time - start_time
    print(f'Time for {n} write: {write_duration}s.')

    code_text = code.getvalue()
    store.close()

    start_time = time.monotonic()
    read_store = safe_load_str(code_text)
    end_time = time.monotonic()
    read_duration = end_time - start_time
    print(f'Time for {n} load: {read_duration}s.')

    code_size = len(code_text)
    write_bandwidth = code_size / write_duration
    read_bandwidth = code_size / read_duration
    print(f'Write bandwidth: {write_bandwidth / 2 ** 20} MB/s')
    print(f'Read bandwidth: {read_bandwidth / 2 **20} MB/s')
    print(f'Size: {code_size / 2**20} MB')

    assert read_store == store
