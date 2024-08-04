import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk, messagebox
import threading
import queue
import re
import webbrowser
import json

class ScrollableLabelFrame(ttk.LabelFrame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind('<Configure>', self.set_canvas_width)

    def set_canvas_width(self, event):
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_frame, width=canvas_width)

    def update_scrollregion(self):
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

class NuitkaGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Py Nuitka GUI v0.1")

        # Create menu bar
        self.create_menu_bar()

        # Center the window on the screen
        self.center_window()

        # Main frame
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollable frame for options and inputs
        self.scrollable_frame = ScrollableLabelFrame(self.main_frame, text="Options")
        self.scrollable_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Nuitka Options
        self.options = {}
        self.create_options()

        # Horizontal separator
        self.separator = ttk.Separator(self.main_frame, orient='horizontal')
        self.separator.pack(fill=tk.X, padx=10, pady=10)

        # Compile button
        self.compile_button = ttk.Button(self.main_frame, text="Compile", command=self.confirm_compilation)
        self.compile_button.pack(pady=(0, 5))

        # Display Commands button
        self.display_commands_button = ttk.Button(self.main_frame, text="Display Commands", command=self.display_commands)
        self.display_commands_button.pack(pady=(0, 5))

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Compiler Output Frame
        self.output_frame = ttk.LabelFrame(self.main_frame, text="Compiler Output:")
        self.output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.output_text = scrolledtext.ScrolledText(self.output_frame, wrap=tk.WORD, height=10)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Queue for thread-safe communication
        self.queue = queue.Queue()

        # Start the queue processor
        self.root.after(100, self.process_queue)

        # Progress tracking variables
        self.total_steps = 20
        self.current_step = 0
        self.compilation_finished = False
        
        # Compile the regex pattern once for efficiency
        self.nuitka_pattern = re.compile(r'Nuitka.*:')

    def create_menu_bar(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save Settings", command=self.save_settings)
        file_menu.add_command(label="Load Settings", command=self.load_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Help", command=self.show_help)
        help_menu.add_command(label="About", command=self.show_about)

    def save_settings(self):
        default_filename = 'project-settings.json'
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=default_filename
        )
        if file_path:
            settings = {
                "file_path": self.file_path_entry.get(),
                "output_dir": self.output_dir_entry.get(),
                "options": {opt: var.get() for opt, var in self.options.items()}
            }
            with open(file_path, 'w') as f:
                json.dump(settings, f, indent=4)
            messagebox.showinfo("Save Settings", "Settings saved successfully!")

    def load_settings(self):
        default_filename = 'project-settings.json'
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")],
            initialfile=default_filename
        )
        if file_path:
            with open(file_path, 'r') as f:
                settings = json.load(f)
            
            self.file_path_entry.delete(0, tk.END)
            self.file_path_entry.insert(0, settings.get("file_path", ""))
            
            self.output_dir_entry.delete(0, tk.END)
            self.output_dir_entry.insert(0, settings.get("output_dir", ""))
            
            for opt, value in settings.get("options", {}).items():
                if opt in self.options:
                    if isinstance(self.options[opt], tk.BooleanVar):
                        self.options[opt].set(value)
                    elif isinstance(self.options[opt], tk.StringVar):
                        self.options[opt].set(value)
            
            messagebox.showinfo("Load Settings", "Settings loaded successfully!")

    def show_help(self):
        help_window = tk.Toplevel(self.root)
        help_window.title("Help")
        help_window.geometry("500x300")
        
        help_text = """Help:

1. Select a Python file to compile using the 'Browse' button next to 'Python file'.
2. Choose an output directory for the compiled files.
3. Set the desired Nuitka options using the checkboxes and input fields.
4. Click 'Compile' to start the compilation process.
5. The progress bar will show the compilation progress.
6. You can save your current settings using File -> Save Settings.
7. Load previously saved settings using File -> Load Settings.

For more detailed information about Nuitka options, please refer to the official Nuitka documentation.
        """
        
        text_widget = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, width=60, height=20)
        text_widget.pack(expand=True, fill='both', padx=10, pady=10)
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)

    def show_about(self):
        about_window = tk.Toplevel(self.root)
        about_window.title("About")
        about_window.geometry("300x150")
        about_window.resizable(False, False)  # Make the window non-resizable

        about_frame = ttk.Frame(about_window, padding="10")
        about_frame.pack(fill=tk.BOTH, expand=True)

        about_text = """Py Nuitka GUI
Version: 0.1

Created by: non-npc"""

        label = ttk.Label(about_frame, text=about_text, justify=tk.CENTER)
        label.pack(pady=(0, 10))

        def open_url():
            webbrowser.open("https://github.com/non-npc/")

        link_button = ttk.Button(about_frame, text="https://github.com/non-npc/", 
                                 command=open_url, style="Link.TButton")
        link_button.pack()

        # Create a style for the link button
        style = ttk.Style()
        style.configure("Link.TButton", foreground="blue", borderwidth=0)
        style.map("Link.TButton", foreground=[('hover', 'darkblue')])

    def create_options(self):
        frame = self.scrollable_frame.scrollable_frame

        # Add header for Python File & Output Directory
        header = ttk.Label(frame, text="Source File & Output Directory", font=("TkDefaultFont", 12, "bold"))
        header.grid(row=0, column=0, columnspan=3, sticky="w", padx=5, pady=10)

        # Path to Python file
        self.file_path_label = ttk.Label(frame, text="Source (.py) file:")
        self.file_path_label.grid(row=1, column=0, columnspan=3, sticky="w", padx=10, pady=(5, 0))
        self.file_path_entry = ttk.Entry(frame, width=50)
        self.file_path_entry.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 5), sticky="ew")
        self.browse_button = ttk.Button(frame, text="Browse", command=self.browse_file)
        self.browse_button.grid(row=2, column=2, padx=10, pady=(0, 5))

        # Output Directory
        self.output_dir_label = ttk.Label(frame, text="Output directory:")
        self.output_dir_label.grid(row=3, column=0, columnspan=3, sticky="w", padx=10, pady=(5, 0))
        self.output_dir_entry = ttk.Entry(frame, width=50)
        self.output_dir_entry.grid(row=4, column=0, columnspan=2, padx=10, pady=(0, 5), sticky="ew")
        self.browse_output_button = ttk.Button(frame, text="Browse", command=self.browse_output_dir)
        self.browse_output_button.grid(row=4, column=2, padx=10, pady=(0, 5))

        options_data = [
            ("General Options", [
                ("--show-memory", "bool", "Output memory information"),
                ("--remove-output", "bool", "Remove output directory before compilation"),
                ("--enable-plugin=tk-inter", "bool", "Enable Tkinter plugin (recommended for Tkinter applications)"),
            ]),
            ("Basic Options", [
                ("--output-filename", "str", "Specify output filename"),
                ("--module", "bool", "Create an extension module"),
                ("--standalone", "bool", "Create a standalone executable"),
                ("--onefile", "bool", "Create a onefile executable"),
            ]),
            ("Control Options", [
                ("--jobs", "int", "Specify number of parallel jobs"),
                ("--lto", "str", "Use link time optimizations (off/auto/full)"),
                ("--python-flag", "str", "Python flags to use"),
                ("--python-debug", "bool", "Use debug version of Python"),
                ("--experimental", "str", "Use experimental features"),
            ]),
            ("Optimization Options", [
                ("--run", "bool", "Run immediately"),
                ("--debugger", "bool", "Run in debugger"),
                ("--trace-execution", "bool", "Trace execution"),
                ("--profile", "bool", "Profile execution"),
                ("--unstripped", "bool", "Keep debug info in result"),
                ("--static-libpython", "bool", "Use static link library for Python"),
            ]),
            ("Windows Specific", [
                ("--windows-console-mode", "str", "Set console mode (disable/attach/force)"),
                ("--windows-icon-from-ico", "path", "Use this icon file"),
                ("--windows-uac-admin", "bool", "Request Windows User Account Control elevation"),
                ("--windows-uac-uiaccess", "bool", "Request Windows User Account Control UI Access"),
            ]),
        ]

        row = 5  # Start after the file path and output directory inputs
        for category, options in options_data:
            # Add category heading
            heading = ttk.Label(frame, text=category, font=("TkDefaultFont", 12, "bold"))
            heading.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=10)
            row += 1

            for option, option_type, description in options:
                if option_type == "bool":
                    self.options[option] = tk.BooleanVar()
                    widget = ttk.Checkbutton(frame, text=f"{option} ({description})", variable=self.options[option])
                    widget.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
                elif option_type in ["str", "int", "path"]:
                    self.options[option] = tk.StringVar()
                    label = ttk.Label(frame, text=f"{option} ({description})")
                    label.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=(5, 0))
                    row += 1
                    if option == "--windows-console-mode":
                        combobox = ttk.Combobox(frame, textvariable=self.options[option], values=["disable", "attach", "force"])
                        combobox.grid(row=row, column=0, columnspan=2, padx=5, pady=(0, 5), sticky="ew")
                        combobox.set("disable")
                    else:
                        entry = ttk.Entry(frame, textvariable=self.options[option])
                        entry.grid(row=row, column=0, columnspan=2, padx=5, pady=(0, 5), sticky="ew")
                    if option_type == "path":
                        browse_button = ttk.Button(frame, text="Browse", command=lambda opt=option: self.browse_option(opt))
                        browse_button.grid(row=row, column=2, padx=5, pady=(0, 5))
                row += 1

        # Update scrollregion after adding all widgets
        self.scrollable_frame.update_scrollregion()

    def center_window(self):
        # Set the window size
        window_width = 600
        window_height = 600

        # Get the screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Find the center point
        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)

        # Set the position of the window to the center of the screen
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Python Files", "*.py")])
        if file_path:
            normalized_path = os.path.normpath(file_path)
            self.file_path_entry.delete(0, tk.END)
            self.file_path_entry.insert(0, normalized_path)

    def browse_output_dir(self):
        output_dir = filedialog.askdirectory()
        if output_dir:
            normalized_path = os.path.normpath(output_dir)
            self.output_dir_entry.delete(0, tk.END)
            self.output_dir_entry.insert(0, normalized_path)

    def browse_option(self, opt):
        file_path = filedialog.askopenfilename()
        if file_path:
            normalized_path = os.path.normpath(file_path)
            self.options[opt].set(normalized_path)

    def confirm_compilation(self):
        file_path = os.path.abspath(os.path.normpath(self.file_path_entry.get().strip()))
        output_dir = os.path.abspath(os.path.normpath(self.output_dir_entry.get().strip()))

        if not os.path.isfile(file_path):
            messagebox.showerror("Error", "Invalid Python file path.")
            return

        if not os.path.isdir(output_dir):
            messagebox.showerror("Error", "Invalid output directory.")
            return

        command = [sys.executable, "-m", "nuitka"]

        for opt, var in self.options.items():
            if isinstance(var, tk.BooleanVar) and var.get():
                command.append(opt)
            elif isinstance(var, tk.StringVar) and var.get():
                value = os.path.abspath(os.path.normpath(var.get().strip())) if opt.endswith(("-from-ico", "-dir")) else var.get()
                command.append(f"{opt}={value}")

        command.append(f"--output-dir={output_dir}")
        command.append(file_path)

        command_str = ' '.join(command)
        self.command_str = command_str
        
        confirm = messagebox.askokcancel("Confirm Compilation", 
                                         f"Do you want to execute the following command?\n\n{command_str}\n\n"
                                         "Click OK to proceed or Cancel to abort.")
        
        if confirm:
            self.start_compilation(command)
        else:
            self.output_text.config(state=tk.NORMAL)
            self.output_text.insert(tk.END, "Compilation cancelled by user.\n")
            self.output_text.config(state=tk.DISABLED)

    def display_commands(self):
        file_path = os.path.abspath(os.path.normpath(self.file_path_entry.get().strip()))
        output_dir = os.path.abspath(os.path.normpath(self.output_dir_entry.get().strip()))

        if not os.path.isfile(file_path):
            messagebox.showerror("Error", "Invalid Python file path.")
            return

        if not os.path.isdir(output_dir):
            messagebox.showerror("Error", "Invalid output directory.")
            return

        command = [sys.executable, "-m", "nuitka"]

        for opt, var in self.options.items():
            if isinstance(var, tk.BooleanVar) and var.get():
                command.append(opt)
            elif isinstance(var, tk.StringVar) and var.get():
                value = os.path.abspath(os.path.normpath(var.get().strip())) if opt.endswith(("-from-ico", "-dir")) else var.get()
                command.append(f"{opt}={value}")

        command.append(f"--output-dir={output_dir}")
        command.append(file_path)

        command_str = ' '.join(command)
        if not command_str:
            messagebox.showinfo("Info", "No command string available.")
            return
        
        popup = tk.Toplevel(self.root)
        popup.title("Command String")
        popup.geometry("500x200")
        
        text_box = scrolledtext.ScrolledText(popup, wrap=tk.WORD, height=5)
        text_box.pack(expand=True, fill='both', padx=10, pady=10)
        text_box.insert(tk.END, command_str)
        text_box.config(state=tk.NORMAL)
        
        def copy_to_clipboard():
            self.root.clipboard_clear()
            self.root.clipboard_append(command_str)
            self.root.update()  # now it stays on the clipboard after the window is closed
            messagebox.showinfo("Copied", "Command string copied to clipboard.")
        
        copy_button = ttk.Button(popup, text="Copy to Clipboard", command=copy_to_clipboard)
        copy_button.pack(pady=10)
        
    def start_compilation(self, command):
        self.compile_button.config(state=tk.DISABLED, text="Compiling please wait...")
        self.clear_output()
        self.reset_compilation_state()
        threading.Thread(target=self.compile, args=(command,), daemon=True).start()
        self.root.after(100, self.process_queue)  # Start processing the queue immediately

    def clear_output(self):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)

    def reset_compilation_state(self):
        self.progress_var.set(0)
        self.total_steps = 20
        self.current_step = 0
        self.compilation_finished = False
        
    def compile(self, command):
        # Clear the queue before starting a new compilation
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break
        
        self.queue.put(f"Executing command: {' '.join(command)}\n\n")

        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
            
            for line in process.stdout:
                self.queue.put(line)
                self.update_progress(line)
            
            process.wait()
            
            if process.returncode == 0:
                self.queue.put("Compilation successful.\n")
                self.update_progress("Compilation successful.")
            else:
                self.queue.put("Compilation failed.\n")
                self.update_progress("Compilation failed.")
        except FileNotFoundError:
            self.queue.put("Error: Python or Nuitka not found. Please ensure they are installed and in your system PATH.\n")
        
        self.queue.put(None)  # Signal that compilation is complete

    def update_progress(self, line):
        if self.nuitka_pattern.search(line):
            self.current_step += 1
            progress = min(self.current_step, self.total_steps)
            self.progress_var.set((progress / self.total_steps) * 100)
        elif 'Compilation successful.' in line:
            self.progress_var.set(100)
            self.compilation_finished = True
        
        # Update the progress bar
        self.root.update_idletasks()

    def process_queue(self):
        try:
            while True:
                message = self.queue.get_nowait()
                if message is None:  # Compilation is complete
                    self.compile_button.config(state=tk.NORMAL, text="Compile")
                    break
                self.output_text.config(state=tk.NORMAL)
                self.output_text.insert(tk.END, message)
                self.output_text.see(tk.END)
                self.output_text.config(state=tk.DISABLED)
                self.output_text.update_idletasks()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)  # Always schedule the next call

if __name__ == "__main__":
    root = tk.Tk()
    app = NuitkaGUI(root)
    root.mainloop()