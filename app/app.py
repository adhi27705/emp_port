import os
import time
import uuid
import sqlite3
# pyrefly: ignore [missing-import]
from flask import Flask, request, jsonify, render_template, send_from_directory
# pyrefly: ignore [missing-import]
from werkzeug.utils import secure_filename

# Try importing psycopg2 for PostgreSQL in Docker/Production
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

app = Flask(__name__)

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Upload Configuration
# In Docker, UPLOAD_FOLDER is set to /uploads. Locally, fallback to app/static/uploads.
DEFAULT_LOCAL_UPLOADS = os.path.join(BASE_DIR, 'static', 'uploads')
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', DEFAULT_LOCAL_UPLOADS)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
# Determine if PostgreSQL should be used
USE_POSTGRES = bool(PSYCOPG2_AVAILABLE and DATABASE_URL and DATABASE_URL.startswith('postgres'))
SQLITE_DB_PATH = os.path.join(BASE_DIR, 'employees.db')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB upload limit
app.config['TEMPLATES_AUTO_RELOAD'] = True

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db_connection():
    """Establish and return database connection (PostgreSQL or SQLite fallback)."""
    global USE_POSTGRES
    if USE_POSTGRES:
        retries = 3
        while retries > 0:
            try:
                conn = psycopg2.connect(DATABASE_URL)
                return conn, True
            except Exception as err:
                retries -= 1
                time.sleep(1)
        print("PostgreSQL connection failed. Falling back to local SQLite database.")
        USE_POSTGRES = False

    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn, False


def init_db():
    """Ensure the employees table exists upon startup and seed starter data."""
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
            print("PostgreSQL database schema verified successfully.")
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
                # Seed initial employees if empty or update placeholders
                starter_employees = [
                    ('Sarah Connor', 'Principal Site Reliability Engineer', 'Engineering', 'sarah.connor@cyberdyne.internal', '/static/img/avatar-sarah.svg'),
                    ('Alex Chen', 'Lead UI/UX Designer', 'Design', 'alex.chen@designlab.internal', '/static/img/avatar-alex.svg'),
                    ('Marcus Vance', 'Cloud Infrastructure Architect', 'Engineering', 'marcus.v@cloudops.internal', '/static/img/avatar-marcus.svg'),
                    ('Priya Patel', 'Head of People Operations', 'Human Resources', 'priya.patel@workplace.internal', '/static/img/avatar-priya.svg'),
                    ('Elena Rostova', 'Senior DevOps Engineer', 'Engineering', 'elena.rostova@devops.internal', '/static/img/avatar-elena.svg'),
                    ('Liam Tanaka', 'Staff Product Manager', 'Product', 'liam.tanaka@product.internal', '/static/img/avatar-liam.svg')
                ]
                cur = conn.execute("SELECT COUNT(*) FROM employees")
                if cur.fetchone()[0] == 0:
                    conn.executemany("""
                        INSERT INTO employees (name, role, department, email, photo_path)
                        VALUES (?, ?, ?, ?, ?)
                    """, starter_employees)
                else:
                    # Update avatars for existing starter employees
                    for name, role, dept, email, photo in starter_employees:
                        conn.execute("""
                            INSERT INTO employees (name, role, department, email, photo_path)
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT(email) DO UPDATE SET 
                                photo_path = excluded.photo_path,
                                role = excluded.role,
                                department = excluded.department
                        """, (name, role, dept, email, photo))
            conn.close()
            print("SQLite local database initialized and seeded with rich avatars successfully.")
    except Exception as e:
        print(f"Schema initialization warning: {e}")


# Initialize table on startup
init_db()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/health')
def health():
    """Healthcheck endpoint for orchestrators."""
    return jsonify({"status": "healthy", "service": "employee-directory"}), 200


@app.route('/static/uploads/<path:filename>')
def serve_uploaded_file(filename):
    """
    Fallback route for serving uploaded photos directly in local standalone mode.
    Note: Under Docker Compose, Nginx intercepts /static/uploads/ directly for maximum performance.
    """
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/')
def index():
    """Render the employee portal page."""
    try:
        conn, is_pg = get_db_connection()
        if is_pg:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, name, role, department, email, photo_path FROM employees ORDER BY id DESC")
                employees = [dict(row) for row in cur.fetchall()]
            conn.close()
        else:
            with conn:
                cur = conn.execute("SELECT id, name, role, department, email, photo_path FROM employees ORDER BY id DESC")
                employees = [dict(row) for row in cur.fetchall()]
            conn.close()
    except Exception as e:
        employees = []
        print(f"Error fetching initial employees: {e}")
    return render_template('index.html', employees=employees)


@app.route('/search', methods=['GET'])
def search():
    """
    Search employees via case-insensitive SQL query.
    Uses PostgreSQL ILIKE in container and SQLite LIKE locally.
    Supports search query 'q' and optional department filter 'dept'.
    """
    query = request.args.get('q', '').strip()
    dept = request.args.get('dept', '').strip()
    try:
        conn, is_pg = get_db_connection()
        like_operator = "ILIKE" if is_pg else "LIKE"
        search_param = f"%{query}%"

        conditions = []
        params = []

        if query:
            ph = "%s" if is_pg else "?"
            conditions.append(f"(name {like_operator} {ph} OR role {like_operator} {ph} OR department {like_operator} {ph} OR email {like_operator} {ph})")
            params.extend([search_param, search_param, search_param, search_param])

        if dept and dept.lower() != 'all':
            ph = "%s" if is_pg else "?"
            conditions.append(f"department = {ph}")
            params.append(dept)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql_query = f"SELECT id, name, role, department, email, photo_path FROM employees {where_clause} ORDER BY id DESC"


        if is_pg:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql_query, tuple(params))
                results = [dict(row) for row in cur.fetchall()]
            conn.close()
        else:
            with conn:
                cur = conn.execute(sql_query, params)
                results = [dict(row) for row in cur.fetchall()]
            conn.close()

        print(f"[DEBUG RESULTS] Returned {len(results)} rows")
        return jsonify(results), 200

    except Exception as e:
        return jsonify({"error": f"Search failed: {str(e)}"}), 500



@app.route('/register', methods=['POST'])
def register():
    """
    Register new employee and upload profile photo.
    Saves photo to the upload directory and stores path in DB.
    """
    name = request.form.get('name', '').strip()
    role = request.form.get('role', '').strip()
    department = request.form.get('department', '').strip()
    email = request.form.get('email', '').strip()
    file = request.files.get('photo')

    if not (name and role and department and email):
        return jsonify({"error": "All fields (name, role, department, email) are required."}), 400

    photo_path = "/static/img/placeholder.svg"

    if file and file.filename != '':
        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type. Allowed: png, jpg, jpeg, gif, webp"}), 400

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
                    RETURNING id, name, role, department, email, photo_path;
                """, (name, role, department, email, photo_path))
                new_employee = dict(cur.fetchone())
                conn.commit()
            conn.close()
        else:
            with conn:
                cur = conn.execute("""
                    INSERT INTO employees (name, role, department, email, photo_path)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, role, department, email, photo_path))
                new_id = cur.lastrowid
                new_employee = {
                    "id": new_id,
                    "name": name,
                    "role": role,
                    "department": department,
                    "email": email,
                    "photo_path": photo_path
                }
            conn.close()

        return jsonify({
            "message": "Employee registered successfully",
            "employee": new_employee
        }), 201
    except Exception as e:
        if "UNIQUE" in str(e).upper() or "DUPLICATE" in str(e).upper():
            return jsonify({"error": "An employee with this email already exists."}), 409
        return jsonify({"error": f"Failed to save employee: {str(e)}"}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"\n=======================================================")
    print(f"  Employee Directory Portal is LIVE!")
    print(f"  Open in your browser: http://localhost:{port}")
    print(f"=======================================================\n")
    app.run(host='0.0.0.0', port=port, debug=False)



