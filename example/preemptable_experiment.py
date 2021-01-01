from laaos import open_file_store

initial_data = dict(config=dict(dataset="MNIST", learning_rate=1e-4, seed=1337), losses=[])

store = open_file_store("experiment_result", suffix="", initial_data=initial_data)

if store["config"] != initial_data["config"]:
    raise ValueError("Experiment mismatch!")

print("Output file: ", store.uri)

losses = store["losses"]

for i in range(len(losses), 10):
    print("Epoch ", i)
    losses.append(1 / (i + 1))

    if i % 3 == 0:
        raise SystemError("Preemption!")

store.close()
