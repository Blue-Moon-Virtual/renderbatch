import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
import subprocess
import time
import json
import threading
import sys
import os
from tkinterdnd2 import DND_FILES, TkinterDnD

# Version information
VERSION = "1.1.0"

# Custom square button class
class SquareButton(ttk.Button):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(width=3, padding=0)
        self.bind('<Configure>', self._on_configure)
    
    def _on_configure(self, event):
        # Force square dimensions
        size = max(event.width, event.height)
        self.configure(width=size//10)  # Approximate conversion from pixels to characters

# Configuration
def get_base_path():
    """Get the base path for the application."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return Path(sys._MEIPASS)
    else:
        # Running as script - use the current working directory
        return Path.cwd()

def get_job_file_path():
    """Get the path to the jobs.json file."""
    if getattr(sys, 'frozen', False):
        # When running as executable, store in AppData/BlueMoonVirtual/RenderBatch
        appdata = Path(os.getenv('APPDATA'))
        app_dir = appdata / "BlueMoonVirtual" / "RenderBatch"
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir / "jobs.json"
    else:
        # When running as script, use the project directory
        return get_base_path() / "jobs.json"

BASE_PATH = get_base_path()
JOB_FILE = get_job_file_path()
BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe"

class BatchRenderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RenderBatch")
        self.root.geometry("800x600")
        
        # Configure dark theme
        self.configure_dark_theme()
        
        # Process control
        self.current_process = None
        self.should_stop = False
        self.was_cancelled = False
        self.auto_retry = False  # New state for auto-retry
        
        # Load jobs
        self.jobs = self.load_job_list()
        
        # Initialize UI
        self._setup_ui()
        self._setup_drag_drop()
        self.update_job_list()
    
    def configure_dark_theme(self):
        """Configure dark theme for ttk widgets."""
        style = ttk.Style()
        
        # Configure colors
        bg_color = "#1e1e1e"  # Darker background
        fg_color = "#ffffff"
        selected_bg = "#2d2d2d"  # Lighter selection
        button_bg = "#333333"  # Slightly lighter buttons
        button_pressed = "#404040"
        border_color = "#3c3c3c"  # Subtle border color
        accent_color = "#007acc"  # Blue accent color
        entry_bg = "#2d2d2d"  # Entry field background
        entry_fg = "#ffffff"  # Entry field text color
        queue_bg = "#252525"  # Slightly lighter background for queue
        delete_bg = "#dc3545"  # Red color for delete buttons
        delete_pressed = "#c82333"  # Darker red for pressed state
        
        # Set the theme to 'clam' which is more customizable
        style.theme_use('clam')
        
        # Configure base style with rounded corners
        style.configure(".",
                       background=bg_color,
                       foreground=fg_color,
                       fieldbackground=bg_color,
                       borderwidth=0,  # Remove border
                       relief="flat")
        
        # Configure Treeview with rounded corners and no border
        style.configure("Treeview",
                       background=queue_bg,  # Lighter background for queue
                       foreground=fg_color,
                       fieldbackground=queue_bg,  # Lighter background for queue
                       borderwidth=0,  # Remove border
                       relief="flat")
        style.configure("Treeview.Heading",
                       background=button_bg,
                       foreground=fg_color,
                       padding=5,
                       font=('Segoe UI', 9, 'bold'),
                       borderwidth=0)  # Remove border
        style.map("Treeview.Heading",
                 background=[('pressed', button_pressed),
                           ('active', selected_bg)])
        style.map("Treeview",
                 background=[('selected', selected_bg)],
                 foreground=[('selected', fg_color)])
        
        # Configure Entry with rounded corners and no border
        style.configure("TEntry",
                       fieldbackground=entry_bg,
                       foreground=entry_fg,
                       insertcolor=entry_fg,
                       borderwidth=0,  # Remove border
                       relief="flat")
        style.map("TEntry",
                 fieldbackground=[('readonly', entry_bg)],
                 selectbackground=[('readonly', selected_bg)],
                 selectforeground=[('readonly', fg_color)])
        
        # Configure Combobox with rounded corners and no border
        style.configure("TCombobox",
                       fieldbackground=entry_bg,
                       foreground=entry_fg,
                       background=button_bg,
                       arrowcolor=fg_color,
                       borderwidth=0,  # Remove border
                       relief="flat")
        style.map("TCombobox",
                 fieldbackground=[('readonly', entry_bg)],
                 selectbackground=[('readonly', selected_bg)],
                 selectforeground=[('readonly', fg_color)])
        
        # Configure Buttons with rounded corners and no border
        style.configure("TButton",
                       background=button_bg,
                       foreground=fg_color,
                       padding=8,
                       font=('Segoe UI', 9),
                       borderwidth=0,  # Remove border
                       relief="flat")
        style.map("TButton",
                 background=[('pressed', button_pressed),
                           ('active', selected_bg)],
                 relief=[('pressed', 'flat')])
        
        # Configure success button with rounded corners and no border
        style.configure("Success.TButton",
                       background="#28a745",
                       foreground=fg_color,
                       padding=8,
                       font=('Segoe UI', 9, 'bold'),
                       borderwidth=0,  # Remove border
                       relief="flat")
        style.map("Success.TButton",
                 background=[('pressed', "#218838"),
                           ('active', "#28a745")])
        
        # Configure danger button with rounded corners and no border
        style.configure("Danger.TButton",
                       background="#dc3545",
                       foreground=fg_color,
                       padding=8,
                       font=('Segoe UI', 9, 'bold'),
                       borderwidth=0,  # Remove border
                       relief="flat")
        style.map("Danger.TButton",
                 background=[('pressed', "#c82333"),
                           ('active', "#dc3545")])
        
        # Configure Frame with rounded corners and no border
        style.configure("TFrame", 
                       background=bg_color,
                       borderwidth=0,  # Remove border
                       relief="flat")
        
        # Configure Label
        style.configure("TLabel",
                       background=bg_color,
                       foreground=fg_color,
                       font=('Segoe UI', 9))
        
        # Configure Scrollbar with rounded corners and no border
        style.configure("Vertical.TScrollbar",
                       background=button_bg,
                       troughcolor=bg_color,
                       bordercolor=border_color,
                       arrowcolor=fg_color,
                       borderwidth=0,  # Remove border
                       relief="flat")
        style.configure("Horizontal.TScrollbar",
                       background=button_bg,
                       troughcolor=bg_color,
                       bordercolor=border_color,
                       arrowcolor=fg_color,
                       borderwidth=0,  # Remove border
                       relief="flat")
        
        # Configure delete button style
        style.configure("Delete.TButton",
                       background=delete_bg,
                       foreground=fg_color,
                       padding=10,
                       font=('Segoe UI', 12, 'bold'),
                       width=3,
                       relief="flat")
        style.map("Delete.TButton",
                 background=[('pressed', delete_pressed),
                           ('active', delete_bg)],
                 relief=[('pressed', 'flat')])
        
        # Configure the root window
        self.root.configure(bg=bg_color)
        
        # Force update of all widgets
        for widget in self.root.winfo_children():
            widget.update()
    
    def _setup_ui(self):
        """Setup the user interface."""
        # Main frame with padding
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure custom styles
        style = ttk.Style()
        
        # Configure the switch button style
        style.configure("Switch.TCheckbutton",
                       padding=5,
                       relief="flat",
                       background="#f0f0f0",
                       foreground="#333333")
        
        # Configure the switch indicator
        style.map("Switch.TCheckbutton",
                 background=[('selected', '#4CAF50'),
                           ('!selected', '#cccccc')],
                 relief=[('pressed', 'flat'),
                        ('!pressed', 'flat')])
        
        # Header with logo and title
        header_frame = ttk.Frame(self.main_frame, style="TFrame")
        header_frame.pack(fill=tk.X, pady=(20, 30))  # Increased top padding to 20
        
        # Left side: Title
        title_frame = ttk.Frame(header_frame, style="TFrame")
        title_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        # Main title
        ttk.Label(title_frame,
                 text="RenderBatch",
                 font=('Segoe UI', 28, 'bold'),
                 style="TLabel",
                 anchor="w").pack(side=tk.TOP, fill=tk.X)
        
        # Subtitle
        ttk.Label(title_frame,
                 text="by Blue Moon Virtual",
                 font=('Segoe UI', 12, 'italic'),
                 foreground="#888888",  # Grey color
                 style="TLabel",
                 anchor="w").pack(side=tk.TOP, fill=tk.X, pady=(5, 0))
        
        # Right side: Logo
        logo_frame = ttk.Frame(header_frame, style="TFrame")
        logo_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Load and display logo
        try:
            # Get the absolute path to the logo
            logo_path = BASE_PATH / "assets" / "logo_header.png"
            print(f"Attempting to load logo from: {logo_path}")
            print(f"Logo file exists: {logo_path.exists()}")
            
            if not logo_path.exists():
                raise FileNotFoundError(f"Logo file not found at: {logo_path}")
                
            logo_image = tk.PhotoImage(file=str(logo_path))
            print(f"Logo loaded successfully. Dimensions: {logo_image.width()}x{logo_image.height()}")
            
            self.logo_label = ttk.Label(logo_frame,
                                      image=logo_image,
                                      style="TLabel")
            self.logo_label.image = logo_image  # Keep a reference
            self.logo_label.pack(side=tk.RIGHT, padx=(20, 0))
            print("Logo displayed successfully")
            
        except Exception as e:
            print(f"Error loading logo: {str(e)}")
            # Create a placeholder label with error text
            self.logo_label = ttk.Label(logo_frame,
                                      text="Logo not found",
                                      style="TLabel",
                                      foreground="red")
            self.logo_label.pack(side=tk.RIGHT, padx=(20, 0))
        
        # Job list with border
        self._setup_job_list()
        
        # Bottom control buttons
        self._setup_bottom_controls()
    
    def _setup_bottom_controls(self):
        """Setup the bottom control buttons."""
        # Bottom frame for controls
        bottom_frame = ttk.Frame(self.main_frame, style="TFrame")
        bottom_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Left side: Add Files and Refresh buttons
        left_controls = ttk.Frame(bottom_frame, style="TFrame")
        left_controls.pack(side=tk.LEFT)
        
        # Add Files button with icon
        self.add_button = ttk.Button(left_controls,
                                   text="📁 Add Files",
                                   command=self.add_files,
                                   style="TButton")
        self.add_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Refresh button with icon
        self.refresh_button = ttk.Button(left_controls,
                                       text="🔄 Refresh",
                                       command=self.refresh_jobs,
                                       style="TButton")
        self.refresh_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Output button
        self.output_button = ttk.Button(left_controls,
                                      text="📂 Output",
                                      command=self.select_output_folder,
                                      style="TButton",
                                      state=tk.DISABLED)  # Initially disabled
        self.output_button.pack(side=tk.LEFT)
        
        # Right side: First frame switch, Auto-retry switch and Render button
        right_controls = ttk.Frame(bottom_frame)
        right_controls.pack(side=tk.RIGHT)
        
        # First frame switch
        self.first_frame_var = tk.BooleanVar(value=False)
        self.first_frame_switch = ttk.Checkbutton(right_controls,
                                                text="1st",
                                                variable=self.first_frame_var,
                                                command=self._toggle_first_frame,
                                                style="Switch.TCheckbutton")
        self.first_frame_switch.pack(side=tk.LEFT, padx=(0, 10))
        
        # Auto-retry switch
        self.auto_retry_var = tk.BooleanVar(value=self.auto_retry)
        self.auto_retry_switch = ttk.Checkbutton(right_controls,
                                               text="Auto-retry",
                                               variable=self.auto_retry_var,
                                               command=self._toggle_auto_retry,
                                               style="Switch.TCheckbutton")
        self.auto_retry_switch.pack(side=tk.LEFT, padx=(0, 10))
        
        # Render button
        self.render_button = ttk.Button(right_controls,
                                      text="▶️ Start Batch Render",
                                      command=self.start_render,
                                      style="Success.TButton")
        self.render_button.pack(side=tk.LEFT)

        # Status label at the bottom
        self.status_label = ttk.Label(self.main_frame,
                                    text="",
                                    style="TLabel",
                                    anchor="w")
        self.status_label.pack(fill=tk.X, pady=(10, 0))
        
        # Initialize output path variable
        self.output_path = None
    
    def _toggle_first_frame(self):
        """Toggle the first frame mode and update output button state."""
        is_first_frame = self.first_frame_var.get()
        self.output_button['state'] = tk.NORMAL if is_first_frame else tk.DISABLED
        
        # Clear output path when disabling first frame mode
        if not is_first_frame:
            self.output_path = None
            self.status_label.config(text="Output path cleared", foreground="yellow")
            self.root.after(2000, lambda: self.status_label.config(text=""))

    def select_output_folder(self):
        """Open folder selection dialog for render output."""
        folder = filedialog.askdirectory(
            title='Select Output Folder for Renders'
        )
        if folder:
            self.output_path = Path(folder)
            self.status_label.config(
                text=f"Output folder: {self.output_path.name}",
                foreground="green"
            )
            self.root.after(2000, lambda: self.status_label.config(text=""))
    
    def _setup_job_list(self):
        """Setup the job list and its controls."""
        list_frame = ttk.Frame(self.main_frame, style="TFrame")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left side: Control buttons
        self._setup_list_controls(list_frame)
        
        # Right side: Queue with scrollbar
        queue_frame = ttk.Frame(list_frame, style="TFrame")
        queue_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # Job list with border
        self.job_list = ttk.Treeview(queue_frame,
                                    columns=("File Name", "Status"),
                                    show="headings",
                                    style="Treeview",
                                    height=10)  # Show 10 rows by default
        self.job_list.heading("File Name", text="File Name")
        self.job_list.heading("Status", text="STATUS")
        self.job_list.column("File Name", width=400)
        self.job_list.column("Status", width=50, anchor="center")  # Narrower status column
        
        # Configure status column heading font
        style = ttk.Style()
        style.configure("Treeview.Heading",
                       font=('Segoe UI', 9, 'bold'))
        
        # Scrollbar attached to queue - initially hidden
        self.scrollbar = ttk.Scrollbar(queue_frame,
                                     orient=tk.VERTICAL,
                                     command=self.job_list.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.scrollbar.pack_forget()  # Hide scrollbar initially
        
        # Pack job list
        self.job_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.job_list.configure(yscrollcommand=self._on_scroll)
    
    def _on_scroll(self, *args):
        """Handle scroll events and show/hide scrollbar as needed."""
        # Update the scrollbar position
        self.scrollbar.set(*args)
        
        # Check if content exceeds visible area
        if self.job_list.yview() != (0.0, 1.0):
            # Show scrollbar if not already visible
            if not self.scrollbar.winfo_ismapped():
                self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        else:
            # Hide scrollbar if content fits
            if self.scrollbar.winfo_ismapped():
                self.scrollbar.pack_forget()
    
    def _setup_list_controls(self, parent):
        """Setup the job list control buttons."""
        control_frame = ttk.Frame(parent, style="TFrame")
        control_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        # Configure button style with larger size and rounded corners
        style = ttk.Style()
        style.configure("Square.TButton",
                       padding=10,  # Increased padding
                       font=('Segoe UI', 12, 'bold'),  # Larger font
                       width=3,  # Fixed width for consistent size
                       relief="flat")  # Flat relief for rounded corners
        
        controls = [
            ("▲", self.move_up, "Square.TButton"),
            ("▼", self.move_down, "Square.TButton"),
            ("×", self.remove_job, "Delete.TButton"),
            ("A", self.remove_all_jobs, "Delete.TButton")
        ]
        
        for text, command, style_name in controls:
            btn = SquareButton(control_frame,
                             text=text,
                             command=command,
                             style=style_name)
            btn.pack(pady=5)
    
    def _setup_drag_drop(self):
        """Setup drag and drop functionality."""
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop)
    
    def load_job_list(self):
        """Load jobs from JSON file."""
        try:
            with Path(JOB_FILE).open('r') as f:
                data = json.load(f)
                return [{'path': Path(job['path']).resolve(), 
                        'status': job.get('status', 'Ready'),
                        'attempts': job.get('attempts', 0)} 
                       for job in data]
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_job_list(self):
        """Save jobs to JSON file."""
        data = [{'path': str(job['path']), 
                'status': job['status'],
                'attempts': job.get('attempts', 0)} 
               for job in self.jobs]
        with Path(JOB_FILE).open('w') as f:
            json.dump(data, f, indent=2)

    def update_job_list(self):
        """Update the job list display."""
        self.job_list.delete(*self.job_list.get_children())
        
        # Sort jobs: first by status (Rendering first), then by attempts (fewer attempts first)
        sorted_jobs = sorted(self.jobs, 
                           key=lambda x: (0 if x['status'] == 'Rendering' else 1, 
                                        x.get('attempts', 0)))
        
        for job in sorted_jobs:
            filename = job['path'].name
            if len(filename) > 30:
                filename = "..." + filename[-30:]
            
            # Add attempt number to status if it's greater than 0
            status = job['status'].upper()
            if job.get('attempts', 0) > 0:
                status = f"{status} | Attempt {job['attempts']}"
            
            self.job_list.insert('', 'end', values=(filename, status))
            
            if job['status'] == 'Done':
                self.job_list.item(self.job_list.get_children()[-1], 
                                 tags=('done',))
        
        # Enable render button if there are any jobs in the queue
        has_jobs = len(self.jobs) > 0
        is_rendering = any(j['status'] == 'Rendering' for j in self.jobs)
        
        # Only disable the button if we're not rendering and there are no jobs
        self.render_button['state'] = tk.NORMAL if (has_jobs or is_rendering) else tk.DISABLED
    
    def on_drop(self, event):
        """Handle drag and drop events."""
        try:
            files = event.data
            if not files:
                return
                
            # Handle Windows-style paths
            files = files.strip('{}').replace('\\', '/')
            file_paths = files.split('} {') if '} {' in files else [files]
            
            for file_path in file_paths:
                job_path = Path(file_path).resolve()
                
                if job_path.suffix.lower() != '.blend':
                    self.status_label.config(
                        text="Only .blend files are supported", 
                        foreground="red")
                    continue
                    
                if not job_path.exists():
                    self.status_label.config(
                        text=f"File not found: {job_path.name}", 
                        foreground="red")
                    continue
                
                if any(Path(str(j['path'])).resolve() == job_path 
                      for j in self.jobs):
                    self.status_label.config(
                        text=f"Already in queue: {job_path.name}", 
                        foreground="yellow")
                    continue
                
                self.jobs.append({'path': job_path, 'status': 'Ready'})
                self.status_label.config(
                    text=f"Added: {job_path.name}", 
                    foreground="green")
            
            self.save_job_list()
            self.update_job_list()
            
        except Exception as e:
            self.status_label.config(
                text=f"Error adding file: {str(e)}", 
                foreground="red")
    
    def add_files(self):
        """Add files using file dialog."""
        files = filedialog.askopenfilenames(
            title='Select Blender files for RenderBatch',
            filetypes=(('Blender Files', '*.blend'),)
        )
        
        if not files:
            return
            
        for file_path in files:
            job_path = Path(file_path)
            if job_path.exists() and not any(
                j['path'] == job_path for j in self.jobs):
                self.jobs.append({'path': job_path, 'status': 'Ready'})
                self.status_label.config(
                    text=f"Added: {job_path.name}", 
                    foreground="green")
        
        self.save_job_list()
        self.update_job_list()
    
    def remove_job(self):
        """Remove selected job."""
        selection = self.job_list.selection()
        if not selection:
            return
            
        index = self.job_list.index(selection[0])
        sorted_jobs = sorted(self.jobs, 
                           key=lambda x: 0 if x['status'] == 'Rendering' else 1)
        selected_job = sorted_jobs[index]
        
        if selected_job['status'] != 'Rendering':
            self.jobs.remove(selected_job)
            self.save_job_list()
            self.status_label.config(text="Task removed", foreground="green")
            self.update_job_list()
    
    def remove_all_jobs(self):
        """Remove all jobs from the queue."""
        self.jobs = []
        self.save_job_list()
        self.status_label.config(text="All jobs removed", foreground="green")
        self.update_job_list()
    
    def move_up(self):
        """Move selected job up in the queue."""
        self._move_job(-1)
    
    def move_down(self):
        """Move selected job down in the queue."""
        self._move_job(1)
    
    def _move_job(self, direction):
        """Helper method to move jobs up or down."""
        selection = self.job_list.selection()
        if not selection:
            return
            
        index = self.job_list.index(selection[0])
        sorted_jobs = sorted(self.jobs, 
                           key=lambda x: 0 if x['status'] == 'Rendering' else 1)
        selected_job = sorted_jobs[index]
        
        original_index = self.jobs.index(selected_job)
        new_index = original_index + direction
        
        if (0 <= new_index < len(self.jobs) and 
            selected_job['status'] != 'Rendering'):
            self.jobs[original_index], self.jobs[new_index] = (
                self.jobs[new_index], self.jobs[original_index])
            self.save_job_list()
            self.update_job_list()
            self.job_list.selection_set(
                self.job_list.get_children()[index + direction])
    
    def refresh_jobs(self):
        """Refresh the job list."""
        self.jobs = self.load_job_list()
        self.update_job_list()
        self.status_label.config(
            text="Status: Waiting..." if any(
                j['status'] == 'Ready' for j in self.jobs) else "", 
            foreground="black")
    
    def start_render(self):
        """Start the batch render process."""
        # Get all jobs that are either Ready or Error
        available_jobs = []
        for job in self.jobs:
            if job['status'] == 'Ready':
                available_jobs.append(job)
            elif job['status'] == 'Error':
                if self.auto_retry:
                    # For auto-retry, move to end of queue
                    self.jobs.remove(job)
                    self.jobs.append(job)
                    available_jobs.append(job)
                else:
                    # For manual retry, just add to available jobs
                    available_jobs.append(job)
            elif job['status'] == 'Canceled':
                # Add canceled jobs to available jobs
                available_jobs.append(job)
        
        # Sort available jobs by attempts (fewer attempts first)
        available_jobs.sort(key=lambda x: x.get('attempts', 0))
        
        # Update button to show cancel state
        self.render_button.configure(
            text="❌ Cancel Render",
            command=self.cancel_render,
            style="Danger.TButton")
        self.render_button['state'] = tk.NORMAL  # Ensure button is enabled
        
        if available_jobs:
            # Only change status to Ready when actually starting the render
            job = available_jobs[0]
            job['status'] = 'Ready'
            self.update_job_list()
            
            self.status_label.config(
                text="Rendering in progress...", 
                foreground="green")
            # Start with the first available job (lowest attempts)
            threading.Thread(target=self.render_job, 
                           args=(job,), 
                           daemon=True).start()
        else:
            self.status_label.config(
                text="No jobs available to render", 
                foreground="red")
            # Reset button to show render state
            self.render_button.configure(
                text="▶️ Start Batch Render",
                command=self.start_render,
                style="Success.TButton")
    
    def cancel_render(self):
        """Cancel the current render."""
        self.should_stop = True
        self.was_cancelled = True
        
        if self.current_process:
            try:
                self.current_process.kill()
            except:
                pass
        
        # Reset button to show render state
        self.render_button.configure(
            text="▶️ Start Batch Render",
            command=self.start_render,
            style="Success.TButton")
        self.render_button['state'] = tk.NORMAL  # Ensure button is enabled
        
        self.status_label.config(text="Job cancelled", foreground="green")
    
    def render_job(self, job):
        """Render a single job."""
        if not job['path'].exists():
            return
            
        job['status'] = 'Rendering'
        self.update_job_list()
        
        # Base command without animation flag
        command = [BLENDER_PATH, "-b", str(job['path'])]
        
        # Add animation flag only if first frame mode is not enabled
        if not self.first_frame_var.get():
            command.append("-a")
        else:
            # Add output path if specified
            if hasattr(self, 'output_path') and self.output_path is not None:
                try:
                    # Create output path if it doesn't exist
                    self.output_path.mkdir(parents=True, exist_ok=True)
                    
                    # Get the original file name without extension
                    original_name = job['path'].stem
                    
                    # Create output path with original filename
                    output_path = str(self.output_path).replace('\\', '/')
                    if not output_path.endswith('/'):
                        output_path += '/'
                    # Use Blender's frame number format
                    output_path += f"{original_name}####.jpg"
                    
                    # Update status to show output path
                    self.status_label.config(
                        text=f"Output: {output_path}",
                        foreground="green"
                    )
                    
                    # Add output path argument
                    command.extend(["-o", output_path])
                    
                except Exception as e:
                    self.status_label.config(
                        text=f"Error setting output path: {str(e)}",
                        foreground="red"
                    )
                    return
            
            # Add first frame argument when first frame mode is enabled
            command.extend(["-f", "1"])
            
        # Log the final command for debugging
        print(f"Executing command: {' '.join(command)}")
        
        self.current_process = subprocess.Popen(command)
        
        while self.current_process.poll() is None and not self.should_stop:
            time.sleep(0.1)
        
        if self.should_stop:
            self.current_process.kill()
            job['status'] = 'Canceled'  # New status for user cancellation
            self.was_cancelled = True
            self.should_stop = False
        else:
            if self.current_process.returncode == 0:
                job['status'] = 'Done'
                job['attempts'] = 0  # Reset attempts on success
            else:
                job['status'] = 'Error'
                if self.auto_retry:
                    # For auto-retry, move to end of queue before incrementing attempts
                    self.jobs.remove(job)
                    self.jobs.append(job)
                job['attempts'] = job.get('attempts', 0) + 1  # Increment attempts on failure
                if self.auto_retry:
                    job['status'] = 'Ready'  # Reset status for retry
                    self.status_label.config(
                        text=f"Job {job['path'].name} will be retried (Attempt {job['attempts']})",
                        foreground="yellow")
        
        self.current_process = None
        self.update_job_list()
        
        if not self.was_cancelled:
            # Save the current state before looking for next job
            self.save_job_list()
            
            if self.auto_retry:
                # When auto-retry is on, sort all jobs by attempts and pick the one with least attempts
                available_jobs = [j for j in self.jobs if j['status'] in ['Ready', 'Error']]
                available_jobs.sort(key=lambda x: x.get('attempts', 0))
                if available_jobs:
                    next_job = available_jobs[0]
                    if next_job['status'] == 'Error':
                        next_job['status'] = 'Ready'
                        self.update_job_list()
                    threading.Thread(target=self.render_job, 
                                   args=(next_job,), 
                                   daemon=True).start()
                else:
                    # Reset button to show render state
                    self.render_button.configure(
                        text="▶️ Start Batch Render",
                        command=self.start_render,
                        style="Success.TButton")
                    self.status_label.config(text="Batch complete", 
                                           foreground="black")
                    self.was_cancelled = False
            else:
                # When auto-retry is off, just get ready jobs
                ready_jobs = [j for j in self.jobs if j['status'] == 'Ready']
                if ready_jobs:
                    threading.Thread(target=self.render_job, 
                                   args=(ready_jobs[0],), 
                                   daemon=True).start()
                else:
                    # Reset button to show render state
                    self.render_button.configure(
                        text="▶️ Start Batch Render",
                        command=self.start_render,
                        style="Success.TButton")
                    self.status_label.config(text="Batch complete", 
                                           foreground="black")
                    self.was_cancelled = False
    
    def _toggle_auto_retry(self):
        """Toggle the auto-retry state."""
        self.auto_retry = self.auto_retry_var.get()
        status_text = "Auto-retry enabled" if self.auto_retry else "Auto-retry disabled"
        self.status_label.config(text=status_text, foreground="green")
        self.root.after(2000, lambda: self.status_label.config(text=""))

if __name__ == "__main__":
    os.chdir(BASE_PATH)
    root = TkinterDnD.Tk()  # Create root window with TkinterDnD
    app = BatchRenderApp(root)
    root.mainloop()


