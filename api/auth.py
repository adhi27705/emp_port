import os
import uuid
from flask import Flask, request, jsonify

app = Flask(__name__)

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')


def get_token_from_request():
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:].strip()
    return request.args.get('token') or request.cookies.get('auth_token', '')


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
def auth_handler(path=''):
    if request.method == 'OPTIONS':
        return ('', 204, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        })

    subpath = path.strip('/').lower()
    full_path = request.path.strip('/').lower()

    # Determine sub-action
    is_login = 'login' in subpath or full_path.endswith('login')
    is_logout = 'logout' in subpath or full_path.endswith('logout')
    is_status = 'status' in subpath or full_path.endswith('status')

    # Handle Login
    if is_login or (request.method == 'POST' and not is_logout):
        data = request.get_json(silent=True) or request.form or {}
        username = (data.get('username') or '').strip()
        password = (data.get('password') or '').strip()

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            token = f"admin-token-{uuid.uuid4().hex}"
            return jsonify({
                "success": True,
                "message": "Login successful",
                "token": token,
                "user": {
                    "username": username,
                    "role": "Administrator",
                    "badge": "Admin"
                }
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Invalid username or password."
            }), 401

    # Handle Logout
    if is_logout:
        return jsonify({
            "success": True,
            "message": "Logged out successfully"
        }), 200

    # Handle Status check
    token = get_token_from_request()
    if token and token.startswith('admin-token-'):
        return jsonify({
            "authenticated": True,
            "user": {
                "username": ADMIN_USERNAME,
                "role": "Administrator",
                "badge": "Admin"
            }
        }), 200
    else:
        return jsonify({
            "authenticated": False
        }), 200


application = app
handler = app

if __name__ == '__main__':
    app.run(port=5003, debug=True)
