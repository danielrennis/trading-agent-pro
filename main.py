import os
import sys
import subprocess
import time

def run():
    # Asegurar que estamos en el directorio raíz del proyecto
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    print("-" * 60)
    print("💹 TRADING BOT PRO - INICIANDO SISTEMA")
    print("-" * 60)
    
    # Verificamos si existe el venv para activarlo o usar su python
    python_exec = sys.executable
    venv_python = os.path.join(base_dir, "venv", "bin", "python")
    if os.path.exists(venv_python):
        python_exec = venv_python
        print(f"📦 Usando entorno virtual: {venv_python}")

    print("🚀 Levantando Servidor y Orquestador...")
    print("🌍 Panel disponible en: http://localhost:3000")
    print("-" * 60)
    
    try:
        # Iniciamos el web_server.py (que a su vez inicia el orchestrator.py)
        # Usamos subprocess.run para que el proceso actual espere y muestre los logs
        subprocess.run([python_exec, "web_server.py"])
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo el bot...")
        # Matar procesos hijos si quedaron colgados
        os.system("pkill -f orchestrator.py")
        print("✅ Sistema apagado.")

if __name__ == "__main__":
    run()
