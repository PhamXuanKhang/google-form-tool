from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
import time
import threading
# import openpyxl

app = FastAPI()

class NumberData:
    def __init__(self, number: int):
        self.number = number
        self.current = 0
        self.progress = 0
        self.running = False
        self.lock = threading.Lock()

    def start(self):
        self.running = True
        self.print_numbers()

    def stop(self):
        self.running = False

    def continue_printing(self):
        self.running = True
        self.print_numbers()

    def print_numbers(self):
        while self.current <= self.number and self.running:
            with self.lock:
                print(self.current)
                self.current += 1
                self.progress = (self.current / self.number) * 100
                time.sleep(0.5)  # Simulate delay

        if self.current > self.number:
            self.save_to_excel()

    # def save_to_excel(self):
    #     wb = openpyxl.Workbook()
    #     ws = wb.active
    #     ws.title = "Numbers"
    #     ws.append(["Number"])
    #     for i in range(self.number + 1):
    #         ws.append([i])
    #     wb.save("numbers.xlsx")

number_data = None

class NumberRequest(BaseModel):
    number: int

@app.post("/api/submit")
async def submit_number(number_request: NumberRequest):
    global number_data
    number_data = NumberData(number_request.number)

@app.post("/api/start")
async def start_printing(background_tasks: BackgroundTasks):
    if number_data:
        background_tasks.add_task(number_data.start)

@app.post("/api/stop")
async def stop_printing():
    if number_data:
        number_data.stop()

@app.post("/api/continue")
async def continue_printing(background_tasks: BackgroundTasks):
    if number_data:
        background_tasks.add_task(number_data.continue_printing)

@app.get("/api/progress")
async def get_progress():
    if number_data:
        return {"progress": number_data.progress}
    return {"progress": 0}

app.mount("/", StaticFiles(directory="statuc", html=True), name="static")
