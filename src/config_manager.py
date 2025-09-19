"""
Configuration management for TixScanner.

Handles loading and parsing configuration from config.ini and environment variables.
"""

import os
import logging
import configparser
from pathlib import Path
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import time

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Exception raised for configuration errors."""
    pass


class ConfigManager:
    """
    Configuration manager for TixScanner.
    
    Loads configuration from config.ini and environment variables,
    with environment variables taking precedence.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file (defaults to config.ini)
        """
        self.config_file = config_file or "config.ini"
        self.config = configparser.ConfigParser()

        # Preserve case for option names (important for event IDs)
        self.config.optionxform = str

        self._load_config()
        logger.info("Configuration manager initialized")
    
    def _load_config(self) -> None:
        """Load configuration from file and environment."""
        config_path = Path(self.config_file)
        
        if not config_path.exists():
            raise ConfigError(f"Configuration file not found: {config_path}")
        
        try:
            self.config.read(config_path)
            logger.info(f"Configuration loaded from {config_path}")
        except Exception as e:
            raise ConfigError(f"Failed to load configuration: {e}")
    
    def get_ticketmaster_api_key(self) -> str:
        """
        Get Ticketmaster API key.
        
        Returns:
            API key string
            
        Raises:
            ConfigError: If API key is not configured
        """
        # Check environment variable first
        api_key = os.getenv('TICKETMASTER_API_KEY')
        
        if not api_key:
            # Fall back to config file
            api_key = self.config.get('api', 'ticketmaster_key', fallback=None)
        
        if not api_key or api_key == 'YOUR_TICKETMASTER_API_KEY_HERE':
            raise ConfigError(
                "Ticketmaster API key not configured. "
                "Set TICKETMASTER_API_KEY environment variable or update config.ini"
            )
        
        return api_key
    
    def get_email_config(self) -> Dict[str, Any]:
        """
        Get email configuration.

        Returns:
            Dictionary with email settings

        Note:
            We now use Gmail OAuth2 authentication, so passwords are not needed.
            Email configuration is primarily for recipient settings.
        """
        return {
            'gmail_user': os.getenv('GMAIL_USER') or self.config.get('email', 'gmail_user', fallback=''),
            'recipient': os.getenv('RECIPIENT_EMAIL') or self.config.get('email', 'recipient', fallback='')
        }
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """
        Get monitoring configuration.
        
        Returns:
            Dictionary with monitoring settings
        """
        try:
            # Parse daily summary time
            summary_time_str = self.config.get('monitoring', 'daily_summary_time', fallback='09:00')
            hour, minute = map(int, summary_time_str.split(':'))
            summary_time = time(hour, minute)
            
            return {
                'check_frequency_hours': self.config.getint('monitoring', 'check_frequency_hours', fallback=2),
                'daily_summary_time': summary_time,
                'minimum_price_drop_percent': self.config.getfloat('monitoring', 'minimum_price_drop_percent', fallback=10.0),
                'max_price_history_days': self.config.getint('monitoring', 'max_price_history_days', fallback=90)
            }
        except Exception as e:
            logger.error(f"Error parsing monitoring configuration: {e}")
            # Return defaults
            return {
                'check_frequency_hours': 2,
                'daily_summary_time': time(9, 0),
                'minimum_price_drop_percent': 10.0,
                'max_price_history_days': 90
            }
    
    def get_concert_config(self) -> Dict[str, Decimal]:
        """
        Get concert tracking configuration.
        
        Returns:
            Dictionary mapping event_id to threshold_price
        """
        concerts = {}
        
        if not self.config.has_section('concerts'):
            logger.warning("No [concerts] section found in configuration")
            return concerts
        
        try:
            for event_id, threshold_str in self.config.items('concerts'):
                try:
                    threshold_price = Decimal(threshold_str)
                    concerts[event_id] = threshold_price
                except Exception as e:
                    logger.error(f"Invalid threshold price for event {event_id}: {threshold_str} ({e})")
            
            logger.info(f"Loaded {len(concerts)} concert configurations")
            
        except Exception as e:
            logger.error(f"Error parsing concert configuration: {e}")
        
        return concerts
    
    def get_section_config(self) -> Dict[str, List[str]]:
        """
        Get section targeting configuration.
        
        Returns:
            Dictionary mapping event_id to list of target sections
        """
        sections = {}
        
        if not self.config.has_section('sections'):
            logger.warning("No [sections] section found in configuration")
            return sections
        
        try:
            for event_id, sections_str in self.config.items('sections'):
                try:
                    # Parse comma-separated section list
                    section_list = [s.strip() for s in sections_str.split(',') if s.strip()]
                    if section_list:
                        sections[event_id] = section_list
                        logger.debug(f"Event {event_id} targets sections: {section_list}")
                except Exception as e:
                    logger.error(f"Invalid section config for event {event_id}: {sections_str} ({e})")
            
            logger.info(f"Loaded section config for {len(sections)} events")
            
        except Exception as e:
            logger.error(f"Error parsing section configuration: {e}")
        
        return sections

    def get_section_thresholds_config(self) -> Dict[str, Dict[str, Decimal]]:
        """
        Get section-specific threshold configuration.

        Returns:
            Dictionary mapping event_id to section_name to threshold_price
            Format: {event_id: {section_name: threshold_price}}
        """
        thresholds = {}

        if not self.config.has_section('section_thresholds'):
            logger.debug("No [section_thresholds] section found in configuration")
            return thresholds

        try:
            for key, threshold_str in self.config.items('section_thresholds'):
                try:
                    # Parse event_id.section_name format
                    if '.' in key:
                        event_id, section_name = key.split('.', 1)
                        threshold_price = Decimal(threshold_str)

                        if event_id not in thresholds:
                            thresholds[event_id] = {}
                        thresholds[event_id][section_name] = threshold_price

                        logger.debug(f"Event {event_id}, section '{section_name}': ${threshold_price}")
                    else:
                        logger.warning(f"Invalid section threshold key format: {key} (expected: event_id.section_name)")

                except Exception as e:
                    logger.error(f"Invalid section threshold for {key}: {threshold_str} ({e})")

            logger.info(f"Loaded section thresholds for {len(thresholds)} events")

        except Exception as e:
            logger.error(f"Error parsing section thresholds configuration: {e}")

        return thresholds

    def get_logging_config(self) -> Dict[str, Any]:
        """
        Get logging configuration.
        
        Returns:
            Dictionary with logging settings
        """
        try:
            return {
                'log_level': self.config.get('logging', 'log_level', fallback='INFO'),
                'max_log_size_mb': self.config.getint('logging', 'max_log_size_mb', fallback=10),
                'log_backup_count': self.config.getint('logging', 'log_backup_count', fallback=5)
            }
        except Exception as e:
            logger.error(f"Error parsing logging configuration: {e}")
            return {
                'log_level': 'INFO',
                'max_log_size_mb': 10,
                'log_backup_count': 5
            }
    
    def get_database_path(self) -> str:
        """
        Get database path.
        
        Returns:
            Path to SQLite database file
        """
        return self.config.get('database', 'path', fallback='tickets.db')
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate configuration completeness.
        
        Returns:
            Dictionary with validation results
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check required API key
        try:
            api_key = self.get_ticketmaster_api_key()
            if len(api_key) < 10:  # Basic sanity check
                results['warnings'].append("API key seems too short")
        except ConfigError as e:
            results['valid'] = False
            results['errors'].append(f"API key: {e}")
        
        # Check concert configuration
        concerts = self.get_concert_config()
        if not concerts:
            results['warnings'].append("No concerts configured for tracking")
        
        # Check monitoring config
        monitoring = self.get_monitoring_config()
        if monitoring['check_frequency_hours'] < 1:
            results['warnings'].append("Check frequency is less than 1 hour - this may hit API limits")
        
        if monitoring['minimum_price_drop_percent'] < 1:
            results['warnings'].append("Minimum price drop threshold is very low - you may get many alerts")
        
        return results
    
    def get_all_config(self) -> Dict[str, Any]:
        """
        Get complete configuration for debugging.
        
        Returns:
            Dictionary with all configuration sections (API keys masked)
        """
        config_dict = {}
        
        for section in self.config.sections():
            config_dict[section] = dict(self.config.items(section))
        
        # Mask sensitive information
        if 'api' in config_dict and 'ticketmaster_key' in config_dict['api']:
            key = config_dict['api']['ticketmaster_key']
            config_dict['api']['ticketmaster_key'] = f"{'*' * (len(key) - 4)}{key[-4:]}" if len(key) > 4 else "****"
        
        return config_dict