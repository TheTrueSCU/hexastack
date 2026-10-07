#!/bin/bash -eu

python3 -m pip install --upgrade pip
python3 -m pip install --ignore-requires-python .

# Find and compile all Atheris fuzz harnesses across packages
for fuzzer in $(find packages -name 'test_fuzz_*.py'); do
    compile_python_fuzzer "$fuzzer"
done
