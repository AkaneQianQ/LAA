#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal MAKCU serial smoke test (Legacy ASCII API).

Reference: https://www.makcu.com/en/api
"""

from __future__ import annotations

import argparse
import sys
import time

import serial


PROMPT = b">>>"


def read_until_prompt(ser: serial.Serial, timeout: float) -> bytes:
    start = time.monotonic()
    buf = bytearray()
    while True:
        if time.monotonic() - start > timeout:
            raise TimeoutError(f"timeout waiting prompt >>>, raw={bytes(buf)!r}")
        waiting = ser.in_waiting
        if waiting > 0:
            buf.extend(ser.read(waiting))
            if PROMPT in buf:
                return bytes(buf)
        else:
            time.sleep(0.001)


def send_command(ser: serial.Serial, command: str, timeout: float) -> str:
    wire = f"{command}\r\n".encode("utf-8")
    ser.write(wire)
    raw = read_until_prompt(ser, timeout)
    text = raw.decode("utf-8", errors="replace")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="MAKCU minimal keyboard/mouse serial smoke test")
    parser.add_argument("--port", default="COM5", help="serial port (default: COM5)")
    parser.add_argument("--baudrate", type=int, default=115200, help="baudrate (default: 115200)")
    parser.add_argument("--timeout", type=float, default=1.5, help="read timeout seconds (default: 1.5)")
    parser.add_argument("--x", type=int, default=1280, help="moveto x (default: 1280)")
    parser.add_argument("--y", type=int, default=720, help="moveto y (default: 720)")
    args = parser.parse_args()

    commands = [
        "km.version()",
        f"km.moveto({args.x},{args.y})",
        "km.click(1,1,50)",
        'km.press("esc",50,0)',
    ]

    try:
        with serial.Serial(
            port=args.port,
            baudrate=args.baudrate,
            timeout=args.timeout,
            write_timeout=args.timeout,
        ) as ser:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            print(f"[OK] opened {args.port} @ {args.baudrate}")
            for cmd in commands:
                print(f"[SEND] {cmd}")
                resp = send_command(ser, cmd, args.timeout)
                print(f"[RECV] {resp.strip() or '<empty>'}")
        print("[OK] test finished")
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
