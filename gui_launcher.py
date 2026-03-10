#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FerrumBot desktop launcher."""

from __future__ import annotations

import queue
from pathlib import Path
import threading
import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, END, LEFT, W, X

from launcher.service import load_interface_config, probe_controller, resolve_controller_name, run_selected_task
from launcher.settings import LauncherSettings, LauncherSettingsStore
from launcher.task_runner import LauncherTaskRunner


PROJECT_ROOT = Path(__file__).resolve().parent
SETTINGS_PATH = PROJECT_ROOT / "data" / "ui_settings.json"


class FerrumBotLauncher:
    def __init__(self) -> None:
        self.settings_store = LauncherSettingsStore(SETTINGS_PATH)
        self.settings = self.settings_store.load()
        self.interface_config = load_interface_config()
        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.runner = LauncherTaskRunner(run_selected_task)

        self.root = ttk.Window(themename="flatly")
        self.root.title("FerrumBot")
        self.root.geometry("980x700")
        self.root.minsize(900, 640)

        self.driver_backend_var = tk.StringVar(value=self.settings.driver_backend)
        self.port_var = tk.StringVar(value=self.settings.ports[self.settings.driver_backend])
        self.status_var = tk.StringVar(value="Idle")
        self.current_task_var = tk.StringVar(value="-")
        self.connection_var = tk.StringVar(value="未检测")
        self.connection_bootstyle = "secondary"
        self.detecting = False

        self._build_ui()
        self.root.after(150, self._poll_logs)
        self.root.after(250, self._auto_detect_current_driver)

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=20)
        container.pack(fill=BOTH, expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(2, weight=1)

        header_frame = ttk.Frame(container)
        header_frame.pack(fill=X, pady=(0, 16))
        ttk.Label(header_frame, text="FerrumBot", font=("Segoe UI", 24, "bold")).pack(anchor="w")
        ttk.Label(
            header_frame,
            text="Lost Ark guild automation launcher",
            bootstyle="secondary",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(2, 4))
        ttk.Label(
            container,
            text=f"Config: {PROJECT_ROOT / 'assets' / 'interface.json'}",
            bootstyle="secondary",
        ).pack(anchor="w", pady=(0, 12))

        top_row = ttk.Frame(container)
        top_row.pack(fill=X, pady=(0, 14))
        top_row.columnconfigure(0, weight=1)
        top_row.columnconfigure(1, weight=1)

        driver_frame = ttk.Labelframe(top_row, text="Driver Control", padding=14)
        driver_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        radio_row = ttk.Frame(driver_frame)
        radio_row.pack(fill=X, pady=(0, 10))
        ttk.Radiobutton(
            radio_row,
            text="Ferrum",
            variable=self.driver_backend_var,
            value="ferrum",
            command=self._on_driver_change,
        ).pack(side=LEFT, padx=(0, 12))
        ttk.Radiobutton(
            radio_row,
            text="Makcu",
            variable=self.driver_backend_var,
            value="makcu",
            command=self._on_driver_change,
        ).pack(side=LEFT)

        port_row = ttk.Frame(driver_frame)
        port_row.pack(fill=X, pady=(0, 10))
        ttk.Label(port_row, text="COM Port", width=10).pack(side=LEFT)
        self.port_entry = ttk.Entry(port_row, textvariable=self.port_var, width=18)
        self.port_entry.pack(side=LEFT, padx=(0, 10))
        self.port_entry.bind("<FocusOut>", lambda _event: self._persist_port())
        self.port_entry.bind("<Return>", lambda _event: self._persist_port())
        self.detect_button = ttk.Button(
            port_row,
            text="检测连接",
            bootstyle="info-outline",
            command=self._start_detection,
        )
        self.detect_button.pack(side=LEFT)

        state_row = ttk.Frame(driver_frame)
        state_row.pack(fill=X)
        ttk.Label(state_row, text="Connection", width=10).pack(side=LEFT)
        self.connection_label = ttk.Label(state_row, textvariable=self.connection_var, bootstyle=self.connection_bootstyle)
        self.connection_label.pack(side=LEFT)

        task_frame = ttk.Labelframe(top_row, text="Tasks", padding=14)
        task_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ttk.Label(task_frame, text="账号读取", font=("Segoe UI", 11, "bold")).pack(anchor=W)
        ttk.Label(task_frame, text="扫描并索引当前账号角色", bootstyle="secondary").pack(anchor=W, pady=(0, 8))
        self.index_button = ttk.Button(
            task_frame,
            text="账号读取",
            bootstyle="primary",
            command=lambda: self._start_task("AccountIndexing", "账号读取"),
        )
        self.index_button.pack(anchor=W, pady=(0, 12))
        ttk.Label(task_frame, text="全自动捐献", font=("Segoe UI", 11, "bold")).pack(anchor=W)
        ttk.Label(task_frame, text="执行角色切换与完整捐献流程", bootstyle="secondary").pack(anchor=W, pady=(0, 8))
        self.switch_button = ttk.Button(
            task_frame,
            text="全自动捐献",
            bootstyle="success",
            command=lambda: self._start_task("CharacterSwitch", "全自动捐献"),
        )
        self.switch_button.pack(anchor=W, pady=(0, 12))

        ttk.Label(task_frame, text="图像触发", font=("Segoe UI", 11, "bold")).pack(anchor=W)
        ttk.Label(task_frame, text="基于图像检测的半自动触发任务", bootstyle="secondary").pack(anchor=W, pady=(0, 8))
        self.trigger_button = ttk.Button(
            task_frame,
            text="图像触发",
            bootstyle="info",
            command=lambda: self._start_task("TriggerTask", "图像触发"),
        )
        self.trigger_button.pack(anchor=W)

        status_frame = ttk.Labelframe(container, text="Runtime", padding=14)
        status_frame.pack(fill=X, pady=(0, 14))
        for title, variable in (
            ("Driver", self.driver_backend_var),
            ("Port", self.port_var),
            ("State", self.status_var),
            ("Task", self.current_task_var),
        ):
            row = ttk.Frame(status_frame)
            row.pack(fill=X, pady=2)
            ttk.Label(row, text=title, width=10, bootstyle="secondary").pack(side=LEFT)
            ttk.Label(row, textvariable=variable).pack(side=LEFT)

        log_frame = ttk.Labelframe(container, text="Logs", padding=14)
        log_frame.pack(fill=BOTH, expand=True)
        self.log_text = tk.Text(
            log_frame,
            height=18,
            wrap="word",
            relief="flat",
            bg="#f8f9fa",
            fg="#1f2933",
            insertbackground="#1f2933",
        )
        self.log_text.pack(fill=BOTH, expand=True)
        self.log_text.configure(state="disabled")

    def _make_settings(self) -> LauncherSettings:
        ports = dict(self.settings.ports)
        ports[self.driver_backend_var.get()] = self.port_var.get().strip() or ports[self.driver_backend_var.get()]
        return LauncherSettings(driver_backend=self.driver_backend_var.get(), ports=ports)

    def _persist_driver_setting(self) -> None:
        self.settings = self._make_settings()
        self.settings_store.save(self.settings)

    def _persist_port(self) -> None:
        self._persist_driver_setting()

    def _on_driver_change(self) -> None:
        selected = self.driver_backend_var.get()
        self.port_var.set(self.settings.ports.get(selected, "COM2" if selected == "ferrum" else "COM3"))
        self._persist_driver_setting()
        self._start_detection()

    def _set_connection_state(self, message: str, bootstyle: str) -> None:
        self.connection_var.set(message)
        self.connection_bootstyle = bootstyle
        self.connection_label.configure(bootstyle=bootstyle)

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.index_button.configure(state=state)
        self.switch_button.configure(state=state)
        self.trigger_button.configure(state=state)
        self.detect_button.configure(state=state)
        self.port_entry.configure(state=state)
        self.status_var.set("Running" if busy else "Idle")
        for child in self.root.winfo_children():
            pass

    def _set_controls_for_detection(self, detecting: bool) -> None:
        self.detecting = detecting
        state = "disabled" if detecting or self.runner.is_busy() else "normal"
        self.detect_button.configure(state=state)
        self.port_entry.configure(state=state)

    def _append_log(self, line: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert(END, line + "\n")
        self.log_text.see(END)
        self.log_text.configure(state="disabled")

    def _auto_detect_current_driver(self) -> None:
        if not self.runner.is_busy():
            self._start_detection()

    def _start_detection(self) -> None:
        if self.detecting or self.runner.is_busy():
            return
        self._persist_port()
        backend = self.driver_backend_var.get()
        port = self.port_var.get().strip()
        self._set_connection_state("检测中", "warning")
        self._set_controls_for_detection(True)
        self.log_queue.put(f"[Launcher] probe {backend} on {port}")

        def worker() -> None:
            result = probe_controller(self.interface_config, backend, port)
            self.log_queue.put(f"[Launcher] {result.message}")
            self.root.after(0, lambda: self._finish_detection(result.ok, result.message))

        threading.Thread(target=worker, name="launcher-probe", daemon=True).start()

    def _finish_detection(self, ok: bool, message: str) -> None:
        self._set_connection_state(message, "success" if ok else "danger")
        self._set_controls_for_detection(False)

    def _start_task(self, task_name: str, task_label: str) -> None:
        if self.runner.is_busy() or self.detecting:
            return

        self._persist_port()
        try:
            controller_name = resolve_controller_name(self.interface_config, self.driver_backend_var.get())
        except Exception as exc:
            messagebox.showerror("Launcher Error", str(exc))
            return

        self.current_task_var.set(task_label)
        self._set_busy(True)
        self.log_queue.put(f"[Launcher] start {task_name} with {controller_name}")
        self.runner.start(
            task_name=task_name,
            controller_name=controller_name,
            log_writer=self.log_queue.put,
            port=self.port_var.get().strip(),
            on_complete=lambda success: self.log_queue.put(
                f"[Launcher] completed {'SUCCESS' if success else 'FAILED'}"
            ),
        )
        self.root.after(200, self._monitor_runner)

    def _monitor_runner(self) -> None:
        if self.runner.is_busy():
            self.root.after(200, self._monitor_runner)
            return
        self._set_busy(False)
        self._set_controls_for_detection(False)

    def _poll_logs(self) -> None:
        while not self.log_queue.empty():
            self._append_log(self.log_queue.get())
        self.root.after(150, self._poll_logs)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    FerrumBotLauncher().run()


if __name__ == "__main__":
    main()
