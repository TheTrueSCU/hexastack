## Step 2: Posting Balanced Transactions

Let's dispatch a balanced transaction through the CQRS command bus transferring \$500.00 from Operating Cash to Accounts Receivable.

Run the test suite or dispatch script:

```bash
uv run hexaqual test run -e financial-ledger
```{{exec}}

Notice that:
- 100% of property-based Hypothesis tests verify invariant conservation across thousands of randomly generated multi-leg entries.
- The dual-implementation SQLite repository matches the naive Python oracle with mathematical exactness ($f_{\text{prod}} \equiv f_{\text{oracle}}$).
