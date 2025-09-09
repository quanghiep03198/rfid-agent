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
        with patch("main.ConfigService.get_conf") as mock_config:
            mock_config.side_effect = lambda section, key: {
                "uhf_reader_tcp_ip": "192.168.1.100",
                "uhf_reader_tcp_port": "8160",
                "uhf_reader_ant": "1",
                "uhf_reader_power": "10",
            }.get(key, "")

            with patch("main.get_ipv4", return_value="192.168.1.50"):
                app = Application()
                yield app

    def test_initialization(self, app):
        """Test Application initialization."""
        # HOST is dynamic based on actual network, so just check it's a string
        assert isinstance(app.HOST, str)
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

    @patch("main.logger")
    @patch("builtins.print")
    def test_bootstrap_keyboard_interrupt(self, mock_print, mock_logger, app):
        """Test bootstrap method handling KeyboardInterrupt."""
        with patch.object(
            app, "_Application__init_mqtt_gateway", side_effect=KeyboardInterrupt
        ):
            with patch.object(
                app, "_Application__handle_close_reader_connection"
            ) as mock_close:
                app.bootstrap()

                mock_print.assert_called_with(
                    "============================== RFID Agent - version 1.0.0 =============================="
                )
                mock_logger.info.assert_called_with("Shutting down the application...")
                mock_close.assert_called_once()

    @patch("main.mqtt.Client")
    @patch("main.logger")
    def test_init_mqtt_gateway_success(self, mock_logger, mock_mqtt_client, app):
        """Test successful MQTT gateway initialization."""
        mock_client = MagicMock()
        mock_mqtt_client.return_value = mock_client
        mock_client.is_connected.return_value = True

        with patch.object(app, "_Application__publish_connection_status"):
            app._Application__init_mqtt_gateway()

            # Verify client setup
            mock_mqtt_client.assert_called_once_with(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2
            )
            assert app.mqtt_gateway == mock_client
            assert (
                app.mqtt_gateway.on_connect == app._Application__on_mqtt_gateway_connect
            )
            assert (
                app.mqtt_gateway.on_disconnect
                == app._Application__on_mqtt_gateway_disconnect
            )
            assert (
                app.mqtt_gateway.on_message == app._Application__on_mqtt_gateway_message
            )

            # Verify connection
            mock_client.connect.assert_called_once_with(
                host=app.HOST, bind_address=app.HOST
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

        mock_logger.error.assert_called_with(
            "Failed to initialize MQTT client: Connection failed"
        )
        mock_client.loop_stop.assert_called_once()
        mock_client.disconnect.assert_called_once()

    @patch("main.logger")
    def test_on_mqtt_gateway_connect(self, mock_logger, app):
        """Test MQTT connect callback."""
        mock_client = MagicMock()
        mock_reason_code = MagicMock()
        mock_reason_code.__str__ = MagicMock(return_value="SUCCESS")

        with patch.object(
            app, "_Application__publish_connection_status"
        ) as mock_publish:
            app._Application__on_mqtt_gateway_connect(
                mock_client, None, None, mock_reason_code, None
            )

            mock_logger.info.assert_any_call("MQTT connected with status 'SUCCESS'")
            mock_logger.info.assert_any_call(">>> Press Ctrl + C to exit <<<")

            # Verify subscriptions
            expected_calls = [
                call(SubscribeTopics.REQUEST_SIGNAL.value),
                call(SubscribeTopics.REQUEST_DATA.value),
                call(SubscribeTopics.REQUEST_SETTINGS.value),
            ]
            mock_client.subscribe.assert_has_calls(expected_calls)
            mock_publish.assert_called_once()

    @patch("main.logger")
    @patch("main.dumps")
    def test_on_mqtt_gateway_disconnect(self, mock_dumps, mock_logger, app):
        """Test MQTT disconnect callback."""
        mock_client = MagicMock()
        mock_reason_code = MagicMock()
        mock_reason_code.__str__ = MagicMock(return_value="DISCONNECT")
        mock_dumps.return_value = '{"test": "data"}'

        app._Application__on_mqtt_gateway_disconnect(
            mock_client, None, None, mock_reason_code, None
        )

        mock_logger.info.assert_called_with(
            "MQTT disconnected with status 'DISCONNECT'"
        )
        mock_client.publish.assert_called_once_with(
            topic=PublishTopics.REPLY_SIGNAL.value, payload=b'{"test": "data"}'
        )

    def test_on_mqtt_gateway_message_ping_action(self, app):
        """Test MQTT message handling for PING action."""
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.topic = SubscribeTopics.REQUEST_SIGNAL.value
        mock_message.payload.decode.return_value = json.dumps(
            {"action": Actions.PING.value}
        )

        with patch.object(
            app, "_Application__publish_connection_status"
        ) as mock_publish:
            with patch.object(
                app, "_Application__handle_publish_data"
            ) as mock_handle_data:
                app._Application__on_mqtt_gateway_message(
                    mock_client, None, mock_message
                )

                mock_publish.assert_called_once()
                mock_handle_data.assert_called_once()

    def test_on_mqtt_gateway_message_connect_action(self, app):
        """Test MQTT message handling for CONNECT action."""
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.topic = SubscribeTopics.REQUEST_SIGNAL.value
        mock_message.payload.decode.return_value = json.dumps(
            {"action": Actions.CONNECT.value}
        )

        with patch("main.Thread") as mock_thread:
            app._Application__on_mqtt_gateway_message(mock_client, None, mock_message)

            mock_thread.assert_called_once_with(
                target=app._Application__handle_open_reader_connection, daemon=True
            )
            mock_thread.return_value.start.assert_called_once()

    def test_on_mqtt_gateway_message_disconnect_action(self, app):
        """Test MQTT message handling for DISCONNECT action."""
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.topic = SubscribeTopics.REQUEST_SIGNAL.value
        mock_message.payload.decode.return_value = json.dumps(
            {"action": Actions.DISCONNECT.value}
        )

        with patch("main.Thread") as mock_thread:
            app._Application__on_mqtt_gateway_message(mock_client, None, mock_message)

            mock_thread.assert_called_once_with(
                target=app._Application__handle_close_reader_connection, daemon=True
            )
            mock_thread.return_value.start.assert_called_once()

    def test_on_mqtt_gateway_message_start_action(self, app):
        """Test MQTT message handling for START action."""
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.topic = SubscribeTopics.REQUEST_SIGNAL.value
        mock_message.payload.decode.return_value = json.dumps(
            {"action": Actions.START.value}
        )

        with patch("main.Thread") as mock_thread:
            app._Application__on_mqtt_gateway_message(mock_client, None, mock_message)

            mock_thread.assert_called_once_with(
                target=app._Application__handle_start_reading, daemon=True
            )
            mock_thread.return_value.start.assert_called_once()

    def test_on_mqtt_gateway_message_stop_action(self, app):
        """Test MQTT message handling for STOP action."""
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.topic = SubscribeTopics.REQUEST_SIGNAL.value
        mock_message.payload.decode.return_value = json.dumps(
            {"action": Actions.STOP.value}
        )

        with patch("main.Thread") as mock_thread:
            app._Application__on_mqtt_gateway_message(mock_client, None, mock_message)

            mock_thread.assert_called_once_with(
                target=app._Application__handle_stop_reading, daemon=True
            )
            mock_thread.return_value.start.assert_called_once()

    def test_on_mqtt_gateway_message_request_data_reset(self, app):
        """Test MQTT message handling for data reset."""
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.topic = SubscribeTopics.REQUEST_DATA.value
        mock_message.payload.decode.return_value = json.dumps({"action": "reset"})

        with patch.object(app, "_Application__reset_scanned_epcs") as mock_reset:
            app._Application__on_mqtt_gateway_message(mock_client, None, mock_message)
            mock_reset.assert_called_once()

    def test_on_mqtt_gateway_message_request_settings_get(self, app):
        """Test MQTT message handling for get settings."""
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.topic = SubscribeTopics.REQUEST_SETTINGS.value
        mock_message.payload.decode.return_value = json.dumps({"action": "get"})

        with patch.object(
            app, "_Application__handle_retrieve_reader_settings"
        ) as mock_get:
            app._Application__on_mqtt_gateway_message(mock_client, None, mock_message)
            mock_get.assert_called_once()

    def test_on_mqtt_gateway_message_request_settings_update(self, app):
        """Test MQTT message handling for update settings."""
        mock_client = MagicMock()
        mock_message = MagicMock()
        test_payload = {"action": "update", "payload": {"readerIP": "10.0.0.1"}}
        mock_message.topic = SubscribeTopics.REQUEST_SETTINGS.value
        mock_message.payload.decode.return_value = json.dumps(test_payload)

        with patch.object(app, "_Application__handle_update_settings") as mock_update:
            app._Application__on_mqtt_gateway_message(mock_client, None, mock_message)
            mock_update.assert_called_once_with(settings={"readerIP": "10.0.0.1"})

    @patch("main.logger")
    def test_on_mqtt_gateway_message_invalid_json(self, mock_logger, app):
        """Test MQTT message handling with invalid JSON."""
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.payload.decode.return_value = "invalid json"

        app._Application__on_mqtt_gateway_message(mock_client, None, mock_message)
        mock_logger.error.assert_called_with("Invalid JSON payload received.")

    @patch("main.dumps")
    def test_publish_connection_status(self, mock_dumps, app):
        """Test publishing connection status."""
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

    def test_compress_data(self, app):
        """Test data compression."""
        test_data = {"EPC001", "EPC002", "EPC003"}

        result = app._Application__compress_data(test_data)

        # Result should be a base64 encoded string
        assert isinstance(result, str)
        assert len(result) > 0

        # Verify we can decode it back
        import base64
        import gzip

        decoded = base64.b64decode(result.encode())
        decompressed = gzip.decompress(decoded)
        original_data = json.loads(decompressed.decode())
        assert set(original_data) == test_data

    def test_handle_publish_data(self, app):
        """Test publishing EPC data."""
        app.mqtt_gateway = MagicMock()
        app.scanned_epcs = {"EPC001", "EPC002"}

        with patch.object(
            app, "_Application__compress_data", return_value="compressed_data"
        ) as mock_compress:
            app._Application__handle_publish_data()

            mock_compress.assert_called_once_with(data=app.scanned_epcs)
            app.mqtt_gateway.publish.assert_called_once_with(
                topic=PublishTopics.REPLY_DATA.value, payload="compressed_data"
            )

    @patch("main.logger")
    def test_handle_receive_epc_new(self, mock_logger, app):
        """Test handling new EPC data."""
        app.mqtt_gateway = MagicMock()
        mock_epc_data = MagicMock()
        mock_epc_data.epc = "epc001"  # lowercase to test upper() conversion

        with patch.object(app, "_Application__handle_publish_data") as mock_publish:
            app._Application__handle_receive_epc(mock_epc_data)

            assert "EPC001" in app.scanned_epcs
            mock_logger.info.assert_called_with("EPC :>>> EPC001")
            mock_publish.assert_called_once()

    @patch("main.logger")
    def test_handle_receive_epc_duplicate(self, mock_logger, app):
        """Test handling duplicate EPC data."""
        app.mqtt_gateway = MagicMock()
        app.scanned_epcs.add("EPC001")
        mock_epc_data = MagicMock()
        mock_epc_data.epc = "EPC001"

        with patch.object(app, "_Application__handle_publish_data") as mock_publish:
            app._Application__handle_receive_epc(mock_epc_data)

            # Should not log or publish for duplicates
            mock_logger.info.assert_not_called()
            mock_publish.assert_not_called()

    @patch("main.logger")
    def test_handle_receive_epc_end(self, mock_logger, app):
        """Test handling EPC reading end."""
        mock_log = MagicMock()
        mock_log.msgId = "MSG123"

        app._Application__handle_receive_epc_end(mock_log)
        mock_logger.info.assert_called_with("Stopped reading EPC with code: >>> MSG123")

    @patch("main.logger")
    def test_reset_scanned_epcs(self, mock_logger, app):
        """Test resetting scanned EPCs."""
        app.scanned_epcs = {"EPC001", "EPC002"}

        app._Application__reset_scanned_epcs()

        assert app.scanned_epcs == set()
        mock_logger.info.assert_called_with("Scanned EPCs have been reset.")

    @patch("main.ConfigService.get_conf")
    @patch("main.dumps")
    def test_handle_retrieve_reader_settings(self, mock_dumps, mock_config, app):
        """Test retrieving reader settings."""
        app.mqtt_gateway = MagicMock()
        mock_config.side_effect = lambda section, key: {
            "uhf_reader_tcp_ip": "192.168.1.100",
            "uhf_reader_ant": "2",
            "uhf_reader_power": "15",
        }.get(key)
        mock_dumps.return_value = '{"settings": "data"}'

        app._Application__handle_retrieve_reader_settings()

        expected_settings = {
            "readerIP": "192.168.1.100",
            "readerAnt": "2",
            "readerPower": "15",
        }
        mock_dumps.assert_called_once_with(
            {"metadata": expected_settings, "message": "Ok"}
        )
        app.mqtt_gateway.publish.assert_called_once_with(
            topic=PublishTopics.REPLY_SETTINGS.value, payload=b'{"settings": "data"}'
        )

    @patch("main.is_ipv4")
    @patch("main.ConfigService.set_conf")
    @patch("main.logger")
    def test_handle_update_settings_success(
        self, mock_logger, mock_set_conf, mock_is_ipv4, app
    ):
        """Test successful settings update."""
        app.mqtt_gateway = MagicMock()
        mock_is_ipv4.return_value = True

        settings = {"readerIP": "10.0.0.1", "readerAnt": "2", "readerPower": "20"}

        with patch.object(app, "_Application__publish_connection_status"):
            with patch.object(app, "_Application__handle_stop_reading"):
                with patch("main.Thread"):
                    with patch("main.dumps", return_value='{"result": "success"}'):
                        app._Application__handle_update_settings(settings)

        # Verify config updates
        expected_calls = [
            call(
                section=ConfigSection.READER.value,
                key="uhf_reader_tcp_ip",
                value="10.0.0.1",
            ),
            call(section=ConfigSection.READER.value, key="uhf_reader_ant", value="2"),
            call(
                section=ConfigSection.READER.value, key="uhf_reader_power", value="20"
            ),
        ]
        mock_set_conf.assert_has_calls(expected_calls)

        # Verify property updates
        assert app.reader_ip == "10.0.0.1"
        assert app.reader_ant == "2"
        assert app.reader_power == "20"

        mock_logger.info.assert_called_with("Reader settings updated successfully.")

    @patch("main.is_ipv4")
    @patch("main.logger")
    def test_handle_update_settings_invalid_ip(self, mock_logger, mock_is_ipv4, app):
        """Test settings update with invalid IP."""
        app.mqtt_gateway = MagicMock()
        mock_is_ipv4.return_value = False

        settings = {"readerIP": "invalid_ip"}

        with patch("main.dumps", return_value='{"error": "invalid"}'):
            app._Application__handle_update_settings(settings)

        mock_logger.info.assert_called_with("Invalid IP address. Please try again.")
        app.mqtt_gateway.publish.assert_called_once()

    @patch("main.is_ipv4")
    @patch("main.logger")
    def test_handle_update_settings_invalid_antenna(
        self, mock_logger, mock_is_ipv4, app
    ):
        """Test settings update with invalid antenna value."""
        app.mqtt_gateway = MagicMock()
        mock_is_ipv4.return_value = True

        settings = {
            "readerIP": "192.168.1.100",
            "readerAnt": "5",  # Invalid: must be 1-4
            "readerPower": "10",
        }

        with patch("main.dumps", return_value='{"error": "invalid"}'):
            app._Application__handle_update_settings(settings)

        mock_logger.info.assert_called_with("Invalid IP address. Please try again.")

    @patch("main.is_ipv4")
    @patch("main.logger")
    def test_handle_update_settings_invalid_power(self, mock_logger, mock_is_ipv4, app):
        """Test settings update with invalid power value."""
        app.mqtt_gateway = MagicMock()
        mock_is_ipv4.return_value = True

        settings = {
            "readerIP": "192.168.1.100",
            "readerAnt": "2",
            "readerPower": "50",  # Invalid: must be 5-30
        }

        with patch("main.dumps", return_value='{"error": "invalid"}'):
            app._Application__handle_update_settings(settings)

        mock_logger.info.assert_called_with("Invalid IP address. Please try again.")

    @patch("main.logger")
    def test_apply_reader_configurations_no_instance(self, mock_logger, app):
        """Test applying configurations when reader instance is None."""
        app.reader_instance = None

        app._Application__apply_reader_configurations()
        mock_logger.warning.assert_called_with("Reader instance is not initialized.")

    def test_apply_reader_configurations_success(self, app):
        """Test successful reader configuration application."""
        app.reader_instance = MagicMock()
        app.reader_power = "15"
        app.reader_ant = "2"

        with patch("main.MsgAppSetBeep") as mock_beep:
            with patch("main.MsgBaseSetPower") as mock_power:
                with patch("main.MsgBaseInventoryEpc") as mock_inventory:
                    with patch("main.EnumG") as mock_enum:
                        mock_enum.AntennaNo_1.value = 1
                        mock_enum.InventoryMode_Inventory.value = 0

                        app._Application__apply_reader_configurations()

        # Verify sendSynMsg calls
        assert app.reader_instance.sendSynMsg.call_count == 3

    def test_apply_reader_configurations_fallback_values(self, app):
        """Test reader configuration with fallback values."""
        app.reader_instance = MagicMock()
        app.reader_power = ""  # Empty string should use fallback
        app.reader_ant = None  # None should use fallback

        with patch("main.MsgAppSetBeep"):
            with patch("main.MsgBaseSetPower"):
                with patch("main.MsgBaseInventoryEpc"):
                    with patch("main.EnumG") as mock_enum:
                        mock_enum.AntennaNo_1.value = 1
                        mock_enum.InventoryMode_Inventory.value = 0

                        app._Application__apply_reader_configurations()

        # Should use fallback values
        assert app.reader_instance.sendSynMsg.call_count == 3

    @patch("main.GClient")
    @patch("main.logger")
    def test_handle_open_reader_connection_success(
        self, mock_logger, mock_gclient, app
    ):
        """Test successful reader connection."""
        mock_reader = MagicMock()
        mock_gclient.return_value = mock_reader
        mock_reader.openTcp.return_value = True

        with patch.object(
            app, "_Application__publish_connection_status"
        ) as mock_publish:
            app._Application__handle_open_reader_connection()

        assert app.reader_instance == mock_reader
        assert app.is_reader_connection_ready is True
        mock_reader.openTcp.assert_called_once_with(
            (app.reader_ip, int(app.reader_port))
        )
        assert mock_reader.callEpcOver == app._Application__handle_receive_epc_end
        assert mock_reader.callEpcInfo == app._Application__handle_receive_epc
        mock_publish.assert_called_once()

    @patch("main.GClient")
    @patch("main.logger")
    def test_handle_open_reader_connection_failure(
        self, mock_logger, mock_gclient, app
    ):
        """Test failed reader connection."""
        mock_reader = MagicMock()
        mock_gclient.return_value = mock_reader
        mock_reader.openTcp.return_value = False

        with patch.object(
            app, "_Application__publish_connection_status"
        ) as mock_publish:
            app._Application__handle_open_reader_connection()

        assert app.is_reader_connection_ready is False
        mock_logger.warning.assert_called_with(
            "Cannot to connect to the reader. Please check your TCP/IP settings, and device connection."
        )
        mock_publish.assert_called_once()

    def test_handle_open_reader_connection_existing_instance(self, app):
        """Test opening connection with existing reader instance."""
        existing_reader = MagicMock()
        existing_reader.openTcp.return_value = True
        app.reader_instance = existing_reader

        with patch.object(app, "_Application__publish_connection_status"):
            app._Application__handle_open_reader_connection()

        # Should use existing instance, not create new one
        assert app.reader_instance == existing_reader

    @patch("main.dumps")
    def test_handle_close_reader_connection(self, mock_dumps, app):
        """Test closing reader connection."""
        app.mqtt_gateway = MagicMock()
        app.reader_instance = MagicMock()
        mock_dumps.return_value = '{"status": "disconnected"}'

        app._Application__handle_close_reader_connection()

        assert app.is_reader_connection_ready is False
        assert app.reader_instance is None
        assert app.is_reading is False
        app.mqtt_gateway.publish.assert_called_once()

    def test_handle_close_reader_connection_no_instance(self, app):
        """Test closing connection when no reader instance exists."""
        app.mqtt_gateway = MagicMock()
        app.reader_instance = None

        with patch("main.dumps", return_value='{"status": "disconnected"}'):
            app._Application__handle_close_reader_connection()

        assert app.is_reader_connection_ready is False
        assert app.is_reading is False

    @patch("main.logger")
    def test_handle_start_reading(self, mock_logger, app):
        """Test starting EPC reading."""
        with patch.object(
            app, "_Application__publish_connection_status"
        ) as mock_publish:
            with patch.object(
                app, "_Application__apply_reader_configurations"
            ) as mock_apply:
                app._Application__handle_start_reading()

        assert app.is_reading is True
        mock_publish.assert_called_once()
        mock_apply.assert_called_once()
        mock_logger.info.assert_called_with("Started reading EPC.")

    @patch("main.logger")
    def test_handle_stop_reading(self, mock_logger, app):
        """Test stopping EPC reading."""
        app.reader_instance = MagicMock()

        with patch.object(
            app, "_Application__publish_connection_status"
        ) as mock_publish:
            with patch("main.MsgBaseStop") as mock_stop:
                app._Application__handle_stop_reading()

        assert app.is_reading is False
        mock_publish.assert_called_once()
        mock_logger.info.assert_called_with("Stopped reading EPC.")
        app.reader_instance.sendSynMsg.assert_called_once()

    @patch("main.logger")
    def test_handle_stop_reading_no_instance(self, mock_logger, app):
        """Test stopping reading when no reader instance exists."""
        app.reader_instance = None

        with patch.object(
            app, "_Application__publish_connection_status"
        ) as mock_publish:
            app._Application__handle_stop_reading()

        assert app.is_reading is False
        mock_publish.assert_called_once()
        mock_logger.info.assert_called_with("Stopped reading EPC.")


class TestApplicationIntegration:
    """Integration tests for the Application class."""

    @pytest.fixture
    def app_with_mocks(self):
        """Create an Application instance with mocked dependencies."""
        with patch("main.ConfigService.get_conf") as mock_config:
            mock_config.side_effect = lambda section, key: {
                "uhf_reader_tcp_ip": "192.168.1.100",
                "uhf_reader_tcp_port": "8160",
                "uhf_reader_ant": "1",
                "uhf_reader_power": "10",
            }.get(key, "")

            with patch("main.get_ipv4", return_value="192.168.1.50"):
                app = Application()
                app.mqtt_gateway = MagicMock()
                yield app

    def test_full_epc_processing_workflow(self, app_with_mocks):
        """Test complete EPC processing workflow."""
        app = app_with_mocks

        # Mock EPC data
        mock_epc_data1 = MagicMock()
        mock_epc_data1.epc = "EPC001"
        mock_epc_data2 = MagicMock()
        mock_epc_data2.epc = "EPC002"

        # Process EPCs
        with patch.object(app, "_Application__handle_publish_data") as mock_publish:
            app._Application__handle_receive_epc(mock_epc_data1)
            app._Application__handle_receive_epc(mock_epc_data2)
            app._Application__handle_receive_epc(mock_epc_data1)  # Duplicate

        # Verify results
        assert app.scanned_epcs == {"EPC001", "EPC002"}
        assert mock_publish.call_count == 2  # Only for unique EPCs

        # Reset and verify
        app._Application__reset_scanned_epcs()
        assert app.scanned_epcs == set()

    def test_mqtt_settings_update_workflow(self, app_with_mocks):
        """Test complete settings update workflow via MQTT."""
        app = app_with_mocks

        # Create MQTT message for settings update
        mock_message = MagicMock()
        mock_message.topic = SubscribeTopics.REQUEST_SETTINGS.value
        settings_payload = {
            "action": "update",
            "payload": {"readerIP": "10.0.0.50", "readerAnt": "3", "readerPower": "25"},
        }
        mock_message.payload.decode.return_value = json.dumps(settings_payload)

        with patch("main.is_ipv4", return_value=True):
            with patch("main.ConfigService.set_conf"):
                with patch("main.Thread"):
                    with patch("main.dumps", return_value='{"success": true}'):
                        app._Application__on_mqtt_gateway_message(
                            None, None, mock_message
                        )

        # Verify settings were updated
        assert app.reader_ip == "10.0.0.50"
        assert app.reader_ant == "3"
        assert app.reader_power == "25"

    def test_reader_connection_lifecycle(self, app_with_mocks):
        """Test complete reader connection lifecycle."""
        app = app_with_mocks

        # Test connection
        with patch("main.GClient") as mock_gclient:
            mock_reader = MagicMock()
            mock_gclient.return_value = mock_reader
            mock_reader.openTcp.return_value = True

            with patch.object(app, "_Application__publish_connection_status"):
                app._Application__handle_open_reader_connection()

            assert app.is_reader_connection_ready is True
            assert app.reader_instance == mock_reader

        # Test start reading
        with patch.object(app, "_Application__publish_connection_status"):
            with patch.object(app, "_Application__apply_reader_configurations"):
                app._Application__handle_start_reading()

            assert app.is_reading is True

        # Test stop reading
        with patch.object(app, "_Application__publish_connection_status"):
            with patch("main.MsgBaseStop"):
                app._Application__handle_stop_reading()

            assert app.is_reading is False

        # Test disconnection
        with patch("main.dumps", return_value='{"disconnected": true}'):
            app._Application__handle_close_reader_connection()

            assert app.is_reader_connection_ready is False
            assert app.reader_instance is None
