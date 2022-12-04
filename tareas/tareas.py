import os
from pydub import AudioSegment
import requests
from notificacion import notificate
from google.cloud import storage
from google.cloud import pubsub_v1
from concurrent.futures import TimeoutError

#os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/home/crackmayo/Desktop/MISW4204-202215-CloudConversionTool-Grupo20/flaskr/vistas/ServiceKey_GoogleCloud.json'
storage_client = storage.Client()

subscriber = pubsub_v1.SubscriberClient()
subscription_path = 'projects/desarrollosoftwarenubegrupo20/subscriptions/files_processing-sub-sub'

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

def callback(message):

    print(f"Received task {message.attributes.get('new_task_id')}: {message}")

    id_user = message.attributes.get('id_user')
    filename = message.attributes.get('filename')
    user_folder = message.attributes.get('user_folder')
    original_format = message.attributes.get('original_format')
    new_format = message.attributes.get('new_format')
    new_task_id = message.attributes.get('new_task_id')
    user_email = message.attributes.get('user_email')
    
    try:
        blob_name = 'files/'+ str(id_user) + '/' + filename
        download_path = os.getcwd() + '/' + filename 
        download_file_from_bucket(blob_name, download_path, "cloudconvertertoolstorage")
        given_audio = AudioSegment.from_file(download_path, format = original_format)
        plain_file_name = os.path.splitext(download_path)[0]
        new_blob_name = filename.replace('.' + original_format, '') + '_Processed.' + new_format
        new_file_path = plain_file_name +"_Processed." + new_format
        given_audio.export(new_file_path, format=new_format)
        url = 'https://desarrollosoftwarenubegrupo20.uc.r.appspot.com/api/queue'
        obj = {'id': new_task_id}
        upload_to_bucket('files/' + str(id_user) + '/' + new_blob_name, new_file_path, "cloudconvertertoolstorage")
        requests.post(url, json = obj)
        os.remove(download_path)
        notificate(user_email, filename, new_format, new_task_id)
        message.ack() 

        print("Tarea procesada!")

    except Exception as e:
        return str(e)

streaming_pull_task = subscriber.subscribe(subscription_path, callback=callback)
print(f'Listening for tasks on {subscription_path}')

with subscriber:
    try:
        streaming_pull_task.result()
    except TimeoutError:
        streaming_pull_task.cancel()
        streaming_pull_task.result()
