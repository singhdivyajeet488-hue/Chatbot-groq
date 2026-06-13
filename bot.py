import os
import discord
from discord import app_commands
from discord.ext import commands
import requests
import aiohttp
from dotenv import load_dotenv

load_dotenv()

class UnifiedBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.monitored_channels = {}

    async def setup_hook(self):
        await self.tree.sync()
        print("Bot online and commands synced.")

bot = UnifiedBot()

# --- CHAT COMMANDS ---
@bot.tree.command(name="ai", description="Toggle auto-chat for a channel.")
@app_commands.choices(action=[app_commands.Choice(name="Start", value="start"), app_commands.Choice(name="Stop", value="stop")])
async def ai_control(interaction: discord.Interaction, action: str, target_channel: discord.TextChannel):
    if action == "start":
        bot.monitored_channels[target_channel.id] = {"active": True, "history": [{"role": "system", "content": "You are a helpful AI assistant."}]}
        await interaction.response.send_message(f"AI chat enabled in {target_channel.mention}")
    else:
        bot.monitored_channels.pop(target_channel.id, None)
        await interaction.response.send_message(f"AI chat disabled in {target_channel.mention}")

# --- IMAGE COMMAND ---
@bot.tree.command(name="imagine", description="Generate a high-quality image.")
async def imagine(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    
    # We use Stable Diffusion API structure
    url = "https://stablediffusionapi.com/api/v4/dreambooth"
    payload = {
        "key": os.environ.get("IMAGE_API_KEY"),
        "prompt": prompt,
        "width": "512",
        "height": "512",
        "samples": "1",
        "num_inference_steps": "30"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            data = await response.json()
            if "output" in data and data["output"]:
                await interaction.followup.send(f"**{prompt}**\n{data['output'][0]}")
            else:
                await interaction.followup.send("Error generating image.")

# --- CHAT LISTENER ---
@bot.event
async def on_message(message):
    if message.author == bot.user: return
    if message.channel.id in bot.monitored_channels:
        async with message.channel.typing():
            try:
                headers = {"Authorization": f"Bearer {os.environ.get('GROQ_API_KEY')}", "Content-Type": "application/json"}
                payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": message.content}]}
                response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
                await message.channel.send(response.json()["choices"][0]["message"]["content"])
            except Exception as e: print(e)
    await bot.process_commands(message)

bot.run(os.environ.get("DISCORD_TOKEN"))
