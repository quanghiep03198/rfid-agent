from uhf.reader import *
from helpers.configuration import ConfigService
from helpers.logger import logger
from ipaddress import ip_address
from helpers.is_ipv4 import is_ipv4, get_ipv4_type_a
from time import sleep
from constants import Actions, ReaderPlayState
import gzip
import json
import base64
from decorators.throttle import throttle
import paho.mqtt.client as mqtt
import paho.mqtt.subscribe as mqtt_sub
from aiohttp import web

# import paho.mqtt.subscribe as mqtt


class App:

    HOST = get_ipv4_type_a()
    MQTT_PORT = 1883

    reader_instance: GClient | None = None

    reader_ip: str = ConfigService.get_env("UHF_READER_TCP_IP")
    reader_port: int = ConfigService.get_env("UHF_READER_TCP_PORT", int)

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
        self.web_adapter = web.Application(logger=logger)

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
        print("MQTT connected with result code " + str(reason_code_list))
        client.subscribe("rfid/signal-request")
        client.subscribe("rfid/data")

    def __on_mqtt_gateway_disconnect(
        self,
        client: mqtt.Client,
        userdata,
        flags: mqtt.ConnectFlags,
        reason_code_list: mqtt.ReasonCode,
        properties: mqtt.Union[mqtt.Properties, None],
    ):
        logger.info("MQTT connected with result code " + str(reason_code_list))

    def __on_mqtt_gateway_message(
        self, client: mqtt.Client, userdata, message: mqtt.MQTTMessage
    ):
        # logger.debug(f"Received message on topic {message.topic}: {message.payload}")
        match message.topic:
            case "rfid/signal-request":
                logger.debug(message.payload)

                client.publish(
                    topic="rfid/signal-reply",
                    payload=json.dumps(
                        {
                            "isMQTTConnectionReady": self.mqtt_gateway.is_connected(),
                            "isReaderConnectionReady": self.is_reader_connection_ready,
                            "isReaderPlaying": self.is_reading,
                        }
                    ),
                )
            case "rfid/data":
                logger.debug(message.payload)

    # endregion

    def __publish_connection_status(self):
        self.mqtt_gateway.publish(
            topic="rfid/signal",
            payload=json.dumps(
                {
                    "isMQTTConnectionReady": self.mqtt_gateway.is_connected(),
                    "isReaderConnectionReady": True,
                    "isReaderPlaying": self.is_reading,
                }
            ),
        )

    def __connection_health_check(self):
        logger.info(f"Reader IP from config: {self.reader_ip}")

    def __handle_receive_epc(self, data: LogBaseEpcInfo):
        epc = data.epc.upper()
        if epc in self.scanned_epcs:
            return
        logger.info(f"New EPC detected: {epc}")
        self.scanned_epcs.add(epc)
        # payload = json.dumps(list(self.scanned_epcs)).encode("utf-8")
        self.mqtt_client.publish("rfid", epc)

    # @throttle(1.0)

    def __handle_receive_epc_end(self, log: LogBaseEpcOver):
        logger.info(f"Stopped with message id: >>> {log.msgId}")

    def __set_config_reader_ip():
        """
        Prompt user to input a valid IPv4 address for the reader.
        """
        try:
            __reader_ip = input("Enter reader IP: ")
            ip_address(__reader_ip)
            ConfigService.set_env("UHF_READER_TCP_IP", __reader_ip)
            return True
        except Exception as e:
            logger.info("Invalid IP address. Please try again.")
            return False

    def __handle_close_reader_connection(self):
        self.is_reader_connection_ready = False
        if self.reader_instance is not None:
            self.reader_instance.close()
            self.reader_instance.callTcpDisconnect
            self.reader_instance = None
            self.is_reading = False
        self.mqtt_gateway.publish(
            topic="rfid/signal",
            payload=json.dumps(
                {
                    "isMQTTConnectionReady": self.mqtt_gateway.is_connected(),
                    "isReaderConnectionReady": False,
                    "isReaderPlaying": False,
                }
            ),
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

    def handle_toggle_connect_reader(self, signal: str):
        match signal:
            case Actions.DISCONNECT.value:
                self.__handle_close_reader_connection()
            case Actions.CONNECT.value:
                self.__handle_open_reader_connection()

    def __handle_start_reading(self):

        # * Set beep sound
        self.reader_instance.sendSynMsg(MsgAppSetBeep(0, 0))

        # * Setup reader power
        FALLBACK_POWER_VALUE: int = 10
        reader_power = ConfigService.get_env("UHF_READER_POWER")
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
        reader_ant = ConfigService.get_env(
            "UHF_READER_ANT",
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

        self.is_reading = False

    def __handle_stop_reading(self):
        socket.emit("is_reading", {"signal": False})

        res = self.reader_instance.sendSynMsg(MsgBaseStop())
        if isinstance(res, int):
            logger.info(f"Stop reading signal :>>>> {res}")

    def handle_toggle_reading(self, signal: Actions):
        match signal:
            case Actions.PLAY.value:
                self.__handle_start_reading()
            case Actions.PAUSE.value:
                self.__handle_stop_reading()

    def __bootstrap__(self):

        self.mqtt_gateway.loop_forever()
        try:
            self.mqtt_gateway.publish(
                topic="rfid/signal-reply",
                payload=json.dumps(
                    {
                        "isMQTTConnectionReady": self.mqtt_gateway.is_connected(),
                        "isReaderConnectionReady": self.is_reader_connection_ready,
                        "isReaderPlaying": self.is_reading,
                    }
                ),
            )

        except KeyboardInterrupt:
            logger.info("Shutting down the application.")
            self.__handle_close_reader_connection()
        finally:
            self.mqtt_gateway.loop_stop()
            self.mqtt_gateway.disconnect()
            # self.mqtt_gateway.disconnect()
        # eventlet.wsgi.server(eventlet.listen((self.HOST, self.PORT)), app)


if __name__ == "__main__":
    app = App()
    app.__bootstrap__()

    # socket = AsyncServer(
    #     async_mode="aiohttp",
    #     cors_allowed_origins="*",
    # )
    # socket.attach(app.web_adapter)
    # mqtt_client = mqtt.Client(
    #     callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    # )
    # mqtt_client.connect(host=app.HOST, bind_address=app.HOST)

    # def on_mqtt_connect(_client, _userdata, _flags, rc):
    #     print("MQTT connected with result code " + str(rc))

    # mqtt_client.on_connect = on_mqtt_connect

    # @socket.event
    # def connect(sid, _environ):
    #     logger.info(f"Client connected: {sid}")
    #     gather(
    #         socket.emit(
    #             "connection",
    #             {
    #                 "signal": (
    #                     ReaderConnectionState.CONNECTING.value
    #                     if app.reader_instance is not None
    #                     else ReaderConnectionState.DISCONNECTING.value
    #                 )
    #             },
    #             to=sid,
    #         ),
    #         socket.emit("is_reading", {"signal": app.is_reading}, to=sid),
    #         socket.emit(
    #             "settings",
    #             {
    #                 "ip": app.reader_ip,
    #                 "port": app.reader_port,
    #             },
    #             to=sid,
    #         ),
    #     )

    # @socket.on("connection")
    # def on_rfid_connection_change(_, data: dict):
    #     print(data)
    #     app.handle_toggle_connect_reader(data.get("signal"))

    # @socket.on("is_reading")
    # def on_rfid_playstate_change(_, data: dict):
    #     print(data)
    #     app.handle_toggle_reading(data.get("signal"))

    # @socket.on("data")
    # def on_rfid_playstate_change(_sid, _data):
    #     if _data == "reset":
    #         app.scanned_epcs.clear()
    #     if _data == "refresh":
    #         compressed_data = base64.b64encode(
    #             gzip.compress(json.dumps(list(app.scanned_epcs)).encode("utf-8"))
    #         ).decode("utf-8")
    #         socket.emit("data", compressed_data)

    # @socket.on("settings")
    # def on_settings_change(_, data: dict):
    #     logger.debug(data)

    # app.__bootstrap__()
