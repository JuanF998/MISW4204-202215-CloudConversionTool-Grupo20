from ast import Str
from email.mime import audio
from fileinput import filename
import os
from flask import request, abort
from flask_jwt_extended import jwt_required, create_access_token, get_jwt, get_jwt_identity, JWTManager
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError
from flask import jsonify
from werkzeug.utils import secure_filename
import time

from modelos import db, User, UserSchema, Task, EnumTaskStatus, TaskSchema

user_schema = UserSchema()
task_schema = TaskSchema()

class VistaSignUp(Resource):

    def post(self):
        
        if (User.query.filter(User.username == request.json["username"]).first() == None):
            if (User.query.filter(User.email == request.json["email"]).first() == None):
                if (request.json["password1"] == request.json["password2"]):
                    new_user = User(username=request.json["username"], password=request.json["password1"], email=request.json[
                                                "email"])
                    db.session.add(new_user)
                    db.session.commit()
                    return {"mensaje": "Usuario creado exitosamente", "id": new_user.id}
                else:
                    return 'Los passwords deben ser iguales!', 400
            else:
                return 'Intente registrarse con un correo de usuario diferente!', 400
        else:
            return 'Intente registrarse con un nombre de usuario diferente!', 400


class VistaLogIn(Resource):

    def post(self):
        user = User.query.filter(User.username == request.json["username"],
                                           User.password == request.json["password"]).first()
        db.session.commit()
        if user is None:
            return "Credenciales incorrectas!", 404
        else:
            token_de_acceso = create_access_token(identity=user.id)
            return {"mensaje": "Inicio de sesión exitoso!", "token": token_de_acceso}


class VistaTasks(Resource):
    @jwt_required()
    def post(self):
        PATH_FILES = os.getcwd() + "\\files\\"
        id_user = get_jwt_identity()
        print(PATH_FILES)
        # You should change 'test' to your preferred folder.
        MYDIR = (str(id_user))
        user_folder = PATH_FILES + '\\' + str(id_user)
        CHECK_FOLDER = os.path.exists(user_folder)

        # If folder doesn't exist, then create it.
        if not CHECK_FOLDER:
            os.makedirs(user_folder)
            print("created folder : ", user_folder)

        else:
            print(user_folder, "folder already exists.")
        audio_file = request.files["file"]
        file_path = user_folder + '\\' + str(time.time())+'_'+ audio_file.filename
        audio_file.save(file_path)

                
                
        # filename = request.json.get("filename")
        # new_format = request.json.get("new_format")
        
        # if filename is None or len(filename) < 1:
        #     return "Parametros de archivo invalidos!", 400
        # elif new_format is None or len(filename) < 1:
        #     return "Ingrese un formato de archivo valido!", 400
        # else:
        #     new_task = Task(filename = filename, new_format = new_format, id_user = id_user)
        #     db.session.add(new_task)
        #     db.session.commit()
            
        #     return task_schema.dump(new_task)


    @jwt_required()
    def get(self):
        id_user = get_jwt_identity()
        max = request.json.get("max")
        order = request.json.get("order")
        tasks = Task.query.filter(Task.id_user == id_user).all()[0:max]
        if order:
            tasks = tasks[::-1]
 
        return [ task_schema.dump(task) for task in tasks ]

    
    




