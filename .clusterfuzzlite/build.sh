#!/bin/bash -eu

python3 -m pip install --upgrade pip
python3 -m pip install uv
uv pip install --system -e "packages/hexastack[all]" || python3 -m pip install -e "packages/hexastack[all]" || true

# Find all Atheris fuzz harnesses across packages
for fuzzer in $(find packages -name 'test_fuzz_*.py'); do
    fuzzer_basename=$(basename -s .py "$fuzzer")
    cp "$fuzzer" "$OUT/${fuzzer_basename}.py"
    cat <<EOF > "$OUT/${fuzzer_basename}"
#!/bin/sh
exec python3 "$OUT/${fuzzer_basename}.py" "\$@"
EOF
    chmod +x "$OUT/${fuzzer_basename}"
done
