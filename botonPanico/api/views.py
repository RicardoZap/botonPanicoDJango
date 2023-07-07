from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import APIException
from api import serializers
import requests
import os
import os
from dotenv import load_dotenv
import random
import string
from threading import Timer
from datetime import datetime
import pyodbc

from .models import Dato
from .serializers import DatoSerializer

load_dotenv()
account = os.getenv("ACCOUNT")
password = os.getenv("PASSWORD")
urlGPS = None
urlVideo = None
jsession_public = None
idDispositivo = None
#objeto que guarda los gps detallados
gps_info = {}
#Llave inicial genereda automaticamente
API_KEY = ""
#Segunda llave/variable que se le dará valor al llamar el método de boton de panico
KEY_ALERTA = ""


# Crear un diccionario para almacenar la información de los autobuses
datos_autobuses = {}

# Cuando se recibe un nuevo botón de pánico para un autobús
def procesar_boton_panico(id_autobus, datos):
    # Verificar si el autobús ya tiene datos almacenados
    if id_autobus in datos_autobuses:
        # Actualizar los datos existentes del autobús
        datos_autobuses[id_autobus].append(datos)
    else:
        # Crear una nueva entrada para el autobús
        datos_autobuses[id_autobus] = [datos]

    # Establecer un temporizador para eliminar los datos después de 15 minutos
    Timer(900, eliminar_datos_autobus).start()
    # Puedes usar una biblioteca como threading o asyncio para esto

# Cuando se desea acceder a los datos de un autobús en particular
def obtener_datos_autobus(id_autobus):
    if id_autobus in datos_autobuses:
        return datos_autobuses[id_autobus]
    else:
        return None

# Cuando se desea eliminar los datos de un autobús después de 15 minutos
def eliminar_datos_autobus(id_autobus):
    if id_autobus in datos_autobuses:
        del datos_autobuses[id_autobus]




def startup_event():
    global API_KEY
    API_KEY = generar_token()

#Middleware para verificar el token en cada solicitud
def verify_api_key(get_response):
    def middleware(request):
        global API_KEY
        global KEY_ALERTA
        if request.path != "/setAlerta":  # Excluir la ruta del botón de panico para evitar problemas con Swagger
            api_key = KEY_ALERTA
            #Si la segunda llave no coincide con la llave inicial se denegará el acceso
            if api_key != API_KEY:
                raise APIException("Acceso no autorizado", code=403)
        response = get_response(request)
        return response
    return middleware

#Método para generar el valor de la llave
def generar_token():
    caracteres = string.ascii_letters + string.digits + string.punctuation
    cadena_aleatoria = ''.join(random.choice(caracteres) for _ in range(16))
    return cadena_aleatoria

#Función para reiniciar el valor la primera llave cada 15 minutos
def reset_token():
    global API_KEY
    API_KEY = generar_token()
    # Reiniciar el temporizador después de 15 minutos
    Timer(900, reset_token).start()

def login():
    global account
    global password
    print(account)
    url = f"http://187.188.171.164:8088/StandardApiAction_login.action?account={account}&password={password}"
    headers = {
        "Content-Type": "application/json-p"
    }
    try:
        response = requests.post(url, headers)
        r = response.json()
        if r["result"] != 0:
            return Response({"result": -1, "mensaje": "Usuario o contraseña incorrecta"})
        else:
            print(response.content)
            global jsession_public
            jsession_public = r["jsession"]
            return Response("Logueado correctamente")
    except Exception as e:
        raise APIException(str(e), code=status.HTTP_500_INTERNAL_SERVER_ERROR)

def getInfo():
    global jsession_public
    url = f"http://187.188.171.164:8088/StandardApiAction_queryUserVehicle.action?jsession={jsession_public}"
    headers = {
        "Content-Type": "application/json-p"
    }
    try:
        response = requests.get(url, headers)
        return response.content
    except Exception as e:
        raise APIException(str(e), code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def getDato(request):
    dato = Dato.objects.all()
    serializers = DatoSerializer(dato, many=True)
    return Response(serializers.data)

@api_view(["GET"])
def getGPSDetail(request):
    global gps_info
    return Response(gps_info)

def getGPSMap(unidad: str):
    global jsession_public
    #global idDispositivo
    global urlGPS
    url = f"http://187.188.171.164:8088/808gps/open/map/vehicleMap.html?jsession={jsession_public}&devIdno={unidad}"
    url2 = f"http://187.188.171.164:8088/StandardApiAction_getDeviceStatus.action?jsession={jsession_public}&devIdno={unidad}"

    headers = {
        "Content-Type": "application/json-p"
    }
    try:
        global gps_info
        response = requests.get(url, headers)
        response2 = requests.get(url2, headers)
        data = response2.json()
        concesion = unidad

        gps_info[concesion] = {
            "speed": data["status"][0]["sp"],
            "ID": (str(data["status"][0]["vid"])).replace('-',''),
            "Course": data["status"][0]["hx"],
            "longitud": float(str(data["status"][0]["mlng"])),
            "latitud": float(str(data["status"][0]["mlat"])),
            "altitud": 0,
            "Date": data["status"][0]["gt"]
        }
        procesar_boton_panico(concesion, gps_info)
        print(gps_info)
        #getGPSDetail(gps_info)
        urlGPS = url
        gps = {
            "GPS": url,
            "GPSData": url2,
            "GPSDetailMethod": f"http://127.0.0.1:8000/api/gpsDetalles/{unidad}"
        }
        return gps
    except Exception as e:
        raise APIException(str(e), code=status.HTTP_500_INTERNAL_SERVER_ERROR)

def getVideo(unidad: str):
    global jsession_public
    #global idDispositivo
    global urlVideo
    url = f"http://187.188.171.164:8088/808gps/open/player/video.html?lang=en&devIdno={unidad}&channel=2&jsession={jsession_public}"
    headers = {
        "Content-Type": "application/json-p"
    }
    try:
        response = requests.get(url, headers)
        urlVideo = url
        return url
    except Exception as e:
        raise APIException(str(e), code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def setAlerta(request):
    login()
    data = request.data
    alerta = Dato.objects.create(
        unidad=data['unidad'],
        device=data['device'],
        primer_nombre=data['primer_nombre'],
        segundo_nombre=data['segundo_nombre'],
        apellido_paterno=data['apellido_paterno'],
        apellido_materno=data['apellido_materno'],
        numero_contacto=data['numero_contacto'],
        notas=data['notas'],
        fecha_evento=data['fecha_evento'],
    )

    json_response = {
        "concesion": alerta.unidad,
        "primer_nombre_contacto": alerta.primer_nombre,
        "segundo_nombre_contacto": alerta.segundo_nombre,
        "apellido_paterno_contacto": alerta.apellido_paterno,
        "apellido_materno_contacto": alerta.apellido_materno,
        "numero_contacto": alerta.numero_contacto,
        "FechaHoraEvento": alerta.fecha_evento,
        "GPS": '',
        "GPSDetallado": '',
        "video": [],
        "notas": alerta.notas
    }

    return Response(json_response)

@api_view(["POST"])
def setAlerta(request):
    data = request.data
    alerta = Dato.objects.create(
        unidad=data['unidad'],
        device=data['device'],
        primer_nombre=data['primer_nombre'],
        segundo_nombre=data['segundo_nombre'],
        apellido_paterno=data['apellido_paterno'],
        apellido_materno=data['apellido_materno'],
        numero_contacto=data['numero_contacto'],
        notas=data['notas'],
        fecha_evento=data['fecha_evento'],
    )
    try:
        global API_KEY
        global KEY_ALERTA
        global idDispositivo
        data = request.data
        idDispositivo = data["unidad"]
        print(API_KEY)
        Timer(900, reset_token).start()
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        login()
        url_gps = getGPSMap(idDispositivo)
        url_video = getVideo(idDispositivo)
        camara1 = url_video + "&index=1"
        camara2 = url_video + "&index=2"
        json_response = {
            "concesion": alerta.unidad,
            "primer_nombre_contacto": alerta.primer_nombre,
            "segundo_nombre_contacto": alerta.segundo_nombre,
            "apellido_paterno_contacto": alerta.apellido_paterno,
            "apellido_materno_contacto": alerta.apellido_materno,
            "numero_contacto": alerta.numero_contacto,
            "FechaHoraEvento": alerta.fecha_evento,
            "GPS": url_gps["GPS"],
            "GPSDetallado": url_gps["GPSDetailMethod"],
            "video": [
                camara1,
                camara2
            ],
            "notas": alerta.notas
        }
        log(json_response)

        KEY_ALERTA = API_KEY
        return Response(json_response)
    except Exception as e:
        raise APIException(str(e), code=status.HTTP_500_INTERNAL_SERVER_ERROR)

def log(json):
    try:
        cnxn = pyodbc.connect(f'DRIVER={os.getenv("DRIVER")};SERVER={os.getenv("SERVER")};DATABASE={os.getenv("DATABASE")};UID={os.getenv("USERNAME_DB")};PWD={os.getenv("PASSWORD_DB")};')
        cursor = cnxn.cursor()
        params = (json["concesion"], json["concesion"], json["primer_nombre_contacto"], json["segundo_nombre_contacto"], json["apellido_paterno_contacto"], json["apellido_materno_contacto"], json["video"][0], json["GPS"], json["notas"], json["FechaHoraEvento"])
        cursor.execute("{CALL ins_Envio_Evento (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)}", params)
        cursor.commit()
        cursor.close()
        cnxn.close()
        return {'mensaje': 'Inserción exitosa'}
    except Exception as e:
        raise APIException(str(e), code=status.HTTP_500_INTERNAL_SERVER_ERROR)
