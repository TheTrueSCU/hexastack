## Step 2: Adding CQRS Commands & Adapters

Hexastack provides dynamic scaffolding commands to generate strongly-typed CQRS commands and queries with automatic unit test symmetry.

Run the following command to scaffold a `CreateOrder` command:

```bash
uv tool run hexastack add command CreateOrder
```{{exec}}

Inspect the generated command and its matching unit test:

```bash
cat src/order_service/domain/commands.py
cat tests/unit/domain/test_commands.py
```{{exec}}

Notice that Hexastack automatically generated a matching unit test in `tests/unit/` to maintain 1:1 test parity!
