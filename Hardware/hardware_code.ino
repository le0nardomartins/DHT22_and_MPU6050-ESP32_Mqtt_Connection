#include <Wire.h>
#include <DHT.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// Configurações WiFi - CONFIGURE AQUI
//const char* ssid = "ARNE";
//const char* password = "SpeakFriend12";

const char* ssid = "Wokwi-GUEST";
const char* password = "";

// Configurações MQTT Mosquitto - CONFIGURE AQUI
const char* mqtt_server = "broker.hivemq.com";
const int mqtt_port = 1883;
// Autenticação removida - conexão sem usuário/senha

// Tópicos MQTT
const char* topic_vibration = "sensor/vibration";
const char* topic_temperature = "sensor/temperature";
const char* topic_humidity = "sensor/humidity";
const char* topic_status = "sensor/status";
const char* topic_commands = "sensor/commands";

// Definições dos pinos
#define DHT_PIN 17     // Pino do DHT22 (SDA)
#define DHT_TYPE DHT22 // Tipo do sensor DHT
#define SDA_PIN 18     // Pino SDA do I2C (MPU6050)
#define SCL_PIN 19     // Pino SCL do I2C (MPU6050)

// Endereço I2C do MPU6050
#define MPU6050_ADDR 0x68

// Registradores do MPU6050
#define PWR_MGMT_1 0x6B
#define ACCEL_XOUT_H 0x3B
#define ACCEL_CONFIG 0x1C

// Criar objetos
DHT dht(DHT_PIN, DHT_TYPE);
WiFiClient espClient;
PubSubClient mqtt(espClient);

// Variáveis para dados dos sensores
int16_t ax, ay, az;
float accelX, accelY, accelZ;
float magnitude;
float baselineMagnitude = 1.0;
float vibrationThreshold = 0.3;
bool vibrationDetected = false;

// Variáveis DHT22
float temperature, humidity;
unsigned long lastDHTReading = 0;
unsigned long dhtInterval = 2000; // DHT22 leitura a cada 2 segundos

// Configurações de tempo
unsigned long lastReading = 0;
unsigned long readingInterval = 50; // 20Hz para vibração

// Estatísticas
int vibrationCount = 0;
float maxVibration = 0;
unsigned long vibrationStartTime = 0;
bool continuousVibration = false;

// Controle MQTT
unsigned long lastMqttAttempt = 0;
unsigned long lastStatusReport = 0;
unsigned long statusInterval = 30000; // Status a cada 30 segundos

void setup() {
  Serial.begin(115200);
  delay(2000); // Aguardar estabilização
  
  Serial.println("=== Inicializando Sistema MQTT ===");
  
  // Conectar WiFi
  setupWiFi();
  
  // Configurar MQTT (sem autenticação)
  mqtt.setServer(mqtt_server, mqtt_port);
  mqtt.setCallback(mqttCallback);
  
  // Inicializar I2C com pinos específicos
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(100000); // 100kHz para estabilidade
  
  // Inicializar DHT22
  Serial.println("Inicializando DHT22...");
  dht.begin();
  delay(2000); // DHT22 precisa de tempo para estabilizar
  
  // Testar DHT22
  float testTemp = dht.readTemperature();
  float testHum = dht.readHumidity();
  
  if (isnan(testTemp) || isnan(testHum)) {
    Serial.println("❌ ERRO: DHT22 não está respondendo!");
    publishStatus("DHT22 ERROR", "Sensor não está respondendo");
  } else {
    Serial.println("✅ DHT22 inicializado com sucesso!");
    Serial.printf("Temp: %.1f°C, Umidade: %.1f%%\n", testTemp, testHum);
    publishStatus("DHT22 OK", "Sensor inicializado");
  }
  
  delay(1000);
  
  // Inicializar MPU6050
  Serial.println("Inicializando MPU6050...");
  
  // Verificar se o MPU6050 está presente
  Wire.beginTransmission(MPU6050_ADDR);
  byte error = Wire.endTransmission();
  
  if (error != 0) {
    Serial.println("❌ ERRO: MPU6050 não encontrado no endereço 0x68!");
    publishStatus("MPU6050 ERROR", "Sensor não encontrado");
  } else {
    // Acordar o MPU6050
    writeRegister(PWR_MGMT_1, 0x00);
    delay(100);
    
    // Configurar acelerômetro para ±4g
    writeRegister(ACCEL_CONFIG, 0x08);
    delay(100);
    
    // Testar leitura
    readAccelData();
    
    Serial.println("✅ MPU6050 inicializado com sucesso!");
    Serial.printf("Acelerômetro: X=%.2f Y=%.2f Z=%.2f\n", accelX, accelY, accelZ);
    
    // Calibrar sensor
    Serial.println("Calibrando MPU6050... (mantenha parado por 3s)");
    delay(3000);
    calibrateSensor();
    
    publishStatus("MPU6050 OK", "Sensor calibrado");
  }
  
  Serial.println("=================================");
  Serial.println("Sistema pronto! Enviando via MQTT...");
  Serial.println("=================================");
}

void loop() {
  // Manter conexão MQTT
  if (!mqtt.connected()) {
    reconnectMQTT();
  }
  mqtt.loop();
  
  unsigned long currentTime = millis();
  
  // Ler DHT22 a cada 2 segundos
  if (currentTime - lastDHTReading >= dhtInterval) {
    lastDHTReading = currentTime;
    readDHT22();
  }
  
  // Ler MPU6050 para vibração a cada 50ms
  if (currentTime - lastReading >= readingInterval) {
    lastReading = currentTime;
    
    // Verificar se MPU6050 está disponível
    Wire.beginTransmission(MPU6050_ADDR);
    if (Wire.endTransmission() == 0) {
      readAccelData();
      detectVibration();
    }
  }
  
  // Verificar comandos seriais
  checkSerialCommands();
  
  // Enviar status periódico via MQTT
  if (currentTime - lastStatusReport >= statusInterval) {
    lastStatusReport = currentTime;
    publishSystemStatus();
  }
}

void setupWiFi() {
  delay(10);
  Serial.println();
  Serial.print("Conectando ao WiFi ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("");
  Serial.println("WiFi conectado!");
  Serial.print("Endereço IP: ");
  Serial.println(WiFi.localIP());
}

void reconnectMQTT() {
  while (!mqtt.connected()) {
    Serial.print("Conectando ao MQTT...");
    
    String clientId = "ESP32Client-";
    clientId += String(random(0xffff), HEX);
    
    // Conectar sem autenticação
    if (mqtt.connect(clientId.c_str())) {
      Serial.println(" conectado!");
      mqtt.subscribe(topic_commands);
      publishStatus("SYSTEM", "Conectado ao MQTT");
    } else {
      Serial.print(" falhou, rc=");
      Serial.print(mqtt.state());
      Serial.println(" tentando novamente em 5 segundos");
      delay(5000);
    }
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message;
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.printf("Comando recebido: %s\n", message.c_str());
  
  if (message.startsWith("threshold:")) {
    float newThreshold = message.substring(10).toFloat();
    if (newThreshold > 0 && newThreshold < 5) {
      vibrationThreshold = newThreshold;
      publishStatus("THRESHOLD", "Limiar ajustado para " + String(newThreshold));
    }
  } else if (message == "calibrate") {
    calibrateSensor();
    publishStatus("CALIBRATE", "Sensor recalibrado");
  } else if (message == "reset") {
    vibrationCount = 0;
    maxVibration = 0;
    publishStatus("RESET", "Estatísticas resetadas");
  } else if (message == "test") {
    testSensors();
  } else if (message == "status") {
    publishSystemStatus();
  }
}

void readDHT22() {
  humidity = dht.readHumidity();
  temperature = dht.readTemperature();
  
  if (!isnan(temperature) && !isnan(humidity)) {
    Serial.printf("🌡️  Temp: %.1f°C | Umidade: %.1f%%\n", temperature, humidity);
    
    // Publicar dados via MQTT
    publishTemperature(temperature);
    publishHumidity(humidity);
  } else {
    Serial.println("❌ Erro na leitura do DHT22");
    publishStatus("DHT22 ERROR", "Falha na leitura");
  }
}

void readAccelData() {
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(ACCEL_XOUT_H);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU6050_ADDR, 6, true);
  
  if (Wire.available() >= 6) {
    ax = Wire.read() << 8 | Wire.read();
    ay = Wire.read() << 8 | Wire.read();
    az = Wire.read() << 8 | Wire.read();
    
    // Converter para g (±4g range)
    accelX = ax / 8192.0;
    accelY = ay / 8192.0;
    accelZ = az / 8192.0;
    
    magnitude = sqrt(accelX*accelX + accelY*accelY + accelZ*accelZ);
  }
}

void detectVibration() {
  float vibrationLevel = abs(magnitude - baselineMagnitude);
  
  if (vibrationLevel > vibrationThreshold) {
    if (!vibrationDetected) {
      vibrationDetected = true;
      vibrationStartTime = millis();
      vibrationCount++;
      Serial.println("🚨 VIBRAÇÃO DETECTADA!");
    }
    
    continuousVibration = true;
    
    if (vibrationLevel > maxVibration) {
      maxVibration = vibrationLevel;
    }
    
    Serial.printf("📳 Vibração: %.3fg | Magnitude: %.3fg\n", vibrationLevel, magnitude);
    String intensity = classifyVibration(vibrationLevel);
    
    // Publicar vibração via MQTT
    publishVibration(vibrationLevel, magnitude, intensity);
    
  } else {
    if (vibrationDetected && continuousVibration) {
      unsigned long duration = millis() - vibrationStartTime;
      Serial.println("✅ Vibração cessou");
      Serial.printf("Duração: %lums | Máxima: %.3fg\n", duration, maxVibration);
      Serial.println("---");
      
      // Publicar fim da vibração
      publishVibrationEnd(duration, maxVibration);
      
      continuousVibration = false;
      maxVibration = 0;
    }
    vibrationDetected = false;
  }
}

void calibrateSensor() {
  Serial.println("Calibrando...");
  float sumMagnitude = 0;
  int samples = 50;
  int validSamples = 0;
  
  for (int i = 0; i < samples; i++) {
    readAccelData();
    if (magnitude > 0) { // Verificar se a leitura é válida
      sumMagnitude += magnitude;
      validSamples++;
    }
    delay(20);
  }
  
  if (validSamples > 0) {
    baselineMagnitude = sumMagnitude / validSamples;
    Serial.printf("✅ Calibração OK. Linha base: %.3fg\n", baselineMagnitude);
  } else {
    Serial.println("❌ Falha na calibração");
  }
}

String classifyVibration(float level) {
  if (level < 0.5) {
    return "LEVE";
  } else if (level < 1.0) {
    return "MODERADA";
  } else if (level < 2.0) {
    return "FORTE";
  } else {
    return "INTENSA";
  }
}

void checkSerialCommands() {
  if (Serial.available()) {
    String command = Serial.readString();
    command.trim();
    command.toLowerCase();
    
    if (command.startsWith("threshold:")) {
      float newThreshold = command.substring(10).toFloat();
      if (newThreshold > 0 && newThreshold < 5) {
        vibrationThreshold = newThreshold;
        Serial.printf("✅ Novo limiar: %.3fg\n", vibrationThreshold);
      }
    } else if (command == "calibrate") {
      calibrateSensor();
    } else if (command == "reset") {
      vibrationCount = 0;
      maxVibration = 0;
      Serial.println("✅ Estatísticas resetadas");
    } else if (command == "test") {
      testSensors();
    } else if (command == "help") {
      Serial.println("📋 COMANDOS DISPONÍVEIS:");
      Serial.println("threshold:X.X - Ajustar limiar (ex: threshold:0.5)");
      Serial.println("calibrate - Recalibrar MPU6050");
      Serial.println("reset - Resetar estatísticas");
      Serial.println("test - Testar sensores");
      Serial.println("help - Mostrar esta ajuda");
    }
  }
}

void testSensors() {
  Serial.println("🔧 TESTANDO SENSORES:");
  
  // Testar DHT22
  float testTemp = dht.readTemperature();
  float testHum = dht.readHumidity();
  
  if (!isnan(testTemp) && !isnan(testHum)) {
    Serial.printf("✅ DHT22: Temp=%.1f°C, Umidade=%.1f%%\n", testTemp, testHum);
  } else {
    Serial.println("❌ DHT22: Falha na leitura");
  }
  
  // Testar MPU6050
  Wire.beginTransmission(MPU6050_ADDR);
  if (Wire.endTransmission() == 0) {
    readAccelData();
    Serial.printf("✅ MPU6050: X=%.2f Y=%.2f Z=%.2f (Mag=%.3f)\n", 
                 accelX, accelY, accelZ, magnitude);
  } else {
    Serial.println("❌ MPU6050: Não conectado");
  }
}

void writeRegister(byte reg, byte data) {
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(reg);
  Wire.write(data);
  Wire.endTransmission();
}

// Funções de publicação MQTT
void publishVibration(float level, float magnitude, String intensity) {
  StaticJsonDocument<200> doc;
  doc["timestamp"] = millis();
  doc["level"] = level;
  doc["magnitude"] = magnitude;
  doc["intensity"] = intensity;
  doc["threshold"] = vibrationThreshold;
  doc["count"] = vibrationCount;
  
  char buffer[200];
  serializeJson(doc, buffer);
  mqtt.publish(topic_vibration, buffer);
}

void publishVibrationEnd(unsigned long duration, float maxLevel) {
  StaticJsonDocument<150> doc;
  doc["timestamp"] = millis();
  doc["event"] = "vibration_end";
  doc["duration"] = duration;
  doc["max_level"] = maxLevel;
  
  char buffer[150];
  serializeJson(doc, buffer);
  mqtt.publish(topic_vibration, buffer);
}

void publishTemperature(float temp) {
  StaticJsonDocument<100> doc;
  doc["timestamp"] = millis();
  doc["temperature"] = temp;
  
  char buffer[100];
  serializeJson(doc, buffer);
  mqtt.publish(topic_temperature, buffer);
}

void publishHumidity(float hum) {
  StaticJsonDocument<100> doc;
  doc["timestamp"] = millis();
  doc["humidity"] = hum;
  
  char buffer[100];
  serializeJson(doc, buffer);
  mqtt.publish(topic_humidity, buffer);
}

void publishStatus(String type, String message) {
  StaticJsonDocument<150> doc;
  doc["timestamp"] = millis();
  doc["type"] = type;
  doc["message"] = message;
  
  char buffer[150];
  serializeJson(doc, buffer);
  mqtt.publish(topic_status, buffer);
}

void publishSystemStatus() {
  StaticJsonDocument<300> doc;
  doc["timestamp"] = millis();
  doc["temperature"] = temperature;
  doc["humidity"] = humidity;
  doc["vibration_count"] = vibrationCount;
  doc["current_magnitude"] = magnitude;
  doc["threshold"] = vibrationThreshold;
  doc["baseline"] = baselineMagnitude;
  doc["wifi_rssi"] = WiFi.RSSI();
  doc["free_heap"] = ESP.getFreeHeap();
  
  char buffer[300];
  serializeJson(doc, buffer);
  mqtt.publish(topic_status, buffer);
}