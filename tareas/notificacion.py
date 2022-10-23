import smtplib
from email.message import EmailMessage
import ssl

def notificate(email_receiver, filename, new_format, new_task_id):
    email_sender = "misw.convertertoolg20@gmail.com"
    email_password = "qjktdhsdbeuyalhz"
    email_receiver = email_receiver
    newName=filename[:len(filename) - 4]
    print(newName)
    subject = f"Conversión de archivo {newName} exitosa!"
    body = f""" Se ha procesado la tarea {new_task_id} con éxito. El archivo {newName}_Processed.{new_format} se encuentra disponible para descargar."""

    em = EmailMessage()
    em['From'] = email_sender
    em['To'] = email_receiver
    em['Subject'] = subject
    em.set_content(body)

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context = context) as smtp:
        smtp.login(email_sender, email_password)
        smtp.sendmail(email_sender, email_receiver, em.as_string())

