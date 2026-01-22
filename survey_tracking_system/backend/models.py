import os
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        """Hash and set user password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)
    
    def is_superadmin(self):
        """Check if user has superadmin role."""
        return self.role == 'superadmin'
    
    def is_admin(self):
        """Check if user has admin or superadmin role."""
        return self.role in ['admin', 'superadmin']
    
    def get_id(self):
        """Return user id as string (required by Flask-Login)."""
        return str(self.id)
    
    def to_dict(self):
        """Convert user to dictionary (excluding password hash)."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    def __repr__(self):
        return f'<User {self.username}>'


def init_db(app):
    """Initialize database with the Flask app."""
    db.init_app(app)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create superadmin user if it doesn't exist
        create_superadmin_user()


def create_superadmin_user():
    """Create the default superadmin user if it doesn't exist."""
    superadmin = User.query.filter_by(username='admin').first()
    
    if not superadmin:
        superadmin = User(
            username='admin',
            email='lmabena@nsa.org.na',
            role='superadmin'
        )
        superadmin.set_password('Amazing@2001')
        
        db.session.add(superadmin)
        db.session.commit()
        print(f"Created superadmin user: {superadmin.username}")
    else:
        print(f"Superadmin user already exists: {superadmin.username}")