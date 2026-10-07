#!/bin/bash -eu

export PYDANTIC_DISABLE_PLUGINS=1

# Find and compile all Atheris fuzz harnesses across packages
for fuzzer in $(find packages -name 'test_fuzz_*.py'); do
    compile_python_fuzzer "$fuzzer"
    fuzzer_basename=$(basename -s .py "$fuzzer")
    sed -i '2i export PYDANTIC_DISABLE_PLUGINS=1' "$OUT/$fuzzer_basename"
done
