from tkinter import *
from tkinter import messagebox

class ModelNameWindow(Toplevel):
  def __init__(self, parent):
    super().__init__(parent)
    self.geometry("200x100")
    self.title('Model Name')
    self.parent = parent

    self.model_name = ''

    self.header = Label(self, text = 'Give a name for this model.')
    self.header.grid(row=0, column=0, padx=10, pady=5)

    self.modelNameEntry = Entry(self, width = 20)
    self.modelNameEntry.grid(row=1, column=0, padx=10, pady=(0, 5))

    self.submitButton = Button(self, width=10, text='Submit', command=self.submit)
    self.submitButton.grid(row=2, column=0, padx=10, pady=10)

  def submit(self):
    if str(self.modelNameEntry.get()) == '':
      messagebox.showerror('SDM Error', 'Must provide model name')
    elif str(self.modelNameEntry.get()) in list(self.parent.models.keys()):
      messagebox.showerror('SDM Error', 'Model name already used.')
    else:
      self.model_name = str(self.modelNameEntry.get())
      self.destroy()
    