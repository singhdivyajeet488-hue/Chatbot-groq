import os
import discord
from discord import app_commands
from discord.ext import commands
import requests
from dotenv import load_dotenv

# Load variables from environment (.env or Railway dashboard)
load_dotenv()

class ChatBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.monitored_channels = {}

    async def setup_hook(self):
        await self.tree.sync()
        print("Bot is online. Only Chat automation is active.")

bot = ChatBot()

# --- AUTOMATED CHAT CONTROL COMMANDS ---
@bot.tree.command(name="ai", description="Toggle auto-chat logic for a chosen text channel.")
@app_commands.choices(action=[
    app_commands.Choice(name="Start", value="start"), 
    app_commands.Choice(name="Stop", value="stop")
])
async def ai_control(interaction: discord.Interaction, action: str, target_channel: discord.TextChannel):
    if action == "start":
        bot.monitored_channels[target_channel.id] = True
        await interaction.response.send_message(f"✅ AI automation active in {target_channel.mention}")
    else:
        bot.monitored_channels.pop(target_channel.id, None)
        await interaction.response.send_message(f"❌ AI automation deactivated in {target_channel.mention}")

# --- CONCURRENT TEXT CHANNEL PASS-THROUGH LISTENER ---
@bot.event
async def on_message(message):
    if message.author == bot.user: 
        return
        
    if message.channel.id in bot.monitored_channels:
        async with message.channel.typing():
            try:
                headers = {
                    "Authorization": f"Bearer {os.environ.get('GROQ_API_KEY')}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": message.content}]
                }
                
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    json=payload,
                    headers=headers
                )
                
                reply = response.json()["choices"][0]["message"]["content"]
                await message.channel.send(reply)
            except Exception as e:
                print(f"Groq Chat Stream Error: {e}")
                
    await bot.process_commands(message)

# Run client using securely mapped container key bindings
bot.run(os.environ.get("DISCORD_TOKEN"))
