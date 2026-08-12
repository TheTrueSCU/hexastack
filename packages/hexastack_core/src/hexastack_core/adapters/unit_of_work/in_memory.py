from hexastack_core.ports.unit_of_work import UnitOfWorkPort


class InMemoryUnitOfWork(UnitOfWorkPort):
    """In-memory Unit of Work adapter tracking transaction states for tests and mocks.

    Notes/Architectural Intent:
        Records commit and rollback events and counters in memory to allow unit tests
        to verify transactional lifecycle behavior without database dependencies.
    """

    def __init__(self, reraise: bool = False) -> None:
        """Initialize in-memory unit of work with counters and flags.

        Args:
            reraise: If True, wraps unhandled exceptions into UnitOfWorkError on context exit.
        """
        super().__init__(reraise=reraise)
        self.committed: bool = False
        self.rolled_back: bool = False
        self.commit_count: int = 0
        self.rollback_count: int = 0

    def clear(self) -> None:
        """Reset transaction state flags and execution counters.

        Returns:
            None.

        Raises:
            None.
        """
        self.committed = False
        self.rolled_back = False
        self.commit_count = 0
        self.rollback_count = 0

    def commit(self) -> None:
        """Commit the in-memory transaction and record execution.

        Returns:
            None.

        Raises:
            None.
        """
        self.committed = True
        self.commit_count += 1

    def rollback(self) -> None:
        """Roll back the in-memory transaction and record execution.

        Returns:
            None.

        Raises:
            None.
        """
        self.rolled_back = True
        self.rollback_count += 1
