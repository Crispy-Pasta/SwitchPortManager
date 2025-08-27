
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    floors = db.relationship('Floor', backref='site', lazy=True, cascade="all, delete-orphan")

class Floor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False)
    switches = db.relationship('Switch', backref='floor', lazy=True, cascade="all, delete-orphan")

class Switch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    ip_address = db.Column(db.String(100), unique=True, nullable=False)
    model = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    enabled = db.Column(db.Boolean, default=True)
    floor_id = db.Column(db.Integer, db.ForeignKey('floor.id'), nullable=False)

def init_db(app):
    """Initialize database with app context."""
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")

def get_db_connection():
    """Get database connection (for compatibility)."""
    return db

