import tkinter as tk
from tkinter import ttk, scrolledtext

class ControlPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("Scripture Display - Control Panel")
        self.root.geometry("700x750")
        
        self.is_listening = False
        self.on_start_callback = None
        self.on_stop_callback = None
        self.on_lookup_callback = None
        self.on_clear_callback = None
        self.on_toggle_display_callback = None
        self.on_detect_callback = None
        
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
        
        tk.Label(settings_frame, text="Auto-clear (seconds):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.auto_clear_var = tk.StringVar(value="10")
        auto_clear_spin = tk.Spinbox(
            settings_frame,
            from_=5,
            to=60,
            textvariable=self.auto_clear_var,
            width=17
        )
        auto_clear_spin.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
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
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
    
    def get_auto_clear_seconds(self):
        try:
            return int(self.auto_clear_var.get())
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
