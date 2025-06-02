import paho.mqtt.client as mqtt
import time
import json
import random
import logging

# Configuração de logs - reduzindo para WARNING para remover mensagens de debug
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuração do Broker MQTT
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
CLIENT_ID = f"python-mqtt-client-{random.randint(0, 1000)}"

# Tópicos
TOPIC_VIBRATION = "sensor/vibration"
TOPIC_TEMPERATURE = "sensor/temperature" 
TOPIC_HUMIDITY = "sensor/humidity"
TOPIC_STATUS = "sensor/status"
TOPIC_COMMANDS = "sensor/commands"

# Armazenamento de dados recebidos
latest_data = {
    "vibration": None,
    "temperature": None,
    "humidity": None,
    "status": "desconhecido",
    "last_update": None
}

# Callbacks
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.warning("Conectado ao broker MQTT!")
        # Inscrever em todos os tópicos
        client.subscribe(TOPIC_VIBRATION)
        client.subscribe(TOPIC_TEMPERATURE)
        client.subscribe(TOPIC_HUMIDITY)
        client.subscribe(TOPIC_STATUS)
        client.subscribe(TOPIC_COMMANDS)
        
        # Publicar status online do cliente receptor
        client.publish(TOPIC_STATUS, json.dumps({"status": "online", "device": "receiver"}))
    else:
        logging.error(f"Falha na conexão, código de retorno: {rc}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = None
        
        # Tentar decodificar a mensagem como JSON
        try:
            payload = json.loads(msg.payload.decode())
        except json.JSONDecodeError:
            # Se não for JSON, tratar como string ou número
            payload_str = msg.payload.decode().strip()
            try:
                # Tentar converter para número
                payload_value = float(payload_str)
                payload = {"value": payload_value}
            except ValueError:
                # Se não for número, usar como string
                payload = {"value": payload_str}
        
        current_time = time.strftime("%H:%M:%S")
        
        # Atualizar dados baseado no tópico
        if topic == TOPIC_VIBRATION and "value" in payload:
            latest_data["vibration"] = payload["value"]
            logging.warning(f"Dado de vibração recebido: {payload['value']}")
            
        elif topic == TOPIC_TEMPERATURE and "value" in payload:
            latest_data["temperature"] = payload["value"]
            logging.warning(f"Dado de temperatura recebido: {payload['value']}")
            
        elif topic == TOPIC_HUMIDITY and "value" in payload:
            latest_data["humidity"] = payload["value"]
            logging.warning(f"Dado de umidade recebido: {payload['value']}")
            
        elif topic == TOPIC_STATUS:
            if isinstance(payload, dict) and "status" in payload:
                latest_data["status"] = payload["status"]
                device = payload.get("device", "unknown")
                logging.warning(f"Status recebido do dispositivo {device}: {payload['status']}")
        
        # Processar comandos recebidos
        elif topic == TOPIC_COMMANDS and isinstance(payload, dict):
            command_type = payload.get("type")
            if command_type:
                logging.warning(f"Comando recebido: {command_type}")
                
                # Publicar resposta ao comando
                response = {
                    "response_to": command_type,
                    "status": "received",
                    "timestamp": time.time()
                }
                client.publish(TOPIC_STATUS, json.dumps(response))
        
        latest_data["last_update"] = current_time
        
    except Exception as e:
        logging.error(f"Erro ao processar mensagem do tópico {msg.topic}: {str(e)}")

def on_disconnect(client, userdata, rc):
    logging.warning("Desconectado do broker MQTT")
    if rc != 0:
        logging.warning("Desconexão inesperada. Tentando reconectar...")

# Configuração do cliente MQTT
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, CLIENT_ID)
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect

# Função principal
def main():
    try:
        # Conectar ao broker
        logging.warning(f"Conectando ao broker {MQTT_BROKER}:{MQTT_PORT}...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        # Iniciar loop MQTT em modo de bloqueio
        logging.warning("Iniciando loop MQTT para receber dados reais dos sensores...")
        client.loop_forever()
            
    except KeyboardInterrupt:
        logging.warning("Programa interrompido pelo usuário")
    except Exception as e:
        logging.error(f"Erro inesperado: {str(e)}")
    finally:
        # Publicar status offline e desconectar
        try:
            client.publish(TOPIC_STATUS, json.dumps({"status": "offline", "device": "receiver"}))
            client.disconnect()
            logging.warning("Desconectado do broker MQTT")
        except Exception:
            pass

if __name__ == "__main__":
    main()
