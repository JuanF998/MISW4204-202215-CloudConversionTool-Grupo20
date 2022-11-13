import os
from celery import Celery
from pydub import AudioSegment
import requests
from notificacion import notificate
from google.cloud import storage

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/home/crackmayo/Desktop/MISW4204-202215-CloudConversionTool-Grupo20/flaskr/vistas/ServiceKey_GoogleCloud.json'
storage_client = storage.Client()
celery_app = Celery(__name__, broker='redis://localhost:6379/0')

def download_file_from_bucket(blob_name, file_path, bucket_name):

    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    with open(file_path, 'wb') as f:
        storage_client.download_blob_to_file(blob, f)

def upload_to_bucket(blob_name, file_path, bucket_name):

    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(file_path)
    os.remove(file_path)
    return blob

@celery_app.task(name='convert_file')
def convert_file(new_task_id, new_format, user_folder, filename, original_format, user_email, id_user):

    try:
        blob_name = 'files/'+ str(id_user) + '/' + filename
        download_path = user_folder + '/' + filename 
        download_file_from_bucket(blob_name, download_path, "cloudconvertertoolstorage")
        given_audio = AudioSegment.from_file(download_path, format = original_format)
        plain_file_name = os.path.splitext(download_path)[0]
        new_blob_name = filename.replace('.' + original_format, '') + '_Processed.' + new_format
        new_file_path = plain_file_name +"_Processed." + new_format
        given_audio.export(new_file_path, format=new_format)
        url = 'http://10.0.2.15/api/queue'
        obj = {'id': new_task_id}
        upload_to_bucket('files/' + str(id_user) + '/' + new_blob_name, new_file_path, "cloudconvertertoolstorage")
        response_update_task_state = requests.post(url, json = obj)
        os.remove(download_path)
        notificate(user_email, filename, new_format, new_task_id)

        return "Tarea procesada!"

    except Exception as e:
        return str(e)

    
