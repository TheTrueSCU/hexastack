from hexastack_core.ports.ratelimit import RateLimiterPort


class MockRateLimiter(RateLimiterPort):
    def __init__(self) -> None:
        self.hits_recorded: list[str] = []

    def hit(self, key: str, limit: str) -> bool:
        self.hits_recorded.append(f"{key}:{limit}")
        return True

    def get_reset_window(self, key: str, limit: str) -> int:
        return 60

    def clear(self, key: str | None = None) -> None:
        self.hits_recorded.clear()


def test_rate_limiter_port_contract():
    limiter: RateLimiterPort = MockRateLimiter()
    assert limiter.hit("ip:1.2.3.4", "10/minute") is True
    assert limiter.get_reset_window("ip:1.2.3.4", "10/minute") == 60
    limiter.clear()
    assert len(limiter.hits_recorded) == 0
