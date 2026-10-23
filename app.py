"""The report program: makes the report, shows a large preview of it, and downloads the PDF
if you want it. Start it by double-clicking "Download Report.bat"."""
import ctypes
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk

import pypdfium2 as pdfium
from PIL import ImageTk

from main import make_report, save_report

if sys.platform == "win32":
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # sharp text on high-resolution screens

PREVIEW_BACKGROUND = "#e8e8e5"
PAGE_BORDER = "#c9c8c2"
PAGE_GAP = 20  # pixels around the pages in the preview


class ReportWindow:
    # Text sizes are in points ("p") so the window looks the same on every screen.
    def __init__(self, root):
        self.root = root
        self.messages = queue.Queue()
        self.pdf = None
        self.pages = []  # the page images, kept here so Tk doesn't throw them away
        self.center = 0  # x position of the middle of the preview

        # A tall window, so a page shows big
        screen_width, screen_height = root.winfo_screenwidth(), root.winfo_screenheight()
        height = int(screen_height * 0.88)
        width = min(int(height * 0.8), screen_width - 40)
        root.geometry(f"{width}x{height}+{(screen_width - width) // 2}+{int(screen_height * 0.02)}")
        root.title("Sales & Returns Report")

        top = ttk.Frame(root, padding="14p")
        top.pack(fill="x")
        top.columnconfigure(0, weight=1)
        ttk.Label(top, text="Sales & Returns Report", font=("Segoe UI", 15, "bold")).grid(row=0, column=0, sticky="w")
        self.button = ttk.Button(top, text="Download PDF", command=self.download)
        self.button.grid(row=0, column=1, rowspan=2, sticky="e", ipadx="6p", ipady="2p")
        self.status = tk.StringVar()
        ttk.Label(top, textvariable=self.status).grid(row=1, column=0, sticky="w", pady=("2p", "8p"))
        self.progress = ttk.Progressbar(top, maximum=100)
        self.progress.grid(row=2, column=0, sticky="ew")
        self.percent = ttk.Label(top, width=5)
        self.percent.grid(row=2, column=1, sticky="w", padx=("8p", 0))

        # The preview: the pages under each other, scrolled with the scrollbar or mouse wheel
        preview = ttk.Frame(root)
        preview.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(preview, background=PREVIEW_BACKGROUND, highlightthickness=0, yscrollincrement=20)
        scrollbar = ttk.Scrollbar(preview, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Configure>", self.keep_centered)
        root.bind_all("<MouseWheel>", lambda event: self.canvas.yview_scroll(-event.delta // 40, "units"))

        root.after(200, self.start)  # start as soon as the window is on screen

    def start(self):
        """Make the report and its preview in the background, so the window doesn't freeze meanwhile."""
        self.button.configure(text="Download PDF", command=self.download)
        self.button.state(["disabled"])
        self.canvas.delete("all")
        self.canvas.create_text(self.center, 60, text="The preview appears here when the report is ready.",
                                fill="#52514e", font=("Segoe UI", 11), tags="centered")
        self.set_progress(0, "Starting...")
        page_width = self.canvas.winfo_width() - 2 * PAGE_GAP
        threading.Thread(target=self.make_preview, args=(page_width,), daemon=True).start()
        self.root.after(100, self.show_messages)

    def make_preview(self, page_width):
        """Runs in the background: makes the report, then draws its pages as images."""
        try:
            # The report itself is 0-95% of the bar, drawing the preview the last 5%
            pdf = make_report(update=lambda percent, message: self.messages.put(("progress", percent * 0.95, message)))
            document = pdfium.PdfDocument(pdf)
            images = [page.render(scale=page_width / page.get_width()).to_pil() for page in document]
            self.messages.put(("ready", pdf, images))
        except Exception as error:  # e.g. no internet connection to the database
            self.messages.put(("error", f"Something went wrong: {error}"))

    def show_messages(self):
        """Show what make_preview() reports, until the preview is ready or something went wrong."""
        while not self.messages.empty():
            kind, *details = self.messages.get()
            if kind == "progress":
                self.set_progress(*details)
                continue
            if kind == "ready":
                self.pdf, images = details
                self.show_pages(images)
                self.set_progress(100, f"Preview of all {len(images)} pages. Download the PDF if it looks right.")
            else:  # "error"
                self.set_progress(0, details[0])
                self.button.configure(text="Try again", command=self.start)
            self.button.state(["!disabled"])
            return
        self.root.after(100, self.show_messages)

    def set_progress(self, percent, message):
        self.progress["value"] = percent
        self.percent.configure(text=f"{percent:.0f}%")
        self.status.set(message)

    def show_pages(self, images):
        """Put the page images under each other, each with a thin border."""
        self.canvas.delete("all")
        self.pages = [ImageTk.PhotoImage(image) for image in images]
        y = PAGE_GAP
        for page in self.pages:
            left = self.center - page.width() // 2
            self.canvas.create_rectangle(left - 1, y - 1, left + page.width(), y + page.height(),
                                         outline=PAGE_BORDER, tags="centered")
            self.canvas.create_image(left, y, image=page, anchor="nw", tags="centered")
            y += page.height() + PAGE_GAP
        self.canvas.configure(scrollregion=(0, 0, 0, y))
        self.canvas.yview_moveto(0)

    def keep_centered(self, event):
        """Keep the pages in the middle when the window changes size."""
        self.canvas.move("centered", event.width // 2 - self.center, 0)
        self.center = event.width // 2

    def download(self):
        self.status.set(save_report(self.pdf))


if __name__ == "__main__":
    window = tk.Tk()
    ReportWindow(window)
    window.mainloop()
