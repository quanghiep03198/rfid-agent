from uhf.reader import *
from helpers.configuration import ConfigService
from helpers.logger import logger
from ipaddress import ip_address
from helpers.is_ipv4 import is_ipv4, get_ipv4_type_a
from socketio import AsyncServer, ASGIApp
from aiohttp import web
from asyncio import gather, run, sleep
from constants import Actions, ReaderConnectionState, ReaderPlayState


class Application:

    HOST = get_ipv4_type_a()
    PORT = 3198

    reader_instance: GClient | None = None

    reader_ip: str = ConfigService.get_env("UHF_READER_TCP_IP")
    reader_port: int = ConfigService.get_env("UHF_READER_TCP_PORT", int)

    @property
    def playstate(self):
        return self.__playstate

    @playstate.setter
    def playstate(self, state: ReaderPlayState):
        self.__playstate = state

    @property
    def scanned_epcs(self):
        return self.__scanned_epcs

    @scanned_epcs.setter
    def scanned_epcs(self, data: set[str]):
        self.__scanned_epcs = data

    def __init__(self):
        self.__playstate = ReaderPlayState.PAUSING.value
        self.__scanned_epcs: set[str] = set()
        self.gateway = web.Application()

    def __connection_health_check(self):
        logger.info(f"Reader IP from config: {self.reader_ip}")
        if not is_ipv4(self.reader_ip):
            while self.__set_config_reader_ip() == False:
                result = self.__set_config_reader_ip()
                if result:
                    break

    async def __handle_receive_epc(self, data: LogBaseEpcInfo):
        # Skip if already scanned
        if data.epc in self.scanned_epcs:
            return
        logger.info(f"New EPC detected: {data.epc}")
        self.scanned_epcs.add(data.epc)
        await socket.emit("data", data.epc.upper())

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

    async def __handle_close_reader_connection(self):
        await gather(
            socket.emit(
                "connection", {"signal": ReaderConnectionState.DISCONNECTING.value}
            ),
            socket.emit("playstate", {"signal": ReaderPlayState.PAUSING.value}),
        )
        if self.reader_instance is not None:
            self.reader_instance.close()
            self.reader_instance.callTcpDisconnect
            self.reader_instance = None
            self.playstate = ReaderPlayState.PAUSING.value

    async def __handle_open_reader_connection(self):
        await socket.emit(
            "connection", {"signal": ReaderConnectionState.CONNECTING.value}
        )
        if self.reader_instance is None:
            self.reader_instance = GClient()
        if self.reader_instance.openTcp((self.reader_ip, self.reader_port)):
            self.reader_instance.callEpcOver = self.__handle_receive_epc_end
            self.reader_instance.callEpcInfo = lambda data: run(
                self.__handle_receive_epc(data)
            )

    async def handle_toggle_connect_reader(self, signal: str):
        match signal:
            case Actions.DISCONNECT.value:
                await self.__handle_close_reader_connection()
            case Actions.CONNECT.value:
                await self.__handle_open_reader_connection()

    async def __handle_start_reading(self):
        await socket.emit("playstate", {"signal": ReaderPlayState.PLAYING.value})

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

        self.playstate = ReaderPlayState.PLAYING.value

    async def __handle_stop_reading(self):
        await socket.emit("playstate", {"signal": ReaderPlayState.PAUSING.value})

        res = self.reader_instance.sendSynMsg(MsgBaseStop())
        if isinstance(res, int):
            logger.info(f"Stop reading signal :>>>> {res}")

    async def handle_toggle_reading(self, signal: Actions):
        match signal:
            case Actions.PLAY.value:
                await self.__handle_start_reading()
            case Actions.PAUSE.value:
                await self.__handle_stop_reading()

    def __bootstrap__(self):
        self.__connection_health_check()
        web.run_app(self.gateway, host=self.HOST, port=self.PORT)


if __name__ == "__main__":
    socket = AsyncServer(cors_allowed_origins="*")
    app = Application()
    socket.attach(app.gateway)

    @socket.event
    async def connect(sid, _environ):
        logger.info(f"Client connected: {sid}")
        await gather(
            socket.emit(
                "connection",
                {
                    "signal": (
                        ReaderConnectionState.CONNECTING.value
                        if app.reader_instance is not None
                        else ReaderConnectionState.DISCONNECTING.value
                    )
                },
                to=sid,
            ),
            socket.emit("playstate", {"signal": app.playstate}, to=sid),
            socket.emit(
                "settings",
                {
                    "ip": app.reader_ip,
                    "port": app.reader_port,
                },
                to=sid,
            ),
        )

    @socket.on("connection")
    async def on_rfid_connection_change(_, data: dict):
        print(data)
        await app.handle_toggle_connect_reader(data.get("signal"))

    @socket.on("playstate")
    async def on_rfid_playstate_change(_, data: dict):
        print(data)
        await app.handle_toggle_reading(data.get("signal"))

    @socket.on("data")
    async def on_rfid_playstate_change(_sid, _data):
        app.scanned_epcs.clear()

    # @socket.on("settings")
    # def on_settings_change(_, data: dict):
    #     logger.debug(data)

    app.__bootstrap__()
