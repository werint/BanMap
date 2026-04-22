import discord
from discord import app_commands
from discord.ext import commands
import os
import random
from typing import List, Dict, Any

# Требуется только TOKEN
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")

if not TOKEN:
    print("❌ Ошибка: Не найден DISCORD_TOKEN в переменных окружения!")
    print("Добавьте переменную DISCORD_TOKEN на Railway")
    exit(1)

# Данные карт (новые названия)
MAP1 = [
    {"custom_id": "Склад", "style": 3, "disable": True, "number": 4, "team": "", "user": "KazaNAVI"},
    {"custom_id": "Гетто", "style": 1, "disable": False, "number": 6, "team": "", "user": ""},
    {"custom_id": "Парковка", "style": 3, "disable": True, "number": 2, "team": "T", "user": "KazaNAVI"},
    {"custom_id": "Трейлера", "style": 1, "disable": True, "number": 5, "team": "", "user": "RUstralis"}
]

MAP2 = [
    {"custom_id": "Ферма", "style": 3, "disable": True, "number": 0, "team": "", "user": "KazaNAVI"},
    {"custom_id": "Склад", "style": 1, "disable": True, "number": 1, "team": "", "user": "RUstralis"},
    {"custom_id": "Гетто", "style": 3, "disable": True, "number": 3, "team": "CT", "user": "RUstralis"}
]

class TournamentBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        
        super().__init__(command_prefix='!', intents=intents)
        
        # Состояние матча
        self.current_match = {
            'team1_captain': None,
            'team2_captain': None,
            'team1_name': None,
            'team2_name': None,
            'current_turn': None,
            'map_data_1': None,
            'map_data_2': None,
            'ban_count': 0
        }
        
        # Разрешенные роли (опционально)
        roles_str = os.getenv("ALLOWED_ROLES", "")
        self.allowed_roles = [int(r.strip()) for r in roles_str.split(",") if r.strip()] if roles_str else []
    
    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Команды синхронизированы глобально")

bot = TournamentBot()

def check_role(interaction: discord.Interaction) -> tuple:
    """Проверка наличия у пользователя разрешенной роли"""
    if not bot.allowed_roles:
        return True, "Доступ открыт всем"
    
    if not interaction.guild:
        return False, "Сервер не найден"
    
    member = interaction.guild.get_member(interaction.user.id)
    if not member:
        return False, "Не удалось получить информацию о пользователе"
    
    user_role_ids = [role.id for role in member.roles]
    
    for role_id in bot.allowed_roles:
        if role_id in user_role_ids:
            return True, f"Роль найдена: {role_id}"
    
    return False, "У вас нет необходимой роли"

@bot.tree.command(name="startmatch", description="Запустить матч (выбор/бан карт)")
@app_commands.describe(
    captain1="Выберите капитана команды 1",
    captain2="Выберите капитана команды 2",
    team1_name="Название команды 1",
    team2_name="Название команды 2"
)
async def startmatch(
    interaction: discord.Interaction, 
    captain1: discord.Member,
    captain2: discord.Member,
    team1_name: str,
    team2_name: str
):
    """Команда для запуска матча"""
    
    # Проверяем права доступа
    has_access, message = check_role(interaction)
    
    if not has_access:
        error_embed = discord.Embed(
            color=0xFF0000,
            title="❌ Нет доступа",
            description=f"**{message}**\n\nДля использования этой команды нужна специальная роль."
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return
    
    # Проверяем, что капитаны разные
    if captain1.id == captain2.id:
        await interaction.response.send_message("❌ Капитаны команд должны быть разными пользователями!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    # Инициализация состояния матча
    bot.current_match['team1_captain'] = captain1.id
    bot.current_match['team2_captain'] = captain2.id
    bot.current_match['team1_name'] = team1_name
    bot.current_match['team2_name'] = team2_name
    bot.current_match['map_data_1'] = [map_item.copy() for map_item in MAP1]
    bot.current_match['map_data_2'] = [map_item.copy() for map_item in MAP2]
    bot.current_match['ban_count'] = 0
    
    # Случайный выбор кто начинает
    teams_list = [captain1.id, captain2.id]
    bot.current_match['current_turn'] = random.choice(teams_list)
    
    # Сброс состояния карт
    for map_item in bot.current_match['map_data_1']:
        map_item['disable'] = False
        map_item['user'] = ''
        map_item['number'] = 6
        map_item['team'] = ''
    
    for map_item in bot.current_match['map_data_2']:
        map_item['disable'] = False
        map_item['user'] = ''
        map_item['number'] = 6
        map_item['team'] = ''
    
    # Определяем кто сейчас ходит
    current_captain_name = captain1.display_name if bot.current_match['current_turn'] == captain1.id else captain2.display_name
    current_team_name = team1_name if bot.current_match['current_turn'] == captain1.id else team2_name
    
    # Создание эмбеда
    embed = discord.Embed(
        color=0xFA747D,
        title="🎯 Выберите карту для бана",
        description="Нажмите на кнопку с картой, которую хотите забанить\n\n**Доступные карты:**\nСклад, Гетто, Парковка, Трейлера, Ферма"
    )
    embed.set_author(name="SDTV.GG", url="https://sdtv.gg/")
    embed.add_field(name="Команда 1", value=f"{team1_name}\nКапитан: {captain1.mention}", inline=True)
    embed.add_field(name="Команда 2", value=f"{team2_name}\nКапитан: {captain2.mention}", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.set_footer(text=f"Сейчас выбирает: {current_team_name} ({current_captain_name})")
    
    # Создаем view
    view = MapBanView(bot, captain1.id, captain2.id, team1_name, team2_name, captain1.display_name, captain2.display_name)
    
    await interaction.followup.send(embed=embed, view=view)

class MapBanView(discord.ui.View):
    """View для обработки бана карт"""
    
    def __init__(self, bot_instance, captain1_id, captain2_id, team1_name, team2_name, captain1_name, captain2_name):
        super().__init__(timeout=300)
        self.bot = bot_instance
        self.captain1_id = captain1_id
        self.captain2_id = captain2_id
        self.team1_name = team1_name
        self.team2_name = team2_name
        self.captain1_name = captain1_name
        self.captain2_name = captain2_name
        
        self.update_buttons()
    
    def update_buttons(self):
        """Обновление кнопок"""
        self.clear_items()
        
        style_map = {1: discord.ButtonStyle.primary, 2: discord.ButtonStyle.secondary,
                    3: discord.ButtonStyle.success, 4: discord.ButtonStyle.danger}
        
        # Получаем все уникальные карты
        all_maps = {}
        for map_item in self.bot.current_match['map_data_1']:
            all_maps[map_item['custom_id']] = map_item
        for map_item in self.bot.current_match['map_data_2']:
            if map_item['custom_id'] not in all_maps:
                all_maps[map_item['custom_id']] = map_item
        
        # Создаем кнопки для каждой карты
        for map_name, map_item in all_maps.items():
            button = discord.ui.Button(
                style=style_map.get(map_item['style'], discord.ButtonStyle.secondary),
                label=map_name,
                custom_id=f"map_{map_name}",
                disabled=map_item['disable']
            )
            button.callback = self.create_callback(map_item)
            self.add_item(button)
    
    def create_callback(self, map_item):
        async def callback(interaction: discord.Interaction):
            await self.handle_map_ban(interaction, map_item)
        return callback
    
    async def handle_map_ban(self, interaction: discord.Interaction, map_item: Dict[str, Any]):
        """Обработка бана карты"""
        
        guild = interaction.guild
        
        # Проверяем, что нажал текущий капитан
        if interaction.user.id != self.bot.current_match['current_turn']:
            current_captain_name = self.captain1_name if self.bot.current_match['current_turn'] == self.captain1_id else self.captain2_name
            await interaction.response.send_message(f"⏰ Сейчас не ваш ход! Сейчас выбирает: {current_captain_name}", ephemeral=True)
            return
        
        # Находим карту в обоих списках и баним
        found = False
        for target_list in [self.bot.current_match['map_data_1'], self.bot.current_match['map_data_2']]:
            for item in target_list:
                if item['custom_id'] == map_item['custom_id']:
                    item['disable'] = True
                    current_captain = guild.get_member(self.bot.current_match['current_turn'])
                    item['user'] = current_captain.display_name if current_captain else "Unknown"
                    item['number'] = self.bot.current_match['ban_count']
                    found = True
                    break
            if found:
                break
        
        self.bot.current_match['ban_count'] += 1
        
        # Меняем очередь
        if self.bot.current_match['current_turn'] == self.captain1_id:
            self.bot.current_match['current_turn'] = self.captain2_id
        else:
            self.bot.current_match['current_turn'] = self.captain1_id
        
        # Проверяем, закончились ли баны (5 карт - 4 бана, 1 остается)
        if self.bot.current_match['ban_count'] >= 4:
            await self.handle_final_map(interaction)
        else:
            # Обновляем эмбед
            current_captain = guild.get_member(self.bot.current_match['current_turn'])
            current_team = self.team1_name if self.bot.current_match['current_turn'] == self.captain1_id else self.team2_name
            current_captain_name = current_captain.display_name if current_captain else "Unknown"
            
            embed = discord.Embed(
                color=0xFA747D,
                title="🎯 Выберите карту для бана",
                description=f"Нажмите на кнопку с картой, которую хотите забанить\n\n**Осталось банов:** {4 - self.bot.current_match['ban_count']}"
            )
            embed.set_author(name="SDTV.GG", url="https://sdtv.gg/")
            embed.add_field(name="Команда 1", value=f"{self.team1_name}\nКапитан: <@{self.captain1_id}>", inline=True)
            embed.add_field(name="Команда 2", value=f"{self.team2_name}\nКапитан: <@{self.captain2_id}>", inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=True)
            embed.set_footer(text=f"Сейчас выбирает: {current_team} ({current_captain_name})")
            
            self.update_buttons()
            await interaction.response.edit_message(embed=embed, view=self)
    
    async def handle_final_map(self, interaction: discord.Interaction):
        """Обработка финальной карты (которая осталась после банов)"""
        
        # Находим оставшуюся карту
        remaining_map = None
        for map_item in self.bot.current_match['map_data_1']:
            if not map_item['disable']:
                remaining_map = map_item
                break
        if not remaining_map:
            for map_item in self.bot.current_match['map_data_2']:
                if not map_item['disable']:
                    remaining_map = map_item
                    break
        
        if remaining_map:
            # Создаем эмбед с результатом
            result_text = f"**Оставшаяся карта:** {remaining_map['custom_id']}\n\n"
            result_text += "**История банов:**\n"
            
            # Собираем все баны
            all_bans = []
            for map_item in self.bot.current_match['map_data_1']:
                if map_item['disable']:
                    all_bans.append((map_item['number'], map_item['custom_id'], map_item['user']))
            for map_item in self.bot.current_match['map_data_2']:
                if map_item['disable']:
                    all_bans.append((map_item['number'], map_item['custom_id'], map_item['user']))
            
            all_bans.sort(key=lambda x: x[0])
            for ban_num, map_name, user in all_bans:
                result_text += f"{ban_num + 1}. 🚫 {map_name} (забанил: {user})\n"
            
            embed = discord.Embed(
                color=0x00FF00,
                title="🎉 Результаты выбора карт",
                description=result_text
            )
            embed.set_author(name="SDTV.GG", url="https://sdtv.gg/")
            embed.add_field(name="Команда 1", value=f"{self.team1_name}\nКапитан: <@{self.captain1_id}>", inline=True)
            embed.add_field(name="Команда 2", value=f"{self.team2_name}\nКапитан: <@{self.captain2_id}>", inline=True)
            
            await interaction.response.edit_message(embed=embed, view=None)

@bot.event
async def on_ready():
    print(f'✅ Бот авторизовался как {bot.user.name}')
    print(f'📡 ID бота: {bot.user.id}')
    print(f'🔗 Подключен к {len(bot.guilds)} серверам')
    
    if bot.allowed_roles:
        print(f'📋 Разрешенные роли: {", ".join([f"<@&{r}>" for r in bot.allowed_roles])}')
    else:
        print('📋 Доступ к командам открыт для всех пользователей')
    
    print('\n🎮 Бот готов к работе!')
    print('🎯 Доступные карты: Склад, Гетто, Парковка, Трейлера, Ферма')
    print('💡 Используйте команду /startmatch для запуска матча')
    print('📝 Формат: /startmatch captain1:@Пользователь captain2:@Пользователь team1_name:"Название" team2_name:"Название"')

if __name__ == "__main__":
    print("🚀 Запуск бота...")
    bot.run(TOKEN)