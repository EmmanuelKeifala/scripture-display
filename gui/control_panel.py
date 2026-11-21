import tkinter as tk
from tkinter import ttk, scrolledtext

class ControlPanel:
    DEFAULT_SOURCE = "System default"
    
    def __init__(self, root):
        self.root = root
        self.root.title("Scripture Display - Control Panel")
        # The app is DPI-aware, so scale the window with the screen's scaling (150% etc.)
        dpi_scale = max(1.0, self.root.winfo_fpixels('1i') / 96)
        self.root.geometry(f"{int(760 * dpi_scale)}x{int(800 * dpi_scale)}")

        self.is_listening = False
        self.on_start_callback = None
        self.on_stop_callback = None
        self.on_lookup_callback = None
        self.on_clear_callback = None
        self.on_toggle_display_callback = None
        self.on_detect_callback = None
        self.on_source_callback = None
        self.list_sources_callback = None
        self.on_fullscreen_callback = None
        self.list_screens_callback = None   # returns list of Monitor
        self.on_screen_callback = None      # called with the chosen Monitor
        self._screens = {}

        self._build_ui()
    
    def _build_ui(self):
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        control_frame = tk.LabelFrame(main_frame, text="Controls", padx=10, pady=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_button = tk.Button(
            control_frame,
            text="Start Listening",
            command=self._on_start,
            bg='green',
            fg='white',
            font=('Arial', 12, 'bold'),
            height=2
        )
        self.start_button.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.stop_button = tk.Button(
            control_frame,
            text="Stop Listening",
            command=self._on_stop,
            bg='red',
            fg='white',
            font=('Arial', 12, 'bold'),
            height=2,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        settings_frame = tk.LabelFrame(main_frame, text="Settings", padx=10, pady=10)
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(settings_frame, text="Translation:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.translation_var = tk.StringVar(value="KJV")
        self.translation_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.translation_var,
            values=["KJV"],
            state="readonly",
            width=15
        )
        self.translation_combo.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        tk.Label(settings_frame, text="Advance/clear after (s, 0 = never):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.auto_clear_var = tk.StringVar(value="10")
        auto_clear_spin = tk.Spinbox(
            settings_frame,
            from_=0,
            to=300,
            textvariable=self.auto_clear_var,
            width=17
        )
        auto_clear_spin.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)

        self.auto_advance_var = tk.BooleanVar(value=True)
        self.auto_advance_button = tk.Button(
            settings_frame,
            command=self._toggle_auto_advance,
            font=('Arial', 9, 'bold'),
            fg='white',
            width=20
        )
        self.auto_advance_button.grid(row=1, column=2, sticky=tk.W, pady=5, padx=5)
        self._update_auto_advance_button()
        
        tk.Label(settings_frame, text="Detection Confidence:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.confidence_var = tk.DoubleVar(value=0.7)
        confidence_scale = tk.Scale(
            settings_frame,
            from_=0.1,
            to=1.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            variable=self.confidence_var,
            length=150
        )
        confidence_scale.grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)
        
        tk.Label(settings_frame, text="Audio source:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.source_var = tk.StringVar(value=self.DEFAULT_SOURCE)
        self.source_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.source_var,
            values=[self.DEFAULT_SOURCE],
            state="readonly",
            width=50,
            # Re-read the attached devices each time the list is opened
            postcommand=self._refresh_sources
        )
        self.source_combo.grid(row=3, column=1, columnspan=2, sticky=tk.W, pady=5, padx=5)
        self.source_combo.bind("<<ComboboxSelected>>", self._on_source_selected)

        tk.Label(settings_frame, text="Display screen:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.screen_var = tk.StringVar()
        self.screen_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.screen_var,
            state="readonly",
            width=30,
            # Re-read monitors each time, so a projector plugged in later shows up
            postcommand=self.refresh_screens
        )
        self.screen_combo.grid(row=4, column=1, sticky=tk.W, pady=5, padx=5)
        self.screen_combo.bind("<<ComboboxSelected>>", self._on_screen_selected)

        manual_frame = tk.LabelFrame(main_frame, text="Manual Verse Input", padx=10, pady=10)
        manual_frame.pack(fill=tk.X, pady=(0, 10))
        
        input_row = tk.Frame(manual_frame)
        input_row.pack(fill=tk.X)
        
        tk.Label(input_row, text="Book:").pack(side=tk.LEFT, padx=(0, 5))
        self.book_var = tk.StringVar()
        self.book_entry = tk.Entry(input_row, textvariable=self.book_var, width=15)
        self.book_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Label(input_row, text="Ch:").pack(side=tk.LEFT, padx=(10, 5))
        self.chapter_var = tk.StringVar()
        self.chapter_entry = tk.Entry(input_row, textvariable=self.chapter_var, width=5)
        self.chapter_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Label(input_row, text="Verse:").pack(side=tk.LEFT, padx=(10, 5))
        self.verse_var = tk.StringVar()
        self.verse_entry = tk.Entry(input_row, textvariable=self.verse_var, width=10)
        self.verse_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Label(input_row, text="(e.g., '1' or '1-3')").pack(side=tk.LEFT, padx=5)
        
        button_row = tk.Frame(manual_frame)
        button_row.pack(fill=tk.X, pady=(10, 0))
        
        tk.Button(
            button_row,
            text="Display Verse",
            command=self._on_lookup,
            bg='blue',
            fg='white',
            font=('Arial', 10, 'bold')
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_row,
            text="Clear Display",
            command=self._on_clear,
            bg='orange',
            fg='white',
            font=('Arial', 10, 'bold')
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_row,
            text="Toggle Display Window",
            command=self._on_toggle_display,
            font=('Arial', 10)
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            button_row,
            text="Fullscreen On/Off",
            command=self._on_fullscreen,
            font=('Arial', 10)
        ).pack(side=tk.LEFT, padx=5)
        
        test_frame = tk.LabelFrame(main_frame, text="Test Scripture Detection", padx=10, pady=10)
        test_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(test_frame, text="Enter text to test detection:").pack(anchor=tk.W)
        
        self.test_text = tk.Text(test_frame, height=3, wrap=tk.WORD, font=('Arial', 9))
        self.test_text.pack(fill=tk.X, pady=(5, 5))
        
        tk.Button(
            test_frame,
            text="Detect & Display Scripture",
            command=self._on_detect,
            bg='purple',
            fg='white',
            font=('Arial', 10, 'bold')
        ).pack(pady=(0, 5))
        
        status_frame = tk.LabelFrame(main_frame, text="Status Log", padx=10, pady=10)
        status_frame.pack(fill=tk.BOTH, expand=True)
        
        self.status_text = scrolledtext.ScrolledText(
            status_frame,
            wrap=tk.WORD,
            font=('Courier', 9),
            height=12
        )
        self.status_text.pack(fill=tk.BOTH, expand=True)
        self.status_text.config(state=tk.DISABLED)
        
        self.log_status("System ready. Click 'Start Listening' to begin.")
    
    def _refresh_sources(self):
        self._sources = self.list_sources_callback() if self.list_sources_callback else {}
        self.source_combo['values'] = [self.DEFAULT_SOURCE] + list(self._sources)
    
    def refresh_screens(self):
        monitors = self.list_screens_callback() if self.list_screens_callback else []
        self._screens = {m.label: m for m in monitors}
        labels = list(self._screens)
        self.screen_combo['values'] = labels
        if labels and self.screen_var.get() not in self._screens:
            # Default to the first non-main screen: usually the projector
            secondary = [m.label for m in monitors if not m.primary]
            self.screen_var.set(secondary[0] if secondary else labels[0])

    def get_selected_screen(self):
        if not self._screens:
            self.refresh_screens()
        return self._screens.get(self.screen_var.get())

    def _on_screen_selected(self, event=None):
        monitor = self.get_selected_screen()
        if monitor and self.on_screen_callback:
            self.on_screen_callback(monitor)

    def _on_source_selected(self, event=None):
        if self.on_source_callback:
            label = self.source_var.get()
            self.on_source_callback(label, self._sources.get(label))
    
    def _on_start(self):
        if self.on_start_callback:
            self.on_start_callback()
    
    def _on_stop(self):
        if self.on_stop_callback:
            self.on_stop_callback()
    
    def _on_lookup(self):
        if self.on_lookup_callback:
            book = self.book_var.get().strip()
            chapter = self.chapter_var.get().strip()
            verse = self.verse_var.get().strip()
            translation = self.translation_var.get()
            
            if book and chapter and verse:
                self.on_lookup_callback(book, chapter, verse, translation)
            else:
                self.log_status("Error: Please enter book, chapter, and verse")
    
    def _on_clear(self):
        if self.on_clear_callback:
            self.on_clear_callback()
    
    def _on_toggle_display(self):
        if self.on_toggle_display_callback:
            self.on_toggle_display_callback()
    
    def _on_fullscreen(self):
        if self.on_fullscreen_callback:
            self.on_fullscreen_callback()

    def _toggle_auto_advance(self):
        self.auto_advance_var.set(not self.auto_advance_var.get())
        self._update_auto_advance_button()
        state = "ON" if self.auto_advance_var.get() else "OFF"
        self.log_status(f"Auto-advance to next verse: {state}")

    def _update_auto_advance_button(self):
        if self.auto_advance_var.get():
            self.auto_advance_button.config(text="Auto-advance: ON", bg='green', activebackground='dark green')
        else:
            self.auto_advance_button.config(text="Auto-advance: OFF", bg='gray', activebackground='dim gray')

    def is_auto_advance_enabled(self):
        return self.auto_advance_var.get()

    def _on_detect(self):
        if self.on_detect_callback:
            text = self.test_text.get(1.0, tk.END).strip()
            if text:
                self.on_detect_callback(text)
            else:
                self.log_status("Error: Please enter text to test detection")
    
    def set_listening_state(self, is_listening):
        self.is_listening = is_listening
        if is_listening:
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
        else:
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
    
    def log_status(self, message):
        print(message)
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
    
    def get_auto_clear_seconds(self):
        try:
            return max(0, int(self.auto_clear_var.get()))
        except ValueError:
            return 10
    
    def get_translation(self):
        return self.translation_var.get()
    
    def get_confidence_threshold(self):
        return self.confidence_var.get()
    
    def update_translations(self, translations):
        self.translation_combo['values'] = translations
        if translations and self.translation_var.get() not in translations:
            self.translation_var.set(translations[0])
