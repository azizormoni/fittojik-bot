import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import anthropic

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Клиент Anthropic
ai = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# Системный промпт — мозг бота
SYSTEM = """Ты FitTojik — AI мураббии фитнес барои аудитории тоҷик.
Ту ҲАМЕША бо забони тоҷикӣ ҷавоб медиҳӣ.

Вазифаҳои ту:
- Маслиҳат дар бораи ғизо, калория, вазн ва машқ
- Ҳисоби калорияи ғизои тоҷикӣ
- Барномаи машқ тартиб деҳ
- Дӯстона, содда ва бо эмодзи ҷавоб деҳ 💪
- Ҷавобҳоят кӯтоҳ бошанд (3-5 ҷумла)

Калорияи ғизои тоҷикӣ:
- Ош (плов) 200г: 380-420 ккал
- Шӯрбо 300мл: 130-160 ккал  
- Кабоб 150г: 290-320 ккал
- Нон 100г: 240-260 ккал
- Самбӯса 1 дона: 290-320 ккал
- Лағмон 300г: 320-370 ккал
- Манту 3 дона: 280-320 ккал
- Чакка 100г: 80-100 ккал"""

# История чатов (в памяти)
user_history = {}

def get_history(user_id):
    if user_id not in user_history:
        user_history[user_id] = []
    return user_history[user_id]

async def ask_ai(user_id: int, message: str) -> str:
    history = get_history(user_id)
    history.append({"role": "user", "content": message})
    
    # Оставляем только последние 20 сообщений
    if len(history) > 20:
        history = history[-20:]
        user_history[user_id] = history

    try:
        response = ai.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=SYSTEM,
            messages=history
        )
        reply = response.content[0].text
        history.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        logger.error(f"AI error: {e}")
        return "Хатогӣ рӯй дод 😔 Лутфан дубора кӯшиш кунед."

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 Акси ғизо — Калория ҳисоб", callback_data="photo_hint")],
        [
            InlineKeyboardButton("💪 Машқҳо", callback_data="exercises"),
            InlineKeyboardButton("🥗 Ғизои солим", callback_data="nutrition"),
        ],
        [
            InlineKeyboardButton("📊 Ҳолати ман", callback_data="stats"),
            InlineKeyboardButton("🎯 Ҳадафи ман", callback_data="goal"),
        ],
        [InlineKeyboardButton("💬 Бо AI сӯҳбат кунам", callback_data="chat")],
    ])

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "Дӯст"
    
    text = (
        f"Салом, {name}! 👋\n\n"
        f"Ман *FitTojik* — мураббии AI-и фитнеси шумо ҳастам 💪\n\n"
        f"Ман ба шумо кӯмак мекунам:\n"
        f"📸 Акси ғизо фиристед — калорияро ҳисоб мекунам\n"
        f"💪 Машқҳои дурусти варзиш\n"
        f"🥗 Маслиҳат дар бораи ғизои солим\n"
        f"🎯 Ба ҳадафатон расидан\n\n"
        f"Аз куҷо оғоз кунем? 👇"
    )
    
    await update.message.reply_text(
        text, 
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

# /help
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 *Кӯмак*\n\n"
        "📸 *Акси ғизо* — акс фиристед, калория ҳисоб мекунам\n"
        "💬 *Ҳар савол* — бинависед, ҷавоб медиҳам\n"
        "🔄 */start* — меню\n"
        "🗑 */reset* — сӯҳбатро тоза кунед",
        parse_mode="Markdown"
    )

# /reset
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_history[user_id] = []
    await update.message.reply_text(
        "✅ Сӯҳбат тоза шуд! Аз нав оғоз мекунем 🔄",
        reply_markup=main_keyboard()
    )

# Текстовые сообщения — идут в AI
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    await update.message.chat.send_action("typing")
    reply = await ask_ai(user_id, text)
    
    await update.message.reply_text(
        reply,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Меню", callback_data="menu")]
        ])
    )

# Фото — анализ еды
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    caption = update.message.caption or ""
    
    await update.message.chat.send_action("typing")
    
    prompt = f"Корбар акси ғизо фиристод. {('Тавзеҳ: ' + caption) if caption else ''} Ба монанди он ки ту ғизоро дидӣ, калория ва БЖУ-ро ҳисоб кун ва маслиҳат деҳ. Агар ғизои тоҷикӣ бошад — мисли ош, шӯрбо, кабоб ва ғайра — ба таври дақиқ ҷавоб деҳ."
    
    reply = await ask_ai(user_id, prompt)
    
    await update.message.reply_text(
        f"📸 *Таҳлили ғизо:*\n\n{reply}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📸 Акси дигар", callback_data="photo_hint")],
            [InlineKeyboardButton("🏠 Меню", callback_data="menu")]
        ])
    )

# Кнопки
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "menu":
        await query.message.reply_text(
            "🏠 Асосӣ:", reply_markup=main_keyboard()
        )

    elif data == "photo_hint":
        await query.message.reply_text(
            "📸 *Акси ғизоро фиристед!*\n\n"
            "Ман дарҳол ҳисоб мекунам:\n"
            "🔥 Калория\n🥩 Сафеда\n🧈 Равған\n🍞 Карбогидрат\n\n"
            "Ҳамчунин маслиҳат медиҳам — оё ин ғизо барои ҳадафи шумо мувофиқ аст.",
            parse_mode="Markdown"
        )

    elif data == "exercises":
        reply = await ask_ai(user_id, "Барои одами мубтадӣ машқҳои беҳтарин кадомҳоянд? Рӯйхати кӯтоҳ бо тавзеҳ деҳ.")
        await query.message.reply_text(
            f"💪 *Машқҳо:*\n\n{reply}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Меню", callback_data="menu")]
            ])
        )

    elif data == "nutrition":
        reply = await ask_ai(user_id, "Барои вазн кам кардан кадом ғизоҳоро хӯрам ва кадомро нахӯрам? Маслиҳати амалӣ деҳ.")
        await query.message.reply_text(
            f"🥗 *Ғизои солим:*\n\n{reply}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Меню", callback_data="menu")]
            ])
        )

    elif data == "stats":
        await query.message.reply_text(
            "📊 *Ҳолати шумо:*\n\n"
            "Барои пайгирии дақиқ маълумоти зеринро нависед:\n\n"
            "• Вазни шумо (кг)\n"
            "• Қади шумо (см)\n"
            "• Синну соли шумо\n"
            "• Ҳадафи шумо\n\n"
            "Ман нормаи калория ва барномаи шахсиро ҳисоб мекунам! 🎯",
            parse_mode="Markdown"
        )

    elif data == "goal":
        await query.message.reply_text(
            "🎯 *Ҳадафи шумо чист?*\n\n"
            "Бинависед ё интихоб кунед:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬇️ Вазн кам кунам", callback_data="goal_lose")],
                [InlineKeyboardButton("⬆️ Вазн зиёд кунам", callback_data="goal_gain")],
                [InlineKeyboardButton("💪 Мушак месозам", callback_data="goal_muscle")],
                [InlineKeyboardButton("🏃 Солим мемонам", callback_data="goal_health")],
            ])
        )

    elif data in ["goal_lose", "goal_gain", "goal_muscle", "goal_health"]:
        goals = {
            "goal_lose": "вазн кам кардан",
            "goal_gain": "вазн зиёд кардан",
            "goal_muscle": "мушаксозӣ",
            "goal_health": "солим мондан"
        }
        goal = goals[data]
        reply = await ask_ai(user_id, f"Ҳадафи ман {goal} аст. Нормаи калория ва барномаи умумии ғизо ва машқро барои ман тартиб деҳ.")
        await query.message.reply_text(
            f"🎯 *Барномаи шумо ({goal}):*\n\n{reply}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Меню", callback_data="menu")]
            ])
        )

    elif data == "chat":
        await query.message.reply_text(
            "💬 Ҳозир бо ман сӯҳбат карда метавонед!\n\n"
            "Ҳар саволе дар бораи фитнес, ғизо ё тандурустӣ дошта бошед — бинависед 👇"
        )

def main():
    token = os.environ["BOT_TOKEN"]
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("🚀 FitTojik бот оғоз ёфт!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
