import discord
from discord import app_commands
from discord.ext import commands
import os
import random
from typing import List, Dict, Any

# Требуется только TOKEN, остальное опционально
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")

if not TOKEN:
    print("❌ Ошибка: Не найден DISCORD_TOKEN в переменных окружения!")
    print("Добавьте переменную DISCORD_TOKEN на Railway")
    exit(1)

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
        intents.guilds = True
        
        super().__init__(command_prefix='!', intents=intents)
        
        # Состояние матча
        self.current_match = {
            'team1': None,
            'team2': None,
            'current_turn': None,
            'map_data_1': None,
            'map_data_2': None,
            'ban_count': 0
        }
        
        # Разрешенные роли (можно настроить через переменную окружения)
        roles_str = os.getenv("ALLOWED_ROLES", "")
        self.allowed_roles = [int(r.strip()) for r in roles_str.split(",") if r.strip()] if roles_str else []
    
    async def setup_hook(self):
        # Синхронизируем команды глобально (не нужно указывать guild_id)
        await self.tree.sync()
        print("✅ Команды синхронизированы глобально")

bot = TournamentBot()

def check_role(interaction: discord.Interaction) -> tuple:
    """Проверка наличия у пользователя разрешенной роли"""
    if not interaction.guild:
        return False, "Сервер не найден"
    
    # Если нет настроенных ролей - доступ открыт всем
    if not bot.allowed_roles:
        return True, "Доступ открыт всем"
    
    member = interaction.guild.get_member(interaction.user.id)
    if not member:
        return False, "Не удалось получить информацию о пользователе"
    
    user_role_ids = [role.id for role in member.roles]
    
    for role_id in bot.allowed_roles:
        if role_id in user_role_ids:
            return True, f"Роль найдена: {role_id}"
    
    return False, "У вас нет необходимой роли"

@bot.tree.command(name="startmatch", description="Запустить матч (выбор/бан карт)")
@app_commands.describe(team1="Выберите команду 1", team2="Выберите команду 2")
async def startmatch(interaction: discord.Interaction, team1: discord.Role, team2: discord.Role):
    """Команда для запуска матча"""
    
    # Проверяем права доступа
    has_access, message = check_role(interaction)
    
    if not has_access:
        error_embed = discord.Embed(
            color=0xFF0000,
            title="❌ Нет доступа",
            description=f"**{message}**\n\n"
                       f"Для использования этой команды нужна специальная роль.\n"
                       f"Обратитесь к администратору сервера."
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return
    
    await interaction.response.defer()
    
    # Инициализация состояния матча
    bot.current_match['team1'] = team1.id
    bot.current_match['team2'] = team2.id
    bot.current_match['map_data_1'] = [map_item.copy() for map_item in MAP1]
    bot.current_match['map_data_2'] = [map_item.copy() for map_item in MAP2]
    bot.current_match['ban_count'] = 0
    
    # Случайная команда для первого бана
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
        title="🎯 Выберите карту для бана",
        description="Нажмите на кнопку с картой, которую хотите забанить"
    )
    embed.set_author(name="SDTV.GG", url="https://sdtv.gg/")
    current_team_name = team1.name if bot.current_match['current_turn'] == team1.id else team2.name
    embed.set_footer(text=f"Сейчас выбирает: {current_team_name}")
    
    # Создаем view
    view = MapBanView(bot, team1.id, team2.id, team1.name, team2.name)
    
    await interaction.followup.send(embed=embed, view=view)

class MapBanView(discord.ui.View):
    """View для обработки бана карт"""
    
    def __init__(self, bot_instance, team1_id, team2_id, team1_name, team2_name):
        super().__init__(timeout=300)
        self.bot = bot_instance
        self.team1_id = team1_id
        self.team2_id = team2_id
        self.team1_name = team1_name
        self.team2_name = team2_name
        
        self.update_buttons()
    
    def update_buttons(self):
        """Обновление кнопок"""
        self.clear_items()
        
        style_map = {1: discord.ButtonStyle.primary, 2: discord.ButtonStyle.secondary,
                    3: discord.ButtonStyle.success, 4: discord.ButtonStyle.danger}
        
        # Добавляем кнопки из первой группы
        for map_item in self.bot.current_match['map_data_1']:
            button = discord.ui.Button(
                style=style_map.get(map_item['style'], discord.ButtonStyle.secondary),
                label=map_item['custom_id'],
                custom_id=f"map1_{map_item['custom_id']}",
                disabled=map_item['disable']
            )
            button.callback = self.create_callback(map_item, 'map1')
            self.add_item(button)
        
        # Добавляем кнопки из второй группы
        for map_item in self.bot.current_match['map_data_2']:
            button = discord.ui.Button(
                style=style_map.get(map_item['style'], discord.ButtonStyle.secondary),
                label=map_item['custom_id'],
                custom_id=f"map2_{map_item['custom_id']}",
                disabled=map_item['disable']
            )
            button.callback = self.create_callback(map_item, 'map2')
            self.add_item(button)
    
    def create_callback(self, map_item, map_type):
        async def callback(interaction: discord.Interaction):
            await self.handle_map_ban(interaction, map_item, map_type)
        return callback
    
    async def handle_map_ban(self, interaction: discord.Interaction, map_item: Dict[str, Any], map_type: str):
        """Обработка бана карты"""
        
        guild = interaction.guild
        
        # Проверяем очередь
        member = guild.get_member(interaction.user.id)
        if not member:
            await interaction.response.send_message("❌ Ошибка!", ephemeral=True)
            return
        
        user_roles = [role.id for role in member.roles]
        if self.bot.current_match['current_turn'] not in user_roles:
            await interaction.response.send_message("⏰ Сейчас не ваш ход!", ephemeral=True)
            return
        
        # Баним карту
        target_list = self.bot.current_match['map_data_1'] if map_type == 'map1' else self.bot.current_match['map_data_2']
        
        for item in target_list:
            if item['custom_id'] == map_item['custom_id']:
                item['disable'] = True
                current_role = guild.get_role(self.bot.current_match['current_turn'])
                item['user'] = current_role.name if current_role else "Unknown"
                item['number'] = self.bot.current_match['ban_count']
                break
        
        self.bot.current_match['ban_count'] += 1
        
        # Меняем очередь
        self.bot.current_match['current_turn'] = self.team2_id if self.bot.current_match['current_turn'] == self.team1_id else self.team1_id
        
        # Проверяем, закончились ли баны
        if self.bot.current_match['ban_count'] >= 6:
            await self.handle_side_selection(interaction)
        else:
            # Обновляем эмбед
            embed = discord.Embed(
                color=0xFA747D,
                title="🎯 Выберите карту для бана",
                description="Нажмите на кнопку с картой, которую хотите забанить"
            )
            embed.set_author(name="SDTV.GG", url="https://sdtv.gg/")
            current_team = guild.get_role(self.bot.current_match['current_turn'])
            embed.set_footer(text=f"Сейчас выбирает: {current_team.name if current_team else 'Неизвестно'}")
            
            self.update_buttons()
            await interaction.response.edit_message(embed=embed, view=self)
    
    async def handle_side_selection(self, interaction: discord.Interaction):
        """Обработка выбора сторон"""
        
        # Сортируем карты
        all_maps = self.bot.current_match['map_data_1'] + self.bot.current_match['map_data_2']
        all_maps.sort(key=lambda x: x['number'])
        
        pick1_map = all_maps[2]
        pick2_map = all_maps[3]
        
        view = SideSelectionView(self.bot, self.team1_id, self.team2_id, self.team1_name, self.team2_name,
                                pick1_map, pick2_map, all_maps)
        
        embed = discord.Embed(
            color=0xFA747D,
            title="⚔️ Выбор сторон",
            description=f"**Карта:** {pick1_map['custom_id']}\n**Выбирает команда:** {pick2_map['user']}"
        )
        embed.set_author(name="SDTV.GG", url="https://sdtv.gg/")
        
        await interaction.response.edit_message(embed=embed, view=view)

class SideSelectionView(discord.ui.View):
    """View для выбора стороны"""
    
    def __init__(self, bot_instance, team1_id, team2_id, team1_name, team2_name, pick1_map, pick2_map, all_maps):
        super().__init__(timeout=120)
        self.bot = bot_instance
        self.team1_id = team1_id
        self.team2_id = team2_id
        self.team1_name = team1_name
        self.team2_name = team2_name
        self.pick1_map = pick1_map
        self.pick2_map = pick2_map
        self.all_maps = all_maps
        self.selection_step = 1
    
    @discord.ui.button(label="CT", style=discord.ButtonStyle.primary)
    async def ct_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_side_choice(interaction, "CT")
    
    @discord.ui.button(label="T", style=discord.ButtonStyle.danger)
    async def t_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_side_choice(interaction, "T")
    
    async def handle_side_choice(self, interaction: discord.Interaction, side: str):
        """Обработка выбора стороны"""
        
        guild = interaction.guild
        member = guild.get_member(interaction.user.id)
        
        if not member:
            await interaction.response.send_message("❌ Ошибка!", ephemeral=True)
            return
        
        user_roles = [role.id for role in member.roles]
        
        if self.selection_step == 1:
            # Проверяем для первого выбора
            expected_team_id = self.team2_id if self.pick2_map['user'] == self.team1_name else self.team1_id
            
            if expected_team_id not in user_roles:
                await interaction.response.send_message("⏰ Сейчас не ваш ход!", ephemeral=True)
                return
            
            self.pick1_map['team'] = "T" if side == "CT" else "CT"
            self.selection_step = 2
            
            embed = discord.Embed(
                color=0xFA747D,
                title="⚔️ Выбор сторон",
                description=f"**Карта:** {self.pick2_map['custom_id']}\n**Выбирает команда:** {self.pick1_map['user']}"
            )
            embed.set_author(name="SDTV.GG", url="https://sdtv.gg/")
            
            await interaction.response.edit_message(embed=embed, view=self)
            
        else:
            # Проверяем для второго выбора
            expected_team_id = self.team1_id if self.pick1_map['user'] == self.team1_name else self.team2_id
            
            if expected_team_id not in user_roles:
                await interaction.response.send_message("⏰ Сейчас не ваш ход!", ephemeral=True)
                return
            
            self.pick2_map['team'] = "T" if side == "CT" else "CT"
            
            # Формируем результат
            result_text = ""
            for i, map_item in enumerate(self.all_maps):
                if i < 2:
                    result_text += f"🚫 Ban - {map_item['custom_id']} ({map_item['user']})\n"
                elif i < 4:
                    result_text += f"✅ Pick - {map_item['custom_id']} ({map_item['user']} - {map_item['team']})\n"
                elif i < 6:
                    result_text += f"🚫 Ban - {map_item['custom_id']} ({map_item['user']})\n"
                else:
                    result_text += f"🎲 Decider - {map_item['custom_id']}"
            
            embed = discord.Embed(
                color=0x00FF00,
                title="🎉 Результаты выбора карт",
                description=result_text
            )
            embed.set_author(name="SDTV.GG", url="https://sdtv.gg/")
            
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
    print('💡 Используйте команду /startmatch для запуска матча')

if __name__ == "__main__":
    print("🚀 Запуск бота...")
    bot.run(TOKEN)