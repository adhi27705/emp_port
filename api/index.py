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


def get_db_connection():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    try:
        conn = get_db_connection()
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
        conn = get_db_connection()
        conditions = []
        params = []

        if query:
            search_param = f"%{query}%"
            conditions.append("(name LIKE ? OR role LIKE ? OR department LIKE ? OR email LIKE ?)")
            params.extend([search_param, search_param, search_param, search_param])

        if dept and dept.lower() != 'all':
            conditions.append("department = ?")
            params.append(dept)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql_query = f"SELECT id, name, role, department, email, photo_path FROM employees {where_clause} ORDER BY id DESC"

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
        conn = get_db_connection()
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
        if "UNIQUE" in str(e).upper():
            return jsonify({"error": "An employee with this email already exists."}), 409
        return jsonify({"error": f"Failed to save employee: {str(e)}"}), 500


@app.errorhandler(404)
def handle_not_found(e):
    # Graceful fallback for single-page routing or rewritten paths
    if request.path.startswith(('/search', '/api/search', '/api/index/search')):
        return search()
    return index()


# Top-level handler aliases expected by Vercel serverless runtime
application = app
handler = app

if __name__ == '__main__':
    app.run(port=5000, debug=True)
