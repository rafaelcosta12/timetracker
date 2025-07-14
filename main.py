from datetime import datetime
import json
import argparse
import requests
from rich.console import Console
from rich.markdown import Markdown
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory


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
        self.workflow_assistants = []
        self.main_workflow_assistant = None
        self._load_config_file()
        self._load_tracker_data()
        self._configure_main_assistant()

    def _configure_main_assistant(self):
        for assistant in self.workflow_assistants:
            if assistant.prefix == 'default':
                self.main_workflow_assistant = assistant
        else:
            self.main_workflow_assistant = AssistentDefinition(
                name="Assistente de Produtividade",
                prefix="default",
                instructions="Você é um assistente de produtividade. Sempre responda de forma clara e objetiva. Pode categorizar tarefas e incluir dados de tempo e sugestões de melhoria.",
                default_message="Com base nas tarefas, faça um resumo do que fiz hoje ({today}) e quais são as minhas póximas prioridades."
            )
            self.workflow_assistants.append(self.main_workflow_assistant)

    def _load_config_file(self):
        try:
            with open(self.cfg_file, 'r') as json_file:
                configuration = json.load(json_file)
                self.deepseek_key = configuration.get('deepseek_key', None) or self.deepseek_key
                self.context_size = configuration.get('context_size', self.context_size)
                for i, assistant_config in enumerate(configuration.get('assistents', [])):
                    self.workflow_assistants.append(AssistentDefinition(
                        name=assistant_config.get('name', 'Assistente Desconhecido'),
                        prefix=assistant_config.get('prefix', f'assistente_{i}'),
                        instructions=assistant_config.get('instructions', 'Você é um assistente de IA.'),
                        default_message=assistant_config.get('default_message', 'Pode me ajudar com as tarefas registradas?')
                    ))
        except FileNotFoundError:
            pass

    def _load_tracker_data(self):
        try:
            with open(self.filename, 'r') as tracker_file:
                for entry_line in json.load(tracker_file):
                    self.tracker_data.append((entry_line[0], datetime.fromisoformat(entry_line[1])))
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
            
            if not current_task: 
                continue

            if current_task.startswith("/"):
                command, params = (current_task + " ").split(" ", 1)
                self._handle_command(command, params)
                continue

            timestamp_now = datetime.now()
            self.tracker_data.append((current_task, timestamp_now))

            elapsed_time = timestamp_now - last_task_time
            last_task_time = timestamp_now
            
            print()
            tempo_str = f"{elapsed_time.seconds // 3600:02}h {(elapsed_time.seconds // 60) % 60:02}m {elapsed_time.seconds % 60:02}s"
            print(f"# {tempo_str}", flush=True)

    def _handle_command(self, command: str, params: str):
        # comando para registrar tarefas com data anterior
        if command == "/t":
            if not params.strip():
                print("Por favor, forneça a data e hora no formato 'YYYY-MM-DD HH:MM:SS'.")
                return
            try:
                task_time = datetime.strptime(params.strip(), '%Y-%m-%d %H:%M:%S')
                self.tracker_data.append((self._prompt_for_task(), task_time))
                print(f"Tarefa registrada para {task_time.strftime('%Y-%m-%d %H:%M:%S')}")
            except ValueError:
                print("Formato de data inválido. Use 'YYYY-MM-DD HH:MM:SS'.")
            return

        # comando para editar tarefas anteriores
        if command == "/e":
            if not params.strip():
                print("Por favor, forneça o índice da tarefa a ser editada.")
                return
            try:
                index = int(params.strip())
                if 0 <= index < len(self.tracker_data):
                    new_task = self._prompt_for_task()
                    self.tracker_data[index] = (new_task, self.tracker_data[index][1])
                    print(f"Tarefa {index} editada para: {new_task}")
                else:
                    print("Índice inválido.")
            except ValueError:
                print("Por favor, forneça um número válido para o índice da tarefa.")
            return

        # mensagem personalizada para deepseek
        if command == "/d":
            if self.main_workflow_assistant is None:
                print("Nenhum assistente principal configurado. Use /c para configurar.")
                return
            self._send_to_deepseek(self.main_workflow_assistant, params.strip())
        
        # comando para configurar assistente
        if command == "/c":
            if not params.strip():
                print("Por favor, forneça o prefixo do assistente.")
                return
            prefix = params.strip()
            for workflow_assistant in self.workflow_assistants:
                if workflow_assistant.prefix == prefix:
                    self.main_workflow_assistant = workflow_assistant
                    print(f"Assistente principal configurado: {workflow_assistant.name}")
                    return
        
        # listar assistentes
        if command == "/a":
            if not self.workflow_assistants:
                print("Nenhum assistente configurado.")
            else:
                print("Assistentes configurados:")
                for assistant in self.workflow_assistants:
                    print(f" - {assistant.name} (prefixo: {assistant.prefix})")

        # comando para listar tarefas
        if command == "/l":
            self._list_tasks()

        # comando para enviar tarefas para o modelo ollama, implementar depois
        if command == "/s":
            pass
        
        # comando para salvar dados
        if command == "/w":
            self._save_tracker_data()
            print("# Dados salvos com sucesso")
        
        for workflow_assistant in self.workflow_assistants:
            if command == f"/{workflow_assistant.prefix}":
                message = params.strip()
                self._send_to_deepseek(workflow_assistant, message)

    def _prompt_for_task(self) -> str:
        try:
            task = prompt('>> ',
             history=FileHistory('.history.txt'),
             auto_suggest=AutoSuggestFromHistory(),
             mouse_support=True)
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
            json.dump(self.tracker_data, f, default=custom_encoder, indent=2, ensure_ascii=False)
        print(f"# Dados salvos em {self.filename}")
    
    def _list_tasks(self):
        if not self.tracker_data:
            print("Nenhuma tarefa registrada.")
            return

        print("Tarefas registradas (total: {}, contexto: {}):".format(len(self.tracker_data), self.context_size))
        for task, timestamp in self.tracker_data[-self.context_size:]:
            print(f"{timestamp.strftime('%d/%m %H:%M:%S')}: {task.capitalize()}")

    def _send_to_deepseek(self, assistent: AssistentDefinition, message=None):
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
        default="tracker.json", 
        help="Arquivo de dados do tracker (padrão: tracker.json)"
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
        print("Bem-vindo! Pressione Ctrl+C para sair e salvar os dados.")
        print("Digite o nome da tarefa e pressione Enter para registrar.")
        print("-" * 70)

        time_tracker = TimeTracker(
            filename=args.file, 
            deepseek_key=args.deepseek_key, 
            cfg_file=args.cfg_file
        )

        time_tracker.start_cli()
    except KeyboardInterrupt:
        print("\n# Encerrando o Time Tracker")
