import sqlite3
import uuid
import os
from datetime import datetime, timezone

# Database paths
MINDSTACK_DB = r"c:\Code\Ecosystem\Storage\database\Mindstack.db"
CENTRAL_AUTH_DB = r"c:\Code\Ecosystem\Storage\database\CentralAuth.db"

def sync_users():
    print("Starting user synchronization...")
    
    if not os.path.exists(MINDSTACK_DB):
        print(f"Error: Mindstack database not found at {MINDSTACK_DB}")
        return
    if not os.path.exists(CENTRAL_AUTH_DB):
        print(f"Error: CentralAuth database not found at {CENTRAL_AUTH_DB}")
        return

    # Connect to databases
    m_conn = sqlite3.connect(MINDSTACK_DB)
    c_conn = sqlite3.connect(CENTRAL_AUTH_DB)
    m_cursor = m_conn.cursor()
    c_cursor = c_conn.cursor()

    try:
        # 1. Clear CentralAuth users (except possibly preserve nothing as requested to replace admin)
        print("Cleaning CentralAuth users table...")
        c_cursor.execute("DELETE FROM users")
        c_cursor.execute("DELETE FROM audit_logs") # Clear logs to stay clean
        
        # 2. Fetch MindStack users
        m_cursor.execute("SELECT user_id, username, email, password_hash, avatar_url FROM users ORDER BY user_id")
        m_users = m_cursor.fetchall()
        print(f"Found {len(m_users)} users in MindStack.")

        for i, (m_id, m_username, m_email, m_password_hash, m_avatar_url) in enumerate(m_users):
            # 3. Prepare CentralAuth data
            c_uuid = str(uuid.uuid4())
            
            # Map first user to 'admin' username in CentralAuth
            final_username = "admin" if i == 0 else m_username
            full_name = m_username # Using username as full_name since MindStack lacks it
            created_at = datetime.now(timezone.utc).isoformat()
            
            print(f"Syncing user: {m_username} -> {final_username} (UUID: {c_uuid})")
            
            # 4. Insert into CentralAuth
            c_cursor.execute("""
                INSERT INTO users (id, username, email, password_hash, full_name, avatar_url, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (c_uuid, final_username, m_email, m_password_hash, full_name, m_avatar_url, 1, created_at))
            
            # 5. Link back to MindStack
            m_cursor.execute("UPDATE users SET central_auth_id = ? WHERE user_id = ?", (c_uuid, m_id))

        # 6. Commit changes
        c_conn.commit()
        m_conn.commit()
        print("Synchronization completed successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")
        c_conn.rollback()
        m_conn.rollback()
    finally:
        m_conn.close()
        c_conn.close()

if __name__ == "__main__":
    sync_users()
