from SDM.User_Interface.Frames.rename_file_row import RenameFileRow
from SDM.User_Interface.Utils.filename_tools import *
from tkinter import *
from tkinter import StringVar, IntVar
from tkinter.filedialog import askopenfile
from tkinter import messagebox
from datetime import datetime, date
import pandas as pd
import os
import traceback

class RenameFilesWindow(Toplevel):
  def __init__(self, parent, directory, filenames):
    super().__init__(parent)
    self.title("Rename Files")
    self.geometry("900x1100")
    self.parent = parent
    self.directory = directory
    self.filenames = filenames

    self.columnconfigure(0, weight=5)
    self.columnconfigure(1, weight=1)
    self.rowconfigure(10, weight=1)

    self.header = Label(self, text = 'Rename Files according to SDM Convention')
    self.header.grid(row=0, column=0, padx=5, pady=(5, 10))
    self.header.config(font=(None, 14, 'bold'))
    
    self.episodeIdentifierLabel = Label(self, text = 'Note: Episode identifiers will automatically be added to filenames \nif there are multiple data sets for a given SubID & Condition.')
    self.episodeIdentifierLabel.config(font=(None, 9, 'italic'))
    self.episodeIdentifierLabel.grid(row=1, column=0, padx=5, pady=3)

    self.buttons_frame = Frame(self)
    self.buttons_frame.grid(row=4, column=0)

    self.submit = Button(self.buttons_frame, text = 'Rename Files (Irreversible)', width=25, command = self.rename_files)
    self.submit.grid(row=0, column=0, padx=10, pady=2, sticky='w')

    self.close = Button(self.buttons_frame, text = 'Close', width=7, command=self.destroy)
    self.close.grid(row=0, column=1, padx=10, pady=2)

    self.rows_frame = Frame(self, height=800, width=600, highlightbackground="black", highlightthickness=2)
    self.rows_frame.grid(row=10, column=0, padx=5, pady=5, sticky="nsew")

    self.canvas = Canvas(self.rows_frame)
    self.canvas.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
    self.rows_frame.columnconfigure(0, weight=1)  # Make the column expand with the window
    self.rows_frame.rowconfigure(0, weight=1)
    self.rows_frame.grid_rowconfigure(0, weight=1)
    self.buttons_frame.columnconfigure(0, weight=1)

    self.scrollbar = Scrollbar(self.rows_frame, orient="vertical", command=self.canvas.yview)
    self.scrollbar.grid(row=0, column=1, sticky="ns")
    self.canvas.configure(yscrollcommand=self.scrollbar.set, highlightthickness=0)

    self.inner_frame = Frame(self.canvas, highlightthickness=0)
    self.inner_frame.grid_rowconfigure(0, weight=1)
    self.inner_frame.grid_columnconfigure(0, weight=1)
    self.canvas.create_window((5, 5), window=self.inner_frame, anchor="nw")

    self.renaming_widgets = {}
    for i, filename in enumerate(self.filenames):
      self.renaming_widgets[filename] = RenameFileRow(self.inner_frame, filename, i)
      self.renaming_widgets[filename].grid(row=i, column=0, pady=2, padx=2, sticky='w')
    
    self.inner_frame.update_idletasks()
    self.canvas.config(scrollregion=self.canvas.bbox("all"))


  def rename_files(self):
    original_filenames = [widget.filename for widget in list(self.renaming_widgets.values())]
    filenames_valid = [widget.filename_valid for widget in list(self.renaming_widgets.values())]
    subids = [int(widget.subidEntry.get()) if widget.subidEntry.get().isnumeric() else widget.subidEntry.get() for widget in list(self.renaming_widgets.values())]
    conditions = [widget.condition.get() for widget in list(self.renaming_widgets.values())]
    extensions = [widget.filename.split('.')[-1] for widget in list(self.renaming_widgets.values())]

    subids_valid = [isinstance(subid, int) or subid == '' for subid in subids]
    conditions_valid = [item in ['Unk', 'Non', 'Alc'] or item == '' for item in conditions]
    
    if any(subid_verification is False for subid_verification in subids_valid) or any(condition_verification is False for condition_verification in conditions_valid):
      messagebox.showerror('SDM Error', f'Invalid SubIDS at rows: {[i+1 for i, bool in subids_valid if bool is False]}\nInvalid condition at rows: {[i+1 for i, bool in conditions_valid if bool is False]}')
    else:
      pairings = {}
      error = False
      for i, filename in enumerate(original_filenames):
        pairing = str(subids[i]) + str(conditions[i])
        if subids[i] == ''  or conditions[i] == '':
          pass # if both subid and condition are not provided, do not include in renaming
        elif len(str(subids[i])) < 3 and pairing != '':
          messagebox.showerror('SDM Error', f'SubID in row {i+1} is less than 3 digits.\n SubIDs must be between 3 and 6 digits long.')
          error = True
          break
        elif pairing not in list(pairings.keys()):
          pairings[pairing] = [filename]
        elif pairing != '':
          pairings[pairing].append(filename)

        
      episode_identifier_required = any([len(filenames) > 1 for filenames in list(pairings.values())])

      filename_renaming = {}
      if not error:
        for pairing, filenames in pairings.items():
          used_epi_ids = []
          for filename in filenames:
            if matches_convention(filename, episode_identifier_required=episode_identifier_required):
              new_filename = filename
              if episode_identifier_required:
                used_epi_ids.append(identify_episode_identifier(filename))
            else:
              extension = extensions[original_filenames.index(filename)]
              subid = subids[original_filenames.index(filename)]
              condition = conditions[original_filenames.index(filename)]
              episode_identifier = identify_episode_identifier(filename, used_epi_ids=used_epi_ids)
              used_epi_ids.append(episode_identifier)

              new_filename = f'{subid} {condition} {episode_identifier}.{extension}' if episode_identifier_required else f'{subid} {condition}.{extension}'

            current_filepath = os.path.join(self.directory, filename)
            updated_filepath = os.path.join(self.directory, new_filename)
            filename_renaming[current_filepath] = updated_filepath
            if os.path.exists(current_filepath) and current_filepath != updated_filepath:
              try:
                os.rename(current_filepath, updated_filepath)
              except:
                print(traceback.format_exc())
                messagebox.showerror('Error', traceback.format_exc())
        
        self.filenames = [file for file in os.listdir(self.directory)]
        for widget in self.renaming_widgets.values():
          widget.grid_forget() 
        self.renaming_widgets = {}
        for i, filename in enumerate(self.filenames):
          self.renaming_widgets[filename] = RenameFileRow(self.inner_frame, filename, i)
          self.renaming_widgets[filename].grid(row=2+i, column=0, pady=2, padx=2, sticky='w')
        filenames_df = pd.DataFrame({
          'Previous Filename': list(filename_renaming.keys()),
           'New Filename': list(filename_renaming.values()),
          })
        if not os.path.exists('Results/File_Renaming/'):
          os.mkdir('Results/File_Renaming/')
        filepath = 'Results/File_Renaming/' + f'{self.directory.split("/")[-2]}_renaming_{date.today().strftime("%m.%d.%Y")}{datetime.now().strftime("%H-%M-%S")}.xlsx'
        print(filenames_df)
        filenames_df.to_excel(filepath, index=False)
        messagebox.showinfo('SDM Update', f'Previous and new filenames are recorded in excel file located here: {filepath}')

      
