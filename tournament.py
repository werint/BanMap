import discord
from discord import app_commands
from discord.ext import commands
import os
import random

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("Ошибка: DISCORD_TOKEN не найден")
    exit(1)

MAPS = ["Склад", "Гетто", "Парковка", "Трейлера", "Ферма"]
match_data = {}

class BanView(discord.ui.View):
    def __init__(self, data, cap1, cap2):
        super().__init__(timeout=120)
        self.data = data
        self.cap1 = cap1
        self.cap2 = cap2
        self.add_buttons()
    
    def add_buttons(self):
        for map_name in self.data['maps']:
            if map_name not in self.data['banned']:
                btn = discord.ui.Button(label=map_name, style=discord.ButtonStyle.danger)
                btn.callback = self.create_callback(map_name)
                self.add_item(btn)
    
    def create_callback(self, map_name):
        async def callback(interaction):
            if interaction.user.id != self.data['turn']:
                await interaction.response.send_message("Не ваш ход!", ephemeral=True)
                return
            
            self.data['banned'].append(map_name)
            self.data['turn'] = self.cap2.id if self.data['turn'] == self.cap1.id else self.cap1.id
            
            if len(self.data['banned']) >= 4:
                remaining = [m for m in self.data['maps'] if m not in self.data['banned']][0]
                ban_list = "\n".join([f"{i+1}. {m}" for i, m in enumerate(self.data['banned'])])
                embed = discord.Embed(
                    color=0x00FF00,
                    title="🎉 Результат",
                    description=f"**Финальная карта:** {remaining}\n\n**Баны:**\n{ban_list}"
                )
                await interaction.response.edit_message(embed=embed, view=None)
            else:
                self.clear_items()
                self.add_buttons()
                current = self.cap1 if self.data['turn'] == self.cap1.id else self.cap2
                banned_text = ', '.join(self.data['banned']) if self.data['banned'] else 'нет'
                embed = discord.Embed(
                    color=0xFA747D,
                    title="🎯 Бан карт",
                    description=f"**Осталось банов:** {4 - len(self.data['banned'])}\n**Забанено:** {banned_text}"
                )
                embed.set_footer(text=f"Ход: {current.display_name}")
                await interaction.response.edit_message(embed=embed, view=self)
        return callback

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix='!', intents=intents)
    
    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

@bot.tree.command(name="startmatch", description="Запустить матч")
@app_commands.describe(captain1="Капитан 1", captain2="Капитан 2")
async def startmatch(interaction: discord.Interaction, captain1: discord.Member, captain2: discord.Member):
    if captain1.id == captain2.id:
        await interaction.response.send_message("❌ Капитаны должны быть разными", ephemeral=True)
        return
    
    data = {
        'captain1': captain1.id,
        'captain2': captain2.id,
        'turn': random.choice([captain1.id, captain2.id]),
        'banned': [],
        'maps': MAPS.copy()
    }
    
    match_data[interaction.channel_id] = data
    
    current = captain1 if data['turn'] == captain1.id else captain2
    embed = discord.Embed(
        color=0xFA747D,
        title="🎯 Бан карт",
        description="**Доступные карты:**\n" + ", ".join(MAPS) + "\n\n**Осталось банов:** 4"
    )
    embed.add_field(name="👤 Капитан 1", value=captain1.mention, inline=True)
    embed.add_field(name="👤 Капитан 2", value=captain2.mention, inline=True)
    embed.set_footer(text=f"Сейчас выбирает: {current.display_name}")
    
    await interaction.response.send_message(embed=embed, view=BanView(data, captain1, captain2))

@bot.event
async def on_ready():
    print(f'✅ Бот запущен: {bot.user.name}')
    print(f'🎮 Команда: /startmatch')

if __name__ == "__main__":
    print("🚀 Запуск...")
    bot.run(TOKEN)