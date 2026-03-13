import os
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

# Initialize the Gemini Client
# The SDK automatically looks for the GEMINI_API_KEY if you've set it in .env
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def generate_schedule(prompt):
    try:
        # We use 'gemini-1.5-flash' because it is optimized for 
        # speed and high-volume tasks like your CV analyzer
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return None