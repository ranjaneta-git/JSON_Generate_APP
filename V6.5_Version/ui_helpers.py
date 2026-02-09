"""
UI Tooltip Helper
Provides tooltip functionality for better user experience
"""

import tkinter as tk

class ToolTip:
    """
    Create a tooltip for a given widget
    """
    def __init__(self, widget, text='', delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        
        self.widget.bind("<Enter>", self.schedule_show)
        self.widget.bind("<Leave>", self.hide)
        self.widget.bind("<ButtonPress>", self.hide)
    
    def schedule_show(self, event=None):
        """Schedule tooltip to show after delay"""
        self.cancel_scheduled()
        self.id = self.widget.after(self.delay, self.show)
    
    def cancel_scheduled(self):
        """Cancel scheduled tooltip"""
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None
    
    def show(self, event=None):
        """Display tooltip"""
        if self.tipwindow or not self.text:
            return
        
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        # Create styled tooltip
        frame = tk.Frame(tw, background="#2c3e50", relief=tk.SOLID, borderwidth=1)
        frame.pack()
        
        label = tk.Label(frame, text=self.text, justify=tk.LEFT,
                        background="#2c3e50", foreground="white",
                        relief=tk.FLAT, borderwidth=0,
                        font=("Segoe UI", 9), padx=10, pady=8)
        label.pack()
    
    def hide(self, event=None):
        """Hide tooltip"""
        self.cancel_scheduled()
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


def add_tooltips_to_app(app):
    """
    Add helpful tooltips to all widgets in the application
    """
    
    # Tooltip texts
    tooltips = {
        'baudrate': "Communication speed in bits per second\nCommon: 9600, 19200, 38400, 115200",
        'data_bits': "Number of data bits in each frame\nStandard: 8 bits",
        'parity': "Error checking method\nE=Even, O=Odd, N=None",
        'stop_bits': "Number of stop bits in each frame\nStandard: 1 or 2",
        'profile': "Modbus communication profile\nRTU: Binary encoding\nASCII: Text encoding",
        'param_id': "Unique parameter identifier (1-9999)",
        'slave_id': "Modbus slave device ID (1-247)",
        'fc': "Function Code:\n1=Read Coils, 2=Read Discrete\n3=Read Holding, 4=Read Input\n5=Write Coil, 6=Write Register\n15=Write Multiple Coils\n16=Write Multiple Registers",
        'address': "Starting Modbus register address (0-65535)",
        'length': "Number of registers to read/write (1-125)",
        'fmt': "Data format:\n1=UINT16, 2=INT16, 3=UINT32\n4=INT32, 5=FLOAT32, 6=STRING\n7=BIT, 8=ARRAY",
        'multiplier': "Value scaling factor\nExample: 0.1 for 123 → 12.3",
        'access': "Parameter access level:\nRO=Read Only\nRW=Read/Write\nWO=Write Only",
        'cloud': "Send to cloud?\nYes=Upload, No=Local only",
        'json_group': "Equipment grouping for cloud\nExample: AHU, Chiller, Pump",
        'json_unit': "Measurement unit for cloud\nExample: Temp, Press, Flow",
        'json_key': "Parameter name for cloud JSON\nExample: Ch1_ChW_T, VFD1_Speed",
        'array_membership': "Multi-value parameter group\nExample: CH1_AIE1 (multiple sensors)"
    }
    
    return tooltips


# Helper function to create labeled entry with tooltip
def create_labeled_entry_with_tooltip(parent, label_text, tooltip_text, row, col, entry_width=20):
    """Create a labeled entry field with tooltip"""
    label = tk.Label(parent, text=label_text, font=('Segoe UI', 9))
    label.grid(row=row, column=col, sticky='w', padx=5, pady=5)
    
    entry = tk.Entry(parent, width=entry_width, font=('Segoe UI', 9))
    entry.grid(row=row, column=col+1, padx=5, pady=5)
    
    # Add tooltip to both label and entry
    ToolTip(label, tooltip_text)
    ToolTip(entry, tooltip_text)
    
    return entry


# Helper function to create status indicator
def create_status_indicator(parent, text, status='info'):
    """Create a colored status indicator"""
    colors = {
        'success': '#27ae60',  # Green
        'warning': '#f39c12',  # Orange
        'error': '#e74c3c',    # Red
        'info': '#3498db'      # Blue
    }
    
    frame = tk.Frame(parent, bg=colors.get(status, colors['info']), padx=10, pady=5)
    label = tk.Label(frame, text=text, bg=colors.get(status, colors['info']), 
                    fg='white', font=('Segoe UI', 9, 'bold'))
    label.pack()
    
    return frame
