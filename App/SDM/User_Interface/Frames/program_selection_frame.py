from SDM.User_Interface.Utils.filename_tools import data_ready, models_ready
from tkinter import *
from tkinter import filedialog, StringVar, IntVar
from tkinter.filedialog import askopenfile
from tkinter import messagebox
import pickle

class ProgramSelectionFrame(Frame):
  def __init__(self, parent, main_window):
    super().__init__(parent)

    self.parent = parent
    self.main_window = main_window

    self.header = Label(self, text='Select SDM program:')
    self.header.grid(row=0, column=0, padx=5, pady=(3, 3), sticky='w')
    self.header.config(font=(None, 10, 'bold'))

    self.var = StringVar()
    self.var.set(None)

    self.custom_font = ('Arial', 9)

    self.signal_processing = self.main_window.data_selection_method != 'Processor'

    self.can_use_already_trained_models = True
    if self.main_window.data_selection_method == 'Processor':
      self.can_use_already_trained_models = models_ready(self.main_window.previous_processor)

    if self.signal_processing:
      self.signalProcessingRadiobutton = Radiobutton(self, text = 'Process TAC signal (cleaning, smoothing, and feature generation).', command=self.update_program, variable=self.var, value = 'P', font=self.custom_font)
      self.signalProcessingRadiobutton.grid(row=1, column=0, padx=5, pady=1, sticky='w')

    if self.can_use_already_trained_models:
      self.makePredictionsRadiobutton = Radiobutton(self, text = 'Process TAC signal and make predictions using already-trained model.' if self.signal_processing else 'Make predictions using already-trained model.', command=self.update_program, variable=self.var, value = 'PP', font=self.custom_font)
      self.makePredictionsRadiobutton.grid(row=2, column=0, padx=5, pady=1, sticky='w')

    if self.main_window.data_selection_method != 'Single': 
      self.modelTrainingRadiobutton = Radiobutton(self, text = 'Process TAC signal, train new model, and make predictions using new model.' if self.signal_processing else 'Train new model and make predictions using new model.', command=self.update_program, variable=self.var, value = 'PTP', font=self.custom_font)
      self.modelTrainingRadiobutton.grid(row=3, column=0, padx=5, pady=1, sticky='w')
      
    self.main_window = main_window
    self.program = self.main_window.program

  def update_program(self):
    self.data_selection_method = self.var.get()
    self.main_window.update_program(self.data_selection_method)

  def update_processor_programs(self, can_use_already_trained_models):
    if can_use_already_trained_models:
      self.makePredictionsRadiobutton = Radiobutton(self, text = 'Process TAC signal and make predictions using already-trained model.' if self.signal_processing else 'Make predictions using already-trained model.', command=self.update_program, variable=self.var, value = 'PP', font=self.custom_font)
      self.makePredictionsRadiobutton.grid(row=2, column=0, padx=5, pady=1, sticky='w')
    else:
      self.makePredictionsRadiobutton.grid_forget()

