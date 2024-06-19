from SDM.User_Interface.Utils.filename_tools import processor_data_ready
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

    self.header = Label(self, text='Select SDM program:', font=(self.main_window.header_style))
    self.header.grid(row=1, column=0, padx=5, pady=(3, 3), sticky='w')

    self.var = StringVar()
    self.var.set(None)

    self.signal_processing = self.main_window.data_loading_method != 'Processor'

    self.can_use_already_trained_models = True
    # if self.main_window.data_loading_method == 'Processor':
    #   self.can_use_already_trained_models = models_ready(self.main_window.previous_processor)

    if self.signal_processing:
      self.signalProcessingRadiobutton = Radiobutton(self, text = 'Process TAC signal (cleaning, smoothing, and feature generation).', command=self.update_program, variable=self.var, value = 'SP', font=self.main_window.label_style)
      self.signalProcessingRadiobutton.grid(row=2, column=0, padx=5, pady=1, sticky='w')

    if self.can_use_already_trained_models:
      value = 'SP_P' if self.signal_processing else 'P'
      text = 'Process TAC signal and make predictions using already-trained model.' if self.signal_processing else 'Make predictions using already-trained model.'
      self.makePredictionsRadiobutton = Radiobutton(self, text = text, command=self.update_program, variable=self.var, value = value, font=self.main_window.label_style)
      self.makePredictionsRadiobutton.grid(row=3, column=0, padx=5, pady=1, sticky='w')

    # if self.main_window.data_loading_method != 'Single':
    #   value = 'SP_ML' if self.signal_processing else 'ML'
    #   text = 'Process TAC signal, train new model, and make predictions using new model.' if self.signal_processing else 'Train new model and make predictions using new model.'
    #   self.modelTrainingRadiobutton = Radiobutton(self, text = text, command=self.update_program, variable=self.var, value = value, font=self.main_window.label_style)
    #   self.modelTrainingRadiobutton.grid(row=4, column=0, padx=5, pady=1, sticky='w')
      
    self.main_window = main_window
    self.program = self.main_window.program

  def update_program(self):
    self.data_loading_method = self.var.get()
    if self.main_window.data_loading_method == 'Processor' and self.main_window.previous_processor:
      self.main_window.previous_processor = None
      self.main_window.select_skyn_data()
    self.main_window.update_program(self.data_loading_method)

  # def update_processor_programs(self, can_use_already_trained_models):
  #   if can_use_already_trained_models:
  #     self.makePredictionsRadiobutton = Radiobutton(self, text = 'Process TAC signal and make predictions using already-trained model.' if self.signal_processing else 'Make predictions using already-trained model.', command=self.update_program, variable=self.var, value = 'PP', font=self.main_window.label_style)
  #     self.makePredictionsRadiobutton.grid(row=3, column=0, padx=5, pady=1, sticky='w')
  #   else:
  #     self.makePredictionsRadiobutton.grid_forget()
