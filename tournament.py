import discord
from discord import app_commands
from discord.ext import commands
import os
import random

# Токен из переменных окружения Railway
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("❌ Ошибка: DISCORD_TOKEN не найден!")
    exit(1)

# Карты
MAPS = ["Склад", "Гетто", "Парковка", "Трейлера", "Ферма"]

class TournamentBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix='!', intents=intents)
        self.match_data = {}

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Команды синхронизированы")

bot = TournamentBot()

@bot.tree.command(name="startmatch", description="Запустить матч")
@app_commands.describe(captain1="Капитан команды 1", captain2="Капитан команды 2")
async def startmatch(interaction: discord.Interaction, captain1: discord.Member, captain2: discord.Member):
    
    if captain1.id == captain2.id:
        await interaction.response.send_message("❌ Капитаны должны быть разными!", ephemeral=True)
        return
    
    # Сохраняем данные матча
    bot.match_data[interaction.channel_id] = {
        'captain1': captain1.id,
        'captain2': captain2.id,
        'turn': random.choice([captain1.id, captain2.id]),
        'banned': [],
        'maps': MAPS.copy()
    }
    
    # Создаем кнопки
    view = BanView(bot.match_data[interaction.channel_id], captain1, captain2)
    
    embed = discord.Embed(
        color=0xFA747D,
        title="🎯 Бан карт",
        description=f"**Доступные карты:**\n{', '.join(MAPS)}\n\n**Осталось банов:** 4",
        footer=f"Сейчас выбирает: {captain1.display_name if bot.match_data[interaction.channel_id]['turn'] == captain1.id else captain2.display_name}"
    )
    embed.add_field(name="👤 Капитан 1", value=captain1.mention, inline=True)
    embed.add_field(name="👤 Капитан 2", value=captain2.mention, inline=True)
    
    await interaction.response.send_message(embed=embed, view=view)

class BanView(discord.ui.View):
    def __init__(self, match_data, captain1, captain2):
        super().__init__(timeout=120)
        self.match_data = match_data
        self.captain1 = captain1
        self.captain2 = captain2
        self.add_buttons()
    
    def add_buttons(self):
        for map_name in self.match_data['maps']:
            if map_name not in self.match_data['banned']:
                button = discord.ui.Button(label=map_name, style=discord.ButtonStyle.danger, custom_id=map_name)
                button.callback = self.create_callback(map_name)
                self.add_item(button)
    
    def create_callback(self, map_name):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.match_data['turn']:
                await interaction.response.send_message("⏰ Сейчас не ваш ход!", ephemeral=True)
                return
            
            self.match_data['banned'].append(map_name)
            
            # Меняем ход
            self.match_data['turn'] = self.captain2.id if self.match_data['turn'] == self.captain1.id else self.captain1.id
            
            # Проверяем окончание
            if len(self.match_data['banned']) >= 4:
                remaining = [m for m in self.match_data['maps'] if m not in self.match_data['banned']][0]
                embed = discord.Embed(
                    color=0x00FF00,
                    title="🎉 Результат",
                    description=f"**Финальная карта:** {remaining}\n\n**История банов:**\n" + 
                                "\n".join([f"{i+1}. 🚫 {m}" for i, m in enumerate(self.match_data['banned'])])
                )
                await interaction.response.edit_message(embed=embed, view=None)
            else:
                # Обновляем кнопки
                self.clear_items()
                self.add_buttons()
                
                current = self.captain1 if self.match_data['turn'] == self.captain1.id else self.captain2
                embed = discord.Embed(
                    color=0xFA747D,
                    title="🎯 Бан карт",
                    description=f"**Осталось банов:** {4 - len(self.match_data['banned'])}\n\n**Забанено:** {', '.join(self.match_data['banned']) if self.match_data['banned'] else 'пока нет'}",
                    footer=f"Сейчас выбирает: {current.display_name}"
                )
                await interaction.response.edit_message(embed=embed, view=self)
        
        return callback

@bot.event
async def on_ready():
    print(f'✅ Бот запущен: {bot.user.name}')
    print(f'🎮 Используйте /startmatch')

if __name__ == "__main__":
    bot.run(TOKEN)