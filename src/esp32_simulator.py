import paho.mqtt.client as mqtt
import time
import json
import random
import logging
import math
import threading
from datetime import datetime

# Configuração de logs
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuração do Broker MQTT
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
CLIENT_ID = f"esp32-simulator-{random.randint(0, 1000)}"

# Tópicos
TOPIC_VIBRATION = "sensor/vibration"
TOPIC_TEMPERATURE = "sensor/temperature" 
TOPIC_HUMIDITY = "sensor/humidity"
TOPIC_STATUS = "sensor/status"
TOPIC_COMMANDS = "sensor/commands"

# Configurações de simulação
UPDATE_INTERVAL = 5  # segundos (ajustado para ter menos pontos no gráfico)
VIBRATION_NORMAL = (0.1, 2.0)  # range normal
VIBRATION_ANOMALY = (5.0, 10.0)  # range de anomalia
TEMP_NORMAL = (20.0, 28.0)  # range normal
TEMP_ANOMALY = (30.0, 45.0)  # range de anomalia
HUMIDITY_NORMAL = (40.0, 60.0)  # range normal
HUMIDITY_ANOMALY = (75.0, 95.0)  # range de anomalia

# Estado do simulador
simulator_state = {
    "running": True,
    "anomaly_mode": False,
    "vibration_value": 0.5,
    "temperature_value": 24.0,
    "humidity_value": 50.0,
    "anomaly_active_until": 0,
    "calibration_mode": False,
    "device_id": f"ESP32-DHT22-MPU6050-{random.randint(1000, 9999)}"
}

# Função para gerar valores com variação suave
def generate_smooth_value(current, target, step_size=0.2):
    if current < target:
        return min(current + step_size, target)
    else:
        return max(current - step_size, target)

# Função para simular uma onda senoidal com ruído
def generate_sine_wave(base_value, amplitude, phase, noise_level=0.1):
    # Gerar valor da onda senoidal
    sine_value = base_value + amplitude * math.sin(phase)
    # Adicionar ruído aleatório
    noise = random.uniform(-noise_level, noise_level)
    return sine_value + noise

# Callbacks MQTT
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.warning(f"Simulador ESP32 [{simulator_state['device_id']}] conectado ao broker MQTT!")
        # Inscrever no tópico de comandos
        client.subscribe(TOPIC_COMMANDS)
        # Publicar status online
        client.publish(TOPIC_STATUS, json.dumps({
            "status": "online", 
            "device": "ESP32", 
            "device_id": simulator_state['device_id'],
            "timestamp": time.time()
        }))
    else:
        logging.error(f"Falha na conexão, código de retorno: {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        logging.warning(f"Comando recebido: {payload}")
        
        if msg.topic == TOPIC_COMMANDS and isinstance(payload, dict):
            command_type = payload.get("type")
            
            if command_type == "reset":
                logging.warning("Comando de reset recebido, reiniciando simulador...")
                # Simular reinicialização do ESP32
                time.sleep(2)  # Simular tempo de reinicialização
                simulator_state["anomaly_mode"] = False
                simulator_state["calibration_mode"] = False
                simulator_state["vibration_value"] = 0.5
                simulator_state["temperature_value"] = 24.0
                simulator_state["humidity_value"] = 50.0
                
                # Enviar confirmação
                client.publish(TOPIC_STATUS, json.dumps({
                    "status": "reset_complete", 
                    "device": "ESP32",
                    "device_id": simulator_state['device_id'],
                    "timestamp": time.time()
                }))
                
            elif command_type == "calibrate":
                logging.warning("Comando de calibração recebido, calibrando sensores...")
                # Simular calibração
                simulator_state["calibration_mode"] = True
                time.sleep(3)  # Simular tempo de calibração
                simulator_state["calibration_mode"] = False
                
                # Enviar confirmação
                client.publish(TOPIC_STATUS, json.dumps({
                    "status": "calibration_complete", 
                    "device": "ESP32",
                    "device_id": simulator_state['device_id'],
                    "timestamp": time.time()
                }))
                
            elif command_type == "status":
                logging.warning("Solicitação de status recebida...")
                # Enviar status completo
                client.publish(TOPIC_STATUS, json.dumps({
                    "status": "online", 
                    "device": "ESP32",
                    "device_id": simulator_state['device_id'],
                    "uptime": int(time.time() - start_time),
                    "free_memory": random.randint(30000, 40000),
                    "wifi_strength": random.randint(70, 95),
                    "battery": random.randint(60, 100),
                    "timestamp": time.time()
                }))
                
            elif command_type == "anomaly":
                # Comando para simular anomalia
                duration = int(payload.get("value", 30))  # Duração em segundos
                logging.warning(f"Comando para simular anomalia recebido, duração: {duration}s")
                simulator_state["anomaly_mode"] = True
                simulator_state["anomaly_active_until"] = time.time() + duration
                
    except json.JSONDecodeError:
        logging.error(f"Formato de comando inválido: {msg.payload.decode()}")
    except Exception as e:
        logging.error(f"Erro ao processar comando: {str(e)}")

def on_disconnect(client, userdata, rc):
    logging.warning("Simulador ESP32 desconectado do broker MQTT")
    if rc != 0:
        logging.warning("Desconexão inesperada. Tentando reconectar...")

# Configuração do cliente MQTT
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, CLIENT_ID)
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect

# Função de simulação do ESP32
def simulate_esp32():
    phase = 0
    last_publish_time = 0
    
    while simulator_state["running"]:
        current_time = time.time()
        
        # Verificar se o modo de anomalia deve ser desativado
        if simulator_state["anomaly_mode"] and current_time > simulator_state["anomaly_active_until"]:
            simulator_state["anomaly_mode"] = False
            logging.warning("Modo de anomalia encerrado")
        
        # Publicar dados a cada UPDATE_INTERVAL segundos
        if current_time - last_publish_time >= UPDATE_INTERVAL:
            # Incrementar fase para a onda senoidal
            phase += 0.1
            
            # Determinar ranges com base no modo atual
            if simulator_state["anomaly_mode"]:
                vib_range = VIBRATION_ANOMALY
                temp_range = TEMP_ANOMALY
                hum_range = HUMIDITY_ANOMALY
            else:
                vib_range = VIBRATION_NORMAL
                temp_range = TEMP_NORMAL
                hum_range = HUMIDITY_NORMAL
            
            # Gerar valores alvo dentro dos ranges apropriados
            vib_target = random.uniform(vib_range[0], vib_range[1])
            temp_target = random.uniform(temp_range[0], temp_range[1])
            hum_target = random.uniform(hum_range[0], hum_range[1])
            
            # Atualizar valores com variação suave
            simulator_state["vibration_value"] = generate_smooth_value(
                simulator_state["vibration_value"], vib_target, 0.3)
            
            # Usar onda senoidal para temperatura
            base_temp = (temp_range[0] + temp_range[1]) / 2
            simulator_state["temperature_value"] = generate_sine_wave(
                base_temp, (temp_range[1] - temp_range[0])/4, phase, 0.2)
            
            # Umidade como inverso parcial da temperatura
            simulator_state["humidity_value"] = generate_sine_wave(
                (hum_range[0] + hum_range[1]) / 2, 
                (hum_range[1] - hum_range[0])/4, 
                phase + math.pi, 0.5)  # Fase oposta à temperatura
            
            # Adicionar variação durante calibração
            if simulator_state["calibration_mode"]:
                simulator_state["vibration_value"] = random.uniform(0, 0.2)
                simulator_state["temperature_value"] += random.uniform(-0.5, 0.5)
                simulator_state["humidity_value"] += random.uniform(-1, 1)
            
            # Publicar valores nos tópicos
            try:
                client.publish(TOPIC_VIBRATION, json.dumps({
                    "value": round(simulator_state["vibration_value"], 2),
                    "timestamp": current_time,
                    "device_id": simulator_state['device_id']
                }))
                
                client.publish(TOPIC_TEMPERATURE, json.dumps({
                    "value": round(simulator_state["temperature_value"], 1),
                    "timestamp": current_time,
                    "device_id": simulator_state['device_id']
                }))
                
                client.publish(TOPIC_HUMIDITY, json.dumps({
                    "value": round(simulator_state["humidity_value"], 1),
                    "timestamp": current_time,
                    "device_id": simulator_state['device_id']
                }))
                
                # Publicar status periodicamente
                if random.random() < 0.2:  # 20% de chance de publicar status
                    client.publish(TOPIC_STATUS, json.dumps({
                        "status": "online", 
                        "device": "ESP32",
                        "device_id": simulator_state['device_id'],
                        "timestamp": current_time
                    }))
                
                logging.warning(f"Publicados: Temp={round(simulator_state['temperature_value'], 1)}°C, " +
                             f"Umid={round(simulator_state['humidity_value'], 1)}%, " +
                             f"Vib={round(simulator_state['vibration_value'], 2)}")
                             
                last_publish_time = current_time
                
            except Exception as e:
                logging.error(f"Erro ao publicar dados: {str(e)}")
        
        # Pausa curta para evitar uso excessivo de CPU
        time.sleep(0.1)

# Função principal
def main():
    global start_time
    start_time = time.time()
    
    try:
        # Conectar ao broker
        logging.warning(f"Iniciando simulador ESP32 [{simulator_state['device_id']}]...")
        logging.warning(f"Conectando ao broker {MQTT_BROKER}:{MQTT_PORT}...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        # Iniciar loop MQTT em uma thread separada
        client.loop_start()
        
        # Criar e iniciar thread de simulação
        simulation_thread = threading.Thread(target=simulate_esp32)
        simulation_thread.daemon = True
        simulation_thread.start()
        
        # Mostrar mensagem de ajuda
        print("\n" + "="*60)
        print("   Simulador ESP32 iniciado!")
        print("   Dispositivo: " + simulator_state['device_id'])
        print("   Publicando dados nos tópicos:")
        print(f"   - {TOPIC_TEMPERATURE}")
        print(f"   - {TOPIC_HUMIDITY}")
        print(f"   - {TOPIC_VIBRATION}")
        print("   Pressione Ctrl+C para encerrar o simulador")
        print("="*60 + "\n")
        
        # Manter o programa em execução
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logging.warning("Simulador interrompido pelo usuário")
    except Exception as e:
        logging.error(f"Erro inesperado: {str(e)}")
    finally:
        # Encerrar simulador
        simulator_state["running"] = False
        
        # Publicar status offline e desconectar
        try:
            client.publish(TOPIC_STATUS, json.dumps({
                "status": "offline", 
                "device": "ESP32",
                "device_id": simulator_state['device_id'],
                "timestamp": time.time()
            }))
            client.loop_stop()
            client.disconnect()
            logging.warning("Simulador ESP32 desconectado")
        except Exception:
            pass

if __name__ == "__main__":
    main() 