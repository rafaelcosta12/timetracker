from datetime import datetime
import json

tracker_data = []

def main():
    print("== ⏰ Time Tracker ==")
    
    start = datetime.now()
    tracker_data.append(("inicio", start))
    print(f"# Inicio da contagem {start}")
    
    last = start
    while True:
        task = get_user_input()
        print("\033[2A")
        if not task: continue

        now = datetime.now()
        tracker_data.append((task, now))

        diff = now - last
        last = now
        
        prompt()
        print(f"{task} em {diff.total_seconds()/60:0.1f} minutos", flush=True)

def prompt():
    print(">> ", flush=True, end="")

def get_user_input():
    try:
        prompt()
        task = input()
    except KeyboardInterrupt:
        print("\033[1A")
        print("# se deseja sair, precione ctrl+c novamente")
        try:
            prompt()
            task = input()
        except KeyboardInterrupt:
            print("\033[1A")
            print("# saindo ...")
            raise
    return task

def get_date_format():
    if tracker_data[0][1].day == tracker_data[-1][1].day:
        return '%H:%M:%S'
    else:
        return '%d/%m %H:%M:%S'

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("# tarefas executadas:")
        date_format = get_date_format()
        for i, item in enumerate(tracker_data):
            name, date = item
            
            if i == 0:
                print(f"{i + 1}: {name} {date}")
                continue
            
            _, last_date = tracker_data[i - 1]
            diff = date - last_date
            print(f"{i + 1}: {name} {diff.total_seconds()/60:0.1f} segundos ({last_date.strftime(date_format)} até {date.strftime(date_format)})")
        with open(tracker_data[0][1].strftime('tracker_%d_%m_%Y.json'), "w") as f:
            f.write(json.dumps(tracker_data, default=str))