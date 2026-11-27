#!/usr/bin/env python3
"""Node Core OS graphical launcher for the historical v1.5.6 source."""
from __future__ import annotations
import os
import shutil
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

VERSION = "1.5.6"
DATA = Path.home() / ".node-core"
CORE = DATA / "bin" / "node-core"

class NodeCoreGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Node Core OS · GUI {VERSION}")
        self.geometry("760x520")
        self.minsize(640, 440)
        self.configure(bg="#101820")
        self._build()
        self.refresh()

    def _label(self, parent, text, size=11, color="#dce7ee", bold=False):
        return tk.Label(parent, text=text, bg=parent["bg"], fg=color,
                        font=("DejaVu Sans", size, "bold" if bold else "normal"))

    def _build(self):
        header = tk.Frame(self, bg="#172733", padx=24, pady=20)
        header.pack(fill="x")
        self._label(header, "NODE CORE OS", 22, "#ffffff", True).pack(anchor="w")
        self._label(header, f"byLAEV  ·  GUI {VERSION}  ·  ARM64 package", 10, "#72d6c5").pack(anchor="w", pady=(5,0))
        body = tk.Frame(self, bg="#101820", padx=24, pady=20)
        body.pack(fill="both", expand=True)
        self._label(body, "Node dashboard", 16, "#ffffff", True).pack(anchor="w")
        self.status = tk.Text(body, height=9, bg="#172733", fg="#dce7ee",
                              insertbackground="#ffffff", relief="flat",
                              font=("DejaVu Sans Mono", 10), padx=12, pady=10)
        self.status.pack(fill="x", pady=12)
        actions = tk.Frame(body, bg="#101820")
        actions.pack(fill="x", pady=4)
        self._button(actions, "Launch Node Core", self.launch).pack(side="left", padx=(0,8))
        self._button(actions, "Open data directory", self.open_data).pack(side="left", padx=8)
        self._button(actions, "Refresh status", self.refresh).pack(side="left", padx=8)
        self._label(body, "Storage", 13, "#ffffff", True).pack(anchor="w", pady=(22,4))
        self._label(body, "Local data: ~/.node-core/     Kubo repository: managed separately by Node Core OS",
                    10, "#a9bac5").pack(anchor="w")
        self._label(body, "GUI controls do not publish content or change network settings.",
                    9, "#72d6c5").pack(anchor="w", pady=(18,0))

    def _button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, bg="#176b66", fg="white",
                         activebackground="#23877f", activeforeground="white",
                         relief="flat", padx=14, pady=9, cursor="hand2")

    def refresh(self):
        self.status.delete("1.0", "end")
        self.status.insert("end", f"GUI version: {VERSION}\n")
        self.status.insert("end", f"Architecture: {os.uname().machine}\n")
        self.status.insert("end", f"Data directory: {DATA}\n")
        self.status.insert("end", f"Core launcher: {CORE}\n")
        self.status.insert("end", f"Core installed: {'YES' if CORE.is_file() else 'NO'}\n")
        self.status.insert("end", f"Kubo executable: {shutil.which('ipfs') or 'not found in PATH'}\n")
        self.status.insert("end", f"Desktop session: {os.environ.get('XDG_CURRENT_DESKTOP', 'unknown')}\n")

    def launch(self):
        if not CORE.is_file():
            messagebox.showwarning("Node Core OS not installed",
                "The GUI is installed, but the Node Core engine was not found. Install the original v1.5.6 source first using its documented user-level installer (without sudo).")
            return
        terminal = shutil.which("x-terminal-emulator") or shutil.which("gnome-terminal") or shutil.which("konsole")
        if not terminal:
            messagebox.showerror("Terminal unavailable", "Install a terminal emulator to launch the Node Core text interface.")
            return
        try:
            if terminal.endswith("gnome-terminal"):
                subprocess.Popen([terminal, "--", str(CORE)])
            elif terminal.endswith("konsole"):
                subprocess.Popen([terminal, "-e", str(CORE)])
            else:
                subprocess.Popen([terminal, "-e", str(CORE)])
        except OSError as exc:
            messagebox.showerror("Launch failed", str(exc))

    def open_data(self):
        DATA.mkdir(parents=True, exist_ok=True)
        opener = shutil.which("xdg-open")
        if opener:
            subprocess.Popen([opener, str(DATA)])
        else:
            messagebox.showinfo("Data directory", str(DATA))

if __name__ == "__main__":
    NodeCoreGUI().mainloop()
