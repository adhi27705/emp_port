import os
import uuid
import sqlite3
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = '/tmp/uploads'
SQLITE_DB_PATH = '/tmp/employees.db'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database Configuration (Supabase PostgreSQL or SQLite fallback)
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL') or os.getenv('SUPABASE_DATABASE_URL')

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

USE_POSTGRES = bool(PSYCOPG2_AVAILABLE and DATABASE_URL and ('postgres' in DATABASE_URL or 'supabase' in DATABASE_URL))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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


def init_db():
    try:
        conn, is_pg = get_db_connection()
        if is_pg:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS employees (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        role VARCHAR(100) NOT NULL,
                        department VARCHAR(100) NOT NULL,
                        email VARCHAR(150) UNIQUE NOT NULL,
                        photo_path VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.commit()
            conn.close()
        else:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS employees (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        role TEXT NOT NULL,
                        department TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        photo_path TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
            conn.close()
    except Exception as e:
        print(f"DB Init Warning: {e}")


@app.route('/', defaults={'path': ''}, methods=['POST', 'GET'])
@app.route('/<path:path>', methods=['POST', 'GET'])
def register_handler(path=''):
    init_db()
    if request.method == 'GET':
        return jsonify({"status": "ready", "endpoint": "register"}), 200

    name = request.form.get('name', '').strip()
    role = request.form.get('role', '').strip()
    department = request.form.get('department', '').strip()
    email = request.form.get('email', '').strip()
    file = request.files.get('photo')

    if not (name and role and department and email):
        return jsonify({"error": "All fields are required."}), 400

    photo_path = "/static/img/placeholder.svg"

    if file and file.filename != '':
        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type."}), 400

        original_ext = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename.rsplit('.', 1)[0])}.{original_ext}"
        destination_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(destination_path)
        photo_path = f"/static/uploads/{unique_filename}"

    try:
        conn, is_pg = get_db_connection()
        if is_pg:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO employees (name, role, department, email, photo_path)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id;
                """, (name, role, department, email, photo_path))
                new_id = cur.fetchone()['id']
                conn.commit()
            conn.close()
        else:
            with conn:
                cur = conn.execute("""
                    INSERT INTO employees (name, role, department, email, photo_path)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, role, department, email, photo_path))
                new_id = cur.lastrowid
            conn.close()

        new_employee = {
            "id": new_id,
            "name": name,
            "role": role,
            "department": department,
            "email": email,
            "photo_path": photo_path
        }
        return jsonify({
            "message": "Employee registered successfully",
            "employee": new_employee
        }), 201
    except Exception as e:
        if "UNIQUE" in str(e).upper():
            return jsonify({"error": "An employee with this email already exists."}), 409
        return jsonify({"error": f"Failed to save employee: {str(e)}"}), 500


application = app
handler = app

if __name__ == '__main__':
    app.run(port=5002, debug=True)
