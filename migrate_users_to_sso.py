import sqlite3
import uuid

# Define Database Paths
MINDSTACK_DB_PATH = r'C:\Code\MindStack\database\mindstack_new.db'
SSO_DB_PATH = r'C:\Code\CentralAuth\sso_auth.db'

def migrate_users():
    print(f"[*] Connecting to MindStack DB at {MINDSTACK_DB_PATH}")
    mindstack_conn = sqlite3.connect(MINDSTACK_DB_PATH)
    mindstack_cursor = mindstack_conn.cursor()

    print(f"[*] Connecting to Central SSO DB at {SSO_DB_PATH}")
    sso_conn = sqlite3.connect(SSO_DB_PATH)
    sso_cursor = sso_conn.cursor()

    try:
        # Extract existing MindStack users
        mindstack_cursor.execute(
            "SELECT user_id, username, email, password_hash, central_auth_id FROM users"
        )
        users = mindstack_cursor.fetchall()
        
        migrated_count = 0
        skipped_count = 0

        for user_id, username, email, password_hash, central_auth_id in users:
            # Skip if already migrated
            if central_auth_id is not None:
                print(f"[~] Skipped user {username} (already has central_auth_id)")
                skipped_count += 1
                continue

            # Generate new UUID for SSO
            new_sso_id = str(uuid.uuid4())
            
            try:
                # Insert shadow record equivalent into SSO database
                # Defaulting full_name to their current username to begin with
                sso_cursor.execute(
                    """
                    INSERT INTO users (id, email, password_hash, full_name, is_active, created_at) 
                    VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                    """,
                    (new_sso_id, email, password_hash, username)
                )
                
                # Update MindStack to establish linking
                mindstack_cursor.execute(
                    "UPDATE users SET central_auth_id = ? WHERE user_id = ?",
                    (new_sso_id, user_id)
                )
                
                print(f"[+] Migrated user: {username} ({email}) -> {new_sso_id}")
                migrated_count += 1
                
            except sqlite3.IntegrityError as e:
                print(f"[-] Failed to migrate {username} ({email}): {e} (Likely email already exists in SSO)")
                continue
                
        # Commit transactions across both databases
        sso_conn.commit()
        mindstack_conn.commit()
        
        print("\n=== Migration Summary ===")
        print(f"Total processed: {len(users)}")
        print(f"Successfully migrated: {migrated_count}")
        print(f"Skipped existing: {skipped_count}")

    except Exception as e:
        print(f"[!] Critical Error during migration: {e}")
        sso_conn.rollback()
        mindstack_conn.rollback()
        
    finally:
        # Safely shut down database connections
        mindstack_conn.close()
        sso_conn.close()

if __name__ == "__main__":
    migrate_users()
