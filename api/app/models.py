from datetime import datetime
import bcrypt

def define_models(db):
    """Define all models with the given db instance"""
    
    class UserRole:
        ADMIN = 'ADMIN'
        USER = 'USER'

    class DocumentStatus:
        UPLOADED = 'uploaded'
        PROCESSING = 'processing'
        COMPLETED = 'completed'
        ERROR = 'error'

    class User(db.Model):
        __tablename__ = 'user'
        
        id = db.Column(db.Integer, primary_key=True)
        email = db.Column(db.String(120), unique=True, nullable=False)
        password_hash = db.Column(db.String(255), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        role = db.Column(db.Enum('ADMIN', 'USER', name='userrole'), default='USER')
        is_active = db.Column(db.Boolean, default=True)
        
        # Relationships
        documents = db.relationship('Document', backref='user', lazy=True)
        processing_rules = db.relationship('ProcessingRule', backref='user', lazy=True)
        
        def set_password(self, password):
            """Hash and set the user's password"""
            self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        def check_password(self, password):
            """Check if the provided password matches the stored hash"""
            return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
        
        def has_role(self, role):
            """Check if user has a specific role"""
            return self.role == role
        
        def is_admin(self):
            """Check if user is an admin"""
            return self.role == 'ADMIN'
        
        def to_dict(self):
            return {
                'id': self.id,
                'email': self.email,
                'role': self.role,
                'is_active': self.is_active,
                'created_at': self.created_at.isoformat() if self.created_at else None
            }

    class Document(db.Model):
        __tablename__ = 'document'
        
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        filename = db.Column(db.String(255), nullable=False)
        original_filename = db.Column(db.String(255), nullable=False)
        file_path = db.Column(db.String(500), nullable=False)
        file_size = db.Column(db.Integer, nullable=False)
        status = db.Column(db.Enum('uploaded', 'processing', 'completed', 'error', name='documentstatus'), default='uploaded')
        uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
        processed_at = db.Column(db.DateTime)
        output_path = db.Column(db.String(500))
        final_file_path = db.Column(db.String(500))  # Path to final document after apply-accepted
        error_message = db.Column(db.Text)
        
        def to_dict(self):
            return {
                'id': self.id,
                'user_id': self.user_id,
                'filename': self.filename,
                'original_filename': self.original_filename,
                'file_path': self.file_path,
                'file_size': self.file_size,
                'status': self.status,
                'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
                'processed_at': self.processed_at.isoformat() if self.processed_at else None,
                'output_path': self.output_path,
                'final_file_path': self.final_file_path,
                'error_message': self.error_message
            }

    class ProcessingRule(db.Model):
        __tablename__ = 'processing_rule'
        
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        name = db.Column(db.String(255), nullable=False)
        instruction = db.Column(db.Text, nullable=False)
        category = db.Column(db.String(100), nullable=False)
        is_active = db.Column(db.Boolean, default=True)
        is_global = db.Column(db.Boolean, default=False, nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        
        def to_dict(self):
            return {
                'id': self.id,
                'user_id': self.user_id,
                'name': self.name,
                'instruction': self.instruction,
                'category': self.category,
                'is_active': self.is_active,
                'is_global': self.is_global,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None
            }

    class ProcessingJob(db.Model):
        __tablename__ = 'processing_job'
        
        id = db.Column(db.Integer, primary_key=True)
        document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=False)
        status = db.Column(db.String(50), default='pending')
        started_at = db.Column(db.DateTime, default=datetime.utcnow)
        completed_at = db.Column(db.DateTime)
        error_message = db.Column(db.Text)
        
        def to_dict(self):
            return {
                'id': self.id,
                'document_id': self.document_id,
                'status': self.status,
                'started_at': self.started_at.isoformat() if self.started_at else None,
                'completed_at': self.completed_at.isoformat() if self.completed_at else None,
                'error_message': self.error_message
            }
    
    # Return the model classes
    return User, Document, ProcessingRule, ProcessingJob, UserRole, DocumentStatus
