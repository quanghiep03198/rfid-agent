import atexit
import signal
import sys
from json import JSONDecodeError, dumps, loads
from pathlib import Path
from threading import Thread

import paho.mqtt.client as mqtt
from uhf.reader import *

from constants import Actions, PublishTopics, SubscribeTopics
from helpers.configuration import ConfigSection, ConfigService
from helpers.ipv4 import get_ipv4, is_ipv4
from helpers.logger import logger


class Application:
    CONFIGURED_IP = ConfigService.get_conf(
        section=ConfigSection.APP.value,
        key="ip",
        default="",
    )

    MQTT_HOST = None
    """
    Host IP address for MQTT broker connection.
    """

    MQTT_PORT = 1883
    """
    MQTT broker port.
    """

    APP_VERSION = None

    reader_instance: GClient | None = None

    @property
    def reader_ip(self):
        return self.__reader_ip

    @reader_ip.setter
    def reader_ip(self, ip: str):
        self.__reader_ip = ip

    @property
    def reader_port(self) -> int:
        return self.__reader_port

    @reader_port.setter
    def reader_port(self, port: int):
        logger.info(f"Reader port updated to: {port}")
        self.__reader_port = port

    @property
    def reader_ant(self) -> EnumG:
        return self.__reader_ant

    @reader_ant.setter
    def reader_ant(self, ant: EnumG):
        logger.info(f"Reader antenna updated to: {ant}")
        self.__reader_ant = ant

    @property
    def reader_power(self) -> EnumG:
        return self.__reader_power

    @reader_power.setter
    def reader_power(self, power: EnumG):
        logger.info(f"Reader power updated to: {power}")
        self.__reader_power = power

    @property
    def is_reader_connection_ready(self):
        return self.__is_reader_connection_ready

    @is_reader_connection_ready.setter
    def is_reader_connection_ready(self, state: bool):
        self.__is_reader_connection_ready = state

    @property
    def is_reading(self):
        return self.__is_reading

    @is_reading.setter
    def is_reading(self, state: bool):
        self.__is_reading = state

    @property
    def scanned_epcs(self):
        return self.__scanned_epcs

    @scanned_epcs.setter
    def scanned_epcs(self, data: set[str]):
        self.__scanned_epcs = data

    def __init__(self):
        self.MQTT_HOST = (
            self.CONFIGURED_IP
            if self.CONFIGURED_IP is not None and self.CONFIGURED_IP != ""
            else get_ipv4()
        )

        self.__is_reader_connection_ready = False
        self.__is_reading = False
        self.__scanned_epcs: set[str] = set()
        self.__reader_ip = ConfigService.get_conf(
            section=ConfigSection.READER.value, key="uhf_reader_tcp_ip"
        )
        self.__reader_port = ConfigService.get_conf(
            section=ConfigSection.READER.value, key="uhf_reader_tcp_port"
        )
        self.__reader_ant = ConfigService.get_conf(
            section=ConfigSection.READER.value, key="uhf_reader_ant"
        )
        self.__reader_power = ConfigService.get_conf(
            section=ConfigSection.READER.value, key="uhf_reader_power"
        )

        # Setup signal handlers for graceful shutdown
        self.__setup_signal_handlers()
        # Register cleanup function to run on exit
        atexit.register(self.__cleanup_on_exit)

    def __setup_signal_handlers(self) -> None:
        """
        Setup signal handlers to catch console close events and interruptions.
        """
        signal.signal(signal.SIGINT, self.__signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, self.__signal_handler)  # Termination signal

        # On Windows, also handle SIGBREAK (Ctrl+Break) and console close
        if sys.platform == "win32":
            signal.signal(signal.SIGBREAK, self.__signal_handler)

    def __signal_handler(self, signum, frame):
        """
        Handle signals for graceful shutdown.
        """
        logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
        print(f"\nReceived termination signal ({signum}). Shutting down gracefully...")
        self.shutdown()
        sys.exit(0)

    def __cleanup_on_exit(self):
        """
        Cleanup function that runs when the program exits.
        """
        logger.info("Application is exiting - performing final cleanup...")
        if hasattr(self, "mqtt_gateway") and self.mqtt_gateway is not None:
            try:
                self.mqtt_gateway.loop_stop()
                self.mqtt_gateway.disconnect()
            except Exception as e:
                logger.error(f"Error during MQTT cleanup: {e}")

        if self.reader_instance is not None:
            try:
                self.reader_instance.close()
                self.reader_instance = None
            except Exception as e:
                logger.error(f"Error during reader cleanup: {e}")

    def __get_app_version(default: str = "v1.0.0") -> str:
        """Read version string from version.json if it exists.

        Returns the version without the optional leading 'v' (e.g. 'v1.1.0' -> '1.1.0'),
        falling back to `default` if anything goes wrong.
        """
        try:
            version_file = Path(__file__).with_name("version.json")
            if not version_file.exists():
                return default
            data = loads(version_file.read_text(encoding="utf-8"))
            version = str(data.get("version", "") or "").strip()

            return version or default
        except Exception:
            return default

    def bootstrap(self) -> None:
        """
        Start the main application loop, handling MQTT and UHF reader interactions.
        This method runs indefinitely until interrupted, managing connections and data flow.
        """
        self.APP_VERSION = self.__get_app_version()
        try:
            print(
                f"============================== RFID Agent - {self.APP_VERSION} =============================="
            )
            print("Press Ctrl+C to exit gracefully or close the console window.")
            self.__restart_reader_connection()
            self.__init_mqtt_gateway()
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received - shutting down the application...")
            self.shutdown()
        except Exception as e:
            logger.error(f"Unexpected error in bootstrap: {e}")
            self.shutdown()
            raise

    def shutdown(self) -> None:
        """
        Gracefully shut down the application, ensuring all connections are closed.
        """
        logger.info("Initiating graceful shutdown...")

        # Stop reading if currently active
        if self.is_reading:
            logger.info("Stopping RFID reading...")
            self.__handle_stop_reading()

        # Send final status update via MQTT if connection exists
        if hasattr(self, "mqtt_gateway") and self.mqtt_gateway is not None:
            try:
                logger.info("Sending final MQTT status update...")
                self.mqtt_gateway.publish(
                    topic=PublishTopics.REPLY_SIGNAL.value,
                    payload=dumps(
                        {
                            "isMQTTConnectionReady": False,
                            "isReaderConnectionReady": False,
                            "isReaderPlaying": False,
                        }
                    ).encode(),
                )
                # Give a moment for the message to be sent
                import time

                time.sleep(0.5)

                self.mqtt_gateway.loop_stop()
                self.mqtt_gateway.disconnect()
                logger.info("MQTT connection closed.")
            except Exception as e:
                logger.error(f"Error during MQTT shutdown: {e}")

        # Close reader connection
        self.__handle_close_reader_connection()
        logger.info("Application shutdown completed.")

    # region MQTT handlers
    def __init_mqtt_gateway(self) -> None:
        try:
            self.mqtt_gateway = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            )
            self.mqtt_gateway.on_connect = self.__on_mqtt_gateway_connect
            self.mqtt_gateway.on_disconnect = self.__on_mqtt_gateway_disconnect
            self.mqtt_gateway.on_message = self.__on_mqtt_gateway_message
            self.mqtt_gateway.connect(
                host=self.MQTT_HOST,
                bind_address=self.MQTT_HOST,
            )
            self.mqtt_gateway.loop_forever()
            self.mqtt_gateway.publish(
                topic=PublishTopics.REPLY_SIGNAL.value,
                payload=dumps(
                    {
                        "isMQTTConnectionReady": self.mqtt_gateway.is_connected(),
                        "isReaderConnectionReady": self.is_reader_connection_ready,
                        "isReaderPlaying": self.is_reading,
                    }
                ).encode(),
            )
        except Exception as e:
            logger.critical(f"Failed to initialize MQTT client: {e}")

    def __on_mqtt_gateway_connect(
        self,
        client: mqtt.Client,
        userdata,
        flags: mqtt.ConnectFlags,
        reason_code_list: mqtt.ReasonCode,
        properties: mqtt.Union[mqtt.Properties, None],
    ):
        logger.info(f"MQTT connected with status '{str(reason_code_list)}'")
        logger.info(">>> Press Ctrl + C to exit <<<")

        client.subscribe(SubscribeTopics.REQUEST_SIGNAL.value)
        client.subscribe(SubscribeTopics.REQUEST_DATA.value)
        client.subscribe(SubscribeTopics.REQUEST_SETTINGS.value)
        self.__publish_connection_status()

    def __on_mqtt_gateway_disconnect(
        self,
        client: mqtt.Client,
        userdata,
        flags: mqtt.ConnectFlags,
        reason_code_list: mqtt.ReasonCode,
        properties: mqtt.Union[mqtt.Properties, None],
    ):
        """
        Publish disconnection status to MQTT broker.
        """
        client.publish(
            topic=PublishTopics.REPLY_SIGNAL.value,
            payload=dumps(
                {
                    "isMQTTConnectionReady": False,
                    "isReaderConnectionReady": False,
                    "isReaderPlaying": False,
                }
            ).encode(),
        )
        logger.info(f"MQTT disconnected with status '{str(reason_code_list)}'")

    def __on_mqtt_gateway_message(
        self, client: mqtt.Client, userdata, message: mqtt.MQTTMessage
    ):
        """
        Handle incoming MQTT messages and perform actions based on the topic and payload.
        """
        try:
            parsed_data: dict[str, str] = loads(message.payload.decode())
        except JSONDecodeError:
            logger.error("Invalid JSON payload received.")
            return

        action = parsed_data.get("action")
        match message.topic:
            case SubscribeTopics.REQUEST_SIGNAL.value:
                match action:
                    case Actions.PING.value:
                        self.__publish_connection_status()
                        self.__handle_restore_data()

                    case Actions.CONNECT.value:
                        Thread(
                            target=self.__handle_open_reader_connection,
                            daemon=True,
                        ).start()
                    case Actions.DISCONNECT.value:
                        Thread(
                            target=self.__handle_close_reader_connection,
                            daemon=True,
                        ).start()
                    case Actions.START.value:
                        Thread(
                            target=self.__handle_start_reading,
                            daemon=True,
                        ).start()
                    case Actions.STOP.value:
                        Thread(
                            target=self.__handle_stop_reading,
                            daemon=True,
                        ).start()

            case SubscribeTopics.REQUEST_DATA.value:
                if action == "reset":
                    self.__reset_scanned_epcs()

            case SubscribeTopics.REQUEST_SETTINGS.value:
                if action == "get":
                    self.__handle_retrieve_reader_settings()
                if action == "update":
                    self.__handle_update_settings(settings=parsed_data.get("payload"))

    def __publish_connection_status(self) -> mqtt.MQTTMessageInfo:
        """
        Publish the current connection status to the MQTT broker.
        """
        if not hasattr(self, "mqtt_gateway") or self.mqtt_gateway is None:
            return
        return self.mqtt_gateway.publish(
            topic=PublishTopics.REPLY_SIGNAL.value,
            payload=dumps(
                {
                    "isMQTTConnectionReady": self.mqtt_gateway.is_connected(),
                    "isReaderConnectionReady": self.is_reader_connection_ready,
                    "isReaderPlaying": self.is_reading,
                }
            ).encode(),
        )

    # endregion

    # region UHF Reader handlers

    def __handle_restore_data(self) -> None:
        """
        Publish all scanned EPCs to the MQTT broker.
        """
        scanned_list = list(self.scanned_epcs)
        for epc in scanned_list:
            self.mqtt_gateway.publish(
                topic=PublishTopics.REPLY_DATA.value,
                payload=epc,
            )

    def __handle_receive_epc(self, data: LogBaseEpcInfo) -> None:
        """
        Handle incoming EPC data from the UHF reader.
        """
        epc = data.epc.upper()
        self.mqtt_gateway.publish(topic=PublishTopics.REPLY_DATA.value, payload=epc)
        if epc in self.scanned_epcs:
            return
        self.scanned_epcs.add(epc)
        logger.debug(f"Total scanned EPCs: {len(self.scanned_epcs)}")

    def __handle_receive_epc_end(self, log: LogBaseEpcOver) -> None:
        logger.info(f"Stopped reading EPC with code: >>> {log.msgId}")

    def __reset_scanned_epcs(self) -> None:
        """
        Clear the set of scanned EPCs.
        """
        self.scanned_epcs.clear()
        logger.info("Scanned EPCs have been reset.")

    def __handle_retrieve_reader_settings(self) -> None:
        """
        Retrieve and publish the current reader settings.
        """

        settings = {
            "readerIP": ConfigService.get_conf(
                section=ConfigSection.READER.value,
                key="uhf_reader_tcp_ip",
            ),
            "readerAnt": ConfigService.get_conf(
                section=ConfigSection.READER.value, key="uhf_reader_ant"
            ),
            "readerPower": ConfigService.get_conf(
                section=ConfigSection.READER.value, key="uhf_reader_power"
            ),
        }
        self.mqtt_gateway.publish(
            topic=PublishTopics.REPLY_SETTINGS.value,
            payload=dumps({"metadata": settings, "message": "Ok"}).encode(),
        )

    def __handle_update_settings(self, settings: dict[str, str]) -> None:
        """
        Prompt user to input a valid IPv4 address for the reader.
        """
        try:

            if is_ipv4(settings.get("readerIP")) is False:
                raise ValueError("Invalid IP address format.")
            if not (1 <= int(settings.get("readerAnt", 0)) <= 4):
                raise ValueError("Antenna value must be between 1 and 4.")
            if not (5 <= int(settings.get("readerPower", 0)) <= 30):
                raise ValueError("Power value must be between 5 and 30.")

            ConfigService.set_conf(
                section=ConfigSection.READER.value,
                key="uhf_reader_tcp_ip",
                value=settings.get("readerIP"),
            )
            ConfigService.set_conf(
                section=ConfigSection.READER.value,
                key="uhf_reader_ant",
                value=settings.get("readerAnt"),
            )
            ConfigService.set_conf(
                section=ConfigSection.READER.value,
                key="uhf_reader_power",
                value=settings.get("readerPower"),
            )

            self.reader_ip = str(settings.get("readerIP", self.reader_ip))
            self.reader_ant = str(settings.get("readerAnt", self.reader_ant))
            self.reader_power = str(settings.get("readerPower", self.reader_power))

            logger.info("Reader settings updated successfully.")

            self.is_reading = False
            Thread(target=self.__publish_connection_status, daemon=True).start()
            Thread(target=self.__handle_stop_reading, daemon=True).start()

            self.mqtt_gateway.publish(
                topic=PublishTopics.REPLY_SETTINGS.value,
                payload=dumps(
                    {"metadata": settings, "message": "Ok", "error": None}
                ).encode(),
            )
        except Exception as e:
            logger.info("Invalid IP address. Please try again.")

            self.mqtt_gateway.publish(
                topic=PublishTopics.REPLY_SETTINGS.value,
                payload=dumps(
                    {
                        "metadata": settings,
                        "message": "Failed to update settings.",
                        "error": e,
                    }
                ).encode(),
            )

    def __apply_reader_configurations(self) -> None:
        if self.reader_instance is None:
            logger.warning("Reader instance is not initialized.")
            return

        # * Set beep sound
        self.reader_instance.sendSynMsg(MsgAppSetBeep(0, 0))

        # * Setup reader power
        FALLBACK_POWER_VALUE: int = 10

        reader_power = (
            FALLBACK_POWER_VALUE
            if self.reader_power == ""
            or self.reader_power is None
            or not self.reader_power.isdigit()
            else int(self.reader_power)
        )
        dict_power = {
            "1": reader_power,
            "2": reader_power,
            "3": reader_power,
            "4": reader_power,
        }
        self.reader_instance.sendSynMsg(MsgBaseSetPower(**dict_power))

        # * Setup reader antenna

        reader_ant = (
            EnumG.AntennaNo_1.value
            if self.reader_ant == ""
            or self.reader_ant is None
            or not self.reader_ant.isdigit()
            else int(self.reader_ant)
        )

        self.reader_instance.sendSynMsg(
            MsgBaseInventoryEpc(
                antennaEnable=reader_ant,
                inventoryMode=EnumG.InventoryMode_Inventory.value,
            )
        )

    def __handle_open_reader_connection(self):

        if self.reader_instance is None:
            self.reader_instance = GClient()

        self.is_reader_connection_ready = self.reader_instance.openTcp(
            (self.reader_ip, int(self.reader_port))
        )
        if self.is_reader_connection_ready:
            self.reader_instance.callEpcOver = self.__handle_receive_epc_end
            self.reader_instance.callEpcInfo = self.__handle_receive_epc
        else:
            logger.warning(
                "Cannot to connect to the reader. Please check your TCP/IP settings, and device connection."
            )
        self.__publish_connection_status()

    def __handle_close_reader_connection(self):
        self.is_reader_connection_ready = False
        if self.reader_instance is not None:
            self.reader_instance.close()
            self.reader_instance.callTcpDisconnect
            self.reader_instance = None
            self.is_reading = False
        self.__publish_connection_status()

    def __restart_reader_connection(self):
        if self.reader_instance is None:
            self.reader_instance = GClient()

        self.reader_instance.openTcp((self.reader_ip, int(self.reader_port)))
        self.reader_instance.sendSynMsg(MsgBaseStop())
        self.reader_instance.close()
        self.reader_instance.callTcpDisconnect
        self.reader_instance = None

        logger.info("Gracefully restarted the reader connection.")

    def __handle_start_reading(self):
        self.is_reading = True
        self.__publish_connection_status()
        self.__apply_reader_configurations()
        logger.info("Started reading EPC.")

    def __handle_stop_reading(self):
        self.is_reading = False
        self.__publish_connection_status()
        logger.info("Stopped reading EPC.")
        if self.reader_instance is None:
            return
        self.reader_instance.sendSynMsg(MsgBaseStop())

    # endregion


if __name__ == "__main__":
    app = Application()
    app.bootstrap()
