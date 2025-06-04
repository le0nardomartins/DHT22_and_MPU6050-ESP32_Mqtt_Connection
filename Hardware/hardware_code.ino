#include <Wire.h>
#include <DHT.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// Configurações WiFi
const char* ssid = "Wokwi-GUEST";
const char* password = "";

// Configurações MQTT Mosquitto
const char* mqtt_server = "broker.hivemq.com";
const int mqtt_port = 1883;

// Tópicos MQTT
const char* topic_vibration = "sensorGS2025FIAPLEOOO_XYZ_0987654321/vibration";
const char* topic_temperature = "sensorGS2025FIAPLEOOO_XYZ_0987654321/temperature";
const char* topic_humidity = "sensorGS2025FIAPLEOOO_XYZ_0987654321/humidity";

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
unsigned long dhtInterval = 60000; // DHT22 leitura a cada 1 minuto

// Configurações de tempo
unsigned long lastReading = 0;
unsigned long readingInterval = 50; // 20Hz para vibração
unsigned long lastDataSend = 0;
unsigned long dataSendInterval = 60000; // Enviar dados a cada 1 minuto

// Estatísticas
int vibrationCount = 0;
float maxVibration = 0;
unsigned long vibrationStartTime = 0;
bool continuousVibration = false;

// Controle MQTT
unsigned long lastMqttAttempt = 0;
unsigned long lastStatusReport = 0;
unsigned long statusInterval = 1800000; // Print status a cada 30 minutos

// Controle de prints
bool verboseMode = false; // Reduzir prints por padrão
unsigned long lastPrintTime = 0;
unsigned long printInterval = 30000; // Print status a cada 30s

void setup() {
  Serial.begin(115200);
  delay(2000);
  
  Serial.println("=== Sistema MQTT Iniciando ===");
  
  // Conectar WiFi
  setupWiFi();
  
  // Configurar MQTT
  mqtt.setServer(mqtt_server, mqtt_port);
  
  // Inicializar I2C
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(100000);
  
  // Inicializar DHT22
  dht.begin();
  delay(2000);
  
  // Testar DHT22
  float testTemp = dht.readTemperature();
  float testHum = dht.readHumidity();
  
  if (isnan(testTemp) || isnan(testHum)) {
    Serial.println("ERRO: DHT22 não responde");
  } else {
    Serial.println("DHT22: OK");
  }
  
  // Inicializar MPU6050
  Wire.beginTransmission(MPU6050_ADDR);
  byte error = Wire.endTransmission();
  
  if (error != 0) {
    Serial.println("ERRO: MPU6050 não encontrado");
  } else {
    writeRegister(PWR_MGMT_1, 0x00);
    delay(100);
    writeRegister(ACCEL_CONFIG, 0x08);
    delay(100);
    
    Serial.println("MPU6050: OK - Calibrando...");
    delay(2000);
    calibrateSensor();
  }
  
  Serial.println("Sistema pronto!");
  Serial.println("Comandos: 'verbose', 'quiet', 'status', 'help'");
}

void loop() {
  // Manter conexão MQTT
  if (!mqtt.connected()) {
    reconnectMQTT();
  }
  mqtt.loop();
  
  unsigned long currentTime = millis();
  
  // Ler sensores continuamente (mas só imprimir quando necessário)
  if (currentTime - lastReading >= readingInterval) {
    lastReading = currentTime;
    
    // Ler MPU6050 para vibração
    Wire.beginTransmission(MPU6050_ADDR);
    if (Wire.endTransmission() == 0) {
      readAccelData();
      detectVibration();
    }
  }
  
  // Ler DHT22 e enviar dados a cada 1 minuto
  if (currentTime - lastDHTReading >= dhtInterval) {
    lastDHTReading = currentTime;
    readDHT22();
    
    // Enviar todos os dados coletados
    sendAllData();
  }
  
  // Print status periodicamente (se verbose ou a cada 30s)
  if (verboseMode || (currentTime - lastPrintTime >= printInterval)) {
    lastPrintTime = currentTime;
    printCurrentStatus();
  }
  
  // Verificar comandos seriais
  checkSerialCommands();
  
  // Print status periodicamente a cada 30 minutos
  if (currentTime - lastStatusReport >= statusInterval) {
    lastStatusReport = currentTime;
    if (verboseMode) printCurrentStatus();
  }
}

void setupWiFi() {
  WiFi.begin(ssid, password);
  Serial.print("WiFi conectando");
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println(" OK");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

void reconnectMQTT() {
  unsigned long currentTime = millis();
  if (currentTime - lastMqttAttempt < 5000) return; // Evitar tentativas muito frequentes
  lastMqttAttempt = currentTime;
  
  if (!mqtt.connected()) {
    String clientId = "ESP32Client-" + String(random(0xffff), HEX);
    
    if (mqtt.connect(clientId.c_str())) {
      if (verboseMode) Serial.println("MQTT: Conectado");
    } else {
      if (verboseMode) {
        Serial.print("MQTT falhou: ");
        Serial.println(mqtt.state());
      }
    }
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Função removida - sem tópico de comandos
}

void readDHT22() {
  humidity = dht.readHumidity();
  temperature = dht.readTemperature();
  
  if (isnan(temperature) || isnan(humidity)) {
    if (verboseMode) Serial.println("DHT22: Erro na leitura");
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
      
      if (verboseMode) Serial.println("VIBRAÇÃO DETECTADA!");
    }
    
    continuousVibration = true;
    
    if (vibrationLevel > maxVibration) {
      maxVibration = vibrationLevel;
    }
    
    // Enviar vibração imediatamente (só em casos críticos)
    if (vibrationLevel > 1.0) { // Vibração forte
      publishVibrationAlert(vibrationLevel, magnitude);
    }
    
  } else {
    if (vibrationDetected && continuousVibration) {
      unsigned long duration = millis() - vibrationStartTime;
      
      if (verboseMode) {
        Serial.println("Vibração cessou - Duração: " + String(duration) + "ms");
      }
      
      continuousVibration = false;
      maxVibration = 0;
    }
    vibrationDetected = false;
  }
}

void sendAllData() {
  if (!mqtt.connected()) return;
  
  // Enviar temperatura
  if (!isnan(temperature)) {
    publishTemperature(temperature);
  }
  
  // Enviar umidade
  if (!isnan(humidity)) {
    publishHumidity(humidity);
  }
  
  // Enviar dados de vibração consolidados
  publishVibrationSummary();
  
  // Enviar valor atual da vibração
  publishCurrentVibration();
  
  if (verboseMode) {
    Serial.println("Dados enviados via MQTT");
  }
}

void printCurrentStatus() {
  Serial.println("--- STATUS ---");
  if (!isnan(temperature) && !isnan(humidity)) {
    Serial.printf("Temp: %.1f°C | Umidade: %.1f%%\n", temperature, humidity);
  }
  Serial.printf("Vibrações: %d | Magnitude: %.3f\n", vibrationCount, magnitude);
  Serial.printf("WiFi: %ddBm | Heap: %d bytes\n", WiFi.RSSI(), ESP.getFreeHeap());
  Serial.println("--------------");
}

void calibrateSensor() {
  float sumMagnitude = 0;
  int samples = 50;
  int validSamples = 0;
  
  for (int i = 0; i < samples; i++) {
    readAccelData();
    if (magnitude > 0) {
      sumMagnitude += magnitude;
      validSamples++;
    }
    delay(20);
  }
  
  if (validSamples > 0) {
    baselineMagnitude = sumMagnitude / validSamples;
    Serial.printf("Calibrado: %.3fg\n", baselineMagnitude);
  }
}

void checkSerialCommands() {
  if (Serial.available()) {
    String command = Serial.readString();
    command.trim();
    command.toLowerCase();
    
    if (command == "verbose") {
      verboseMode = true;
      Serial.println("Modo verbose ativado");
    } else if (command == "quiet") {
      verboseMode = false;
      Serial.println("Modo quiet ativado");
    } else if (command == "status") {
      printCurrentStatus();
    } else if (command == "calibrate") {
      calibrateSensor();
    } else if (command == "reset") {
      vibrationCount = 0;
      maxVibration = 0;
      Serial.println("Stats resetadas");
    } else if (command == "help") {
      Serial.println("Comandos:");
      Serial.println("verbose - Ativar modo detalhado");
      Serial.println("quiet - Ativar modo silencioso");
      Serial.println("status - Mostrar status atual");
      Serial.println("calibrate - Recalibrar sensor");
      Serial.println("reset - Resetar estatísticas");
    }
  }
}

void writeRegister(byte reg, byte data) {
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(reg);
  Wire.write(data);
  Wire.endTransmission();
}

// Funções de publicação MQTT otimizadas
void publishVibrationAlert(float level, float magnitude) {
  StaticJsonDocument<150> doc;
  doc["timestamp"] = millis();
  doc["level"] = level;
  doc["magnitude"] = magnitude;
  doc["type"] = "alert";
  
  char buffer[150];
  serializeJson(doc, buffer);
  mqtt.publish(topic_vibration, buffer);
}

void publishCurrentVibration() {
  StaticJsonDocument<150> doc;
  doc["timestamp"] = millis();
  doc["magnitude"] = magnitude;
  doc["vibration_level"] = abs(magnitude - baselineMagnitude);
  doc["baseline"] = baselineMagnitude;
  doc["is_vibrating"] = vibrationDetected;
  
  char buffer[150];
  serializeJson(doc, buffer);
  mqtt.publish(topic_vibration, buffer);
}

void publishVibrationSummary() {
  StaticJsonDocument<200> doc;
  doc["timestamp"] = millis();
  doc["count"] = vibrationCount;
  doc["current_magnitude"] = magnitude;
  doc["threshold"] = vibrationThreshold;
  doc["baseline"] = baselineMagnitude;
  doc["type"] = "summary";
  
  char buffer[200];
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