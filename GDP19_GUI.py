import tkinter as tk # old formatting
from tkinter import ttk # new formatting
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg #integrates matplotlib with tk
import tkinter.font as tkFont
from tkinter.messagebox import showerror
import serial
import serial.tools.list_ports
import time
import threading # required for csv logging

'''
GDP 19 Python Script

The following code creates and runs the GUI for the creation of gait cycle
routines for the testing of the rig created by GDP 19. The GUI provides a user-
friendly interface for intuitive creation of test programs without requiring 
substantial coding knowledge. This code is to be run with the ARDUINO scripts 
in the repository which are communicated to with serial communication.

NOTES:
 -  Created by Travis Richards, tr2g21.
 -  TKinter package used for GUI creation.
 -  Spyder (Anaconda) IDE used.
 -  Serial communication to ARDUINO scripts.
 -  <movement, duration> formatting of communication.
 -  115200 baude rate used.
    
FUTURE IMPROVEMENTS:
 -  Live plotting of force feedback from load cell - can be implemented with
    threading - I did not have the time.
 -  Scroll/button to change the scale of the x-axis on the graphs.
 -  Treeview instead of listbox for better organisation of the movement cycle 
    list.
 -  Theming using TKinter style packages.
 -  Timing mismatch between Python and ARDUINO
 
REFERENCES:
 -  https://tkdocs.com/tutorial/index.html
 -  https://matplotlib.org/stable/api/matplotlib_configuration_api.html
 -  https://numpy.org/

Tutorials followed:
 -  Corey Schafer, Python Tkinter Tutorial (Part 1): Getting Started, Elements, 
    Layouts, and Events - https://youtu.be/epDKamC-V-8?si=H2ugy1IKypD8D9ZT
 -  Corey Schafer, Python Tkinter Tutorial (Part 2): Using Classes for 
    Functionality and Organization - https://youtu.be/X5yyKZpZ4vU?si=5V5Da_KVWt5fbG7B
 -  Code First with Hala, Python Dashboard with Tkinter and Matplotlib tutorial 
    [for beginners] - https://youtu.be/2JjQIh-sgHU?si=1uiUNsOUVxNAa7Fv
'''
#%% Main loop

def main():
    app = Application()
    default_font = tkFont.nametofont("TkDefaultFont")
    default_font.configure(size=11)
    # Application size constraints
    app.geometry("1600x1000")
    app.minsize(1600,1000)
    
    # Theming for future implementation
    # style = ttk.Style(app)
    # app.tk.call('source', r'C:\Users\tr2g21\Downloads\ttk-Breeze-master\ttk-Breeze-master\Breeze.tcl')
    # style.theme_use('Breeze')
    
    app.mainloop()
    
#%% Setup all frames

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GDP 19 - Canine Elbow Joint Simulator")
        
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=3)

        self.rowconfigure(0, weight=0) 
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=0)

        # Frame dependencies
        Welcome = WelcomeFrame(self)
        Add = AddFrame(self)
        Plot = PlotFrame(self, Welcome, Add)
        Run = ArduinoRunFrame(self, Welcome, Add, Plot)
        Add.set_plot_frame(Plot)
        
        # Layout
        Welcome.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        Add.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        Run.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        Plot.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=5, pady=5)
        
        self.run_frame = Run
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def on_close(self):
        if hasattr(self.run_frame, "arduino") and self.run_frame.arduino.is_open:
            self.run_frame.arduino.close()
        self.destroy()
        
#%% Welcome Frame - Title, weight spinbox

class WelcomeFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=0)
        self.columnconfigure(3, weight=0)

        self.welcome = ttk.Label(self, text="Welcome", anchor="center",font=("TKDefaultFont",18, "bold")) # center aligned
        self.welcome.grid(row=0, column=0, columnspan = 4, sticky="ew") 
        
        self.weight = ttk.Label(self, text="Weight (kg) :")        
        self.weight.grid(row=1, column=0, sticky="w")
        
        self.var = tk.DoubleVar(value=36) # default value = 36 kg
        self.spinbox = ttk.Spinbox(self, from_=20, to =50, width = 5, textvariable = self.var)
        self.spinbox.grid(row=1, column=1, sticky="w")
        
        self.com_lbl = ttk.Label(self, text="COM:")
        self.com_lbl.grid(row=1, column=3)
        
        self.com = ttk.Combobox(self, values=self.serial_ports())
        self.com.grid(row=1, column=4, sticky="e")
        self.com.bind('<<ComboboxSelected>>', self.on_select)
        
    def serial_ports(self):
        ports = serial.tools.list_ports.comports()
        
        # Create mapping: "COM4 - Arduino Uno (COM4)" → "COM4"
        self.port_map = {
            f"{p.device} - {p.description}": p.device
            for p in ports
        }
        
        return list(self.port_map.keys())
    
    def on_select(self, event=None):
        selected_text = self.com.get()
        self.comport = self.port_map.get(selected_text)
    
#%% Add Frame - Edit movement cycle routine (add, remove, reset, presets), movement cycle listbox

class AddFrame(ttk.Frame):    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.movements = [] # create blank array for serial communication
        self.durations = []
        self.popup = None # initialise toplevels for error handling
        self.popup_presets = None
        
        self.i = 1 # movement cycle number

        for c in range(4):
            self.columnconfigure(c, weight=0)
          
        self.rowconfigure(0, weight=0)    
        self.rowconfigure(1, weight=1)

        self.btn_add = ttk.Button(self, text="Add", padding=(0,10),command = self.open_top)
        self.btn_add.grid(row=0, column=0, sticky="ew", pady=2)
        
        self.btn_rem = ttk.Button(self, text="Remove", padding=(0,10), command = self.remove_last)
        self.btn_rem.grid(row=0, column=1, sticky="ew", pady=2)
        
        self.btn_res = ttk.Button(self, text="Reset", padding=(0,10), command = self.clear_list)
        self.btn_res.grid(row=0, column=2, sticky="ew", pady=2)
        
        self.btn_pres = ttk.Button(self, text="Preset Programs", padding=(0,10), command = self.presets)
        self.btn_pres.grid(row=0, column=3, sticky="ew", pady=2)

        self.text_list = tk.Listbox(self) # Treeview may be more appropriate for future iterations
        self.text_list.grid(row=1, column=0, columnspan = 4, sticky="nsew")
        self.text_list.insert(tk.END, f"{0:<5} - {'Initialise':<10} - {60:>5} seconds")
        
    def open_top(self, event=None): # add movement cycle window
        self.popup = tk.Toplevel(self)
        self.popup.minsize(240, 144)
        self.popup.maxsize(240, 144)
        
        for c in range(2):
            self.popup.columnconfigure(c, weight = 1)
        for c in range(3):
            self.popup.rowconfigure(c, weight = 1)
 
        self.popup.title("Add Movement")
        
        self.lbl_dur = ttk.Label(self.popup, text = "Duration (s) :", anchor="center")
        self.lbl_dur.grid(row = 0, column = 0, sticky = "e")
        
        self.var2 = tk.DoubleVar(value=10) # default value = 10 seconds
        self.sbox_dur = ttk.Spinbox(self.popup, from_=0, to =120, width = 10, textvariable = self.var2)
        self.sbox_dur.grid(row = 0, column = 1)

        
        self.btn_stand = ttk.Button(self.popup, text = "Stand", padding=(10,10), command = self.add_stand)
        self.btn_stand.grid(row = 1, column = 0, sticky="nse", pady = 2)
        
        self.btn_walk = ttk.Button(self.popup, text = "Walk", padding=(10,10), command = self.add_walk)
        self.btn_walk.grid(row = 1, column = 1, sticky="nsw", pady = 2)
        
        self.btn_run = ttk.Button(self.popup, text = "Trot", padding=(10,10), command = self.add_run)
        self.btn_run.grid(row = 2, column = 0, sticky="nse", pady = 2)
        
        self.btn_custom = ttk.Button(self.popup, text = "Off", padding=(10,10), command = self.add_off)
        self.btn_custom.grid(row = 2, column = 1, sticky="nsw", pady = 2)
        
    def remove_last(self):
        if self.text_list.index("end") == 1: # don't remove initialise sequence
            return
        else:
            self.text_list.delete(tk.END)
            self.i -= 1
            self.movements.pop()
            self.durations.pop()
            self.plot_frame.update_plot() # edits the graphs accordingly
            
    def clear_list(self):
        self.text_list.delete(1, tk.END)
        self.i = 1
        self.movements = []
        self.durations = []
        self.plot_frame.update_plot()
        
    def add_stand(self, duration=None):
        if duration is None:
            try: # error handling to only except numbers
                duration = abs(int(self.sbox_dur.get())) # force positive number
            except:
                duration = 10
                showerror('Error', 'Invalid duration - defaulting to 10s')
                self.popup.lift() # bring add back to front
            
        self.text_list.insert(tk.END, f"{self.i:<5} - {'Stand':<9} - {duration:>5} seconds")
        self.i += 1
        self.movements += [1] # defined in ARDUINO
        self.durations += [int(duration)]
        self.plot_frame.update_plot()
        
    def add_walk(self, duration=None):
        if duration is None:
            try:
                duration = int(self.sbox_dur.get())
            except:
                duration = 10
                showerror('Error', 'Invalid duration - defaulting to 10s')
                self.popup.lift()
            
        self.text_list.insert(tk.END, f"{self.i:<5} - {'Walk':<9} - {duration:>5} seconds")
        self.i += 1
        self.movements += [2] # defined in ARDUINO
        self.durations += [int(duration)]
        self.plot_frame.update_plot()
            
    def add_run(self, duration=None):
        if duration is None:
            try:
                duration = int(self.sbox_dur.get())
            except:
                duration = 10
                showerror('Error', 'Invalid duration - defaulting to 10s')
                self.popup.lift()
            
        self.text_list.insert(tk.END, f"{self.i:<5} - {'Trot':<10} - {duration:>5} seconds")
        self.i += 1
        self.movements += [3] # defined in ARDUINO
        self.durations += [int(duration)]
        self.plot_frame.update_plot()
        
    def add_off(self, duration=None):
        if duration is None:
            try:
                duration = int(self.sbox_dur.get())
            except:
                duration = 10
                showerror('Error', 'Invalid duration - defaulting to 10s')
                self.popup.lift()
            
        self.text_list.insert(tk.END, f"{self.i:<5} - {'Off':<11} - {duration:>5} seconds")
        self.i += 1
        self.movements += [0] # defined in ARDUINO
        self.durations += [int(duration)]
        self.plot_frame.update_plot()
        
    def set_plot_frame(self, plot_frame):
        self.plot_frame = plot_frame
        
    def disable(self): # disable movement cycle editing when ARDUINO connected
        self.btn_add["state"] = "disabled"
        self.btn_rem["state"] = "disabled"
        self.btn_res["state"] = "disabled"
        self.btn_pres["state"] = "disabled"
        
    def enable(self): # enable movement cycle editing when ARDUINO disconnected
        self.btn_add["state"] = "normal"
        self.btn_rem["state"] = "normal"
        self.btn_res["state"] = "normal"
        self.btn_pres["state"] = "normal"
        
    def presets(self):
        self.popup_presets = tk.Toplevel(self)
        self.popup_presets.minsize(240, 240)
        self.popup_presets.maxsize(240, 240)
        
        self.popup_presets.columnconfigure(0, weight = 0)
        self.popup_presets.columnconfigure(1, weight = 1)
        self.popup_presets.rowconfigure(0, weight = 0)
        self.popup_presets.rowconfigure(1, weight = 1)
        self.popup_presets.rowconfigure(2, weight = 0)
 
        self.popup_presets.title("Preset Programs")
        
        self.lbl_pro = ttk.Label(self.popup_presets, text = "Program :")
        self.lbl_pro.grid(row = 0, column = 0, sticky = "e")
        
        self.var_presets = tk.StringVar() # preassign combobox default
        self.cbox_presets = ttk.Combobox(self.popup_presets, textvariable = self.var_presets)
        self.cbox_presets.grid(row = 0, column = 1)
        
        self.cbox_presets['values'] = ('Program 1 - SWOR',
                                       'Program 2 - SOSO',
                                       'Program 3 - WOWO',
                                       'Program 4 - TOTO')
        
        self.cbox_presets.bind("<<ComboboxSelected>>", self.update_com)
        
        self.lbl_pre = ttk.Label(self.popup_presets, text = "Select a preset program from the dropdown above.", wraplength = 200)
        self.lbl_pre.grid(row = 1, column = 0, columnspan = 2)
        
        self.btn_addpre = ttk.Button(self.popup_presets, text = "Add Program", padding=(2,2), command = self.add_presets)
        self.btn_addpre.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
    def update_com(self, event=None):
        value = self.var_presets.get()
        if value == 'Program 1 - SWOR':
            self.lbl_pre.configure(text = "Program 1 selected\n\nStand - 20 seconds\nWalk - 20 seconds\nOff - 10 seconds\nRun - 10 seconds")
        if value == 'Program 2 - SOSO':
            self.lbl_pre.configure(text = "Program 2 selected\n\nStand - 30 seconds\nOff - 30 seconds\nStand - 30 seconds\nOff - 30 seconds")
        if value == 'Program 3 - WOWO':
            self.lbl_pre.configure(text = "Program 3 selected\n\nWalk - 30 seconds\nOff - 30 seconds\nWalk - 30 seconds\nOff - 30 seconds")
        if value == 'Program 4 - TOTO':
            self.lbl_pre.configure(text = "Program 4 selected\n\nTrot - 10 seconds\nOff - 10 seconds\nTrot - 10 seconds\nOff - 10 seconds")
            
    def add_presets(self, event=None):
        value = self.var_presets.get()
        if value == 'Program 1 - SWOR':
            self.add_stand(duration=20)
            self.add_walk(duration=20)
            self.add_off(duration=10)
            self.add_run(duration=10)
        if value == 'Program 2 - SOSO':
            self.add_stand(duration=30)
            self.add_off(duration=30)
            self.add_stand(duration=30)
            self.add_off(duration=30)
        if value == 'Program 3 - WOWO':
            self.add_walk(duration=30)
            self.add_off(duration=30)
            self.add_walk(duration=30)
            self.add_walk(duration=30)
        if value == 'Program 4 - TOTO':
            self.add_run(duration=10)
            self.add_off(duration=10)
            self.add_run(duration=10)
            self.add_off(duration=10) 
#%% Run Frame - verify ARDUINO connection and start/pause/stop routine

class ArduinoRunFrame(ttk.Frame):
    def __init__(self, parent, Welcome, Add, Plot):
        super().__init__(parent)
        
        # dependencies
        self.Welcome = Welcome
        self.Add = Add
        self.Plot = Plot
        
        # csv data
        self.log_data = []
        self.reading = False
        self.paused = False # keep separate for accuracy
        
        for c in range(7):
            self.columnconfigure(c, weight=1)
            
        self.style = ttk.Style()
        self.style.configure('Run.TButton', font=("TkDefaultFont", 11, "bold"), foreground='#079D68') # colour editing for ttk
        self.style.configure('Pause.TButton', font=("TkDefaultFont", 11, "bold"), foreground='#ffbf00')
        self.style.configure('Stop.TButton', font=("TkDefaultFont", 11, "bold"), foreground='#ff2400')

        self.btn_conn = ttk.Button(self, text="Connect ARDUINO", padding=(0,10) , command = self.connect)
        self.btn_conn.grid(row=0, column=0, sticky="ew", pady=2)
        
        self.btn_disc = ttk.Button(self, text="Disconnect ARDUINO", padding=(0,10), state="disabled", command = self.disconnect)
        self.btn_disc.grid(row=0, column=1, sticky="ew", pady=2)
        
        self.btn_run = ttk.Button(self, text="Run", padding=(0,10), style='Run.TButton', state="disabled", command = self.start_run) 
        self.btn_run.grid(row=0, column=2, sticky="ew", pady=2)
        
        self.btn_pause = ttk.Button(self, text="Pause", padding=(0,10), style='Pause.TButton', state="disabled", command = self.pause_run)
        self.btn_pause.grid(row=0, column=3, sticky="ew", pady=2)
        
        self.btn_stop = ttk.Button(self, text="Stop", padding=(0,10), style='Stop.TButton', state="disabled", command = self.stop_run)
        self.btn_stop.grid(row=0, column=4, sticky="ew", pady=2)
        
        self.btn_skipf = ttk.Button(self, text="Skip Forward", padding=(0,10), state="disabled", command = self.skip_forward)
        self.btn_skipf.grid(row=0, column=5, sticky="ew", pady=2)
        
        self.btn_skipb = ttk.Button(self, text="Save CSV", padding=(0,10), state="disabled", command = self.save_csv)
        self.btn_skipb.grid(row=0, column=6, sticky="ew", pady=2)
    
    # movement cycle playback
    def start_run(self):
        if self.Plot.running:
            return
    
        if self.Plot.x_data is None or len(self.Plot.x_data) == 0:
            return
        
        self.Plot.current_time = 0
        self.Plot.running = True
        self.Plot.paused = False
        
        self.btn_pause.config(text="Pause")
        self.btn_run["state"] = "disabled"
        
        self.arduino.write(b"<R>")
        
        self.read_serial()
        
        self.Plot.start_anim()
        
    def pause_run(self):
        if not self.Plot.running:
            return
    
        # toggle pause state
        self.Plot.paused = not self.Plot.paused
    
        if self.Plot.paused:
            self.btn_pause.config(text="Resume")
        else:
            self.Plot.start_time_ref = time.perf_counter() - self.Plot.current_time
            self.Plot.animate()
            self.btn_pause.config(text="Pause")
        
        self.arduino.write(b"<P>")
    
    def stop_run(self):
        self.Plot.running = False
        self.Plot.paused = False
        self.reading = False
        self.Plot.current_time = 0
        
        # reset dots to start (or hide them)
        if self.Plot.x_data is not None and len(self.Plot.x_data) > 0:
            self.Plot.force_dot.set_data([], [])
            self.Plot.rot_dot.set_data([], [])
        
        # reset view window
        self.Plot.ax_force.set_xlim(0, self.Plot.window)
        self.Plot.ax_rotation.set_xlim(0, self.Plot.window)
        
        self.Plot.canvas.draw_idle()
        
        # reset button text
        self.btn_pause.config(text="Pause")
        self.btn_run["state"]="normal"
        
        self.arduino.write(b"<S>")
        
    def disconnect(self):
        self.stop_run()
        self.Add.enable()
        self.RunDisable()
        self.btn_conn["state"] = "normal"
        self.btn_disc["state"] = "disabled"
        
        if hasattr(self, "arduino") and self.arduino.is_open:
            self.arduino.close()
            self.arduino.write(b"<S>")
        
    def connect(self):
        
        try:
            self.arduino = serial.Serial(port=self.Welcome.comport, baudrate=115200, timeout = 1)
        except:
            showerror('Error', 'Invalid COM port selected')
            return
            
        self.Add.disable()
        self.RunEnable()
        self.Plot.update_plot()
        
        # close top levels if they exist:
        if self.Add.popup and self.Add.popup.winfo_exists():
            self.Add.popup.destroy()
        if self.Add.popup_presets and self.Add.popup_presets.winfo_exists():
            self.Add.popup_presets.destroy()
            
        self.btn_disc["state"] = "normal"
        self.btn_conn["state"] = "disabled"
        
        time.sleep(2)
        self.send_program()
        
    def RunDisable(self):
        self.btn_run["state"] = "disabled"
        self.btn_pause["state"] = "disabled"
        self.btn_stop["state"] = "disabled"
        self.btn_skipf["state"] = "disabled"
        self.btn_skipb["state"] = "disabled"
        
    def RunEnable(self):
        self.btn_run["state"] = "normal"
        self.btn_pause["state"] = "normal"
        self.btn_stop["state"] = "normal"
        self.btn_skipf["state"] = "normal"
        self.btn_skipb["state"] = "normal"
        
    def skip_forward(self):
        b = self.Plot.boundaries
        t = self.Plot.current_time
    
        for boundary in b:
            if boundary > t:
                self.Plot.current_time = boundary
                break
    
        self.Plot.update_dot_position()
        
    # def skip_backward(self):
    #     b = self.Plot.boundaries
    #     t = self.Plot.current_time
    
    #     prev = 0
    #     for boundary in b:
    #         if boundary >= t:
    #             break
    #         prev = boundary
    
    #     self.Plot.current_time = prev
    #     self.Plot.update_dot_position()
        
    def send_program(self):
        if not hasattr(self, "arduino") or not self.arduino.is_open:
            return
    
        n = len(self.Add.movements)
    
        data = [str(n)]
        for m, d in zip(self.Add.movements, self.Add.durations):
            data.append(str(m))
            data.append(str(d))
    
        msg = "<" + ",".join(data) + ">"
        self.arduino.write(msg.encode())
        
    def read_serial(self): # threading required to read/write serial
        self.reading = True
        self.read_thread = threading.Thread(target=self.read_loop, daemon=True) # daemon thread allows program to close abruptly
        self.read_thread.start()

    def read_loop(self):
        while self.reading:
            try:
                data = self.arduino.readline().decode(errors='ignore').strip()
    
                if data and not self.paused:
                    if data.startswith("Time"):
                        continue
    
                    timeseries = time.strftime('%H:%M:%S')
                    line = f"{timeseries},{data}"
    
                    self.log_data.append(line) # store csv locally
            except (serial.SerialException, OSError) as e:
                print(f"Serial connection lost: {e}")
                break
            
    def save_csv(self):
        if not self.log_data: # ensure there is data to save
            return
        
        print(self.log_data)
        filename = f'PID_Force_{time.strftime("%H_%M_%S")}.csv' # saves to the current working directory
    
        with open(filename, 'w') as f:
            f.write("PC_Time,Arduino_Time,Force(N)\n")
            for line in self.log_data:
                f.write(line + '\n')
#%% Plot Frame - display matplotlib graphs, scroll bar

class PlotFrame(ttk.Frame):
    def __init__(self, parent, Welcome, Add):
        super().__init__(parent)
        
        # dependencies
        self.Welcome = Welcome
        self.Add = Add

        # preallocation
        self.window = 20  # seconds (fixed visible range)
        self.x_data = None
        self.y_force = None
        self.y_rot  = None
        self.running = False
        self.paused = False
        self.boundaries = [] # for skip buttons
        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # matplotlib subplots
        self.figure = plt.Figure(figsize=(5.5, 4))
        self.ax_force = self.figure.add_subplot(211)
        self.ax_rotation = self.figure.add_subplot(212)
        self.figure.tight_layout()
        
        # markers
        self.force_dot, = self.ax_force.plot([], [], 'ro')
        self.rot_dot, = self.ax_rotation.plot([], [], 'bo')
        
        self.current_time = 0
        self.running = False
        
        # implement into TKinter
        self.canvas = FigureCanvasTkAgg(self.figure, self)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # scroll control
        self.view_start = tk.DoubleVar(value=0)

        self.slider = ttk.Scale(
            self,from_=0,to=0,orient="horizontal", state="disabled",
            variable=self.view_start,
            command=lambda e: self.update_plot()
        )
        self.slider.grid(row=1, column=0, sticky="ew")

        # # Line object (for smoother updates)
        # self.line, = self.ax_force.plot([], [])
        # self.line, = self.ax_rotation.plot([], [])

        self.update_plot()

    def update_plot(self):

        if not self.Add.movements:
            self.ax_force.clear()
            self.ax_rotation.clear()
            self.canvas.draw()
            return

        step = 0.01 # resolution of graph plot, reduce for performance
        current_time = 0
        x = np.array([])
        y = np.array([])
        y_rotation = np.array([])
        
        try: # error handling weight spinbox
            weight = int(self.Welcome.var.get())
        except:
            weight = 36
            showerror('Error', 'Invalid weight - defaulting to 36kg')
            self.Add.popup.lift()
            
        walk_force = weight * 0.69 * 9.81
        stand_force = walk_force / 2
        run_force = weight * 1.06 * 9.81
        base_freq = 1  # CHANGE TO SLOW DOWN ROTATION, REPRESENTS WALKING FREQ
        period = 1/base_freq

        # movement functions - force
        stand = lambda t: np.full_like(t, stand_force)

        walk = lambda t: np.piecewise(
            t,
            [t % period < (0.5*period), t % period >= (0.5*period)],
            [lambda t: walk_force * np.abs(np.sin(t * np.pi * 2 * base_freq)), 0]
        )

        run = lambda t: np.piecewise(
            t,
            [t % (0.5*period) < (0.25*period), t % (0.5*period) >= (0.25*period)],
            [lambda t: run_force * np.abs(np.sin(t * np.pi * 4 * base_freq)), 0]
        )

        off = lambda t: np.full_like(t, 0)

        movement_map = {
            1: stand,
            2: walk,
            3: run,
            0: off
        }
        
        # movement functions - rotation
        stand_rot = lambda t: np.full_like(t, 140)
        walk_rot = lambda t: np.piecewise(
            t,
            [t % period < (0.5*period), t % period >= (0.5*period)],
            [140, lambda t: 20 * np.cos(t * np.pi * 4 * base_freq) + 120]
            )
        run_rot = lambda t: np.piecewise(
            t,
            [t % (0.5*period) < (0.25*period), t % (0.5*period) >= (0.25*period)],
            [140, lambda t: 25 * np.cos(t * np.pi * 8 * base_freq) + 115]
            )
        
        movement_rot_map = {
            1: stand_rot,
            2: walk_rot,
            3: run_rot,
            0: stand_rot
        }

        # build graphs
        self.boundaries = [0]
        for movement, duration in zip(self.Add.movements, self.Add.durations):
        
            if movement not in movement_map:
                continue
            
            duration = float(duration)
        
            # store boundary BEFORE adding segment
            self.boundaries.append(current_time + duration)
        
            t = np.arange(0, duration, step)
        
            x = np.concatenate((x, t + current_time))
            y = np.concatenate((y, movement_map[movement](t)))
            y_rotation = np.concatenate((y_rotation, movement_rot_map[movement](t)))
        
            current_time += duration

        total_time = current_time

        # slider range
        max_start = max(0, total_time - self.window)
        
        if max_start == 0:
            self.slider.configure(to=0, state="disabled")
            self.view_start.set(0)
        else:
            self.slider.configure(to=max_start, state="normal")

        start = self.view_start.get()
        end = start + self.window

        # clamp window
        if end > total_time:
            end = total_time
            start = max(0, end - self.window)

        # plot updates - force
        self.ax_force.clear()
        self.ax_force.plot(x, y)

        self.ax_force.set_xlim(start, end)
        self.ax_force.set_title("Elbow Loading")
        # self.ax_force.set_xlabel("Time (s)")
        self.ax_force.set_ylabel("Force (N)")
        self.ax_force.grid(alpha=0.1)
        
        # plot updates - rotation
        self.ax_rotation.clear()
        self.ax_rotation.plot(x, y_rotation, color='orange')

        self.ax_rotation.set_xlim(start, end)
        self.ax_rotation.set_ylim(70, 170)
        self.ax_rotation.set_title("Elbow Joint Angle")
        self.ax_rotation.set_xlabel("Time (s)")
        self.ax_rotation.set_ylabel("Rotation (deg)")
        self.ax_rotation.grid(alpha=0.1)
        
        # for animation
        self.x_data = x
        self.y_force = y
        self.y_rot = y_rotation
        # reset marker view (since plot updates clear axis)
        self.force_dot, = self.ax_force.plot([], [], 'ro', zorder=5, alpha = 0.6)
        self.rot_dot, = self.ax_rotation.plot([], [], 'ro', zorder=5, alpha = 0.6)
        
        self.canvas.draw()
        
    def start_anim(self):
        self.running = True
        self.paused = False
        self.start_time_ref = time.perf_counter() - self.current_time
        self.animate()
                
    def animate(self):        
        if not self.running or self.x_data is None:
            return
        
        if self.paused:
            return  # stop advancing but keep state
            
        now = time.perf_counter()
        self.current_time = now - self.start_time_ref
    
        idx = np.searchsorted(self.x_data, self.current_time) # state control
    
        if idx >= len(self.x_data):
            self.running = False
            return
    
        self.force_dot.set_data([self.x_data[idx]], [self.y_force[idx]])
        self.rot_dot.set_data([self.x_data[idx]], [self.y_rot[idx]])
        
        # auto scroll moving window
        start, end = self.ax_force.get_xlim()
        
        if self.current_time > start + self.window * 0.6:
            new_start = self.current_time - self.window * 0.6
            self.ax_force.set_xlim(new_start, new_start + self.window)
            self.ax_rotation.set_xlim(new_start, new_start + self.window)
        
        # only draw during downtime to prevent performance issues
        self.canvas.draw_idle()

        
        self.after(20, self.animate)
        
    def update_dot_position(self): # for skip forward / backward
        if self.x_data is None:
            return
    
        idx = np.searchsorted(self.x_data, self.current_time)
    
        if idx >= len(self.x_data):
            idx = len(self.x_data) - 1
    
        self.force_dot.set_data([self.x_data[idx]], [self.y_force[idx]])
        self.rot_dot.set_data([self.x_data[idx]], [self.y_rot[idx]])
    
        # auto scroll moving window
        start, end = self.ax_force.get_xlim()
        
        if self.current_time > start + self.window * 0.6:
            new_start = self.current_time - self.window * 0.6
            self.ax_force.set_xlim(new_start, new_start + self.window)
            self.ax_rotation.set_xlim(new_start, new_start + self.window)
    
        self.canvas.draw_idle()
#%% main loop
if __name__ == "__main__":
    main()