## Step 1: The Double-Entry Invariant

In financial engineering, floating-point numbers (`float`) are prohibited because rounding errors cause subtle balance discrepancies. Hexastack enforces `Decimal` arithmetic and strict balance invariants at the entity boundary:

$$\sum \text{Debits} \equiv \sum \text{Credits}$$

Navigate to the financial ledger example project:

```bash
cd examples/financial-ledger
```{{exec}}

Inspect the domain invariant check in the `Transaction` aggregate:

```bash
cat src/financial_ledger/domain/models.py
```{{exec}}

Notice how the `Transaction` entity validates in `__post_init__` that total debits equal total credits before allowing instantiation.
