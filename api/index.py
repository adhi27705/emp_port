import os
import uuid
import sqlite3
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename

# Determine root directories for templates and static assets
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

# Support multiple environments (local and Vercel serverless bundle)
template_candidates = [
    os.path.join(CURRENT_DIR, 'templates'),
    os.path.join(ROOT_DIR, 'app', 'templates'),
    os.path.join(ROOT_DIR, 'templates'),
    CURRENT_DIR
]
TEMPLATE_DIR = next((p for p in template_candidates if os.path.exists(p)), CURRENT_DIR)

static_candidates = [
    os.path.join(CURRENT_DIR, 'static'),
    os.path.join(ROOT_DIR, 'app', 'static'),
    os.path.join(ROOT_DIR, 'static'),
    CURRENT_DIR
]
STATIC_DIR = next((p for p in static_candidates if os.path.exists(p)), CURRENT_DIR)

# Create Flask application at top-level
app = Flask(
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR,
    static_url_path='/static'
)

# Vercel serverless writable paths (/tmp)
UPLOAD_FOLDER = '/tmp/uploads'
SQLITE_DB_PATH = '/tmp/employees.db'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
app.config['TEMPLATES_AUTO_RELOAD'] = True

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


def get_db_connection():
    global USE_POSTGRES
    if USE_POSTGRES:
        try:
            # Fix postgres:// URI prefix for newer psycopg2 if needed
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
                cur.execute("SELECT COUNT(*) FROM employees")
                if cur.fetchone()[0] == 0:
                    cur.executemany("""
                        INSERT INTO employees (name, role, department, email, photo_path)
                        VALUES (%s, %s, %s, %s, %s)
                    """, [
                        ('Sarah Connor', 'Principal Site Reliability Engineer', 'Engineering', 'sarah.connor@cyberdyne.internal', '/static/img/avatar-sarah.svg'),
                        ('Alex Chen', 'Lead UI/UX Designer', 'Design', 'alex.chen@designlab.internal', '/static/img/avatar-alex.svg'),
                        ('Marcus Vance', 'Cloud Infrastructure Architect', 'Engineering', 'marcus.v@cloudops.internal', '/static/img/avatar-marcus.svg'),
                        ('Priya Patel', 'Head of People Operations', 'Human Resources', 'priya.patel@workplace.internal', '/static/img/avatar-priya.svg'),
                        ('Elena Rostova', 'Senior DevOps Engineer', 'Engineering', 'elena.rostova@devops.internal', '/static/img/avatar-elena.svg'),
                        ('Liam Tanaka', 'Staff Product Manager', 'Product', 'liam.tanaka@product.internal', '/static/img/avatar-liam.svg')
                    ])
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
                cur = conn.execute("SELECT COUNT(*) FROM employees")
                if cur.fetchone()[0] == 0:
                    conn.executemany("""
                        INSERT INTO employees (name, role, department, email, photo_path)
                        VALUES (?, ?, ?, ?, ?)
                    """, [
                        ('Sarah Connor', 'Principal Site Reliability Engineer', 'Engineering', 'sarah.connor@cyberdyne.internal', '/static/img/avatar-sarah.svg'),
                        ('Alex Chen', 'Lead UI/UX Designer', 'Design', 'alex.chen@designlab.internal', '/static/img/avatar-alex.svg'),
                        ('Marcus Vance', 'Cloud Infrastructure Architect', 'Engineering', 'marcus.v@cloudops.internal', '/static/img/avatar-marcus.svg'),
                        ('Priya Patel', 'Head of People Operations', 'Human Resources', 'priya.patel@workplace.internal', '/static/img/avatar-priya.svg'),
                        ('Elena Rostova', 'Senior DevOps Engineer', 'Engineering', 'elena.rostova@devops.internal', '/static/img/avatar-elena.svg'),
                        ('Liam Tanaka', 'Staff Product Manager', 'Product', 'liam.tanaka@product.internal', '/static/img/avatar-liam.svg')
                    ])
            conn.close()
    except Exception as e:
        print(f"DB Init Warning: {e}")


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/health')
@app.route('/api/health')
@app.route('/api/index/health')
def health():
    return jsonify({"status": "healthy", "service": "employee-directory-portal"}), 200


@app.before_request
def vercel_request_dispatcher():
    endpoint = (request.args.get('__endpoint') or '').lower()
    raw_path = request.path.lower()
    matched = (request.headers.get('x-matched-path') or 
               request.headers.get('x-now-route-matches') or
               request.environ.get('HTTP_X_MATCHED_PATH') or
               request.environ.get('HTTP_X_FORWARDED_URI') or
               request.environ.get('HTTP_X_VERCEL_PATH') or '').lower()

    if (endpoint == 'search' or 
        raw_path.endswith('/search') or 
        'search' in matched or 
        'q' in request.args or 
        ('dept' in request.args and request.args.get('dept') != '')):
        return search()

    if (endpoint == 'register' or 
        raw_path.endswith('/register') or 
        'register' in matched):
        return register()

    if (endpoint == 'delete' or 
        raw_path.endswith('/delete') or 
        'delete' in matched):
        return delete_employee()

    if (endpoint.startswith('auth') or 
        '/auth' in raw_path or 
        '/auth' in matched or 
        raw_path.endswith('/login') or 
        raw_path.endswith('/logout')):
        return auth_endpoint()

    if (endpoint == 'health' or 
        raw_path.endswith('/health') or 
        'health' in matched):
        return health()

    return None


@app.route('/static/uploads/<path:filename>')
@app.route('/uploads/<path:filename>')
def serve_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/')
@app.route('/api')
@app.route('/api/index')
@app.route('/api/index.py')
def index():
    init_db()
    endpoint = (request.args.get('__endpoint') or '').lower()
    raw_path = request.path.lower()
    matched = (request.headers.get('x-matched-path') or 
               request.headers.get('x-now-route-matches') or
               request.environ.get('HTTP_X_MATCHED_PATH') or
               request.environ.get('HTTP_X_FORWARDED_URI') or
               request.environ.get('HTTP_X_VERCEL_PATH') or '').lower()

    if (endpoint == 'search' or 'search' in raw_path or 'search' in matched or 
        'q' in request.args or ('dept' in request.args and request.args.get('dept') != '')):
        return search()
    if (endpoint == 'register' or 'register' in raw_path or 'register' in matched or 
        request.method == 'POST' or request.files):
        return register()
    if (endpoint == 'health' or 'health' in raw_path or 'health' in matched):
        return health()

    try:
        return render_template('index.html')
    except Exception:
        # Robust fallback: directly read index.html if Jinja loader encounters packaging issues in Lambda
        for p in [
            os.path.join(TEMPLATE_DIR, 'index.html'),
            os.path.join(CURRENT_DIR, 'templates', 'index.html'),
            os.path.join(CURRENT_DIR, 'index.html'),
            os.path.join(ROOT_DIR, 'public', 'index.html'),
            os.path.join(ROOT_DIR, 'app', 'templates', 'index.html')
        ]:
            if os.path.exists(p):
                with open(p, 'r', encoding='utf-8') as f:
                    return f.read(), 200, {'Content-Type': 'text/html; charset=utf-8'}
        raise


@app.route('/search', methods=['GET'])
@app.route('/api/search', methods=['GET'])
@app.route('/api/index/search', methods=['GET'])
def search():
    init_db()
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

        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": f"Search failed: {str(e)}"}), 500


@app.route('/register', methods=['POST'])
@app.route('/api/register', methods=['POST'])
@app.route('/api/index/register', methods=['POST'])
def register():
    init_db()
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


ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')


@app.route('/delete', methods=['POST', 'DELETE'])
@app.route('/api/delete', methods=['POST', 'DELETE'])
def delete_employee():
    init_db()
    data = request.get_json(silent=True) or request.form or {}
    emp_id = data.get('id') or request.args.get('id')
    if not emp_id:
        return jsonify({"error": "Employee ID is required."}), 400

    try:
        emp_id = int(emp_id)
        conn, is_pg = get_db_connection()
        if is_pg:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT photo_path FROM employees WHERE id = %s", (emp_id,))
                row = cur.fetchone()
                if not row:
                    conn.close()
                    return jsonify({"error": "Employee not found."}), 404
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

        return jsonify({"success": True, "message": "Employee deleted successfully.", "id": emp_id}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete employee: {str(e)}"}), 500


@app.route('/auth/login', methods=['POST'])
@app.route('/api/auth/login', methods=['POST'])
@app.route('/login', methods=['POST'])
@app.route('/auth/logout', methods=['POST'])
@app.route('/api/auth/logout', methods=['POST'])
@app.route('/logout', methods=['POST'])
@app.route('/auth/status', methods=['GET'])
@app.route('/api/auth/status', methods=['GET'])
def auth_endpoint():
    path = request.path.lower()
    if 'logout' in path:
        return jsonify({"success": True, "message": "Logged out successfully"}), 200
    if 'status' in path:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header[7:].strip() if auth_header.startswith('Bearer ') else (request.args.get('token') or '')
        if token and token.startswith('admin-token-'):
            return jsonify({"authenticated": True, "user": {"username": ADMIN_USERNAME, "role": "Administrator"}}), 200
        return jsonify({"authenticated": False}), 200

    data = request.get_json(silent=True) or request.form or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        token = f"admin-token-{uuid.uuid4().hex}"
        return jsonify({
            "success": True,
            "message": "Login successful",
            "token": token,
            "user": {"username": username, "role": "Administrator"}
        }), 200
    return jsonify({"success": False, "error": "Invalid username or password."}), 401


@app.errorhandler(404)
def handle_not_found(e):
    matched = (request.headers.get('x-matched-path') or 
               request.headers.get('x-now-route-matches') or
               request.environ.get('HTTP_X_MATCHED_PATH') or
               request.environ.get('HTTP_X_FORWARDED_URI') or '').lower()
    path = request.path.lower()

    if (matched.startswith('/search') or path.startswith(('/search', '/api/search', '/api/index/search')) or 
            'q' in request.args or 'dept' in request.args):
        return search()
    if matched.startswith('/register') or path.startswith(('/register', '/api/register', '/api/index/register')) or request.method == 'POST':
        return register()
    if matched.startswith('/health') or path.startswith(('/health', '/api/health', '/api/index/health')):
        return health()
    return index()


# Top-level handler aliases expected by Vercel serverless runtime
application = app
handler = app

if __name__ == '__main__':
    app.run(port=5000, debug=True)
