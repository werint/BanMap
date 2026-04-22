import discord
from discord import app_commands
from discord.ext import commands
import os
import random
from typing import List, Dict, Any
import asyncio

# Конфигурация - используйте переменные окружения на Railway
CONFIG = {
    "Token": os.getenv("DISCORD_TOKEN", "YOUR_BOT_TOKEN_HERE"),
    "id_bot": os.getenv("BOT_ID", "YOUR_BOT_ID_HERE"),
    "guild_id": os.getenv("GUILD_ID", "YOUR_GUILD_ID_HERE"),
    "roleImmunityId": os.getenv("ROLE_IMMUNITY_IDS", "").split(",") if os.getenv("ROLE_IMMUNITY_IDS") else ["1055935128863518730", "1056225570674970624", "1054691919592177666"]
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
        # Включаем все необходимые intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True  # ВАЖНО: нужно включить в Discord Developer Portal
        intents.guilds = True
        intents.guild_messages = True
        
        super().__init__(command_prefix='!', intents=intents)
        
        # Глобальные переменные для состояния матча
        self.current_match = {
            'team1': None,
            'team2': None,
            'current_turn': None,
            'map_data_1': None,
            'map_data_2': None,
            'ban_count': 0
        }
    
    async def setup_hook(self):
        # Синхронизация команд только для конкретной гильдии
        guild = discord.Object(id=int(CONFIG['guild_id']))
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print(f"✅ Команды синхронизированы для гильдии {CONFIG['guild_id']}")

bot = TournamentBot()

def check_role(interaction: discord.Interaction) -> tuple:
    """Проверка наличия у пользователя иммунной роли"""
    if not interaction.guild:
        return False, "Сервер не найден"
    
    # Получаем участника
    member = interaction.guild.get_member(interaction.user.id)
    if not member:
        # Пытаемся получить через fetch
        try:
            member = interaction.guild.fetch_member(interaction.user.id)
        except:
            return False, "Не удалось получить информацию о пользователе"
    
    # Получаем ID ролей пользователя
    user_role_ids = [role.id for role in member.roles]
    
    # Для отладки - выводим роли пользователя в консоль
    print(f"🔍 Роли пользователя {member.name}: {user_role_ids}")
    print(f"🔍 Разрешенные роли: {CONFIG['roleImmunityId']}")
    
    # Проверяем наличие разрешенной роли
    for immunity_role in CONFIG['roleImmunityId']:
        if not immunity_role:  # Пропускаем пустые строки
            continue
        try:
            role_id = int(immunity_role)
            if role_id in user_role_ids:
                return True, f"Роль найдена: {role_id}"
        except ValueError:
            continue
    
    return False, "У вас нет необходимой роли"

@bot.tree.command(name="startmatch", description="Запустить матч")
@app_commands.describe(team1="Выберите команду 1", team2="Выберите команду 2")
async def startmatch(interaction: discord.Interaction, team1: discord.Role, team2: discord.Role):
    """Команда для запуска матча"""
    
    # Проверяем права доступа
    has_access, message = check_role(interaction)
    
    if not has_access:
        # Отправляем подробное сообщение об ошибке
        error_embed = discord.Embed(
            color=0xFF0000,
            title="❌ Нет доступа",
            description=f"**{message}**\n\n"
                       f"Для использования этой команды нужна одна из ролей:\n"
            f"{', '.join([f'<@&{role_id}>' for role_id in CONFIG['roleImmunityId'] if role_id])}\n\n"
                       f"Ваши текущие роли: {', '.join([role.mention for role in interaction.user.roles if role.name != '@everyone']) or 'нет ролей'}"
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return
    
    # Отправляем сообщение о запуске
    await interaction.response.send_message("🔄 Запускаю процесс выбора карт...", ephemeral=True)
    
    # Инициализация состояния матча
    bot.current_match['team1'] = team1.id
    bot.current_match['team2'] = team2.id
    bot.current_match['map_data_1'] = [map_item.copy() for map_item in MAP1]
    bot.current_match['map_data_2'] = [map_item.copy() for map_item in MAP2]
    bot.current_match['ban_count'] = 0
    
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
        title="🎯 Выберите карту для бана",
        description="Нажмите на кнопку с картой, которую хотите забанить"
    )
    embed.set_author(name="SDTV.GG", url="https://sdtv.gg/")
    embed.set_footer(text=f"Сейчас выбирает: {team1.name if bot.current_match['current_turn'] == team1.id else team2.name}")
    
    # Создаем и отправляем view
    view = MapBanView(bot, interaction.guild.id, team1.id, team2.id)
    
    # Удаляем временное сообщение и отправляем основное
    await interaction.delete_original_response()
    await interaction.channel.send(embed=embed, view=view)

class MapBanView(discord.ui.View):
    """View для обработки бана карт"""
    
    def __init__(self, bot_instance, guild_id, team1_id, team2_id):
        super().__init__(timeout=300)
        self.bot = bot_instance
        self.guild_id = guild_id
        self.team1_id = team1_id
        self.team2_id = team2_id
        
        # Добавляем кнопки
        self.update_buttons()
    
    def update_buttons(self):
        """Обновление кнопок на основе текущих данных"""
        self.clear_items()
        
        # Создаем кнопки для первой группы карт
        style_map = {1: discord.ButtonStyle.primary, 2: discord.ButtonStyle.secondary,
                    3: discord.ButtonStyle.success, 4: discord.ButtonStyle.danger}
        
        for map_item in self.bot.current_match['map_data_1']:
            button = discord.ui.Button(
                style=style_map.get(map_item['style'], discord.ButtonStyle.secondary),
                label=map_item['custom_id'],
                custom_id=f"map1_{map_item['custom_id']}",
                disabled=map_item['disable']
            )
            button.callback = self.create_callback(map_item, 'map1')
            self.add_item(button)
        
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
        """Создание callback для кнопки"""
        async def callback(interaction: discord.Interaction):
            await self.handle_map_ban(interaction, map_item, map_type)
        return callback
    
    async def handle_map_ban(self, interaction: discord.Interaction, map_item: Dict[str, Any], map_type: str):
        """Обработка бана карты"""
        
        guild = interaction.guild
        
        # Проверяем очередь
        member = guild.get_member(interaction.user.id)
        if not member:
            await interaction.response.send_message("❌ Не удалось определить вашу роль!", ephemeral=True)
            return
        
        user_roles = [role.id for role in member.roles]
        if self.bot.current_match['current_turn'] not in user_roles:
            await interaction.response.send_message("⏰ Сейчас не ваш ход!", ephemeral=True)
            return
        
        # Баним карту
        if map_type == 'map1':
            target_list = self.bot.current_match['map_data_1']
        else:
            target_list = self.bot.current_match['map_data_2']
        
        for item in target_list:
            if item['custom_id'] == map_item['custom_id']:
                item['disable'] = True
                item['user'] = guild.get_role(self.bot.current_match['current_turn']).name
                item['number'] = self.bot.current_match['ban_count']
                break
        
        self.bot.current_match['ban_count'] += 1
        
        # Меняем очередь
        if self.bot.current_match['current_turn'] == self.team1_id:
            self.bot.current_match['current_turn'] = self.team2_id
        else:
            self.bot.current_match['current_turn'] = self.team1_id
        
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
        
        # Сортируем карты по номеру
        all_maps = self.bot.current_match['map_data_1'] + self.bot.current_match['map_data_2']
        all_maps.sort(key=lambda x: x['number'])
        
        # Получаем информацию о пиках
        pick1_map = all_maps[2]
        pick2_map = all_maps[3]
        
        # Создаем view для выбора стороны
        view = SideSelectionView(self.bot, self.guild_id, self.team1_id, self.team2_id, 
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
    
    def __init__(self, bot_instance, guild_id, team1_id, team2_id, pick1_map, pick2_map, all_maps):
        super().__init__(timeout=120)
        self.bot = bot_instance
        self.guild_id = guild_id
        self.team1_id = team1_id
        self.team2_id = team2_id
        self.pick1_map = pick1_map
        self.pick2_map = pick2_map
        self.all_maps = all_maps
        self.selection_step = 1
    
    @discord.ui.button(label="CT", style=discord.ButtonStyle.primary, custom_id="ct_select")
    async def ct_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_side_choice(interaction, "CT")
    
    @discord.ui.button(label="T", style=discord.ButtonStyle.danger, custom_id="t_select")
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
            expected_team_id = self.team2_id if self.pick2_map['user'] == guild.get_role(self.team1_id).name else self.team1_id
            
            if expected_team_id not in user_roles:
                await interaction.response.send_message("⏰ Сейчас не ваш ход!", ephemeral=True)
                return
            
            # Сохраняем выбор
            self.pick1_map['team'] = "T" if side == "CT" else "CT"
            self.selection_step = 2
            
            # Обновляем эмбед
            embed = discord.Embed(
                color=0xFA747D,
                title="⚔️ Выбор сторон",
                description=f"**Карта:** {self.pick2_map['custom_id']}\n**Выбирает команда:** {self.pick1_map['user']}"
            )
            embed.set_author(name="SDTV.GG", url="https://sdtv.gg/")
            
            await interaction.response.edit_message(embed=embed, view=self)
            
        else:
            # Проверяем для второго выбора
            expected_team_id = self.team1_id if self.pick1_map['user'] == guild.get_role(self.team1_id).name else self.team2_id
            
            if expected_team_id not in user_roles:
                await interaction.response.send_message("⏰ Сейчас не ваш ход!", ephemeral=True)
                return
            
            # Сохраняем выбор
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
    
    # Выводим информацию о ролях из конфига
    print(f'\n📋 Настроенные роли для доступа:')
    for role_id in CONFIG['roleImmunityId']:
        if role_id:
            print(f"   - {role_id}")
    
    print('\n🎮 Бот готов к работе!')
    
    # Устанавливаем статус
    await bot.change_presence(activity=discord.Game(name="/startmatch | Турниры"))

if __name__ == "__main__":
    print("🚀 Запуск бота...")
    bot.run(CONFIG['Token'])