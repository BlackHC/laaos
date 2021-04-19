import io

import laaos.torch
import laaos
import torch

def create_memory_store(initial_data=None, type_handlers=None):
    code = io.StringIO()
    store = laaos.Store(code, initial_data=initial_data, type_handlers=type_handlers)
    return store.root, code


def test_torch_tensor():
    store, code = create_memory_store(type_handlers=[laaos.torch.TensorHandler()])
    store["tensor"] = torch.as_tensor((1., 2.))

    assert code.getvalue() == "store = {}\nstore['tensor']=[1.0, 2.0]\n"

    store.close()

