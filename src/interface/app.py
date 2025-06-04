import flask
from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import json
import threading
import time
import random
import logging
from flask_socketio import SocketIO
import math

# Configuração de logs - reduzindo nível para WARNING para remover mensagens de debug
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Dados em memória
sensor_data = {
    "vibration": [],
    "temperature": [],
    "humidity": [],
    "status": "desconhecido",
    "last_update": None,
    "last_data_received": 0,  # Timestamp da última recepção de dados
    "alerts": []  # Lista para armazenar alertas ativos
}

# Configuração do Broker MQTT
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
CLIENT_ID = f"python-mqtt-dashboard-{random.randint(0, 1000)}"

# Tópicos
TOPIC_VIBRATION = "sensorGS2025FIAPLEOOO_XYZ_0987654321/vibration"
TOPIC_TEMPERATURE = "sensorGS2025FIAPLEOOO_XYZ_0987654321/temperature" 
TOPIC_HUMIDITY = "sensorGS2025FIAPLEOOO_XYZ_0987654321/humidity"
TOPIC_STATUS = "sensorGS2025FIAPLEOOO_XYZ_0987654321/status"

# Limite de pontos nos gráficos
MAX_DATA_POINTS = 60
# Tempo máximo sem dados para considerar offline (segundos)
OFFLINE_THRESHOLD = 15

# Limites para alertas
TEMPERATURE_MAX = 50.0  # Temperatura máxima em °C
HUMIDITY_MAX = 85.0     # Umidade máxima em %
VIBRATION_THRESHOLD = 4.0  # Valor de magnitude considerado alto (antes do remapeamento)

# Valor máximo de magnitude do sensor (para remapeamento)
VIBRATION_MAX_SENSOR = 3.464102
VIBRATION_MAX_SCALE = 9.0  # Escala máxima desejada

# Função para adicionar dados ao histórico com verificação de duplicatas
def add_data_to_history(sensor_type, value, time_str):
    # Verificar se temos uma lista válida para este tipo de sensor
    if sensor_type not in sensor_data or not isinstance(sensor_data[sensor_type], list):
        logging.error(f"Tipo de sensor inválido ou lista não inicializada: {sensor_type}")
        return
    
    # Validar o valor
    if not isinstance(value, (int, float)) or math.isnan(value):
        logging.error(f"Valor inválido para adicionar ao histórico: {value}")
        return
    
    # Verificar se já temos dados para este timestamp específico para evitar duplicatas
    for item in sensor_data[sensor_type]:
        if item["time"] == time_str:
            # Atualizar o valor existente em vez de adicionar um novo
            item["value"] = value
            socketio.emit('data_update', sensor_data)
            return
            
    # Se não existir, adicionar novo ponto
    if len(sensor_data[sensor_type]) >= MAX_DATA_POINTS:
        sensor_data[sensor_type].pop(0)  # Remover o ponto mais antigo
        
    sensor_data[sensor_type].append({"time": time_str, "value": value})
    
    # Garantir que estamos sempre enviando atualizações via WebSocket
    socketio.emit('data_update', sensor_data)

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
        
        # Registra a hora atual
        current_time = time.strftime("%H:%M:%S")
        
        # Processar o payload com base no tópico
        if topic == TOPIC_VIBRATION:
            process_vibration_data(msg.payload, current_time)
            
        elif topic == TOPIC_TEMPERATURE:
            process_temperature_data(msg.payload, current_time)
            
        elif topic == TOPIC_HUMIDITY:
            process_humidity_data(msg.payload, current_time)
            
        elif topic == TOPIC_STATUS:
            process_status_data(msg.payload)
        
        # Atualiza a hora da última atualização
        sensor_data["last_update"] = current_time
        
        # Verificar se é necessário gerar alertas
        check_alerts()
        
        # Enviar dados atualizados via WebSocket
        socketio.emit('data_update', sensor_data)
    
    except Exception as e:
        logging.error(f"Erro ao processar mensagem do tópico {topic}: {str(e)}")

# Função para remapear valores de vibração para a escala 0-9
def remap_vibration(value):
    # Garantir que o valor está dentro do intervalo esperado
    value = max(0, min(value, VIBRATION_MAX_SENSOR))
    # Aplicar regra de três para remapear
    return (value / VIBRATION_MAX_SENSOR) * VIBRATION_MAX_SCALE

# Função para processar dados de vibração
def process_vibration_data(payload, current_time):
    # Tentar extrair o valor do payload
    try:
        # Tentar como JSON primeiro
        data = json.loads(payload.decode())
        
        # Detectar formato do JSON e extrair valor
        if isinstance(data, dict):
            # Priorizar valores específicos
            if "magnitude" in data:
                raw_value = data["magnitude"]
            elif "level" in data:
                raw_value = data["level"]
            elif "current_magnitude" in data:
                raw_value = data["current_magnitude"]
            elif "vibration_level" in data:
                raw_value = data["vibration_level"]
            else:
                # Usar o primeiro campo numérico encontrado
                for key, val in data.items():
                    if isinstance(val, (int, float)) and key != "timestamp":
                        raw_value = val
                        break
                else:
                    raw_value = 0.0
        else:
            raw_value = float(data)
            
    except (json.JSONDecodeError, ValueError):
        # Se não for JSON, tentar como float ou string
        try:
            raw_value = float(payload.decode().strip())
        except ValueError:
            raw_value = 0.0
    
    # Remapear o valor para a escala 0-9
    remapped_value = remap_vibration(raw_value)
    
    # Adicionar dados ao histórico
    if len(sensor_data["vibration"]) >= MAX_DATA_POINTS:
        sensor_data["vibration"].pop(0)
        
    sensor_data["vibration"].append({
        "time": current_time, 
        "value": remapped_value, 
        "raw_value": raw_value
    })
    
    logging.warning(f"Dado de magnitude processado: valor original={raw_value}, remapeado={remapped_value:.2f}")

# Função para processar dados de temperatura
def process_temperature_data(payload, current_time):
    # Tentar extrair o valor do payload
    try:
        # Tentar como JSON primeiro
        data = json.loads(payload.decode())
        
        # Detectar formato do JSON e extrair valor
        if isinstance(data, dict):
            if "temperature" in data:
                value = float(data["temperature"])
            else:
                # Usar o primeiro campo numérico encontrado
                for key, val in data.items():
                    if isinstance(val, (int, float)) and key != "timestamp":
                        value = float(val)
                        break
                else:
                    logging.error("Não foi possível encontrar valor de temperatura válido no payload")
                    return
        else:
            value = float(data)
            
    except (json.JSONDecodeError, ValueError) as e:
        # Se não for JSON, tentar como float ou string
        try:
            value = float(payload.decode().strip())
        except ValueError:
            logging.error(f"Erro ao processar dados de temperatura: {str(e)}")
            return
    
    # Validar valor
    if not isinstance(value, (int, float)) or math.isnan(value):
        logging.error(f"Valor de temperatura inválido: {value}")
        return
    
    # Adicionar dados ao histórico usando a função de verificação de duplicatas
    add_data_to_history("temperature", value, current_time)
    
    logging.warning(f"Dado de temperatura recebido: {value}°C (Total: {len(sensor_data['temperature'])} pontos)")

# Função para processar dados de umidade
def process_humidity_data(payload, current_time):
    # Tentar extrair o valor do payload
    try:
        # Tentar como JSON primeiro
        data = json.loads(payload.decode())
        
        # Detectar formato do JSON e extrair valor
        if isinstance(data, dict):
            if "humidity" in data:
                value = float(data["humidity"])
            else:
                # Usar o primeiro campo numérico encontrado
                for key, val in data.items():
                    if isinstance(val, (int, float)) and key != "timestamp":
                        value = float(val)
                        break
                else:
                    logging.error("Não foi possível encontrar valor de umidade válido no payload")
                    return
        else:
            value = float(data)
            
    except (json.JSONDecodeError, ValueError) as e:
        # Se não for JSON, tentar como float ou string
        try:
            value = float(payload.decode().strip())
        except ValueError:
            logging.error(f"Erro ao processar dados de umidade: {str(e)}")
            return
    
    # Validar valor
    if not isinstance(value, (int, float)) or math.isnan(value):
        logging.error(f"Valor de umidade inválido: {value}")
        return
    
    # Adicionar dados ao histórico usando a função de verificação de duplicatas
    add_data_to_history("humidity", value, current_time)
    
    logging.warning(f"Dado de umidade recebido: {value}% (Total: {len(sensor_data['humidity'])} pontos)")

# Função para processar dados de status
def process_status_data(payload):
    try:
        # Tentar como JSON primeiro
        data = json.loads(payload.decode())
        
        if isinstance(data, dict) and "status" in data:
            sensor_data["status"] = data["status"]
        elif isinstance(data, str):
            sensor_data["status"] = data
            
    except (json.JSONDecodeError, ValueError):
        # Se não for JSON, usar como string
        try:
            sensor_data["status"] = payload.decode().strip()
        except:
            pass
    
    logging.warning(f"Status atualizado explicitamente: {sensor_data['status']}")

# Função para verificar e gerar alertas com base nos dados dos sensores
def check_alerts():
    # Limpar alertas antigos
    current_time = time.time()
    sensor_data["alerts"] = [alert for alert in sensor_data["alerts"] 
                           if current_time - alert["timestamp"] < 60]  # Remover alertas com mais de 60 segundos
    
    # Verificar temperatura
    if sensor_data["temperature"] and len(sensor_data["temperature"]) > 0:
        temp_value = sensor_data["temperature"][-1]["value"]
        if isinstance(temp_value, (int, float)) and temp_value > TEMPERATURE_MAX:
            add_alert("temperatura", f"Temperatura crítica: {temp_value:.1f}°C", "danger")
    
    # Verificar umidade
    if sensor_data["humidity"] and len(sensor_data["humidity"]) > 0:
        humidity_value = sensor_data["humidity"][-1]["value"]
        if isinstance(humidity_value, (int, float)) and humidity_value > HUMIDITY_MAX:
            add_alert("umidade", f"Umidade crítica: {humidity_value:.1f}%", "warning")
    
    # Verificar vibração
    if sensor_data["vibration"] and len(sensor_data["vibration"]) > 0:
        vib_data = sensor_data["vibration"][-1]
        raw_value = vib_data.get("raw_value", 0)
        remapped_value = vib_data["value"]
        
        if isinstance(remapped_value, (int, float)) and remapped_value > 4.0:
            # Alerta de deslizamentos extremos quando a magnitude for maior que 4.0
            add_alert("magnitude", f"ALERTA DE DESLIZAMENTOS EXTREMOS: {remapped_value:.1f}/9.0", "danger")
        elif isinstance(remapped_value, (int, float)) and remapped_value > 3.0:
            # Vibração moderada, alerta menos grave
            add_alert("magnitude", f"Magnitude elevada: {remapped_value:.1f}/9.0", "warning")

# Função para adicionar um novo alerta
def add_alert(type, message, level):
    # Verificar se já existe um alerta similar recente
    for alert in sensor_data["alerts"]:
        if alert["type"] == type and time.time() - alert["timestamp"] < 30:
            # Atualizar alerta existente em vez de criar novo
            alert["message"] = message
            alert["timestamp"] = time.time()
            return
    
    # Adicionar novo alerta
    sensor_data["alerts"].append({
        "type": type,
        "message": message,
        "level": level,
        "timestamp": time.time()
    })
    logging.warning(f"Novo alerta gerado: {message} (nível: {level})")

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
            # Enviar atualização via WebSocket
            socketio.emit('data_update', sensor_data)
        
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

# Rota para enviar dados de teste (apenas para fins de depuração durante desenvolvimento)
@app.route('/api/test/send')
def send_test_data():
    # Simular recebimento de dados de temperatura
    topic = TOPIC_TEMPERATURE
    temperature = request.args.get('temp', None)
    
    if temperature:
        temperature = float(temperature)
    else:
        temperature = 25.0 + (random.random() * 15)
        
    # Criar payload
    payload = json.dumps({"temperature": temperature}).encode()
    
    # Processar como se fosse um evento MQTT
    current_time = time.strftime("%H:%M:%S")
    process_temperature_data(payload, current_time)
    
    # Simular recebimento de dados de umidade
    topic = TOPIC_HUMIDITY
    humidity = request.args.get('hum', None)
    
    if humidity:
        humidity = float(humidity)
    else:
        humidity = 40.0 + (random.random() * 40)
        
    # Criar payload
    payload = json.dumps({"humidity": humidity}).encode()
    
    # Processar como se fosse um evento MQTT
    process_humidity_data(payload, current_time)
    
    # Atualizar status e timestamp
    sensor_data["status"] = "online"
    sensor_data["last_update"] = current_time
    sensor_data["last_data_received"] = time.time()
    
    # Enviar dados via WebSocket
    socketio.emit('data_update', sensor_data)
    
    return jsonify({"success": True, "temperature": temperature, "humidity": humidity})

# Evento de conexão do WebSocket
@socketio.on('connect')
def handle_connect():
    # Enviar dados atuais quando um cliente se conecta
    socketio.emit('data_update', sensor_data)

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
    
    # Iniciar aplicação Flask com SocketIO
    socketio.run(app, debug=False, host='0.0.0.0', port=5000) 