from typing import Type
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict
from langchain_openai import ChatOpenAI
import time
from crewai import Agent, LLM, Task, Crew, Process
from crewai_tools import SerperDevTool
from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
import os

# Import the synchronous functions from websocket_server
from websocket_server import start_server, send_question, get_answer

# Tool Implementation
class QuestionAskingToolInput(BaseModel):
    """Input schema for QuestionAskingTool."""
    question: str = Field(..., description='question for context')

class QuestionAskingTool(BaseTool):
    name: str = "Human Input Tool"
    description: str = "Ask questions and get answers from a human through a websocket connection"
    args_schema: Type[BaseModel] = QuestionAskingToolInput

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, question: str) -> str:
        """Run the tool synchronously.
        
        Args:
            question: The question to ask the human
            
        Returns:
            The human's answer as a string
        """
        print(f"Asking human: {question}")
        
        # Send the question to the client
        send_question(question)
        
        # Wait for the answer
        answer = get_answer(timeout=180)
        print(f"Received answer: {answer}")
        
        return answer

    async def _arun(self, question: str) -> str:
        """This tool only supports synchronous operations."""
        if isinstance(question, dict) and "question" in question:
            question = question["question"]
        return self._run(question)

def run_crew_ai():
    # Start the FastAPI server in a background thread
    server_thread = start_server()
    
    # Wait for the server to start
    print("Waiting for server to start...")
    time.sleep(5)
    
    print("Server started. Please connect to http://localhost:8000 in your browser.")
    print("Waiting for a client to connect...")
    
    # Initialize the Gemini LLM using CrewAI's LLM wrapper
    my_llm = LLM(
        api_key=os.getenv("GOOGLE_API_KEY"),
        model="gemini/gemini-1.5-flash",
        temperature=0.1,
        verbose=True
    )
    
    # Create the human input tool
    human_input_tool = QuestionAskingTool()
    
    # Define your agent with the tool
    poem_writer = Agent(
        role="Creative Poet",
        goal="Craft an engaging poem based on user-provided words. "
            "First, ask the user how many words (between 1 and 5) they want to rhyme around. "
            "Then, ask for that many words before composing a final poem."
            "Send the final response to the user again",
        verbose=True,
        memory=True,
        backstory=(
            "A master of rhythm and rhyme, you weave words into captivating poetry that resonates with emotions and themes."
        ),
        llm=my_llm,
        tools=[human_input_tool]  # The tool for interacting with the user
    )

    # Define tasks
    poetry_task = Task(
        description=(
            "Engage with the user to determine the number of words for the poem (max 5, min 1). "
            "Then, gather the specified words one by one through an interactive Q&A process. "
            "Once all words are collected, compose a creative and compelling poem around them."
        ),
        expected_output='A beautifully crafted poem using the words provided by the user.',
        agent=poem_writer
    )

    # Create and run the crew
    crew = Crew(
        agents=[poem_writer],
        tasks=[poetry_task],
        process=Process.sequential,
    )

    # Run the crew and get the result
    # answer = get_answer(timeout=180)
    result = crew.kickoff()
    print("\nFinal Result:", result)
    
    # Send the final result
    send_question(f"FINAL REPORT: {result}")
    
    print("\nCrewAI process completed! The final report has been sent to the client.")
    print("The server will continue running. Press Ctrl+C to exit.")
    
    # Keep the program running so the server thread stays alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")

if __name__ == "__main__":
    run_crew_ai()