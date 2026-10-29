## Step 1: Scaffold a New Service

Let's start by creating a new microservice using the minimal template.

Run the following command in the terminal:

```bash
uv tool run hexastack new --template minimal order-service
cd order-service
```{{exec}}

Now inspect the scaffolded directory structure:

```bash
tree -L 3 src/
```{{exec}}

Notice how Hexastack cleanly separates concerns into 4 strict hexagonal tiers:
- `domain/`: Pure business models and domain rules with 0 dependencies.
- `ports/`: Abstract interfaces defining driving and driven contracts.
- `adapters/`: Concrete technological implementations (FastAPI, SQLite, Redis).
- `infra/`: Dependency injection and application bootstrapping.
