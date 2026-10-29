## Step 3: Observing Invariant Rejection

Now let's simulate what happens when a client attempts to submit an unbalanced transaction (e.g. Debit \$500.00 vs Credit \$450.00).

Run the interactive python assertion:

```bash
uv run python -c "
from decimal import Decimal
from financial_ledger.domain.models import Transaction, Entry, AccountType

try:
    tx = Transaction(
        description='Unbalanced Payment',
        entries=[
            Entry(account_id='cash-01', account_type=AccountType.ASSET, amount=Decimal('500.00'), is_debit=True),
            Entry(account_id='ar-01', account_type=AccountType.ASSET, amount=Decimal('450.00'), is_debit=False),
        ]
    )
    print('ERROR: Unbalanced transaction was allowed!')
except ValueError as e:
    print('SUCCESS: Domain invariant rejected unbalanced transaction:')
    print(f'-> {e}')
"
```{{exec}}

The domain rejects the invalid transaction at construction time, preventing corrupted entries from reaching persistence adapters!
