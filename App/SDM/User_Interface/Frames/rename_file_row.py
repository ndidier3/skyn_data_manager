from tkinter import *
from tkinter import StringVar, IntVar
from SDM.User_Interface.Utils.filename_tools import *

class RenameFileRow(Frame):
  def __init__(self, parent, filename, i):
    super().__init__(parent)
    self.parent = parent
    self.filename = filename
    self.filename_valid = matches_convention(self.filename)  
    self.configure(highlightthickness=0)

    self.row_idx = Label(self, text=i+1)
    self.row_idx.config(font=(None, 12, 'bold'))
    self.row_idx.grid(row=1, column=0, padx=1, pady=1)

    valid_label_text = "Filename Matches Convention:" if self.filename_valid else "Invalid Filename:"
    valid_label_text = "Partially Valid Filename:" if  not self.filename_valid and (identify_subid(self.filename) != '' and identify_condition(self.filename) != '') else valid_label_text

    self.filenameLabel = Label(self, text = f'{valid_label_text} {filename}', width = 50)
    self.filenameLabel.config(font=(None, 12, 'bold'), fg='red' if not self.filename_valid else 'green')
    self.filenameLabel.grid(row=1, column=2, padx=(5, 10), pady=(1, 2), sticky='w')
      
    self.renameFile = IntVar()
    self.renameFile.set(1 if not self.filename_valid else 0)
    self.renameFileCheckbutton = Checkbutton(self, text = "Rename File?", variable=self.renameFile, command=self.show_renaming_entries)
    self.filenameLabel.config(font=(None, 11, 'italic'))
    self.renameFileCheckbutton.grid(row=1, column=3, padx=5, pady=(1, 2), sticky='e')

    self.subidLabel = Label(self, text='')
    self.subidLabel.config(font=(None, 8, 'normal'))
    self.subidLabel.grid(row=0, column=4, pady=0, padx=5)

    validate_numeric = self.register(lambda P: (P.isdigit() and len(P) <= 6) or len(P) == 0)
    self.subid_text = StringVar()
    self.subid_text.set(identify_subid(self.filename))
    self.subidEntry = Entry(self, width=7, validate='key', validatecommand=(validate_numeric, "%P"), text = self.subid_text)

    self.conditionLabel = Label(self, text='')
    self.conditionLabel.config(font=(None, 8, 'normal'))
    self.conditionLabel.grid(row=0, column=5, pady=0, padx=5)

    self.condition = StringVar(self)
    self.condition.set(identify_condition(self.filename))
    self.conditionOptionMenu = OptionMenu(self, self.condition, *['Alc', 'Non', 'Unk'])

    self.columnconfigure(0, weight=1)
    self.columnconfigure(1, weight=3)
    self.columnconfigure(2, weight=3)
    self.columnconfigure(3, weight=3)
    self.columnconfigure(4, weight=3)
    self.columnconfigure(5, weight=2)
    self.columnconfigure(6, weight=2)

    self.show_renaming_entries()

  def show_renaming_entries(self):
    if self.renameFile.get() == 1:
      self.subidEntry.grid(row=1, column=4, padx=5, pady=(1, 2))
      self.conditionOptionMenu.grid(row=1, column=5, padx=5, pady=(1, 2))
      self.subidLabel['text'] = 'SubID (3-6 digits)'
      self.conditionLabel['text'] = 'Condition'
    else:
      self.subidEntry.grid_forget()
      self.conditionOptionMenu.grid_forget()
      self.subidLabel['text'] = ''
      self.conditionLabel['text'] = ''
  
