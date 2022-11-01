from ast import Str
import datetime
from email.mime import audio
from fileinput import filename
from hashlib import new
import os
import resource
from flask import request, abort
from flask_jwt_extended import jwt_required, create_access_token, get_jwt, get_jwt_identity, JWTManager
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError
from flask import jsonify
from werkzeug.utils import secure_filename
import time
from celery import Celery
from modelos import db, User, UserSchema, Task, EnumTaskStatus, TaskSchema
from flask import send_from_directory,send_file
from sqlalchemy import asc,desc

celery_app = Celery(__name__, broker='redis://10.0.2.14:6379/0')
user_schema = UserSchema()
task_schema = TaskSchema()

@celery_app.task(name='convert_file')
def convert_file(*args):
    pass

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
        new_format = request.form["newFormat"].lower()
        audio_file = request.files["fileName"]
        original_format = audio_file.filename.split(".")[-1]
        if(original_format == "mp3" or original_format == "wav" or original_format == "ogg"):
            if(new_format == "mp3" or new_format == "wav" or new_format == "ogg"):
                PATH_FILES ="/nfs/general/files"
                id_user = get_jwt_identity()
                MYDIR = (str(id_user))
                user_folder = PATH_FILES + '/' + str(id_user)
                CHECK_FOLDER = os.path.exists(user_folder)
                if not CHECK_FOLDER:
                    os.makedirs(user_folder)
                    print("created folder : ", user_folder)
                else:
                    print(user_folder, "folder already exists.")
                filename = str(time.time())+'_'+ audio_file.filename
                file_path = user_folder + '/' + filename
                audio_file.save(file_path)
                original_format = audio_file.filename.split(".")[-1]
                
                if filename is None or len(filename) < 1:
                    return "Parametros de archivo invalidos!", 400
                elif new_format is None or len(filename) < 1:
                    return "Ingrese un formato de archivo valido!", 400
                else:
                    new_task = Task(filename = filename, new_format = new_format, id_user = id_user)
                    db.session.add(new_task)
                    db.session.commit()
                    user = User.query.filter_by(id=id_user).first()
                    user_email = user.email
                    args = (new_task.id, new_format, user_folder, filename, original_format, user_email)                  
                    convert_file.apply_async(args=args, queue = 'tasks')
                    return task_schema.dump(new_task)
            else:
                return "El formato del nuevo archivo no es soportado por la plataforma. Solo son validos los formatos mp3, wav y ogg.", 404
        else:
            return "El formato del archivo a convertir no es soportado por la plataforma. Solo son validos los formatos mp3, wav y ogg.", 404
        

    @jwt_required()
    def get(self):
        id_user = get_jwt_identity()
        max = request.json.get("max")
        order = request.json.get("order")
        if order:
            tasks = Task.query.filter(Task.id_user == id_user).order_by(Task.id.desc()).all()[:max]
        else:
            tasks = Task.query.filter(Task.id_user == id_user).order_by(Task.id.asc()).all()[:max]           
 
        return [ task_schema.dump(task) for task in tasks ]


class VistaQueue(Resource):
    
    def post(self):
        print(request.json["id"])
        try:
            task = Task.query.filter(Task.id == request.json["id"]).first()
            print(task)
            task.status = EnumTaskStatus.processed
            task.time_file_processed = datetime.datetime.utcnow()
            db.session.commit()
            return "Tarea " + "procesada exitosamente!", 200  
        except:
            return "Bad request!", 400
            
class VistaTask(Resource):
    @jwt_required()
    def get(self,id_task):
        return task_schema.dump(Task.query.get_or_404(id_task))

    @jwt_required()
    def put(self, id_task):
        task = Task.query.get_or_404(id_task)
        if(task.status == EnumTaskStatus.processed):
            old_format = task.new_format
            id_user = get_jwt_identity()
            task.new_format = request.json.get('newFormat')
            task.status = EnumTaskStatus.uploaded
            task.time_file_processed = None
            db.session.commit()
            user_folder = '/nfs/general/files/' + str(id_user)
            size_file_name = len(task.filename)
            path_file = user_folder + '/' + task.filename[:size_file_name - 4] + '_Processed' + '.' + old_format
            os.remove(path_file)
            original_format = task.filename.split(".")[-1]
            user = User.query.filter_by(id=id_user).first()
            user_email = user.email
            args = (task.id, task.new_format, user_folder, task.filename, original_format,user_email)
            convert_file.apply_async(args=args, queue = 'tasks')
            return task_schema.dump(task), 200
        else:
            return "La tarea que esta intentado modficar aun no ha sido procesada!", 400

    
    @jwt_required()
    def delete(self,id_task):
        id_user = get_jwt_identity()
        task = Task.query.filter(Task.id == id_task , Task.id_user==id_user).first()
        if(task is None):
            return "tarea no encotrada", 400
        else:    
            if(task.status==EnumTaskStatus.processed):
                db.session.delete(task)
                db.session.commit()
                path_folder = '/nfs/general/files/' + str(id_user)
                path_file_original=path_folder + "/" + task.filename
                print("path archivo original->" + path_file_original)

                existe_archivo=os.path.exists(path_file_original)
                if(existe_archivo):
                    os.remove(path_file_original)
                    print("Archivo Borrado: archivo original")
                else:
                    print("no encontro path: archivo original")


                path_file_newfile=path_folder + "/" + task.filename[:len(task.filename) - 4]+"_Processed."+task.new_format
                print("path archivo newfile->" + path_file_newfile)
                existe_archivo=os.path.exists(path_file_newfile)

                if(existe_archivo):
                    os.remove(path_file_newfile)
                    print("Archivo Borrado: archivo nuevo")
                else:
                    print("no encontro path: archivo nuevo")

                

                return "archivo borrado!",200
            else:
                return "archivo no ha sido procesado!",400

class VistaTaskFiles(Resource):
    @jwt_required()
    def get(self,filename):
        #print(filename)
        id_user=get_jwt_identity()
        #task_file=Task.query.filter(Task.filename == filename).first()
        path_usuario_files= '/nfs/general/files/' + str(id_user)
        pathFile=path_usuario_files +"/" + filename
        #print(pathFile)
        existe_archivo=os.path.exists(pathFile)
        if(existe_archivo):        
            return send_file(pathFile,as_attachment=True)
        else:
            return "archivo no existe",400


        # if(task_file is None):
        #     return 'No se encontro el archivo, solicitado para el usuario',400
        # else:
        #     pathFile=path_usuario_files +"/" + task_file.filename
        #     #print(pathFile)
        #     existe_archivo=os.path.exists(pathFile)
        #     if(existe_archivo):        
        #         return send_file(pathFile,as_attachment=True)
        #     else:
        #         return "archivo no existe",400





