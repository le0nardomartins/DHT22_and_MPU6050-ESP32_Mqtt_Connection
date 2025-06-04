# Sistema de Monitoramento IoT com ESP32, MQTT e Flask

Este projeto implementa um sistema de monitoramento IoT que utiliza sensores DHT22 (temperatura e umidade) e MPU6050 (acelerômetro/vibração) conectados a um ESP32, com comunicação MQTT e uma interface web interativa.

## Estrutura do Projeto

- `main.py`: Arquivo principal para iniciar todos os componentes do sistema
- `src/interface/`: Aplicação web Flask para visualização dos dados
  - `app.py`: Servidor Flask com integração MQTT
  - `templates/`: Templates HTML
  - `static/`: Arquivos CSS e JavaScript

## Arquitetura do Sistema

O sistema utiliza o padrão publish/subscribe via MQTT:

1. O dispositivo ESP32 publica dados dos sensores nos tópicos MQTT
2. A interface web se inscreve nesses tópicos para receber os dados em tempo real
3. Os usuários podem enviar comandos através da interface que são publicados em um tópico de comandos
4. O ESP32 recebe e processa esses comandos

## Instalação de Dependências

Instale todas as dependências necessárias com:

```bash
pip install -r requirements.txt
```

## Executando o Projeto

Execute o arquivo principal que iniciará todos os componentes:

```bash
python main.py
```

A aplicação será acessível em: http://localhost:5000

Para encerrar o sistema, pressione Ctrl+C no terminal.

## Requisitos

- Python 3.6+
- Flask
- Paho-MQTT 2.2.1+
- Chart.js (incluído via CDN)
- Bootstrap 5 (incluído via CDN)

## Características

- 📊 Visualização em tempo real dos dados dos sensores
- 🔔 Sistema de alertas para eventos extremos
- 📈 Gráficos históricos para temperatura, umidade e vibração
- 📱 Interface responsiva para desktop e mobile

## Sistema de Alertas Preventivos

O dashboard possui um sistema avançado de alertas que monitora continuamente os valores dos sensores e alerta preventivamente sobre:

- 🌡️ Temperaturas anormalmente altas ou baixas
- 💧 Níveis de umidade excessivos
- 📳 Vibrações que podem indicar falhas no equipamento

Os alertas são classificados em três níveis de severidade:
- **Atenção** - Valores acima do normal
- **Perigo** - Valores elevados que requerem intervenção
- **Crítico** - Valores extremos que podem causar danos imediatos

## Hardware Compatível

Este dashboard foi projetado para ser usado com o ESP32 equipado com:
- Sensor DHT22 para temperatura e umidade
- Sensor MPU6050 para medição de vibração
