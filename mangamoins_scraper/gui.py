"""Tkinter GUI for downloading a MangaMoins chapter as a PDF.

Kept deliberately thin: all scraping/PDF logic lives in scraper.py and
pdf_builder.py, this module only wires it to widgets and runs it off the
Tk main thread via a background worker + event queue (Tk is not
thread-safe, so the worker never touches widgets directly).
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from .pdf_builder import build_pdf
from .scraper import MangaMoinsScraper, ScraperError

WINDOW_TITLE = "MangaMoins vers PDF"
MISSING_BROWSER_MARKER = "Executable doesn't exist"

# Playwright's bundled Node driver otherwise resolves its default browser
# cache relative to its own install location. When frozen by PyInstaller
# that location is a fresh temp folder wiped after every run, so without
# this override Chromium would need to be re-downloaded (and fail to be
# found) on every single launch instead of once.
_BROWSERS_PATH = Path(
    os.environ.get("LOCALAPPDATA", str(Path.home()))
) / "MangaMoins-to-PDF" / "browsers"
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(_BROWSERS_PATH))


def default_output_name(target: str) -> str:
    """Derive a default PDF filename (e.g. 'OP1188.pdf') from a slug or URL."""
    target = target.strip()
    if not target:
        return "chapitre.pdf"
    try:
        slug = MangaMoinsScraper.extract_slug(target)
    except ScraperError:
        slug = "chapitre"
    return f"{slug}.pdf"


def is_missing_browser_error(exc: BaseException) -> bool:
    """True if *exc* looks like Playwright's "browser not installed" error."""
    return MISSING_BROWSER_MARKER in str(exc)


def default_download_directory() -> Path:
    """Best-effort default folder for suggested output paths."""
    downloads = Path.home() / "Downloads"
    return downloads if downloads.is_dir() else Path.cwd()


class _DownloadWorker(threading.Thread):
    """Runs the scrape + PDF build off the Tk main thread."""

    def __init__(
        self,
        target: str,
        output_path: Path,
        events: "queue.Queue[tuple]",
    ) -> None:
        super().__init__(daemon=True)
        self.target = target
        self.output_path = output_path
        self.events = events

    def run(self) -> None:
        scraper = MangaMoinsScraper()
        try:
            chapter = self._get_chapter(scraper)
        except Exception as exc:  # noqa: BLE001 - reported to the UI, not raised
            self.events.put(("error", str(exc)))
            return

        total = len(chapter.image_urls)
        self.events.put(("progress-max", total))

        images: list[bytes] = []
        for index, url in enumerate(chapter.image_urls, start=1):
            self.events.put(
                ("status", f"Téléchargement de la page {index}/{total}...")
            )
            self.events.put(("log", f"[{index}/{total}] {url}"))
            try:
                images.append(scraper.download_image(url, chapter.referer))
            except Exception as exc:  # noqa: BLE001
                self.events.put(("log", f"  Erreur de téléchargement : {exc}"))
            self.events.put(("progress", index))

        if not images:
            self.events.put(("error", "Aucune image n'a pu être téléchargée."))
            return

        self.events.put(("status", "Génération du PDF..."))
        try:
            build_pdf(images, self.output_path)
        except Exception as exc:  # noqa: BLE001
            self.events.put(
                ("error", f"Erreur lors de la génération du PDF : {exc}")
            )
            return

        self.events.put(("done", len(images), self.output_path))

    def _get_chapter(self, scraper: MangaMoinsScraper):
        try:
            return scraper.get_chapter_pages(self.target)
        except Exception as exc:  # noqa: BLE001
            if not is_missing_browser_error(exc):
                raise

        self.events.put(
            ("status", "Téléchargement du navigateur intégré (une seule fois)...")
        )
        self._install_chromium()
        return scraper.get_chapter_pages(self.target, force_playwright=True)

    @staticmethod
    def _install_chromium() -> None:
        """Install Playwright's Chromium build in-process.

        Shells out via Playwright's own CLI entry point instead of
        `python -m playwright`, because a frozen executable has no
        separate interpreter to invoke with `-m`.
        """
        from playwright.__main__ import main as playwright_main

        original_argv = sys.argv
        sys.argv = ["playwright", "install", "chromium"]
        try:
            playwright_main()
        except SystemExit as exc:
            if exc.code not in (0, None):
                raise RuntimeError(
                    f"Échec du téléchargement du navigateur (code {exc.code})."
                ) from exc
        finally:
            sys.argv = original_argv


class MangaMoinsApp:
    """Main application window."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry("620x460")
        self.root.minsize(520, 400)

        self.events: "queue.Queue[tuple]" = queue.Queue()
        self.worker: Optional[_DownloadWorker] = None
        self._output_is_custom = False

        self.target_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.status_var = tk.StringVar(
            value="Entrez un slug ou une URL de chapitre pour commencer."
        )

        self.target_var.trace_add("write", self._on_target_changed)

        self._build_widgets()
        self.root.after(100, self._poll_events)

    # -- widget construction ---------------------------------------------

    def _build_widgets(self) -> None:
        frame = ttk.Frame(self.root)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="URL ou slug du chapitre (ex : OP1188)").pack(
            anchor="w", padx=14, pady=(14, 0)
        )
        target_entry = ttk.Entry(frame, textvariable=self.target_var)
        target_entry.pack(fill="x", padx=14)
        target_entry.focus_set()
        target_entry.bind("<Return>", lambda _event: self._start_download())

        ttk.Label(frame, text="Enregistrer le PDF sous").pack(
            anchor="w", padx=14, pady=(12, 0)
        )
        output_row = ttk.Frame(frame)
        output_row.pack(fill="x", padx=14)
        ttk.Entry(output_row, textvariable=self.output_var).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(output_row, text="Parcourir...", command=self._choose_output).pack(
            side="left", padx=(8, 0)
        )

        self.download_button = ttk.Button(
            frame, text="Télécharger", command=self._start_download
        )
        self.download_button.pack(pady=14)

        self.progress = ttk.Progressbar(frame, mode="determinate")
        self.progress.pack(fill="x", padx=14)

        ttk.Label(frame, textvariable=self.status_var, wraplength=580).pack(
            anchor="w", padx=14, pady=(8, 4)
        )

        log_frame = ttk.Frame(frame)
        log_frame.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.log_text = tk.Text(log_frame, height=10, state="disabled", wrap="word")
        scrollbar = ttk.Scrollbar(
            log_frame, orient="vertical", command=self.log_text.yview
        )
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    # -- event handlers ----------------------------------------------------

    def _on_target_changed(self, *_args: object) -> None:
        if self._output_is_custom:
            return
        directory = (
            Path(self.output_var.get()).parent
            if self.output_var.get()
            else default_download_directory()
        )
        self.output_var.set(str(directory / default_output_name(self.target_var.get())))

    def _choose_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Enregistrer le PDF sous",
            defaultextension=".pdf",
            initialfile=default_output_name(self.target_var.get()),
            filetypes=[("Fichier PDF", "*.pdf")],
        )
        if path:
            self.output_var.set(path)
            self._output_is_custom = True

    def _start_download(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            return

        target = self.target_var.get().strip()
        if not target:
            messagebox.showwarning(WINDOW_TITLE, "Entrez un slug ou une URL de chapitre.")
            return

        output_text = self.output_var.get().strip()
        if not output_text:
            messagebox.showwarning(WINDOW_TITLE, "Choisissez où enregistrer le PDF.")
            return

        self._set_busy(True)
        self._clear_log()
        self.progress.configure(value=0, maximum=1)
        self.status_var.set("Recherche du chapitre...")

        self.worker = _DownloadWorker(target, Path(output_text), self.events)
        self.worker.start()

    def _set_busy(self, busy: bool) -> None:
        self.download_button.configure(state="disabled" if busy else "normal")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _append_log(self, text: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # -- background worker polling -----------------------------------------

    def _poll_events(self) -> None:
        try:
            while True:
                self._handle_event(self.events.get_nowait())
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _handle_event(self, event: tuple) -> None:
        kind = event[0]
        if kind == "status":
            self.status_var.set(event[1])
        elif kind == "log":
            self._append_log(event[1])
        elif kind == "progress-max":
            self.progress.configure(maximum=max(event[1], 1))
        elif kind == "progress":
            self.progress.configure(value=event[1])
        elif kind == "error":
            self._set_busy(False)
            self.status_var.set("Échec.")
            messagebox.showerror(WINDOW_TITLE, event[1])
        elif kind == "done":
            count, output_path = event[1], event[2]
            self._set_busy(False)
            self.status_var.set(f"Terminé : {count} page(s) -> {output_path}")
            if messagebox.askyesno(
                WINDOW_TITLE,
                f"PDF créé avec {count} page(s) :\n{output_path}\n\nOuvrir le dossier ?",
            ):
                self._open_containing_folder(output_path)

    @staticmethod
    def _open_containing_folder(path: Path) -> None:
        if sys.platform == "win32":
            os.startfile(path.parent)  # noqa: S606 - user-chosen local path
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path.parent)], check=False)
        else:
            subprocess.run(["xdg-open", str(path.parent)], check=False)


def main() -> None:
    root = tk.Tk()
    MangaMoinsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
