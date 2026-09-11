from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/', defaults={'path': ''}, methods=['GET'])
@app.route('/<path:path>', methods=['GET'])
def health_handler(path=''):
    return jsonify({"status": "healthy", "service": "employee-directory-portal"}), 200

application = app
handler = app
