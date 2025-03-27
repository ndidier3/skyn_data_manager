from tkinter import *
from tkinter import ttk

class YesNoMessage(Toplevel):
    def __init__(self, parent, title, message):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x200")  # Adjust size as needed
        self.resizable(False, False)

        self.result = None  # To store the result (True/False)

        label = Label(self, text=message, wraplength=350, justify=LEFT)
        label.pack(pady=20, padx=10)

        button_frame = Frame(self)
        button_frame.pack(pady=10)

        yes_button = Button(button_frame, text="Yes", command=self._on_yes)
        no_button = Button(button_frame, text="No", command=self._on_no)

        yes_button.pack(side=LEFT, padx=10)
        no_button.pack(side=LEFT, padx=10)

        self.transient(parent)
        self.grab_set()
        self.wait_window(self)  # Wait until this window is closed

    def _on_yes(self):
        self.result = True
        self.destroy()

    def _on_no(self):
        self.result = False
        self.destroy()