from enum import Enum
import subprocess
import logging
from pathlib import Path
import json
from typing import List, Optional
import re

class AutoconfigStatus(Enum):
    DISABLED = 0
    ENABLED = 1
    UNABLE_TO_FETCH = 2
    NOT_UPDATED = 3

class WifiScanUtility:
    """Utility for managing Windows WiFi interface autoconfig settings."""
    
    def __init__(self, log_level: int = logging.INFO, config_path: str = "wifi_config.json"):
        self._interfaces: List[str] = []
        self._current_interface: Optional[str] = None
        self._last_status = AutoconfigStatus.NOT_UPDATED
        self._config_path = Path(config_path)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(Path.home() / "wifi_utility.log")
            ]
        )
        self.logger = logging.getLogger(__name__)
        self._load_config()

    def _load_config(self) -> None:
        """Load interface configuration from JSON file."""
        if not self._config_path.exists():
            self.logger.info("Config file not found, creating new one")
            self._save_config()
            return

        try:
            with open(self._config_path) as f:
                config = json.load(f)
                interface = config.get('current_interface')
                if interface:
                    self._current_interface = interface
                    self.logger.info(f"Loaded interface from config: {interface}")
        except json.JSONDecodeError:
            self.logger.error("Invalid config file format")
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")

    def _save_config(self) -> None:
        """Save current interface to JSON config file."""
        try:
            config = {'current_interface': self._current_interface}
            with open(self._config_path, 'w') as f:
                json.dump(config, f)
            self.logger.info("Config saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")

    def _run_command(self, command: str) -> str:
        """Execute a shell command and return its output."""
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {command}\nError: {e}")
            return ""

    def get_available_interfaces(self) -> List[str]:
        """Get list of available WiFi interfaces."""
        output = self._run_command("netsh wlan show profiles")
        if not output:
            self.logger.warning("No WiFi profiles found")
            self._interfaces = []
            return []

        interfaces = [match.group(1) for match in re.finditer(r"on interface (.*):", output)]
        self._interfaces = interfaces
        self.logger.info(f"Found interfaces: {interfaces}")
        return interfaces

    def set_current_interface(self, interface_name: str) -> bool:
        """Set the current WiFi interface to operate on."""
        if not interface_name or interface_name not in self._interfaces:
            self.logger.error(f"Invalid interface name: {interface_name}")
            self._current_interface = None
            return False
            
        self._current_interface = interface_name
        self._save_config()
        self.logger.info(f"Current interface set to: {interface_name}")
        return True

    def get_autoconfig_status(self) -> AutoconfigStatus:
        """Get current autoconfig status for the selected interface."""
        output = self._run_command("netsh wlan show autoconfig")
        
        if "enabled" in output.lower():
            status = AutoconfigStatus.ENABLED
        elif "disabled" in output.lower():
            status = AutoconfigStatus.DISABLED
        else:
            status = AutoconfigStatus.UNABLE_TO_FETCH
            
        self._last_status = status
        self.logger.info(f"Autoconfig status: {status}")
        return status

    def _modify_autoconfig(self, enable: bool) -> bool:
        """Helper method to modify autoconfig status."""
        if not self._current_interface:
            self.logger.error("No interface selected")
            return False

        command = f'netsh wlan set autoconfig enabled={"yes" if enable else "no"} interface="{self._current_interface}"'
        output = self._run_command(command)
        status = self.get_autoconfig_status()
        return status == (AutoconfigStatus.ENABLED if enable else AutoconfigStatus.DISABLED)

    def disable_scan(self) -> bool:
        """Disable WiFi scanning on current interface."""
        return self._modify_autoconfig(False)

    def enable_scan(self) -> bool:
        """Enable WiFi scanning on current interface."""
        return self._modify_autoconfig(True)

    @property
    def current_interface(self) -> Optional[str]:
        """Get currently selected interface."""
        return self._current_interface

    @property
    def last_status(self) -> AutoconfigStatus:
        """Get last known autoconfig status."""
        return self._last_status