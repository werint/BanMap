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
    
    current_captain = captain1 if bot.match_data[interaction.channel_id]['turn'] == captain1.id else captain2
    
    embed = discord.Embed(
        color=0xFA747D,
        title="🎯 Бан карт",
        description=f"**Доступные карты:**\n{', '.join(MAPS)}\n\n**Осталось банов:** 4"
    )
    embed.set_author(name="SDTV.GG", url="https://sdtv.gg/")
    embed.add_field(name="👤 Капитан 1", value=captain1.mention, inline=True)
    embed.add_field(name="👤 Капитан 2", value=captain2.mention, inline=True)
    embed.set_footer(text=f"Сейчас выбирает: {current_captain.display_name}")
    
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
            if self.match_data['turn'] == self.captain1.id:
                self.match_data['turn'] = self.captain2.id
            else:
                self.match_data['turn'] = self.captain1.id
            
            # Проверяем окончание (4 бана из 5 карт)
            if len(self.match_data['banned']) >= 4:
                remaining = [m for m in self.match_data['maps'] if m not in self.match_data['banned']][0]
                
                # История банов
                ban_history = ""
                for i, m in enumerate(self.match_data['banned']):
                    ban_history += f"{i+1}. 🚫 {m}\n"
                
                embed = discord.Embed(
                    color=0x00FF00,
                    title="🎉 Результаты выбора карт",
                    description=f"**Финальная карта:** {remaining}\n\n**История банов:**\n{ban_history}"
                )
                embed.set_author(name="SDTV.GG", url="https://sdtv.gg/")
                embed.add_field(name="👤 Капитан 1", value=self.captain1.mention, inline=True)
                embed.add_field(name="👤 Капитан 2", value=self.captain2.mention, inline=True)
                
                await interaction.response.edit_message(embed=embed, view=None)
            else:
                # Обновляем кнопки
                self.clear_items()
                self.add_buttons()
                
                current_captain = self.captain1 if self.match_data['turn'] == self.captain1.id else self.captain2
                
                banned_list = ', '.join(self.match_data['banned']) if self.match_data['banned'] else 'пока нет'
                
                embed = discord.Embed(
                    color=0xFA747D,
                    title="🎯 Бан карт",
                    description=f"**Осталось банов:** {4 - len(self.match_data['banned'])}\n\n**Забанено:** {banned_list}"
                )
                embed.set_author(name="SDTV.GG", url="https://sdtv.gg/")
                embed.add_field(name="👤 Капитан 1", value=self.captain1.mention, inline=True)
                embed.add_field(name="👤 Капитан 2", value=self.captain2.mention, inline=True)
                embed.set_footer(text=f"Сейчас выбирает: {current_captain.display_name}")
                
                await interaction.response.edit_message(embed=embed, view=self)
        
        return callback

@bot.event
async def on_ready():
    print(f'✅ Бот запущен: {bot.user.name}')
    print(f'🎮 Используйте команду /startmatch')
    print(f'📝 Формат: /startmatch captain1:@Капитан1 captain2:@Капитан2')

if __name__ == "__main__":
    print("🚀 Запуск бота...")
    bot.run(TOKEN)