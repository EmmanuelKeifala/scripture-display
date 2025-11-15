import tkinter as tk
from tkinter import font

class DisplayWindow:
    def __init__(self):
        self.window = tk.Toplevel()
        self.window.title("Scripture Display")
        self.window.configure(bg='black')
        
        self.window.attributes('-fullscreen', False)
        self.window.geometry("800x600")
        
        self.reference_label = tk.Label(
            self.window,
            text="",
            font=('Arial', 28, 'bold'),
            fg='white',
            bg='black',
            pady=20
        )
        self.reference_label.pack()
        
        self.verse_text = tk.Text(
            self.window,
            font=('Arial', 36),
            fg='white',
            bg='black',
            wrap=tk.WORD,
            bd=0,
            highlightthickness=0,
            padx=40,
            pady=20
        )
        self.verse_text.pack(fill=tk.BOTH, expand=True)
        self.verse_text.config(state=tk.DISABLED)
        
        self.translation_label = tk.Label(
            self.window,
            text="",
            font=('Arial', 18),
            fg='gray',
            bg='black',
            pady=10
        )
        self.translation_label.pack(side=tk.BOTTOM)
        
        self.auto_clear_after_id = None
        
        # Track current scripture for auto-advance
        self.current_scripture = None  # (book, chapter, start_verse, end_verse)
        self.on_advance_callback = None  # Called to advance to next verse
        
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
        
        self.verse_text.config(state=tk.NORMAL)
        self.verse_text.delete(1.0, tk.END)
        self.verse_text.insert(1.0, verse['text'])
        self.verse_text.tag_configure("center", justify='center')
        self.verse_text.tag_add("center", 1.0, "end")
        self.verse_text.config(state=tk.DISABLED)
        
        self.translation_label.config(text=verse['translation'])
        
        # Store current scripture for auto-advance
        self.current_scripture = (
            verse['book'],
            verse['chapter'],
            verse['verse'],
            verse['verse'],
            verse['translation']
        )
        
        if auto_clear_seconds:
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
        
        self.verse_text.config(state=tk.NORMAL)
        self.verse_text.delete(1.0, tk.END)
        self.verse_text.insert(1.0, text_content.strip())
        self.verse_text.config(state=tk.DISABLED)
        
        self.translation_label.config(text=first['translation'])
        
        if auto_clear_seconds:
            self._schedule_auto_clear(auto_clear_seconds)
    
    def clear_display(self):
        self.reference_label.config(text="")
        self.verse_text.config(state=tk.NORMAL)
        self.verse_text.delete(1.0, tk.END)
        self.verse_text.config(state=tk.DISABLED)
        self.translation_label.config(text="")
        
        if self.auto_clear_after_id:
            self.window.after_cancel(self.auto_clear_after_id)
            self.auto_clear_after_id = None
        
        # Reset current scripture when manually clearing
        self.current_scripture = None
    
    def _schedule_auto_clear(self, seconds):
        if self.auto_clear_after_id:
            self.window.after_cancel(self.auto_clear_after_id)
        
        self.auto_clear_after_id = self.window.after(
            int(seconds * 1000),
            self._on_auto_clear
        )
    
    def _on_auto_clear(self):
        """Called when auto-clear timer expires. Advances to next verse instead of clearing."""
        if self.current_scripture and self.on_advance_callback:
            book, chapter, start_verse, end_verse, translation = self.current_scripture
            # Advance to next verse
            next_verse = start_verse + 1
            print(f"[DisplayWindow] Auto-advancing from {book} {chapter}:{start_verse} to {book} {chapter}:{next_verse}")
            self.on_advance_callback(book, chapter, next_verse, translation)
        else:
            # No callback or no scripture tracked, just clear
            self.clear_display()
    
    def toggle_fullscreen(self):
        current = self.window.attributes('-fullscreen')
        self.window.attributes('-fullscreen', not current)
    
    def show(self):
        self.window.deiconify()
    
    def hide(self):
        self.window.withdraw()
