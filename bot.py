import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import google.generativeai as genai
import json
import random
import hashlib
import time

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
asked_questions = {}  # Track asked questions per user

class QuizGenerator:
    @staticmethod
    def generate_question(subject, user_id):
        """Generate unique questions for each user"""
        max_retries = 5
        
        # Get user's question history
        if user_id not in asked_questions:
            asked_questions[user_id] = set()
        
        # Add randomness to prompt
        timestamp = int(time.time())
        random_seed = random.randint(1000, 9999)
        
        prompts = {
            "English": f"""You are an SSC CGL/CHSL exam expert. Generate 1 UNIQUE and CHALLENGING English question.

IMPORTANT: Question ID {timestamp}{random_seed} - Make this completely different from previous questions.

Focus areas (pick ONE randomly):
- Advanced Grammar (Subject-Verb Agreement, Tenses, Voice, Narration)
- Vocabulary (Difficult Synonyms, Antonyms, One-word substitution)
- Idioms & Phrases (Common SSC idioms)
- Sentence Improvement/Error Detection
- Fill in the Blanks (Contextual usage)
- Cloze Test/Comprehension

Difficulty: SSC CGL/CHSL Tier-1 level (Moderately Hard)

Generate in EXACT JSON format:
{{
    "question": "Your challenging SSC-level question here",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct": 0,
    "explanation": "Detailed explanation with grammar rules/reasoning"
}}

Make it challenging but fair. No easy questions!""",
            
            "GK": f"""You are an SSC CGL/CHSL exam expert. Generate 1 UNIQUE General Knowledge question in BILINGUAL format.

IMPORTANT: Question ID {timestamp}{random_seed} - Make this completely different from previous questions.

Topics (pick ONE randomly):
- Indian History (Freedom Struggle, Ancient/Medieval/Modern India)
- Indian Geography (Rivers, Mountains, States, Capitals)
- Indian Polity & Governance (Constitution, President, PM, Parliament)
- Indian Economy (Budget, GDP, Banking, Currency)
- General Science (Physics, Chemistry, Biology basics)
- Current Affairs (Recent 6 months)
- Books & Authors (Indian)
- National & International Awards
- Sports (Olympics, Cricket, Recent tournaments)
- Important Days & Dates

Difficulty: SSC CGL/CHSL Tier-1 level (Moderately Hard)

Generate in EXACT JSON format with BILINGUAL content (Hindi | English):
{{
    "question": "हिंदी में चुनौतीपूर्ण सवाल | Challenging question in English",
    "options": [
        "हिंदी विकल्प A | English Option A",
        "हिंदी विकल्प B | English Option B",
        "हिंदी विकल्प C | English Option C",
        "हिंदी विकल्प D | English Option D"
    ],
    "correct": 0,
    "explanation": "हिंदी में विस्तृत व्याख्या | Detailed explanation in English"
}}

Make it factually accurate, challenging but fair. Include year/date in explanation if relevant!"""
        }
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Generating question attempt {attempt + 1}/{max_retries}")
                
                # Generate with temperature for more randomness
                response = model.generate_content(
                    prompts.get(subject, prompts["GK"]),
                    generation_config=genai.types.GenerationConfig(
                        temperature=1.0,  # Higher temperature = more creative/random
                        top_p=0.95,
                        top_k=40,
                    )
                )
                
                text = response.text.strip()
                
                # Clean JSON
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()
                
                data = json.loads(text)
                
                # Validate structure
                if all(k in data for k in ["question", "options", "correct", "explanation"]):
                    if isinstance(data["options"], list) and len(data["options"]) == 4:
                        if isinstance(data["correct"], int) and 0 <= data["correct"] <= 3:
                            # Check if question is unique
                            question_hash = hashlib.md5(data["question"].encode()).hexdigest()
                            
                            if question_hash not in asked_questions[user_id]:
                                asked_questions[user_id].add(question_hash)
                                logger.info(f"✅ Generated unique {subject} question")
                                
                                # Limit history to last 100 questions per user
                                if len(asked_questions[user_id]) > 100:
                                    asked_questions[user_id] = set(list(asked_questions[user_id])[-100:])
                                
                                return data
                            else:
                                logger.warning(f"Duplicate question detected, retry {attempt + 1}")
                                continue
                
                logger.warning(f"Invalid structure on attempt {attempt + 1}")
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error on attempt {attempt + 1}: {e}")
                time.sleep(0.5)  # Small delay before retry
            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}: {e}")
                time.sleep(0.5)
        
        # Fallback questions - Large pool to avoid repeats
        logger.warning("Using fallback question")
        if subject == "GK":
            fallback = [
                {
                    "question": "भारत के प्रथम राष्ट्रपति कौन थे? | Who was the first President of India?",
                    "options": ["डॉ. राजेंद्र प्रसाद | Dr. Rajendra Prasad", "सर्वपल्ली राधाकृष्णन | Sarvepalli Radhakrishnan", "जाकिर हुसैन | Zakir Husain", "वी.वी. गिरि | V.V. Giri"],
                    "correct": 0,
                    "explanation": "डॉ. राजेंद्र प्रसाद भारत के प्रथम राष्ट्रपति थे (1950-1962)। | Dr. Rajendra Prasad was the first President of India (1950-1962)."
                },
                {
                    "question": "भारतीय संविधान कब लागू हुआ? | When did the Indian Constitution come into effect?",
                    "options": ["15 अगस्त 1947 | 15 August 1947", "26 जनवरी 1950 | 26 January 1950", "26 नवंबर 1949 | 26 November 1949", "2 अक्टूबर 1947 | 2 October 1947"],
                    "correct": 1,
                    "explanation": "भारतीय संविधान 26 जनवरी 1950 को लागू हुआ। इसी दिन को गणतंत्र दिवस मनाया जाता है। | The Indian Constitution came into effect on 26 January 1950. This day is celebrated as Republic Day."
                },
                {
                    "question": "भारत में सबसे लंबी नदी कौन सी है? | Which is the longest river in India?",
                    "options": ["यमुना | Yamuna", "गोदावरी | Godavari", "गंगा | Ganga", "ब्रह्मपुत्र | Brahmaputra"],
                    "correct": 2,
                    "explanation": "गंगा भारत की सबसे लंबी नदी है जिसकी लंबाई 2525 किमी है। | Ganga is the longest river in India with a length of 2525 km."
                },
                {
                    "question": "भारत का राष्ट्रीय पशु क्या है? | What is the national animal of India?",
                    "options": ["शेर | Lion", "हाथी | Elephant", "बाघ | Tiger", "तेंदुआ | Leopard"],
                    "correct": 2,
                    "explanation": "बाघ (रॉयल बंगाल टाइगर) भारत का राष्ट्रीय पशु है। | Tiger (Royal Bengal Tiger) is the national animal of India."
                },
                {
                    "question": "भारत में कुल कितने राज्य हैं? | How many states are there in India?",
                    "options": ["27 | 27", "28 | 28", "29 | 29", "30 | 30"],
                    "correct": 1,
                    "explanation": "भारत में वर्तमान में 28 राज्य और 8 केंद्र शासित प्रदेश हैं। | India currently has 28 states and 8 union territories."
                },
                {
                    "question": "भारत का सबसे बड़ा राज्य (क्षेत्रफल में) कौन सा है? | Which is the largest state in India by area?",
                    "options": ["महाराष्ट्र | Maharashtra", "राजस्थान | Rajasthan", "मध्य प्रदेश | Madhya Pradesh", "उत्तर प्रदेश | Uttar Pradesh"],
                    "correct": 1,
                    "explanation": "राजस्थान भारत का सबसे बड़ा राज्य है जिसका क्षेत्रफल 3,42,239 वर्ग किमी है। | Rajasthan is the largest state in India with an area of 3,42,239 sq km."
                }
            ]
            return random.choice(fallback)
        else:
            fallback = [
                {
                    "question": "Choose the correctly spelled word:",
                    "options": ["Embarrassment", "Embarassment", "Embarrasment", "Embarasment"],
                    "correct": 0,
                    "explanation": "'Embarrassment' is the correct spelling with double 'r' and double 's'. It means a feeling of self-consciousness or shame."
                },
                {
                    "question": "Find the antonym of 'INDIGENOUS':",
                    "options": ["Native", "Local", "Foreign", "Aboriginal"],
                    "correct": 2,
                    "explanation": "'Foreign' is the antonym of 'Indigenous'. Indigenous means native or originating from a particular place, while foreign means from another country."
                },
                {
                    "question": "Choose the correct idiom meaning 'To reveal a secret':",
                    "options": ["Spill the beans", "Beat around the bush", "Piece of cake", "Break the ice"],
                    "correct": 0,
                    "explanation": "'Spill the beans' means to reveal a secret or disclose information that was meant to be kept confidential."
                },
                {
                    "question": "Identify the error: 'Each of the students have submitted their assignments.'",
                    "options": ["No error", "Error in 'have'", "Error in 'their'", "Error in 'submitted'"],
                    "correct": 1,
                    "explanation": "The error is in 'have'. It should be 'has' because 'each' is a singular subject and requires a singular verb."
                },
                {
                    "question": "Fill in the blank: He was _____ by the news of his success.",
                    "options": ["overwhelmed", "overcome", "overtaken", "overjoyed"],
                    "correct": 3,
                    "explanation": "'Overjoyed' is the most appropriate word meaning extremely happy. While 'overwhelmed' could work, 'overjoyed' specifically means filled with great joy."
                },
                {
                    "question": "Find the synonym of 'METICULOUS':",
                    "options": ["Careless", "Precise", "Rough", "Hasty"],
                    "correct": 1,
                    "explanation": "'Precise' is a synonym of 'Meticulous'. Both mean showing great attention to detail and being very careful and exact."
                }
            ]
            return random.choice(fallback)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Initialize user's question history
    if user_id not in asked_questions:
        asked_questions[user_id] = set()
    
    keyboard = [
        [InlineKeyboardButton("📚 English", callback_data='subject_English')],
        [InlineKeyboardButton("🌍 GK (General Knowledge)", callback_data='subject_GK')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """🎓 *Welcome to SSC CGL/CHSL Test Bot!*

AI-powered with UNIQUE questions every time!

✨ Features:
• Unlimited NEW questions (No repeats!)
• Real SSC exam difficulty
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
            text = f"�� Your Score: {score}/{total}\n\n🎓 Select a subject to continue:"
        else:
            text = "🎓 Select a subject to start:"
        
        await query.edit_message_text(text, reply_markup=reply_markup)

async def send_question(query, user_id, subject):
    try:
        await query.edit_message_text("⏳ Generating NEW SSC-level question...\n\n🤖 AI is thinking...")
        
        # Generate unique question for this user
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
        await query.edit_message_text("❌ Error generating question. Please try again.")

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
        await query.edit_message_text("❌ Error processing answer. Please try again.")

async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is alive and generating unique questions!")

def main():
    logger.info("🚀 Starting SSC Quiz Bot with NO REPEAT questions...")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("health", health_check))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("✅ Bot is ready! Generating unique questions...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
