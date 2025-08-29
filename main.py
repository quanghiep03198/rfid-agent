from uhf.reader import *
from helpers.configuration import ConfigService, ConfigSection
from constants import Actions, PublishTopics, SubscribeTopics
from helpers.logger import logger

# from ipaddress import ip_address
from helpers.is_ipv4 import is_ipv4, get_ipv4_type_a
import gzip
import json
import base64

import paho.mqtt.client as mqtt

# import threading

# from decorators.throttle import throttle

# import paho.mqtt.subscribe as mqtt


class App:

    HOST = get_ipv4_type_a()
    MQTT_PORT = 1883

    reader_instance: GClient | None = None

    reader_ip: str = ConfigService.get_conf(
        section=ConfigSection.READER.value, key="UHF_READER_TCP_IP"
    )
    reader_port: int = ConfigService.get_conf(
        section=ConfigSection.READER.value, key="UHF_READER_TCP_PORT", serializer=int
    )

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

        self.mqtt_gateway = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )

        self.mqtt_gateway.on_connect = self.__on_mqtt_gateway_connect
        self.mqtt_gateway.on_disconnect = self.__on_mqtt_gateway_disconnect
        self.mqtt_gateway.on_message = self.__on_mqtt_gateway_message
        self.mqtt_gateway.connect(host=self.HOST, bind_address=self.HOST)
        # self.web_adapter = web.Application(logger=logger)

    # region MQTT handlers

    # * MQTT connection handlers
    def __on_mqtt_gateway_connect(
        self,
        client: mqtt.Client,
        userdata,
        flags: mqtt.ConnectFlags,
        reason_code_list: mqtt.ReasonCode,
        properties: mqtt.Union[mqtt.Properties, None],
    ):
        logger.info(f"MQTT connected with status '{str(reason_code_list)}'")
        client.subscribe(SubscribeTopics.REQUEST_SIGNAL.value)
        client.subscribe(SubscribeTopics.REQUEST_DATA.value)
        client.subscribe(SubscribeTopics.REQUEST_SETTINGS.value)

    def __on_mqtt_gateway_disconnect(
        self,
        client: mqtt.Client,
        userdata,
        flags: mqtt.ConnectFlags,
        reason_code_list: mqtt.ReasonCode,
        properties: mqtt.Union[mqtt.Properties, None],
    ):
        client.publish(
            topic=PublishTopics.REPLY_SIGNAL.value,
            payload=json.dumps(
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
        try:
            payload: dict[str, str] = json.loads(message.payload.decode())
        except json.JSONDecodeError:
            logger.error("Invalid JSON payload received.")
            return

        act = payload.get("act")
        match message.topic:
            case SubscribeTopics.REQUEST_SIGNAL.value:
                match act:
                    case Actions.PING.value:
                        self.__publish_connection_status()
                    case Actions.CONNECT.value:
                        self.__handle_open_reader_connection()
                    case Actions.DISCONNECT.value:
                        self.__handle_close_reader_connection()
                    case Actions.START.value:
                        self.__handle_start_reading()
                    case Actions.STOP.value:
                        self.__handle_stop_reading()

                # * Always publish the connection status after handling the action

            case SubscribeTopics.REQUEST_DATA.value:
                if act == "reset":
                    self.__reset_scanned_epcs()

            case SubscribeTopics.REQUEST_SETTINGS.value:
                if act == "get":
                    self.__handle_get_reader_settings()
                if act == "update":
                    self.__handle_change_settings(settings=payload)

    # endregion

    def __publish_connection_status(self):
        self.mqtt_gateway.publish(
            topic=PublishTopics.REPLY_SIGNAL.value,
            payload=json.dumps(
                {
                    "isMQTTConnectionReady": self.mqtt_gateway.is_connected(),
                    "isReaderConnectionReady": self.is_reader_connection_ready,
                    "isReaderPlaying": self.is_reading,
                }
            ).encode(),
        )

    def __reset_scanned_epcs(self):
        self.scanned_epcs.clear()
        logger.info("Scanned EPCs have been reset.")

    def __handle_receive_epc(self, data: LogBaseEpcInfo):
        epc = data.epc.upper()
        if epc in self.scanned_epcs:
            return
        logger.info(f"EPC :>>> {epc}")
        self.scanned_epcs.add(epc)
        compressed_data = self.__compress_data(data=self.scanned_epcs)
        self.mqtt_gateway.publish(
            topic=PublishTopics.REPLY_DATA.value, payload=compressed_data
        )

    def __compress_data(self, data: set[str]) -> str:
        json_data = json.dumps(list(data))
        compressed_data = gzip.compress(json_data.encode())
        encoded_data = base64.b64encode(compressed_data).decode()
        return encoded_data

    def __handle_receive_epc_end(self, log: LogBaseEpcOver):
        logger.info(f"Stopped reading EPC with code: >>> {log.msgId}")

    def __handle_get_reader_settings(self):
        settings = {
            "readerIP": ConfigService.set_conf(
                key="UHF_READER_TCP_IP", value=settings.get("uhf_reader_ip")
            ),
            "readerAnt": ConfigService.set_conf(
                key="UHF_READER_ANT", value=settings.get("uhf_reader_ant")
            ),
            "readerAnt": ConfigService.set_conf(
                key="UHF_READER_ANT", value=settings.get("uhf_reader_ant")
            ),
        }
        self.mqtt_gateway.publish(
            topic=PublishTopics.REPLY_SETTINGS.value,
            payload=json.dumps(settings).encode(),
        )

    def __handle_change_settings(self, settings: dict[str, str]):
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
                key="UHF_READER_TCP_IP", value=settings.get("readerIP")
            )
            ConfigService.set_conf(
                key="UHF_READER_ANT", value=settings.get("readerAnt")
            )
            ConfigService.set_conf(
                key="UHF_READER_POWER", value=settings.get("readerPower")
            )

            return True
        except Exception as e:
            logger.info("Invalid IP address. Please try again.")
            self.mqtt_gateway.publish(
                topic=PublishTopics.REPLY_SETTINGS.value,
                payload=json.dumps(
                    {
                        "success": False,
                        "message": str(e),
                    }
                ).encode(),
            )

    def __handle_close_reader_connection(self):
        self.is_reader_connection_ready = False
        if self.reader_instance is not None:
            self.reader_instance.close()
            self.reader_instance.callTcpDisconnect
            self.reader_instance = None
            self.is_reading = False
        self.mqtt_gateway.publish(
            topic=PublishTopics.REPLY_SIGNAL.value,
            payload=json.dumps(
                {
                    "isMQTTConnectionReady": self.mqtt_gateway.is_connected(),
                    "isReaderConnectionReady": False,
                    "isReaderPlaying": False,
                }
            ).encode(),
        )

    def __handle_open_reader_connection(self):

        if self.reader_instance is None:
            self.reader_instance = GClient()

        self.is_reader_connection_ready = self.reader_instance.openTcp(
            (self.reader_ip, self.reader_port)
        )
        if self.is_reader_connection_ready:
            self.reader_instance.callEpcOver = self.__handle_receive_epc_end
            self.reader_instance.callEpcInfo = self.__handle_receive_epc
        self.__publish_connection_status()

    def __handle_start_reading(self):
        logger.info("Starting reading process...")
        self.is_reading = True
        self.__publish_connection_status()
        # * Set beep sound
        self.reader_instance.sendSynMsg(MsgAppSetBeep(0, 0))

        # * Setup reader power
        FALLBACK_POWER_VALUE: int = 10
        reader_power = ConfigService.get_conf(
            section=ConfigSection.READER.value, key="UHF_READER_POWER"
        )
        reader_power = (
            FALLBACK_POWER_VALUE
            if reader_power == "" or reader_power is None or not reader_power.isdigit()
            else int(reader_power)
        )
        dict_power = {
            "1": reader_power,
            "2": reader_power,
            "3": reader_power,
            "4": reader_power,
        }
        self.reader_instance.sendSynMsg(MsgBaseSetPower(**dict_power))

        # * Setup reader antenna
        reader_ant = ConfigService.get_conf(
            section=ConfigSection.READER.value,
            key="UHF_READER_ANT",
        )
        reader_ant = (
            EnumG.AntennaNo_1.value
            if reader_ant == "" or reader_ant is None or not reader_ant.isdigit()
            else int(reader_ant)
        )
        self.reader_instance.sendSynMsg(
            MsgBaseInventoryEpc(
                antennaEnable=reader_ant,
                inventoryMode=EnumG.InventoryMode_Inventory.value,
            )
        )

    def __handle_stop_reading(self):
        self.is_reading = False
        self.__publish_connection_status()
        res = self.reader_instance.sendSynMsg(MsgBaseStop())
        if isinstance(res, int):
            logger.info(f"Stop reading signal :>>>> {res}")

    def bootstrap(self):
        try:
            self.mqtt_gateway.loop_forever()
            self.mqtt_gateway.publish(
                topic=PublishTopics.REPLY_SIGNAL.value,
                payload=json.dumps(
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
        # eventlet.wsgi.server(eventlet.listen((self.HOST, self.PORT)), app)


if __name__ == "__main__":
    app = App()
    app.bootstrap()
