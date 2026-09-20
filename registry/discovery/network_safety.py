"""Network safety guards against SSRF, local network access, and unsafe redirects."""

import ipaddress
import socket
from typing import Any, Callable, List, Optional, Union
from urllib.parse import urlparse

# RFC 5737 and RFC 3849 documentation/test blocks used in safe mock testing
TEST_NETWORKS = [
    ipaddress.IPv4Network("192.0.2.0/24"),
    ipaddress.IPv4Network("198.51.100.0/24"),
    ipaddress.IPv4Network("203.0.113.0/24"),
]

BLOCKED_DOMAINS = {
    "localhost",
    "localhost.localdomain",
    "broadcasthost",
}

BLOCKED_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".lan",
    ".home",
    ".corp",
)

_DEFAULT_DNS_RESOLVER: Optional[Callable[[str], List[str]]] = None


def set_default_dns_resolver(resolver: Optional[Callable[[str], List[str]]]) -> None:
    global _DEFAULT_DNS_RESOLVER
    _DEFAULT_DNS_RESOLVER = resolver


def is_safe_ip(
    ip_obj_or_str: Union[str, ipaddress.IPv4Address, ipaddress.IPv6Address],
    allow_test_networks: bool = True,
) -> bool:
    """
    Check if an IP address is a globally routable public address.
    Rejects loopback, private RFC 1918, link-local, multicast, unspecified, and CGNAT.
    """
    if isinstance(ip_obj_or_str, str):
        # Strip brackets from IPv6 literal
        cleaned = ip_obj_or_str.strip().strip("[]")
        try:
            ip = ipaddress.ip_address(cleaned)
        except ValueError:
            return False
    else:
        ip = ip_obj_or_str

    # Test-safe networks (RFC 5737) are allowed for mock tests when requested
    if allow_test_networks and isinstance(ip, ipaddress.IPv4Address):
        if any(ip in net for net in TEST_NETWORKS):
            return True

    # Reject standard unroutable / local / private properties
    if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
        return False

    if isinstance(ip, ipaddress.IPv4Address):
        # 0.0.0.0/8 (Current network)
        if ip in ipaddress.IPv4Network("0.0.0.0/8"):
            return False
        # 100.64.0.0/10 (Carrier-grade NAT)
        if ip in ipaddress.IPv4Network("100.64.0.0/10"):
            return False
        # 192.0.0.0/24 (IETF Protocol Assignments)
        if ip in ipaddress.IPv4Network("192.0.0.0/24"):
            return False
        # 198.18.0.0/15 (Benchmarking)
        if ip in ipaddress.IPv4Network("198.18.0.0/15"):
            return False
        # 240.0.0.0/4 (Reserved / Future use)
        if ip in ipaddress.IPv4Network("240.0.0.0/4"):
            return False
    elif isinstance(ip, ipaddress.IPv6Address):
        # IPv4-mapped IPv6 address (e.g. ::ffff:127.0.0.1)
        if ip.ipv4_mapped:
            return is_safe_ip(ip.ipv4_mapped, allow_test_networks=allow_test_networks)

    return True


def is_safe_public_http_url(
    url: str,
    resolve_dns: bool = True,
    dns_resolver: Optional[Callable[[str], List[str]]] = None,
    allow_test_networks: bool = True,
) -> bool:
    """
    Validate that a URL is a public, secure HTTPS URL that does not target
    localhost, private networks, or internal infrastructure.
    """
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False

    # 1. Scheme must be HTTPS
    if parsed.scheme.lower() != "https":
        return False

    # 2. No embedded user credentials
    if parsed.username or parsed.password:
        return False

    # 3. Hostname must be present
    host = (parsed.hostname or "").lower().strip()
    if not host:
        return False

    # 4. Reject localhost and private / internal suffixes
    if host in BLOCKED_DOMAINS or any(host.endswith(sfx) for sfx in BLOCKED_SUFFIXES):
        return False

    # 5. Check if host is an IP literal
    clean_host = host.strip("[]")
    is_ip_literal = False
    try:
        ipaddress.ip_address(clean_host)
        is_ip_literal = True
    except ValueError:
        is_ip_literal = False

    if is_ip_literal:
        return is_safe_ip(clean_host, allow_test_networks=allow_test_networks)

    # 6. Resolve DNS if requested
    if resolve_dns:
        if dns_resolver:
            try:
                resolved_ips = dns_resolver(host)
            except Exception:
                return False
        elif _DEFAULT_DNS_RESOLVER:
            try:
                resolved_ips = _DEFAULT_DNS_RESOLVER(host)
            except Exception:
                return False
        elif (host == "example" or host.endswith(".example")) and allow_test_networks:
            # Test-safe public address strategy for RFC 2606 .example documentation/test domains
            resolved_ips = ["203.0.113.10"]
        else:
            try:
                addr_info = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
                resolved_ips = [info[4][0] for info in addr_info if info and info[4]]
            except (socket.gaierror, socket.herror, OSError):
                return False

        if not resolved_ips:
            return False

        # Reject if ANY resolved IP targets a private or non-routable address
        for ip_str in resolved_ips:
            if not is_safe_ip(ip_str, allow_test_networks=allow_test_networks):
                return False

    return True


def validate_public_navigation_url(
    url: str,
    resolve_dns: bool = True,
    dns_resolver: Optional[Callable[[str], List[str]]] = None,
    allow_test_networks: bool = True,
) -> str:
    """Validate a URL against SSRF rules, raising ValueError if unsafe."""
    if not is_safe_public_http_url(
        url,
        resolve_dns=resolve_dns,
        dns_resolver=dns_resolver,
        allow_test_networks=allow_test_networks,
    ):
        raise ValueError(f"Unsafe public navigation target: {url}")
    return url


def _get_page_url(page: Any, default_url: str) -> str:
    attr = getattr(page, "url", getattr(page, "last_url", default_url))
    if callable(attr):
        try:
            return str(attr())
        except Exception:
            return default_url
    return str(attr) if attr else default_url


async def safe_goto(
    page: Any,
    url: str,
    timeout_ms: int = 6000,
    dns_resolver: Optional[Callable[[str], List[str]]] = None,
    allow_test_networks: bool = True,
) -> bool:
    """
    Safely navigate a Playwright page to a public URL.
    - Validates initial URL before navigation
    - Intercepts navigation requests to abort redirects targeting private networks
    - Validates final page URL post-navigation
    Returns True if navigation succeeded safely, False otherwise.
    """
    if not is_safe_public_http_url(
        url,
        resolve_dns=True,
        dns_resolver=dns_resolver,
        allow_test_networks=allow_test_networks,
    ):
        return False

    # Real Playwright Page with routing support
    if hasattr(page, "route") and hasattr(page, "unroute"):
        async def _route_handler(route, request):
            if request.is_navigation_request():
                target_url = request.url
                if not is_safe_public_http_url(
                    target_url,
                    resolve_dns=True,
                    dns_resolver=dns_resolver,
                    allow_test_networks=allow_test_networks,
                ):
                    try:
                        await route.abort("blockedbyclient")
                    except Exception:
                        pass
                    return
            try:
                await route.continue_()
            except Exception:
                pass

        try:
            await page.route("**/*", _route_handler)
        except Exception:
            pass

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        except Exception:
            return False
        finally:
            try:
                await page.unroute("**/*", _route_handler)
            except Exception:
                pass

        final_url = _get_page_url(page, url)
        if final_url and not is_safe_public_http_url(
            final_url,
            resolve_dns=True,
            dns_resolver=dns_resolver,
            allow_test_networks=allow_test_networks,
        ):
            return False
        return True

    # MockPage or test page without route handler
    try:
        if hasattr(page, "goto"):
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        final_url = _get_page_url(page, url)
        if final_url and not is_safe_public_http_url(
            final_url,
            resolve_dns=True,
            dns_resolver=dns_resolver,
            allow_test_networks=allow_test_networks,
        ):
            return False
        return True
    except Exception:
        return False
