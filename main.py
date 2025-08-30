from uhf.reader import *
from helpers.configuration import ConfigService, ConfigSection
from constants import Actions, PublishTopics, SubscribeTopics
from helpers.logger import logger
from helpers.is_ipv4 import is_ipv4, get_ipv4_type_a
from gzip import compress
from json import loads, dumps, JSONDecodeError
from base64 import b64encode
import paho.mqtt.client as mqtt
from threading import Thread


class Application:

    HOST = get_ipv4_type_a()
    MQTT_PORT = 1883

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

        self.mqtt_gateway = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )

        self.mqtt_gateway.on_connect = self.__on_mqtt_gateway_connect
        self.mqtt_gateway.on_disconnect = self.__on_mqtt_gateway_disconnect
        self.mqtt_gateway.on_message = self.__on_mqtt_gateway_message
        self.mqtt_gateway.connect(host=self.HOST, bind_address=self.HOST)

    def bootstrap(self):
        try:
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
        except KeyboardInterrupt:
            logger.info("Shutting down the application...")
            self.__handle_close_reader_connection()
        finally:
            self.mqtt_gateway.loop_stop()
            self.mqtt_gateway.disconnect()

    # region MQTT handlers
    def __on_mqtt_gateway_connect(
        self,
        client: mqtt.Client,
        userdata,
        flags: mqtt.ConnectFlags,
        reason_code_list: mqtt.ReasonCode,
        properties: mqtt.Union[mqtt.Properties, None],
    ):
        logger.info(f"MQTT connected with status '{str(reason_code_list)}'")
        logger.info(">>> Press Ctrl+C to exit <<<")

        client.subscribe(SubscribeTopics.REQUEST_SIGNAL.value)
        client.subscribe(SubscribeTopics.REQUEST_DATA.value)
        client.subscribe(SubscribeTopics.REQUEST_SETTINGS.value)
        self.__publish_connection_status()
        # self.__handle_get_reader_settings()

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

    def __compress_data(self, data: set[str]) -> str:
        """
        Compress and encode data to be sent over MQTT.
        """

        json_data = dumps(list(data))
        compressed_data = compress(json_data.encode())
        encoded_data = b64encode(compressed_data).decode()
        return encoded_data

    def __handle_receive_epc(self, data: LogBaseEpcInfo) -> None:
        """
        Handle incoming EPC data from the UHF reader.
        """
        epc = data.epc.upper()
        if epc in self.scanned_epcs:
            return
        logger.info(f"EPC :>>> {epc}")
        self.scanned_epcs.add(epc)
        compressed_data = self.__compress_data(data=self.scanned_epcs)
        self.mqtt_gateway.publish(
            topic=PublishTopics.REPLY_DATA.value, payload=compressed_data
        )

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
        self.__publish_connection_status()

    def __handle_close_reader_connection(self):
        self.is_reader_connection_ready = False
        if self.reader_instance is not None:
            self.reader_instance.close()
            self.reader_instance.callTcpDisconnect
            self.reader_instance = None
            self.is_reading = False
        self.mqtt_gateway.publish(
            topic=PublishTopics.REPLY_SIGNAL.value,
            payload=dumps(
                {
                    "isMQTTConnectionReady": self.mqtt_gateway.is_connected(),
                    "isReaderConnectionReady": False,
                    "isReaderPlaying": False,
                }
            ).encode(),
        )

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
