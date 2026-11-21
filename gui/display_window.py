import tkinter as tk
from tkinter import font
from gui.monitors import list_monitors

class DisplayWindow:
    # Font sizes are designed for this window size and scaled from there
    BASE_WIDTH = 800
    BASE_HEIGHT = 600
    BASE_REFERENCE_SIZE = 28
    BASE_VERSE_SIZE = 36
    BASE_TRANSLATION_SIZE = 18
    MIN_VERSE_SIZE = 12

    def __init__(self):
        self.window = tk.Toplevel()
        self.window.title("Scripture Display  (F11 / double-click: fullscreen, Esc: exit fullscreen)")
        self.window.configure(bg='black')

        self._fullscreen = False
        self._windowed_geometry = None
        # Start at a size proportional to the screen rather than a fixed 800x600
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        width = max(800, int(screen_w * 0.6))
        height = max(600, int(screen_h * 0.6))
        self.window.geometry(f"{width}x{height}")
        self.window.minsize(400, 300)
        # Closing the window must only hide it; destroying it breaks every later display
        self.window.protocol("WM_DELETE_WINDOW", self.hide)

        self.window.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.window.bind("<Double-Button-1>", lambda e: self.toggle_fullscreen())
        self.window.bind("<Escape>", lambda e: self.exit_fullscreen())

        self.reference_font = font.Font(family='Arial', size=self.BASE_REFERENCE_SIZE, weight='bold')
        self.verse_font = font.Font(family='Arial', size=self.BASE_VERSE_SIZE)
        self.translation_font = font.Font(family='Arial', size=self.BASE_TRANSLATION_SIZE)

        self.reference_label = tk.Label(
            self.window,
            text="",
            font=self.reference_font,
            fg='white',
            bg='black',
            pady=20
        )
        self.reference_label.pack()

        # Packed before the text so it keeps its space when the text is large
        self.translation_label = tk.Label(
            self.window,
            text="",
            font=self.translation_font,
            fg='gray',
            bg='black',
            pady=10
        )
        self.translation_label.pack(side=tk.BOTTOM)

        self.verse_text = tk.Text(
            self.window,
            font=self.verse_font,
            fg='white',
            bg='black',
            wrap=tk.WORD,
            bd=0,
            highlightthickness=0,
            padx=40,
            pady=20,
            cursor='arrow'
        )
        self.verse_text.pack(fill=tk.BOTH, expand=True)
        self.verse_text.tag_configure("center", justify='center')
        self.verse_text.config(state=tk.DISABLED)

        self.auto_clear_after_id = None
        self._resize_after_id = None
        self._last_size = None
        self.window.bind("<Configure>", self._on_configure)

        # Track current scripture for auto-advance
        self.current_scripture = None  # (book, chapter, start_verse, end_verse)
        self.on_advance_callback = None  # Called to advance to next verse
        # Returns True when the timer should advance to the next verse rather than clear
        self.auto_advance_enabled = lambda: True

    def display_verse(self, verse_data, auto_clear_seconds=None, on_advance_callback=None):
        if on_advance_callback:
            self.on_advance_callback = on_advance_callback
        if isinstance(verse_data, list):
            self._display_verse_range(verse_data, auto_clear_seconds)
        else:
            self._display_single_verse(verse_data, auto_clear_seconds)

    def _display_single_verse(self, verse, auto_clear_seconds=None):
        reference = f"{verse['book']} {verse['chapter']}:{verse['verse']}"
        self.reference_label.config(text=reference)

        self._set_text(verse['text'])

        self.translation_label.config(text=verse['translation'])

        # Store current scripture for auto-advance
        self.current_scripture = (
            verse['book'],
            verse['chapter'],
            verse['verse'],
            verse['verse'],
            verse['translation']
        )

        self._schedule_auto_clear(auto_clear_seconds)

    def _display_verse_range(self, verses, auto_clear_seconds=None):
        if not verses:
            return

        first = verses[0]
        last = verses[-1]
        reference = f"{first['book']} {first['chapter']}:{first['verse']}-{last['verse']}"
        self.reference_label.config(text=reference)

        text_content = ""
        for v in verses:
            text_content += f"{v['verse']} {v['text']}\n\n"

        self._set_text(text_content.strip())

        self.translation_label.config(text=first['translation'])

        # Advancing continues after the last verse of the range
        self.current_scripture = (
            first['book'],
            first['chapter'],
            last['verse'],
            last['verse'],
            first['translation']
        )

        self._schedule_auto_clear(auto_clear_seconds)

    def _set_text(self, text):
        self.verse_text.config(state=tk.NORMAL)
        self.verse_text.delete(1.0, tk.END)
        self.verse_text.insert(1.0, text, "center")
        self.verse_text.config(state=tk.DISABLED)
        self._apply_scaling()

    def clear_display(self):
        self.reference_label.config(text="")
        self._set_text("")
        self.translation_label.config(text="")

        if self.auto_clear_after_id:
            self.window.after_cancel(self.auto_clear_after_id)
            self.auto_clear_after_id = None

        # Reset current scripture when manually clearing
        self.current_scripture = None

    def _schedule_auto_clear(self, seconds):
        if self.auto_clear_after_id:
            self.window.after_cancel(self.auto_clear_after_id)
            self.auto_clear_after_id = None

        # 0 / None means keep the verse up until something else replaces it
        if not seconds:
            return

        self.auto_clear_after_id = self.window.after(
            int(seconds * 1000),
            self._on_auto_clear
        )

    def _on_auto_clear(self):
        """Called when the timer expires: advance to the next verse if enabled, else clear."""
        self.auto_clear_after_id = None
        if self.current_scripture and self.on_advance_callback and self.auto_advance_enabled():
            book, chapter, start_verse, end_verse, translation = self.current_scripture
            next_verse = end_verse + 1
            print(f"[DisplayWindow] Auto-advancing from {book} {chapter}:{end_verse} to {book} {chapter}:{next_verse}")
            self.on_advance_callback(book, chapter, next_verse, translation)
        else:
            self.clear_display()

    # --- Scaling -------------------------------------------------------------

    def _on_configure(self, event):
        if event.widget is not self.window:
            return
        size = (event.width, event.height)
        if size == self._last_size:
            return
        self._last_size = size
        # Resizing fires many events; rescale once it settles
        if self._resize_after_id:
            self.window.after_cancel(self._resize_after_id)
        self._resize_after_id = self.window.after(100, self._apply_scaling)

    def _apply_scaling(self):
        self._resize_after_id = None
        width = max(self.window.winfo_width(), 1)
        height = max(self.window.winfo_height(), 1)
        scale = max(0.5, min(width / self.BASE_WIDTH, height / self.BASE_HEIGHT))

        self.reference_font.configure(size=int(self.BASE_REFERENCE_SIZE * scale))
        self.translation_font.configure(size=int(self.BASE_TRANSLATION_SIZE * scale))
        self.reference_label.config(pady=int(20 * scale))
        self.translation_label.config(pady=int(10 * scale))
        self.verse_text.config(padx=int(40 * scale), pady=int(20 * scale))

        # Largest verse size for this window, shrunk until long passages fit
        size = int(self.BASE_VERSE_SIZE * scale)
        self.verse_font.configure(size=size)
        while size > self.MIN_VERSE_SIZE and self._text_overflows():
            size = max(self.MIN_VERSE_SIZE, int(size * 0.9))
            self.verse_font.configure(size=size)

    def _text_overflows(self):
        self.verse_text.update_idletasks()
        available = self.verse_text.winfo_height() - 2 * int(self.verse_text.cget('pady'))
        if available <= 1:
            return False
        try:
            result = self.verse_text.count("1.0", "end", "ypixels")
        except tk.TclError:
            return False
        if isinstance(result, tuple):
            result = result[0] if result else 0
        return (result or 0) > available

    # --- Fullscreen --------------------------------------------------------
    # Done by hand (borderless window sized to a monitor) because Tk's
    # '-fullscreen' on Windows keeps jumping back to the main screen.

    def is_fullscreen(self):
        return self._fullscreen

    def current_monitor(self):
        """The monitor containing the centre of the display window."""
        monitors = list_monitors(self.window)
        if not monitors:
            return None
        self.window.update_idletasks()
        cx = self.window.winfo_rootx() + self.window.winfo_width() // 2
        cy = self.window.winfo_rooty() + self.window.winfo_height() // 2
        for monitor in monitors:
            if monitor.contains(cx, cy):
                return monitor
        return monitors[0]

    def toggle_fullscreen(self, monitor=None):
        if self._fullscreen:
            self.exit_fullscreen()
        else:
            self.enter_fullscreen(monitor)

    def enter_fullscreen(self, monitor=None):
        monitor = monitor or self.current_monitor()
        if monitor is None:
            return
        if not self._fullscreen:
            self._windowed_geometry = self.window.geometry()
        self._fullscreen = True
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.geometry(f"{monitor.width}x{monitor.height}+{monitor.x}+{monitor.y}")
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()
        self.window.after(50, self._apply_scaling)

    def exit_fullscreen(self):
        if not self._fullscreen:
            return
        self._fullscreen = False
        self.window.withdraw()
        self.window.overrideredirect(False)
        if self._windowed_geometry:
            self.window.geometry(self._windowed_geometry)
        self.window.deiconify()
        self.window.after(50, self._apply_scaling)

    def move_to_monitor(self, monitor):
        """Put the (windowed) display in the middle of the given monitor."""
        if self._fullscreen:
            self.enter_fullscreen(monitor)
            return
        self.window.update_idletasks()
        width = min(self.window.winfo_width(), monitor.width)
        height = min(self.window.winfo_height(), monitor.height)
        x = monitor.x + (monitor.width - width) // 2
        y = monitor.y + (monitor.height - height) // 2
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def show(self):
        self.window.deiconify()

    def hide(self):
        self.window.withdraw()

    def is_visible(self):
        return self.window.state() != 'withdrawn'
