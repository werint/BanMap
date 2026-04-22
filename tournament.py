import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random
from typing import List, Dict, Any

# Конфигурация
CONFIG = {
    "Token": os.getenv("DISCORD_TOKEN", "TOKEN"),
    "id_bot": os.getenv("BOT_ID", "1064202366947176488"),
    "guild_id": os.getenv("GUILD_ID", "1054690397366005821"),
    "roleImmunityId": os.getenv("ROLE_IMMUNITY_IDS", "1055935128863518730,1056225570674970624,1054691919592177666").split(",")
}

# Данные карт
MAP1 = [
    {"custom_id": "Anubis", "style": 3, "disable": True, "number": 4, "team": "", "user": "KazaNAVI"},
    {"custom_id": "Inferno", "style": 1, "disable": False, "number": 6, "team": "", "user": ""},
    {"custom_id": "Mirage", "style": 3, "disable": True, "number": 2, "team": "T", "user": "KazaNAVI"},
    {"custom_id": "Nuke", "style": 1, "disable": True, "number": 5, "team": "", "user": "RUstralis"}
]

MAP2 = [
    {"custom_id": "Overpass", "style": 3, "disable": True, "number": 0, "team": "", "user": "KazaNAVI"},
    {"custom_id": "Ancient", "style": 1, "disable": True, "number": 1, "team": "", "user": "RUstralis"},
    {"custom_id": "Vertigo", "style": 3, "disable": True, "number": 3, "team": "CT", "user": "RUstralis"}
]

class TournamentBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix='!', intents=intents)
        
        # Глобальные переменные для состояния матча
        self.current_match = {
            'team1': None,
            'team2': None,
            'current_turn': None,
            'map1': None,
            'map2': None,
            'map_data_1': None,
            'map_data_2': None
        }
    
    async def setup_hook(self):
        await self.tree.sync()
        print(f"Синхронизированы команды для гильдии {CONFIG['guild_id']}")

bot = TournamentBot()

def check_role(interaction: discord.Interaction) -> bool:
    """Проверка наличия у пользователя иммунной роли"""
    # Получаем участника из гильдии
    if not interaction.guild:
        return False
    
    member = interaction.guild.get_member(interaction.user.id)
    if not member:
        return False
    
    member_roles = [role.id for role in member.roles]
    for immunity_role in CONFIG['roleImmunityId']:
        if int(immunity_role) in member_roles:
            return True
    return False

def check_role_by_id(interaction: discord.Interaction, role_id: int) -> bool:
    """Проверка наличия конкретной роли у пользователя"""
    if not interaction.guild:
        return False
    
    member = interaction.guild.get_member(interaction.user.id)
    if not member:
        return False
    
    member_roles = [role.id for role in member.roles]
    return role_id in member_roles

def check_role_by_name(interaction: discord.Interaction, role_name: str) -> bool:
    """Проверка наличия роли по имени"""
    if not interaction.guild:
        return False
    
    member = interaction.guild.get_member(interaction.user.id)
    if not member:
        return False
    
    for role in member.roles:
        if role.name == role_name:
            return True
    return False

def create_button(map_item: Dict[str, Any]) -> discord.Button:
    """Создание кнопки для карты"""
    style_map = {1: discord.ButtonStyle.primary, 2: discord.ButtonStyle.secondary, 
                 3: discord.ButtonStyle.success, 4: discord.ButtonStyle.danger}
    
    return discord.Button(
        style=style_map.get(map_item['style'], discord.ButtonStyle.secondary),
        label=map_item['custom_id'],
        custom_id=f"map_{map_item['custom_id']}",
        disabled=map_item['disable']
    )

@bot.tree.command(name="startmatch", description="Запустить матч")
@app_commands.describe(team1="Выберите команду 1", team2="Выберите команду 2")
async def startmatch(interaction: discord.Interaction, team1: discord.Role, team2: discord.Role):
    """Команда для запуска матча"""
    
    if not check_role(interaction):
        await interaction.response.send_message("У вас нет доступа к этой команде!", ephemeral=True)
        return
    
    # Инициализация состояния матча
    bot.current_match['team1'] = team1.id
    bot.current_match['team2'] = team2.id
    bot.current_match['map_data_1'] = [map_item.copy() for map_item in MAP1]
    bot.current_match['map_data_2'] = [map_item.copy() for map_item in MAP2]
    
    # Определение случайной команды для первого бана
    teams_list = [team1.id, team2.id]
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
    
    # Создание эмбеда
    embed = discord.Embed(
        color=0xFA747D,
        title="Выберите карту для бана",
        description="Нажмите на кнопку с картой, которую хотите забанить"
    )
    embed.set_author(name="SDTV.GG", url="https://sdtv.gg/")
    embed.set_footer(text=f"Сейчас выбирает: {interaction.guild.get_role(bot.current_match['current_turn']).name}")
    
    # Создаем и отправляем view
    view = MapBanView(bot, interaction.guild.id, team1.id, team2.id)
    await interaction.response.send_message(embed=embed, view=view)

class MapBanView(discord.ui.View):
    """View для обработки бана карт"""
    
    def __init__(self, bot_instance, guild_id, team1_id, team2_id):
        super().__init__(timeout=300)
        self.bot = bot_instance
        self.guild_id = guild_id
        self.team1_id = team1_id
        self.team2_id = team2_id
        self.ban_count = 0
        self.current_turn = random.choice([team1_id, team2_id])
        
        # Добавляем кнопки
        self.update_buttons()
    
    def update_buttons(self):
        """Обновление кнопок на основе текущих данных"""
        self.clear_items()
        
        # Создаем кнопки для первой группы карт
        for map_item in self.bot.current_match['map_data_1']:
            style_map = {1: discord.ButtonStyle.primary, 2: discord.ButtonStyle.secondary,
                        3: discord.ButtonStyle.success, 4: discord.ButtonStyle.danger}
            
            button = discord.ui.Button(
                style=style_map.get(map_item['style'], discord.ButtonStyle.secondary),
                label=map_item['custom_id'],
                custom_id=f"map1_{map_item['custom_id']}",
                disabled=map_item['disable']
            )
            self.add_item(button)
        
        # Создаем кнопки для второй группы карт
        for map_item in self.bot.current_match['map_data_2']:
            style_map = {1: discord.ButtonStyle.primary, 2: discord.ButtonStyle.secondary,
                        3: discord.ButtonStyle.success, 4: discord.ButtonStyle.danger}
            
            button = discord.ui.Button(
                style=style_map.get(map_item['style'], discord.ButtonStyle.secondary),
                label=map_item['custom_id'],
                custom_id=f"map2_{map_item['custom_id']}",
                disabled=map_item['disable']
            )
            self.add_item(button)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Проверка перед каждым взаимодействием"""
        # Получаем участника
        member = interaction.guild.get_member(interaction.user.id)
        if not member:
            await interaction.response.send_message("Не удалось определить вашу роль!", ephemeral=True)
            return False
        
        # Проверяем, имеет ли пользователь право ходить
        member_roles = [role.id for role in member.roles]
        if self.current_turn not in member_roles:
            await interaction.response.send_message("Сейчас не ваш ход!", ephemeral=True)
            return False
        
        return True
    
    @discord.ui.button(label="Anubis", style=discord.ButtonStyle.success, custom_id="map1_Anubis", disabled=True)
    async def anubis_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_map_ban(interaction, "Anubis", "map1")
    
    async def handle_map_ban(self, interaction: discord.Interaction, map_name: str, map_type: str):
        """Обработка бана карты"""
        
        guild = interaction.guild
        
        # Баним карту
        if map_type == 'map1':
            target_list = self.bot.current_match['map_data_1']
        else:
            target_list = self.bot.current_match['map_data_2']
        
        for item in target_list:
            if item['custom_id'] == map_name:
                item['disable'] = True
                item['user'] = guild.get_role(self.current_turn).name
                item['number'] = self.ban_count
                break
        
        self.ban_count += 1
        
        # Меняем очередь
        self.current_turn = self.team2_id if self.current_turn == self.team1_id else self.team1_id
        
        # Проверяем, закончились ли баны (6 банов для 7 карт)
        if self.ban_count >= 6:
            # Переходим к выбору сторон
            await self.handle_side_selection(interaction)
        else:
            # Обновляем эмбед
            embed = discord.Embed(
                color=0xFA747D,
                title="Выберите карту для бана",
                description="Нажмите на кнопку с картой, которую хотите забанить"
            )
            embed.set_author(name="SDTV.GG", url="https://sdtv.gg/")
            embed.set_footer(text=f"Сейчас выбирает: {guild.get_role(self.current_turn).name}")
            
            self.update_buttons()
            await interaction.response.edit_message(embed=embed, view=self)
    
    async def handle_side_selection(self, interaction: discord.Interaction):
        """Обработка выбора сторон"""
        
        # Сортируем карты по номеру
        all_maps = self.bot.current_match['map_data_1'] + self.bot.current_match['map_data_2']
        all_maps.sort(key=lambda x: x['number'])
        
        # Получаем информацию о пиках
        pick1_map = all_maps[2]  # Первый пик
        pick2_map = all_maps[3]  # Второй пик
        
        # Создаем view для выбора стороны
        view = SideSelectionView(self.bot, self.guild_id, self.team1_id, self.team2_id, 
                                pick1_map, pick2_map, all_maps)
        
        embed = discord.Embed(
            color=0xFA747D,
            title="Выбор сторон",
            description=f"Выбор стороны на карте: {pick1_map['custom_id']}\nВыбирает команда: {pick2_map['user']}"
        )
        embed.set_author(name="SDTV.GG", url="https://sdtv.gg/")
        
        await interaction.response.edit_message(embed=embed, view=view)

class SideSelectionView(discord.ui.View):
    """View для выбора стороны"""
    
    def __init__(self, bot_instance, guild_id, team1_id, team2_id, pick1_map, pick2_map, all_maps):
        super().__init__(timeout=120)
        self.bot = bot_instance
        self.guild_id = guild_id
        self.team1_id = team1_id
        self.team2_id = team2_id
        self.pick1_map = pick1_map
        self.pick2_map = pick2_map
        self.all_maps = all_maps
        self.selection_step = 1  # 1 - первый выбор, 2 - второй выбор
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Проверка перед каждым взаимодействием"""
        member = interaction.guild.get_member(interaction.user.id)
        if not member:
            await interaction.response.send_message("Не удалось определить вашу роль!", ephemeral=True)
            return False
        
        member_roles = [role.id for role in member.roles]
        
        if self.selection_step == 1:
            # Проверяем для первого выбора
            expected_team_id = None
            if self.pick2_map['user'] == interaction.guild.get_role(self.team1_id).name:
                expected_team_id = self.team1_id
            else:
                expected_team_id = self.team2_id
            
            if expected_team_id not in member_roles:
                await interaction.response.send_message("Сейчас не ваш ход!", ephemeral=True)
                return False
        else:
            # Проверяем для второго выбора
            expected_team_id = None
            if self.pick1_map['user'] == interaction.guild.get_role(self.team1_id).name:
                expected_team_id = self.team1_id
            else:
                expected_team_id = self.team2_id
            
            if expected_team_id not in member_roles:
                await interaction.response.send_message("Сейчас не ваш ход!", ephemeral=True)
                return False
        
        return True
    
    @discord.ui.button(label="CT", style=discord.ButtonStyle.primary, custom_id="ct_select")
    async def ct_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_side_choice(interaction, "CT")
    
    @discord.ui.button(label="T", style=discord.ButtonStyle.danger, custom_id="t_select")
    async def t_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_side_choice(interaction, "T")
    
    async def handle_side_choice(self, interaction: discord.Interaction, side: str):
        """Обработка выбора стороны"""
        
        guild = interaction.guild
        
        if self.selection_step == 1:
            # Сохраняем выбор для первого пика
            self.pick1_map['team'] = "T" if side == "CT" else "CT"  # Инвертируем, так как выбирающая команда получает противоположную сторону
            
            # Переходим ко второму выбору
            self.selection_step = 2
            
            # Обновляем эмбед для второго выбора
            embed = discord.Embed(
                color=0xFA747D,
                title="Выбор сторон",
                description=f"Выбор стороны на карте: {self.pick2_map['custom_id']}\nВыбирает команда: {self.pick1_map['user']}"
            )
            embed.set_author(name="SDTV.GG", url="https://sdtv.gg/")
            
            await interaction.response.edit_message(embed=embed, view=self)
            
        else:  # Второй выбор
            # Сохраняем выбор для второго пика
            self.pick2_map['team'] = "T" if side == "CT" else "CT"
            
            # Формируем финальный результат
            result_text = ""
            for i, map_item in enumerate(self.all_maps):
                if i < 2:  # Баны
                    result_text += f"Ban - {map_item['custom_id']} ({map_item['user']})\n"
                elif i < 4:  # Пики
                    result_text += f"Pick - {map_item['custom_id']} ({map_item['user']} - {map_item['team']})\n"
                elif i < 6:  # Баны
                    result_text += f"Ban - {map_item['custom_id']} ({map_item['user']})\n"
                else:  # Решающая карта
                    result_text += f"Decider - {map_item['custom_id']}"
            
            embed = discord.Embed(
                color=0xFA747D,
                title="Результаты выбора",
                description=result_text
            )
            embed.set_author(name="SDTV.GG", url="https://sdtv.gg/")
            
            # Очищаем view и отправляем финальный результат
            await interaction.response.edit_message(embed=embed, view=None)

@bot.event
async def on_ready():
    print(f'Бот авторизовался как {bot.user.name}!')
    print(f'ID бота: {bot.user.id}')
    print(f'Подключен к {len(bot.guilds)} серверам')
    print('------')
    
    # Устанавливаем статус бота
    await bot.change_presence(activity=discord.Game(name="Турнирные матчи"))

@bot.event
async def on_error(event, *args, **kwargs):
    print(f'Произошла ошибка в событии {event}:')
    import traceback
    traceback.print_exc()

if __name__ == "__main__":
    # Запуск бота
    bot.run(CONFIG['Token'])