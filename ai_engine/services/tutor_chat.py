import anthropic
from django.conf import settings

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

def ask_tutor(question, course_name, topic, chat_history=None):
    """
    Ask AI tutor a question. chat_history is a list of {role, content} dicts.
    """
    system_prompt = f"""You are an expert AI tutor helping a student with their course "{course_name}", currently studying the topic "{topic}".

Your role:
- Answer questions clearly and simply
- Give examples when explaining concepts
- Encourage the student
- Keep responses concise (max 3-4 paragraphs)
- If you give code, keep it short and well-commented"""

    messages = []
    if chat_history:
        messages.extend(chat_history)
    messages.append({"role": "user", "content": question})

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=system_prompt,
            messages=messages
        )
        return response.content[0].text
    except Exception as e:
        print(f"Tutor AI Error: {e}")
        return "Sorry, I couldn't process your question right now. Please try again."