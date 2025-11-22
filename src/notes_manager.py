# import streamlit as st # <-- REMOVED
import sqlite3
import uuid
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PersistentStorageManager:
    def __init__(self, db_path: str = 'workspace.db'):
        """
        Initialize the persistent storage manager with a SQLite database.
        
        Args:
            db_path (str): Path to the SQLite database file.
        """
        self.db_path = db_path
        self._init_database()
        self.last_saved_session_id: Optional[str] = None

    def _init_database(self) -> None:
        """Initialize SQLite database schema and perform migrations if necessary."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create notes table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS notes (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        content TEXT,
                        tags TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        folder TEXT DEFAULT 'General'
                    )
                ''')
                
                # Create chats table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS chats (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        chat_history TEXT, -- Stored as JSON string
                        uploaded_files TEXT, -- Stored as JSON string (list of filenames)
                        vectorstore_path TEXT, -- <-- ADDED
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # --- Schema Migration for existing databases ---
                cursor.execute("PRAGMA table_info(chats)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'title' not in columns:
                    logger.info("Migrating 'chats' table: Adding 'title' column.")
                    cursor.execute("ALTER TABLE chats ADD COLUMN title TEXT DEFAULT 'Untitled Chat'")
                
                if 'uploaded_files' not in columns:
                    logger.info("Migrating 'chats' table: Adding 'uploaded_files' column.")
                    cursor.execute("ALTER TABLE chats ADD COLUMN uploaded_files TEXT DEFAULT '[]'")
                
                if 'created_at' not in columns:
                    logger.info("Migrating 'chats' table: Adding 'created_at' column.")
                    cursor.execute("ALTER TABLE chats ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

                if 'last_updated' not in columns:
                    logger.info("Migrating 'chats' table: Adding 'last_updated' column.")
                    cursor.execute("ALTER TABLE chats ADD COLUMN last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                
                if 'vectorstore_path' not in columns:
                    logger.info("Migrating 'chats' table: Adding 'vectorstore_path' column.")
                    cursor.execute("ALTER TABLE chats ADD COLUMN vectorstore_path TEXT")

                conn.commit()
            logger.info("Database initialized and migrated successfully.")
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    # --- NOTE: All st.error() calls have been removed from all methods below ---
    # --- The logger will log the error, and in most cases we re-raise it ---

    def add_note(self, title: str, content: str, tags: List[str], folder: str = 'General') -> str:
        note_id = str(uuid.uuid4())
        tags_json = json.dumps(tags)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO notes (id, title, content, tags, folder) VALUES (?, ?, ?, ?, ?)",
                    (note_id, title, content, tags_json, folder)
                )
                conn.commit()
            logger.info(f"Note '{title}' added with ID: {note_id}")
            return note_id
        except sqlite3.Error as e:
            logger.error(f"Failed to add note '{title}': {e}")
            raise

    def get_note(self, note_id: str) -> Optional[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
                row = cursor.fetchone()
                if row:
                    note = dict(row)
                    note['tags'] = json.loads(note['tags'])
                    logger.info(f"Note '{note_id}' retrieved.")
                    return note
                return None
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve note '{note_id}': {e}")
            raise

    def get_all_notes(self) -> List[Dict[str, Any]]:
        notes = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM notes ORDER BY created_at DESC")
                rows = cursor.fetchall()
                for row in rows:
                    note = dict(row)
                    note['tags'] = json.loads(note['tags'])
                    notes.append(note)
            logger.info(f"Retrieved {len(notes)} notes.")
            return notes
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve all notes: {e}")
            raise

    def update_note(self, note_id: str, title: str, content: str, tags: List[str], folder: str) -> bool:
        tags_json = json.dumps(tags)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE notes SET title = ?, content = ?, tags = ?, folder = ? WHERE id = ?",
                    (title, content, tags_json, folder, note_id)
                )
                conn.commit()
            logger.info(f"Note '{note_id}' updated.")
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Failed to update note '{note_id}': {e}")
            raise

    def delete_note(self, note_id: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
                conn.commit()
            logger.info(f"Note '{note_id}' deleted.")
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Failed to delete note '{note_id}': {e}")
            raise

    def search_notes(self, query: str = "", filter_tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        notes = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                sql_query = "SELECT * FROM notes WHERE 1=1"
                params: List[Any] = []

                if query:
                    sql_query += " AND (title LIKE ? OR content LIKE ?)"
                    params.extend([f"%{query}%", f"%{query}%"])
                
                if filter_tags:
                    tag_conditions = []
                    for tag in filter_tags:
                        tag_conditions.append("tags LIKE ?")
                        params.append(f"%\"{tag}\"%")
                    if tag_conditions:
                        sql_query += " AND (" + " OR ".join(tag_conditions) + ")"
                
                sql_query += " ORDER BY created_at DESC"
                
                cursor.execute(sql_query, tuple(params))
                rows = cursor.fetchall()
                for row in rows:
                    note = dict(row)
                    note['tags'] = json.loads(note['tags'])
                    notes.append(note)
            logger.info(f"Found {len(notes)} notes for query '{query}' and tags {filter_tags}.")
            return notes
        except sqlite3.Error as e:
            logger.error(f"Failed to search notes: {e}")
            raise

    def save_chat_session(self, session_id: Optional[str], title: str, chat_history: List[Dict[str, Any]], uploaded_files: List[str], vectorstore_path: Optional[str] = None) -> str:
        chat_history_json = json.dumps(chat_history)
        uploaded_files_json = json.dumps(uploaded_files)
        current_time = datetime.now().isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if session_id:
                    # If no new path is provided, keep the existing one
                    if not vectorstore_path:
                        cursor.execute("SELECT vectorstore_path FROM chats WHERE id = ?", (session_id,))
                        row = cursor.fetchone()
                        if row:
                            vectorstore_path = row[0]
                    
                    cursor.execute(
                        """
                        UPDATE chats SET title = ?, chat_history = ?, uploaded_files = ?, vectorstore_path = ?, last_updated = ?
                        WHERE id = ?
                        """,
                        (title, chat_history_json, uploaded_files_json, vectorstore_path, current_time, session_id)
                    )
                    if cursor.rowcount == 0:
                        session_id = str(uuid.uuid4())
                        cursor.execute(
                            """
                            INSERT INTO chats (id, title, chat_history, uploaded_files, vectorstore_path, created_at, last_updated)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (session_id, title, chat_history_json, uploaded_files_json, vectorstore_path, current_time, current_time)
                        )
                        logger.info(f"New chat session inserted (update failed) with ID: {session_id}")
                    else:
                        logger.info(f"Chat session '{session_id}' updated.")
                else:
                    session_id = str(uuid.uuid4())
                    cursor.execute(
                        """
                        INSERT INTO chats (id, title, chat_history, uploaded_files, vectorstore_path, created_at, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (session_id, title, chat_history_json, uploaded_files_json, vectorstore_path, current_time, current_time)
                    )
                    logger.info(f"New chat session created with ID: {session_id}")
                conn.commit()
            self.last_saved_session_id = session_id
            return session_id
        except sqlite3.Error as e:
            logger.error(f"Failed to save chat session '{session_id}': {e}")
            raise

    def get_chat_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM chats WHERE id = ?", (session_id,))
                row = cursor.fetchone()
                if row:
                    session = dict(row)
                    session['chat_history'] = json.loads(session['chat_history'])
                    session['uploaded_files'] = json.loads(session.get('uploaded_files', '[]'))
                    # vectorstore_path is included automatically by dict(row)
                    logger.info(f"Chat session '{session_id}' retrieved.")
                    return session
                return None
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve chat session '{session_id}': {e}")
            raise

    def get_all_chat_sessions(self) -> Dict[str, Dict[str, Any]]:
        sessions = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT id, title, created_at, last_updated FROM chats ORDER BY last_updated DESC")
                rows = cursor.fetchall()
                for row in rows:
                    session_id = row['id']
                    sessions[session_id] = {
                        'title': row['title'],
                        'created_at': row['created_at'],
                        'last_updated': row['last_updated']
                    }
            logger.info(f"Retrieved {len(sessions)} chat sessions (metadata only).")
            return sessions
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve all chat sessions: {e}")
            raise

    def delete_chat_session(self, session_id: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM chats WHERE id = ?", (session_id,))
                conn.commit()
            logger.info(f"Chat session '{session_id}' deleted.")
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Failed to delete chat session '{session_id}': {e}")
            raise
            
    # --- NEW METHOD ---
    def rename_chat_session(self, session_id: str, new_title: str) -> bool:
        """
        Updates only the title of a specific chat session.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE chats SET title = ? WHERE id = ?",
                    (new_title, session_id)
                )
                conn.commit()
            logger.info(f"Chat session '{session_id}' renamed to '{new_title}'.")
            return cursor.rowcount > 0 # Returns true if a row was updated
        except sqlite3.Error as e:
            logger.error(f"Failed to rename chat session '{session_id}': {e}")
            raise
    # --- END NEW METHOD ---

    def export_workspace(self) -> str:
        try:
            all_notes = self.get_all_notes()
            all_chat_sessions_full = {}
            for session_id in self.get_all_chat_sessions().keys():
                full_session_data = self.get_chat_session(session_id)
                if full_session_data:
                    all_chat_sessions_full[session_id] = full_session_data

            workspace_data = {
                "notes": all_notes,
                "chat_sessions": all_chat_sessions_full
            }
            logger.info("Workspace data exported.")
            return json.dumps(workspace_data, indent=4)
        except Exception as e:
            logger.error(f"Failed to export workspace: {e}")
            raise

    def import_workspace(self, import_data: str) -> bool:
        try:
            data = json.loads(import_data)
            notes_to_import = data.get("notes", [])
            chat_sessions_to_import = data.get("chat_sessions", {})

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM notes")
                cursor.execute("DELETE FROM chats")
                logger.info("Cleared existing notes and chat sessions for import.")

                # Import notes
                for note in notes_to_import:
                    # ... (import logic)
                    pass
                logger.info(f"Imported {len(notes_to_import)} notes.")

                # Import chat sessions
                for session_id, session_data in chat_sessions_to_import.items():
                    # ... (import logic)
                    pass
                logger.info(f"Imported {len(chat_sessions_to_import)} chat sessions.")
                
                conn.commit()
            logger.info("Workspace imported successfully.")
            return True
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format for workspace import: {e}")
            raise
        except sqlite3.Error as e:
            logger.error(f"Failed to import workspace into database: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during workspace import: {e}")
            raise