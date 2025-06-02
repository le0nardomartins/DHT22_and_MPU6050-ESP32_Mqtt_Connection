import flask
from flask import Flask, render_template, jsonify
import paho.mqtt.client as mqtt
import json
import threading
import time
import random
import logging

# Configuração de logs - reduzindo nível para WARNING para remover mensagens de debug
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Dados em memória
sensor_data = {
    "vibration": [],
    "temperature": [],
    "humidity": [],
    "status": "desconhecido",
    "last_update": None,
    "last_data_received": 0  # Timestamp da última recepção de dados
}

# Configuração do Broker MQTT
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
CLIENT_ID = f"python-mqtt-dashboard-{random.randint(0, 1000)}"

# Tópicos
TOPIC_VIBRATION = "sensor/vibration"
TOPIC_TEMPERATURE = "sensor/temperature" 
TOPIC_HUMIDITY = "sensor/humidity"
TOPIC_STATUS = "sensor/status"

# Limite de pontos nos gráficos
MAX_DATA_POINTS = 10
# Tempo máximo sem dados para considerar offline (segundos)
OFFLINE_THRESHOLD = 30

# Callbacks MQTT
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.warning("Interface web conectada ao broker MQTT!")
        # Inscrever nos tópicos
        client.subscribe(TOPIC_VIBRATION)
        client.subscribe(TOPIC_TEMPERATURE)
        client.subscribe(TOPIC_HUMIDITY)
        client.subscribe(TOPIC_STATUS)
        
        # Definir status como "desconhecido" no início
        sensor_data["status"] = "desconhecido"
    else:
        logging.error(f"Falha na conexão, código de retorno: {rc}")

def on_message(client, userdata, msg):
    topic = msg.topic
    try:
        # Atualizar timestamp de última recepção de dados
        sensor_data["last_data_received"] = time.time()
        
        # Assumir que o dispositivo está online se recebemos qualquer dado
        if sensor_data["status"] != "online":
            sensor_data["status"] = "online"
            logging.warning("Status atualizado para 'online' devido a recepção de dados")
        
        # Obter valor do payload
        payload_value = None
        
        # Tentar decodificar o payload de diferentes formas
        try:
            # Primeiro tenta como JSON
            payload = json.loads(msg.payload.decode())
            if isinstance(payload, dict) and "value" in payload:
                payload_value = payload["value"]
            else:
                # Se for JSON mas não tiver campo "value", usa o próprio payload
                payload_value = payload
        except json.JSONDecodeError:
            # Se não for JSON, tenta como float ou string
            try:
                payload_value = float(msg.payload.decode().strip())
            except ValueError:
                # Se não for número, usa como string
                payload_value = msg.payload.decode().strip()
        
        # Se ainda não temos um valor, tenta o payload bruto
        if payload_value is None:
            try:
                payload_value = float(msg.payload)
            except (ValueError, TypeError):
                payload_value = str(msg.payload)
        
        # Registra a hora atual
        current_time = time.strftime("%H:%M:%S")
        
        # Processa o valor baseado no tópico
        if topic == TOPIC_VIBRATION:
            if len(sensor_data["vibration"]) >= MAX_DATA_POINTS:
                sensor_data["vibration"].pop(0)
            sensor_data["vibration"].append({"time": current_time, "value": payload_value})
            logging.warning(f"Dado de vibração recebido: {payload_value}")
            
        elif topic == TOPIC_TEMPERATURE:
            if len(sensor_data["temperature"]) >= MAX_DATA_POINTS:
                sensor_data["temperature"].pop(0)
            sensor_data["temperature"].append({"time": current_time, "value": payload_value})
            logging.warning(f"Dado de temperatura recebido: {payload_value}")
            
        elif topic == TOPIC_HUMIDITY:
            if len(sensor_data["humidity"]) >= MAX_DATA_POINTS:
                sensor_data["humidity"].pop(0)
            sensor_data["humidity"].append({"time": current_time, "value": payload_value})
            logging.warning(f"Dado de umidade recebido: {payload_value}")
            
        elif topic == TOPIC_STATUS:
            # Tratar mensagem de status explícita
            if isinstance(payload_value, dict) and "status" in payload_value:
                sensor_data["status"] = payload_value["status"]
            elif isinstance(payload_value, str):
                # Se for uma string direta como "online" ou "offline"
                sensor_data["status"] = payload_value
            logging.warning(f"Status atualizado explicitamente: {sensor_data['status']}")
        
        # Atualiza a hora da última atualização
        sensor_data["last_update"] = current_time
    
    except Exception as e:
        logging.error(f"Erro ao processar mensagem do tópico {topic}: {str(e)}")

def on_disconnect(client, userdata, rc):
    logging.warning("Interface web desconectada do broker MQTT")
    if rc != 0:
        logging.warning("Desconexão inesperada. Tentando reconectar...")

# Função para verificar periodicamente o status online/offline
def check_online_status():
    while True:
        current_time = time.time()
        last_received = sensor_data["last_data_received"]
        
        # Se não recebemos dados há mais de OFFLINE_THRESHOLD segundos e não estamos offline
        if last_received > 0 and (current_time - last_received) > OFFLINE_THRESHOLD and sensor_data["status"] != "offline":
            sensor_data["status"] = "offline"
            logging.warning(f"Status atualizado para 'offline' - sem dados há {int(current_time - last_received)} segundos")
        
        time.sleep(5)  # Verificar a cada 5 segundos

# Configuração do cliente MQTT
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, CLIENT_ID)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.on_disconnect = on_disconnect

# Rotas da aplicação web
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    return jsonify(sensor_data)

# Inicialização do cliente MQTT em uma thread separada
def start_mqtt_client():
    try:
        logging.warning(f"Conectando interface web ao broker {MQTT_BROKER}:{MQTT_PORT}...")
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_forever()
    except Exception as e:
        logging.error(f"Erro na conexão MQTT da interface: {str(e)}")

if __name__ == '__main__':
    # Iniciar cliente MQTT em thread separada
    mqtt_thread = threading.Thread(target=start_mqtt_client)
    mqtt_thread.daemon = True
    mqtt_thread.start()
    
    # Iniciar thread para verificação de status online/offline
    status_thread = threading.Thread(target=check_online_status)
    status_thread.daemon = True
    status_thread.start()
    
    # Iniciar aplicação Flask
    app.run(debug=False, host='0.0.0.0', port=5000) 