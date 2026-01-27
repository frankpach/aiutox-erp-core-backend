"""URL validation utilities for SSRF protection."""

import ipaddress
import socket
from urllib.parse import urlparse

from fastapi import status

from app.core.exceptions import APIException

# Private IP ranges (RFC 1918, RFC 4193, etc.)
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 private
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]

# Blocked hostnames
BLOCKED_HOSTNAMES = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "[::]",
    "metadata.google.internal",  # GCP metadata
    "169.254.169.254",  # AWS/Azure metadata
]


def is_private_ip(ip_str: str) -> bool:
    """Check if IP address is private/internal.

    Args:
        ip_str: IP address string

    Returns:
        True if IP is private, False otherwise
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        return any(ip in network for network in PRIVATE_IP_RANGES)
    except ValueError:
        return False


def validate_url_safe(url: str) -> tuple[bool, str]:
    """Validate URL is safe (not SSRF vulnerable).

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url or not isinstance(url, str):
        return False, "URL is required and must be a string"

    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    # Require HTTP/HTTPS
    if parsed.scheme not in ["http", "https"]:
        return False, "Only HTTP/HTTPS URLs are allowed"

    # Check hostname
    hostname = parsed.hostname
    if not hostname:
        return False, "URL must have a valid hostname"

    # Block dangerous hostnames
    if hostname.lower() in BLOCKED_HOSTNAMES:
        return False, f"Access to {hostname} is not allowed"

    # Resolve and check IP
    try:
        ip = socket.gethostbyname(hostname)
        if is_private_ip(ip):
            return False, "Access to private IP addresses is not allowed"
    except socket.gaierror:
        return False, f"Could not resolve hostname: {hostname}"

    return True, ""


def validate_file_url(file_url: str) -> None:
    """Validate file URL for SSRF protection.

    Args:
        file_url: File URL to validate

    Raises:
        APIException if URL is not safe
    """
    is_valid, error_msg = validate_url_safe(file_url)
    if not is_valid:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_FILE_URL",
            message=f"Invalid file URL: {error_msg}",
        )
