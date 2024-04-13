
import sqlite3
import json
import uuid
import db.dbconn as dbconn
def store_activity_log(payload,image_list):
    try:
        conn = dbconn.activity_database()
        cur = conn.cursor()
        id_uuid = str(uuid.uuid4())
        cur.execute(f"""
            INSERT INTO activity_logs VALUES (
                    '{id_uuid}',
                    '{payload['fk_project']}', 
                    '{payload['fk_todo']}', 
                    '{payload['date']}', 
                    '{payload['start_time']}', 
                    '{payload['end_time']}', 
                    '{payload['duration']}', 
                    '{payload['idle_time']}', 
                    '{json.dumps(payload['screen_activity'])}',
                    
                    '{json.dumps(image_list)}'
                )
        """
        )
        conn.commit()
        conn.close()
        return "done"
    except sqlite3.Error as error:
        print("Error storing activity log:", error)
    except Exception as e:
        print(f"Error: {e}")
