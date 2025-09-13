"""
Price chart generation for TixScanner email notifications.

This module generates professional-looking price trend charts using matplotlib
for embedding in email notifications.
"""

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server environments

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from decimal import Decimal
import io
import base64
from pathlib import Path

from .models import PriceHistory, Concert
from .db_operations import get_price_history, get_concert

logger = logging.getLogger(__name__)

# Chart styling constants
CHART_WIDTH = 10
CHART_HEIGHT = 6
DPI = 150
COLORS = {
    'primary': '#2E86AB',    # Blue
    'secondary': '#A23B72',   # Purple
    'success': '#F18F01',     # Orange
    'danger': '#C73E1D',      # Red
    'threshold': '#FF6B6B',   # Light red for threshold line
    'background': '#F8F9FA',  # Light gray
    'text': '#2C3E50',        # Dark gray
    'grid': '#E9ECEF'         # Light grid lines
}

STYLE_CONFIG = {
    'font.family': 'sans-serif',
    'font.size': 10,
    'axes.labelsize': 12,
    'axes.titlesize': 14,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'axes.edgecolor': COLORS['text'],
    'axes.linewidth': 0.8,
    'grid.color': COLORS['grid'],
    'grid.linestyle': '-',
    'grid.linewidth': 0.5,
    'text.color': COLORS['text']
}


class ChartGenerator:
    """
    Chart generator for price trend visualization.
    
    Creates professional charts for embedding in email notifications
    with customizable styling and data visualization options.
    """
    
    def __init__(self):
        """Initialize chart generator with styling."""
        # Apply styling
        plt.rcParams.update(STYLE_CONFIG)
        logger.debug("Chart generator initialized")
    
    def generate_price_trend_chart(self, event_id: str, days: int = 30,
                                  chart_title: Optional[str] = None,
                                  db_path: Optional[str] = None) -> Optional[str]:
        """
        Generate a price trend chart for an event.
        
        Args:
            event_id: Event ID to generate chart for
            days: Number of days of history to include
            chart_title: Custom chart title (optional)
            db_path: Database path (optional)
            
        Returns:
            Base64-encoded PNG image string or None if generation fails
        """
        try:
            # Get event and price data
            concert = get_concert(event_id, db_path)
            if not concert:
                logger.error(f"Concert not found: {event_id}")
                return None
            
            price_history = get_price_history(event_id, days, db_path)
            if not price_history:
                logger.warning(f"No price history found for {event_id}")
                # Generate placeholder chart
                return self._generate_no_data_chart(concert.name)
            
            # Create the chart
            return self._create_trend_chart(concert, price_history, chart_title)
            
        except Exception as e:
            logger.error(f"Failed to generate chart for {event_id}: {e}")
            return None
    
    def _create_trend_chart(self, concert: Concert, 
                           price_history: List[PriceHistory],
                           chart_title: Optional[str] = None) -> str:
        """
        Create the actual trend chart.
        
        Args:
            concert: Concert object
            price_history: List of price history records
            chart_title: Custom chart title
            
        Returns:
            Base64-encoded PNG image string
        """
        # Create figure and axis
        fig, ax = plt.subplots(figsize=(CHART_WIDTH, CHART_HEIGHT), dpi=DPI)
        
        # Prepare data
        dates = [ph.recorded_at for ph in price_history]
        prices = [float(ph.price) for ph in price_history]
        
        # Convert to pandas for easier manipulation
        df = pd.DataFrame({
            'date': dates,
            'price': prices,
            'section': [ph.section or 'General' for ph in price_history]
        })
        
        # Sort by date
        df = df.sort_values('date')
        
        # Group by section if multiple sections exist
        sections = df['section'].unique()
        
        # Plot price lines for each section
        colors_cycle = [COLORS['primary'], COLORS['secondary'], COLORS['success'], COLORS['danger']]
        
        for i, section in enumerate(sections):
            section_data = df[df['section'] == section].sort_values('date')
            color = colors_cycle[i % len(colors_cycle)]
            
            ax.plot(section_data['date'], section_data['price'], 
                   color=color, linewidth=2.5, marker='o', markersize=4,
                   label=section, alpha=0.8)
        
        # Add threshold line
        threshold_price = float(concert.threshold_price)
        ax.axhline(y=threshold_price, color=COLORS['threshold'], 
                  linestyle='--', linewidth=2, alpha=0.8,
                  label=f'Threshold (${threshold_price:.0f})')
        
        # Highlight current price
        if prices:
            latest_price = prices[-1]
            latest_date = dates[-1]
            
            # Add price annotation
            bbox_props = dict(boxstyle="round,pad=0.3", facecolor='white', 
                            edgecolor=COLORS['primary'], alpha=0.9)
            ax.annotate(f'Current: ${latest_price:.0f}', 
                       xy=(latest_date, latest_price),
                       xytext=(10, 10), textcoords='offset points',
                       bbox=bbox_props, fontweight='bold',
                       arrowprops=dict(arrowstyle='->', color=COLORS['primary']))
        
        # Customize axes
        ax.set_xlabel('Date', fontweight='bold')
        ax.set_ylabel('Price ($)', fontweight='bold')
        
        # Set title
        title = chart_title or f'{concert.name}'
        if concert.venue:
            title += f'\n{concert.venue}'
        ax.set_title(title, fontweight='bold', pad=20)
        
        # Format x-axis dates
        if len(dates) > 7:
            ax.xaxis.set_major_locator(mdates.WeekdayLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        else:
            ax.xaxis.set_major_locator(mdates.DayLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        
        # Rotate x-axis labels for better readability
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Add grid
        ax.grid(True, alpha=0.3)
        
        # Add legend
        if len(sections) > 1 or any(prices):
            ax.legend(loc='upper right', frameon=True, fancybox=True, shadow=True)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save to base64 string
        return self._fig_to_base64(fig)
    
    def _generate_no_data_chart(self, event_name: str) -> str:
        """
        Generate a placeholder chart when no price data is available.
        
        Args:
            event_name: Name of the event
            
        Returns:
            Base64-encoded PNG image string
        """
        fig, ax = plt.subplots(figsize=(CHART_WIDTH, CHART_HEIGHT), dpi=DPI)
        
        # Create empty plot with message
        ax.text(0.5, 0.5, 'No Price Data Available\nMonitoring Started Recently', 
               ha='center', va='center', transform=ax.transAxes,
               fontsize=16, color=COLORS['text'], 
               bbox=dict(boxstyle="round,pad=0.5", facecolor=COLORS['background']))
        
        ax.set_title(f'{event_name}\nPrice Monitoring', fontweight='bold', pad=20)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xticks([])
        ax.set_yticks([])
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def generate_summary_chart(self, concert_data: List[Dict], 
                              db_path: Optional[str] = None) -> Optional[str]:
        """
        Generate a summary chart showing multiple concerts.
        
        Args:
            concert_data: List of concert dictionaries with price changes
            db_path: Database path (optional)
            
        Returns:
            Base64-encoded PNG image string or None if generation fails
        """
        try:
            if not concert_data:
                return self._generate_no_concerts_chart()
            
            fig, ax = plt.subplots(figsize=(CHART_WIDTH, CHART_HEIGHT), dpi=DPI)
            
            # Prepare data
            names = []
            current_prices = []
            price_changes = []
            threshold_prices = []
            
            for concert in concert_data:
                names.append(concert['name'][:30] + '...' if len(concert['name']) > 30 else concert['name'])
                current_prices.append(concert.get('current_price', 0))
                price_changes.append(concert.get('price_change_percent', 0))
                threshold_prices.append(concert.get('threshold_price', 0))
            
            # Create bar chart
            y_pos = np.arange(len(names))
            
            # Color bars based on price change
            colors = []
            for change in price_changes:
                if change < -5:  # Significant drop
                    colors.append(COLORS['success'])
                elif change < 0:  # Small drop
                    colors.append(COLORS['primary'])
                elif change > 5:  # Significant increase
                    colors.append(COLORS['danger'])
                else:  # Small increase or no change
                    colors.append(COLORS['secondary'])
            
            bars = ax.barh(y_pos, current_prices, color=colors, alpha=0.8)
            
            # Add threshold markers
            for i, threshold in enumerate(threshold_prices):
                if threshold > 0:
                    ax.axvline(x=threshold, color=COLORS['threshold'], 
                             linestyle='--', alpha=0.6, linewidth=1)
            
            # Add price labels on bars
            for i, (bar, price, change) in enumerate(zip(bars, current_prices, price_changes)):
                width = bar.get_width()
                change_text = f"{change:+.1f}%" if change != 0 else "0%"
                ax.text(width + max(current_prices) * 0.01, bar.get_y() + bar.get_height()/2,
                       f'${price:.0f} ({change_text})', 
                       ha='left', va='center', fontweight='bold', fontsize=9)
            
            # Customize chart
            ax.set_yticks(y_pos)
            ax.set_yticklabels(names)
            ax.set_xlabel('Current Price ($)', fontweight='bold')
            ax.set_title('Concert Price Summary', fontweight='bold', pad=20)
            
            # Add grid
            ax.grid(True, axis='x', alpha=0.3)
            
            # Adjust layout
            plt.tight_layout()
            
            return self._fig_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Failed to generate summary chart: {e}")
            return None
    
    def _generate_no_concerts_chart(self) -> str:
        """Generate placeholder chart when no concerts are being tracked."""
        fig, ax = plt.subplots(figsize=(CHART_WIDTH, CHART_HEIGHT), dpi=DPI)
        
        ax.text(0.5, 0.5, 'No Concerts Being Tracked\nAdd events to your config.ini', 
               ha='center', va='center', transform=ax.transAxes,
               fontsize=16, color=COLORS['text'],
               bbox=dict(boxstyle="round,pad=0.5", facecolor=COLORS['background']))
        
        ax.set_title('TixScanner Dashboard', fontweight='bold', pad=20)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xticks([])
        ax.set_yticks([])
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def _fig_to_base64(self, fig) -> str:
        """
        Convert matplotlib figure to base64 string.
        
        Args:
            fig: Matplotlib figure object
            
        Returns:
            Base64-encoded PNG image string
        """
        try:
            # Save figure to bytes buffer
            buffer = io.BytesIO()
            fig.savefig(buffer, format='png', dpi=DPI, bbox_inches='tight',
                       facecolor='white', edgecolor='none', 
                       pad_inches=0.2, transparent=False)
            buffer.seek(0)
            
            # Convert to base64
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Clean up
            buffer.close()
            plt.close(fig)
            
            logger.debug("Chart converted to base64 successfully")
            return image_base64
            
        except Exception as e:
            logger.error(f"Failed to convert chart to base64: {e}")
            plt.close(fig)
            return ""
    
    def save_chart_file(self, event_id: str, days: int = 30, 
                       output_path: Optional[str] = None,
                       db_path: Optional[str] = None) -> Optional[str]:
        """
        Save chart as a file (for testing/debugging).
        
        Args:
            event_id: Event ID to generate chart for
            days: Number of days of history
            output_path: Output file path (optional)
            db_path: Database path (optional)
            
        Returns:
            Path to saved file or None if failed
        """
        try:
            base64_image = self.generate_price_trend_chart(event_id, days, db_path=db_path)
            if not base64_image:
                return None
            
            # Decode base64 and save
            image_data = base64.b64decode(base64_image)
            
            if not output_path:
                output_path = f"chart_{event_id}_{days}days.png"
            
            Path(output_path).write_bytes(image_data)
            logger.info(f"Chart saved to: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to save chart file: {e}")
            return None


def generate_price_chart(event_id: str, days: int = 30, 
                        db_path: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to generate a price chart.
    
    Args:
        event_id: Event ID
        days: Number of days of history
        db_path: Database path (optional)
        
    Returns:
        Base64-encoded PNG image string or None if failed
    """
    generator = ChartGenerator()
    return generator.generate_price_trend_chart(event_id, days, db_path=db_path)


def generate_summary_chart(concert_data: List[Dict], 
                          db_path: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to generate a summary chart.
    
    Args:
        concert_data: List of concert data dictionaries
        db_path: Database path (optional)
        
    Returns:
        Base64-encoded PNG image string or None if failed
    """
    generator = ChartGenerator()
    return generator.generate_summary_chart(concert_data, db_path)