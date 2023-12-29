import logging
import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from src.controllers.bridge_controller import bapi
from src.config.database import initialize_db

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
MONGODB_NAME = os.environ.get("MONGODB_NAME")
LOG_FILE_PATH = "./app.log"  # Path to the log file


app = Flask(__name__)
app.register_blueprint(bapi, url_prefix='/bapi')
app.config['MONGODB_URI'] = DATABASE_URL
app.config['MONGODB_NAME'] = MONGODB_NAME
initialize_db(app)

CORS(app, resources={r"/*": {"origins": "*", "allow_headers": "*"}})
# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)
file_handler = logging.FileHandler(LOG_FILE_PATH)
logger.addHandler(file_handler)


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


@app.route("/ping")
def ping():
    return "pong"


if __name__ == "__main__":
    app.run()
