    import discord
    from discord.ext import commands, tasks
    import asyncio
    import aiohttp
    from datetime import datetime, timedelta
    import os
    from dotenv import load_dotenv
    import json
    import io
    import base64
    
    # Проверяем доступность Pillow для создания изображений
    try:
        from PIL import Image, ImageDraw, ImageFont
        PIL_AVAILABLE = True
    except ImportError:
        print("⚠️ Pillow не установлен. Функции создания изображений будут недоступны.")
        print("Установите Pillow командой: pip install Pillow")
        PIL_AVAILABLE = False

    # Load environment variables
    load_dotenv()
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    CLIENT_ID = os.getenv("CLIENT_ID")
    WEBSITE_URL = os.getenv("WEBSITE_URL", "http://localhost:5000")

    if not BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN не задан в .env файле")
    if not CLIENT_ID:
        raise ValueError("❌ CLIENT_ID не задан в .env файле")
    if not WEBSITE_URL:
        raise ValueError("❌ WEBSITE_URL не задан в .env файле")

    # Bot setup
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.members = True

    bot = commands.Bot(command_prefix=['!', '/'], intents=intents, help_command=None)

    async def fetch_json(session, url, description):
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    print(f"Ошибка {description}: HTTP {resp.status}")
                    return None
                return await resp.json()
        except asyncio.TimeoutError:
            print(f"Ошибка {description}: таймаут запроса")
        except aiohttp.ClientError as e:
            print(f"Ошибка {description}: {e}")
        return None

    async def create_ascend_image(player_data, ascend_data):
        """Generate ASCEND card image using PIL"""
        if not PIL_AVAILABLE:
            print("PIL недоступен - изображение не может быть создано")
            return None
            
        try:
            # Create image
            width, height = 800, 600
            img = Image.new('RGB', (width, height), '#1a1a2e')
            draw = ImageDraw.Draw(img)

            try:
                # Attempt to use specific fonts, fallback to default if not found
                font_large = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 36)
                font_medium = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 24)
                font_small = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 18)
            except IOError:
                print("Шрифты Liberation не найдены, используется шрифт по умолчанию.")
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()

            # Header
            draw.text((400, 30), "ASCEND Performance Card", fill='#ffd700', font=font_large, anchor='mt')
            draw.text((400, 80), f"{player_data['nickname']}", fill='white', font=font_medium, anchor='mt')

            # Skills
            skills = [
                (ascend_data.get('skill1_name', 'PVP'), ascend_data.get('skill1_score', 25)),
                (ascend_data.get('skill2_name', 'Clutching'), ascend_data.get('skill2_score', 25)),
                (ascend_data.get('skill3_name', 'Block Placement'), ascend_data.get('skill3_score', 25)),
                (ascend_data.get('skill4_name', 'Gamesense'), ascend_data.get('skill4_score', 25))
            ]

            y_start = 150
            for i, (skill_name, score) in enumerate(skills):
                y = y_start + (i * 80)

                # Skill name
                draw.text((50, y), f"{skill_name}:", fill='white', font=font_medium)

                # Score bar
                bar_width = 300
                bar_height = 20
                bar_x = 250
                bar_y = y + 5

                # Background bar
                draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], fill='#333333')

                # Score bar
                score_width = (score / 100) * bar_width
                color = '#ff4757' if score < 40 else '#ffa502' if score < 70 else '#2ed573'
                draw.rectangle([bar_x, bar_y, bar_x + score_width, bar_y + bar_height], fill=color)

                # Score text
                draw.text((bar_x + bar_width + 20, y), f"{score}/100", fill='white', font=font_small)

            # Overall tier
            overall_tier = ascend_data.get('overall_tier', 'D')
            draw.text((400, 500), f"Overall Tier: {overall_tier}", fill='#ffd700', font=font_large, anchor='mt')

            # Average score
            avg_score = sum(skill[1] for skill in skills) / 4
            draw.text((400, 550), f"Average Score: {avg_score:.1f}", fill='#48dbfb', font=font_medium, anchor='mt')

            # Convert to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            return img_bytes
        except Exception as e:
            print(f"Error creating ASCEND image: {e}")
            return None

    @bot.event
    async def on_ready():
        print(f'{bot.user} подключен к Discord!')
        print(f'Bot ID: {bot.user.id}')
        await bot.change_presence(activity=discord.Game(name="Elite Squad ASCEND | /help"))

        # Start background tasks
        leaderboard_update.start()
        karma_monitor.start()

        # Sync slash commands
        try:
            synced = await bot.tree.sync()
            print(f"Синхронизировано {len(synced)} slash-команд")
        except Exception as e:
            print(f"Ошибка синхронизации команд: {e}")

    @tasks.loop(hours=1)
    async def leaderboard_update():
        """Update bot status with current leaderboard info"""
        try:
            async with aiohttp.ClientSession() as session:
                stats = await fetch_json(session, f"{WEBSITE_URL}/api/stats", "получения статистики")
                if stats and stats.get('total_players'):
                    activity = discord.Game(name=f"Elite Squad | {stats['total_players']} игроков")
                    await bot.change_presence(activity=activity)
        except Exception as e:
            print(f"Ошибка обновления статуса: {e}")

    @tasks.loop(minutes=30)
    async def karma_monitor():
        """Monitor players with low karma and send warnings"""
        try:
            async with aiohttp.ClientSession() as session:
                # Get players with low karma (< 20)
                players = await fetch_json(session, f"{WEBSITE_URL}/api/leaderboard?sort=reputation&limit=100", "получения игроков")
                if players and players.get('players'):
                    low_karma_players = [p for p in players['players'] if p.get('reputation', 0) < 20]

                    if low_karma_players:
                        # Find main guild and general channel
                        for guild in bot.guilds:
                            # Heuristic to find the main server (e.g., most members)
                            if guild.member_count > 1000: # Assuming a large server is the main one
                                general = discord.utils.get(guild.channels, name='general') or discord.utils.get(guild.channels, name='main') or discord.utils.get(guild.channels, name='chat') or guild.text_channels[0]
                                if general:
                                    embed = discord.Embed(
                                        title="⚠️ Мониторинг кармы",
                                        description=f"Найдено {len(low_karma_players)} игроков с низкой кармой",
                                        color=0xff6b6b,
                                        timestamp=datetime.utcnow()
                                    )

                                    karma_list = []
                                    for player in low_karma_players[:5]:
                                        karma_list.append(f"**{player['nickname']}** - Карма: {player.get('reputation', 0)}")

                                    embed.add_field(name="Игроки с низкой кармой:", value="\n".join(karma_list), inline=False)
                                    embed.add_field(name="Последствия низкой кармы:",
                                                  value="• Ограничения в чате\n• Снижение дропа ресурсов\n• Ограничение участия в турнирах",
                                                  inline=False)

                                    await general.send(embed=embed)
                                break # Process only the first likely main server found
        except Exception as e:
            print(f"Ошибка мониторинга кармы: {e}")

    @leaderboard_update.before_loop
    async def before_leaderboard_update():
        await bot.wait_until_ready()

    @karma_monitor.before_loop
    async def before_karma_monitor():
        await bot.wait_until_ready()

    @bot.tree.command(name="ascend", description="Показать ASCEND карточку игрока с изображением")
    async def ascend_card(interaction: discord.Interaction, nickname: str, gamemode: str = "bedwars", visual: bool = False):
        try:
            await interaction.response.defer()

            async with aiohttp.ClientSession() as session:
                data = await fetch_json(session, f"{WEBSITE_URL}/api/search?q={nickname}", "поиска игрока")
                if not data or not data.get('players'):
                    await interaction.followup.send(f"❌ Игрок `{nickname}` не найден", ephemeral=True)
                    return

                player = data['players'][0]
                player_id = player['id']

                ascend_data = await fetch_json(session, f"{WEBSITE_URL}/api/player/{player_id}/ascend-data?gamemode={gamemode}", "получения ASCEND данных")
                if not ascend_data or not ascend_data.get('success'):
                    await interaction.followup.send("❌ ASCEND данные недоступны", ephemeral=True)
                    return

                ascend = ascend_data['ascend']

            embed = discord.Embed(
                title="🎮 ASCEND Performance Card",
                description=f"**{player['nickname']}** | Уровень {player['level']} | {gamemode.title()}",
                color=get_tier_color(ascend['overall_tier']),
                timestamp=datetime.utcnow()
            )

            # Use dynamic skill names
            skill_emojis = get_skill_emojis(gamemode)
            skills = [
                (ascend.get('skill1_name', 'PVP'), ascend.get('skill1_tier', ascend.get('pvp_tier', 'D')), ascend.get('skill1_score', ascend.get('pvp_score', 25))),
                (ascend.get('skill2_name', 'Clutching'), ascend.get('skill2_tier', ascend.get('clutching_tier', 'D')), ascend.get('skill2_score', ascend.get('clutching_score', 25))),
                (ascend.get('skill3_name', 'Block Placement'), ascend.get('skill3_tier', ascend.get('block_placement_tier', 'D')), ascend.get('skill3_score', ascend.get('block_placement_score', 25))),
                (ascend.get('skill4_name', 'Gamesense'), ascend.get('skill4_tier', ascend.get('gamesense_tier', 'D')), ascend.get('skill4_score', ascend.get('gamesense_score', 25)))
            ]

            for i, (name, tier, score) in enumerate(skills):
                emoji = skill_emojis[i] if i < len(skill_emojis) else "⭐"
                embed.add_field(name=f"{emoji} {name}", value=f"**{tier}** ({score}/100)", inline=True)

            embed.add_field(name="👑 Overall", value=f"**{ascend['overall_tier']}** TIER", inline=True)

            avg_score = sum(skill[2] for skill in skills) / 4
            embed.add_field(name="📊 Средняя оценка", value=f"**{avg_score:.1f}/100**", inline=True)

            if ascend.get('global_rank'):
                embed.add_field(name="🌍 Глобальный ранг", value=f"**#{ascend['global_rank']}**", inline=True)

            if ascend.get('comment'):
                embed.add_field(name="💬 Оценка эксперта", value=f"*{ascend['comment'][:1000]}*", inline=False)

            embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{player['nickname']}/100")
            embed.set_footer(text=f"Оценщик: {ascend.get('evaluator_name', 'Elite Squad')} | Elite Squad ASCEND")

            files = []
            if visual:
                if PIL_AVAILABLE:
                    # Generate image
                    img_bytes = await create_ascend_image(player, ascend)
                    if img_bytes:
                        files.append(discord.File(img_bytes, filename=f"ascend_{nickname}.png"))
                        embed.set_image(url=f"attachment://ascend_{nickname}.png")
                    else:
                        embed.add_field(name="⚠️ Изображение", value="Не удалось создать изображение", inline=False)
                else:
                    embed.add_field(name="⚠️ Изображение", value="Функция создания изображений недоступна (нет Pillow)", inline=False)

            view = ASCENDView(player_id, player['nickname'], gamemode)
            await interaction.followup.send(embed=embed, view=view, files=files)

        except Exception as e:
            print(f"Ошибка в команде ascend: {e}")
            await interaction.followup.send("❌ Произошла ошибка при получении данных", ephemeral=True)

    @bot.tree.command(name="karma", description="Показать информацию о карме игрока")
    async def karma_info(interaction: discord.Interaction, nickname: str = None):
        try:
            await interaction.response.defer()

            if not nickname:
                # Show general karma info
                embed = discord.Embed(
                    title="🔮 Система кармы Elite Squad",
                    description="Карма влияет на ваш игровой опыт",
                    color=0x8b4fa5,
                    timestamp=datetime.utcnow()
                )

                embed.add_field(
                    name="💜 Преимущества высокой кармы (80+)",
                    value="• Увеличенный дроп ресурсов\n• Доступ к эксклюзивным турнирам\n• Приоритет в очереди\n• Специальные роли в Discord",
                    inline=False
                )

                embed.add_field(
                    name="⚠️ Последствия низкой кармы (20-)",
                    value="• Ограничения в чате\n• Снижение дропа ресурсов\n• Ограничение участия в турнирах\n• Автоматический мониторинг",
                    inline=False
                )

                embed.add_field(
                    name="📈 Как повысить карму",
                    value="• Побеждайте в играх\n• Выполняйте квесты\n• Помогайте другим игрокам\n• Участвуйте в сообществе",
                    inline=False
                )

                await interaction.followup.send(embed=embed)
                return

            async with aiohttp.ClientSession() as session:
                data = await fetch_json(session, f"{WEBSITE_URL}/api/search?q={nickname}", "поиска игрока")
                if not data or not data.get('players'):
                    await interaction.followup.send(f"❌ Игрок `{nickname}` не найден", ephemeral=True)
                    return

                player = data['players'][0]

            karma = player.get('reputation', 0)

            # Determine karma level and color
            if karma >= 80:
                level = "Высокая"
                color = 0x00ff00
                emoji = "💚"
            elif karma >= 50:
                level = "Средняя"
                color = 0xffff00
                emoji = "💛"
            elif karma >= 20:
                level = "Низкая"
                color = 0xff8800
                emoji = "🧡"
            else:
                level = "Критическая"
                color = 0xff0000
                emoji = "💔"

            embed = discord.Embed(
                title=f"🔮 Карма игрока {player['nickname']}",
                color=color,
                timestamp=datetime.utcnow()
            )

            embed.add_field(name="💜 Текущая карма", value=f"**{karma}** {emoji}", inline=True)
            embed.add_field(name="📊 Уровень", value=f"**{level}**", inline=True)
            embed.add_field(name="⭐ Игровой уровень", value=f"**{player['level']}**", inline=True)

            if karma < 20:
                embed.add_field(
                    name="⚠️ Предупреждение",
                    value="У вас критически низкая карма! Это влияет на игровой опыт.",
                    inline=False
                )

            embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{player['nickname']}/100")
            embed.set_footer(text="Карма обновляется в реальном времени")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Ошибка в команде karma: {e}")
            await interaction.followup.send("❌ Произошла ошибка при получении данных кармы", ephemeral=True)

    @bot.tree.command(name="shop", description="Просмотреть магазин товаров")
    async def shop_command(interaction: discord.Interaction, category: str = "all"):
        try:
            await interaction.response.defer()

            async with aiohttp.ClientSession() as session:
                # Get shop items
                shop_data = await fetch_json(session, f"{WEBSITE_URL}/api/shop", "получения товаров магазина")
                if not shop_data or not shop_data.get('items'):
                    await interaction.followup.send("❌ Магазин временно недоступен", ephemeral=True)
                    return

            items = shop_data['items']
            if category != "all":
                items = [item for item in items if item.get('category') == category]

            if not items:
                await interaction.followup.send(f"❌ Товары в категории `{category}` не найдены", ephemeral=True)
                return

            embed = discord.Embed(
                title="🛒 Магазин Elite Squad",
                description=f"Доступно товаров: {len(items)}",
                color=0x00ff00,
                timestamp=datetime.utcnow()
            )

            # Show first 10 items
            for item in items[:10]:
                price_text = ""
                if item.get('price_coins', 0) > 0:
                    price_text += f"💰 {item['price_coins']:,} койнов"
                if item.get('price_reputation', 0) > 0:
                    if price_text:
                        price_text += " | "
                    price_text += f"💜 {item['price_reputation']} кармы"

                embed.add_field(
                    name=f"{item.get('emoji', '📦')} {item['display_name']}",
                    value=f"{item.get('description', 'Нет описания')}\n**Цена:** {price_text}",
                    inline=True
                )

            embed.add_field(
                name="💡 Как купить",
                value=f"Используйте `/buy <название_товара>` или зайдите на сайт: {WEBSITE_URL}/shop",
                inline=False
            )

            embed.set_footer(text="Цены указаны в койнах и карме")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Ошибка в команде shop: {e}")
            await interaction.followup.send("❌ Произошла ошибка при получении товаров", ephemeral=True)

    @bot.tree.command(name="inventory", description="Просмотреть инвентарь игрока")
    async def inventory_command(interaction: discord.Interaction, nickname: str):
        try:
            await interaction.response.defer()

            async with aiohttp.ClientSession() as session:
                data = await fetch_json(session, f"{WEBSITE_URL}/api/search?q={nickname}", "поиска игрока")
                if not data or not data.get('players'):
                    await interaction.followup.send(f"❌ Игрок `{nickname}` не найден", ephemeral=True)
                    return

                player = data['players'][0]
                player_id = player['id']

                # Get inventory data
                inventory_data = await fetch_json(session, f"{WEBSITE_URL}/api/player/{player_id}/inventory", "получения инвентаря")

            embed = discord.Embed(
                title=f"🎒 Инвентарь {player['nickname']}",
                color=0x3498db,
                timestamp=datetime.utcnow()
            )

            embed.add_field(name="💰 Койны", value=f"**{player.get('coins', 0):,}**", inline=True)
            embed.add_field(name="💜 Карма", value=f"**{player.get('reputation', 0)}**", inline=True)
            embed.add_field(name="⭐ Уровень", value=f"**{player['level']}**", inline=True)

            # Show inventory items if available
            if inventory_data and inventory_data.get('success'):
                inventory = inventory_data.get('inventory', {})

                for category, items in inventory.items():
                    if items:
                        items_text = []
                        for item_id, quantity in items.items():
                            items_text.append(f"• ID {item_id}: x{quantity}")

                        embed.add_field(
                            name=f"📦 {category.title()}",
                            value="\n".join(items_text[:5]) + ("..." if len(items_text) > 5 else ""),
                            inline=True
                        )

            embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{player['nickname']}/100")
            embed.set_footer(text="Обновлено в реальном времени")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Ошибка в команде inventory: {e}")
            await interaction.followup.send("❌ Произошла ошибка при получении инвентаря", ephemeral=True)

    @bot.tree.command(name="quests", description="Просмотреть квесты игрока")
    async def quests_command(interaction: discord.Interaction, nickname: str):
        try:
            await interaction.response.defer()

            async with aiohttp.ClientSession() as session:
                data = await fetch_json(session, f"{WEBSITE_URL}/api/search?q={nickname}", "поиска игрока")
                if not data or not data.get('players'):
                    await interaction.followup.send(f"❌ Игрок `{nickname}` не найден", ephemeral=True)
                    return

                player = data['players'][0]
                player_id = player['id']

                # Get quests data
                quests_data = await fetch_json(session, f"{WEBSITE_URL}/api/player/{player_id}/quests", "получения квестов")

            embed = discord.Embed(
                title=f"📜 Квесты игрока {player['nickname']}",
                color=0xe74c3c,
                timestamp=datetime.utcnow()
            )

            if quests_data and quests_data.get('success'):
                active_quests = quests_data.get('active_quests', [])
                completed_quests = quests_data.get('completed_quests', [])

                if active_quests:
                    quests_text = []
                    for quest in active_quests[:5]:
                        progress = quest.get('progress', 0)
                        target = quest.get('target', 100)
                        progress_percent = (progress / target) * 100 if target > 0 else 0

                        quests_text.append(f"**{quest['title']}**\nПрогресс: {progress}/{target} ({progress_percent:.1f}%)")

                    embed.add_field(name="🎯 Активные квесты", value="\n\n".join(quests_text), inline=False)

                if completed_quests:
                    embed.add_field(name="✅ Выполнено квестов", value=f"**{len(completed_quests)}**", inline=True)

            embed.add_field(
                name="💡 Как выполнить квест",
                value="Прикрепите скриншот выполнения к команде `/submit_quest`",
                inline=False
            )

            embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{player['nickname']}/100")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Ошибка в команде quests: {e}")
            await interaction.followup.send("❌ Произошла ошибка при получении квестов", ephemeral=True)

    @bot.tree.command(name="submit_quest", description="Отправить скриншот выполнения квеста на проверку")
    async def submit_quest(interaction: discord.Interaction, quest_name: str, attachment: discord.Attachment = None):
        try:
            await interaction.response.defer()

            if not attachment:
                await interaction.followup.send("❌ Необходимо приложить скриншот", ephemeral=True)
                return

            # Check if attachment is image
            if not attachment.content_type or not attachment.content_type.startswith('image/'):
                await interaction.followup.send("❌ Необходимо приложить изображение", ephemeral=True)
                return

            # Create submission embed
            embed = discord.Embed(
                title="📋 Заявка на проверку квеста",
                description=f"**Игрок:** {interaction.user.mention}\n**Квест:** {quest_name}",
                color=0xffa500,
                timestamp=datetime.utcnow()
            )

            embed.add_field(name="📎 Приложение", value=f"[{attachment.filename}]({attachment.url})", inline=False)
            embed.set_image(url=attachment.url)
            embed.set_footer(text=f"ID пользователя: {interaction.user.id}")

            # Send to admin channel
            admin_channel = None
            for guild in bot.guilds:
                admin_channel = discord.utils.get(guild.channels, name='quest-submissions') or \
                               discord.utils.get(guild.channels, name='admin') or \
                               discord.utils.get(guild.channels, name='модерация')
                if admin_channel:
                    break

            if admin_channel:
                view = QuestReviewView(interaction.user.id, quest_name)
                await admin_channel.send(embed=embed, view=view)

                await interaction.followup.send(
                    "✅ Заявка отправлена на проверку! Ожидайте решения администратора.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ Канал для заявок не найден. Обратитесь к администратору.",
                    ephemeral=True
                )

        except Exception as e:
            print(f"Ошибка в команде submit_quest: {e}")
            await interaction.followup.send("❌ Произошла ошибка при отправке заявки", ephemeral=True)

    class QuestReviewView(discord.ui.View):
        def __init__(self, user_id, quest_name):
            super().__init__(timeout=None)
            self.user_id = user_id
            self.quest_name = quest_name

        @discord.ui.button(label="✅ Принять", style=discord.ButtonStyle.success)
        async def accept_quest(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.defer()

            # Here you would call your API to complete the quest
            try:
                async with aiohttp.ClientSession() as session:
                    response = await session.post(
                        f"{WEBSITE_URL}/api/admin/complete_quest",
                        json={
                            'user_id': self.user_id,
                            'quest_name': self.quest_name,
                            'approved_by': str(interaction.user.id)
                        }
                    )
                    # Optionally check response status here
                    if response.status != 200:
                        print(f"API Error completing quest: {response.status} - {await response.text()}")
                        await interaction.followup.send("❌ Ошибка при обработке запроса на сервере.", ephemeral=True)
                        return

            except Exception as e:
                print(f"Error completing quest: {e}")
                await interaction.followup.send("❌ Произошла ошибка при связи с сервером.", ephemeral=True)
                return

            embed = discord.Embed(
                title="✅ Квест принят",
                description=f"Квест **{self.quest_name}** для пользователя <@{self.user_id}> выполнен!",
                color=0x00ff00
            )
            embed.set_footer(text=f"Принял: {interaction.user}")

            await interaction.edit_original_response(embed=embed, view=None)

            # Notify user
            try:
                user = bot.get_user(self.user_id)
                if user:
                    await user.send(f"✅ Ваш квест **{self.quest_name}** был принят и засчитан!")
            except discord.Forbidden:
                print(f"Не удалось отправить DM пользователю {self.user_id} (запрет DM).")
            except Exception as e:
                print(f"Ошибка при отправке DM пользователю {self.user_id}: {e}")

        @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger)
        async def reject_quest(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_modal(RejectQuestModal(self.user_id, self.quest_name))

    class RejectQuestModal(discord.ui.Modal, title="Отклонить квест"):
        def __init__(self, user_id, quest_name):
            super().__init__()
            self.user_id = user_id
            self.quest_name = quest_name

        reason = discord.ui.TextInput(
            label="Причина отклонения",
            placeholder="Укажите причину...",
            max_length=500,
            required=True
        )

        async def on_submit(self, interaction: discord.Interaction):
            embed = discord.Embed(
                title="❌ Квест отклонен",
                description=f"Квест **{self.quest_name}** для пользователя <@{self.user_id}> отклонен",
                color=0xff0000
            )
            embed.add_field(name="Причина", value=self.reason.value, inline=False)
            embed.set_footer(text=f"Отклонил: {interaction.user}")

            await interaction.response.edit_message(embed=embed, view=None)

            # Notify user
            try:
                user = bot.get_user(self.user_id)
                if user:
                    await user.send(f"❌ Ваш квест **{self.quest_name}** был отклонен.\nПричина: {self.reason.value}")
            except discord.Forbidden:
                print(f"Не удалось отправить DM пользователю {self.user_id} (запрет DM).")
            except Exception as e:
                print(f"Ошибка при отправке DM пользователю {self.user_id}: {e}")

    # --- Existing ASCENDView class ---
    class ASCENDView(discord.ui.View):
        def __init__(self, player_id, nickname, current_gamemode):
            super().__init__(timeout=300)
            self.player_id = player_id
            self.nickname = nickname
            self.current_gamemode = current_gamemode

        @discord.ui.select(
            placeholder="Выберите режим игры...",
            options=[
                discord.SelectOption(label="Bedwars", value="bedwars", emoji="🛏️"),
                discord.SelectOption(label="KitPVP", value="kitpvp", emoji="⚔️"),
                discord.SelectOption(label="SkyWars", value="skywars", emoji="☁️"),
                discord.SelectOption(label="BridgeFight", value="bridgefight", emoji="🌉"),
                discord.SelectOption(label="Sumo", value="sumo", emoji="👐"),
                discord.SelectOption(label="Fireball Fight", value="fireball_fight", emoji="🔥"),
                discord.SelectOption(label="Bridge", value="bridge", emoji="🌁")
            ]
        )
        async def gamemode_select(self, interaction: discord.Interaction, select: discord.ui.Select):
            await interaction.response.defer()

            try:
                async with aiohttp.ClientSession() as session:
                    ascend_data = await fetch_json(session, f"{WEBSITE_URL}/api/player/{self.player_id}/ascend-data?gamemode={select.values[0]}", "получения ASCEND данных")

                    if not ascend_data or not ascend_data.get('success'):
                        await interaction.followup.send("❌ ASCEND данные недоступны", ephemeral=True)
                        return

                    ascend = ascend_data['ascend']

                embed = discord.Embed(
                    title="🎮 ASCEND Performance Card",
                    description=f"**{self.nickname}** | {select.values[0].title()}",
                    color=get_tier_color(ascend['overall_tier']),
                    timestamp=datetime.utcnow()
                )

                skill_emojis = get_skill_emojis(select.values[0])
                skills = [
                    (ascend.get('skill1_name', 'PVP'), ascend.get('skill1_tier', 'D'), ascend.get('skill1_score', 25)),
                    (ascend.get('skill2_name', 'Clutching'), ascend.get('skill2_tier', 'D'), ascend.get('skill2_score', 25)),
                    (ascend.get('skill3_name', 'Block Placement'), ascend.get('skill3_tier', 'D'), ascend.get('skill3_score', 25)),
                    (ascend.get('skill4_name', 'Gamesense'), ascend.get('skill4_tier', 'D'), ascend.get('skill4_score', 25))
                ]

                for i, (name, tier, score) in enumerate(skills):
                    emoji = skill_emojis[i] if i < len(skill_emojis) else "⭐"
                    embed.add_field(name=f"{emoji} {name}", value=f"**{tier}** ({score}/100)", inline=True)

                embed.add_field(name="👑 Overall", value=f"**{ascend['overall_tier']}** TIER", inline=True)

                avg_score = sum(skill[2] for skill in skills) / 4
                embed.add_field(name="📊 Средняя оценка", value=f"**{avg_score:.1f}/100**", inline=True)

                embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{self.nickname}/100")
                embed.set_footer(text=f"Оценщик: {ascend.get('evaluator_name', 'Elite Squad')} | Elite Squad ASCEND")

                self.current_gamemode = select.values[0]
                await interaction.edit_original_response(embed=embed, view=self)

            except Exception as e:
                print(f"Ошибка при смене режима: {e}")
                await interaction.followup.send("❌ Ошибка при смене режима", ephemeral=True)

        @discord.ui.button(label="История оценок", style=discord.ButtonStyle.secondary, emoji="📈")
        async def history_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.defer()

            try:
                async with aiohttp.ClientSession() as session:
                    history_data = await fetch_json(session, f"{WEBSITE_URL}/api/player/{self.player_id}/ascend-history?gamemode={self.current_gamemode}&limit=10", "получения истории")

                    if not history_data or not history_data.get('success'):
                        await interaction.followup.send("❌ История недоступна", ephemeral=True)
                        return

                    history = history_data['history']

                embed = discord.Embed(
                    title=f"📈 История оценок - {self.nickname}",
                    description=f"Режим: {self.current_gamemode.title()}",
                    color=0x3498db,
                    timestamp=datetime.utcnow()
                )

                if not history:
                    embed.add_field(name="📝 История", value="Нет данных об оценках", inline=False)
                else:
                    history_text = ""
                    for entry in history[:5]:
                        date = datetime.fromisoformat(entry['created_at'].replace('Z', '+00:00')).strftime('%d.%m.%Y')
                        change_emoji = "📈" if entry['change_type'] == 'upgrade' else "📉" if entry['change_type'] == 'downgrade' else "🔄"
                        tier_change = f"{entry['old_overall_tier']} → {entry['new_overall_tier']}" if entry['old_overall_tier'] else f"New: {entry['new_overall_tier']}"
                        history_text += f"{change_emoji} {date}: {tier_change}\n"

                    embed.add_field(name="📝 Последние изменения", value=history_text or "Нет данных", inline=False)

                await interaction.followup.send(embed=embed, ephemeral=True)

            except Exception as e:
                print(f"Ошибка при получении истории: {e}")
                await interaction.followup.send("❌ Ошибка при получении истории", ephemeral=True)

    @bot.tree.command(name="leaderboard", description="Показать таблицу лидеров")
    async def leaderboard_command(interaction: discord.Interaction, sort_by: str = "experience", limit: int = 10):
        try:
            await interaction.response.defer()

            limit = min(max(limit, 5), 20)

            async with aiohttp.ClientSession() as session:
                data = await fetch_json(session, f"{WEBSITE_URL}/api/leaderboard?sort={sort_by}&limit={limit}", "получения таблицы лидеров")

                if not data or not data.get('players'):
                    await interaction.followup.send("❌ Не удалось получить таблицу лидеров", ephemeral=True)
                    return

                players = data['players']

            embed = discord.Embed(
                title="🏆 Таблица лидеров Elite Squad",
                description=f"Топ {len(players)} игроков по {sort_by}",
                color=0xffd700,
                timestamp=datetime.utcnow()
            )

            leaderboard_text = ""
            for i, player in enumerate(players):
                rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
                value = player.get(sort_by, 0)
                leaderboard_text += f"{rank_emoji} **{player['nickname']}** - {value:,}\n"

            embed.add_field(name=f"📊 Рейтинг по {sort_by}", value=leaderboard_text, inline=False)
            embed.set_footer(text="Elite Squad Bedwars")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Ошибка в команде leaderboard: {e}")
            await interaction.followup.send("❌ Произошла ошибка при получении таблицы лидеров", ephemeral=True)

    @bot.tree.command(name="player", description="Показать статистику игрока")
    async def player_command(interaction: discord.Interaction, nickname: str):
        try:
            await interaction.response.defer()

            async with aiohttp.ClientSession() as session:
                data = await fetch_json(session, f"{WEBSITE_URL}/api/search?q={nickname}", "поиска игрока")

                if not data or not data.get('players'):
                    await interaction.followup.send(f"❌ Игрок `{nickname}` не найден", ephemeral=True)
                    return

                player = data['players'][0]

            embed = discord.Embed(
                title=f"👤 Профиль игрока {player['nickname']}",
                color=0x3498db,
                timestamp=datetime.utcnow()
            )

            embed.add_field(name="📊 Уровень", value=f"**{player['level']}**", inline=True)
            embed.add_field(name="✨ Опыт", value=f"**{player['experience']:,}**", inline=True)
            embed.add_field(name="💜 Карма", value=f"**{player.get('reputation', 0)}**", inline=True)
            embed.add_field(name="⚔️ Убийства", value=f"**{player['kills']:,}**", inline=True)
            embed.add_field(name="💀 Смерти", value=f"**{player['deaths']:,}**", inline=True)
            embed.add_field(name="📈 K/D", value=f"**{player['kd_ratio']}**", inline=True)
            embed.add_field(name="🛏️ Кровати", value=f"**{player.get('beds_broken', 0):,}**", inline=True)
            embed.add_field(name="🏆 Победы", value=f"**{player['wins']:,}**", inline=True)
            embed.add_field(name="🎮 Игры", value=f"**{player['games_played']:,}**", inline=True)

            embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{player['nickname']}/100")
            embed.add_field(name="🔗 Профиль", value=f"[Открыть на сайте]({WEBSITE_URL}/player/{player['id']})", inline=False)

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Ошибка в команде player: {e}")
            await interaction.followup.send("❌ Произошла ошибка при получении данных игрока", ephemeral=True)

    @bot.tree.command(name="stats", description="Показать общую статистику сервера")
    async def stats_command(interaction: discord.Interaction):
        try:
            await interaction.response.defer()

            async with aiohttp.ClientSession() as session:
                data = await fetch_json(session, f"{WEBSITE_URL}/api/stats", "получения статистики")

                if not data:
                    await interaction.followup.send("❌ Не удалось получить статистику сервера", ephemeral=True)
                    return

            embed = discord.Embed(
                title="📊 Статистика Elite Squad",
                color=0xe74c3c,
                timestamp=datetime.utcnow()
            )

            embed.add_field(name="👥 Всего игроков", value=f"**{data.get('total_players', 0):,}**", inline=True)
            embed.add_field(name="⚔️ Всего убийств", value=f"**{data.get('total_kills', 0):,}**", inline=True)
            embed.add_field(name="🛏️ Кроватей сломано", value=f"**{data.get('total_beds_broken', 0):,}**", inline=True)
            embed.add_field(name="🏆 Всего побед", value=f"**{data.get('total_wins', 0):,}**", inline=True)
            embed.add_field(name="🎮 Всего игр", value=f"**{data.get('total_games', 0):,}**", inline=True)
            embed.add_field(name="💰 Всего койнов", value=f"**{data.get('total_coins', 0):,}**", inline=True)

            if data.get('top_player'):
                embed.add_field(name="👑 Топ игрок", value=f"**{data['top_player']['nickname']}**", inline=True)

            embed.set_footer(text="Elite Squad Bedwars")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Ошибка в команде stats: {e}")
            await interaction.followup.send("❌ Произошла ошибка при получении статистики", ephemeral=True)

    @bot.tree.command(name="help", description="Показать список команд")
    async def help_command(interaction: discord.Interaction):
        embed = discord.Embed(
            title="🤖 Команды Elite Squad Bot v2.0",
            description="Все доступные команды бота с новыми функциями",
            color=0x9b59b6,
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="🎮 Игровые команды",
            value="""
            `/ascend <nickname> [gamemode] [visual]` - ASCEND карточка
            `/player <nickname>` - Статистика игрока
            `/leaderboard [sort_by] [limit]` - Таблица лидеров
            `/stats` - Статистика сервера
            """,
            inline=False
        )

        embed.add_field(
            name="💜 Система кармы",
            value="""
            `/karma [nickname]` - Информация о карме
            """,
            inline=False
        )

        embed.add_field(
            name="🛒 Магазин и инвентарь",
            value="""
            `/shop [category]` - Просмотр магазина
            `/inventory <nickname>` - Инвентарь игрока
            """,
            inline=False
        )

        embed.add_field(
            name="📜 Квесты",
            value="""
            `/quests <nickname>` - Квесты игрока
            `/submit_quest <name> [screenshot]` - Отправить на проверку
            """,
            inline=False
        )

        embed.add_field(name="🎮 Режимы игры для ASCEND",
                       value="bedwars, kitpvp, skywars, bridgefight, sumo, fireball_fight, bridge", inline=False)
        embed.add_field(name="🔗 Сайт", value=f"[Открыть Elite Squad]({WEBSITE_URL})", inline=False)

        embed.set_footer(text="Elite Squad ASCEND Bot v2.0 | Новые функции!")

        await interaction.response.send_message(embed=embed)

    def get_tier_color(tier):
        colors = {
            'S+': 0xff1744, 'S': 0xff5722,
            'A+': 0xff9800, 'A': 0xffc107,
            'B+': 0x4caf50, 'B': 0x2196f3,
            'C+': 0x9c27b0, 'C': 0x607d8b,
            'D': 0x795548
        }
        return colors.get(tier, 0x607d8b)

    def get_skill_emojis(gamemode):
        emoji_maps = {
            'bedwars': ['⚔️', '🔥', '🧱', '🧠'],
            'kitpvp': ['🎯', '❤️', '🏃', '📏'],
            'skywars': ['🔍', '🧪', '⚫', '👊'],
            'bridgefight': ['✏️', '🌉', '🧠', '⚔️'],
            'sumo': ['🧠', '✋', '⚙️', '🏃'],
            'fireball_fight': ['🛡️', '🔥', '🧠', '⚔️'],
            'bridge': ['⏩', '🛡️', '🧠', '⚔️']
        }
        return emoji_maps.get(gamemode, ['⭐', '⭐', '⭐', '⭐'])

    def run_bot():
        try:
            bot.run(BOT_TOKEN)
        except discord.errors.LoginFailure:
            print("❌ Ошибка: Неверный токен бота. Пожалуйста, проверьте ваш BOT_TOKEN в .env файле.")
        except Exception as e:
            print(f"❌ Произошла непредвиденная ошибка при запуске бота: {e}")

    if __name__ == "__main__":
        run_bot()