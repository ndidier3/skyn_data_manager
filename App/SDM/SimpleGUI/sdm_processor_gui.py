import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from App.SDM.Run.process_single import process_and_analyze_single_subject
from App.SDM.Configuration.file_management import (
    extract_subid, 
    extract_dataset_identifier,
    matches_filename_convention,
    is_subid_valid,
    is_dataset_id_valid,
    stringify_dataset_id
)
from App.SDM.Analysis.curveFeatures import curveFeatures
from App.SDM.Analysis.dayFeatures import dayFeatures
from settings import smooth_and_impute_attrs, curve_attrs, day_attrs, gaps_and_non_wear_attrs
from datetime import datetime
import pandas as pd
import shutil

class RenameDialog:
    def __init__(self, parent, original_path):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Rename File")
        self.dialog.geometry("400x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.original_path = original_path
        self.original_filename = os.path.basename(original_path)
        self.original_dir = os.path.dirname(original_path)
        self.new_filename = None
        
        # Create and pack widgets
        ttk.Label(self.dialog, text="Filename does not meet naming convention.\nPlease enter new filename and study ID:").pack(pady=10)
        
        # Subject ID entry
        subid_frame = ttk.Frame(self.dialog)
        subid_frame.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(subid_frame, text="Subject ID (3-6 digits):").pack(side=tk.LEFT)
        self.subid_var = tk.StringVar()
        self.subid_entry = ttk.Entry(subid_frame, textvariable=self.subid_var, width=10)
        self.subid_entry.pack(side=tk.LEFT, padx=5)
        
        # Study ID entry
        studyid_frame = ttk.Frame(self.dialog)
        studyid_frame.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(studyid_frame, text="Study ID (3 digits):").pack(side=tk.LEFT)
        self.studyid_var = tk.StringVar()
        self.studyid_entry = ttk.Entry(studyid_frame, textvariable=self.studyid_var, width=10)
        self.studyid_entry.pack(side=tk.LEFT, padx=5)
        
        # Rename button
        self.rename_button = ttk.Button(self.dialog, text="Rename", command=self.rename_file, state=tk.DISABLED)
        self.rename_button.pack(pady=20)
        
        # Bind validation
        self.subid_var.trace_add('write', self.validate_entries)
        self.studyid_var.trace_add('write', self.validate_entries)
        
    def validate_entries(self, *args):
        subid = self.subid_var.get()
        studyid = self.studyid_var.get()
        
        # Debug prints
        print(f"Validating - Subid: {subid}, Studyid: {studyid}")
        print(f"Subid valid: {is_subid_valid(subid)}")
        print(f"Studyid valid: {is_dataset_id_valid(studyid, None)}")
        print(f"Studyid length: {len(studyid)}")
        
        # Enable rename button only if both entries are valid
        if (is_subid_valid(subid) and 
            is_dataset_id_valid(studyid, None) and 
            len(studyid) == 3):
            print("Validation passed - enabling rename button")
            self.rename_button.config(state=tk.NORMAL)
        else:
            print("Validation failed - disabling rename button")
            self.rename_button.config(state=tk.DISABLED)
    
    def rename_file(self):
        subid = self.subid_var.get()
        studyid = stringify_dataset_id(self.studyid_var.get())
        
        # Get file extension
        _, ext = os.path.splitext(self.original_filename)
        
        # Create new filename
        new_filename = f"{subid}_{studyid}{ext}"
        new_path = os.path.join(self.original_dir, new_filename)
        
        # Check if file already exists
        if os.path.exists(new_path):
            messagebox.showerror("Error", f"File '{new_filename}' already exists. Please choose a different name.")
            return
        
        try:
            # Rename the file
            shutil.move(self.original_path, new_path)
            self.new_filename = new_filename
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rename file: {str(e)}")
    
    def show(self):
        self.dialog.wait_window()
        return self.new_filename

class SDMProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SDM Processor")
        self.root.geometry("800x600")  # Increased both width and height
        
        # Configure default font
        default_font = ('Helvetica', 16)
        label_font = ('Helvetica', 14)  # Slightly smaller than default for labels
        self.root.option_add('*Font', default_font)
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="20")  # Increased padding
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # File selection frame
        file_frame = ttk.LabelFrame(main_frame, text="Select Data File", padding="15")  # Increased padding
        file_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=15)  # Increased pady
        
        # File selection button
        self.file_var = tk.StringVar()
        ttk.Button(file_frame, text="Browse for Data File", command=self.browse_file, width=25).grid(row=0, column=0, padx=10, pady=10)  # Increased button width and padding
        ttk.Label(file_frame, textvariable=self.file_var, wraplength=500, font=label_font).grid(row=0, column=1, padx=10, pady=10)  # Increased wraplength and padding
        
        # Cohort name frame
        cohort_frame = ttk.LabelFrame(main_frame, text="Cohort Information", padding="15")  # Increased padding
        cohort_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=15)  # Increased pady
        
        # Cohort name entry
        ttk.Label(cohort_frame, text="Cohort Name:", font=label_font).grid(row=0, column=0, sticky=tk.W, pady=10)  # Increased pady
        self.cohort_var = tk.StringVar()
        self.cohort_entry = ttk.Entry(cohort_frame, textvariable=self.cohort_var, width=25)  # Increased width
        self.cohort_entry.grid(row=0, column=1, sticky=tk.W, padx=10, pady=10)  # Increased padding
        
        # Info display
        info_frame = ttk.LabelFrame(main_frame, text="File Information", padding="15")  # Increased padding
        info_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=15)  # Increased pady
        
        # Subject ID (label)
        ttk.Label(info_frame, text="Subject ID:", font=label_font).grid(row=0, column=0, sticky=tk.W, pady=10)  # Increased pady
        self.subid_var = tk.StringVar()
        ttk.Label(info_frame, textvariable=self.subid_var, font=label_font).grid(row=0, column=1, sticky=tk.W, padx=10, pady=10)  # Increased padding
        
        # Study ID (label)
        ttk.Label(info_frame, text="Study ID:", font=label_font).grid(row=1, column=0, sticky=tk.W, pady=10)  # Increased pady
        self.dataset_id_var = tk.StringVar()
        ttk.Label(info_frame, textvariable=self.dataset_id_var, font=label_font).grid(row=1, column=1, sticky=tk.W, padx=10, pady=10)  # Increased padding
        
        # Process button
        ttk.Button(main_frame, text="Process Data", command=self.process_data, width=25).grid(row=3, column=0, columnspan=3, pady=25)  # Increased button width and pady
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(main_frame, textvariable=self.status_var, font=label_font).grid(row=4, column=0, columnspan=3, pady=10)  # Increased pady
        
    def browse_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("All files", "*.*")],
            title="Select Data File"
        )
        if file_path:
            filename = os.path.basename(file_path)
            
            # Extract and validate subject ID
            subid = extract_subid(filename)
            dataset_id = extract_dataset_identifier(filename)
            
            # If filename doesn't meet convention, show rename dialog
            if not (subid and dataset_id and matches_filename_convention(filename, None)):
                dialog = RenameDialog(self.root, file_path)
                new_filename = dialog.show()
                
                if new_filename:
                    # Update file path and extract new IDs
                    file_path = os.path.join(os.path.dirname(file_path), new_filename)
                    filename = new_filename
                    subid = extract_subid(filename)
                    dataset_id = extract_dataset_identifier(filename)
                else:
                    return
            
            # Update the GUI with the file information
            self.file_var.set(file_path)
            self.subid_var.set(subid)
            self.dataset_id_var.set(dataset_id)
            
    def process_data(self):
        # Validate inputs
        if not self.file_var.get() or not self.subid_var.get() or not self.cohort_var.get():
            messagebox.showerror("Error", "Please select a valid data file and provide a cohort name")
            return
            
        try:
            self.status_var.set("Processing...")
            self.root.update()
            
            # Get the directory containing the selected file
            file_path = self.file_var.get()
            data_input_folder = os.path.dirname(file_path)
            processed_data_folder = data_input_folder.replace('_RAW', '_PROCESSED')
            
            # Use the workspace path as project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            
            # Get today's date for file naming
            today = datetime.today().strftime('%m.%d.%Y')
            
            # Set up results directory structure using cohort name
            results_dir = f'{project_root}/Results/{self.cohort_var.get()}/{today}'
            data_out = f'{results_dir}/Datasets'
            graphs_out = f'{results_dir}/Plots'
            analyses_out = f'{results_dir}/Model_Performance'
            
            # Create directories if they don't exist
            os.makedirs(data_out, exist_ok=True)
            os.makedirs(graphs_out, exist_ok=True)
            os.makedirs(analyses_out, exist_ok=True)
            
            # Call the processing function with settings from settings.py
            process_and_analyze_single_subject(
                project_root=project_root,
                data_input_folder=data_input_folder,
                subid=self.subid_var.get(),
                output_folder_name=self.cohort_var.get(),  # Pass cohort name as output folder
                smooth_and_impute=True,
                adjust_for_gaps_and_non_wear=True,
                analyze_days=True,
                identify_curves=False,  # Changed to False to disable curve analysis
                smooth_and_impute_attrs=smooth_and_impute_attrs,
                gaps_and_non_wear_attrs=gaps_and_non_wear_attrs,
                curve_attrs=curve_attrs,
                day_attrs=day_attrs,
                use_prior_save=True,
            )
            
            # Run day features analysis
            self.status_var.set("Analyzing day features...")
            self.root.update()
            
            try:
                day_features = dayFeatures(
                    processed_data_folder,
                    subid=self.subid_var.get(),
                    dataset_id=self.dataset_id_var.get()
                )
                day_output = f'{results_dir}/day_features_{self.subid_var.get()}_{self.dataset_id_var.get()}.xlsx'
                day_features.export_workbook_days(day_output)
            except Exception as e:
                print(f"Error analyzing day features: {str(e)}")
                print(f"Full error details: {repr(e)}")  # Print full error details
                print(f"Error occurred at line {e.__traceback__.tb_lineno} in {e.__traceback__.tb_frame.f_code.co_filename}")
                messagebox.showwarning("Warning", f"Error analyzing day features: {str(e)}")
            
            self.status_var.set("Processing completed successfully!")
            messagebox.showinfo("Success", f"Data processing and analysis completed successfully!\nResults saved in: {results_dir}")
            
        except Exception as e:
            self.status_var.set("Error occurred during processing")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

def main():
    root = tk.Tk()
    app = SDMProcessorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 