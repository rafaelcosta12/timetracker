from datetime import datetime
import json
import argparse
import requests


class TimeTracker:
    def __init__(self, filename='tracker.json'):
        self.filename = filename
        self.tracker_data = []
        self.load_tracker_data()
    
    def load_tracker_data(self):
        try:
            with open(self.filename, 'r') as f:
                self.tracker_data = json.load(f)
        except FileNotFoundError:
            self.tracker_data = []

    def start(self):
        self.start_time = datetime.now()
        
        if not self.tracker_data:
            self.tracker_data.append(("inicio", self.start_time))
        
        print(f"# Inicio da contagem {self.start_time}")

        last_task_time = self.start_time
        while True:
            current_task = self.prompt_for_task()
            if not current_task: continue

            timestamp_now = datetime.now()
            self.tracker_data.append((current_task, timestamp_now))

            elapsed_time = timestamp_now - last_task_time
            last_task_time = timestamp_now
            
            print()
            print(f"{current_task} em {elapsed_time.seconds/60:0.1f}min", flush=True)
    
    def prompt_for_task(self) -> str:
        try:
            task = input(">> ")
        except KeyboardInterrupt:
            print("# se deseja sair, precione ctrl+c novamente")
            try:
                task = input(">> ")
            except KeyboardInterrupt as ex:
                self.save_tracker_data()
                raise ex
        return task
    
    def save_tracker_data(self):
        with open(self.filename, 'w') as f:
            def custom_encoder(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return str(obj)
            json.dump(self.tracker_data, f, default=custom_encoder, indent=2)
        print(f"# Dados salvos em {self.filename}")
    
    def list_tasks(self):
        if not self.tracker_data:
            print("Nenhuma tarefa registrada.")
            return
        
        print("Tarefas registradas:")
        for task, timestamp in self.tracker_data:
            print(f"{datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M:%S')}: {task}")
        
        print(f"\nTotal de tarefas: {len(self.tracker_data)}")

    def send_to_ollama(self, model_name):
        url = "http://localhost:11434/api/generate"
        headers = {"Content-Type": "application/json"}
        data = {
            "model": model_name,
            "prompt": "Por favor, analise as seguintes tarefas registradas e me ajude a entender como posso melhorar minha produtividade:\n\n" + "\n".join([f"{task} em {datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M:%S')}" for task, timestamp in self.tracker_data]),
            "stream": False,
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            print("Resposta do modelo:", response.json().get("response", "Nenhuma resposta recebida"))
        else:
            print("Erro ao enviar tarefa para o modelo:", response.status_code, response.text)

    def send_to_deepseek(self, key=None):
        if not key:
            print("Chave de API DeepSeek não fornecida. Por favor, use o argumento -k ou --key para fornecer a chave.")
            return
        
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}"
        }
        data = {
            "model": "deepseek-chat",
            "stream": False,
            "messages": [
                {"role": "system", "content": "Você é um assistente de produtividade. Faça uma análise das tarefas registradas e uma lista com as pendências do dia."},
                {"role": "user", "content": "Aqui estão as tarefas registradas:\n\n" + "\n".join([f"{task} em {datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M:%S')}" for task, timestamp in self.tracker_data])}
            ]
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            print("Resposta do modelo:", )
            for chunk in response.json().get("choices", []):
                print(chunk.get("message", {}).get("content", "Nenhuma resposta recebida"))
        else:
            print("Erro ao enviar tarefa para o modelo:", response.status_code, response.text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Time Tracker CLI - registre e acompanhe suas tarefas e o tempo gasto nelas."
    )
    
    parser.add_argument(
        "-f", "--file", 
        type=str, 
        default="tracker.json", 
        help="Arquivo de dados do tracker (padrão: tracker.json)"
    )

    parser.add_argument(
        "-l", "--list", 
        action="store_true",
        help="Listar tarefas registradas"
    )

    parser.add_argument(
        "-s", "--send",
        type=str,
        help="Enviar tarefas para o modelo de IA (ollama)"
    )

    parser.add_argument(
        "-d", "--deepseek",
        action="store_true",
        help="Enviar tarefas para o modelo DeepSeek via API"
    )

    parser.add_argument(
        "-k", "--key",
        type=str,
        help="Chave de API para o modelo DeepSeek (se necessário)"
    )
    
    args = parser.parse_args()

    try:
        print("=" * 26, "⏰ Time Tracker", "=" * 26)
        print("Bem-vindo! Pressione Ctrl+C duas vezes para sair e salvar os dados.")
        print("Digite o nome da tarefa e pressione Enter para registrar.")
        print("-" * 70)

        time_tracker = TimeTracker(filename=args.file)
        
        if args.list:
            time_tracker.list_tasks()
            exit(0)
        
        if args.send:
            print(f"Enviando tarefas para o modelo {args.send} ...")
            time_tracker.send_to_ollama(args.send)
            exit(0)
        
        if args.deepseek:
            print("Enviando tarefas para o modelo DeepSeek API ...")
            time_tracker.send_to_deepseek(args.key)
            exit(0)
        
        time_tracker.start()
    except KeyboardInterrupt:
        print("\n# Encerrando o Time Tracker")
