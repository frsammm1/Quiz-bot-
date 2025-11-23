import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import google.generativeai as genai
import json
import random
import time
import asyncio

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not GEMINI_API_KEY or not TELEGRAM_TOKEN:
    logger.error("❌ Environment variables missing!")
    exit(1)

logger.info(f"🔑 API Key: {GEMINI_API_KEY[:20]}...")

try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    logger.info("✅ Gemini API configured successfully")
except Exception as e:
    logger.error(f"❌ Gemini API configuration failed: {e}")
    exit(1)

user_sessions = {}

ENGLISH_TOPICS = [
    "synonyms", "antonyms", "idioms", "grammar", "spelling",
    "sentence correction", "fill in blanks", "one word substitution"
]

GK_TOPICS = [
    "Indian History", "Indian Geography", "Indian Polity",
    "Indian Economy", "General Science", "Current Affairs",
    "Awards", "Sports", "Books and Authors"
]

def clean_json_response(text):
    """Clean and extract JSON from AI response"""
    try:
        # Remove markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        # Find JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]
        
        # Clean up
        text = text.strip()
        return text
    except Exception as e:
        logger.error(f"Error cleaning JSON: {e}")
        return text

async def generate_with_retry(prompt, max_retries=3):
    """Generate content with retry logic"""
    for attempt in range(max_retries):
        try:
            logger.info(f"🤖 Generating content (attempt {attempt + 1}/{max_retries})")
            
            response = await asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.9,
                    top_p=0.95,
                    top_k=40,
                    max_output_tokens=800,
                )
            )
            
            if response and response.text:
                logger.info(f"✅ Got response: {response.text[:100]}...")
                return response.text
            
            logger.warning(f"⚠️ Empty response on attempt {attempt + 1}")
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"❌ Error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(3)
            else:
                raise
    
    return None

async def generate_question(subject, user_id):
    """Generate question using Gemini AI"""
    
    random_num = random.randint(1000, 9999)
    topic = random.choice(ENGLISH_TOPICS if subject == "English" else GK_TOPICS)
    
    if subject == "English":
        prompt = f"""Create 1 SSC CGL/CHSL English question about {topic}.

Question must be moderately challenging, real exam level.

Return ONLY this JSON format (no other text):
{{
    "question": "Your question here",
    "options": ["A option", "B option", "C option", "D option"],
    "correct": 0,
    "explanation": "Why this answer is correct"
}}

Topic: {topic}
ID: {random_num}"""
    
    else:  # GK
        prompt = f"""Create 1 SSC CGL/CHSL GK question about {topic} in BILINGUAL format (Hindi | English).

Question must be factual, moderately challenging, real exam level.

Return ONLY this JSON format (no other text):
{{
    "question": "हिंदी प्रश्न | English question",
    "options": ["हिंदी A | English A", "हिंदी B | English B", "हिंदी C | English C", "हिंदी D | English D"],
    "correct": 0,
    "explanation": "हिंदी व्याख्या | English explanation"
}}

Topic: {topic}
ID: {random_num}"""
    
    try:
        text = await generate_with_retry(prompt)
        
        if not text:
            logger.error("❌ No response from AI")
            return None
        
        # Clean and parse JSON
        cleaned = clean_json_response(text)
        data = json.loads(cleaned)
        
        # Validate
        if all(k in data for k in ["question", "options", "correct", "explanation"]):
            if len(data["options"]) == 4 and 0 <= data["correct"] <= 3:
                logger.info(f"✅ Valid question generated: {data['question'][:50]}...")
                return data
        
        logger.error(f"❌ Invalid question structure: {data}")
        return None
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parse error: {e}")
        logger.error(f"Response was: {cleaned[:200]}")
        return None
    except Exception as e:
        logger.error(f"❌ Generation error: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📚 English", callback_data='subject_English')],
        [InlineKeyboardButton("🌍 GK", callback_data='subject_GK')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """🎓 *SSC CGL/CHSL Quiz Bot*

🤖 AI-Powered by Gemini
📝 Real exam level questions
🔄 Fresh questions every time

Select subject:"""
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith('subject_'):
        subject = data.replace('subject_', '')
        user_sessions[user_id] = {'subject': subject, 'score': 0, 'total': 0}
        await send_question(query, user_id, subject)
    
    elif data.startswith('answer_'):
        selected = int(data.split('_')[1])
        await check_answer(query, user_id, selected)
    
    elif data == 'next_question':
        subject = user_sessions.get(user_id, {}).get('subject', 'GK')
        await send_question(query, user_id, subject)
    
    elif data == 'back_to_menu':
        keyboard = [
            [InlineKeyboardButton("📚 English", callback_data='subject_English')],
            [InlineKeyboardButton("🌍 GK", callback_data='subject_GK')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if user_id in user_sessions:
            score = user_sessions[user_id]['score']
            total = user_sessions[user_id]['total']
            text = f"📊 Score: {score}/{total}\n\nSelect subject:"
        else:
            text = "Select subject:"
        
        await query.edit_message_text(text, reply_markup=reply_markup)

async def send_question(query, user_id, subject):
    try:
        await query.edit_message_text(
            "⏳ Generating question...\n\n🤖 AI is thinking...\n\n"
            "This may take 5-10 seconds..."
        )
        
        question_data = await generate_question(subject, user_id)
        
        if not question_data:
            keyboard = [[InlineKeyboardButton("🔄 Try Again", callback_data='next_question')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "⚠️ Unable to generate question.\n\n"
                "This could be due to:\n"
                "• API rate limits\n"
                "• Network issues\n\n"
                "Please try again in a moment.",
                reply_markup=reply_markup
            )
            return
        
        user_sessions[user_id]['current_question'] = question_data
        
        keyboard = []
        labels = ['A', 'B', 'C', 'D']
        for i, option in enumerate(question_data['options']):
            keyboard.append([InlineKeyboardButton(
                f"{labels[i]}. {option}", 
                callback_data=f'answer_{i}'
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        question_text = f"❓ *Question:*\n\n{question_data['question']}"
        
        await query.edit_message_text(
            question_text, 
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )
    
    except Exception as e:
        logger.error(f"Error in send_question: {e}")
        keyboard = [[InlineKeyboardButton("🔄 Try Again", callback_data='next_question')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"❌ Error: {str(e)[:100]}\n\nPlease try again.",
            reply_markup=reply_markup
        )

async def check_answer(query, user_id, selected):
    try:
        if user_id not in user_sessions or 'current_question' not in user_sessions[user_id]:
            await query.edit_message_text("⚠️ Session expired. /start again.")
            return
        
        q_data = user_sessions[user_id]['current_question']
        correct = q_data['correct']
        user_sessions[user_id]['total'] += 1
        
        labels = ['A', 'B', 'C', 'D']
        
        if selected == correct:
            user_sessions[user_id]['score'] += 1
            result = "✅ *Correct!*\n\n"
        else:
            result = f"❌ *Wrong!*\n\nYou selected: {labels[selected]}. {q_data['options'][selected]}\n\n"
        
        result += f"✔️ Answer: *{labels[correct]}. {q_data['options'][correct]}*\n\n"
        result += f"💡 {q_data['explanation']}\n\n"
        result += f"📊 Score: {user_sessions[user_id]['score']}/{user_sessions[user_id]['total']}"
        
        keyboard = [
            [InlineKeyboardButton("➡️ Next", callback_data='next_question')],
            [InlineKeyboardButton("🏠 Menu", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(result, reply_markup=reply_markup, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error in check_answer: {e}")
        await query.edit_message_text(f"❌ Error: {str(e)}")

async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is alive and connected to Gemini AI!")

def main():
    logger.info("🚀 Starting SSC Quiz Bot...")
    logger.info(f"🔑 Using Gemini API Key: {GEMINI_API_KEY[:20]}...")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("health", health_check))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("✅ Bot is ready!")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
