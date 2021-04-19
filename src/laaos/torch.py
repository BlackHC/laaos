# We do not specify as a requirement, as this is an "extension" file.
import torch

import laaos


class TensorHandler(laaos.TypeHandler):
    def supports(self, obj):
        return isinstance(obj, torch.Tensor)

    def wrap(self, obj, wrap):
        return obj.tolist()

    def repr(self, obj, repr, store):
        # This will never be called.
        return repr(obj.tolist())


TypeHandlers = [TensorHandler()]
