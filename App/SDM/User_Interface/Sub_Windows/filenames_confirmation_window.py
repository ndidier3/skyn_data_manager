from tkinter import *
from tkinter import filedialog, StringVar, IntVar
from tkinter.filedialog import askopenfile
from tkinter import messagebox
import pandas as pd
import os

class FilenamesConfirmationWindow(Toplevel):
  def __init__(self, parent, parsing_indices):
    super().__init__(parent)

    self.geometry("500x600")
    self.title('Confirm Filenames')

    self.parent = parent
    self.parsing_indices = parsing_indices

    if any(item is None for item in self.parsing_indices[:4]):
      messagebox.showerror('SDM Error', 'Please select indices for SubID and Condition.')
    else:
      data = self.parent.prepare_filename_data()
      self.episode_labels = Variable(
        value = [f'Subject: {data["SubID"][i]} | Condition: {data["Condition"][i]} | ID: {data["Dataset_Identifier"][i] if data["Dataset_Identifier"][i] else "NA"}' for i in range(0, len(data['SubID']))])
      
      self.fileDataListbox = Listbox(self, selectmode="none", height=18, width=60, listvariable=self.episode_labels)
      self.fileDataListbox.grid(row=22, column=1, padx=5, pady=5)

      self.verifyLabel = Label(self, text = 'Are filenames parsed correctly?')
      self.verifyLabel.grid(row=23, column=1, padx=5, pady=(7, 2))

      self.yes_no_frame = Frame(self)
      self.yes_no_frame.grid(row=24, column=1)

      self.confirmed = False
      self.yesButton = Button(self.yes_no_frame, text = 'Yes', width = 10, command = self.submitYes)
      self.yesButton.grid(column=0, row=0, padx=(0, 10), pady=5)
      self.noButton = Button(self.yes_no_frame, text = 'No', width = 10, command = self.submitNo)
      self.noButton.grid(column=1, row=0, padx=(10, 0), pady=5)

  def submitYes(self):
    self.confirmed = True
    self.destroy()

  def submitNo(self):
    self.confirmed = False
    self.destroy()
