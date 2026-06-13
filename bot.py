import os
import discord
from discord import app_commands
from discord.ext import commands
import requests
import aiohttp
from dotenv import load_dotenv

# Load variables from environment (.env or Railway dashboard)
load_dotenv()

class UnifiedBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.monitored_channels = {}

    async def setup_hook(self):
        await self.tree.sync()
        print("Bot is online and slash commands are fully synced.")

bot = UnifiedBot()

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

# --- HIGH-QUALITY IMAGE GENERATION COMMAND ---
@bot.tree.command(name="imagine", description="Generate high-resolution images using ModelsLab.")
async def imagine(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer() # Extends the 3-second token expiration limit
    
    # Official ModelsLab V6 Stable Endpoint URL
    url = "https://modelslab.com/api/v6/images/text2img"
    payload = {
        "key": os.environ.get("IMAGE_API_KEY"),
        "model_id": "v6fp16",  # Standard high-quality production model ID
        "prompt": prompt,
        "negative_prompt": "blurry, lower quality, distorted proportions, low resolution",
        "width": 512,
        "height": 512,
        "samples": 1,
        "num_inference_steps": 25,
        "safety_checker": False
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    raw_err = await response.text()
                    print(f"ModelsLab API Response Error status {response.status}: {raw_err}")
                    await interaction.followup.send(f"⚠️ API Error ({response.status}). The server rejected the format or parameters.")
                    return

                data = await response.json()
                
                # Condition A: Image is rendered and served instantly
                if "output" in data and data["output"]:
                    embed = discord.Embed(title="AI Image Generation", description=f"**Prompt:** {prompt}", color=0x3498db)
                    embed.set_image(url=data["output"][0])
                    await interaction.followup.send(embed=embed)
                    
                # Condition B: Server is busy; item queued to generation tracking bucket
                elif data.get("status") == "processing" or "fetch_result" in data:
                    fetch_link = data.get("fetch_result", "Check your ModelsLab dashboard.")
                    await interaction.followup.send(
                        f"⏳ **Your image processing request is queued!**\n"
                        f"ModelsLab GPUs are currently busy rendering your prompt. Tracking location:\n{fetch_link}"
                    )
                else:
                    await interaction.followup.send("❌ Render completed, but the API payload did not contain any valid downlinks.")
                    
    except Exception as e:
        await interaction.followup.send(f"An unexpected internal connection failure occurred: {str(e)}")

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
