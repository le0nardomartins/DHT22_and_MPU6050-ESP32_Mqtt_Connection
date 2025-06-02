# Sistema de Monitoramento IoT com ESP32, MQTT e Flask

Este projeto implementa um sistema de monitoramento IoT que utiliza sensores DHT22 (temperatura e umidade) e MPU6050 (acelerômetro/vibração) conectados a um ESP32, com comunicação MQTT e uma interface web interativa.

## Estrutura do Projeto

- `main.py`: Arquivo principal para iniciar todos os componentes do sistema
- `src/esp32_simulator.py`: Simulador do ESP32 que envia dados reais via MQTT
- `src/interface/`: Aplicação web Flask para visualização dos dados
  - `app.py`: Servidor Flask com integração MQTT
  - `templates/`: Templates HTML
  - `static/`: Arquivos CSS e JavaScript

## Arquitetura do Sistema

O sistema utiliza o padrão publish/subscribe via MQTT:

1. O dispositivo ESP32 (simulado) publica dados dos sensores nos tópicos MQTT
2. A interface web se inscreve nesses tópicos para receber os dados em tempo real
3. Os usuários podem enviar comandos através da interface que são publicados em um tópico de comandos
4. O ESP32 recebe e processa esses comandos

## Configuração do MQTT

- **Broker**: broker.hivemq.com
- **Porta**: 1883
- **Tópicos**:
  - `sensor/vibration`: Dados de vibração do MPU6050
  - `sensor/temperature`: Dados de temperatura do DHT22
  - `sensor/humidity`: Dados de umidade do DHT22
  - `sensor/status`: Status do dispositivo (online/offline)
  - `sensor/commands`: Comandos para o dispositivo

## Instalação de Dependências

Instale todas as dependências necessárias com:

```bash
pip install -r requirements.txt
```

**Nota**: Este projeto utiliza paho-mqtt 2.2.1+, que introduziu uma nova API de callbacks. O código foi adaptado para essa versão.

## Executando o Projeto

### Método 1: Executar tudo de uma vez (Recomendado)

Execute o arquivo principal que iniciará todos os componentes:

```bash
python main.py
```

Isso iniciará tanto o simulador ESP32 quanto a interface web. A aplicação será acessível em: http://localhost:5000

Para encerrar o sistema, pressione Ctrl+C no terminal.

### Método 2: Executar componentes separadamente

Se preferir, você pode executar cada componente separadamente.

#### Simulador ESP32

```bash
python src/esp32_simulator.py
```

#### Interface Web

```bash
python src/interface/app.py
```

Acesse a interface em: http://localhost:5000

## Funcionalidades

- **Monitoramento em tempo real**: Visualização dos dados de temperatura, umidade e vibração em gráficos atualizados a cada 3 segundos
- **Controle remoto**: Envio de comandos para o dispositivo (reset, calibração, verificação de status)
- **Status do dispositivo**: Indicação visual do estado de conexão do dispositivo
- **Simulação de anomalias**: O simulador pode gerar anomalias nos valores dos sensores para testar o sistema

## Simulador ESP32

O simulador emula um ESP32 com os seguintes sensores:
- DHT22: Temperatura e umidade
- MPU6050: Acelerômetro (vibração)

Funcionalidades do simulador:
- Gera dados realistas com variações suaves
- Responde a comandos como um dispositivo real
- Simula eventos como calibração e reset
- Pode gerar anomalias para testar o sistema de alertas

## Comandos disponíveis

A interface permite enviar os seguintes comandos:
- **Reiniciar Dispositivo**: Simula um reset do ESP32
- **Calibrar Sensores**: Simula uma calibração dos sensores
- **Verificar Status**: Solicita o status atual do dispositivo

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

## Tópicos MQTT

O sistema está configurado para receber dados dos seguintes tópicos MQTT:

- `sensor/temperature` - Temperatura em °C (formato: valor numérico)
- `sensor/humidity` - Umidade em % (formato: valor numérico)
- `sensor/vibration` - Dados de vibração (formato: JSON)
- `sensor/status` - Status do sistema (formato: JSON)
- `sensor/commands` - Canal para envio de comandos

## Sistema de Alertas Preventivos

O dashboard possui um sistema avançado de alertas que monitora continuamente os valores dos sensores e alerta preventivamente sobre:

- 🌡️ Temperaturas anormalmente altas ou baixas
- 💧 Níveis de umidade excessivos
- 📳 Vibrações que podem indicar falhas no equipamento

Os alertas são classificados em três níveis de severidade:
- **Atenção** - Valores acima do normal
- **Perigo** - Valores elevados que requerem intervenção
- **Crítico** - Valores extremos que podem causar danos imediatos

## Instalação e Execução

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/mqtt-dashboard.git
cd mqtt-dashboard
```

2. Instale as dependências:
```bash
npm install
```

3. Execute em modo de desenvolvimento:
```bash
npm start
```

4. Para build de produção:
```bash
npm run build
```

## Deploy na Vercel

Este projeto está configurado para deploy na Vercel. Para fazer o deploy:

1. Instale a CLI da Vercel (opcional):
```bash
npm install -g vercel
```

2. Deploy via CLI:
```bash
vercel
```

Ou simplesmente conecte seu repositório GitHub ao Vercel e configure o deploy automático.

O arquivo `vercel.json` já está configurado com todas as configurações necessárias, incluindo as regras de segurança para conexões WebSocket.

## Configuração MQTT

O dashboard está pré-configurado para conectar automaticamente ao broker HiveMQ:

- **Host**: broker.hivemq.com
- **Porta**: 8000 (WebSocket)
- **Tópicos**:
  - `sensor/temperature` - Temperatura em °C
  - `sensor/humidity` - Umidade em %
  - `sensor/vibration` - Dados de vibração (JSON)
  - `sensor/status` - Status do sistema (JSON)
  - `sensor/commands` - Canal para envio de comandos

**Nota para ESP32**: Configure o dispositivo para usar o mesmo broker (broker.hivemq.com) na porta 1883 (porta MQTT padrão para dispositivos).

## Hardware Compatível

Este dashboard foi projetado para ser usado com o ESP32 equipado com:
- Sensor DHT22 para temperatura e umidade
- Sensor MPU6050 para medição de vibração

## Licença

MIT
