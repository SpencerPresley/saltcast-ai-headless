from fastapi import FastAPI
from scripts.chatbot import Chatbot
from scripts.routes import setup_routes


def create_app():
    app = FastAPI()
    chatbot = Chatbot(
        project_name="Salinity",
        database_name="index",
    )
    setup_routes(app, chatbot)
    return app, chatbot


app, chatbot = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
