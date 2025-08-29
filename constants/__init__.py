from enum import Enum, unique


@unique
class Actions(Enum):
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    START = "start"
    STOP = "stop"
    PING = "ping"


@unique
class PublishTopics(Enum):
    REPLY_SIGNAL = "reply/signal"
    REPLY_DATA = "reply/data"
    REPLY_SETTINGS = "reply/settings"


@unique
class SubscribeTopics(Enum):
    REQUEST_SIGNAL = "request/signal"
    REQUEST_DATA = "request/data"
    REQUEST_SETTINGS = "request/settings"
