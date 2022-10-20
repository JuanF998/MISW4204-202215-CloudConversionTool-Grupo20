from flask import request, abort
from flask_jwt_extended import jwt_required, create_access_token, get_jwt, get_jwt_identity, JWTManager
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError
from flask import jsonify

from modelos import db, User, UserSchema

user_schema = UserSchema()

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





