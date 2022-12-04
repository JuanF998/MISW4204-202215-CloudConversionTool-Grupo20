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
from modelos import db, User, UserSchema, Task, EnumTaskStatus, TaskSchema
from flask import send_from_directory,send_file
from sqlalchemy import asc,desc
from google.cloud import storage
from google.cloud import pubsub_v1

#os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/home/crackmayo/Desktop/MISW4204-202215-CloudConversionTool-Grupo20/flaskr/vistas/ServiceKey_GoogleCloud.json'
storage_client = storage.Client()

publisher = pubsub_v1.PublisherClient()
topic_path = 'projects/desarrollosoftwarenubegrupo20/topics/files_processing-sub'

user_schema = UserSchema()
task_schema = TaskSchema()

def upload_to_bucket(blob_name, file_path, bucket_name):

    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(file_path)
    os.remove(file_path)
    return blob

def blob_exists(bucket_name, filename):

   bucket = storage_client.get_bucket(bucket_name)
   blob = bucket.blob(filename)
   return blob.exists()

def delete_blob(bucket_name, blob_name):

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.delete()

def generate_download_signed_url(bucket_name, blob_name):

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=5),
        method="GET",
    )
    return url

def download_file_from_bucket(blob_name, file_path, bucket_name):

    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    with open(file_path, 'wb') as f:
        storage_client.download_blob_to_file(blob, f)

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
                PATH_FILES = os.getcwd() + "/files/"
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
                upload_to_bucket("files/" + str(id_user) + "/" + filename, file_path, "cloudconvertertoolstorage")
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
                
                    data = 'New file to process!'
                    data = data.encode('utf-8')
                    attributes = {
                        'new_task_id': str(new_task.id),
                        'new_format': str(new_format),
                        'user_folder': str(user_folder),
                        'filename': str(filename),
                        'original_format': str(original_format),
                        'user_email': str(user_email),
                        'id_user': str(id_user)
                    }

                    publisher.publish(topic_path, data, **attributes)

                    return task_schema.dump(new_task)
            else:
                return "El formato del nuevo archivo no es soportado por la plataforma. Solo son validos los formatos mp3, wav y ogg.", 404
        else:
            return "El formato del archivo a convertir no es soportado por la plataforma. Solo son validos los formatos mp3, wav y ogg.", 404
        
    @jwt_required()
    def get(self):

        id_user = get_jwt_identity()
        max = int(request.args.get('max'))
        order = int(request.args.get('order'))

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

        bucket_name = "cloudconvertertoolstorage"
        task = Task.query.get_or_404(id_task)
        if(task.status == EnumTaskStatus.processed):
            old_format = task.new_format
            id_user = get_jwt_identity()
            task.new_format = request.json.get('newFormat')
            task.status = EnumTaskStatus.uploaded
            task.time_file_processed = None
            db.session.commit()

            path_folder = 'files/' + str(id_user)
            processed_blob_name = path_folder + "/" + task.filename[:len(task.filename) - 4]+"_Processed." + old_format

            if(blob_exists(bucket_name, processed_blob_name)):
                delete_blob(bucket_name, processed_blob_name)
            else:
                print("No se encontro el blob: archivo procesado")

            user_folder = os.getcwd() + "/files/" + str(id_user)
            original_format = task.filename.split(".")[-1]
            user = User.query.filter_by(id=id_user).first()
            user_email = user.email
            args = (task.id, task.new_format, user_folder, task.filename, original_format,user_email, id_user)

            data = 'New file to process!'
            data = data.encode('utf-8')
            attributes = {
                'new_task_id': str(task.id),
                'new_format': str(task.new_format),
                'user_folder': str(user_folder),
                'filename': str(task.filename),
                'original_format': str(original_format),
                'user_email': str(user_email),
                'id_user': str(id_user)
            }

            publisher.publish(topic_path, data, **attributes)

            return task_schema.dump(task), 200
        else:
            return "La tarea que esta intentado modficar aun no ha sido procesada!", 400

    @jwt_required()
    def delete(self,id_task):

        bucket_name = "cloudconvertertoolstorage"
        id_user = get_jwt_identity()
        task = Task.query.filter(Task.id == id_task , Task.id_user==id_user).first()
        if(task is None):
            return "Tarea no encotrada", 400
        else:    
            if(task.status==EnumTaskStatus.processed):
                db.session.delete(task)
                db.session.commit()
                path_folder = 'files/' + str(id_user)
                original_blob_name = path_folder + "/" + task.filename

                if(blob_exists(bucket_name, original_blob_name)):
                    delete_blob(bucket_name, original_blob_name)
                else:
                    print("No se encontro el blob: archivo original")

                processed_blob_name = path_folder + "/" + task.filename[:len(task.filename) - 4]+"_Processed." + task.new_format
              
                if(blob_exists(bucket_name, processed_blob_name)):
                    delete_blob(bucket_name, processed_blob_name)
                else:
                    print("No se encontro el blob: archivo procesado")

                return "Tarea eliminada, archivos borrados!",200
            else:
                return "La tarea no ha sido procesada aun!",400

class VistaTaskFiles(Resource):

    @jwt_required()
    def get(self,filename):

        bucket_name = "cloudconvertertoolstorage"
        id_user = get_jwt_identity()
        blob_name = 'files/' + str(id_user) + '/' + filename
        download_path = os.getcwd() + '/' + filename 
        if(blob_exists(bucket_name, blob_name)):  
            download_file_from_bucket(blob_name, download_path, "cloudconvertertoolstorage")
            return send_file(download_path,as_attachment=True)
        else:
            return "Archivo no existe!",400