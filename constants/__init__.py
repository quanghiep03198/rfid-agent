from enum import Enum, unique


@unique
class Actions(Enum):
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    PLAY = "play"
    PAUSE = "pause"


@unique
class ReaderConnectionState(Enum):
    CONNECTING = "connecting"
    DISCONNECTING = "disconnecting"


@unique
class ReaderPlayState(Enum):
    PLAYING = "playing"
    PAUSING = "pausing"
