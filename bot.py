import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import google.generativeai as genai
import json
import random

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not GEMINI_API_KEY or not TELEGRAM_TOKEN:
    logger.error("❌ Environment variables missing!")
    logger.error("Set TELEGRAM_BOT_TOKEN and GEMINI_API_KEY")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

user_sessions = {}

class QuizGenerator:
    @staticmethod
    def generate_question(subject):
        max_retries = 3
        
        prompts = {
            "English": """Generate 1 SSC CGL/CHSL level English multiple choice question. Focus on: Grammar, Vocabulary, Synonyms, Antonyms, Idioms, Sentence Correction, Fill in the blanks, Error Detection, or Comprehension.

Make it exam-realistic and challenging. Format as JSON:
{
    "question": "Your SSC-level question here",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct": 0,
    "explanation": "Detailed explanation with grammar rules or vocabulary meaning"
}""",
            
            "GK": """Generate 1 SSC CGL/CHSL level General Knowledge question in BILINGUAL format (Hindi + English). 

Topics: Indian History, Geography, Indian Polity, Economics, Science, Current Affairs, Books & Authors, Awards, Sports, Important Dates.

Format EXACTLY as JSON with BILINGUAL text (Hindi | English):
{
    "question": "हिंदी में सवाल | Question in English",
    "options": [
        "हिंदी विकल्प A | English Option A",
        "हिंदी विकल्प B | English Option B",
        "हिंदी विकल्प C | English Option C",
        "हिंदी विकल्प D | English Option D"
    ],
    "correct": 0,
    "explanation": "हिंदी में व्याख्या | Explanation in English"
}

Make it SSC exam level - factual, precise, and educational."""
        }
        
        for attempt in range(max_retries):
            try:
                response = model.generate_content(prompts.get(subject, prompts["GK"]))
                text = response.text.strip()
                
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()
                
                data = json.loads(text)
                
                if all(k in data for k in ["question", "options", "correct", "explanation"]):
                    if isinstance(data["options"], list) and len(data["options"]) == 4:
                        if isinstance(data["correct"], int) and 0 <= data["correct"] <= 3:
                            logger.info(f"✅ Generated {subject} question")
                            return data
                
                logger.warning(f"Invalid structure on attempt {attempt + 1}")
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error on attempt {attempt + 1}: {e}")
            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}: {e}")
        
        logger.warning("Using fallback question")
        if subject == "GK":
            fallback = [
                {
                    "question": "भारत के प्रथम राष्ट्रपति कौन थे? | Who was the first President of India?",
                    "options": ["डॉ. राजेंद्र प्रसाद | Dr. Rajendra Prasad", "सर्वपल्ली राधाकृष्णन | Sarvepalli Radhakrishnan", "जाकिर हुसैन | Zakir Husain", "वी.वी. गिरि | V.V. Giri"],
                    "correct": 0,
                    "explanation": "डॉ. राजेंद्र प्रसाद भारत के प्रथम राष्ट्रपति थे। उन्होंने 1950 से 1962 तक सेवा की। | Dr. Rajendra Prasad was the first President of India. He served from 1950 to 1962."
                },
                {
                    "question": "भारत की राजधानी क्या है? | What is the capital of India?",
                    "options": ["मुंबई | Mumbai", "नई दिल्ली | New Delhi", "कोलकाता | Kolkata", "चेन्नई | Chennai"],
                    "correct": 1,
                    "explanation": "नई दिल्ली भारत की राजधानी है और यह दिल्ली केंद्र शासित प्रदेश में स्थित है। | New Delhi is the capital of India and is located in the National Capital Territory of Delhi."
                },
                {
                    "question": "भारतीय संविधान कब लागू हुआ? | When did the Indian Constitution come into effect?",
                    "options": ["15 अगस्त 1947 | 15 August 1947", "26 जनवरी 1950 | 26 January 1950", "26 नवंबर 1949 | 26 November 1949", "2 अक्टूबर 1947 | 2 October 1947"],
                    "correct": 1,
                    "explanation": "भारतीय संविधान 26 जनवरी 1950 को लागू हुआ था। इसी दिन को हम गणतंत्र दिवस के रूप में मनाते हैं। | The Indian Constitution came into effect on 26 January 1950. We celebrate this day as Republic Day."
                }
            ]
            return random.choice(fallback)
        else:
            fallback = [
                {
                    "question": "Choose the correctly spelled word:",
                    "options": ["Occassion", "Occasion", "Ocassion", "Ocasion"],
                    "correct": 1,
                    "explanation": "'Occasion' is the correct spelling with double 'c' and single 's'. It means a particular event or time."
                },
                {
                    "question": "Find the synonym of 'ABUNDANT':",
                    "options": ["Scarce", "Plentiful", "Rare", "Limited"],
                    "correct": 1,
                    "explanation": "'Plentiful' means existing in large quantities, which is the same as 'Abundant'."
                },
                {
                    "question": "Choose the correct form: He _____ to school every day.",
                    "options": ["go", "goes", "going", "gone"],
                    "correct": 1,
                    "explanation": "'Goes' is correct because 'He' is third person singular present tense."
                }
            ]
            return random.choice(fallback)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📚 English", callback_data='subject_English')],
        [InlineKeyboardButton("🌍 GK (General Knowledge)", callback_data='subject_GK')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """🎓 *Welcome to SSC CGL/CHSL Test Bot!*

Make learning easy with AI-powered questions!

✨ Features:
• Unlimited unique questions
• Exam-level difficulty
• Detailed explanations
• Score tracking

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
            text = "�� Select a subject to start:"
        
        await query.edit_message_text(text, reply_markup=reply_markup)

async def send_question(query, user_id, subject):
    await query.edit_message_text("⏳ Generating SSC-level question... Please wait...")
    
    question_data = QuizGenerator.generate_question(subject)
    user_sessions[user_id]['current_question'] = question_data
    
    keyboard = []
    options_labels = ['A', 'B', 'C', 'D']
    for i, option in enumerate(question_data['options']):
        keyboard.append([InlineKeyboardButton(f"{options_labels[i]}. {option}", callback_data=f'answer_{i}')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    question_text = f"❓ *Question:*\n\n{question_data['question']}"
    
    await query.edit_message_text(question_text, reply_markup=reply_markup, parse_mode='Markdown')

async def check_answer(query, user_id, selected):
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

async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is alive and running!")

def main():
    logger.info("🚀 Starting SSC Quiz Bot...")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("health", health_check))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("✅ Bot is ready and listening!")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
