import os
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

# Database Configuration (Supabase PostgreSQL or SQLite fallback)
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL') or os.getenv('SUPABASE_DATABASE_URL')
SQLITE_DB_PATH = '/tmp/employees.db'

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


@app.route('/', defaults={'path': ''}, methods=['GET'])
@app.route('/<path:path>', methods=['GET'])
def search_handler(path=''):
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
        sql_query = f"SELECT id, name, role, department, email, photo_path FROM employees {where_clause} ORDER BY id ASC"

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

        return jsonify(results), 200, {'Content-Type': 'application/json'}
    except Exception as e:
        return jsonify({"error": f"Search failed: {str(e)}"}), 500, {'Content-Type': 'application/json'}


application = app
handler = app

if __name__ == '__main__':
    app.run(port=5001, debug=True)
