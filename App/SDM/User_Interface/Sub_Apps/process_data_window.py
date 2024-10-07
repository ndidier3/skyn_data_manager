from SDM.Run.process_many import process_many
from SDM.User_Interface.Utils.filename_tools import extract_subid, get_project_root
from SDM.User_Interface.Messages.yesno import YesNoMessage
from tkinter import *
from tkinter import filedialog, ttk, simpledialog
from tkinter import messagebox
import os
import sys
import traceback

class ProcessSkynApp(Tk):
  def __init__(self):
    super().__init__()
    self.geometry("300x350")
    self.title("Single File Processor")
    self.protocol("WM_DELETE_WINDOW", self.on_closing)

    self.selectDataButton = Button(self, width = 27, text='Select Data', command=self.select_skyn_data)
    self.selectDataButton.grid(row=5, column=0, pady=(10,3), padx=5)

    self.dataLabel = Label(self, text = 'No dataset loaded')
    self.dataLabel.grid(row=6, column=0, pady=3, padx=5)

    self.outputLabel = Label(self, text = 'Output Folder Name')
    self.outputLabel.grid(row=7, column=0, pady=(5,1), padx=5)
    self.outputFolder = Entry(self, width=20)
    self.outputFolder.grid(row=8, column=0, pady=(1,5), padx=5)

    self.runButton = Button(self, text = 'Run Signal Processing', command=self.run, width=20)
    self.runButton.grid(row=9, column=0, pady=(10, 5), padx=5)
    
    self.update_idletasks()
    mainloop()

  def select_skyn_data(self):
      skyn_dataset_file = filedialog.askopenfile(mode='r', filetypes=[('Skyn dataset','*.xlsx *.csv *.CSV')])

      if skyn_dataset_file:
        self.full_filename = os.path.abspath(skyn_dataset_file.name)
        self.filename=os.path.split(self.full_filename)[-1]
        self.directory = os.path.dirname(self.full_filename)
        self.project_root = get_project_root(self.directory)
        skyn_dataset_file.close()
        self.subid = extract_subid(self.filename)
        if self.subid != '':
          self.dataLabel['text'] = f'Dataset selected: {self.filename}'
          self.dataLabel.config(fg='green')
        else:
          self.dataLabel['text'] = f'Invalid Dataset: {self.filename}'
          self.dataLabel.config(fg='red')

  def run(self):
    if self.filename and self.subid and self.outputFolder.get():
      entries_confirmed = YesNoMessage(self,'Confirmation', 
        f'Would you like to process the file {self.filename}\n'
        f'in the directory {self.directory} and save the output\n'
        f'in Results/{self.outputFolder.get()}?'
      )
      if entries_confirmed.result:
        try:
          process_many(self.project_root, self.directory, self.outputFolder.get(), single_file=self.filename, use_popups=True)
          messagebox.showinfo('Complete', f'Processing complete. See Results/{self.outputFolder.get()}')
        except Exception:
          messagebox.showerror('Error', f'Failed to load. See error: \n{traceback.format_exc()}')
          print(traceback.format_exc())
    else:
      messagebox.showerror('Error', 'Missing required inputs.')

  def on_closing(self):
    self.destroy()
    sys.exit(0)