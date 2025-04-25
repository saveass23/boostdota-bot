import discord
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Бот {bot.user} запущен!")

@bot.command()
async def очистить(ctx):
    if ctx.author.guild_permissions.administrator:
        await ctx.send("Очищаю сервер...")
        for channel in ctx.guild.channels:
            try:
                await channel.delete()
            except:
                pass
        for role in ctx.guild.roles:
            if role.name != "@everyone":
                try:
                    await role.delete()
                except:
                    pass
        await ctx.send("Готово! Сервер очищен.")
    else:
        await ctx.send("У тебя нет прав администратора.")

@bot.command()
async def привет(ctx):
    await ctx.send("Привет! Я готов бустить сервер по Dota 2!")

bot.run(os.getenv("DISCORD_TOKEN"))
