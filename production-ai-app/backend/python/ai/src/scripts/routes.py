from fastapi import FastAPI, Request, HTTPException, Depends
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from fastapi.middleware.cors import CORSMiddleware
from .fast_dependencies import InitializeRequest
import json
import os
from .utils import generate_session_id



def setup_routes(app: FastAPI, chatbot):
    # Add CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5000",
            "http://127.0.0.1:5000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/stream")
    async def stream_chat(request: Request, prompt: str = "", session_id: str = ""):
        """Stream chat responses."""
        print(
            f"Received stream request. Prompt: {prompt[:50]}..., Session ID: {session_id}"
        )
        try:
            # Process the prompt asynchronously
            response = await chatbot.process_prompt(prompt, session_id, request)

            print("Finished processing stream request.")
            return response
        except Exception as e:
            print(f"An error occurred in stream_chat: {str(e)}")
            import traceback

            traceback.print_exc()
            raise

    @app.post("/initialize")
    async def initialize_chat(request: InitializeRequest):
        """Initialize a new chat session."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        system_messages_path = os.path.join(
            script_dir, "static", "system_messages.json"
        )

        with open(system_messages_path, "r") as f:
            system_messages = json.load(f)

        print(
            f"Received session ID: {request.session_id}"
        )  # Log the received session ID

        if not request.session_id:
            session_id = generate_session_id()
            print(f"Generated new session ID: {session_id}")
            chatbot.global_chat_history = [
                SystemMessage(content=system_messages["initial_system_message"])
            ]
        else:
            session_id = request.session_id
            print(f"Using provided session ID: {session_id}")

        return {"status": "initialized", "session_id": session_id}

    @app.get("/")
    async def read_root():
        """Root endpoint to check if the server is running."""
        return {"message": "FastAPI server is running"}
