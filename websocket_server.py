import threading
import time
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import webbrowser

# Create FastAPI app
app = FastAPI()

# HTML interface for user interaction
html = """
<!DOCTYPE html>
<html>
    <head>
        <title>CrewAI Human Input</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            #messages {
                margin-bottom: 20px;
                padding: 20px;
                border: 1px solid #ddd;
                height: 400px;
                overflow-y: auto;
            }
            .question {
                background-color: #f0f0f0;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 10px;
            }
            .answer {
                background-color: #e6f7ff;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 10px;
                margin-left: 20px;
            }
            #answerForm {
                display: flex;
                gap: 10px;
            }
            #answerInput {
                flex-grow: 1;
                padding: 8px;
            }
            button {
                padding: 8px 16px;
                background-color: #4CAF50;
                color: white;
                border: none;
                cursor: pointer;
            }
        </style>
    </head>
    <body>
        <h1>CrewAI Human Input Interface</h1>
        <div id="messages"></div>
        <form id="answerForm">
            <input type="text" id="answerInput" placeholder="Type your answer here...">
            <button type="submit">Send</button>
        </form>
        <script>
            var ws = new WebSocket("ws://" + window.location.host + "/ws");
            var messagesDiv = document.getElementById("messages");
            var answerForm = document.getElementById("answerForm");
            var answerInput = document.getElementById("answerInput");
            
            ws.onmessage = function(event) {
                var data = JSON.parse(event.data);
                if (data.question) {
                    var questionDiv = document.createElement("div");
                    questionDiv.className = "question";
                    questionDiv.textContent = "Agent: " + data.question;
                    messagesDiv.appendChild(questionDiv);
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    answerInput.focus();
                }
            };
            
            answerForm.addEventListener("submit", function(event) {
                event.preventDefault();
                if (answerInput.value) {
                    var answerDiv = document.createElement("div");
                    answerDiv.className = "answer";
                    answerDiv.textContent = "You: " + answerInput.value;
                    messagesDiv.appendChild(answerDiv);
                    ws.send(answerInput.value);
                    answerInput.value = "";
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                }
            });
        </script>
    </body>
</html>
"""

# Global variables for communication
latest_question = None
latest_answer = None
active_websocket = None

@app.get("/")
def get_page():
    """Returns the HTML interface for user interaction."""
    return HTMLResponse(html)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handles WebSocket connections for real-time communication."""
    global latest_answer, active_websocket
    await websocket.accept()
    active_websocket = websocket
    await websocket.send_json({"question": "Connected! Waiting for the AI agent to start..."})
    
    try:
        while True:
            latest_answer = await websocket.receive_text()
    except WebSocketDisconnect:
        active_websocket = None
        print("WebSocket disconnected")


def start_server():
    """Starts the FastAPI server in a separate thread and opens the web interface automatically."""
    server_thread = threading.Thread(
        target=lambda: uvicorn.run(app, host="0.0.0.0", port=8000),
        daemon=True
    )
    server_thread.start()
    time.sleep(2)  # Give server a moment to start
    webbrowser.open("http://localhost:8000")
    print("FastAPI server started on http://localhost:8000")
    return server_thread


def send_question(question):
    """Sends a question to the client synchronously and updates the UI."""
    global latest_question, active_websocket
    latest_question = question
    if active_websocket:
        import asyncio
        asyncio.run(active_websocket.send_json({"question": question}))
    return True


def get_answer(timeout=180):
    """Retrieves an answer from the client synchronously with a timeout."""
    global latest_answer
    start_time = time.time()
    while latest_answer is None:
        if time.time() - start_time > timeout:
            return "No response received within the timeout period."
        time.sleep(1)
    answer = latest_answer
    latest_answer = None
    return answer