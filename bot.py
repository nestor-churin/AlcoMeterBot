import os
import yaml
import sqlite3
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Завантаження конфігурації
with open('config.yml', 'r', encoding='utf-8') as file:
    config = yaml.safe_load(file)

# Ініціалізація бота
app = Client(
    "AlcoMeterBot",
    api_id=config['bot']['api_id'],
    api_hash=config['bot']['api_hash'],
    bot_token=config['bot']['bot_token']
)

# Створення папки для бази даних
os.makedirs(os.path.dirname(config['database']['path']), exist_ok=True)

# Ініціалізація бази даних
def init_db():
    conn = sqlite3.connect(config['database']['path'])
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS drinks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            alcohol_type TEXT,
            subtype TEXT,
            volume INTEGER,
            proof REAL,
            video_file_id TEXT,
            status TEXT DEFAULT 'pending',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Додаємо таблицю для порушень
    c.execute('''
        CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            violation_type TEXT,
            ban_duration INTEGER,  -- тривалість бану в годинах
            ban_until DATETIME,    -- час до якого діє бан
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Функція для отримання загального об'єму випитого
def get_total_volume(user_id):
    conn = sqlite3.connect(config['database']['path'])
    c = conn.cursor()
    c.execute('''
        SELECT 
            SUM(volume) as total_volume,
            SUM(volume * proof / 100) as total_pure_alcohol
        FROM drinks 
        WHERE user_id = ? AND status = 'approved'
    ''', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] or 0, result[1] or 0

# Функція для збереження запису про випите
def save_drink(user_id, username, alcohol_type, subtype, volume, proof, video_file_id):
    conn = sqlite3.connect(config['database']['path'])
    c = conn.cursor()
    c.execute('''
        INSERT INTO drinks (user_id, username, alcohol_type, subtype, volume, proof, video_file_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, alcohol_type, subtype, volume, proof, video_file_id))
    conn.commit()
    conn.close()

# Перевірка на адміністратора
def is_admin(user_id):
    return user_id in config['bot']['admin_ids']

# Оновлюємо текст команди /help
HELP_TEXT = """
📖 Довідка по використанню AlcoMeterBot:

🎯 Основні команди:
/start - Почати роботу з ботом
/help - Показати цю довідку
/types - Показати доступні типи алкоголю
/top - Показати топ користувачів
/add - Додати новий запис 👈 
/stats - Показати вашу статистику 📊
/history - Показати історію ваших записів 📜
/tos - Показати умови використання

📝 Як додати запис:
1. Використайте команду /add
2. Надішліть відео-кружечок з доказом випитого алкоголю
3. Виберіть тип алкоголю зі списку
4. Виберіть підтип алкоголю
5. Вкажіть об'єм (можна вибрати зі стандартних або ввести свій)
6. Чекайте підтвердження від адміністратора

⚠️ Важливо:
- Приймаються тільки відео-кружечки
- Відео має чітко показувати процес вживання
- Об'єм вказується в мілілітрах
- Неправдиві дані будуть відхилені
"""

# Текст для команди /tos
TOS_TEXT = """
📜 Умови використання AlcoMeterBot:

1️⃣ Загальні положення:
- Бот призначений для розважальних цілей
- Користувач повинен бути повнолітнім (18+)
- Бот не пропагує надмірне вживання алкоголю

2️⃣ Конфіденційність:
- Ми зберігаємо тільки надані вами дані (нік, відео, об'єми)
- Відео доступні тільки адміністраторам для верифікації
- Публічно показуються лише загальні об'єми в рейтингу

3️⃣ Правила використання:
- Заборонено надсилати неправдиві дані
- Заборонено надсилати невідповідний контент
- Заборонено спамити та зловживати функціоналом

4️⃣ Відповідальність:
- Користувач несе повну відповідальність за свої дії
- Адміністрація може відхилити будь-який запис
- За порушення правил можливе блокування

5️⃣ Обмеження відповідальності:
- Бот не несе відповідальності за дії користувачів
- Ми не рекомендуємо надмірне вживання алкоголю
- Використовуйте бота відповідально

❗️ Використовуючи бота, ви погоджуєтеся з цими умовами
"""

# Команда /help
@app.on_message(filters.command("help"))
async def help_command(client, message: Message):
    await message.reply_text(HELP_TEXT)

# Команда /tos
@app.on_message(filters.command("tos"))
async def tos_command(client, message: Message):
    await message.reply_text(TOS_TEXT)

# Оновлюємо текст команди /start
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    await message.reply_text(
        "🍺 AlcoMeterBot - ваш персональний трекер випитого алкоголю!\n\n"
        "📱 Записуйте кожен випитий напій через відео-кружечок, "
        "відстежуйте свою статистику та змагайтеся з друзями.\n\n"
        "🎯 Головні команди:\n"
        "/add - Додати новий запис\n"
        "/stats - Моя статистика\n"
        "/top - Рейтинг користувачів\n\n"
        "❓ Детальніше: /help"
    )
# Додаємо команду для перегляду статистики користувача
@app.on_message(filters.command("stats"))
async def stats_command(client, message):
    await message.reply_text("⚙️ Ця команда знаходиться в розробці. Слідкуйте за оновленнями!")
    user_id = message.from_user.id

    conn = sqlite3.connect(config['database']['path'])
    c = conn.cursor()
    
    # Персональна статистика для користувача
    c.execute('''
        SELECT 
            COUNT(*) as total_records,
            COALESCE(SUM(CASE WHEN status = 'approved' THEN volume ELSE 0 END), 0) as total_volume,
            COALESCE(SUM(CASE WHEN status = 'approved' THEN volume * proof / 100 ELSE 0 END), 0) as total_pure_alcohol
        FROM drinks
        WHERE user_id = ?
    ''', (user_id,))
    stats = c.fetchone() or (0, 0, 0)
    
    c.execute('''
        SELECT 
            alcohol_type,
            COUNT(*) as count,
            COALESCE(SUM(CASE WHEN status = 'approved' THEN volume ELSE 0 END), 0) as volume
        FROM drinks
        WHERE user_id = ?
        GROUP BY alcohol_type
        ORDER BY volume DESC
    ''', (user_id,))
    types_stats = c.fetchall()
    
    conn.close()
    
    text = "📊 Ваша персональна статистика:\n\n"
    text += f"📝 Всього записів: {stats[0]}\n"
    
    total_volume = stats[1]
    total_pure = stats[2]
    
    liters = total_volume // 1000
    ml = total_volume % 1000
    volume_text = f"{liters}л {ml}мл" if liters > 0 else f"{ml}мл"
    
    text += f"🥃 Загальний об'єм: {volume_text}\n"
    text += f"💪 Чистого спирту: {total_pure:.1f}мл\n\n"
    
    if types_stats:
        text += "🍷 По типам напоїв:\n"
        for type_name, count, volume in types_stats:
            if volume:
                liters = volume // 1000
                ml = volume % 1000
                volume_text = f"{liters}л {ml}мл" if liters > 0 else f"{ml}мл"
                text += f"- {config['alcohol_types'].get(type_name, {}).get('name', type_name)}: {volume_text} ({count} записів)\n"
    else:
        text += "🔹 У вас ще немає затверджених записів. Додайте свій перший запис!"
    
    await message.reply_text(text)

# Додаємо команду для перегляду історії записів
@app.on_message(filters.command("history"))
async def history_command(client, message: Message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect(config['database']['path'])
    c = conn.cursor()
    
    # Отримуємо останні 10 записів
    c.execute('''
        SELECT 
            alcohol_type,
            subtype,
            volume,
            proof,
            status,
            timestamp
        FROM drinks
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT 10
    ''', (user_id,))
    history = c.fetchall()
    conn.close()
    
    if not history:
        await message.reply_text("📭 У вас поки що немає записів.")
        return
    
    text = "📜 Останні 10 записів:\n\n"
    for alcohol_type, subtype, volume, proof, status, timestamp in history:
        dt = datetime.fromisoformat(timestamp)
        formatted_date = dt.strftime("%d.%m.%Y %H:%M")
        
        status_emoji = {
            'pending': '⏳',
            'approved': '✅',
            'rejected': '❌'
        }.get(status, '❓')
        
        text += f"{formatted_date}\n"
        text += f"{status_emoji} {config['alcohol_types'][alcohol_type]['name']} ({subtype})\n"
        text += f"└ {volume}мл, {proof}%\n\n"
    
    await message.reply_text(text)
# Команда /types
@app.on_message(filters.command("types"))
async def types_command(client, message: Message):
    text = "📋 Доступні типи алкоголю:\n\n"
    for alcohol_id, details in config['alcohol_types'].items():
        text += f"🍷 {details['name']} ({details['strength']}%)\n"
        text += f"└ Підтипи: {', '.join(details['subtypes'])}\n"
    await message.reply_text(text)

# Команда /top
@app.on_message(filters.command("top"))
async def top_command(client, message: Message):
    conn = sqlite3.connect(config['database']['path'])
    c = conn.cursor()
    c.execute('''
        SELECT 
            user_id,
            username,
            SUM(volume) as total_volume,
            SUM(volume * proof / 100) as total_pure_alcohol
        FROM drinks 
        WHERE status = 'approved'
        GROUP BY user_id
        ORDER BY total_pure_alcohol DESC
        LIMIT 10
    ''')
    results = c.fetchall()
    conn.close()

    if not results:
        await message.reply_text("📊 Поки що немає даних для відображення.")
        return

    text = "🏆 Топ-10 по випитому:\n\n"
    for i, (user_id, username, volume, pure_alcohol) in enumerate(results, 1):
        liters = volume // 1000
        ml = volume % 1000
        volume_text = f"{liters}л {ml}мл" if liters > 0 else f"{ml}мл"
        text += f"{i}. {username}: {volume_text} (чистого спирту: {pure_alcohol:.1f}мл)\n"

    await message.reply_text(text)

# Команда /add для додавання нового запису
@app.on_message(filters.command("add"))
async def add_command(client, message: Message):
    user_id = message.from_user.id
    
    # Перевіряємо чи користувач не забанений
    ban_until = is_user_banned(user_id)
    if ban_until:
        await message.reply_text(
            f"❌ Ви заблоковані до {ban_until.strftime('%d.%m.%Y %H:%M')}!\n"
            "Спробуйте пізніше."
        )
        return
    
    # Перевіряємо чи користувач вже не додає запис
    if hasattr(app, 'temp_data') and user_id in app.temp_data:
        await message.reply_text(
            "❌ У вас вже є активна сесія додавання запису.\n"
            "Будь ласка, завершіть її або почекайте 5 хвилин для автоматичного скидання."
        )
        return
    
    # Ініціалізуємо тимчасові дані
    if not hasattr(app, 'temp_data'):
        app.temp_data = {}
    
    app.temp_data[user_id] = {
        'waiting_for_video': True,
        'user_id': user_id,
        'username': message.from_user.username or message.from_user.first_name
    }
    
    await message.reply_text(
        "🎥 Будь ласка, надішліть відео-кружечок з доказом випитого алкоголю.\n"
        "⚠️ Приймаються тільки відео-кружечки!\n"
        "⚠️ Відео має чітко показувати процес вживання!"
    )

# Глобальна змінна для зберігання статусу паузи для кожного адміна
if not hasattr(app, 'admin_paused'):
    app.admin_paused = set()

# Команда /requests для адміністраторів
@app.on_message(filters.command("requests"))
async def requests_command(client, message: Message):
    if not is_admin(message.from_user.id):
        await message.reply_text("❌ Ця команда доступна тільки адміністраторам!")
        return
        
    conn = sqlite3.connect(config['database']['path'])
    c = conn.cursor()
    
    # Отримуємо всі pending заявки
    c.execute('''
        SELECT 
            id,
            user_id,
            username,
            alcohol_type,
            subtype,
            volume,
            proof,
            video_file_id,
            timestamp
        FROM drinks
        WHERE status = 'pending'
        ORDER BY timestamp DESC
    ''')
    pending_requests = c.fetchall()
    conn.close()
    
    if not pending_requests:
        pause_button = InlineKeyboardButton(
            "⏸️ Призупинити сповіщення" if message.from_user.id not in app.admin_paused else "▶️ Відновити сповіщення",
            callback_data="toggle_pause"
        )
        await message.reply_text(
            "📭 Немає активних заявок на розгляд.",
            reply_markup=InlineKeyboardMarkup([[pause_button]])
        )
        return
    
    # Відправляємо кожну заявку окремим повідомленням
    for request in pending_requests:
        (req_id, user_id, username, alcohol_type, subtype, volume, proof, video_id, timestamp) = request
        
        # Форматуємо дату
        dt = datetime.fromisoformat(timestamp)
        formatted_date = dt.strftime("%d.%m.%Y %H:%M")
        
        try:
            # Спочатку надсилаємо відео-кружечок
            await client.send_video_note(
                chat_id=message.chat.id,
                video_note=video_id
            )
            
            # Потім надсилаємо інформацію окремим повідомленням
            await client.send_message(
                chat_id=message.chat.id,
                text=(
                    f"📝 Заявка #{req_id}\n"
                    f"📅 Дата: {formatted_date}\n"
                    f"👤 Користувач: {username}\n"
                    f"🍷 Тип: {config['alcohol_types'][alcohol_type]['name']}\n"
                    f"📝 Підтип: {subtype}\n"
                    f"🔢 Об'єм: {volume}мл\n"
                    f"💪 Міцність: {proof}%"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Підтвердити", callback_data=f"approve_{user_id}_{volume}"),
                        InlineKeyboardButton("❌ Відхилити", callback_data=f"reject_{user_id}_{volume}")
                    ]
                ])
            )
        except Exception as e:
            print(f"Помилка при відправці відео для заявки #{req_id}: {e}")
            continue
    
    # Додаємо кнопку паузи/відновлення в окремому повідомленні
    pause_button = InlineKeyboardButton(
        "⏸️ Призупинити сповіщення" if message.from_user.id not in app.admin_paused else "▶️ Відновити сповіщення",
        callback_data="toggle_pause"
    )
    await message.reply_text(
        f"📋 Всього активних заявок: {len(pending_requests)}",
        reply_markup=InlineKeyboardMarkup([[pause_button]])
    )

# Оновлюємо обробку callback-кнопок
@app.on_callback_query()
async def handle_callback(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    # Обробка паузи/відновлення сповіщень
    if data == "toggle_pause" and is_admin(user_id):
        if user_id in app.admin_paused:
            app.admin_paused.remove(user_id)
            await callback_query.message.edit_text(
                callback_query.message.text + "\n\n▶️ Сповіщення відновлено!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⏸️ Призупинити сповіщення", callback_data="toggle_pause")
                ]])
            )
        else:
            app.admin_paused.add(user_id)
            await callback_query.message.edit_text(
                callback_query.message.text + "\n\n⏸️ Сповіщення призупинено!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("▶️ Відновити сповіщення", callback_data="toggle_pause")
                ]])
            )
        return
    
    # Обробка підтвердження/відхилення адміністратором
    if data.startswith(('approve_', 'reject_')):
        if not is_admin(user_id):
            await callback_query.answer("❌ Ця дія доступна тільки адміністраторам!", show_alert=True)
            return
            
        # Обробка звичайних записів
        action, target_user_id, volume = data.split('_')
        target_user_id = int(target_user_id)
        volume = int(volume)
        
        conn = sqlite3.connect(config['database']['path'])
        c = conn.cursor()
        
        if action == 'approve':
            # Спочатку знаходимо ID запису
            c.execute('''
                SELECT id FROM drinks 
                WHERE user_id = ? AND volume = ? AND status = 'pending'
                ORDER BY id DESC LIMIT 1
            ''', (target_user_id, volume))
            
            result = c.fetchone()
            if result:
                record_id = result[0]
                # Тепер оновлюємо конкретний запис
                c.execute('''
                    UPDATE drinks 
                    SET status = 'approved' 
                    WHERE id = ?
                ''', (record_id,))
                
                if c.rowcount > 0:
                    await callback_query.message.edit_text(
                        callback_query.message.text + "\n\n✅ Підтверджено!"
                    )
                    
                    # Повідомляємо користувача
                    try:
                        await client.send_message(
                            chat_id=target_user_id,
                            text="🎉 Ваш запис було підтверджено адміністратором!"
                        )
                    except Exception:
                        pass
            
        else:  # reject
            # Спочатку знаходимо ID запису
            c.execute('''
                SELECT id, username FROM drinks 
                WHERE user_id = ? AND volume = ? AND status = 'pending'
                ORDER BY id DESC LIMIT 1
            ''', (target_user_id, volume))
            
            result = c.fetchone()
            if result:
                record_id, username = result
                # Оновлюємо статус запису
                c.execute('''
                    UPDATE drinks 
                    SET status = 'rejected' 
                    WHERE id = ?
                ''', (record_id,))
                
                if c.rowcount > 0:
                    # Отримуємо інформацію про порушення
                    rejected_count, next_ban_duration = get_user_info(target_user_id)
                    
                    # Якщо це не перше порушення, баним користувача
                    ban_info = ""
                    if rejected_count >= 3:
                        ban_until = ban_user(target_user_id, username, next_ban_duration)
                        ban_info = f"\n\n🚫 Користувача заблоковано до {ban_until.strftime('%d.%m.%Y %H:%M')}"
                    
                    await callback_query.message.edit_text(
                        callback_query.message.text + f"\n\n❌ Відхилено!\n📊 Всього відхилень: {rejected_count}{ban_info}"
                    )
                    
                    # Повідомляємо користувача
                    try:
                        message = "❌ Ваш запис було відхилено адміністратором."
                        if ban_info:
                            message += f"\n{ban_info}"
                        await client.send_message(
                            chat_id=target_user_id,
                            text=message
                        )
                    except Exception:
                        pass
        
        conn.commit()
        conn.close()
        return
        
    # Обробка інших callback-кнопок (вибір типу, підтипу, об'єму)
    if not hasattr(app, 'temp_data') or user_id not in app.temp_data:
        await callback_query.answer("❌ Сесія закінчилася. Будь ласка, надішліть відео знову.", show_alert=True)
        return
    
    # Обробка вибору типу алкоголю
    if data.startswith('alcohol_'):
        alcohol_type = data.split('_')[1]
        app.temp_data[user_id]['alcohol_type'] = alcohol_type
        
        # Створюємо клавіатуру з підтипами
        keyboard = []
        row = []
        for subtype in config['alcohol_types'][alcohol_type]['subtypes']:
            if len(row) == 2:
                keyboard.append(row)
                row = []
            row.append(InlineKeyboardButton(
                subtype,
                callback_data=f"subtype_{alcohol_type}_{subtype}"
            ))
        if row:
            keyboard.append(row)
            
        await callback_query.message.edit_text(
            f"🥃 Виберіть підтип {config['alcohol_types'][alcohol_type]['name']}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    # Обробка вибору підтипу
    elif data.startswith('subtype_'):
        _, alcohol_type, subtype = data.split('_')
        app.temp_data[user_id]['subtype'] = subtype
        app.temp_data[user_id]['proof'] = config['alcohol_types'][alcohol_type]['strength']
        
        # Створюємо клавіатуру для вибору об'єму
        default_volume = config['alcohol_types'][alcohol_type]['default_volume']
        keyboard = [
            [
                InlineKeyboardButton(f"{default_volume}мл", callback_data=f"volume_{default_volume}"),
                InlineKeyboardButton(f"{default_volume*2}мл", callback_data=f"volume_{default_volume*2}")
            ],
            [
                InlineKeyboardButton("Інший об'єм", callback_data="volume_custom")
            ]
        ]
        
        await callback_query.message.edit_text(
            "🔢 Виберіть об'єм або введіть свій:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    # Обробка вибору об'єму
    elif data.startswith('volume_'):
        volume = data.split('_')[1]
        
        if volume == 'custom':
            await callback_query.message.edit_text(
                "📝 Введіть об'єм в мілілітрах (наприклад: 750):"
            )
            app.temp_data[user_id]['waiting_for_volume'] = True
        else:
            volume = int(volume)
            app.temp_data[user_id]['volume'] = volume
            
            # Зберігаємо запис
            save_drink(
                user_id=app.temp_data[user_id]['user_id'],
                username=app.temp_data[user_id]['username'],
                alcohol_type=app.temp_data[user_id]['alcohol_type'],
                subtype=app.temp_data[user_id]['subtype'],
                volume=volume,
                proof=app.temp_data[user_id]['proof'],
                video_file_id=app.temp_data[user_id]['file_id']
            )
            
            await callback_query.message.edit_text(
                "✅ Запис збережено і відправлено на підтвердження адміністратору!\n"
                f"Тип: {config['alcohol_types'][app.temp_data[user_id]['alcohol_type']]['name']}\n"
                f"Підтип: {app.temp_data[user_id]['subtype']}\n"
                f"Об'єм: {volume}мл\n"
                f"Міцність: {app.temp_data[user_id]['proof']}%"
            )
            
            # Надсилаємо повідомлення адмінам
            for admin_id in config['bot']['admin_ids']:
                await send_video_to_admin(
                    client,
                    admin_id,
                    app.temp_data[user_id],
                    app.temp_data[user_id].get('is_video_note', True)
                )
            
            # Очищаємо тимчасові дані
            del app.temp_data[user_id]

# Обробка введення користувацького об'єму
@app.on_message(filters.text & filters.private)
async def handle_text(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Перевіряємо чи користувач в процесі додавання об'єму
    if hasattr(app, 'temp_data') and user_id in app.temp_data and app.temp_data[user_id].get('waiting_for_volume'):
        try:
            volume = int(message.text)
            if volume <= 0:
                raise ValueError
                
            app.temp_data[user_id]['volume'] = volume
            app.temp_data[user_id]['waiting_for_volume'] = False
            
            # Зберігаємо запис
            save_drink(
                user_id=app.temp_data[user_id]['user_id'],
                username=app.temp_data[user_id]['username'],
                alcohol_type=app.temp_data[user_id]['alcohol_type'],
                subtype=app.temp_data[user_id]['subtype'],
                volume=volume,
                proof=app.temp_data[user_id]['proof'],
                video_file_id=app.temp_data[user_id]['file_id']
            )
            
            await message.reply_text(
                "✅ Запис збережено і відправлено на підтвердження адміністратору!\n"
                f"Тип: {config['alcohol_types'][app.temp_data[user_id]['alcohol_type']]['name']}\n"
                f"Підтип: {app.temp_data[user_id]['subtype']}\n"
                f"Об'єм: {volume}мл\n"
                f"Міцність: {app.temp_data[user_id]['proof']}%"
            )
            
            # Надсилаємо повідомлення адмінам
            for admin_id in config['bot']['admin_ids']:
                await send_video_to_admin(
                    client,
                    admin_id,
                    app.temp_data[user_id],
                    app.temp_data[user_id].get('is_video_note', True)
                )
            
            # Очищаємо тимчасові дані
            del app.temp_data[user_id]
            
        except ValueError:
            await message.reply_text("❌ Будь ласка, введіть коректне число в мілілітрах (наприклад: 750)")
        return
    
    # Перевіряємо чи користувач в процесі додавання пропозиції
    if hasattr(app, 'suggest_data') and user_id in app.suggest_data:
        suggest_data = app.suggest_data[user_id]
        
        if suggest_data['step'] == 'name':
            suggest_data['name'] = message.text
            suggest_data['step'] = 'strength'
            await message.reply_text(
                "2️⃣ Введіть міцність напою у відсотках (наприклад: 40):"
            )
            
        elif suggest_data['step'] == 'strength':
            try:
                strength = float(message.text)
                if strength <= 0 or strength > 100:
                    raise ValueError
                
                suggest_data['strength'] = strength
                suggest_data['step'] = 'subtypes'
                await message.reply_text(
                    "3️⃣ Введіть підтипи напою через кому (наприклад: Світле, Темне, Нефільтроване):"
                )
                
            except ValueError:
                await message.reply_text("❌ Будь ласка, введіть коректне число від 1 до 100.")
                
        elif suggest_data['step'] == 'subtypes':
            subtypes = [s.strip() for s in message.text.split(',')]
            suggest_data['subtypes'] = ','.join(subtypes)
            
            # Зберігаємо пропозицію
            conn = sqlite3.connect(config['database']['path'])
            c = conn.cursor()
            c.execute('''
                INSERT INTO alcohol_suggestions (user_id, username, name, strength, subtypes)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, suggest_data['username'], suggest_data['name'], 
                  suggest_data['strength'], suggest_data['subtypes']))
            conn.commit()
            conn.close()
            
            # Надсилаємо повідомлення адміністраторам
            for admin_id in config['bot']['admin_ids']:
                try:
                    await client.send_message(
                        chat_id=admin_id,
                        text=(
                            "🆕 Нова пропозиція типу алкоголю!\n\n"
                            f"👤 Від користувача: {suggest_data['username']}\n"
                            f"🍷 Назва: {suggest_data['name']}\n"
                            f"💪 Міцність: {suggest_data['strength']}%\n"
                            f"📝 Підтипи: {suggest_data['subtypes']}"
                        ),
                        reply_markup=InlineKeyboardMarkup([
                            [
                                InlineKeyboardButton("✅ Прийняти", 
                                    callback_data=f"approve_suggest_{user_id}_{len(subtypes)}"),
                                InlineKeyboardButton("❌ Відхилити", 
                                    callback_data=f"reject_suggest_{user_id}_{len(subtypes)}")
                            ]
                        ])
                    )
                except Exception as e:
                    print(f"Помилка при надсиланні пропозиції адміну {admin_id}: {e}")
            
            await message.reply_text(
                "✅ Дякуємо за пропозицію! Вона буде розглянута адміністраторами."
            )
            
            # Очищаємо дані пропозиції
            del app.suggest_data[user_id]
# Оновлюємо функцію надсилання відео адміністратору
async def send_video_to_admin(client, admin_id, user_data, is_video_note=True):
    # Перевіряємо чи адмін не на паузі
    if admin_id in app.admin_paused:
        return
        
    try:
        # Спочатку надсилаємо відео-кружечок
        await client.send_video_note(
            chat_id=admin_id,
            video_note=user_data['file_id']
        )
        
        # Потім надсилаємо інформацію окремим повідомленням
        await client.send_message(
            chat_id=admin_id,
            text=(
                "🆕 Новий запис на підтвердження!\n"
                f"👤 Користувач: {user_data['username']}\n"
                f"🍷 Тип: {config['alcohol_types'][user_data['alcohol_type']]['name']}\n"
                f"📝 Підтип: {user_data['subtype']}\n"
                f"🔢 Об'єм: {user_data['volume']}мл\n"
                f"💪 Міцність: {user_data['proof']}%"
            ),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Підтвердити", callback_data=f"approve_{user_data['user_id']}_{user_data['volume']}"),
                    InlineKeyboardButton("❌ Відхилити", callback_data=f"reject_{user_data['user_id']}_{user_data['volume']}")
                ]
            ])
        )
    except Exception as e:
        print(f"Помилка при надсиланні відео адміністратору {admin_id}: {e}")

# Оновлюємо обробку відео
@app.on_message(filters.video_note)
async def handle_video(client, message: Message):
    user_id = message.from_user.id
    
    # Перевіряємо чи користувач в процесі додавання запису
    if not hasattr(app, 'temp_data') or user_id not in app.temp_data or not app.temp_data[user_id].get('waiting_for_video'):
        await message.reply_text(
            "❌ Будь ласка, спочатку використайте команду /add для початку додавання запису."
        )
        return
    
    # Зберігаємо file_id відео
    app.temp_data[user_id]['file_id'] = message.video_note.file_id
    app.temp_data[user_id]['waiting_for_video'] = False
    
    # Створюємо клавіатуру з типами алкоголю
    keyboard = []
    row = []
    for alcohol_id, details in config['alcohol_types'].items():
        if len(row) == 2:
            keyboard.append(row)
            row = []
        row.append(InlineKeyboardButton(
            details['name'],
            callback_data=f"alcohol_{alcohol_id}"
        ))
    if row:
        keyboard.append(row)

    await message.reply_text(
        "🍷 Виберіть тип алкоголю:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Додаємо обробник для звичайних відео
@app.on_message(filters.video)
async def handle_regular_video(client, message: Message):
    user_id = message.from_user.id
    
    # Перевіряємо чи користувач в процесі додавання запису
    if not hasattr(app, 'temp_data') or user_id not in app.temp_data or not app.temp_data[user_id].get('waiting_for_video'):
        return
    
    await message.reply_text(
        "❌ Вибачте, але приймаються тільки відео-кружечки.\n"
        "Будь ласка, надішліть ваше відео у форматі відео-кружечка."
    )

# Додаємо функцію для роботи з порушеннями
def get_user_violations(user_id):
    conn = sqlite3.connect(config['database']['path'])
    c = conn.cursor()
    
    # Отримуємо кількість відхилених заявок
    c.execute('''
        SELECT COUNT(*) 
        FROM drinks 
        WHERE user_id = ? AND status = 'rejected'
    ''', (user_id,))
    rejected_count = c.fetchone()[0]
    
    # Отримуємо історію банів
    c.execute('''
        SELECT violation_type, ban_duration, ban_until, timestamp
        FROM violations
        WHERE user_id = ?
        ORDER BY timestamp DESC
    ''', (user_id,))
    violations = c.fetchall()
    
    conn.close()
    return rejected_count, violations

# Функція для бану користувача
def ban_user(user_id, username, duration_hours):
    conn = sqlite3.connect(config['database']['path'])
    c = conn.cursor()
    
    ban_until = datetime.now().replace(microsecond=0)
    ban_until = ban_until.replace(hour=ban_until.hour + duration_hours)
    
    c.execute('''
        INSERT INTO violations (user_id, username, violation_type, ban_duration, ban_until)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, 'rejection_ban', duration_hours, ban_until))
    
    conn.commit()
    conn.close()
    return ban_until

# Функція перевірки чи користувач забанений
def is_user_banned(user_id):
    conn = sqlite3.connect(config['database']['path'])
    c = conn.cursor()
    
    c.execute('''
        SELECT ban_until
        FROM violations
        WHERE user_id = ? AND ban_until > datetime('now')
        ORDER BY ban_until DESC
        LIMIT 1
    ''', (user_id,))
    
    result = c.fetchone()
    conn.close()
    
    if result:
        return datetime.fromisoformat(result[0])
    return None

# Оновлюємо функцію для отримання інформації про користувача
def get_user_info(user_id):
    rejected_count, violations = get_user_violations(user_id)
    
    # Визначаємо тривалість наступного бану
    if rejected_count == 0:
        next_ban_duration = 72  # 3 дні для першого порушення
    else:
        last_ban = violations[0][1] if violations else 72
        if rejected_count > len(violations) * 2:
            next_ban_duration = min(last_ban * 2, 720)  # Максимум 30 днів
        else:
            next_ban_duration = max(72, last_ban // 2)  # Зменшуємо покарання
            
    return rejected_count, next_ban_duration



# Запуск бота
if __name__ == "__main__":
    init_db()
    print("AlcoMeterBot запущено!")
    app.run()