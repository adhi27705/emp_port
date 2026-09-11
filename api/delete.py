import os
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

UPLOAD_FOLDER = '/tmp/uploads'
SQLITE_DB_PATH = '/tmp/employees.db'

# Database Configuration (Supabase PostgreSQL or SQLite fallback)
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL') or os.getenv('SUPABASE_DATABASE_URL')

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

USE_POSTGRES = bool(PSYCOPG2_AVAILABLE and DATABASE_URL and ('postgres' in DATABASE_URL or 'supabase' in DATABASE_URL))


def get_db_connection():
    global USE_POSTGRES
    if USE_POSTGRES:
        try:
            pg_url = DATABASE_URL
            if pg_url.startswith('postgres://'):
                pg_url = pg_url.replace('postgres://', 'postgresql://', 1)
            if 'sslmode' not in pg_url:
                separator = '&' if '?' in pg_url else '?'
                pg_url = f"{pg_url}{separator}sslmode=require"
            conn = psycopg2.connect(pg_url, connect_timeout=4)
            return conn, True
        except Exception as e:
            print(f"PostgreSQL connection warning: {e}. Falling back to SQLite.")
            USE_POSTGRES = False

    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn, False


@app.route('/', defaults={'path': ''}, methods=['POST', 'DELETE', 'GET', 'OPTIONS'])
@app.route('/<path:path>', methods=['POST', 'DELETE', 'GET', 'OPTIONS'])
def delete_handler(path=''):
    if request.method == 'OPTIONS':
        return ('', 204, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        })

    # Extract ID from path, json, form, or query param
    emp_id = None
    clean_path = path.strip('/')
    if clean_path and clean_path.isdigit():
        emp_id = int(clean_path)

    if not emp_id:
        data = request.get_json(silent=True) or request.form or {}
        emp_id = data.get('id') or request.args.get('id')

    if not emp_id:
        return jsonify({"error": "Employee ID is required."}), 400

    try:
        emp_id = int(emp_id)
    except ValueError:
        return jsonify({"error": "Invalid employee ID."}), 400

    try:
        conn, is_pg = get_db_connection()
        photo_path = None

        if is_pg:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT photo_path FROM employees WHERE id = %s", (emp_id,))
                row = cur.fetchone()
                if not row:
                    conn.close()
                    return jsonify({"error": "Employee not found."}), 404
                photo_path = row['photo_path']

                cur.execute("DELETE FROM employees WHERE id = %s", (emp_id,))
                conn.commit()
            conn.close()
        else:
            cur = conn.execute("SELECT photo_path FROM employees WHERE id = ?", (emp_id,))
            row = cur.fetchone()
            if not row:
                conn.close()
                return jsonify({"error": "Employee not found."}), 404
            photo_path = row['photo_path']

            with conn:
                conn.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
            conn.close()

        # Clean up custom uploaded file if applicable
        if photo_path and photo_path.startswith('/static/uploads/'):
            filename = photo_path.replace('/static/uploads/', '')
            file_disk_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.exists(file_disk_path):
                try:
                    os.remove(file_disk_path)
                except Exception as file_err:
                    print(f"File cleanup warning: {file_err}")

        return jsonify({
            "success": True,
            "message": "Employee deleted successfully.",
            "id": emp_id
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to delete employee: {str(e)}"}), 500


application = app
handler = app

if __name__ == '__main__':
    app.run(port=5004, debug=True)
