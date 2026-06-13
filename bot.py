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
    
    # ModelsLab updated v6 realtime endpoint URL
    url = "https://modelslab.com/api/v6/realtime/text2img"
    payload = {
        "key": os.environ.get("IMAGE_API_KEY"),
        "model_id": "realtime-text-to-image",
        "prompt": prompt,
        "width": "512",
        "height": "512",
        "samples": "1",
        "safety_checker": "no"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    text = await response.text()
                    print(f"ModelsLab API Error Response: {text}")
                    await interaction.followup.send(f"API Error ({response.status}): Endpoint rejected payload. Check server logs.")
                    return

                data = await response.json()
                
                # ModelsLab typically puts result strings inside the "output" array
                if "output" in data and data["output"]:
                    embed = discord.Embed(title=f"Generated Image", description=f"**Prompt:** {prompt}")
                    embed.set_image(url=data["output"][0])
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("Image processed, but no valid download URL was returned by the provider.")
    except Exception as e:
        await interaction.followup.send(f"An unexpected internal connection error occurred: {str(e)}")

# --- CHAT LISTENER ---
@bot.event
async def on_message(message):
    if message.author == bot.user: return
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
                print(f"Groq Chat Error: {e}")
    await bot.process_commands(message)

bot.run(os.environ.get("DISCORD_TOKEN"))
