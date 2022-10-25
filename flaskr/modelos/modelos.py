import datetime
from email.policy import default
import enum
from sqlalchemy.sql import func
from fileinput import filename
from flask_sqlalchemy import SQLAlchemy
from marshmallow import fields, Schema
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    password = db.Column(db.String(50))
    email= db.Column(db.String(50))
    tasks = db.relationship('Task', cascade='all, delete, delete-orphan')

class EnumTaskStatus(enum.Enum):
    processed = 1
    uploaded = 2

class EnumADiccionario(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        return {"llave": value.name, "valor": value.value}

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(80))
    new_format = db.Column(db.String(50))
    timestamp= db.Column(db.DateTime, default=datetime.datetime.utcnow)
    status = db.Column(db.Enum(EnumTaskStatus), default=EnumTaskStatus.uploaded)
    id_user = db.Column(db.Integer, db.ForeignKey('user.id'))
    time_file_processed = db.Column(db.DateTime, default = None, nullable = True)
    
class UserSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = User
        include_relationships = True
        load_instance = True

class TaskSchema(SQLAlchemyAutoSchema):
    status =  EnumADiccionario(attribute=("status"))
    class Meta:
        model = Task
        include_relationships = True
        load_instance = True
        

   



    