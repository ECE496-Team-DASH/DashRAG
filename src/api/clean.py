#!/usr/bin/env python3
"""
Clean State Script
==================
This script cleans the application state by:
1. Deleting the SQLite database file
2. Removing all session data from data/sessions/

Usage:
    python clean_state.py [--confirm]
    uv run clean_state.py [--confirm]
    
Options:
    --confirm    Skip confirmation prompt and proceed with cleanup
    -y           Alias for --confirm

Important:
    Stop the FastAPI server before running this script to avoid 
    database lock errors. If the database is locked, the sessions
    will still be cleaned but the database file will remain.
"""

import shutil
import sys
from pathlib import Path


def clean_database(db_path: Path) -> bool:
    """Remove the database file if it exists."""
    if db_path.exists():
        try:
            db_path.unlink()
            print(f"✓ Deleted database: {db_path}")
            return True
        except PermissionError as e:
            print(f"✗ Failed to delete database: {e}", file=sys.stderr)
            print("  ⚠️  The database is locked (server may be running). Stop the server first.", file=sys.stderr)
            return False
        except Exception as e:
            print(f"✗ Failed to delete database: {e}", file=sys.stderr)
            return False
    else:
        print(f"ℹ Database not found: {db_path}")
        return True


def clean_sessions(sessions_path: Path) -> bool:
    """Remove all session directories."""
    if not sessions_path.exists():
        print(f"ℹ Sessions directory not found: {sessions_path}")
        return True
    
    try:
        session_dirs = [d for d in sessions_path.iterdir() if d.is_dir()]
        
        if not session_dirs:
            print(f"ℹ No sessions to clean in: {sessions_path}")
            return True
        
        for session_dir in session_dirs:
            shutil.rmtree(session_dir)
            print(f"✓ Deleted session: {session_dir.name}")
        
        print(f"✓ Cleaned {len(session_dirs)} session(s)")
        return True
    except Exception as e:
        print(f"✗ Failed to clean sessions: {e}", file=sys.stderr)
        return False


def main():
    """Main cleanup function."""
    # Check for confirmation flag
    skip_confirm = "--confirm" in sys.argv or "-y" in sys.argv
    
    # Define paths relative to script location
    script_dir = Path(__file__).parent
    db_path = script_dir / "dashrag.db"
    sessions_path = script_dir / "data" / "sessions"
    
    print("Clean State Script")
    print("=" * 50)
    print(f"Database: {db_path}")
    print(f"Sessions: {sessions_path}")
    print("=" * 50)
    
    # Check what will be deleted
    db_exists = db_path.exists()
    session_dirs = []
    if sessions_path.exists():
        session_dirs = [d for d in sessions_path.iterdir() if d.is_dir()]
    
    if not db_exists and not session_dirs:
        print("\nℹ Nothing to clean. State is already empty.")
        return 0
    
    # Show what will be deleted
    if db_exists:
        print(f"\n• Database file will be deleted")
    if session_dirs:
        print(f"• {len(session_dirs)} session(s) will be deleted:")
        for session_dir in session_dirs:
            print(f"  - {session_dir.name}")
    
    # Confirmation prompt
    if not skip_confirm:
        print("\n⚠️  This action cannot be undone!")
        response = input("Proceed with cleanup? (yes/no): ").strip().lower()
        if response not in ["yes", "y"]:
            print("Cleanup cancelled.")
            return 0
    
    # Perform cleanup
    print("\nCleaning state...")
    success = True
    
    if db_exists:
        success = clean_database(db_path) and success
    
    if session_dirs:
        success = clean_sessions(sessions_path) and success
    
    # Summary
    print("\n" + "=" * 50)
    if success:
        print("✓ State cleaned successfully!")
        return 0
    else:
        print("✗ Some errors occurred during cleanup.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
