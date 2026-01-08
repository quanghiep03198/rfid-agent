import asyncio
import json
import time
from threading import Thread
from unittest.mock import MagicMock, Mock, call, patch

import paho.mqtt.client as mqtt
import pytest

from constants import Actions, PublishTopics, SubscribeTopics
from helpers.configuration import ConfigSection
from main import Application


class TestApplication:
    """Test cases for the Application class."""

    @pytest.fixture
    def app(self):
        """Create an Application instance for testing."""
        with patch("main.signal.signal"):
            with patch("main.atexit.register"):
                with patch("main.ConfigService.get_conf") as mock_config:

                    def _fake_get_conf(*, section, key, default=""):
                        # App-level config
                        if section == ConfigSection.APP.value and key == "ip":
                            return "192.168.1.50"
                        # Reader config
                        return {
                            "uhf_reader_tcp_ip": "192.168.1.100",
                            "uhf_reader_tcp_port": "8160",
                            "uhf_reader_ant": "1",
                            "uhf_reader_power": "10",
                        }.get(key, default)

                    mock_config.side_effect = _fake_get_conf

                    with patch("main.get_ipv4", return_value="192.168.1.99"):
                        app = Application()
                        yield app

    def test_initialization(self, app):
        """Test Application initialization."""
        # MQTT_HOST may come from a configured IP (loaded at import-time) or fallback to get_ipv4().
        assert isinstance(app.MQTT_HOST, str)
        assert app.MQTT_HOST != ""
        assert app.MQTT_PORT == 1883
        assert app.reader_instance is None
        assert app.reader_ip == "192.168.1.100"
        assert app.reader_port == "8160"
        assert app.reader_ant == "1"
        assert app.reader_power == "10"
        assert app.is_reader_connection_ready is False
        assert app.is_reading is False
        assert app.scanned_epcs == set()

    def test_reader_ip_property(self, app):
        """Test reader_ip property getter and setter."""
        assert app.reader_ip == "192.168.1.100"

        app.reader_ip = "10.0.0.1"
        assert app.reader_ip == "10.0.0.1"

    def test_reader_port_property(self, app):
        """Test reader_port property getter and setter."""
        assert app.reader_port == "8160"

        with patch("main.logger") as mock_logger:
            app.reader_port = 9000
            assert app.reader_port == 9000
            mock_logger.info.assert_called_with("Reader port updated to: 9000")

    def test_reader_ant_property(self, app):
        """Test reader_ant property getter and setter."""
        assert app.reader_ant == "1"

        with patch("main.logger") as mock_logger:
            app.reader_ant = "2"
            assert app.reader_ant == "2"
            mock_logger.info.assert_called_with("Reader antenna updated to: 2")

    def test_reader_power_property(self, app):
        """Test reader_power property getter and setter."""
        assert app.reader_power == "10"

        with patch("main.logger") as mock_logger:
            app.reader_power = "15"
            assert app.reader_power == "15"
            mock_logger.info.assert_called_with("Reader power updated to: 15")

    def test_is_reader_connection_ready_property(self, app):
        """Test is_reader_connection_ready property."""
        assert app.is_reader_connection_ready is False

        app.is_reader_connection_ready = True
        assert app.is_reader_connection_ready is True

    def test_is_reading_property(self, app):
        """Test is_reading property."""
        assert app.is_reading is False

        app.is_reading = True
        assert app.is_reading is True

    def test_scanned_epcs_property(self, app):
        """Test scanned_epcs property."""
        assert app.scanned_epcs == set()

        test_epcs = {"EPC001", "EPC002"}
        app.scanned_epcs = test_epcs
        assert app.scanned_epcs == test_epcs

    def test_property_types_behavior(self, app):
        """Test that properties behave as strings despite EnumG type hints."""
        # These properties should return strings, not EnumG instances
        assert isinstance(app.reader_ant, str)
        assert isinstance(app.reader_power, str)
        assert isinstance(app.reader_ip, str)
        assert isinstance(app.reader_port, str)

        # Verify they can be set with string values
        app.reader_ant = "3"
        app.reader_power = "20"
        assert app.reader_ant == "3"
        assert app.reader_power == "20"

    @patch("main.logger")
    @patch("builtins.print")
    def test_bootstrap_keyboard_interrupt(self, mock_print, mock_logger, app):
        """Test bootstrap method handling KeyboardInterrupt."""
        with patch.object(app, "_Application__restart_reader_connection"):
            with patch.object(
                app, "_Application__init_mqtt_gateway", side_effect=KeyboardInterrupt
            ):
                with patch.object(app, "shutdown") as mock_shutdown:
                    with patch.object(
                        app, "_Application__get_app_version", return_value="v9.9.9"
                    ):
                        app.bootstrap()

                    mock_print.assert_any_call(
                        "============================== RFID Agent - v9.9.9 =============================="
                    )
                    mock_print.assert_any_call(
                        "Press Ctrl+C to exit gracefully or close the console window."
                    )
                    mock_logger.info.assert_called_with(
                        "KeyboardInterrupt received - shutting down the application..."
                    )
                    mock_shutdown.assert_called_once()

    def test_shutdown_with_mqtt_gateway(self, app):
        """Test shutdown method with mqtt_gateway."""
        app.mqtt_gateway = MagicMock()

        with patch.object(
            app, "_Application__handle_close_reader_connection"
        ) as mock_close:
            with patch("main.dumps", return_value='{"test": "data"}'):
                app.shutdown()

                app.mqtt_gateway.publish.assert_called_once_with(
                    topic=PublishTopics.REPLY_SIGNAL.value, payload=b'{"test": "data"}'
                )
                app.mqtt_gateway.loop_stop.assert_called_once()
                app.mqtt_gateway.disconnect.assert_called_once()
                mock_close.assert_called_once()

    def test_shutdown_without_mqtt_gateway(self, app):
        """Test shutdown method without mqtt_gateway."""
        app.mqtt_gateway = None

        with patch.object(
            app, "_Application__handle_close_reader_connection"
        ) as mock_close:
            app.shutdown()
            # Latest shutdown() always closes reader connection regardless of mqtt_gateway.
            mock_close.assert_called_once()

    @patch("main.mqtt.Client")
    @patch("main.logger")
    def test_init_mqtt_gateway_success(self, mock_logger, mock_mqtt_client, app):
        """Test successful MQTT gateway initialization."""
        mock_client = MagicMock()
        mock_mqtt_client.return_value = mock_client
        mock_client.is_connected.return_value = True

        app._Application__init_mqtt_gateway()

        # Verify client setup
        mock_mqtt_client.assert_called_once_with(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        assert app.mqtt_gateway == mock_client
        assert app.mqtt_gateway.on_connect == app._Application__on_mqtt_gateway_connect
        assert (
            app.mqtt_gateway.on_disconnect
            == app._Application__on_mqtt_gateway_disconnect
        )
        assert app.mqtt_gateway.on_message == app._Application__on_mqtt_gateway_message

        # Verify connection
        mock_client.connect.assert_called_once_with(
            host=app.MQTT_HOST, bind_address=app.MQTT_HOST
        )
        mock_client.loop_forever.assert_called_once()

    @patch("main.mqtt.Client")
    @patch("main.logger")
    def test_init_mqtt_gateway_exception(self, mock_logger, mock_mqtt_client, app):
        """Test MQTT gateway initialization with exception."""
        mock_client = MagicMock()
        mock_mqtt_client.return_value = mock_client
        mock_client.connect.side_effect = Exception("Connection failed")

        app._Application__init_mqtt_gateway()

        mock_logger.critical.assert_called_with(
            "Failed to initialize MQTT client: Connection failed"
        )

    # ...existing code...

    def test_publish_connection_status_without_gateway(self, app):
        """Test publishing connection status without mqtt_gateway."""
        app.mqtt_gateway = None

        result = app._Application__publish_connection_status()
        assert result is None

    @patch("main.dumps")
    def test_publish_connection_status_with_gateway(self, mock_dumps, app):
        """Test publishing connection status with mqtt_gateway."""
        app.mqtt_gateway = MagicMock()
        app.mqtt_gateway.is_connected.return_value = True
        app.is_reader_connection_ready = True
        app.is_reading = True
        mock_dumps.return_value = '{"status": "connected"}'

        result = app._Application__publish_connection_status()

        expected_data = {
            "isMQTTConnectionReady": True,
            "isReaderConnectionReady": True,
            "isReaderPlaying": True,
        }
        mock_dumps.assert_called_once_with(expected_data)
        app.mqtt_gateway.publish.assert_called_once_with(
            topic=PublishTopics.REPLY_SIGNAL.value, payload=b'{"status": "connected"}'
        )

    # ...existing code...

    def test_handle_close_reader_connection_with_mqtt(self, app):
        """Test closing reader connection with mqtt_gateway."""
        app.mqtt_gateway = MagicMock()
        app.reader_instance = MagicMock()

        with patch.object(
            app, "_Application__publish_connection_status"
        ) as mock_publish:
            app._Application__handle_close_reader_connection()

            assert app.is_reader_connection_ready is False
            assert app.reader_instance is None
            assert app.is_reading is False
            mock_publish.assert_called_once()

    def test_handle_close_reader_connection_without_mqtt(self, app):
        """Test closing connection without mqtt_gateway."""
        app.mqtt_gateway = None
        app.reader_instance = MagicMock()

        with patch.object(
            app, "_Application__publish_connection_status"
        ) as mock_publish:
            app._Application__handle_close_reader_connection()

            assert app.is_reader_connection_ready is False
            assert app.reader_instance is None
            assert app.is_reading is False
            mock_publish.assert_called_once()

    @patch("main.GClient")
    @patch("main.logger")
    def test_restart_reader_connection(self, mock_logger, mock_gclient, app):
        """Test restart reader connection workflow."""
        # Setup mock GClient instance
        mock_reader_instance = MagicMock()
        mock_gclient.return_value = mock_reader_instance
        mock_reader_instance.openTcp.return_value = True

        # Set initial state
        app.reader_instance = None

        # Execute the method
        app._Application__restart_reader_connection()

        # Verify GClient was instantiated
        mock_gclient.assert_called_once()

        # Verify the sequence of operations
        mock_reader_instance.openTcp.assert_called_once_with(
            (app.reader_ip, int(app.reader_port))
        )
        mock_reader_instance.sendSynMsg.assert_called_once()
        mock_reader_instance.close.assert_called_once()

        # Verify reader_instance is set to None at the end
        assert app.reader_instance is None

        # Verify logger was called
        mock_logger.info.assert_called_with(
            "Gracefully restarted the reader connection."
        )

    # ...existing code...
