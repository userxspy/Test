import asyncio
from google import genai
from hydrogram import Client, filters
from info import GEMINI_API_KEY

# ==========================================
# 🧠 GEMINI CONFIG (STABLE)
# ==========================================

GEMINI_MODEL = "gemini-1.5-flash"

ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# ==========================================
# 🗣️ AI CHAT COMMAND
# ==========================================

@Client.on_message(filters.command(["ask", "ai"]))
async def ask_ai(client, message):
    if not ai_client:
        return await message.reply("❌ AI API Key missing.")

    prompt = None

    # Direct command: /ask hello
    if len(message.command) > 1:
        prompt = message.text.split(None, 1)[1]

    # Reply to text or caption
    elif message.reply_to_message:
        prompt = (
            message.reply_to_message.text
            or message.reply_to_message.caption
        )

    if not prompt or not prompt.strip():
        return await message.reply(
            "⚡ **Gemini AI**\n\n"
            "Usage:\n"
            "• `/ask Who is Batman?`\n"
            "• Reply to text/caption with `/ask`"
        )

    status = await message.reply("⚡ Thinking...")

    try:
        loop = asyncio.get_running_loop()

        response = await loop.run_in_executor(
            None,
            lambda: ai_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )
        )

        text = response.text or "❌ No response from AI."

        if len(text) > 4000:
            for i in range(0, len(text), 4000):
                await message.reply(text[i:i + 4000])
            await status.delete()
        else:
            await status.edit(text)

    except Exception as e:
        await status.edit(f"❌ Error: `{e}`")
