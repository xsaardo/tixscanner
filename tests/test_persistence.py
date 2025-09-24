"""
Tests for database persistence functionality.

These tests verify that the git-based database backup system works correctly
for GitHub Codespaces deployment.
"""

import unittest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from git_backup import GitDatabaseBackup


class TestDatabasePersistence(unittest.TestCase):
    """Test database persistence with git backup."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.test_dir, "test.db")

        # Create a dummy database file
        with open(self.test_db_path, 'w') as f:
            f.write("dummy database content")

        self.backup = GitDatabaseBackup(
            db_path=self.test_db_path,
            repo_path=self.test_dir
        )

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_database_backup_initialization(self):
        """Test backup system initialization."""
        self.assertEqual(self.backup.db_path, Path(self.test_db_path))
        self.assertEqual(self.backup.repo_path, Path(self.test_dir))
        self.assertFalse(self.backup.git_configured)

    def test_backup_status_without_git(self):
        """Test backup status when git is not available."""
        with patch.object(self.backup, 'check_git_availability', return_value=False):
            status = self.backup.get_backup_status()
            self.assertFalse(status['git_available'])
            self.assertTrue(status['database_exists'])

    @patch('subprocess.run')
    def test_git_availability_check(self, mock_run):
        """Test git availability checking."""
        # Test git command available and in repository
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="git version 2.34.1"),  # git --version
            MagicMock(returncode=0, stdout=".git")  # git rev-parse --git-dir
        ]

        result = self.backup.check_git_availability()
        self.assertTrue(result)
        self.assertEqual(mock_run.call_count, 2)

    @patch('subprocess.run')
    def test_git_configuration_for_codespaces(self, mock_run):
        """Test git configuration for Codespaces."""
        # Mock git config check (no existing config)
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout=""),  # git config --global user.email (fails)
            MagicMock(returncode=0),  # git config --global user.email (set)
            MagicMock(returncode=0),  # git config --global user.name (set)
            MagicMock(returncode=0)   # git config --global init.defaultBranch (set)
        ]

        result = self.backup.configure_git_for_codespaces()
        self.assertTrue(result)
        self.assertTrue(self.backup.git_configured)

    @patch('subprocess.run')
    def test_backup_database_success(self, mock_run):
        """Test successful database backup."""
        # Mock successful git operations
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="git version"),  # git --version
            MagicMock(returncode=0, stdout=".git"),  # git rev-parse --git-dir
            MagicMock(returncode=0, stdout="M test.db"),  # git status --porcelain
            MagicMock(returncode=0),  # git add
            MagicMock(returncode=0, stdout="[main abc123] Auto-backup"),  # git commit
            MagicMock(returncode=0)   # git push
        ]

        with patch.object(self.backup, 'git_configured', True):
            result = self.backup.backup_database()

        self.assertTrue(result['success'])
        self.assertTrue(result['committed'])
        self.assertTrue(result['pushed'])

    @patch('subprocess.run')
    def test_backup_no_changes(self, mock_run):
        """Test backup when there are no changes."""
        # Mock git operations showing no changes
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="git version"),  # git --version
            MagicMock(returncode=0, stdout=".git"),  # git rev-parse --git-dir
            MagicMock(returncode=0, stdout="")  # git status --porcelain (empty)
        ]

        with patch.object(self.backup, 'git_configured', True):
            result = self.backup.backup_database()

        self.assertTrue(result['success'])
        self.assertFalse(result['committed'])
        self.assertEqual(result['message'], 'No database changes to backup')

    def test_scheduler_integration(self):
        """Test that scheduler can integrate with git backup."""
        try:
            from scheduler import MonitoringScheduler

            # Create a mock price monitor
            mock_monitor = MagicMock()
            mock_monitor.check_all_prices.return_value = {'prices_checked': 0, 'alerts_sent': 0}
            mock_monitor.send_daily_summary.return_value = True
            mock_monitor.cleanup_old_data.return_value = 0

            # Test scheduler creation with git backup
            scheduler = MonitoringScheduler(mock_monitor)
            self.assertIsNotNone(scheduler.git_backup)

            # Test status includes git backup info
            status = scheduler.get_status()
            self.assertIn('git_backup', status)

        except ImportError:
            self.skipTest("Scheduler module not available for testing")


class TestSchedulerPersistence(unittest.TestCase):
    """Test scheduler integration with persistence."""

    def test_backup_scheduling_logic(self):
        """Test backup scheduling logic."""
        try:
            from scheduler import MonitoringScheduler
            from datetime import datetime, time

            # Create mock price monitor
            mock_monitor = MagicMock()
            scheduler = MonitoringScheduler(mock_monitor)

            # Test backup time configuration
            test_time = time(1, 30)  # 1:30 AM
            scheduler.configure(backup_time=test_time)
            self.assertEqual(scheduler.backup_time, test_time)

            # Test should backup logic
            # Should backup if it's after backup time and haven't backed up today
            test_datetime = datetime.now().replace(hour=2, minute=0)  # 2:00 AM
            scheduler._last_backup_date = None
            should_backup = scheduler._should_backup_database(test_datetime)
            self.assertTrue(should_backup)

            # Should not backup if already backed up today
            scheduler._last_backup_date = test_datetime.date()
            should_backup = scheduler._should_backup_database(test_datetime)
            self.assertFalse(should_backup)

        except ImportError:
            self.skipTest("Scheduler module not available for testing")


if __name__ == '__main__':
    unittest.main()