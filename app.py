#!/usr/bin/env python3
"""
Flask application wrapper for gunicorn
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Create the base model class
class Base(DeclarativeBase):
    pass

# Initialize the SQLAlchemy object
db = SQLAlchemy(model_class=Base)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "sarya_dev_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Import models and modules after initializing db to avoid circular imports
with app.app_context():
    from main import *  # Import routes and other configurations
    db.create_all()  # Create database tables

# This file is used by gunicorn to run the Flask app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)