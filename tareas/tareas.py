import os
from celery import Celery
from pydub import AudioSegment

celery_app = Celery(__name__, broker='redis://localhost:6379/0')

@celery_app.task(name='convert_file')
def convert_file(new_task_id, new_format, user_folder, filename, original_format):
    original_file_path = user_folder + '/' + filename
    given_audio = AudioSegment.from_file(original_file_path, format=original_format)
    plain_file_name = os.path.splitext(original_file_path)[0]
    new_file_path = plain_file_name +"_Processed." + new_format
    given_audio.export(new_file_path, format=new_format)
    return "Tarea " + new_task_id + " procesada!"
