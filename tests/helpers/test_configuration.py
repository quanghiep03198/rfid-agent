import os
import shutil
import tempfile
from configparser import ConfigParser
from unittest.mock import MagicMock, mock_open, patch

import pytest

from helpers.configuration import ConfigSection, ConfigService


class TestConfigSection:
    """Test cases for the ConfigSection enum."""

    def test_config_section_enum_values(self):
        """Test that ConfigSection enum has expected values."""
        assert ConfigSection.READER.value == "READER"

    def test_config_section_enum_type(self):
        """Test that ConfigSection is an Enum."""
        from enum import Enum

        assert issubclass(ConfigSection, Enum)


class TestConfigService:
    """Test cases for the ConfigService class."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for config files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_config_file(self, temp_config_dir):
        """Create a mock config file path."""
        config_path = os.path.join(temp_config_dir, ".config")
        return config_path

    @pytest.fixture
    def sample_config_content(self):
        """Sample configuration file content."""
        return """[READER]
uhf_reader_tcp_ip = 192.168.1.100
uhf_reader_tcp_port = 8160
uhf_reader_ant = 1
uhf_reader_power = 10
"""

    def test_get_conf_existing_key(
        self, temp_config_dir, mock_config_file, sample_config_content
    ):
        """Test getting configuration for existing key."""
        # Write sample config
        with open(mock_config_file, "w") as f:
            f.write(sample_config_content)

        # Mock the config file path
        with patch("helpers.configuration.__cfg_file__", mock_config_file):
            with patch("helpers.configuration.__configs__") as mock_configs:
                mock_configs.has_option.return_value = True
                mock_configs.get.return_value = "192.168.1.100"

                result = ConfigService.get_conf("READER", "uhf_reader_tcp_ip")
                assert result == "192.168.1.100"
                mock_configs.has_option.assert_called_once_with(
                    "READER", "uhf_reader_tcp_ip"
                )

    def test_get_conf_nonexistent_key(self):
        """Test getting configuration for non-existent key returns default."""
        with patch("helpers.configuration.__configs__") as mock_configs:
            mock_configs.has_option.return_value = False

            result = ConfigService.get_conf(
                "READER", "nonexistent_key", default="default_value"
            )
            assert result == "default_value"

    def test_get_conf_nonexistent_key_no_default(self):
        """Test getting configuration for non-existent key with no default returns None."""
        with patch("helpers.configuration.__configs__") as mock_configs:
            mock_configs.has_option.return_value = False

            result = ConfigService.get_conf("READER", "nonexistent_key")
            assert result is None

    def test_get_conf_with_serializer(self):
        """Test getting configuration with custom serializer function."""
        with patch("helpers.configuration.__configs__") as mock_configs:
            mock_configs.has_option.return_value = True
            mock_configs.get.return_value = "8160"

            result = ConfigService.get_conf(
                "READER", "uhf_reader_tcp_port", serializer=int
            )
            assert result == 8160
            assert isinstance(result, int)

    def test_get_conf_with_invalid_serializer(self):
        """Test getting configuration with invalid serializer."""
        with patch("helpers.configuration.__configs__") as mock_configs:
            mock_configs.has_option.return_value = True
            mock_configs.get.return_value = "8160"

            # Pass a non-callable serializer
            result = ConfigService.get_conf(
                "READER", "uhf_reader_tcp_port", serializer="not_callable"
            )
            assert result == "8160"  # Should return string value without serialization

    def test_get_conf_serializer_exception(self):
        """Test behavior when serializer raises an exception."""

        def bad_serializer(value):
            raise ValueError("Serialization failed")

        with patch("helpers.configuration.__configs__") as mock_configs:
            mock_configs.has_option.return_value = True
            mock_configs.get.return_value = "invalid_int"

            with pytest.raises(ValueError, match="Serialization failed"):
                ConfigService.get_conf(
                    "READER", "uhf_reader_tcp_port", serializer=bad_serializer
                )

    def test_get_conf_common_serializers(self):
        """Test common serializer functions."""
        test_cases = [
            ("123", int, 123),
            ("45.67", float, 45.67),
            ("true", lambda x: x.lower() == "true", True),
            ("false", lambda x: x.lower() == "true", False),
            ("item1,item2,item3", lambda x: x.split(","), ["item1", "item2", "item3"]),
        ]

        for value, serializer, expected in test_cases:
            with patch("helpers.configuration.__configs__") as mock_configs:
                mock_configs.has_option.return_value = True
                mock_configs.get.return_value = value

                result = ConfigService.get_conf(
                    "READER", "test_key", serializer=serializer
                )
                assert result == expected

    def test_set_conf_new_value(self, temp_config_dir, mock_config_file):
        """Test setting a new configuration value."""
        # Create initial config file
        with open(mock_config_file, "w") as f:
            f.write("[READER]\n")

        with patch("helpers.configuration.__cfg_file__", mock_config_file):
            with patch("helpers.configuration.__configs__") as mock_configs:
                mock_file = mock_open()

                with patch("builtins.open", mock_file):
                    ConfigService.set_conf(
                        ConfigSection.READER.value, "new_key", "new_value"
                    )

                    mock_configs.set.assert_called_once_with(
                        ConfigSection.READER.value, "new_key", "new_value"
                    )
                    mock_configs.write.assert_called_once()

    def test_set_conf_update_existing_value(
        self, temp_config_dir, mock_config_file, sample_config_content
    ):
        """Test updating an existing configuration value."""
        # Write sample config
        with open(mock_config_file, "w") as f:
            f.write(sample_config_content)

        with patch("helpers.configuration.__cfg_file__", mock_config_file):
            with patch("helpers.configuration.__configs__") as mock_configs:
                mock_file = mock_open()

                with patch("builtins.open", mock_file):
                    ConfigService.set_conf(
                        ConfigSection.READER.value, "uhf_reader_tcp_ip", "10.0.0.1"
                    )

                    mock_configs.set.assert_called_once_with(
                        ConfigSection.READER.value, "uhf_reader_tcp_ip", "10.0.0.1"
                    )
                    mock_configs.write.assert_called_once()

    def test_set_conf_different_data_types(self):
        """Test setting configuration with different data types."""
        test_values = [
            ("string_value", "string_value"),
            (123, "123"),
            (45.67, "45.67"),
            (True, "True"),
            (False, "False"),
            (None, "None"),
            ([1, 2, 3], "[1, 2, 3]"),
            ({"key": "value"}, "{'key': 'value'}"),
        ]

        for value, expected_str in test_values:
            with patch("helpers.configuration.__configs__") as mock_configs:
                mock_file = mock_open()

                with patch("builtins.open", mock_file):
                    ConfigService.set_conf(
                        ConfigSection.READER.value, "test_key", value
                    )

                    mock_configs.set.assert_called_with(
                        ConfigSection.READER.value, "test_key", expected_str
                    )

    def test_set_conf_file_write_error(self):
        """Test behavior when file write fails."""
        with patch("helpers.configuration.__configs__") as mock_configs:
            with patch("builtins.open", side_effect=IOError("Cannot write file")):
                with pytest.raises(IOError, match="Cannot write file"):
                    ConfigService.set_conf(
                        ConfigSection.READER.value, "test_key", "test_value"
                    )


class TestConfigFileInitialization:
    """Test cases for configuration file initialization."""

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_config_file_creation_when_not_exists(self, mock_file, mock_exists):
        """Test that config file is created when it doesn't exist."""
        mock_exists.return_value = False

        # Import the module to trigger the initialization
        import importlib

        import helpers.configuration

        importlib.reload(helpers.configuration)

        # Verify file was opened for writing
        mock_file.assert_called()
        handle = mock_file()

        # Check that default configuration was written
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        assert "[READER]" in written_content
        assert "uhf_reader_tcp_ip = " in written_content
        assert "uhf_reader_tcp_port = 8160" in written_content
        assert "uhf_reader_ant = 1" in written_content
        assert "uhf_reader_power = 10" in written_content

    @patch("os.path.exists")
    @patch("configparser.ConfigParser.read")
    def test_config_file_loading_when_exists(self, mock_read, mock_exists):
        """Test that existing config file is loaded."""
        mock_exists.return_value = True

        # Import the module to trigger the initialization
        import importlib

        import helpers.configuration

        importlib.reload(helpers.configuration)

        # Verify ConfigParser.read was called
        mock_read.assert_called()

    def test_config_file_path_construction(self):
        """Test that config file path is constructed correctly."""
        from helpers.configuration import __cfg_file__

        # Should be an absolute path
        assert os.path.isabs(__cfg_file__)

        # Should end with .config
        assert __cfg_file__.endswith(".config")

        # Should be in the project root directory (parent of helpers)
        expected_base = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert os.path.dirname(__cfg_file__) == expected_base


class TestIntegration:
    """Integration tests for the configuration system."""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for integration tests."""
        fd, path = tempfile.mkstemp(suffix=".config")
        os.close(fd)
        yield path
        os.unlink(path)

    def test_full_config_workflow(self, temp_config_file):
        """Test complete configuration workflow: create, set, get."""
        # Patch the global config file path
        with patch("helpers.configuration.__cfg_file__", temp_config_file):
            # Reinitialize the config parser
            from helpers.configuration import __configs__

            __configs__.clear()

            # Add section
            __configs__.add_section("READER")

            # Set some values
            ConfigService.set_conf(
                ConfigSection.READER.value, "uhf_reader_tcp_ip", "192.168.1.100"
            )
            ConfigService.set_conf(
                ConfigSection.READER.value, "uhf_reader_tcp_port", "8160"
            )

            # Re-read the config to simulate fresh start
            __configs__.read(temp_config_file)

            # Get values back
            ip = ConfigService.get_conf("READER", "uhf_reader_tcp_ip")
            port = ConfigService.get_conf(
                "READER", "uhf_reader_tcp_port", serializer=int
            )

            assert ip == "192.168.1.100"
            assert port == 8160
            assert isinstance(port, int)

    def test_missing_section_handling(self, temp_config_file):
        """Test behavior when configuration section is missing."""
        with patch("helpers.configuration.__cfg_file__", temp_config_file):
            from helpers.configuration import __configs__

            __configs__.clear()

            # Don't add any sections
            result = ConfigService.get_conf("NONEXISTENT", "key", default="default")
            assert result == "default"
