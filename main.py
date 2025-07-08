from datetime import datetime
import json
import argparse
import requests
from rich.console import Console
from rich.markdown import Markdown

class AssistentDefinition:
    def __init__(self, name: str, instructions: str, default_message: str = None, prefix: str = None):
        self.prefix = prefix
        self.instructions = instructions
        self.name = name
        self.default_message = default_message


class TimeTracker:
    def __init__(self, filename='tracker.json', deepseek_key=None, cfg_file='config.json'):
        self.filename = filename
        self.tracker_data = []
        self.deepseek_key = deepseek_key
        self.cfg_file = cfg_file
        self.context_size = 100
        self.assistents = [
            AssistentDefinition(
                name="Assistente de Produtividade",
                prefix="default",
                instructions="Você é um assistente de produtividade. Sempre responda de forma clara e objetiva. Pode categorizar tarefas e incluir dados de tempo e sugestões de melhoria.",
                default_message="Com base nas tarefas, faça um resumo do que fiz hoje ({today}) e quais são as minhas póximas prioridades."
            )
        ]
        self.productivity_assistant = self.assistents[0]
        self._load_config_file()
        self._load_tracker_data()
    
    def _load_config_file(self):
        try:
            with open(self.cfg_file, 'r') as f:
                config = json.load(f)
                self.deepseek_key = config.get('deepseek_key', None) or self.deepseek_key
                self.context_size = config.get('context_size', self.context_size)
                for i, a in enumerate(config.get('assistents', [])):
                    self.assistents.append(AssistentDefinition(
                        name=a.get('name', 'Assistente Desconhecido'),
                        prefix=a.get('prefix', f"assistente_{i}"),
                        instructions=a.get('instructions', "Você é um assistente de IA."),
                        default_message=a.get('default_message', "Pode me ajudar com as tarefas registradas?")
                    ))
        except FileNotFoundError:
            pass

    def _load_tracker_data(self):
        try:
            with open(self.filename, 'r') as f:
                for l in json.load(f):
                    self.tracker_data.append((l[0], datetime.fromisoformat(l[1])))
        except FileNotFoundError:
            self.tracker_data = []

    def start_cli(self):
        if not self.tracker_data:
            self.start_time = datetime.now()
            self.tracker_data.append(("inicio", self.start_time))
            print(f"# Horário atual {self.start_time}")
        else:
            self.start_time = self.tracker_data[-1][1]
            print(f"# Última iteração {self.start_time}")
        
        last_task_time = self.start_time
        
        while True:
            current_task = self._prompt_for_task()
            if not current_task: continue

            if current_task.startswith("/"):
                command, params = (current_task + " ").split(" ")

                # mensagem personalizada para deepseek
                if command == "/d":
                    self.send_to_deepseek(self.productivity_assistant, params.strip())

                # comando para listar tarefas
                if command == "/l":
                    self.list_tasks()

                # comando para enviar tarefas para o modelo ollama, implementar depois
                if command == "/s":
                    pass

                # comando para sair
                if command == "/q":
                    self._save_tracker_data()
                    print("# Encerrando o Time Tracker")
                    break
                
                # comando para salvar dados
                if command == "/w":
                    self._save_tracker_data()
                
                for assistent in self.assistents:
                    if command == f"/{assistent.prefix}":
                        message = params.strip()
                        self.send_to_deepseek(assistent, message)
                
                continue

            timestamp_now = datetime.now()
            self.tracker_data.append((current_task, timestamp_now))

            elapsed_time = timestamp_now - last_task_time
            last_task_time = timestamp_now
            
            print()
            tempo_str = f"{elapsed_time.seconds // 3600:02}h {(elapsed_time.seconds // 60) % 60:02}m {elapsed_time.seconds % 60:02}s"
            print(f"# {tempo_str}", flush=True)

    def _prompt_for_task(self) -> str:
        try:
            task = input(">> ")
        except KeyboardInterrupt as ex:
            self._save_tracker_data()
            raise ex
        return task
    
    def _save_tracker_data(self):
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
            print(f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')}: {task.capitalize()}")
        
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

    def send_to_deepseek(self, assistent: AssistentDefinition, message=None):
        if not self.deepseek_key:
            print("Chave de API DeepSeek não fornecida. Por favor, use o argumento -k ou --key para fornecer a chave.")
            return

        message = (message or assistent.default_message).format(
            today=datetime.today().date(),
        )

        tasks = self.tracker_data[-self.context_size:]  # limita o contexto ao tamanho máximo
        response = requests.post("https://api.deepseek.com/chat/completions", headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.deepseek_key}"
        }, json={
            "model": "deepseek-chat",
            "stream": False,
            "messages": [
                {"role": "system", "content": assistent.instructions},
                {"role": "user", "content": "Tarefas registradas:\n\n" + "\n".join([f"{task} em {timestamp.strftime('%Y-%m-%d %H:%M:%S')}" for task, timestamp in tasks])},
                {"role": "user", "content": message}
            ]
        })

        if response.status_code == 200:
            print("Resposta do modelo:", )
            print()
            console = Console()
            for chunk in response.json().get("choices", []):
                content = chunk.get("message", {}).get("content", "")
                console.print(Markdown(content))
        else:
            print("Erro ao enviar tarefa para o modelo:", response.status_code, response.text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Time Tracker CLI - registre e acompanhe suas tarefas e o tempo gasto nelas."
    )
    
    parser.add_argument(
        "-f", "--file", 
        type=str, 
        default=datetime.today().strftime('%Y-%m-%d') + ".json", 
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
        "-k", "--deepseek_key",
        type=str,
        help="Chave de API para o modelo DeepSeek (se necessário)"
    )

    parser.add_argument(
        "-c", "--cfg-file",
        type=str,
        default="config.json",
        help="Arquivo de configuração (padrão: config.json)"
    )
    
    args = parser.parse_args()

    try:
        print("=" * 26, "⏰ Time Tracker", "=" * 26)
        print("Bem-vindo! Pressione Ctrl+C duas vezes para sair e salvar os dados.")
        print("Digite o nome da tarefa e pressione Enter para registrar.")
        print("-" * 70)

        time_tracker = TimeTracker(filename=args.file, deepseek_key=args.deepseek_key, cfg_file=args.cfg_file)
        
        if args.list:
            time_tracker.list_tasks()
            exit(0)
        
        if args.send:
            print(f"Enviando tarefas para o modelo {args.send} ...")
            time_tracker.send_to_ollama(args.send)
            exit(0)
        
        if args.deepseek:
            print("Enviando tarefas para o modelo DeepSeek API ...")
            time_tracker.send_to_deepseek()
            exit(0)
        
        time_tracker.start_cli()
    except KeyboardInterrupt:
        print("\n# Encerrando o Time Tracker")
