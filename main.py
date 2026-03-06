from fastapi import FastAPI
import uvicorn 


def main():
    app = FastAPI()

    @app.get("/")
    def read_root():
        return {"message": "Hello from ashell!"}

    @app.get("/hello")
    def hello():
        return {"message": "Hello!"}

    @app.get("/new")
    def new_route():
        return {"message": "New route"}

    @app.get("/another")
    def another_route():
        return {"message": "Another route"}

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
