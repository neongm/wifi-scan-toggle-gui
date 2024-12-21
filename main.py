import dearpygui.dearpygui as dpg
from wifi_scan_utility import WifiScanUtility, AutoconfigStatus
import ctypes
import sys
from pathlib import Path
import win32con
import win32gui
import win32console
import logging

class WifiUtilityGUI:
    def __init__(self):
        self.wsu = WifiScanUtility()
        self.interfaces = []
        self.status_text = ""
        self.selected_interface = self.wsu.current_interface
        self.log_entries = []
        self.setup_log_handler()
        
        # Hide the console window associated with this script
        console_window = win32console.GetConsoleWindow()
        if console_window:
            win32gui.ShowWindow(console_window, win32con.SW_HIDE)

    def setup_log_handler(self):
        class GUILogHandler(logging.Handler):
            def __init__(self, callback):
                super().__init__()
                self.callback = callback

            def emit(self, record):
                log_entry = self.format(record)
                self.callback(log_entry)

        self.log_handler = GUILogHandler(self.add_log_entry)
        self.log_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        logging.getLogger().addHandler(self.log_handler)

    def add_log_entry(self, entry):
        # Add the new entry at the beginning of the list
        self.log_entries.insert(0, entry)
        if len(self.log_entries) > 10:  # Keep only the last 10 entries
            self.log_entries.pop()

        # Update the log text in the scrollable window
        if dpg.does_item_exist("log_text"):
            dpg.set_value("log_text", "\n".join(self.log_entries))



    def is_admin(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def restart_as_admin(self):
        script_path = Path(sys.argv[0]).resolve()
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, f'"{script_path}"', None, 1
            )
            sys.exit(0)  # Gracefully exit the current process after restarting
        except Exception as e:
            logging.error(f"Failed to restart as admin: {e}")


    def show_admin_prompt(self):
        if not dpg.does_item_exist("admin_modal"):
            with dpg.window(
                label="Administrator Required",
                modal=True,
                tag="admin_modal",
                width=460,
                height=150,
                no_close=True,
                pos=(100, 100)
            ):
                dpg.add_text(
                    "Changing WiFi settings requires administrator privileges.\n"
                    "Would you like to restart the application as administrator?"
                )
                with dpg.group(horizontal=True):
                    dpg.add_button(
                        label="Restart as Administrator",
                        callback=self.restart_as_admin
                    )
                    dpg.add_button(
                        label="Cancel",
                        callback=lambda: dpg.delete_item("admin_modal")
                    )
        else:
            # Bring the modal to the front if it already exists
            dpg.configure_item("admin_modal", show=True)


    def try_modify_settings(self, enable: bool):
        if not self.is_admin():
            self.show_admin_prompt()
            return
        
        if enable:
            self.wsu.enable_scan()
        else:
            self.wsu.disable_scan()
        self.update_status()

    def refresh_interfaces(self):
        self.interfaces = self.wsu.get_available_interfaces()
        if self.interfaces:
            dpg.configure_item("interface_combo", items=self.interfaces)
            if len(self.interfaces) == 1 or self.selected_interface in self.interfaces:
                interface_to_select = self.selected_interface if self.selected_interface in self.interfaces else self.interfaces[0]
                dpg.set_value("interface_combo", interface_to_select)
                self.on_interface_select(None, interface_to_select)

    def update_status(self):
        status = self.wsu.get_autoconfig_status()
        self.status_text = f"Status: {status.name}"
        dpg.set_value("status_text", self.status_text)
        
        if status == AutoconfigStatus.ENABLED:
            dpg.hide_item("enable_button")
            dpg.show_item("disable_button")
        else:
            dpg.show_item("enable_button")
            dpg.hide_item("disable_button")

    def on_interface_select(self, sender, app_data):
        self.selected_interface = app_data
        self.wsu.set_current_interface(app_data)
        self.update_status()

    def create_ui(self):
        with dpg.window(label="Settings", tag="Primary Window"):
            
            with dpg.group(horizontal=True):
                dpg.add_text("Select interface:")
                dpg.add_combo(
                    items=self.interfaces,
                    callback=self.on_interface_select,
                    tag="interface_combo",
                    default_value=self.selected_interface,
                    width=478
                )
                dpg.add_button(
                    label="Refresh",
                    callback=self.refresh_interfaces
                )
            
            dpg.add_spacer(height=10)


            dpg.add_text("", tag="status_text")

            dpg.add_button(
                label="Disable scan",
                callback=lambda: self.try_modify_settings(False),
                tag="disable_button",
                width=670,
                height=50
            )
            dpg.add_button(
                label="Enable scan",
                callback=lambda: self.try_modify_settings(True),
                tag="enable_button",
                width=670,
                height=50
            )

            dpg.add_spacer(height=20)
            dpg.add_text("Log:")
            # Scrollable child window for log display
            with dpg.child_window(
                tag="log_window",
                width=670,
                height=150,
                border=True,
                autosize_x=False,
                autosize_y=False
            ):
                dpg.add_text("", tag="log_text")  # Placeholder for log content

def start():
    dpg.create_context()
    dpg.create_viewport(
        title='Rinvos WiFi Autoconfig Toggle',
        width=702,
        height=370,
        resizable=False,
        vsync=True
    )

    gui = WifiUtilityGUI()
    gui.create_ui()
    gui.refresh_interfaces()

    dpg.setup_dearpygui()
    dpg.set_primary_window("Primary Window", True)
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()

if __name__ == "__main__":
    start()