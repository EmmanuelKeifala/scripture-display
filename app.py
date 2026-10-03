import threading
import tkinter as tk
from gui.control_panel import ControlPanel
from gui.display_window import DisplayWindow
from scripture.lookup import ScriptureLookup
from scripture.detector import ScriptureDetector
from audio.capture import list_sources
from audio.processor import AudioProcessor

class ScriptureDisplayApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.lookup = ScriptureLookup()
        self.detector = ScriptureDetector(confidence_threshold=0.7)
        self.audio_processor = AudioProcessor(
            model_size='small.en',
            transcription_callback=self._on_transcription,
            status_callback=lambda message: self.root.after(0, self.control_panel.log_status, message)
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
        self.control_panel.list_sources_callback = list_sources
        self.control_panel.on_source_callback = self.set_audio_source
        
        self._load_translations()
        
        self.display_window.hide()
        self._last_heard = ""
        self._shown = set()
        self._context = None  # (book, chapter) last displayed, for "verse 17" follow-ups
    
    def _load_translations(self):
        translations = self.lookup.get_available_translations()
        self.control_panel.update_translations(translations)
        self.control_panel.log_status(f"Loaded translations: {', '.join(translations)}")
    
    def _on_transcription(self, text: str, final: bool):
        # Called from the transcription thread; Tk must only be touched on its own
        self.root.after(0, self._handle_speech, text, final)
    
    def _handle_speech(self, text: str, final: bool):
        """final=False is a live guess at what is still being said."""
        if final:
            self.control_panel.log_status(f"Heard: {text}")
        self.detector.set_confidence_threshold(self.control_panel.get_confidence_threshold())
        
        # A reference can straddle two utterances ("John chapter 3" ... "verse 16"),
        # so detect on previous + current; _shown stops the same one firing twice
        combined = f"{self._last_heard} {text}".strip()
        references = [ref for ref in self.detector.detect(combined, allow_trailing=final)
                      if self._reference_key(ref) not in self._shown]
        if not references and final and self._context:
            references = self.detector.detect_followup(text, *self._context)
        
        self._show_first(references)
        self._shown.update(self._reference_key(ref) for ref in references)
        if final:
            self._last_heard = text
            self._shown = {self._reference_key(ref) for ref in self.detector.detect(text)}
    
    @staticmethod
    def _reference_key(ref):
        return (ref.book, ref.chapter, ref.start_verse, ref.end_verse)
    
    def start_listening(self):
        self.control_panel.log_status("Starting audio listener...")
        self.control_panel.log_status("Loading Whisper model (this may take a moment)...")
        self.control_panel.start_button.config(state=tk.DISABLED)
        # Model load (and first-run download) blocks, so keep it off the Tk thread
        threading.Thread(target=self._start_audio, daemon=True).start()

    def _start_audio(self):
        try:
            self.audio_processor.start()
            self.root.after(0, self._on_audio_started, None)
        except Exception as e:
            self.root.after(0, self._on_audio_started, e)

    def _on_audio_started(self, error):
        if error:
            self.control_panel.log_status(f"Error starting audio: {error}")
            self.control_panel.set_listening_state(False)
        else:
            self.control_panel.set_listening_state(True)
            self.control_panel.log_status("Status: LISTENING - Speak scripture references into your microphone")
    
    def set_audio_source(self, label, source):
        try:
            self.audio_processor.set_source(source)
            self.control_panel.log_status(f"Audio source: {label}")
        except Exception as e:
            self.control_panel.log_status(f"Could not open {label}: {e}")
    
    def stop_listening(self):
        try:
            self.control_panel.log_status("Stopping audio listener...")
            self.audio_processor.stop()
            self._last_heard = ""
            self._shown = set()
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
        self.detector.set_confidence_threshold(self.control_panel.get_confidence_threshold())
        if not self._show_first(self.detector.detect(text)):
            self.control_panel.log_status("No displayable reference found")
    
    def _show_first(self, references) -> bool:
        translation = self.control_panel.get_translation()
        auto_clear = self.control_panel.get_auto_clear_seconds()
        
        for ref in references:
            label = f"{ref.book} {ref.chapter}:{ref.start_verse}"
            if ref.start_verse == ref.end_verse:
                verses = self.lookup.get_verse(ref.book, ref.chapter, ref.start_verse, translation)
            else:
                label += f"-{ref.end_verse}"
                verses = self.lookup.get_verse_range(
                    ref.book, ref.chapter, ref.start_verse, ref.end_verse, translation
                )
            
            if verses:
                self.display_window.display_verse(verses, auto_clear)
                self.display_window.show()
                self._context = (ref.book, ref.chapter)
                self.control_panel.log_status(f"Displayed: {label} ({ref.confidence:.0%})")
                return True
            self.control_panel.log_status(f"No such verse: {label}")
        return False
    
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
