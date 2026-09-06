import os
from agora_agent import Agora, Area

client = Agora(
    area=Area.US,
    app_id=os.environ["AGORA_APP_ID"],
    app_certificate=os.environ["AGORA_APP_CERTIFICATE"]
)

print("✅ Agora client initialized successfully!")
print(f"App ID: {client.app_id}")
