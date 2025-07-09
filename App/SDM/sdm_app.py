import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import re
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys

# Import SDM modules
from App.SDM.Run.process_single import process_and_analyze_single_subject
from App.SDM.Analysis.curveFeatures import curveFeatures
from App.SDM.Analysis.dayFeatures import dayFeatures
from App.SDM.Configuration.file_management import (
    extract_subid, extract_dataset_identifier, 
    matches_filename_convention, create_save_directories
)
from App.SDM.Scripts.Test.test_settings import (
    smooth_and_impute_attrs, curve_attrs, day_attrs
)


class FilenameCorrectionDialog:
    """
    Dialog window for correcting invalid filenames.
    Allows users to manually enter Subject ID and Dataset ID.
    """
    
    def __init__(self, parent, original_filename, original_filepath):
        self.parent = parent
        self.original_filename = original_filename
        self.original_filepath = original_filepath
        self.corrected_filename = None
        self.corrected_filepath = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Correct Filename")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (400 // 2)
        self.dialog.geometry(f"500x400+{x}+{y}")
        
        # Initialize variables
        self.subid_var = tk.StringVar()
        self.dataset_id_var = tk.StringVar()
        
        # Extract current values from filename
        current_subid = extract_subid(original_filename, validate=False)
        current_dataset_id = extract_dataset_identifier(original_filename, validate=False)
        
        self.subid_var.set(current_subid)
        self.dataset_id_var.set(current_dataset_id)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI components."""
        # Create main container with proper weight distribution
        main_container = ttk.Frame(self.dialog)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Content frame (will expand to fill available space)
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title and explanation
        title_label = ttk.Label(content_frame, text="Filename Correction Required", 
                               font=('TkDefaultFont', 12, 'bold'))
        title_label.pack(pady=(0, 10))
        
        explanation_text = ("The selected file does not follow the required naming convention.\n"
                          "Please provide the correct Subject ID and Dataset ID to continue.")
        explanation_label = ttk.Label(content_frame, text=explanation_text, 
                                     wraplength=450, justify=tk.CENTER)
        explanation_label.pack(pady=(0, 20))
        
        # Original filename display
        ttk.Label(content_frame, text="Original Filename:", font=('TkDefaultFont', 9, 'bold')).pack(anchor=tk.W)
        original_label = ttk.Label(content_frame, text=self.original_filename, 
                                  foreground='red', font=('TkDefaultFont', 9))
        original_label.pack(anchor=tk.W, pady=(0, 15))
        
        # Input fields frame
        input_frame = ttk.Frame(content_frame)
        input_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Subject ID input
        ttk.Label(input_frame, text="Subject ID (3-6 digits):").grid(row=0, column=0, sticky=tk.W, pady=5)
        subid_entry = ttk.Entry(input_frame, textvariable=self.subid_var, width=15)
        subid_entry.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Dataset ID input
        ttk.Label(input_frame, text="Dataset ID (3 digits):").grid(row=1, column=0, sticky=tk.W, pady=5)
        dataset_entry = ttk.Entry(input_frame, textvariable=self.dataset_id_var, width=15)
        dataset_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Validation feedback
        self.validation_label = ttk.Label(content_frame, text="", font=('TkDefaultFont', 9))
        self.validation_label.pack(pady=(0, 20))
        
        # Add separator line
        separator = ttk.Separator(content_frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=(0, 20))
        
        # Button frame (fixed at bottom)
        button_frame = ttk.Frame(main_container)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Make the Rename File button more prominent
        rename_button = ttk.Button(button_frame, text="Rename File", command=self.rename_file, width=15)
        rename_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="Cancel", command=self.cancel, width=10).pack(side=tk.RIGHT)
        
        # Bind validation to entry changes
        self.subid_var.trace('w', self.validate_inputs)
        self.dataset_id_var.trace('w', self.validate_inputs)
        
        # Initial validation
        self.validate_inputs()
        
        # Focus on first entry
        subid_entry.focus_set()
        
    def validate_inputs(self, *args):
        """Validate the entered Subject ID and Dataset ID."""
        subid = self.subid_var.get().strip()
        dataset_id = self.dataset_id_var.get().strip()
        
        # Validate Subject ID
        subid_valid = (len(subid) >= 3 and len(subid) <= 6 and subid.isdigit())
        
        # Validate Dataset ID
        dataset_valid = (len(dataset_id) == 3 and dataset_id.isdigit() and int(dataset_id) != 0)
        
        if subid_valid and dataset_valid:
            self.validation_label.config(text="✓ Valid format", foreground='green')
            return True
        else:
            errors = []
            if not subid_valid:
                errors.append("Subject ID must be 3-6 digits")
            if not dataset_valid:
                errors.append("Dataset ID must be 3 digits (not 000)")
            
            self.validation_label.config(text="✗ " + "; ".join(errors), foreground='red')
            return False
    
    def rename_file(self):
        """Rename the file with corrected Subject ID and Dataset ID."""
        if not self.validate_inputs():
            messagebox.showerror("Invalid Input", "Please correct the Subject ID and Dataset ID before renaming.")
            return
        
        try:
            # Get the corrected values
            subid = self.subid_var.get().strip()
            dataset_id = self.dataset_id_var.get().strip()
            
            # Get file extension
            file_ext = os.path.splitext(self.original_filename)[1]
            
            # Create new filename
            new_filename = f"{subid}_{dataset_id}{file_ext}"
            new_filepath = os.path.join(os.path.dirname(self.original_filepath), new_filename)
            
            # Check if new filename already exists
            if os.path.exists(new_filepath) and new_filepath != self.original_filepath:
                result = messagebox.askyesno("File Exists", 
                                           f"A file named '{new_filename}' already exists.\n\n"
                                           "Do you want to overwrite it?")
                if not result:
                    return
            
            # Rename the file
            os.rename(self.original_filepath, new_filepath)
            
            self.corrected_filename = new_filename
            self.corrected_filepath = new_filepath
            
            messagebox.showinfo("Success", f"File renamed successfully to:\n{new_filename}")
            self.dialog.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rename file: {str(e)}")
    
    def cancel(self):
        """Cancel the filename correction."""
        self.dialog.destroy()


class SkynDataManagerGUI:
    """
    TKINTER GUI for processing single Skyn data files.
    Provides file validation, configuration options, and analysis execution.
    """
    
    def __init__(self, root):
        self.root = root
        self.root.title("Skyn Data Manager - Single File Processor")
        self.root.geometry("900x500")
        
        # Initialize variables
        self.selected_file = tk.StringVar()
        self.subid = tk.StringVar()
        self.dataset_id = tk.StringVar()
        self.file_valid = tk.BooleanVar(value=False)
        
        # Automatically determine project root (2 levels up from this script)
        if getattr(sys, 'frozen', False):
            # Running as a PyInstaller bundle
            self.project_root = os.path.dirname(sys.executable)
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.project_root = os.path.dirname(os.path.dirname(script_dir))
        
        self.cohort_name = tk.StringVar(value="")
        
        # Analysis options
        self.run_signal_processing = tk.BooleanVar(value=True)
        self.export_curve_stats = tk.BooleanVar(value=False)
        self.export_day_stats = tk.BooleanVar(value=True)
        
        # Configuration attributes from test_settings
        self.smooth_and_impute_attrs = smooth_and_impute_attrs
        self.curve_attrs = curve_attrs
        self.gaps_and_non_wear_attrs = {'export_excel': False}
        self.day_attrs = day_attrs
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface components."""
        
        # Create main frame with scrollbar
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # File Selection Section
        self.create_file_section(main_frame)
        
        # File Validation Section
        self.create_validation_section(main_frame)
        
        # Analysis Options Section
        self.create_analysis_section(main_frame)
        
        # Action Buttons Section
        self.create_action_buttons(main_frame)
        

        
    def create_file_section(self, parent):
        """Create file selection section."""
        file_frame = ttk.LabelFrame(parent, text="File Selection", padding=10)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Display project root (read-only)
        ttk.Label(file_frame, text="Project Root:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        project_root_label = ttk.Label(file_frame, text=self.project_root, foreground='blue', font=('TkDefaultFont', 9))
        project_root_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), columnspan=2)
        
        ttk.Label(file_frame, text="Data File:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Entry(file_frame, textvariable=self.selected_file, width=60, state='readonly').grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        ttk.Button(file_frame, text="Select File", command=self.select_file).grid(row=1, column=2, padx=(10, 0))
        
        ttk.Label(file_frame, text="Cohort Name:").grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Entry(file_frame, textvariable=self.cohort_name, width=30).grid(row=2, column=1, sticky=tk.W, padx=(10, 0))
        
    def create_validation_section(self, parent):
        """Create file validation section."""
        validation_frame = ttk.LabelFrame(parent, text="File Validation", padding=10)
        validation_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Subject ID
        ttk.Label(validation_frame, text="Subject ID:").grid(row=0, column=0, sticky=tk.W)
        self.subid_label = ttk.Label(validation_frame, textvariable=self.subid, font=('TkDefaultFont', 10, 'bold'))
        self.subid_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 20))
        
        # Dataset ID
        ttk.Label(validation_frame, text="Dataset ID:").grid(row=0, column=2, sticky=tk.W)
        self.dataset_label = ttk.Label(validation_frame, textvariable=self.dataset_id, font=('TkDefaultFont', 10, 'bold'))
        self.dataset_label.grid(row=0, column=3, sticky=tk.W, padx=(10, 20))
        
        # Validation status
        ttk.Label(validation_frame, text="File Valid:").grid(row=0, column=4, sticky=tk.W)
        self.validation_label = ttk.Label(validation_frame, text="No file selected", foreground='red')
        self.validation_label.grid(row=0, column=5, sticky=tk.W, padx=(10, 0))
        
        # Add "Correct Filename" button
        self.correct_filename_button = ttk.Button(validation_frame, text="Correct Filename", 
                                                 command=self.show_filename_correction, state='disabled')
        self.correct_filename_button.grid(row=1, column=0, columnspan=6, pady=(10, 0), sticky=tk.W)
        

        
    def create_analysis_section(self, parent):
        """Create analysis options section."""
        analysis_frame = ttk.LabelFrame(parent, text="Analysis Options", padding=10)
        analysis_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Checkbutton(analysis_frame, text="Process Signal", variable=self.run_signal_processing, state='disabled').grid(row=0, column=0, sticky=tk.W, padx=(0, 20), pady=5)
        ttk.Checkbutton(analysis_frame, text="Export Curve Stats", variable=self.export_curve_stats).grid(row=0, column=1, sticky=tk.W, padx=(0, 20), pady=5)
        ttk.Checkbutton(analysis_frame, text="Export Day Stats", variable=self.export_day_stats).grid(row=0, column=2, sticky=tk.W, pady=5)
        
    def create_action_buttons(self, parent):
        """Create main action buttons."""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(button_frame, text="RUN", command=self.run_selected_analyses, style='Accent.TButton', width=15).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Exit", command=self.root.quit).pack(side=tk.RIGHT)
        
    def select_file(self):
        """Select data file and validate it."""
        file_path = filedialog.askopenfilename(
            title="Select Skyn Data File",
            filetypes=[
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.selected_file.set(file_path)
            self.validate_file(file_path)
            
    def validate_file(self, file_path):
        """Validate file naming convention and extract IDs."""
        filename = os.path.basename(file_path)
        
        # Extract SubID and Dataset ID
        subid = extract_subid(filename)
        dataset_id = extract_dataset_identifier(filename)
        
        self.subid.set(subid if subid else "Invalid")
        self.dataset_id.set(dataset_id if dataset_id else "Invalid")
        
        # Check if file matches convention
        file_valid = matches_filename_convention(filename, [])
        self.file_valid.set(file_valid)
        
        if file_valid:
            self.validation_label.config(text="✓ Valid", foreground='green')
            self.subid_label.config(foreground='green')
            self.dataset_label.config(foreground='green')
            self.correct_filename_button.config(state='disabled')
        else:
            self.validation_label.config(text="✗ Invalid", foreground='red')
            self.subid_label.config(foreground='red')
            self.dataset_label.config(foreground='red')
            self.correct_filename_button.config(state='normal')
    
    def show_filename_correction(self):
        """Show the filename correction dialog."""
        if not self.selected_file.get():
            messagebox.showwarning("No File Selected", "Please select a file first.")
            return
        
        dialog = FilenameCorrectionDialog(self.root, os.path.basename(self.selected_file.get()), self.selected_file.get())
        self.root.wait_window(dialog.dialog)
        
        # If file was renamed, update the GUI
        if dialog.corrected_filepath:
            self.selected_file.set(dialog.corrected_filepath)
            self.validate_file(dialog.corrected_filepath)


    def run_selected_analyses(self):
        """Run selected analysis steps based on checkboxes.
        
        Requires:
        - Valid data file selected and validated
        - Cohort name entered (determines output folder)
        """
        # Validate required inputs first
        if not self.validate_inputs():
            return
            
        # Check if at least one export option is selected (signal processing always runs)
        if not (self.export_curve_stats.get() or self.export_day_stats.get()):
            result = messagebox.askyesno("No Exports Selected", 
                                       "Signal processing will run but no statistics will be exported.\n\n"
                                       "Do you want to continue anyway?")
            if not result:
                return
            
        try:
            data_input_folder = os.path.dirname(self.selected_file.get())
            subid = self.subid.get()
            results = []
            
            # Run signal processing if selected
            if self.run_signal_processing.get():
                process_and_analyze_single_subject(
                    project_root=self.project_root,
                    data_input_folder=data_input_folder,
                    subid=subid,
                    output_folder_name=self.cohort_name.get(),
                    event_data=pd.DataFrame(),
                    use_prior_save=False,
                    smooth_and_impute=True,
                    adjust_for_gaps_and_non_wear=True,
                    analyze_days=True,
                    identify_curves=True,
                    curve_attrs=self.curve_attrs,
                    smooth_and_impute_attrs=self.smooth_and_impute_attrs,
                    day_attrs=self.day_attrs,
                    gaps_and_non_wear_attrs=self.gaps_and_non_wear_attrs
                )
                results.append("Signal processing completed")
            
            # Export curve stats if selected
            if self.export_curve_stats.get():
                processed_data_folder = data_input_folder.replace('_RAW', '_PROCESSED')
                subid_int = int(subid)
                today = datetime.today().strftime('%m.%d.%Y')
                
                curves = curveFeatures(
                    processed_data_folder,
                    smooth_and_impute_attrs=self.smooth_and_impute_attrs,
                    curve_attrs=self.curve_attrs,
                    subids=[subid_int]
                )
                # curves.run_stats()
                curve_output_file = f'{self.project_root}/Results/{self.cohort_name.get()}/curve_stats_subject_{subid_int}_{today}.xlsx'
                curves.export_workbook_curves(curve_output_file)
                results.append(f"Curve statistics exported to: {curve_output_file}")
            
            # Export day stats if selected
            if self.export_day_stats.get():
                processed_data_folder = data_input_folder.replace('_RAW', '_PROCESSED')
                subid_int = int(subid)
                today = datetime.today().strftime('%m.%d.%Y')
                
                days = dayFeatures(
                    processed_data_folder,
                    subids=[subid_int]
                )
                days.configure_columns_for_compliance_check()
                day_output_file = f'{self.project_root}/Results/{self.cohort_name.get()}/day_stats_subject_{subid_int}_{today}.xlsx'
                days.export_workbook_days(day_output_file)
                results.append(f"Day statistics exported to: {day_output_file}")
            
            # Clean up the .sdp file after processing
            self.cleanup_sdp_file(data_input_folder, subid, self.dataset_id.get())
            
            # Show success message with all completed tasks
            success_message = "Analysis completed successfully!\n\n" + "\n".join(results)
            messagebox.showinfo("Success", success_message)
            
            
        except Exception as e:
            messagebox.showerror("Error", f"Error during analysis: {str(e)}")
    
    def cleanup_sdp_file(self, data_input_folder, subid, dataset_id):
        """Delete the .sdp file after processing is complete."""
        try:
            processed_data_folder = data_input_folder.replace('_RAW', '_PROCESSED')
            print(processed_data_folder)
            if os.path.exists(processed_data_folder):
                for filename in os.listdir(processed_data_folder):
                    print(filename)
                    if filename == f"{subid}_{dataset_id}_skyn_data_processed.sdp.sdm" or filename == f"{subid}_{dataset_id}_skyn_data_invalid.sdp.sdm":
                        sdp_file_path = os.path.join(processed_data_folder, filename)
                        os.remove(sdp_file_path)
                        print(f"Cleaned up .sdp file: {filename}")
        except Exception as e:
            print(f"Warning: Could not clean up .sdp file: {str(e)}")
        
    def validate_inputs(self):
        """Validate inputs before processing."""
        # Check if data file is selected
        if not self.selected_file.get():
            messagebox.showerror("Missing File", "Please select a data file before running analysis.")
            return False
            
        # Check if file follows naming convention
        if not self.file_valid.get():
            messagebox.showerror("Invalid File", "Selected file does not follow the required naming convention.\n\nPlease select a valid Skyn data file or use the 'Correct Filename' button to fix it.")
            return False
            
        # Check if cohort name is provided
        cohort_name = self.cohort_name.get().strip()
        if not cohort_name:
            messagebox.showerror("Missing Cohort Name", "Please enter a cohort name before running analysis.\n\nThis determines where results will be saved.")
            return False
            
        # Check for invalid characters in cohort name
        if not re.match(r'^[a-zA-Z0-9_-]+$', cohort_name):
            messagebox.showerror("Invalid Cohort Name", "Cohort name can only contain letters, numbers, underscores, and hyphens.\n\nPlease use a valid folder name.")
            return False
            
        # Check if project root exists
        if not os.path.exists(self.project_root):
            messagebox.showerror("Error", "Project root directory does not exist.")
            return False
            
        return True


def main():
    """Main function to run the application."""
    root = tk.Tk()
    app = SkynDataManagerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
