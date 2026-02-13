import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
import subprocess
import time
import json
import threading
import sys
import os
import re
import hashlib
from tkinterdnd2 import DND_FILES, TkinterDnD

# Version information
VERSION = "1.3.0"

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

def get_settings_file_path():
    """Get the path to the settings.json file."""
    if getattr(sys, 'frozen', False):
        # When running as executable, store in AppData/BlueMoonVirtual/RenderBatch
        appdata = Path(os.getenv('APPDATA'))
        app_dir = appdata / "BlueMoonVirtual" / "RenderBatch"
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir / "settings.json"
    else:
        # When running as script, use the project directory
        return get_base_path() / "settings.json"

def get_render_times_file_path():
    """Get the path to the render_times.json file."""
    if getattr(sys, 'frozen', False):
        # When running as executable, store in AppData/BlueMoonVirtual/RenderBatch
        appdata = Path(os.getenv('APPDATA'))
        app_dir = appdata / "BlueMoonVirtual" / "RenderBatch"
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir / "render_times.json"
    else:
        # When running as script, use the project directory
        return get_base_path() / "render_times.json"

def get_render_stats_file_path():
    """Get the path to the render_stats.json file."""
    if getattr(sys, 'frozen', False):
        appdata = Path(os.getenv('APPDATA'))
        app_dir = appdata / "BlueMoonVirtual" / "RenderBatch"
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir / "render_stats.json"
    else:
        return get_base_path() / "render_stats.json"

def load_app_settings():
    """Load settings.json as dict."""
    try:
        settings_file = get_settings_file_path()
        if settings_file.exists():
            with settings_file.open('r') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return {}

def save_app_settings(data):
    """Save settings dict to settings.json."""
    try:
        settings_file = get_settings_file_path()
        with settings_file.open('w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False

def load_blender_path():
    """Load Blender path from settings file."""
    try:
        data = load_app_settings()
        blender_path = data.get('blender_path')
        if blender_path and Path(blender_path).exists():
            return blender_path
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass
    # Default fallback path
    return r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"

def save_blender_path(blender_path):
    """Save Blender path to settings file."""
    data = load_app_settings()
    data['blender_path'] = blender_path
    return save_app_settings(data)

def load_first_frame_setting():
    """Load persisted first-frame toggle setting."""
    data = load_app_settings()
    return bool(data.get('first_frame_enabled', False))

def save_first_frame_setting(enabled):
    """Persist first-frame toggle setting."""
    data = load_app_settings()
    data['first_frame_enabled'] = bool(enabled)
    return save_app_settings(data)

BASE_PATH = get_base_path()
JOB_FILE = get_job_file_path()
SETTINGS_FILE = get_settings_file_path()
BLENDER_PATH = load_blender_path()

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
        
        # Render time tracking
        self.render_times = self.load_render_times()
        self.render_stats = self.load_render_stats()
        self.current_render_start = None
        self.time_update_timer = None
        self.batch_start_time = None
        self.last_batch_elapsed = None
        self.checked_jobs = set()
        self.job_key_map = {}
        
        # Load settings
        self.blender_path = load_blender_path()
        self.first_frame_enabled = load_first_frame_setting()
        self.blender_version = self._detect_blender_version(self.blender_path)
        
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
        
        # Configure Buttons with rounded appearance
        style.configure("TButton",
                       background=button_bg,
                       foreground=fg_color,
                       padding=(16, 10),  # Horizontal, vertical padding for rounded appearance
                       font=('Segoe UI', 9),
                       borderwidth=0,
                       relief="flat",
                       focuscolor='none')
        style.map("TButton",
                 background=[('pressed', button_pressed),
                           ('active', selected_bg)],
                 relief=[('pressed', 'flat')])
        
        # Configure success button with rounded appearance
        style.configure("Success.TButton",
                       background="#28a745",
                       foreground=fg_color,
                       padding=(20, 12),  # Extra padding for main action button
                       font=('Segoe UI', 9, 'bold'),
                       borderwidth=0,
                       relief="flat",
                       focuscolor='none')
        style.map("Success.TButton",
                 background=[('pressed', "#218838"),
                           ('active', "#28a745")])

        # Configure first-frame render button style (blue)
        style.configure("FirstFrame.TButton",
                       background=accent_color,
                       foreground=fg_color,
                       padding=(20, 12),
                       font=('Segoe UI', 9, 'bold'),
                       borderwidth=0,
                       relief="flat",
                       focuscolor='none')
        style.map("FirstFrame.TButton",
                 background=[('pressed', "#006bb3"),
                           ('active', accent_color)])
        
        # Configure danger button with rounded appearance
        style.configure("Danger.TButton",
                       background="#dc3545",
                       foreground=fg_color,
                       padding=(20, 12),  # Extra padding for main action button
                       font=('Segoe UI', 9, 'bold'),
                       borderwidth=0,
                       relief="flat",
                       focuscolor='none')
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
        
        # Configure delete button style with rounded appearance
        style.configure("Delete.TButton",
                       background=delete_bg,
                       foreground=fg_color,
                       padding=(14, 10),
                       font=('Segoe UI', 12, 'bold'),
                       width=3,
                       relief="flat",
                       focuscolor='none')
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
        ttk.Label(title_frame,
                 text=f"v{VERSION}",
                 font=('Segoe UI', 10, 'italic'),
                 foreground="#888888",
                 style="TLabel",
                 anchor="w").pack(side=tk.TOP, fill=tk.X, pady=(2, 0))
        
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
        self._bind_hint(self.add_button, "Add .blend files to the queue")
        
        # Refresh button with icon
        self.refresh_button = ttk.Button(left_controls,
                                       text="🔄 Refresh",
                                       command=self.refresh_jobs,
                                       style="TButton")
        self.refresh_button.pack(side=tk.LEFT, padx=(0, 5))
        self._bind_hint(self.refresh_button, "Reload queue from jobs file")
        
        # Output button
        self.output_button = ttk.Button(left_controls,
                                      text="📂 Output",
                                      command=self.select_output_folder,
                                      style="TButton",
                                      state=tk.DISABLED)  # Initially disabled
        self.output_button.pack(side=tk.LEFT)
        self._bind_hint(self.output_button, "Pick output folder (non-1st mode)")
        
        # Settings button
        self.settings_button = ttk.Button(left_controls,
                                        text="⚙️ Settings",
                                        command=self.select_blender_path,
                                        style="TButton")
        self.settings_button.pack(side=tk.LEFT, padx=(5, 0))
        self._bind_hint(self.settings_button, "Select Blender executable")

        # Info button (statistics popup)
        self.info_button = ttk.Button(left_controls,
                                      text="ℹ️",
                                      command=self.show_stats_popup,
                                      style="TButton",
                                      width=3)
        self.info_button.pack(side=tk.LEFT, padx=(5, 0))
        self._bind_hint(self.info_button, "Render statistics and logs")
        
        # Right side: First frame switch, Auto-retry switch and Render button
        right_controls = ttk.Frame(bottom_frame)
        right_controls.pack(side=tk.RIGHT)
        
        # First frame switch
        self.first_frame_var = tk.BooleanVar(value=self.first_frame_enabled)
        self.first_frame_switch = ttk.Checkbutton(right_controls,
                                                text="1st",
                                                variable=self.first_frame_var,
                                                command=self._toggle_first_frame,
                                                style="Switch.TCheckbutton")
        self.first_frame_switch.pack(side=tk.LEFT, padx=(0, 10))
        self._bind_hint(self.first_frame_switch, "Render only frame 1")
        # Apply initial state from persisted setting.
        self.output_button['state'] = tk.DISABLED if self.first_frame_var.get() else tk.NORMAL
        
        # Auto-retry switch
        self.auto_retry_var = tk.BooleanVar(value=self.auto_retry)
        self.auto_retry_switch = ttk.Checkbutton(right_controls,
                                               text="Auto-retry",
                                               variable=self.auto_retry_var,
                                               command=self._toggle_auto_retry,
                                               style="Switch.TCheckbutton")
        self.auto_retry_switch.pack(side=tk.LEFT, padx=(0, 10))
        self._bind_hint(self.auto_retry_switch, "Retry failed jobs automatically")
        
        # Render button + total estimate (estimate shown under button)
        render_controls = ttk.Frame(right_controls, style="TFrame")
        render_controls.pack(side=tk.LEFT)

        self.render_button = ttk.Button(render_controls,
                                      text="▶️ Start Batch Render",
                                      command=self.start_render,
                                      style="Success.TButton")
        self.render_button.pack(side=tk.TOP)
        self._bind_hint(self.render_button, "Start or cancel batch render")
        self._set_render_button_idle()

        self.total_estimate_label = ttk.Label(
            render_controls,
            text="",
            style="TLabel",
            anchor="center",
            foreground="#9ecbff",
            font=('Segoe UI', 8, 'italic')
        )
        self.total_estimate_label.pack(side=tk.TOP, pady=(4, 0))

        # Status label at the bottom
        self.status_label = ttk.Label(self.main_frame,
                                    text="",
                                    style="TLabel",
                                    anchor="w")
        self.status_label.pack(fill=tk.X, pady=(10, 0))

        # Footer: Blender executable version
        self.blender_version_label = ttk.Label(
            self.main_frame,
            text=f"Blender: {self.blender_version}",
            style="TLabel",
            anchor="w",
            foreground="#9a9a9a",
            font=('Segoe UI', 8, 'italic')
        )
        self.blender_version_label.pack(fill=tk.X, pady=(3, 0))
        
        # Initialize output path variable
        self.output_path = None
    
    def _toggle_first_frame(self):
        """Toggle the first frame mode and update output button state."""
        is_first_frame = self.first_frame_var.get()
        save_first_frame_setting(is_first_frame)
        # Disable output button in first frame mode (uses Blender file settings)
        self.output_button['state'] = tk.DISABLED if is_first_frame else tk.NORMAL
        if not (self.current_process and self.current_process.poll() is None):
            self._set_render_button_idle()
        
        # Clear output path when enabling first frame mode (we'll use Blender file settings)
        if is_first_frame:
            self.output_path = None
            self.status_label.config(text="First frame mode: using project output settings", foreground="green")
            self.root.after(3000, lambda: self.status_label.config(text=""))

    def _set_render_button_idle(self):
        """Set render button text/style for idle state based on mode."""
        if self.first_frame_var.get():
            self.render_button.configure(
                text="Render 1st Frame",
                command=self.start_render,
                style="FirstFrame.TButton"
            )
        else:
            self.render_button.configure(
                text="▶️ Start Batch Render",
                command=self.start_render,
                style="Success.TButton"
            )

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
    
    def select_blender_path(self):
        """Open file selection dialog for Blender executable."""
        # Show current blender path
        current_path = Path(self.blender_path)
        if current_path.exists():
            self.status_label.config(
                text=f"Current: {current_path.name}",
                foreground="blue"
            )
        else:
            self.status_label.config(
                text="Blender path not found - please select",
                foreground="red"
            )
        
        file_path = filedialog.askopenfilename(
            title='Select Blender Executable (blender.exe)',
            filetypes=(('Executable Files', '*.exe'), ('All Files', '*.*'))
        )
        if file_path:
            blender_path = Path(file_path)
            if blender_path.name.lower() == 'blender.exe':
                self.blender_path = str(blender_path)
                if save_blender_path(self.blender_path):
                    self.blender_version = self._detect_blender_version(self.blender_path)
                    self.blender_version_label.config(text=f"Blender: {self.blender_version}")
                    self.status_label.config(
                        text=f"Blender path saved: {blender_path.name}",
                        foreground="green"
                    )
                else:
                    self.status_label.config(
                        text="Error saving Blender path",
                        foreground="red"
                    )
            else:
                self.status_label.config(
                    text="Please select blender.exe",
                    foreground="red"
                )
            self.root.after(3000, lambda: self.status_label.config(text=""))
    
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
                                    columns=("Select", "File Name", "Status", "Reset", "Time"),
                                    show="headings",
                                    style="Treeview",
                                    selectmode="extended",
                                    height=10)  # Show 10 rows by default
        self.job_list.heading("Select", text="☐")
        self.job_list.heading("File Name", text="File Name")
        self.job_list.heading("Status", text="STATUS")
        self.job_list.heading("Reset", text="RESET")
        self.job_list.heading("Time", text="TIME")
        self.job_list.column("Select", width=45, anchor="center")
        self.job_list.column("File Name", width=300)
        self.job_list.column("Status", width=125, anchor="center")
        self.job_list.column("Reset", width=65, anchor="center")
        self.job_list.column("Time", width=100, anchor="center")
        
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
        self.job_list.bind("<Button-1>", self._on_job_list_click, add="+")
    
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

    def _on_job_list_click(self, event):
        """Handle checkbox/reset clicks while keeping extended selection behavior."""
        region = self.job_list.identify("region", event.x, event.y)
        column = self.job_list.identify_column(event.x)

        # Header click on checkbox column toggles all checkboxes.
        if region == "heading" and column == "#1":
            all_keys = {self._job_key(job) for job in self.jobs}
            if all_keys and self.checked_jobs.issuperset(all_keys):
                self.checked_jobs.clear()
                self.job_list.selection_remove(self.job_list.selection())
            else:
                self.checked_jobs = set(all_keys)
                self.job_list.selection_set(tuple(all_keys))
            self.update_job_list()
            return "break"

        if region != "cell":
            return

        row_id = self.job_list.identify_row(event.y)
        if not row_id:
            return

        # Checkbox column (first visible column): toggle row checkbox.
        if column == "#1":
            if row_id in self.checked_jobs:
                self.checked_jobs.remove(row_id)
                self.job_list.selection_remove(row_id)
            else:
                self.checked_jobs.add(row_id)
                self.job_list.selection_add(row_id)
            self.update_job_list()
            return "break"

        # RESET column is now the 4th visible column (#4).
        if column != "#4":
            return

        values = self.job_list.item(row_id, "values")
        if len(values) < 4 or values[3] != "↺":
            return

        selected_job = self._get_job_by_key(row_id)
        if not selected_job:
            return
        if selected_job["status"] != "Done":
            return

        selected_job["status"] = "Ready"
        selected_job["attempts"] = 0
        selected_job["last_render_time"] = None
        self.checked_jobs.discard(row_id)
        self.save_job_list()
        self.update_job_list()
        self.status_label.config(text=f"Reset: {selected_job['path'].name}", foreground="green")
        self.root.after(2000, lambda: self.status_label.config(text=""))
        return "break"
    
    def _setup_list_controls(self, parent):
        """Setup the job list control buttons."""
        control_frame = ttk.Frame(parent, style="TFrame")
        control_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        # Configure button style with larger size and rounded appearance
        style = ttk.Style()
        style.configure("Square.TButton",
                       padding=(14, 10),  # Horizontal, vertical padding for rounded appearance
                       font=('Segoe UI', 12, 'bold'),
                       width=3,
                       relief="flat",
                       focuscolor='none')
        
        controls = [
            ("▲", self.move_up, "Square.TButton"),
            ("▼", self.move_down, "Square.TButton"),
            ("✓", self.clear_done_jobs, "Delete.TButton"),
            ("🔄", self.reset_selected_job, "Square.TButton"),
            ("⟲", self.reset_all_jobs, "Square.TButton"),
            ("×", self.remove_job, "Delete.TButton"),
            ("A", self.remove_all_jobs, "Delete.TButton")
        ]
        hints = {
            "▲": "Move selected job up",
            "▼": "Move selected job down",
            "✓": "Clear all DONE jobs",
            "🔄": "Reset selected jobs to Ready",
            "⟲": "Reset all non-rendering jobs to Ready",
            "×": "Delete selected jobs",
            "A": "Delete all jobs",
        }
        
        for text, command, style_name in controls:
            btn = SquareButton(control_frame,
                             text=text,
                             command=command,
                             style=style_name)
            btn.pack(pady=5)
            self._bind_hint(btn, hints.get(text, ""))
    
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
                        'attempts': job.get('attempts', 0),
                        'last_render_time': job.get('last_render_time')} 
                       for job in data]
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_job_list(self):
        """Save jobs to JSON file."""
        data = [{'path': str(job['path']), 
                'status': job['status'],
                'attempts': job.get('attempts', 0),
                'last_render_time': job.get('last_render_time')} 
               for job in self.jobs]
        with Path(JOB_FILE).open('w') as f:
            json.dump(data, f, indent=2)

    def load_render_times(self):
        """Load render time history from JSON file."""
        try:
            render_times_file = get_render_times_file_path()
            if render_times_file.exists():
                with render_times_file.open('r') as f:
                    return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return {}

    def load_render_stats(self):
        """Load persistent render statistics and logs."""
        defaults = {
            "total_successful_renders": 0,
            "total_errors": 0,
            "total_attempts": 0,
            "total_render_seconds": 0.0,
            "recent_logs": []
        }
        try:
            stats_file = get_render_stats_file_path()
            if stats_file.exists():
                with stats_file.open('r') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        for key, value in defaults.items():
                            data.setdefault(key, value)
                        return data
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return defaults

    def save_render_stats(self):
        """Save persistent render statistics."""
        stats_file = get_render_stats_file_path()
        with stats_file.open('w') as f:
            json.dump(self.render_stats, f, indent=2)

    def _record_render_log(self, job_name, status, duration_seconds, attempt_number):
        """Append one render event to recent logs."""
        logs = self.render_stats.get("recent_logs", [])
        logs.append({
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "file": job_name,
            "status": status,
            "attempt": attempt_number,
            "duration_seconds": round(float(duration_seconds), 2),
        })
        self.render_stats["recent_logs"] = logs[-60:]  # keep recent logs bounded

    def _detect_blender_version(self, blender_path):
        """Return Blender version string from blender.exe."""
        try:
            if not blender_path or not Path(blender_path).exists():
                return "not found"
            result = subprocess.run(
                [str(blender_path), "--version"],
                capture_output=True,
                text=True,
                timeout=8,
                encoding="utf-8",
                errors="replace"
            )
            first_line = (result.stdout or "").splitlines()
            if first_line:
                line = first_line[0].strip()
                if line:
                    return line
            return "unknown"
        except Exception:
            return "unknown"

    def show_stats_popup(self):
        """Open a popup window with render statistics and recent logs."""
        successful = int(self.render_stats.get("total_successful_renders", 0))
        errors = int(self.render_stats.get("total_errors", 0))
        attempts = int(self.render_stats.get("total_attempts", 0))
        total_seconds = float(self.render_stats.get("total_render_seconds", 0.0))
        success_rate = (successful / attempts * 100.0) if attempts > 0 else 0.0
        avg_success_time = (total_seconds / successful) if successful > 0 else 0.0

        popup = tk.Toplevel(self.root)
        popup.title("Render Statistics")
        popup.geometry("620x460")
        popup.transient(self.root)
        popup.grab_set()
        popup.configure(bg="#1e1e1e")

        header = ttk.Label(
            popup,
            text="Render Statistics",
            style="TLabel",
            font=('Segoe UI', 12, 'bold')
        )
        header.pack(anchor="w", padx=12, pady=(12, 6))

        summary_lines = [
            f"Successful renders: {successful}",
            f"Errors: {errors}",
            f"Total attempts: {attempts}",
            f"Success rate: {success_rate:.1f}%",
            f"Total render time: {self.format_time(total_seconds)}",
            f"Average time per successful render: {self.format_time(avg_success_time) if successful else '---'}",
        ]
        summary = ttk.Label(
            popup,
            text="\n".join(summary_lines),
            style="TLabel",
            justify="left"
        )
        summary.pack(anchor="w", padx=12, pady=(0, 10))

        logs_label = ttk.Label(popup, text="Recent logs", style="TLabel", font=('Segoe UI', 10, 'bold'))
        logs_label.pack(anchor="w", padx=12, pady=(0, 4))

        logs_box = tk.Text(
            popup,
            height=14,
            bg="#252525",
            fg="#e6e6e6",
            insertbackground="#e6e6e6",
            relief="flat",
            wrap="none"
        )
        logs_box.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))

        recent_logs = list(self.render_stats.get("recent_logs", []))[-25:]
        if recent_logs:
            for entry in reversed(recent_logs):
                line = (
                    f"{entry.get('time', '')} | {entry.get('status', ''):<7} | "
                    f"A{entry.get('attempt', 0):<2} | {self.format_time(entry.get('duration_seconds', 0))} | "
                    f"{entry.get('file', '')}\n"
                )
                logs_box.insert(tk.END, line)
        else:
            logs_box.insert(tk.END, "No logs yet.\n")
        logs_box.config(state=tk.DISABLED)

        close_btn = ttk.Button(popup, text="Close", command=popup.destroy, style="TButton")
        close_btn.pack(anchor="e", padx=12, pady=(0, 12))

    def save_render_times(self):
        """Save render time history to JSON file."""
        render_times_file = get_render_times_file_path()
        with render_times_file.open('w') as f:
            json.dump(self.render_times, f, indent=2)

    def get_estimated_time(self, filename):
        """Get estimated render time for a file based on history.
        Returns estimated seconds, or None if no data available."""
        if filename not in self.render_times:
            return None
        
        times = self.render_times[filename]
        if not times:
            return None
        
        # Calculate median with outlier detection
        sorted_times = sorted(times)
        n = len(sorted_times)
        
        if n == 1:
            return sorted_times[0]
        
        # Calculate median
        if n % 2 == 0:
            median = (sorted_times[n//2 - 1] + sorted_times[n//2]) / 2
        else:
            median = sorted_times[n//2]
        
        # If we have enough data, filter outliers (keep values within 2x of median)
        if n >= 3:
            filtered = [t for t in sorted_times if t <= median * 2.5 and t >= median / 2.5]
            if filtered:
                sorted_times = filtered
                n = len(sorted_times)
                # Recalculate median with filtered data
                if n % 2 == 0:
                    median = (sorted_times[n//2 - 1] + sorted_times[n//2]) / 2
                else:
                    median = sorted_times[n//2]
        
        return median

    def record_render_time(self, filename, duration_seconds):
        """Record a render time for a file."""
        if filename not in self.render_times:
            self.render_times[filename] = []
        
        # Keep only the last 10 render times to avoid bloat and adapt to changes
        times = self.render_times[filename]
        times.append(duration_seconds)
        
        # If we have more than 10 entries, check if this one is way off
        if len(times) > 10:
            # Keep the most recent 10, but if the new time is very different,
            # it might indicate a project change - keep only recent 5 + new one
            median = self.get_estimated_time(filename)
            if median and (duration_seconds > median * 3 or duration_seconds < median / 3):
                # Major change detected - rebase with recent data only
                self.render_times[filename] = times[-5:]
            else:
                # Normal variation - keep last 10
                self.render_times[filename] = times[-10:]
        
        self.save_render_times()

    def format_time(self, seconds):
        """Format seconds into HH:MM:SS or MM:SS."""
        if seconds is None:
            return "---"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    def _job_key(self, job):
        """Return a stable, safe key for a job row."""
        return hashlib.md5(str(job['path']).encode('utf-8')).hexdigest()

    def _get_job_by_key(self, key):
        """Return job object by row key, or None."""
        return self.job_key_map.get(key)

    def _show_hint(self, text):
        """Show temporary hint text in the status bar."""
        self.status_label.config(text=text, foreground="gray")

    def _clear_hint(self):
        """Clear hint text without overriding active status messages."""
        if self.status_label.cget("foreground") == "gray":
            self.status_label.config(text="")

    def _bind_hint(self, widget, text):
        """Attach hover hint behavior to a widget."""
        widget.bind("<Enter>", lambda e, t=text: self._show_hint(t), add="+")
        widget.bind("<Leave>", lambda e: self._clear_hint(), add="+")

    def _median_value(self, values):
        """Return median for a non-empty list of numeric values."""
        ordered = sorted(values)
        n = len(ordered)
        mid = n // 2
        if n % 2 == 0:
            return (ordered[mid - 1] + ordered[mid]) / 2
        return ordered[mid]

    def _percentile_value(self, values, percentile):
        """Return percentile value for a non-empty list."""
        ordered = sorted(values)
        if not ordered:
            return None
        if len(ordered) == 1:
            return ordered[0]
        idx = int(round((len(ordered) - 1) * percentile))
        idx = max(0, min(idx, len(ordered) - 1))
        return ordered[idx]

    def _get_conservative_estimate(self, filename):
        """Return a conservative estimate to avoid over-optimistic countdown."""
        base = self.get_estimated_time(filename)
        if base is None:
            return None

        history = self.render_times.get(filename, [])
        if not history:
            return base

        # Use upper quartile as baseline to avoid optimistic medians.
        p75 = self._percentile_value(history, 0.75)
        conservative = max(base, p75 if p75 is not None else base)

        # Add safety margin that shrinks as history grows.
        n = len(history)
        if n <= 1:
            factor = 1.6
        elif n <= 3:
            factor = 1.4
        elif n <= 6:
            factor = 1.25
        else:
            factor = 1.15
        return conservative * factor

    def _compute_total_estimated_seconds(self):
        """Estimate total remaining render time excluding jobs already Done.
        Returns (total_seconds, inferred_count) or (None, 0) when unavailable."""
        pending_jobs = [j for j in self.jobs if j.get('status') != 'Done']
        if not pending_jobs:
            return None, 0

        known_estimates = []
        for job in pending_jobs:
            est = self._get_conservative_estimate(job['path'].name)
            if est is not None:
                known_estimates.append(est)

        # If pending jobs have no direct estimates, build a global fallback from historical data.
        if not known_estimates:
            fallback_pool = []
            # Use finished job durations from current queue.
            for j in self.jobs:
                if j.get('status') == 'Done' and j.get('last_render_time'):
                    fallback_pool.append(j['last_render_time'])
            # Use global render history (all files).
            for values in self.render_times.values():
                if isinstance(values, list):
                    fallback_pool.extend([v for v in values if isinstance(v, (int, float)) and v > 0])

            if not fallback_pool:
                return None, 0
            known_estimates = fallback_pool

        fallback_estimate = self._median_value(known_estimates) * 1.10

        total = 0.0
        inferred_count = 0
        for job in pending_jobs:
            est = self._get_conservative_estimate(job['path'].name)
            if est is None:
                est = fallback_estimate
                inferred_count += 1

            # If currently rendering, estimate remaining time instead of full estimate.
            if job.get('status') == 'Rendering' and self.current_render_start:
                elapsed = max(0.0, time.time() - self.current_render_start)
                # Keep a non-zero floor to avoid hitting 00:00 too early.
                floor_seconds = max(est * 0.15, 15 if est >= 60 else 5)
                total += max(est - elapsed, floor_seconds)
            else:
                total += est

        return total, inferred_count

    def _update_total_estimate_display(self):
        """Refresh estimate text shown under the render button."""
        total_seconds, inferred_count = self._compute_total_estimated_seconds()
        if total_seconds is None:
            if self.last_batch_elapsed is not None:
                self.total_estimate_label.config(
                    text=f"Last run: {self.format_time(self.last_batch_elapsed)}"
                )
            else:
                self.total_estimate_label.config(text="")
            return

        estimate_text = f"Total est: ~{self.format_time(total_seconds)}"
        if inferred_count > 0:
            estimate_text += f" (inferred {inferred_count})"
        self.total_estimate_label.config(text=estimate_text)

    def update_job_list(self):
        """Update the job list display."""
        previous_selection = set(self.job_list.selection())
        self.job_list.delete(*self.job_list.get_children())
        self.job_key_map = {}
        
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
            attempts = job.get('attempts', 0)
            if job['status'] == 'Done':
                # Keep done rows clean unless more than one attempt was needed.
                if attempts > 1:
                    status = f"{status} | Attempts {attempts}"
            elif job['status'] == 'Rendering':
                # Current in-flight attempt number.
                if attempts > 0:
                    status = f"{status} | Attempt {attempts}"
            else:
                # Show next attempt number for queued/error/canceled jobs.
                if attempts > 0:
                    status = f"{status} | Next {attempts + 1}"
            
            # Get time estimate or elapsed time
            time_str = "---"
            if job['status'] == 'Rendering':
                # Show elapsed time for currently rendering job
                if self.current_render_start:
                    elapsed = time.time() - self.current_render_start
                    estimated = self.get_estimated_time(job['path'].name)
                    if estimated:
                        time_str = f"{self.format_time(elapsed)} / {self.format_time(estimated)}"
                    else:
                        time_str = self.format_time(elapsed)
            elif job['status'] == 'Done':
                # Show actual render time for completed jobs
                if job.get('last_render_time'):
                    time_str = self.format_time(job['last_render_time'])
            elif job['status'] in ['Ready', 'Error', 'Canceled']:
                # Show estimate for pending jobs
                estimated = self.get_estimated_time(job['path'].name)
                if estimated:
                    time_str = f"~{self.format_time(estimated)}"

            reset_action = "↺" if job["status"] == "Done" else ""
            job_key = self._job_key(job)
            self.job_key_map[job_key] = job
            checked_mark = "☑" if job_key in self.checked_jobs else "☐"
            self.job_list.insert('', 'end', iid=job_key, values=(checked_mark, filename, status, reset_action, time_str))
            
            if job['status'] == 'Done':
                self.job_list.item(job_key, tags=('done',))

        # Drop stale checked keys (jobs removed from queue).
        self.checked_jobs.intersection_update(set(self.job_key_map.keys()))

        # Restore selection for existing keys.
        restorable_selection = [k for k in previous_selection if k in self.job_key_map]
        if restorable_selection:
            self.job_list.selection_set(restorable_selection)

        # Keep checked rows selected to support bulk actions naturally.
        if self.checked_jobs:
            self.job_list.selection_add(tuple(self.checked_jobs))

        # Update select-all header checkbox state.
        all_keys = set(self.job_key_map.keys())
        header_mark = "☑" if all_keys and self.checked_jobs.issuperset(all_keys) else "☐"
        self.job_list.heading("Select", text=header_mark)
        
        # Enable render button if there are any jobs in the queue
        has_jobs = len(self.jobs) > 0
        is_rendering = any(j['status'] == 'Rendering' for j in self.jobs)
        
        # Only disable the button if we're not rendering and there are no jobs
        self.render_button['state'] = tk.NORMAL if (has_jobs or is_rendering) else tk.DISABLED
        self._update_total_estimate_display()
    
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
                
                self.jobs.append({'path': job_path, 'status': 'Ready', 'attempts': 0, 'last_render_time': None})
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
                self.jobs.append({'path': job_path, 'status': 'Ready', 'attempts': 0, 'last_render_time': None})
                self.status_label.config(
                    text=f"Added: {job_path.name}", 
                    foreground="green")
        
        self.save_job_list()
        self.update_job_list()
    
    def remove_job(self):
        """Remove selected job."""
        selected_keys = set(self.job_list.selection()) | set(self.checked_jobs)
        if not selected_keys:
            self.status_label.config(text="No jobs selected", foreground="yellow")
            self.root.after(1500, lambda: self._clear_hint())
            return

        removed_count = 0
        blocked_count = 0
        for key in list(selected_keys):
            job = self._get_job_by_key(key)
            if not job:
                continue
            if job['status'] == 'Rendering':
                blocked_count += 1
                continue
            try:
                self.jobs.remove(job)
                removed_count += 1
                self.checked_jobs.discard(key)
            except ValueError:
                pass

        if removed_count > 0:
            self.save_job_list()
            self.update_job_list()
            msg = f"Removed {removed_count} job(s)"
            if blocked_count:
                msg += f" ({blocked_count} rendering skipped)"
            self.status_label.config(text=msg, foreground="green")
        elif blocked_count:
            self.status_label.config(text="Cannot remove rendering job(s)", foreground="red")
        else:
            self.status_label.config(text="No removable jobs selected", foreground="yellow")
    
    def remove_all_jobs(self):
        """Remove all jobs from the queue."""
        self.jobs = []
        self.checked_jobs.clear()
        self.job_key_map = {}
        self.save_job_list()
        self.status_label.config(text="All jobs removed", foreground="green")
        self.update_job_list()

    def clear_done_jobs(self):
        """Remove all jobs with Done status from the queue."""
        done_jobs = [j for j in self.jobs if j.get('status') == 'Done']
        if not done_jobs:
            self.status_label.config(text="No done jobs to clear", foreground="yellow")
            self.root.after(1500, lambda: self._clear_hint())
            return

        done_keys = {self._job_key(j) for j in done_jobs}
        self.jobs = [j for j in self.jobs if j.get('status') != 'Done']
        self.checked_jobs.difference_update(done_keys)
        self.save_job_list()
        self.update_job_list()
        self.status_label.config(text=f"Cleared {len(done_jobs)} done job(s)", foreground="green")
    
    def reset_selected_job(self):
        """Reset selected job status to Ready."""
        selected_keys = set(self.job_list.selection()) | set(self.checked_jobs)
        if not selected_keys:
            self.status_label.config(text="No job selected", foreground="yellow")
            return

        reset_count = 0
        blocked_count = 0
        for key in list(selected_keys):
            job = self._get_job_by_key(key)
            if not job:
                continue
            if job['status'] == 'Rendering':
                blocked_count += 1
                continue
            if job['status'] != 'Ready':
                job['status'] = 'Ready'
                job['attempts'] = 0
                job['last_render_time'] = None
                reset_count += 1

        if reset_count > 0:
            self.save_job_list()
            self.update_job_list()
            msg = f"Reset {reset_count} job(s) to Ready"
            if blocked_count:
                msg += f" ({blocked_count} rendering skipped)"
            self.status_label.config(text=msg, foreground="green")
            self.root.after(2000, lambda: self.status_label.config(text=""))
        elif blocked_count:
            self.status_label.config(text="Cannot reset rendering job(s)", foreground="red")
        else:
            self.status_label.config(text="Selected jobs already Ready", foreground="yellow")
    
    def reset_all_jobs(self):
        """Reset all non-rendering jobs to Ready status."""
        reset_count = 0
        for job in self.jobs:
            if job['status'] != 'Rendering' and job['status'] != 'Ready':
                job['status'] = 'Ready'
                job['attempts'] = 0
                reset_count += 1
        
        if reset_count > 0:
            self.save_job_list()
            self.update_job_list()
            self.status_label.config(text=f"Reset {reset_count} job(s) to Ready", foreground="green")
            self.root.after(2000, lambda: self.status_label.config(text=""))
        else:
            self.status_label.config(text="No jobs to reset", foreground="yellow")
            self.root.after(2000, lambda: self.status_label.config(text=""))
    
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
        # Always reset stale cancel flags when a new batch is started.
        self.should_stop = False
        self.was_cancelled = False

        # Guard against accidental double-start while a process is alive.
        if self.current_process and self.current_process.poll() is None:
            self.status_label.config(text="Render already in progress...", foreground="yellow")
            return

        # Validate blender path exists
        if not Path(self.blender_path).exists():
            self.status_label.config(
                text="Blender path not found. Please check settings.",
                foreground="red"
            )
            return
        
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
            # New batch start timestamp for total elapsed reporting.
            if self.batch_start_time is None:
                self.batch_start_time = time.time()
            self.last_batch_elapsed = None

            # Only change status to Ready when actually starting the render
            job = available_jobs[0]
            job['status'] = 'Ready'
            self.update_job_list()
            
            self.status_label.config(
                text="Rendering in progress...", 
                foreground="green")
            
            print(f"\n{'='*80}")
            print(f"🚀 BATCH RENDER STARTED - {len(available_jobs)} job(s) in queue")
            print(f"{'='*80}\n")
            
            # Start with the first available job (lowest attempts)
            threading.Thread(target=self.render_job, 
                           args=(job,), 
                           daemon=True).start()
        else:
            self.status_label.config(
                text="No jobs available to render", 
                foreground="red")
            # Reset button to show render state
            self._set_render_button_idle()
    
    def cancel_render(self):
        """Cancel the current render."""
        # Only enter cancel mode if there is an active process.
        if self.current_process and self.current_process.poll() is None:
            self.should_stop = True
            self.was_cancelled = True
            try:
                self.current_process.kill()
            except Exception:
                pass
        else:
            # Prevent stale cancel flags from auto-canceling the next start.
            self.should_stop = False
            self.was_cancelled = False
        
        # Reset button to show render state
        self._set_render_button_idle()
        self.render_button['state'] = tk.NORMAL  # Ensure button is enabled
        
        self.status_label.config(
            text="Job cancelled" if self.current_process else "Nothing to cancel",
            foreground="green"
        )

    def _start_time_update(self):
        """Start periodic UI updates to show elapsed time."""
        self._update_elapsed_time()

    def _update_elapsed_time(self):
        """Update the job list to show current elapsed time."""
        if self.current_render_start and not self.should_stop:
            self.update_job_list()
            # Schedule next update in 1 second
            self.time_update_timer = self.root.after(1000, self._update_elapsed_time)

    def _stop_time_update(self):
        """Stop the periodic time updates."""
        if self.time_update_timer:
            self.root.after_cancel(self.time_update_timer)
            self.time_update_timer = None

    def _is_relevant_blender_line(self, line):
        """Filter Blender output to important progress/warning/error lines."""
        lower = line.lower()

        # Keep explicit warnings/errors and traceback context.
        if (
            "error" in lower
            or "warning" in lower
            or "traceback" in lower
            or lower.startswith("file \"")
            or lower.startswith("exception")
        ):
            return True

        # Keep progress/status lines.
        progress_tokens = [
            "rendering frame",
            "sample ",
            "samples ",
            "tile ",
            "path tracing",
            "fra:",
            "remaining:",
            "mem:",
            "saved:",
            "composit",
            "frame ",
            "initializing render",
            "render complete",
        ]
        if any(token in lower for token in progress_tokens):
            return True

        # Keep our own script lines/emojis and Blender version line.
        if line.startswith("  ") or line.startswith("✅") or line.startswith("❌") or line.startswith("🎬") or line.startswith("📸") or line.startswith("💾"):
            return True
        if line.startswith("Blender "):
            return True

        return False

    def _normalize_blender_output(self, line):
        """Normalize useful lines for cleaner console display."""
        # Collapse excessive whitespace for easier reading.
        line = re.sub(r"\s+", " ", line).strip()
        return line
    
    def render_job(self, job):
        """Render a single job."""
        if not job['path'].exists():
            return
            
        # Count attempt at the start of each run.
        job['attempts'] = job.get('attempts', 0) + 1
        self.render_stats["total_attempts"] = int(self.render_stats.get("total_attempts", 0)) + 1
        self.save_render_stats()
        job['status'] = 'Rendering'
        
        # Start timing
        self.current_render_start = time.time()
        self._start_time_update()
        
        self.update_job_list()
        
        # Base command (minimal output - errors and warnings only)
        command = [self.blender_path, "-b", str(job['path'])]
        
        # Use Python scripts for detailed progress
        if not self.first_frame_var.get():
            # Animation mode: use animation script for frame-by-frame progress
            render_script = BASE_PATH / "render_animation.py"
            if not render_script.exists():
                # Fallback for development/source mode
                render_script = get_base_path() / "src" / "render_animation.py"
            
            command.extend(["--python", str(render_script)])
            
            # Update status
            self.status_label.config(
                text=f"Rendering animation (using project frame range)",
                foreground="green"
            )
        else:
            # First frame mode: use single frame script
            render_script = BASE_PATH / "render_progress.py"
            if not render_script.exists():
                # Fallback for development/source mode
                render_script = get_base_path() / "src" / "render_progress.py"
            
            command.extend(["--python", str(render_script)])
            
            # Update status
            self.status_label.config(
                text=f"Rendering frame 1 (using project output settings)",
                foreground="green"
            )
            
        # Log start of render (clean output)
        print(f"\n{'='*80}")
        print(f"RENDER: {job['path'].name}")
        print(f"{'='*80}")
        
        # Create subprocess and stream filtered console output
        self.current_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1
        )

        if self.current_process.stdout:
            for raw_line in self.current_process.stdout:
                if self.should_stop and self.current_process.poll() is None:
                    try:
                        self.current_process.kill()
                    except Exception:
                        pass
                    break
                line = raw_line.strip()
                if not line:
                    continue
                if self._is_relevant_blender_line(line):
                    print(self._normalize_blender_output(line), flush=True)

        # Ensure process has finished.
        self.current_process.wait()
        
        # Stop timing and record
        render_duration = time.time() - self.current_render_start if self.current_render_start else 0
        self._stop_time_update()
        
        if self.should_stop:
            self.current_process.kill()
            job['status'] = 'Canceled'  # New status for user cancellation
            self.was_cancelled = True
            self.should_stop = False
            self.batch_start_time = None
            print(f"\n{'='*80}")
            print(f"❌ CANCELED: {job['path'].name}")
            print(f"{'='*80}\n")
        else:
            if self.current_process.returncode == 0:
                job['status'] = 'Done'
                job['last_render_time'] = render_duration  # Store the actual render time
                # Record successful render time in history
                self.record_render_time(job['path'].name, render_duration)
                self.render_stats["total_successful_renders"] = int(self.render_stats.get("total_successful_renders", 0)) + 1
                self.render_stats["total_render_seconds"] = float(self.render_stats.get("total_render_seconds", 0.0)) + float(render_duration)
                self._record_render_log(job['path'].name, "SUCCESS", render_duration, job.get('attempts', 1))
                self.save_render_stats()
                print(f"\n{'='*80}")
                print(f"✅ COMPLETED: {job['path'].name} in {self.format_time(render_duration)}")
                print(f"{'='*80}\n")
            else:
                job['status'] = 'Error'
                if self.auto_retry:
                    # For auto-retry, move to end of queue before incrementing attempts
                    self.jobs.remove(job)
                    self.jobs.append(job)
                if self.auto_retry:
                    job['status'] = 'Ready'  # Reset status for retry
                    self.status_label.config(
                        text=f"Job {job['path'].name} will be retried (Attempt {job['attempts'] + 1})",
                        foreground="yellow")
                self.render_stats["total_errors"] = int(self.render_stats.get("total_errors", 0)) + 1
                self.render_stats["total_render_seconds"] = float(self.render_stats.get("total_render_seconds", 0.0)) + float(render_duration)
                self._record_render_log(job['path'].name, "ERROR", render_duration, job.get('attempts', 1))
                self.save_render_stats()
                print(f"\n{'='*80}")
                print(f"❌ ERROR: {job['path'].name} (Exit code: {self.current_process.returncode})")
                print(f"{'='*80}\n")
        
        self.current_process = None
        self.current_render_start = None
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
                    self._set_render_button_idle()
                    self.status_label.config(text="Batch complete", 
                                           foreground="black")
                    if self.batch_start_time:
                        self.last_batch_elapsed = time.time() - self.batch_start_time
                        self.batch_start_time = None
                    self.was_cancelled = False
                    self.update_job_list()
                    print(f"\n{'='*80}")
                    print("🎉 ALL JOBS COMPLETE")
                    print(f"{'='*80}\n")
            else:
                # When auto-retry is off, continue through jobs that can be started manually:
                # Ready jobs first, then Error/Canceled (same behavior as start_render).
                available_jobs = []
                for j in self.jobs:
                    if j['status'] == 'Ready':
                        available_jobs.append(j)
                    elif j['status'] in ['Error', 'Canceled']:
                        available_jobs.append(j)

                # Keep predictable order by attempts.
                available_jobs.sort(key=lambda x: x.get('attempts', 0))

                if available_jobs:
                    next_job = available_jobs[0]
                    if next_job['status'] in ['Error', 'Canceled']:
                        next_job['status'] = 'Ready'
                        self.update_job_list()
                    threading.Thread(target=self.render_job, 
                                   args=(next_job,), 
                                   daemon=True).start()
                else:
                    # Reset button to show render state
                    self._set_render_button_idle()
                    self.status_label.config(text="Batch complete", 
                                           foreground="black")
                    if self.batch_start_time:
                        self.last_batch_elapsed = time.time() - self.batch_start_time
                        self.batch_start_time = None
                    self.was_cancelled = False
                    self.update_job_list()
                    print(f"\n{'='*80}")
                    print("🎉 ALL JOBS COMPLETE")
                    print(f"{'='*80}\n")
    
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


