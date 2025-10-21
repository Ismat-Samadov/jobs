"""
Helper script to get Telegram chat IDs from bot updates
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ Error: TELEGRAM_BOT_TOKEN not found in .env file")
    print("\nPlease add your bot token to .env:")
    print("TELEGRAM_BOT_TOKEN=your_bot_token_here")
    exit(1)

print("=" * 70)
print("TELEGRAM CHAT ID FINDER")
print("=" * 70)
print("\nFetching updates from your bot...")

try:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    response = requests.get(url, timeout=10)

    if response.status_code != 200:
        print(f"\n❌ Error: HTTP {response.status_code}")
        print(f"Response: {response.text}")
        exit(1)

    data = response.json()

    if not data.get('ok'):
        print(f"\n❌ Error: {data.get('description', 'Unknown error')}")
        exit(1)

    updates = data.get('result', [])

    if not updates:
        print("\n⚠️  No messages found!")
        print("\nTo get your chat ID:")
        print("1. Add your bot to the 'BoB' group")
        print("2. Send a message in the group (like 'Hello Bot!')")
        print("3. Run this script again")
        exit(0)

    # Extract unique chats
    chats = {}
    for update in updates:
        message = update.get('message', {})
        chat = message.get('chat', {})

        chat_id = chat.get('id')
        chat_type = chat.get('type')
        chat_title = chat.get('title', chat.get('first_name', 'Unknown'))

        if chat_id and chat_id not in chats:
            chats[chat_id] = {
                'type': chat_type,
                'title': chat_title
            }

    print(f"\n✓ Found {len(chats)} chat(s):\n")
    print("-" * 70)

    for chat_id, info in chats.items():
        chat_type = info['type']
        chat_title = info['title']

        # Emoji based on type
        emoji = "👥" if chat_type in ['group', 'supergroup'] else "👤"

        print(f"{emoji} {chat_type.upper():<12} | {chat_title:<30} | ID: {chat_id}")

    print("-" * 70)

    # Find BoB group and personal chat
    bob_group = None
    personal_chat = None

    for chat_id, info in chats.items():
        if 'bob' in info['title'].lower():
            bob_group = chat_id
        elif info['type'] == 'private':
            personal_chat = chat_id

    # Build configuration
    print("\n" + "=" * 70)
    print("RECOMMENDED CONFIGURATION")
    print("=" * 70)

    if bob_group and personal_chat:
        print(f"\n✓ Found both personal chat and 'BoB' group!")
        print(f"\n📋 Update your .env file with (sends to BOTH):")
        print(f"   TELEGRAM_CHAT_ID={personal_chat},{bob_group}")
        print(f"\n   Personal: {personal_chat}")
        print(f"   Group:    {bob_group}")
    elif bob_group:
        print(f"\n✓ Found 'BoB' group!")
        print(f"\n📋 Update your .env file with:")
        print(f"   TELEGRAM_CHAT_ID={bob_group}")
    elif personal_chat:
        print(f"\n✓ Found personal chat!")
        print(f"\n📋 Update your .env file with:")
        print(f"   TELEGRAM_CHAT_ID={personal_chat}")
    else:
        print("\n⚠️  No suitable chats found.")
        print("\nTo get chat IDs:")
        print("1. Send a message to your bot (personal)")
        print("2. Add bot to 'BoB' group and send a message there")
        print("3. Run this script again")

    print("\n" + "=" * 70)

except requests.exceptions.RequestException as e:
    print(f"\n❌ Network error: {e}")
    exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    exit(1)
