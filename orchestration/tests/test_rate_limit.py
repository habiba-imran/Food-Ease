from foodease_session.rate_limit import RateLimiter


def test_rate_limiter_blocks_after_max() -> None:
    lim = RateLimiter(max_requests=3, window_seconds=60)
    assert lim.allow("a")
    assert lim.allow("a")
    assert lim.allow("a")
    assert not lim.allow("a")
    assert lim.allow("b")
