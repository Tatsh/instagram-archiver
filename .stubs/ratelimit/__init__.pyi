from ratelimit.decorators import RateLimitDecorator, sleep_and_retry

limits = RateLimitDecorator

__all__ = ('limits', 'sleep_and_retry')
