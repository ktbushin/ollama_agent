# Start up the OLLAMA Server
# $ ollama serve

# Activate/Deactivate python venv
# source ./GenAI[venv name]/bin/activate
# source ./GenAI[venv name]/bin/deactivate

from ollama import Client
import time

client = Client(host="http://192.168.11.27:11434")

start_time = time.time()

response = client.chat(model="llama3.2", messages=[
    {
       "role" : "user",
       "content" : "why is the sky blue? Answer within 100 words",
    },
])

print(response["message"]["content"])

end_time = time.time()

print()

print(f"処理時間:{end_time - start_time:.3f}[sec]")