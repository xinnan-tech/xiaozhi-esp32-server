import asyncio
import edge_tts

async def list_voices():
    voices = await edge_tts.VoicesManager.create()
    en_gb_voices = voices.find(Language="en", Locale="en-GB")
    for v in en_gb_voices:
        print(f"{v['ShortName']} ({v['Gender']})")

if __name__ == "__main__":
    asyncio.run(list_voices())
