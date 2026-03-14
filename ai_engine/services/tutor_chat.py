from google import genai
from google.genai import types
from django.conf import settings

def ask_tutor(question, course_name, topic, history):
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    # Standardize history for the Gemini API
    formatted_history = []
    for entry in history:
        # Map roles correctly: 'assistant' or 'model' becomes 'model'
        role = "user" if entry['role'] == 'user' else "model"
        # Gemini expects 'parts' to be a list or a string depending on the SDK version
        content = entry.get('parts') or entry.get('content')
        
        formatted_history.append(
            types.Content(role=role, parts=[types.Part.from_text(text=content)])
        )

    system_instr = (
        f"You are a helpful AI Tutor for the course '{course_name}'. "
        f"The student is currently focused on the topic: {topic}. "
        "Keep your answers educational, clear, and encouraging."
    )

    try:
        # Start the chat session with history
        chat = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(system_instruction=system_instr),
            history=formatted_history
        )
        
        response = chat.send_message(question)
        return response.text

    except Exception as e:
        print(f"Chat API Error: {e}")
        return "I'm sorry, I'm having trouble connecting to my tutor brain. Please try again in a moment!"