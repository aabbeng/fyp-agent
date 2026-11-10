# Tests

The suite uses Python's built-in `unittest` framework, so no third-party test dependency is required.

Run all tests from the repository root:

```powershell
python -m unittest discover -s tests -v
```

`scenarios.json` defines the initial 20-case evaluation matrix. The executable multi-step scenario runner will be added after these individual tools form a stable baseline.
