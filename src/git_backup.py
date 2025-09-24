"""
Git-based database backup system for TixScanner.

This module provides automated database backup functionality using Git,
specifically designed for GitHub Codespaces where the filesystem is ephemeral.
"""

import logging
import subprocess
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class GitBackupError(Exception):
    """Custom exception for git backup operations."""
    pass


class GitDatabaseBackup:
    """
    Git-based database backup system.

    Provides automated backup of SQLite database to Git repository,
    with support for Codespaces environment.
    """

    def __init__(self, db_path: str = "tickets.db", repo_path: str = "."):
        """
        Initialize git backup system.

        Args:
            db_path: Path to the SQLite database file
            repo_path: Path to the git repository root
        """
        self.db_path = Path(db_path)
        self.repo_path = Path(repo_path)
        self.git_configured = False

        logger.info(f"Git backup initialized for database: {db_path}")

    def check_git_availability(self) -> bool:
        """
        Check if git is available and repository is initialized.

        Returns:
            True if git is available and repository exists
        """
        try:
            # Check if git command is available
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                logger.error("Git command not available")
                return False

            # Check if we're in a git repository
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=10
            )
            if result.returncode != 0:
                logger.error("Not in a git repository")
                return False

            logger.info("Git availability check passed")
            return True

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"Git availability check failed: {e}")
            return False

    def configure_git_for_codespaces(self) -> bool:
        """
        Configure git for automated commits in Codespaces environment.

        Returns:
            True if configuration successful
        """
        try:
            # Check if git is already configured
            result = subprocess.run(
                ["git", "config", "--global", "user.email"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0 or not result.stdout.strip():
                # Configure git for automated commits
                commands = [
                    ["git", "config", "--global", "user.email", "tixscanner@codespaces.github"],
                    ["git", "config", "--global", "user.name", "TixScanner Auto-Backup"],
                    ["git", "config", "--global", "init.defaultBranch", "main"]
                ]

                for cmd in commands:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode != 0:
                        logger.error(f"Git config command failed: {' '.join(cmd)}")
                        return False

                logger.info("Git configured for Codespaces")
            else:
                logger.info("Git already configured")

            self.git_configured = True
            return True

        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            logger.error(f"Git configuration failed: {e}")
            return False

    def check_database_changes(self) -> bool:
        """
        Check if database has changes that need to be committed.

        Returns:
            True if database has uncommitted changes
        """
        try:
            # Check git status for the database file
            result = subprocess.run(
                ["git", "status", "--porcelain", str(self.db_path)],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=10
            )

            if result.returncode != 0:
                logger.error("Failed to check git status")
                return False

            # If output is not empty, there are changes
            has_changes = bool(result.stdout.strip())
            logger.debug(f"Database changes detected: {has_changes}")
            return has_changes

        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            logger.error(f"Failed to check database changes: {e}")
            return False

    def backup_database(self, commit_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Backup database to git repository.

        Args:
            commit_message: Custom commit message

        Returns:
            Dictionary with backup results
        """
        result = {
            'success': False,
            'committed': False,
            'pushed': False,
            'message': '',
            'timestamp': datetime.now()
        }

        try:
            # Check if git is available
            if not self.check_git_availability():
                result['message'] = 'Git not available'
                return result

            # Configure git if needed
            if not self.git_configured and not self.configure_git_for_codespaces():
                result['message'] = 'Git configuration failed'
                return result

            # Check if database file exists
            if not self.db_path.exists():
                result['message'] = f'Database file not found: {self.db_path}'
                logger.warning(result['message'])
                return result

            # Check if there are changes to commit
            if not self.check_database_changes():
                result['message'] = 'No database changes to backup'
                result['success'] = True
                logger.info("Database backup: no changes detected")
                return result

            # Add database file to git
            add_result = subprocess.run(
                ["git", "add", str(self.db_path)],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=30
            )

            if add_result.returncode != 0:
                result['message'] = f'Git add failed: {add_result.stderr}'
                logger.error(result['message'])
                return result

            # Create commit message
            if not commit_message:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                commit_message = f"Auto-backup database: {timestamp}"

            # Commit changes
            commit_result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=30
            )

            if commit_result.returncode != 0:
                # Check if it's because there are no changes
                if "nothing to commit" in commit_result.stdout:
                    result['message'] = 'No changes to commit'
                    result['success'] = True
                    logger.info("Database backup: no changes to commit")
                    return result
                else:
                    result['message'] = f'Git commit failed: {commit_result.stderr}'
                    logger.error(result['message'])
                    return result

            result['committed'] = True
            logger.info(f"Database committed to git: {commit_message}")

            # Try to push changes (may fail if no remote or authentication issues)
            try:
                push_result = subprocess.run(
                    ["git", "push"],
                    capture_output=True,
                    text=True,
                    cwd=self.repo_path,
                    timeout=60
                )

                if push_result.returncode == 0:
                    result['pushed'] = True
                    logger.info("Database changes pushed to remote repository")
                else:
                    logger.warning(f"Failed to push to remote: {push_result.stderr}")
                    # Don't fail the backup if push fails - commit is still successful

            except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
                logger.warning(f"Push attempt failed: {e}")

            result['success'] = True
            result['message'] = f'Database backup successful (committed: {result["committed"]}, pushed: {result["pushed"]})'
            logger.info(result['message'])

        except Exception as e:
            result['message'] = f'Database backup failed: {e}'
            logger.error(result['message'])

        return result

    def restore_database_from_git(self) -> bool:
        """
        Restore database from git (useful for Codespace startup).

        Returns:
            True if restore successful or no action needed
        """
        try:
            # Check if database already exists locally
            if self.db_path.exists():
                logger.info("Database file already exists locally")
                return True

            # Check if git is available
            if not self.check_git_availability():
                logger.warning("Git not available for database restore")
                return False

            # Pull latest changes from remote
            try:
                pull_result = subprocess.run(
                    ["git", "pull"],
                    capture_output=True,
                    text=True,
                    cwd=self.repo_path,
                    timeout=60
                )

                if pull_result.returncode == 0:
                    logger.info("Pulled latest changes from remote repository")
                else:
                    logger.warning(f"Failed to pull from remote: {pull_result.stderr}")

            except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
                logger.warning(f"Pull attempt failed: {e}")

            # Check if database file now exists
            if self.db_path.exists():
                logger.info(f"Database restored from git: {self.db_path}")
                return True
            else:
                logger.info("No database file in repository - will be created on first run")
                return True

        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return False

    def get_backup_status(self) -> Dict[str, Any]:
        """
        Get status information about git backup system.

        Returns:
            Dictionary with backup system status
        """
        status = {
            'git_available': False,
            'git_configured': self.git_configured,
            'database_exists': self.db_path.exists(),
            'database_size_mb': 0,
            'has_uncommitted_changes': False,
            'last_commit': None,
            'remote_configured': False
        }

        try:
            # Check git availability
            status['git_available'] = self.check_git_availability()

            if status['git_available']:
                # Check for uncommitted changes
                status['has_uncommitted_changes'] = self.check_database_changes()

                # Get last commit info
                try:
                    result = subprocess.run(
                        ["git", "log", "-1", "--pretty=format:%H|%ad|%s", "--date=iso", "--", str(self.db_path)],
                        capture_output=True,
                        text=True,
                        cwd=self.repo_path,
                        timeout=10
                    )

                    if result.returncode == 0 and result.stdout.strip():
                        parts = result.stdout.strip().split('|', 2)
                        if len(parts) == 3:
                            status['last_commit'] = {
                                'hash': parts[0][:8],
                                'date': parts[1],
                                'message': parts[2]
                            }

                except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                    pass

                # Check if remote is configured
                try:
                    result = subprocess.run(
                        ["git", "remote", "-v"],
                        capture_output=True,
                        text=True,
                        cwd=self.repo_path,
                        timeout=10
                    )

                    status['remote_configured'] = bool(result.stdout.strip())

                except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                    pass

            # Get database file size
            if status['database_exists']:
                status['database_size_mb'] = round(self.db_path.stat().st_size / 1024 / 1024, 2)

        except Exception as e:
            logger.error(f"Failed to get backup status: {e}")

        return status