import os
import discord
from discord import app_commands
from discord.ext import commands
import requests
import aiohttp
from dotenv import load_dotenv

# Load variables from environment
load_dotenv()

class UnifiedBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.monitored_channels = {}

    async def setup_hook(self):
        await self.tree.sync()
        print("Bot is online and slash commands are synced.")

bot = UnifiedBot()

# --- CHAT COMMANDS ---
@bot.tree.command(name="ai", description="Toggle auto-chat for a channel.")
@app_commands.choices(action=[app_commands.Choice(name="Start", value="start"), app_commands.Choice(name="Stop", value="stop")])
async def ai_control(interaction: discord.Interaction, action: str, target_channel: discord.TextChannel):
    if action == "start":
        bot.monitored_channels[target_channel.id] = True
        await interaction.response.send_message(f"AI chat enabled in {target_channel.mention}")
    else:
        bot.monitored_channels.pop(target_channel.id, None)
        await interaction.response.send_message(f"AI chat disabled in {target_channel.mention}")

# --- IMAGE COMMAND ---
@bot.tree.command(name="imagine", description="Generate a high-quality image.")
async def imagine(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    
    # Using the standard v3 text2img endpoint
    url = "https://stablediffusionapi.com/api/v3/text2img"
    payload = {
        "key": os.environ.get("IMAGE_API_KEY"),
        "prompt": prompt,
        "width": "512",
        "height": "512",
        "samples": "1",
        "num_inference_steps": "30"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    text = await response.text()
                    await interaction.followup.send(f"API Error ({response.status}): The server rejected the request. Check your API Key.")
                    return

                data = await response.json()
                if "output" in data and data["output"]:
                    await interaction.followup.send(f"**Prompt:** {prompt}\n{data['output'][0]}")
                else:
                    await interaction.followup.send("Generated, but no image URL was returned.")
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")

# --- CHAT LISTENER ---
@bot.event
async def on_message(message):
    if message.author == bot.user: return
    if message.channel.id in bot.monitored_channels:
        async with message.channel.typing():
            try:
                headers = {"Content-Type": "application/json"}
                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": message.content}]
                }
                
                # Corrected: single 'json' argument and 'headers' argument
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {os.environ.get('GROQ_API_KEY')}"}
                )
                
                reply = response.json()["choices"][0]["message"]["content"]
                await message.channel.send(reply)
            except Exception as e:
                print(f"Chat Error: {e}")
    await bot.process_commands(message)

bot.run(os.environ.get("DISCORD_TOKEN"))
