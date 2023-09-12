from tkinter import *
from tkinter import filedialog, StringVar, IntVar, Toplevel
from tkinter.filedialog import askopenfile
from tkinter import messagebox
from datetime import date
import traceback
import pandas as pd

class CreateMetadataWindow:
  def __init__(self, data, cohort_name, original_window):

    self.__subWindow = Toplevel(original_window)
    self.__subWindow.geometry("1200x900")

    self.data = data
    print(data)
    self.cohort_name = cohort_name

    self.metadata_frame = Frame(self.__subWindow, width=600, height=800, highlightbackground="black", highlightthickness=2)
    self.metadata_frame.grid(row=0, column=1)

    self.excludeSubidsLabelText = 'First, confirm that SubIDs, Conditions, and Episode Identifiers have been properly read for each episode listed below. \n           If any are incorrect, exit this window and then revise either index submissions in the previous window or \n          filenames in your cohort data folder. \nNext, select each episode that you want to exclude from analyses. \nTo create metadata file, click the button below.'
    self.excludeSubidsLabel = Label(self.metadata_frame, text = self.excludeSubidsLabelText, anchor='w', justify='left')
    self.excludeSubidsLabel.grid(row=1, column=1, padx=5, pady=5)

    self.episode_labels = Variable(
      value = [f'Subject: {data["SubID"][i]} | Condition: {data["Condition"][i]} | ID: {data["Episode_Identifier"][i] if data["Episode_Identifier"][i] else "NA"}' for i in range(0, len(data['SubID']))]
    )
    self.excludeSubidsListbox = Listbox(self.metadata_frame, selectmode=MULTIPLE, height=18, width=60, listvariable=self.episode_labels)
    self.excludeSubidsListbox.grid(row=2, column=1, padx=5, pady=5)

    self.createMetadataButton = Button(self.metadata_frame, text = 'Create Metadata (Excel)', width = 25, command=self.createMetadata, fg = 'blue')
    self.createMetadataButton.grid(row=3, column=1, padx=5, pady=7)

  def createMetadata(self):
    try:
      self.selected_text_list = [i for i in self.excludeSubidsListbox.curselection()]
      self.data['Use_Data'] = [self.data['Use_Data'][i] if i not in self.selected_text_list else 'N' for i in range(0, len(self.data['Use_Data']))]
      meta_df = pd.DataFrame(self.data)
      meta_df.to_excel(f'Resources/{self.cohort_name}_Metadata.xlsx', index=False)
      messagebox.showinfo('Success', f'File created: Resources/{self.cohort_name}_Metadata.xlsx')
      self.__subWindow.destroy()
    except Exception:
      print(traceback.format_exc())
      messagebox.showerror('\Error creating metadata file', traceback.format_exc())
    

