class EngineIOError(Exception): ...
class ContentTooLongError(EngineIOError): ...
class UnknownPacketError(EngineIOError): ...
class QueueEmpty(EngineIOError): ...
class SocketIsClosedError(EngineIOError): ...
class ConnectionError(EngineIOError): ...
