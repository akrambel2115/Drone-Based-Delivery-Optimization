import asyncio
import os
import sys

from app.schemas.run import BBConfigIn, RunRequest
from app.services.solver_runner import submit_run, get_job

def test_bb():
    print("Starting B&B test")
    
    config = BBConfigIn()
    run_id = submit_run("instance_01_basic_small", "bb", config.model_dump())
    print(f"Submitted run_id: {run_id}")
    
    import time
    while True:
        job = get_job(run_id)
        if not job:
            print("Job not found!")
            break
            
        print(f"Status: {job.status}")
        if job.status in ("done", "error"):
            print(f"Result: {job.result}")
            if job.error:
                print(f"Error: {job.error}")
            break
            
        time.sleep(1)

if __name__ == "__main__":
    test_bb()
