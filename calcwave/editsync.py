import watchdog
from watchdog.events import FileSystemEventHandler
import curses
import contextlib

# Creates a temp file containing the editor text, watches it for changes, and updates the editor text.
class FileWatchAndSync(FileSystemEventHandler):
  def __init__(self, editor, windowmanager, infoDisplay, lock) -> None:
    self.editor = editor
    self.window = windowmanager
    self.infoDisplay = infoDisplay
    self.lock = lock
    super().__init__()

  def on_created(self, event):
    self.on_modified(event)

  def on_modified(self, event):
    #print(f'event type: {event.event_type}  path : {event.src_path}')
    curses.beep()
    text = None
    with open(event.src_path, 'r') as file:
      text = file.read()
      with (self.lock if self.lock is not None else contextlib.nullcontext):
        self.editor.hideCursor()
        self.editor.setText(text)
    if text:
      self.infoDisplay.updateInfo("File read")
      self.window.try_compile_code(text)