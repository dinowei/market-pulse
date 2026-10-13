"""Client address behind a known chain of proxies (H-23, ADR-020).

With N trusted proxies, each one appends the address of its own peer to X-Forwarded-For,
so the client is the N-th entry from the right. Everything to the left of it was written
by the client and is ignored, which makes the address impossible to forge by prepending.
Without trusted hops, the header is ignored and the socket peer is the client.
"""

from ipaddress import ip_address

from starlette.requests import Request

from app.core.config import get_settings


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    hops = get_settings().trusted_proxy_hops
    if hops == 0:
        return peer
    entries = [
        item.strip()
        for value in request.headers.getlist("x-forwarded-for")
        for item in value.split(",")
        if item.strip()
    ]
    if len(entries) < hops:
        return peer
    try:
        return str(ip_address(entries[-hops]))
    except ValueError:
        return peer
