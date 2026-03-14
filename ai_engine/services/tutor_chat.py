from google import genai
from google.genai import types
from django.conf import settings

def ask_tutor(question, course_name, topic, history):
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    # 1. Ensure history only contains valid 'user' and 'model' turns
    # and strictly follows the User -> Model -> User pattern
    formatted_history = []
    for entry in history:
        role = "user" if entry.get('role') == 'user' else "model"
        content = entry.get('content') or ""
        
        if content:
            formatted_history.append(
                types.Content(role=role, parts=[types.Part.from_text(text=str(content))])
            )

    # 2. API Safety: Chat must start with 'user' and end with 'model' 
    # before we send the next 'user' message
    if formatted_history and formatted_history[0].role == "model":
        formatted_history.pop(0)

    system_instr = (
        f"You are a helpful AI Tutor for the course '{course_name}'. "
        f"The current topic is: {topic}."
    )

    try:
        # 3. Use the stable client.chats.create pattern
        chat = client.chats.create(
            model="gemini-2.5-flash", 
            config=types.GenerateContentConfig(
                system_instruction=system_instr,
                temperature=0.1, # Keep it focused on the course
            ),
            history=formatted_history
        )
        
        response = chat.send_message(question)
        return response.text

    except Exception as e:
        # Check your VS Code terminal for this specific output!
        print(f"--- GEMINI ERROR: {e} ---") 
        return "I'm sorry, I'm having trouble connecting to my tutor brain. Please try again in a moment."