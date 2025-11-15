import tkinter as tk
from gui.control_panel import ControlPanel
from gui.display_window import DisplayWindow
from scripture.lookup import ScriptureLookup
from scripture.detector import ScriptureDetector
from audio.processor import AudioProcessor

class ScriptureDisplayApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.lookup = ScriptureLookup()
        self.detector = ScriptureDetector(confidence_threshold=0.7)
        self.audio_processor = AudioProcessor(
            model_size='base',
            transcription_callback=self._on_transcription
        )
        
        self.control_panel = ControlPanel(self.root)
        self.display_window = DisplayWindow()
        
        # Set the advance callback for auto-advance on auto-clear
        self.display_window.on_advance_callback = self.advance_to_next_verse
        
        self.control_panel.on_start_callback = self.start_listening
        self.control_panel.on_stop_callback = self.stop_listening
        self.control_panel.on_lookup_callback = self.manual_lookup
        self.control_panel.on_clear_callback = self.clear_display
        self.control_panel.on_toggle_display_callback = self.toggle_display_window
        self.control_panel.on_detect_callback = self.process_transcription
        
        self._load_translations()
        
        self.display_window.hide()
    
    def _load_translations(self):
        translations = self.lookup.get_available_translations()
        self.control_panel.update_translations(translations)
        self.control_panel.log_status(f"Loaded translations: {', '.join(translations)}")
    
    def _on_transcription(self, text: str, result: dict):
        self.control_panel.log_status(f"Transcribed: {text[:100]}...")
        self.root.after(0, lambda: self.process_transcription(text))
    
    def start_listening(self):
        try:
            self.control_panel.log_status("Starting audio listener...")
            self.control_panel.log_status("Loading Whisper model (this may take a moment)...")
            self.audio_processor.start()
            self.control_panel.set_listening_state(True)
            self.control_panel.log_status("Status: LISTENING - Speak scripture references into your microphone")
        except Exception as e:
            self.control_panel.log_status(f"Error starting audio: {e}")
            self.control_panel.set_listening_state(False)
    
    def stop_listening(self):
        try:
            self.control_panel.log_status("Stopping audio listener...")
            self.audio_processor.stop()
            self.control_panel.set_listening_state(False)
            self.control_panel.log_status("Status: STOPPED")
        except Exception as e:
            self.control_panel.log_status(f"Error stopping audio: {e}")
    
    def manual_lookup(self, book, chapter, verse_input, translation):
        try:
            self.control_panel.log_status(f"Looking up: {book} {chapter}:{verse_input}")
            
            if '-' in verse_input:
                start_verse, end_verse = verse_input.split('-')
                start_verse = int(start_verse.strip())
                end_verse = int(end_verse.strip())
                
                verses = self.lookup.get_verse_range(
                    book, int(chapter), start_verse, end_verse, translation
                )
                
                if verses:
                    auto_clear = self.control_panel.get_auto_clear_seconds()
                    self.display_window.display_verse(verses, auto_clear)
                    self.display_window.show()
                    self.control_panel.log_status(f"Displayed: {book} {chapter}:{start_verse}-{end_verse}")
                else:
                    self.control_panel.log_status(f"Error: Verse range not found")
            else:
                verse_num = int(verse_input.strip())
                verse = self.lookup.get_verse(book, int(chapter), verse_num, translation)
                
                if verse:
                    auto_clear = self.control_panel.get_auto_clear_seconds()
                    self.display_window.display_verse(verse, auto_clear)
                    self.display_window.show()
                    self.control_panel.log_status(f"Displayed: {book} {chapter}:{verse_num}")
                else:
                    self.control_panel.log_status(f"Error: Verse not found")
        
        except ValueError as e:
            self.control_panel.log_status(f"Error: Invalid verse format - {e}")
        except Exception as e:
            self.control_panel.log_status(f"Error: {e}")
    
    def process_transcription(self, text: str):
        confidence_threshold = self.control_panel.get_confidence_threshold()
        self.detector.set_confidence_threshold(confidence_threshold)
        
        print(f"[process_transcription] Input text: '{text}'")
        references = self.detector.detect(text)
        print(f"[process_transcription] detector.detect() returned: {references}")
        
        if references:
            self.control_panel.log_status(f"Detected {len(references)} reference(s) in: '{text[:50]}...'")
            
            for ref in references:
                self.control_panel.log_status(
                    f"  Found: {ref.book} {ref.chapter}:{ref.start_verse}"
                    f"{'-' + str(ref.end_verse) if ref.end_verse != ref.start_verse else ''} "
                    f"({ref.confidence:.0%})"
                )
                
                translation = self.control_panel.get_translation()
                
                if ref.start_verse == ref.end_verse:
                    verse = self.lookup.get_verse(ref.book, ref.chapter, ref.start_verse, translation)
                    if verse:
                        auto_clear = self.control_panel.get_auto_clear_seconds()
                        self.display_window.display_verse(verse, auto_clear)
                        self.display_window.show()
                        self.control_panel.log_status(f"Displayed: {ref.book} {ref.chapter}:{ref.start_verse}")
                else:
                    verses = self.lookup.get_verse_range(
                        ref.book, ref.chapter, ref.start_verse, ref.end_verse, translation
                    )
                    if verses:
                        auto_clear = self.control_panel.get_auto_clear_seconds()
                        self.display_window.display_verse(verses, auto_clear)
                        self.display_window.show()
                        self.control_panel.log_status(
                            f"Displayed: {ref.book} {ref.chapter}:{ref.start_verse}-{ref.end_verse}"
                        )
                
                break
    
    def advance_to_next_verse(self, book, chapter, next_verse, translation):
        """
        Advance to the next verse in the current scripture.
        Called by display window when auto-clear timer expires.
        If a new scripture is detected, this is interrupted.
        """
        try:
            verse = self.lookup.get_verse(book, chapter, next_verse, translation)
            if verse:
                auto_clear = self.control_panel.get_auto_clear_seconds()
                self.display_window.display_verse(verse, auto_clear)
                self.display_window.show()
                self.control_panel.log_status(f"Auto-advanced to: {book} {chapter}:{next_verse}")
            else:
                # Verse not found (end of chapter?), stop auto-advance
                print(f"[DisplayWindow] Verse {book} {chapter}:{next_verse} not found, stopping auto-advance")
                self.display_window.clear_display()
                self.control_panel.log_status(f"End of available verses for {book} {chapter}")
        except Exception as e:
            print(f"[DisplayWindow] Error advancing verse: {e}")
            self.display_window.clear_display()
    
    def clear_display(self):
        self.display_window.clear_display()
        self.control_panel.log_status("Display cleared")
    
    def toggle_display_window(self):
        try:
            if self.display_window.window.state() == 'withdrawn':
                self.display_window.show()
                self.control_panel.log_status("Display window shown")
            else:
                self.display_window.hide()
                self.control_panel.log_status("Display window hidden")
        except tk.TclError:
            self.display_window.show()
            self.control_panel.log_status("Display window shown")
    
    def on_closing(self):
        self.control_panel.log_status("Shutting down...")
        if self.audio_processor.is_active():
            self.audio_processor.stop()
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        self.control_panel.log_status("Scripture Display System initialized")
        self.control_panel.log_status("Ready to display verses")
        self.root.mainloop()

def main():
    app = ScriptureDisplayApp()
    app.run()

if __name__ == "__main__":
    main()
