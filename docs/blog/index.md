# Engineering Blog

> Articles from the creator of Hexastack, cross-posted from
> [DEV.to](https://dev.to) and [Medium](https://medium.com).
> Each article is a standalone deep-dive into a specific layer, pattern, or
> decision in Hexastack's design.

---

## Series: Building Production Python with Hexastack

A twelve-article series covering hexagonal architecture, CQRS, distributed
events, AI-native backends, compliance, and the developer tooling that makes
it all maintainable at speed — including with AI coding assistants.

| # | Title | Topic | DEV.to | Medium |
|---|-------|-------|--------|--------|
| 10 | What 20 Years of Python Taught Me About Building in the AI Era | Manifesto | — | — |
| 0 | What Is Hexastack? | Overview | — | — |
| 6 | Your FastAPI Service, Now AI-Native: LLM Agents + MCP | AI / MCP | — | — |
| 5 | Managing 17 Python Packages: The `uv` Workspace Monorepo Pattern | Tooling | — | — |
| 1 | Stop Writing Spaghetti FastAPI: Hexagonal Architecture + CQRS | Architecture | — | — |
| 3 | 90%+ Coverage Isn't Enough: Mutation Testing + OpenSSF Gold | Quality | — | — |
| 2 | The Dual-Write Trap: Transactional Outbox with NATS JetStream | Events | — | — |
| 7 | Beyond `if os.getenv`: Feature Flags with OpenFeature | Flags | — | — |
| 8 | Logging and Tracing That Don't Fight Your Architecture | Observability | — | — |
| 11 | Building for HIPAA and FedRAMP: Architecture as Compliance | Compliance | — | — |
| 9 | gRPC and REST from the Same Service, Without Spaghetti | gRPC | — | — |
| 4 | Reactive DevTools in Python with NiceGUI | DevTools | — | — |

> URLs populate automatically as articles are published via `uv run medium-publish <slug> --publish`.

---

## Cross-Post Strategy

All articles are published to **DEV.to first** (canonical source), then
syndicated to **Medium** using Medium's Import feature, which auto-sets
the canonical URL back to DEV.to for SEO correctness.

```
<drafts>/<slug>.md  →  DEV.to (canonical)  →  Medium (syndicated)
                            ↓
                docs/blog/index.md (this page)
```
