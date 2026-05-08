from __future__ import annotations

import struct
import time
from dataclasses import dataclass, field


MAGIC = b"ECAM"
HEADER_FORMAT = "!4sIIBBH"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
PROTOCOL_VERSION = 1


@dataclass
class Packet:
    frame_id: int
    total_size: int
    packet_index: int
    packet_count: int
    payload: bytes


@dataclass
class PartialFrame:
    frame_id: int
    total_size: int
    packet_count: int
    created_at: float = field(default_factory=time.monotonic)
    packets: dict[int, bytes] = field(default_factory=dict)

    def add(self, packet: Packet) -> None:
        if packet.total_size != self.total_size or packet.packet_count != self.packet_count:
            return
        if 0 <= packet.packet_index < self.packet_count:
            self.packets[packet.packet_index] = packet.payload

    def is_complete(self) -> bool:
        return len(self.packets) == self.packet_count

    def build(self) -> bytes | None:
        if not self.is_complete():
            return None
        data = b"".join(self.packets[index] for index in range(self.packet_count))
        if len(data) != self.total_size:
            return None
        return data


def parse_packet(data: bytes, max_frame_bytes: int) -> Packet | None:
    if len(data) < HEADER_SIZE:
        return None
    magic, frame_id, total_size, packet_index, packet_count, payload_size = struct.unpack(
        HEADER_FORMAT,
        data[:HEADER_SIZE],
    )
    if magic != MAGIC or total_size <= 0 or total_size > max_frame_bytes:
        return None
    if packet_count <= 0 or packet_index >= packet_count:
        return None
    payload = data[HEADER_SIZE:]
    if len(payload) != payload_size:
        return None
    return Packet(
        frame_id=frame_id,
        total_size=total_size,
        packet_index=packet_index,
        packet_count=packet_count,
        payload=payload,
    )
