import subprocess
import threading
import time
import os
import signal
import sys
import logging

# Configuração de logs
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

def run_web_interface():
    """Executa a interface web em um processo separado"""
    print("Iniciando interface web...")
    return subprocess.Popen(["python", "src/interface/app.py"],
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          text=True)

def log_output(process, name):
    """Função para capturar e exibir a saída do processo"""
    for line in process.stdout:
        # Filtra mensagens de warning/error para exibir
        if "WARNING" in line or "ERROR" in line or "Conectado" in line:
            print(f"[{name}] {line.strip()}")

def main():
    """Função principal que inicia todos os componentes"""
    try:
        # Iniciar interface web
        web_process = run_web_interface()
        # Thread para capturar a saída do processo da interface web
        web_log_thread = threading.Thread(target=log_output, args=(web_process, "WEB"), daemon=True)
        web_log_thread.start()
        
        # Mensagem para o usuário
        print("\n" + "="*60)
        print("   Sistema de Monitoramento IoT iniciado com sucesso!")
        print("   Interface web disponível em: http://localhost:5000")
        print("   Recebendo dados dos sensores via MQTT")
        print("   Pressione Ctrl+C para encerrar o sistema")
        print("="*60 + "\n")
        
        # Esperar até que o usuário interrompa com Ctrl+C
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nEncerrando aplicação...")
    finally:
        # Encerrar processos ao sair
        if 'web_process' in locals():
            print("Encerrando interface web...")
            web_process.terminate()
            web_process.wait(timeout=5)
        
        print("\nSistema encerrado.")

if __name__ == "__main__":
    main()
