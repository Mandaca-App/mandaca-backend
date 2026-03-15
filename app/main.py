from fastapi import FastAPI

app = FastAPI()
# uvicorn main: app --reload


@app.get("/")
def read_root():
    return {"message": "Hello World"}
