import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import google.generativeai as genai
import json
import random
import time
from datetime import datetime

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

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

user_sessions = {}

# Topic pools for variety
ENGLISH_TOPICS = [
    "Fill in the blanks with appropriate preposition",
    "Identify grammatical error in sentence",
    "Choose correct synonym",
    "Choose correct antonym", 
    "Idioms and phrases meaning",
    "One word substitution",
    "Sentence improvement",
    "Active and passive voice conversion",
    "Direct and indirect speech",
    "Spellings - identify correct spelling",
    "Sentence rearrangement",
    "Cloze test",
    "Reading comprehension based question",
    "Para jumbles"
]

GK_TOPICS = [
    "Indian Freedom Struggle and Freedom Fighters",
    "Ancient Indian History - Mauryan, Gupta dynasty",
    "Medieval Indian History - Mughal Empire",
    "Modern Indian History - British Era",
    "Indian Geography - Rivers, Mountains, States",
    "World Geography - Countries, Capitals, Continents",
    "Indian Polity - Constitution, Fundamental Rights",
    "Indian Economy - GDP, Budget, Banking, RBI",
    "General Science - Physics concepts",
    "General Science - Chemistry concepts",
    "General Science - Biology and Human body",
    "Indian Art and Culture",
    "Books and Authors - Indian",
    "Important Awards - Bharat Ratna, Nobel Prize",
    "Sports - Olympics, Cricket, Commonwealth Games",
    "Important Days and Dates",
    "Current Affairs - Last 6 months events",
    "Famous Personalities of India",
    "World Organizations - UN, WHO, UNESCO",
    "Indian States - Capitals, CMs, Governors"
]

class QuizGenerator:
    @staticmethod
    def generate_question(subject, user_id):
        """Generate 100% AI questions - NO hardcoded fallbacks"""
        
        # Add extreme randomness
        timestamp = int(time.time())
        random_number = random.randint(10000, 99999)
        current_date = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Pick random topic for variety
        if subject == "English":
            random_topic = random.choice(ENGLISH_TOPICS)
            
            prompt = f"""You are an expert SSC CGL/CHSL English exam question creator.

CRITICAL INSTRUCTIONS:
- Generate a COMPLETELY NEW and UNIQUE question
- Question ID: {current_date}{random_number}
- Topic: {random_topic}
- Difficulty: SSC CGL Tier-1 level (Moderately Challenging)
- Make it different from typical questions
- Use varied sentence structures
- Include contemporary examples

Generate question on: {random_topic}

Return ONLY valid JSON in this EXACT format (no extra text):
{{
    "question": "Your unique challenging question here",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct": 0,
    "explanation": "Clear explanation with grammar rules/reasoning"
}}

Remember: Make it CHALLENGING but FAIR. Real SSC exam level!"""
        
        else:  # GK
            random_topic = random.choice(GK_TOPICS)
            
            prompt = f"""You are an expert SSC CGL/CHSL General Knowledge exam question creator.

CRITICAL INSTRUCTIONS:
- Generate a COMPLETELY NEW and UNIQUE question
- Question ID: {current_date}{random_number}
- Topic: {random_topic}
- Difficulty: SSC CGL Tier-1 level (Moderately Challenging)
- Make it BILINGUAL (Hindi | English)
- Include specific facts, years, numbers
- Use recent/updated information

Generate question on: {random_topic}

Return ONLY valid JSON in this EXACT format (no extra text):
{{
    "question": "हिंदी में प्रश्न | Question in English",
    "options": [
        "हिंदी विकल्प A | English Option A",
        "हिंदी विकल्प B | English Option B",
        "हिंदी विकल्प C | English Option C",
        "हिंदी विकल्प D | English Option D"
    ],
    "correct": 0,
    "explanation": "हिंदी में व्याख्या (तथ्यों के साथ) | Explanation in English (with facts)"
}}

Remember: Include YEAR/DATE in explanation if relevant. Make it FACTUALLY ACCURATE!"""
        
        # Try with maximum randomness
        for attempt in range(10):  # 10 attempts
            try:
                logger.info(f"🤖 AI Generating {subject} question - Attempt {attempt + 1}/10")
                
                # Generate with high temperature for maximum creativity
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=1.5,  # MAXIMUM randomness
                        top_p=0.98,
                        top_k=64,
                        max_output_tokens=1024,
                    )
                )
                
                text = response.text.strip()
                logger.info(f"AI Response received: {text[:100]}...")
                
                # Extract JSON
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()
                
                # Try to find JSON in text
                if "{" in text and "}" in text:
                    json_start = text.find("{")
                    json_end = text.rfind("}") + 1
                    text = text[json_start:json_end]
                
                data = json.loads(text)
                
                # Validate structure
                required_keys = ["question", "options", "correct", "explanation"]
                if all(k in data for k in required_keys):
                    if isinstance(data["options"], list) and len(data["options"]) == 4:
                        if isinstance(data["correct"], int) and 0 <= data["correct"] <= 3:
                            logger.info(f"✅ Successfully generated {subject} question!")
                            return data
                
                logger.warning(f"⚠️ Invalid structure, retrying...")
                time.sleep(0.3)  # Small delay
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON error: {e}")
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"❌ Error: {e}")
                time.sleep(0.5)
        
        # If all 10 attempts fail, show error message
        logger.error("❌ Failed to generate question after 10 attempts")
        return {
            "question": "⚠️ Unable to generate question. Please try again.",
            "options": ["Try Again", "Try Again", "Try Again", "Try Again"],
            "correct": 0,
            "explanation": "AI couldn't generate a question. Click 'Next Question' to try again."
        }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    keyboard = [
        [InlineKeyboardButton("📚 English", callback_data='subject_English')],
        [InlineKeyboardButton("🌍 GK (General Knowledge)", callback_data='subject_GK')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """🎓 *Welcome to SSC CGL/CHSL Test Bot!*

🤖 100% AI-Powered Questions by Gemini!

✨ Features:
• Every question generated fresh by AI
• Real SSC exam difficulty
• Never repeating questions
• Detailed explanations

Select a subject to start:"""
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

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
            [InlineKeyboardButton("🌍 GK (General Knowledge)", callback_data='subject_GK')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if user_id in user_sessions:
            score = user_sessions[user_id]['score']
            total = user_sessions[user_id]['total']
            text = f"📊 Your Score: {score}/{total}\n\n🎓 Select a subject to continue:"
        else:
            text = "🎓 Select a subject to start:"
        
        await query.edit_message_text(text, reply_markup=reply_markup)

async def send_question(query, user_id, subject):
    try:
        await query.edit_message_text("⏳ AI is generating a NEW question...\n\n🤖 Gemini is thinking...\n\n⚡ Please wait...")
        
        # Generate 100% AI question
        question_data = QuizGenerator.generate_question(subject, user_id)
        user_sessions[user_id]['current_question'] = question_data
        
        # Create option buttons
        keyboard = []
        options_labels = ['A', 'B', 'C', 'D']
        for i, option in enumerate(question_data['options']):
            keyboard.append([InlineKeyboardButton(f"{options_labels[i]}. {option}", callback_data=f'answer_{i}')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        question_text = f"❓ *Question:*\n\n{question_data['question']}"
        
        await query.edit_message_text(question_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error in send_question: {e}")
        keyboard = [[InlineKeyboardButton("🔄 Try Again", callback_data='next_question')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "❌ Error generating question. Please try again.",
            reply_markup=reply_markup
        )

async def check_answer(query, user_id, selected):
    try:
        if user_id not in user_sessions or 'current_question' not in user_sessions[user_id]:
            await query.edit_message_text("⚠️ Session expired. Please /start again.")
            return
        
        question_data = user_sessions[user_id]['current_question']
        correct_index = question_data['correct']
        user_sessions[user_id]['total'] += 1
        
        options_labels = ['A', 'B', 'C', 'D']
        
        if selected == correct_index:
            user_sessions[user_id]['score'] += 1
            result_text = f"✅ *Correct Answer!*\n\n"
        else:
            result_text = f"❌ *Wrong Answer!*\n\n"
            result_text += f"You selected: *{options_labels[selected]}. {question_data['options'][selected]}*\n\n"
        
        result_text += f"✔️ Correct Answer: *{options_labels[correct_index]}. {question_data['options'][correct_index]}*\n\n"
        result_text += f"💡 *Explanation:*\n{question_data['explanation']}\n\n"
        result_text += f"📊 Score: {user_sessions[user_id]['score']}/{user_sessions[user_id]['total']}"
        
        keyboard = [
            [InlineKeyboardButton("➡️ Next Question", callback_data='next_question')],
            [InlineKeyboardButton("🏠 Back to Menu", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(result_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error in check_answer: {e}")
        await query.edit_message_text("❌ Error processing answer. Please try /start again.")

async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is alive! 100% AI-powered by Gemini!")

def main():
    logger.info("🚀 Starting PURE AI SSC Quiz Bot - 100% Gemini Generated!")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("health", health_check))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("✅ Bot ready! All questions generated by Gemini AI!")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
