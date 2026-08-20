# Tutorial 4: Event-Driven Architecture with Outbox & CloudEvents

In this chapter, you will publish domain events (e.g., `TodoCreatedEvent`, `TodoCompletedEvent`) to notify external services or trigger reminder notifications using `hexastack-events` and the **Transactional Outbox Pattern**.

---

## 1. Defining Pure Domain Events

Create `src/todo_app/domain/events.py`:

```python
# src/todo_app/domain/events.py
from hexastack_core.domain import Event

class TodoCreatedEvent(Event):
    """Published whenever a new To-Do task is successfully created."""

    todo_id: str
    title: str
    priority: str


class TodoCompletedEvent(Event):
    """Published whenever a To-Do task transitions to completed."""

    todo_id: str
```

---

## 2. Emitting Events from CQRS Handlers

Update `src/todo_app/infra/handlers.py` to publish events via the injected `EventBusPort`:

```python
# src/todo_app/infra/handlers.py
from hexastack_core.ports.events import EventBusPort
from todo_app.domain.events import TodoCompletedEvent, TodoCreatedEvent

def handle_create_todo(
    cmd: CreateTodoCommand,
    repo: TodoRepositoryPort,
    events: EventBusPort,
) -> TodoItemDTO:
    item = TodoItem(title=cmd.title, description=cmd.description, priority=cmd.priority)
    repo.save(item)

    # Publish domain event
    events.publish(
        TodoCreatedEvent(
            todo_id=item.id,
            title=item.title,
            priority=item.priority,
        )
    )
    return _to_dto(item)
```

---

## 3. Subscribing to Events (Async Notification Worker)

Create event subscribers in `src/todo_app/adapters/driven/notifications.py`:

```python
# src/todo_app/adapters/driven/notifications.py
from hexastack_cqrs.infra.decorators import event_listener
from todo_app.domain.events import TodoCreatedEvent

@event_listener(TodoCreatedEvent)
def send_task_creation_notification(event: TodoCreatedEvent) -> None:
    """Send email/push notification when a high-priority task is created."""
    if event.priority == "high":
        print(f"🚨 [URGENT NOTIFICATION] New high priority task created: '{event.title}' (ID: {event.todo_id})")
```

---

## 4. Guaranteed Delivery via Transactional Outbox

With `hexastack-events[outbox]`, domain events are committed in the same database transaction as the entity state update, ensuring **zero lost events** even during process crashes.
