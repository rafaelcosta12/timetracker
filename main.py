from datetime import datetime
import json
import argparse

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
        
        time_tracker.start()
    except KeyboardInterrupt:
        print("\n# Encerrando o Time Tracker")
