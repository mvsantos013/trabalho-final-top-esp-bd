import os
import traceback
from flask import Flask, jsonify, request as req
from flask_cors import CORS
import service

ENV = os.environ.get('STAGE')

app = Flask(__name__)
CORS(app)
app.config['JSON_SORT_KEYS'] = False

# Returns a error in a standard way if endpoint crashes.
@app.errorhandler(Exception)
def handle_exception(e):
    print(traceback.format_exc())
    return jsonify({'error': str(e)}), 500


# Register routes
app.register_blueprint(service.blueprint)

# Ignore this route
@app.route('/favicon.ico')
def favicon():
    return ''