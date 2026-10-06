"""CQRS Command and Query handlers executing domain operations with injected ports."""

from __future__ import annotations

from hexastack_core.adapters.notification import InMemoryNotificationAdapter
from hexastack_core.domain.exceptions import PermissionDeniedError
from hexastack_core.ports.notification import (
    NotificationPort,
    NotificationPriority,
)
from hexastack_cqrs.infra.decorators import command_handler, query_handler

from todo_app.domain.commands import (
    CompleteTodoCommand,
    CreateTodoCommand,
    DeleteTodoCommand,
    GetTodoQuery,
    ListTodosQuery,
    TodoItemDTO,
)
from todo_app.domain.models import TodoItem, TodoNotFoundError
from todo_app.ports.repositories import TodoRepositoryPort

_DEFAULT_NOTIFIER = InMemoryNotificationAdapter()


def _to_dto(item: TodoItem) -> TodoItemDTO:
    return TodoItemDTO(
        id=item.id,
        title=item.title,
        owner_id=item.owner_id,
        description=item.description,
        priority=item.priority,
        completed=item.completed,
    )


@command_handler(CreateTodoCommand)
class CreateTodoHandler:
    """Handler creating a new To-Do item and saving via repository port."""

    def __init__(self, repo: TodoRepositoryPort) -> None:
        self.repo = repo

    def __call__(self, cmd: CreateTodoCommand) -> TodoItemDTO:
        """Execute command to create and persist a new To-Do task.

        Args:
            cmd: Command specifying title, owner, and task metadata.

        Returns:
            Data transfer object of the newly created To-Do item.

        Raises:
            None.

        Notes/Architectural Intent:
            Converts command message into pure domain entity and persists via port.
        """
        item = TodoItem(
            title=cmd.title,
            owner_id=cmd.owner_id,
            description=cmd.description,
            priority=cmd.priority,
        )
        self.repo.save(item)
        return _to_dto(item)


@command_handler(CompleteTodoCommand)
class CompleteTodoHandler:
    """Handler marking a To-Do item as completed."""

    def __init__(self, repo: TodoRepositoryPort) -> None:
        self.repo = repo

    def __call__(self, cmd: CompleteTodoCommand) -> TodoItemDTO:
        """Mark a To-Do item as completed after validating requester permissions.

        Args:
            cmd: Command containing todo ID and requester identity.

        Returns:
            Updated To-Do data transfer object.

        Raises:
            TodoNotFoundError: If the target item is not found.
            PermissionDeniedError: If requester is not the owner or an admin.

        Notes/Architectural Intent:
            Enforces aggregate boundary rules and entity lifecycle transitions.
        """
        item = self.repo.get_by_id(cmd.todo_id)
        if item is None:
            raise TodoNotFoundError(cmd.todo_id)

        # Domain ownership check
        if not cmd.is_admin and item.owner_id != cmd.requester_id:
            raise PermissionDeniedError(
                f"Forbidden: '{cmd.requester_id}' cannot complete task owned by '{item.owner_id}'."
            )

        item.mark_completed()
        self.repo.save(item)
        return _to_dto(item)


@command_handler(DeleteTodoCommand)
class DeleteTodoHandler:
    """Handler deleting a To-Do item with ownership verification and admin alerting."""

    def __init__(
        self,
        repo: TodoRepositoryPort,
        notifier: NotificationPort = _DEFAULT_NOTIFIER,
    ) -> None:
        self.repo = repo
        self.notifier = notifier

    def __call__(self, cmd: DeleteTodoCommand) -> bool:
        """Delete target To-Do item and dispatch security notifications on admin overrides.

        Args:
            cmd: Command containing todo ID and requester identity.

        Returns:
            True if the task was successfully deleted.

        Raises:
            TodoNotFoundError: If the task is not found.
            PermissionDeniedError: If requester lacks ownership or admin authorization.

        Notes/Architectural Intent:
            Publishes audit notifications through the outbound notification port.
        """
        item = self.repo.get_by_id(cmd.todo_id)
        if item is None:
            raise TodoNotFoundError(cmd.todo_id)

        # Domain ownership check
        if not cmd.is_admin and item.owner_id != cmd.requester_id:
            raise PermissionDeniedError(
                f"Forbidden: '{cmd.requester_id}' cannot delete task owned by '{item.owner_id}'."
            )

        deleted = self.repo.delete(cmd.todo_id)
        if not deleted:
            raise TodoNotFoundError(cmd.todo_id)

        # If admin deleted another user's task, dispatch domain event notification
        if cmd.is_admin and item.owner_id != cmd.requester_id:
            self.notifier.notify(
                title="⚠️ Admin Task Deletion Notice",
                body=f"Admin '{cmd.requester_id}' deleted task '{item.title}' owned by '{item.owner_id}'.",
                priority=NotificationPriority.HIGH,
                tags=["audit", "admin-action"],
            )

        return True


@query_handler(ListTodosQuery)
class ListTodosHandler:
    """Handler querying To-Do items from repository."""

    def __init__(self, repo: TodoRepositoryPort) -> None:
        self.repo = repo

    def __call__(self, query: ListTodosQuery) -> list[TodoItemDTO]:
        """Query repository for To-Do items matching ownership and completion filters.

        Args:
            query: Query criteria including optional owner and completion filters.

        Returns:
            List of matching To-Do data transfer objects.

        Raises:
            None.

        Notes/Architectural Intent:
            Projects domain entities to read-only DTOs.
        """
        items = self.repo.list_all(completed=query.completed_only)
        if query.owner_id is not None:
            items = [i for i in items if i.owner_id == query.owner_id]
        return [_to_dto(i) for i in items]


@query_handler(GetTodoQuery)
class GetTodoHandler:
    """Handler fetching single To-Do item."""

    def __init__(self, repo: TodoRepositoryPort) -> None:
        self.repo = repo

    def __call__(self, query: GetTodoQuery) -> TodoItemDTO:
        """Fetch single To-Do item by unique ID.

        Args:
            query: Query specifying todo ID.

        Returns:
            To-Do data transfer object.

        Raises:
            TodoNotFoundError: If the requested item does not exist.

        Notes/Architectural Intent:
            Encapsulates entity retrieval and projection.
        """
        item = self.repo.get_by_id(query.todo_id)
        if item is None:
            raise TodoNotFoundError(query.todo_id)
        return _to_dto(item)


# Functional helpers for direct unit testing without DI container
def handle_create_todo(cmd: CreateTodoCommand, repo: TodoRepositoryPort) -> TodoItemDTO:
    """Functional convenience helper to create a To-Do item.

    Args:
        cmd: Create command.
        repo: Repository port instance.

    Returns:
        Created To-Do DTO.

    Raises:
        None.
    """
    return CreateTodoHandler(repo)(cmd)


def handle_complete_todo(
    cmd: CompleteTodoCommand, repo: TodoRepositoryPort
) -> TodoItemDTO:
    """Functional convenience helper to mark a To-Do item as completed.

    Args:
        cmd: Complete command.
        repo: Repository port instance.

    Returns:
        Completed To-Do DTO.

    Raises:
        TodoNotFoundError: If item does not exist.
        PermissionDeniedError: If requester lacks permission.
    """
    return CompleteTodoHandler(repo)(cmd)


def handle_delete_todo(
    cmd: DeleteTodoCommand,
    repo: TodoRepositoryPort,
    notifier: NotificationPort = _DEFAULT_NOTIFIER,
) -> bool:
    """Functional convenience helper to delete a To-Do item.

    Args:
        cmd: Delete command.
        repo: Repository port instance.
        notifier: Optional notification port instance.

    Returns:
        True if deleted successfully.

    Raises:
        TodoNotFoundError: If item does not exist.
        PermissionDeniedError: If requester lacks permission.
    """
    return DeleteTodoHandler(repo, notifier)(cmd)


def handle_list_todos(
    query: ListTodosQuery, repo: TodoRepositoryPort
) -> list[TodoItemDTO]:
    """Functional convenience helper to list To-Do items.

    Args:
        query: List query.
        repo: Repository port instance.

    Returns:
        List of To-Do DTOs.

    Raises:
        None.
    """
    return ListTodosHandler(repo)(query)


def handle_get_todo(query: GetTodoQuery, repo: TodoRepositoryPort) -> TodoItemDTO:
    """Functional convenience helper to retrieve a single To-Do item.

    Args:
        query: Get query.
        repo: Repository port instance.

    Returns:
        To-Do DTO.

    Raises:
        TodoNotFoundError: If item does not exist.
    """
    return GetTodoHandler(repo)(query)


__all__ = [
    "CompleteTodoHandler",
    "CreateTodoHandler",
    "DeleteTodoHandler",
    "GetTodoHandler",
    "handle_complete_todo",
    "handle_create_todo",
    "handle_delete_todo",
    "handle_get_todo",
    "handle_list_todos",
    "ListTodosHandler",
]
