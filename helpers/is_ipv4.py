from ipaddress import ip_address
from helpers.logger import logger
import socket


def is_ipv4(value: str | None):
    """
    Check if the given value is a valid IPv4 address.
    """
    try:
        if value is None or value.strip() == "":
            logger.info("Please provide an IPv4 address.")
        ip = ip_address(value)
        logger.debug(ip)
        return ip.version == 4
    except ValueError:
        return False


def get_ipv4_type_a():
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    ips = socket.gethostbyname_ex(hostname)[2]
    for ip in ips:
        if ip.startswith("10."):
            local_ip = ip

    return local_ip
