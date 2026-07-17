import asyncio, sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from src.youtube_uploader import YouTubeUploader

u = YouTubeUploader()
u.authenticate()

print("=== mine=True ===")
r1 = u.youtube.channels().list(part="id,snippet", mine=True).execute()
for ch in r1.get("items", []):
    print(f"  {ch['snippet']['title']} -> {ch['id']}")

print("\n=== managedByMe=True ===")
try:
    r2 = u.youtube.channels().list(part="id,snippet", managedByMe=True, maxResults=50).execute()
    for ch in r2.get("items", []):
        print(f"  {ch['snippet']['title']} -> {ch['id']}")
except Exception as e:
    print(f"  Error: {e}")

print("\n=== forHandle=@DreamlandNarrations ===")
try:
    r3 = u.youtube.channels().list(part="id,snippet", forHandle="@DreamlandNarrations").execute()
    for ch in r3.get("items", []):
        print(f"  {ch['snippet']['title']} -> {ch['id']}")
except Exception as e:
    print(f"  Error: {e}")

print("\n=== forHandle=@mzubairhassan18 ===")
try:
    r4 = u.youtube.channels().list(part="id,snippet", forHandle="@mzubairhassan18").execute()
    for ch in r4.get("items", []):
        print(f"  {ch['snippet']['title']} -> {ch['id']}")
except Exception as e:
    print(f"  Error: {e}")
