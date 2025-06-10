import os
import asyncio
import chainlit as cl
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Get or create assistant
def get_assistant():
    if os.path.exists(".assistant_id"):
        with open(".assistant_id", "r") as f:
            return f.read().strip()
    else:
        assistant = client.beta.assistants.create(
            name="Smart Student Agent Assistant",
            instructions="""
            You are a helpful assistant for students. Your tasks are:
            - Answer academic questions in subjects like math, science, history
            - Provide practical study tips
            - Summarize small text passages (up to 500 words) into 2-3 sentences
            Respond simply, accurately, and friendly. Assume text passages need summaries.
            """,
            model="gpt-3.5-turbo",
            tools=[{"type": "code_interpreter"}]
        )
        with open(".assistant_id", "w") as f:
            f.write(assistant.id)
        return assistant.id

assistant_id = get_assistant()

@cl.on_chat_start
async def start_chat():
    thread = client.beta.threads.create()
    cl.user_session.set("thread_id", thread.id)
    await cl.Message(author="Agent", content="📚 Hi! I'm your Smart Student Assistant. Ask academic questions, request study tips, or give me text to summarize!").send()

@cl.on_message
async def handle_message(message: cl.Message):
    thread_id = cl.user_session.get("thread_id")
    
    # Add user message to thread
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message.content
    )
    
    # Create run
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id
    )
    
    # Check run status
    while run.status != "completed":
        await asyncio.sleep(0.5)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        
        if run.status == "failed":
            error_msg = run.last_error.message if run.last_error else "Unknown error"
            await cl.Message(content=f"❌ Error: {error_msg}").send()
            return
    
    # Get assistant's response
    messages = client.beta.threads.messages.list(
        thread_id=thread_id,
        order="desc",
        limit=1
    )
    
    response = messages.data[0].content[0].text.value
    await cl.Message(author="Agent", content=response).send()