from dataclasses import dataclass
from typing import Any


@dataclass
class RecordArgs:
    format: int
    output_format: str
    channels: int
    rate: int
    chunk: int
    record_seconds: float
    def to_json(self):
        return {
            "format": self.format,
            "output_format": self.output_format,
            "channels": self.channels,
            "rate": self.rate,
            "chunk": self.chunk,
            "record_seconds": self.record_seconds
        }
    @staticmethod
    def from_json(data: dict[str, Any]):
        return RecordArgs(
            format=data["format"],
            output_format=data["output_format"],
            channels=data["channels"],
            rate=data["rate"],
            chunk=data["chunk"],
            record_seconds=data["record_seconds"]
        )


def format_file_size(size: int) -> str:
    size_text = ""
    units = ["TB", "GB", "MB", "KB", "B"]
    units.reverse()
    for unit in units:
        if size > 1024:
            size /= 1024
        else:
            size_text = f"{size:.2f} {unit}"
            break
    return size_text


def format_time(time_seconds: float) -> str:
    time_text = ""
    if time_seconds >= 60 * 60:
        time_text += f"{time_seconds // 3600}h"
        time_seconds %= 3600
    if time_seconds >= 60:
        time_text += f"{time_seconds // 60}m"
        time_seconds %= 60
    time_text += f"{time_seconds:.2f}s"
    return time_text
