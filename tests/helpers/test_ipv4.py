import socket
from unittest.mock import MagicMock, patch

import pytest

from helpers.ipv4 import get_ipv4, is_ipv4


class TestIsIPv4:
    """Test cases for the is_ipv4 function."""

    def test_valid_ipv4_addresses(self):
        """Test with valid IPv4 addresses."""
        valid_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "8.8.8.8",
            "127.0.0.1",
            "0.0.0.0",
            "255.255.255.255",
        ]

        for ip in valid_ips:
            assert is_ipv4(ip) is True, f"Expected {ip} to be valid IPv4"

    def test_invalid_ipv4_addresses(self):
        """Test with invalid IPv4 addresses."""
        invalid_ips = [
            "256.256.256.256",  # Numbers too high
            "192.168.1",  # Missing octet
            "192.168.1.1.1",  # Too many octets
            "192.168.1.a",  # Non-numeric
            "192.168.-1.1",  # Negative number
            "192.168.1.01",  # Leading zero
            "192 168 1 1",  # Spaces instead of dots
            "192.168.1.",  # Trailing dot
            ".192.168.1.1",  # Leading dot
            "",  # Empty string
            "not_an_ip",  # Random string
            "http://192.168.1.1",  # URL format
        ]

        for ip in invalid_ips:
            assert is_ipv4(ip) is False, f"Expected {ip} to be invalid IPv4"

    def test_ipv6_addresses(self):
        """Test that IPv6 addresses return False."""
        ipv6_addresses = [
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "2001:db8:85a3::8a2e:370:7334",
            "::1",
            "fe80::1",
        ]

        for ip in ipv6_addresses:
            assert is_ipv4(ip) is False, f"Expected IPv6 {ip} to return False"

    def test_none_value(self):
        """Test with None value."""
        assert is_ipv4(None) is False

    def test_whitespace_values(self):
        """Test with whitespace values."""
        whitespace_values = [
            "   ",  # Spaces
            "\t",  # Tab
            "\n",  # Newline
            "\r\n",  # Windows newline
            "",  # Empty string
        ]

        for value in whitespace_values:
            assert (
                is_ipv4(value) is False
            ), f"Expected whitespace '{repr(value)}' to be invalid"

    def test_edge_cases(self):
        """Test edge cases and boundary values."""
        edge_cases = [
            ("0.0.0.0", True),  # All zeros
            ("255.255.255.255", True),  # All max values
            ("127.0.0.1", True),  # Localhost
            ("192.168.1.1 ", False),  # Trailing space
            (" 192.168.1.1", False),  # Leading space
            ("192.168.1.1\n", False),  # Trailing newline
        ]

        for ip, expected in edge_cases:
            assert is_ipv4(ip) is expected, f"Expected {ip} to return {expected}"


class TestGetIPv4:
    """Test cases for the get_ipv4 function."""

    @patch("socket.gethostname")
    @patch("socket.gethostbyname")
    @patch("socket.gethostbyname_ex")
    def test_get_ipv4_with_10_x_preference(
        self, mock_gethostbyname_ex, mock_gethostbyname, mock_gethostname
    ):
        """Test that function prefers 10.x.x.x addresses when available."""
        mock_gethostname.return_value = "test-hostname"
        mock_gethostbyname.return_value = "192.168.1.100"
        mock_gethostbyname_ex.return_value = (
            "test-hostname",
            [],
            ["192.168.1.100", "10.0.0.50", "172.16.0.10"],
        )

        result = get_ipv4()
        assert result == "10.0.0.50", "Should prefer 10.x.x.x address"

    @patch("socket.gethostname")
    @patch("socket.gethostbyname")
    @patch("socket.gethostbyname_ex")
    def test_get_ipv4_no_10_x_address(
        self, mock_gethostbyname_ex, mock_gethostbyname, mock_gethostname
    ):
        """Test fallback when no 10.x.x.x address is available."""
        mock_gethostname.return_value = "test-hostname"
        mock_gethostbyname.return_value = "192.168.1.100"
        mock_gethostbyname_ex.return_value = (
            "test-hostname",
            [],
            ["192.168.1.100", "172.16.0.10"],
        )

        result = get_ipv4()
        assert (
            result == "192.168.1.100"
        ), "Should return default IP when no 10.x.x.x available"

    @patch("socket.gethostname")
    @patch("socket.gethostbyname")
    @patch("socket.gethostbyname_ex")
    def test_get_ipv4_multiple_10_x_addresses(
        self, mock_gethostbyname_ex, mock_gethostbyname, mock_gethostname
    ):
        """Test behavior with multiple 10.x.x.x addresses."""
        mock_gethostname.return_value = "test-hostname"
        mock_gethostbyname.return_value = "192.168.1.100"
        mock_gethostbyname_ex.return_value = (
            "test-hostname",
            [],
            ["192.168.1.100", "10.0.0.50", "10.1.1.100", "172.16.0.10"],
        )

        result = get_ipv4()
        # Should return the last 10.x.x.x address found (based on implementation)
        assert result == "10.1.1.100", "Should return last 10.x.x.x address found"

    @patch("socket.gethostname")
    @patch("socket.gethostbyname")
    @patch("socket.gethostbyname_ex")
    def test_get_ipv4_empty_ip_list(
        self, mock_gethostbyname_ex, mock_gethostbyname, mock_gethostname
    ):
        """Test behavior with empty IP list."""
        mock_gethostname.return_value = "test-hostname"
        mock_gethostbyname.return_value = "127.0.0.1"
        mock_gethostbyname_ex.return_value = ("test-hostname", [], [])

        result = get_ipv4()
        assert result == "127.0.0.1", "Should return default IP when list is empty"

    @patch("socket.gethostname")
    @patch("socket.gethostbyname")
    @patch("socket.gethostbyname_ex")
    def test_get_ipv4_localhost_only(
        self, mock_gethostbyname_ex, mock_gethostbyname, mock_gethostname
    ):
        """Test behavior with only localhost address."""
        mock_gethostname.return_value = "localhost"
        mock_gethostbyname.return_value = "127.0.0.1"
        mock_gethostbyname_ex.return_value = ("localhost", [], ["127.0.0.1"])

        result = get_ipv4()
        assert result == "127.0.0.1", "Should handle localhost correctly"

    @patch("socket.gethostname")
    @patch("socket.gethostbyname")
    @patch("socket.gethostbyname_ex")
    def test_get_ipv4_socket_error_handling(
        self, mock_gethostbyname_ex, mock_gethostbyname, mock_gethostname
    ):
        """Test error handling when socket operations fail."""
        mock_gethostname.side_effect = socket.error("Network error")

        with pytest.raises(socket.error):
            get_ipv4()

    @patch("socket.gethostname")
    @patch("socket.gethostbyname")
    @patch("socket.gethostbyname_ex")
    def test_get_ipv4_real_network_simulation(
        self, mock_gethostbyname_ex, mock_gethostbyname, mock_gethostname
    ):
        """Test with realistic network configuration."""
        mock_gethostname.return_value = "DESKTOP-ABC123"
        mock_gethostbyname.return_value = "192.168.1.150"
        mock_gethostbyname_ex.return_value = (
            "DESKTOP-ABC123",
            [],
            [
                "127.0.0.1",  # Localhost
                "192.168.1.150",  # Default network
                "10.42.0.1",  # VPN or virtual network
                "172.17.0.1",  # Docker network
            ],
        )

        result = get_ipv4()
        assert result == "10.42.0.1", "Should prefer 10.x network in realistic scenario"
