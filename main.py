from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
import threading
from run_pipeline import run_full_pipeline

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello from FastAPI 2"}


def safe_run_pipeline():
    threading.Thread(target=run_full_pipeline).start() # stay responsive and doecnt block requests

# Scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(safe_run_pipeline, 'interval', seconds=30)
scheduler.start()

