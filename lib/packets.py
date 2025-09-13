from enum import Enum
from typing import Any

from lib.data import RecordArgs


class ClientPackType(Enum):
    NULL = -1
    # Stat - 状态
    INIT = 0
    REC_START = 1
    RECORDING = 2
    REC_PAUSE = 3
    REC_STOP = 4
    SAVING_FILE = 5
    FILE_SAVED = 6
    RECORD_START_ERROR = 7
    RECORD_START_FAILED = 8
    RECORDING_ERROR = 9
    RECORDING_FAILED = 10
    RECORD_STOP_FAILED = 11
    EXIT = 12

    # Data - 数据
    LOG = 13


class ServerPackType(Enum):
    pass


class ClientPack:
    def __init__(self, stat_type: ClientPackType, data: dict[str, Any] = None):
        if data is None:
            data = {}
        self.stat_type = stat_type
        self.data = {"PACK_TYPE": stat_type.value, **data}

    def add_data(self, append_data: dict[str, Any]):
        self.data = {**self.data, **append_data}

    @classmethod
    def from_data(cls, data: dict[str, Any]):
        packet = cls(ClientPackType(data.get("PACK_TYPE", ClientPackType.NULL.value)))
        annotations = cls.__annotations__
        for key, value in data:
            if key in annotations:
                setattr(packet, key, value)
        return packet


class InitPack(ClientPack):
    current_config: dict[str, Any]

    def __init__(self, current_config: dict[str, Any]):
        super().__init__(ClientPackType.INIT, {"current_config": current_config})


class RecSessionPack(ClientPack):
    session_id: str

    def __init__(self, pack_type: ClientPackType, session_id: str):
        super().__init__(pack_type, {"session_id": session_id})


class RecordingStartPack(RecSessionPack):
    rec_args: RecordArgs

    def __init__(self, session_id: str, rec_args: RecordArgs):
        super().__init__(ClientPackType.REC_START, session_id)
        self.add_data({"rec_args": rec_args.to_json()})


class RecordingStatPack(RecSessionPack):
    start: float
    end: str
    def __init__(self, session_id: str, pack_type: ClientPackType, start: float, end: float):
        super().__init__(pack_type, session_id)


class RecordingPack(RecordingStatPack):
    def __init__(self, session_id: str, start: float, end: float):
        super().__init__(session_id, ClientPackType.RECORDING, start, end)


class RecordingPausePack(RecordingStatPack):
    def __init__(self, session_id: str, start: float, end: float):
        super().__init__(session_id, ClientPackType.REC_PAUSE, start, end)


class RecordingStopPack(RecordingStatPack):
    def __init__(self, session_id: str, start: float, end: float):
        super().__init__(session_id, ClientPackType.REC_STOP, start, end)


class SavingFilePack(ClientPack):
    sample_size: int
    args: RecordArgs
    file_path: str
    def __init__(self, sample_size: int, args: RecordArgs, file_path: str):
        super().__init__(ClientPackType.SAVING_FILE,
                         {"sample_size": sample_size, "args": args.to_json(), "file_path": file_path})


class FileSavedPack(ClientPack):
    use_time: float
    file_size: int
    file_path: str
    def __int__(self, use_time: float, file_size: int, file_path: str):
        super().__init__(ClientPackType.FILE_SAVED,
                         {"use_time": use_time, "file_size": file_size, "file_path": file_path})




class SessionStatGen:
    def __init__(self, session_id: str):
        self.session_id = session_id

    @property
    def base_data(self):
        return {"session_id": self.session_id}

    def recording_start(self, rec_args: RecordArgs):
        return ClientPack(ClientPackType.REC_START, {**self.base_data, "rec_args": rec_args.to_json()})

    def recording(self, start: float, stop: float):
        return ClientPack(ClientPackType.RECORDING, {**self.base_data, "start": start, "stop": stop})

    def pause(self, start: float, stop: float):
        return ClientPack(ClientPackType.REC_PAUSE, {**self.base_data, "start": start, "stop": stop})

    def saving(self, length: float):
        return ClientPack(ClientPackType.SAVING_FILE, {**self.base_data, "length": length})

    def file_saved(self, file_path: str, file_size: int):
        return ClientPack(ClientPackType.FILE_SAVED, {**self.base_data, "file_path": file_path, "file_size": file_size})

    def recording_error(self, wait_time: float):
        return ClientPack(ClientPackType.RECORDING_ERROR, {**self.base_data, "wait_time": wait_time})

    def recording_failed(self):
        return ClientPack(ClientPackType.RECORDING_FAILED, self.base_data)


CLIENT_PACK_TYPE_MAP: dict[int, ClientPackType] = {}
