
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess
import threading
import sys
import os
import time
from queue import Queue, Empty
import tempfile
import json

class CodeEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Young Coder's Python Editor")
        self.root.geometry("1000x800")
        self.root.configure(bg='grey')
        self.root.option_add("*TCombobox*Listbox*Background", "black")    
        self.current_file = None
        self.process = None
        self.input_queue = Queue()
        self.is_running = False
        self.execution_history = []
        self.code_templates = {
            "Hello World": 'print("Hello, World!")',
            "My Name": 'print("Sheshagiri Rao")'  
        }
        
        self.setup_ui()
        self.setup_bindings()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.create_toolbar(main_frame)
        
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=2)

        self.setup_code_editor(left_frame)
 
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.setup_terminal_tab()
        self.setup_templates_tab()
        self.setup_history_tab()
        self.setup_help_tab()
        self.create_status_bar(main_frame)
        
    def create_toolbar(self, parent):
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(toolbar, text="New", command=self.new_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Open", command=self.open_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Save", command=self.save_file).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="▶️ Run", command=self.run_code, 
                  style="Accent.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="⏹️ Stop", command=self.stop_execution).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Clear Terminal", command=self.clear_terminal).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="Format Code", command=self.format_code).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Check Syntax", command=self.check_syntax).pack(side=tk.LEFT, padx=2)
        
    def setup_code_editor(self, parent):
        editor_frame = ttk.Frame(parent)
        editor_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(editor_frame, text="Code Editor", font=("Arial", 12, "bold")).pack(anchor=tk.W)
        text_frame = ttk.Frame(editor_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        self.line_numbers = tk.Text(text_frame, width=4, padx=3, takefocus=0,
                                   border=0, state='disabled', wrap='none',
                                   bg='#3c3c3c', fg='#888888', font=("Consolas", 11))
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        self.code_editor = scrolledtext.ScrolledText(
            text_frame, wrap=tk.NONE, font=("Consolas", 11),
            bg='#1e1e1e', fg='#dcdcdc', insertbackground='white',
            selectbackground='#264f78', selectforeground='white',
            undo=True, maxundo=50
        )
        self.code_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        starter_code = """# Welcome to My Python Editor! 
"""
        self.code_editor.insert(tk.END, starter_code)
        self.code_editor.bind('<KeyRelease>', self.update_line_numbers)
        self.code_editor.bind('<Button-1>', self.update_line_numbers)
        self.code_editor.bind('<MouseWheel>', self.sync_scroll)
        
        self.update_line_numbers()
        
    def setup_terminal_tab(self):
        terminal_frame = ttk.Frame(self.notebook)
        self.notebook.add(terminal_frame, text="🖥️ Terminal")

        ttk.Label(terminal_frame, text="Output:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        self.terminal_output = scrolledtext.ScrolledText(
            terminal_frame, height=15, font=("Consolas", 10),
            bg='#0c0c0c', fg='#00ff00', state=tk.DISABLED
        )
        self.terminal_output.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        input_frame = ttk.Frame(terminal_frame)
        input_frame.pack(fill=tk.X)
        
        ttk.Label(input_frame, text="Input:").pack(side=tk.LEFT)
        self.input_entry = ttk.Entry(input_frame, font=("Consolas", 10))
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.input_entry.bind('<Return>', self.send_input)
        
        ttk.Button(input_frame, text="Send", command=self.send_input).pack(side=tk.RIGHT, padx=(5, 0))
        
    def setup_templates_tab(self):
        templates_frame = ttk.Frame(self.notebook)
        self.notebook.add(templates_frame, text="📚 Templates")
        
        ttk.Label(templates_frame, text="Code Templates:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        for name, code in self.code_templates.items():
            btn = ttk.Button(templates_frame, text=name, 
                           command=lambda c=code: self.load_template(c))
            btn.pack(fill=tk.X, pady=1)
            
    def setup_history_tab(self):
        history_frame = ttk.Frame(self.notebook)
        self.notebook.add(history_frame, text="History")
        
        ttk.Label(history_frame, text="Execution History:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        self.history_listbox = tk.Listbox(history_frame, font=("Consolas", 9))
        self.history_listbox.pack(fill=tk.BOTH, expand=True)
        self.history_listbox.bind('<Double-Button-1>', self.load_from_history)
        
    def setup_help_tab(self):
        help_frame = ttk.Frame(self.notebook)
        self.notebook.add(help_frame, text=" Help")
        
        help_text = """🎯 Quick Start Guide:

1. 📝 Write Python code in the editor
2. ▶️ Click Run to execute
3. 💬 Use the Input box for user input
4. 📚 Try code templates
5. 🔍 Check syntax before running

Learning Tips:
• Start with templates
• Read error messages carefully
• Use print() to debug
• Experiment with different inputs

 Debugging Help:
• Check for typos
• Verify indentation
• Use a syntax checker
• Read terminal output
"""
        
        help_display = scrolledtext.ScrolledText(help_frame, wrap=tk.WORD, 
                                                font=("Arial", 9), height=20)
        help_display.pack(fill=tk.BOTH, expand=True)
        help_display.insert(tk.END, help_text)
        help_display.config(state=tk.DISABLED)
        
    def create_status_bar(self, parent):
        self.status_bar = ttk.Label(parent, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def setup_bindings(self):
        self.root.bind('<Control-n>', lambda e: self.new_file())
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.root.bind('<F5>', lambda e: self.run_code())
        self.root.bind('<Control-slash>', lambda e: self.toggle_comment())
        
    def update_line_numbers(self, event=None):
        self.line_numbers.config(state='normal')
        self.line_numbers.delete('1.0', tk.END)
        
        lines = int(self.code_editor.index('end-1c').split('.')[0])
        line_numbers_text = '\n'.join(str(i) for i in range(1, lines + 1))
        self.line_numbers.insert('1.0', line_numbers_text)
        self.line_numbers.config(state='disabled')
        
    def sync_scroll(self, event):
        self.line_numbers.yview_moveto(self.code_editor.yview()[0])
        
    def new_file(self):
        if messagebox.askokcancel("New File", "Create a new file? Unsaved changes will be lost."):
            self.code_editor.delete('1.0', tk.END)
            self.current_file = None
            self.status_bar.config(text="New file created")
            
    def open_file(self):
        file_path = filedialog.askopenfilename(
            title="Open Python File",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    self.code_editor.delete('1.0', tk.END)
                    self.code_editor.insert('1.0', content)
                    self.current_file = file_path
                    self.status_bar.config(text=f"Opened: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {e}")
                
    def save_file(self):
        if self.current_file:
            try:
                content = self.code_editor.get('1.0', tk.END + '-1c')
                with open(self.current_file, 'w', encoding='utf-8') as file:
                    file.write(content)
                self.status_bar.config(text=f"Saved: {os.path.basename(self.current_file)}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {e}")
        else:
            self.save_file_as()
            
    def save_file_as(self):
        file_path = filedialog.asksaveasfilename(
            title="Save Python File",
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if file_path:
            self.current_file = file_path
            self.save_file()
            
    def run_code(self):
        if self.is_running:
            messagebox.showwarning("Already Running", "Code is already running!")
            return
            
        code = self.code_editor.get('1.0', tk.END + '-1c').strip()
        if not code:
            messagebox.showwarning("No Code", "Please write some code first!")
            return
        timestamp = time.strftime("%H:%M:%S")
        self.execution_history.append(f"[{timestamp}] Execution")
        self.history_listbox.insert(tk.END, f"[{timestamp}] Execution")
        self.terminal_output.config(state=tk.NORMAL)
        self.terminal_output.delete('1.0', tk.END)
        self.terminal_output.insert(tk.END, f" Running code at {timestamp}...\n\n")
        self.terminal_output.config(state=tk.DISABLED)
        self.is_running = True
        self.status_bar.config(text="Running...")
        threading.Thread(target=self.execute_code, args=(code,), daemon=True).start()
        
    def execute_code(self, code):
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name
            self.process = subprocess.Popen(
                [sys.executable, temp_file_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            while True:
                output = self.process.stdout.readline()
                if output == '' and self.process.poll() is not None:
                    break
                if output:
                    self.root.after(0, self.update_terminal, output)
                try:
                    if not self.input_queue.empty():
                        user_input = self.input_queue.get_nowait()
                        self.process.stdin.write(user_input + '\n')
                        self.process.stdin.flush()
                except Empty:
                    pass
            return_code = self.process.poll()
            os.unlink(temp_file_path)
            
            self.root.after(0, self.execution_finished, return_code)
            
        except Exception as e:
            self.root.after(0, self.update_terminal, f" Error: {str(e)}\n")
            self.root.after(0, self.execution_finished, -1)
            
    def update_terminal(self, text):
        self.terminal_output.config(state=tk.NORMAL)
        self.terminal_output.insert(tk.END, text)
        self.terminal_output.see(tk.END)
        self.terminal_output.config(state=tk.DISABLED)
        
    def execution_finished(self, return_code):
        self.is_running = False
        self.process = None
        
        if return_code == 0:
            self.update_terminal("\n Program finished successfully!\n")
            self.status_bar.config(text="Execution completed")
        else:
            self.update_terminal(f"\n Program finished with errors (code: {return_code})\n")
            self.status_bar.config(text="Execution failed")
            
    def send_input(self, event=None):
        if not self.is_running:
            messagebox.showwarning("Not Running", "No program is currently running!")
            return
            
        user_input = self.input_entry.get()
        if user_input:
            self.input_queue.put(user_input)
            self.update_terminal(f"> {user_input}\n")
            self.input_entry.delete(0, tk.END)
            
    def stop_execution(self):
        if self.process:
            self.process.terminate()
            self.update_terminal("\nExecution stopped by user\n")
            self.execution_finished(-1)
        else:
            messagebox.showinfo("Not Running", "No program is currently running!")
            
    def clear_terminal(self):
        self.terminal_output.config(state=tk.NORMAL)
        self.terminal_output.delete('1.0', tk.END)
        self.terminal_output.config(state=tk.DISABLED)
        
    def load_template(self, template_code):
        if messagebox.askokcancel("Load Template", "Load this template? Current code will be replaced."):
            self.code_editor.delete('1.0', tk.END)
            self.code_editor.insert('1.0', template_code)
            self.update_line_numbers()
            
    def load_from_history(self, event=None):
        messagebox.showinfo("History", "Double-click functionality coming soon!")
        
    def check_syntax(self):
        code = self.code_editor.get('1.0', tk.END + '-1c')
        try:
            compile(code, '<string>', 'exec')
            messagebox.showinfo("Syntax Check", "Syntax is correct!")
        except SyntaxError as e:
            messagebox.showerror("Syntax Error", f"Line {e.lineno}: {e.msg}")
            
    def format_code(self):
        code = self.code_editor.get('1.0', tk.END + '-1c')
        lines = code.split('\n')
        formatted_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped:
                if any(stripped.startswith(keyword) for keyword in ['def ', 'class ', 'if ', 'for ', 'while ', 'try:', 'except', 'else:', 'elif ']):
                    formatted_lines.append(stripped)
                elif stripped.startswith(('return', 'break', 'continue', 'pass', 'print(', 'input(')):
                    formatted_lines.append('    ' + stripped if not line.startswith('    ') else stripped)
                else:
                    formatted_lines.append(stripped)
            else:
                formatted_lines.append('')
                
        self.code_editor.delete('1.0', tk.END)
        self.code_editor.insert('1.0', '\n'.join(formatted_lines))
        self.update_line_numbers()
        messagebox.showinfo("Format Code", " Code formatted!")
        
    def toggle_comment(self):
        try:
            current_line = self.code_editor.index(tk.INSERT).split('.')[0]
            line_start = f"{current_line}.0"
            line_end = f"{current_line}.end"
            line_content = self.code_editor.get(line_start, line_end)
            
            if line_content.strip().startswith('#'):
                new_content = line_content.replace('#', '', 1).lstrip()
            else:
                new_content = '# ' + line_content
                
            self.code_editor.delete(line_start, line_end)
            self.code_editor.insert(line_start, new_content)
        except:
            pass

def main():
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use('clam')
    style.configure('Accent.TButton', background='#0078d4', foreground='white')
    app = CodeEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()

