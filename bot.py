import os
import discord
from discord import app_commands
from discord.ext import commands
import requests
from dotenv import load_dotenv

# Load keys from your .env file
load_dotenv()

class GroqBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        
        # State Tracking Cache
        self.monitored_channels = {}
        self.MAX_MEMORY_LENGTH = 20  # Keep history slightly shorter for standard context windows

    async def setup_hook(self):
        print("Registering and syncing global slash commands...")
        await self.tree.sync()

bot = GroqBot()

# --- Discord Slash Command ---

@bot.tree.command(
    name="ai", 
    description="Configure the automated Groq AI chat engine."
)
@app_commands.describe(
    action="Choose whether to start or stop the AI automation engine.",
    target_channel="The text channel where the AI will chat autonomously."
)
@app_commands.choices(action=[
    app_commands.Choice(name="Start Autonomous Chat Engine", value="start"),
    app_commands.Choice(name="Stop Autonomous Chat Engine", value="stop")
])
async def ai_control(
    interaction: discord.Interaction, 
    action: str, 
    target_channel: discord.TextChannel
):
    channel_id = target_channel.id

    if action == "start":
        bot.monitored_channels[channel_id] = {
            "active": True,
            "history": [
                {"role": "system", "content": "You are a helpful, lightning-fast AI assistant chatting in a Discord server, powered by Groq."}
            ]
        }
        await interaction.response.send_message(
            f"🚀 **Groq Automation Online!** Running on Llama-3.3. It will now reply to *every* message typed in {target_channel.mention} instantly."
        )
    
    elif action == "stop":
        if channel_id in bot.monitored_channels:
            del bot.monitored_channels[channel_id]
            await interaction.response.send_message(
                f"🛑 **Automation Offline.** Groq has stopped listening to {target_channel.mention}."
            )
        else:
            await interaction.response.send_message(
                f"❌ {target_channel.mention} is not currently automated.",
                ephemeral=True
            )

# --- Real-Time Chat Engine Listener ---

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.channel.id in bot.monitored_channels:
        channel_config = bot.monitored_channels[message.channel.id]
        if channel_config.get("active"):
            
            user_prompt = message.content.strip()
            if not user_prompt:
                return

            channel_config["history"].append(
                {"role": "user", "content": f"{message.author.name}: {user_prompt}"}
            )

            if len(channel_config["history"]) > bot.MAX_MEMORY_LENGTH:
                channel_config["history"].pop(1)

            async with message.channel.typing():
                try:
                    # Pointing directly to Groq's official high-speed endpoint
                    headers = {
                        "Authorization": f"Bearer {os.environ.get('GROQ_API_KEY')}",
                        "Content-Type": "application/json"
                    }
                    
                    payload = {
                        # Using Meta's premier open-weights model hosted on Groq
                        "model": "llama-3.3-70b-versatile",
                        "messages": channel_config["history"],
                        "temperature": 0.7
                    }

                    response = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions", 
                        json=payload, 
                        headers=headers
                    )
                    response_data = response.json()

                    if response.status_code == 200:
                        ai_reply = response_data["choices"][0]["message"]["content"]
                        
                        channel_config["history"].append(
                            {"role": "assistant", "content": ai_reply}
                        )
                        
                        if len(ai_reply) > 2000:
                            for i in range(0, len(ai_reply), 2000):
                                await message.channel.send(ai_reply[i:i+2000])
                        else:
                            await message.channel.send(ai_reply)
                    else:
                        print(f"Groq API Error: {response_data}")
                        await message.channel.send(f"⚠️ Groq API Error: {response_data.get('error', {}).get('message', 'Unknown error')}")
                        
                except Exception as e:
                    print(f"Exception triggered: {e}")

    await bot.process_commands(message)

bot.run(os.environ.get("DISCORD_TOKEN"))
