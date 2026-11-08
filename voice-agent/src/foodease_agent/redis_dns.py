"""Optional per-Redis DNS resolution; preserve original TLS SNI and hostname checks."""

import ssl

from redis.asyncio.connection import SSLConnection
from redis.exceptions import ConnectionError as RedisConnectionError


class ResolvedSSLConnection(SSLConnection):
    def __init__(self, *, resolver, **kwargs):
        self._resolver = resolver
        self._resolved_host = None
        super().__init__(**kwargs)

    def _connection_arguments(self):
        arguments = dict(super()._connection_arguments())
        if self._resolved_host is not None:
            arguments["host"] = self._resolved_host
            arguments["server_hostname"] = self.host
        return arguments

    async def _connect(self):
        try:
            answer = await self._resolver.resolve(self.host, "A", lifetime=2, search=False)
            addresses = [str(record.address) for record in answer]
            if not addresses:
                raise ValueError("No address")
        except Exception:
            raise RedisConnectionError(
                "Redis DNS resolution failed with configured resolver"
            ) from None
        try:
            for index, address in enumerate(addresses):
                self._resolved_host = address
                try:
                    await super()._connect()
                    return
                except ssl.SSLError:
                    raise  # Never hide/bypass a certificate or hostname failure.
                except (TimeoutError, OSError):
                    if index == len(addresses) - 1:
                        raise
        finally:
            self._resolved_host = None
