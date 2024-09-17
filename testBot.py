from telegram import Update , Bot 
from telegram import Update,  CallbackQuery, Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler,CallbackQueryHandler, CallbackContext, MessageHandler, filters
from telegram import Update, ChatPermissions
from telegram.ext import Application,CommandHandler, CallbackContext , MessageHandler , filters , PollAnswerHandler
import random
from telegram import Update, Poll
from telegram import Update, InputMediaPhoto
import datetime
from telegram import CallbackQuery
import logging  
from telegram.ext import Updater
import requests
from collections import defaultdict
import os
from telegram import InputFile , InputMediaAnimation
import sqlite3
from google.cloud import vision_v1 as vision
from google.oauth2 import service_account
import io
import os
import time
import datetime
import random



# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)




async def info(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    await update.message.reply_text(
        f'User Info:\n'
        f'Name: {user.full_name}\n'
        f'Username: @{user.username}\n'
        f'User ID: {user.id}'
    )

# Database setup
def setup_database():
    conn = sqlite3.connect('chat_activity.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            user_id INTEGER,
            username TEXT,
            chat_id INTEGER,
            message_date DATE,
            PRIMARY KEY (user_id, chat_id, message_date)
        )
    ''')
    conn.commit()
    conn.close()

def log_message(user_id, username, chat_id, message_date):
    conn = sqlite3.connect('chat_activity.db')
    c = conn.cursor()
    c.execute('''
        INSERT OR IGNORE INTO messages (user_id, username, chat_id, message_date)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, chat_id, message_date))
    conn.commit()
    conn.close()


def get_user_stats(user_id, chat_id):
    conn = sqlite3.connect('chat_activity.db')
    c = conn.cursor()

    # Total messages globally
    c.execute('''
        SELECT COUNT(*) FROM messages
        WHERE user_id = ?
    ''', (user_id,))
    total_msgs = c.fetchone()[0]

    # Messages in the current group
    c.execute('''
        SELECT COUNT(*) FROM messages
        WHERE user_id = ? AND chat_id = ?
    ''', (user_id, chat_id))
    group_msgs = c.fetchone()[0]

    conn.close()
    return total_msgs, group_msgs

async def profile(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    user_id = user.id
    chat_id = update.message.chat.id

    total_msgs, group_msgs = get_user_stats(user_id, chat_id)

    # Fetch user profile photos
    photos = await context.bot.get_user_profile_photos(user_id)
    if photos.photos:
        photo_file_id = photos.photos[0][-1].file_id
        photo = await context.bot.get_file(photo_file_id)
        profile_pic_url = photo.file_path
    else:
        profile_pic_url = None

    profile_message = (
        f"*Profile Information:*\n\n"
        f"*Name:* {user.full_name}\n"
        f"*Username:* @{user.username}\n"
        f"*User ID:* {user.id}\n\n"
        f"*Total Messages Globally:* {total_msgs}\n"
        f"*Messages in This Group:* {group_msgs}\n"
    )
    
    if profile_pic_url:
        await update.message.reply_photo(photo=profile_pic_url, caption=profile_message, parse_mode='Markdown')
    else:
        await update.message.reply_text(profile_message, parse_mode='Markdown')



def get_ranking(period):
    conn = sqlite3.connect('chat_activity.db')
    c = conn.cursor()
    
    if period == 'today':
        start_date = datetime.datetime.now().date()
    elif period == 'week':
        start_date = datetime.datetime.now().date() - datetime.timedelta(days=7)
    elif period == 'total':
        start_date = '0000-01-01'  # No limit for total
    else:
        return []

    c.execute('''
        SELECT username, COUNT(*) as message_count
        FROM messages
        WHERE message_date >= ?
        GROUP BY user_id
        ORDER BY message_count DESC
    ''', (start_date,))
    
    rankings = c.fetchall()
    conn.close()
    return rankings


async def log_chat(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    chat_id = update.message.chat.id
    message_date = update.message.date.date()
    log_message(user_id, username, chat_id, message_date)

async def rankings(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Today", callback_data='today')],
        [InlineKeyboardButton("This Week", callback_data='week')],
        [InlineKeyboardButton("Total", callback_data='total')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Select a period to view rankings:', reply_markup=reply_markup)

async def handle_ranking_query(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    period = query.data
    rankings = get_ranking(period)
    
    if not rankings:
        await query.message.reply_text(f'No data available for the period: {period}.')
        return

    ranking_message = f'User Rankings ({period.capitalize()}):\n'
    for username, message_count in rankings:
        ranking_message += f'{username}: {message_count} messages\n'

    await query.message.edit_text(ranking_message)


setup_database()


# Define the choices
CHOICES = ['rock', 'paper', 'scissors']

# Function to handle the /play command
async def play(update: Update, context: CallbackContext) -> None:
    user_choice = ' '.join(context.args).lower()
    
    if user_choice not in CHOICES:
        await update.message.reply_text("Please choose one of the following: rock, paper, or scissors. \n Use /play before your choices (for ex: /play rock)")
        return
    
    # Bot's choice
    bot_choice = random.choice(CHOICES)
    
    # Determine the result
    if user_choice == bot_choice:
        result = "It's a draw!"
    elif (user_choice == 'rock' and bot_choice == 'scissors') or \
         (user_choice == 'scissors' and bot_choice == 'paper') or \
         (user_choice == 'paper' and bot_choice == 'rock'):
        result = "You win!"
    else:
        result = "You lose!"
    
    # Send the result to the user
    response = f"You chose {user_choice}.\nI chose {bot_choice}.\n{result}"
    await update.message.reply_text(response)


# Define the story
story = {
    'start': {
        'text': "You find yourself at the entrance of a dark forest. Do you wish to enter or leave?",
        'choices': {
            'Enter': 'enter_forest',
            'Leave': 'leave_forest'
        }
    },
    'enter_forest': {
        'text': "You enter the forest and see two paths: one to the left and one to the right. Which path do you choose?",
        'choices': {
            'Left': 'left_path',
            'Right': 'right_path'
        }
    },
    'leave_forest': {
        'text': "You decide to leave the forest. You are now back where you started. The adventure ends.",
        'choices': {}
    },
    'left_path': {
        'text': "The left path leads to a beautiful clearing with a stream. You can relax here, search for herbs, or continue your adventure.",
        'choices': {
            'Relax': 'end',
            'Search for Herbs': 'find_herbs',
            'Continue': 'continue_adventure'
        }
    },
    'right_path': {
        'text': "The right path leads to a dark cave. Do you wish to enter or turn back?",
        'choices': {
            'Enter': 'enter_cave',
            'Turn Back': 'enter_forest'
        }
    },
    'enter_cave': {
        'text': "You enter the cave and find a hidden treasure chest. Do you wish to open it or leave it alone?",
        'choices': {
            'Open the Chest': 'treasure_chest',
            'Leave It Alone': 'end'
        }
    },
    'find_herbs': {
        'text': "You find some rare herbs in the clearing. As you collect them, you hear a rustling sound. Do you investigate or ignore it?",
        'choices': {
            'Investigate': 'rustling_sound',
            'Ignore': 'end'
        }
    },
    'rustling_sound': {
        'text': "You investigate the sound and discover a friendly forest sprite. The sprite offers you a magical amulet. Do you accept it or decline?",
        'choices': {
            'Accept': 'amulet',
            'Decline': 'end'
        }
    },
    'amulet': {
        'text': "You accept the amulet and gain a new magical power. Congratulations, you are now a powerful mage! The adventure ends.",
        'choices': {}
    },
    'treasure_chest': {
        'text': "You open the chest and find a pile of gold and a mysterious map. Do you take the gold or study the map?",
        'choices': {
            'Take the Gold': 'gold',
            'Study the Map': 'mysterious_map'
        }
    },
    'gold': {
        'text': "You take the gold and leave the cave. Your adventure ends with newfound riches.",
        'choices': {}
    },
    'mysterious_map': {
        'text': "You study the map and find it leads to a hidden ancient ruin. Do you follow the map or leave the cave?",
        'choices': {
            'Follow the Map': 'ancient_ruin',
            'Leave the Cave': 'end'
        }
    },
    'ancient_ruin': {
        'text': "You follow the map to the ancient ruin and discover an ancient artifact. Congratulations, you have made a great archaeological discovery!",
        'choices': {}
    },
    'continue_adventure': {
        'text': "You continue your adventure and encounter many challenges and wonders. The adventure is endless and full of surprises.",
        'choices': {}
    },
    'end': {
        'text': "You decide to end your adventure here. Thanks for playing!",
        'choices': {}
    }
}

# Define the /play2 command handler
async def play_game(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    
    # Initialize the game state for the user
    context.chat_data['story_state'] = 'start'
    context.chat_data['user_id'] = user_id
    
    # Send the starting message
    start_text = story['start']['text']
    choices = '\n'.join([f"/{choice}" for choice in story['start']['choices']])
    await update.message.reply_text(f"{start_text}\n\nChoices:\n{choices}")

# Define the message handler for user choices
async def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    user_message = update.message.text
    
    if 'story_state' not in context.chat_data or context.chat_data['user_id'] != user_id:
        return
    
    current_state = context.chat_data['story_state']
    
    # Handle choices based on the current state
    if user_message in story[current_state]['choices']:
        next_state = story[current_state]['choices'][user_message]
        context.chat_data['story_state'] = next_state
        
        next_text = story[next_state]['text']
        choices = '\n'.join([f"/{choice}" for choice in story[next_state]['choices']])
        await update.message.reply_text(f"{next_text}\n\nChoices:\n{choices}")
    else:
        await update.message.reply_text("Invalid choice. Please select a valid option.")


app = Application.builder().token("7419788460:AAFyXg-ysiqTXg7BkNh769Rc-2mvr_ZJeK0").build()


def init_db():
    conn = sqlite3.connect('user_stats.db')
    cursor = conn.cursor()
    
    # Create table for user messages
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_messages (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        message_count INTEGER
    )
    ''')
    
    conn.commit()
    conn.close()

# Call this function once to initialize the database
init_db()




# Function to update or insert user message count
def update_user_stats(user_id: int, username: str):
    conn = sqlite3.connect('user_stats.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM user_messages WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result:
        cursor.execute('UPDATE user_messages SET message_count = message_count + 1 WHERE user_id = ?', (user_id,))
    else:
        cursor.execute('INSERT INTO user_messages (user_id, username, message_count) VALUES (?, ?, ?)', 
                       (user_id, username, 1))
    
    conn.commit()
    conn.close()


# Command to create a poll
async def create_poll(update: Update, context: CallbackContext) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /poll <question> <option1> <option2> ...")
        return

    question = context.args[0]
    options = context.args[1:]

    if len(options) < 2:
        await update.message.reply_text("Please provide at least two options for the poll.")
        return

    # Send the poll to the chat
    await update.message.reply_poll(
        question=question,
        options=options,
        is_anonymous=False,  # Poll is not anonymous
        allows_multiple_answers=False  # Users can choose only one option
    )


# Function to handle poll answers
async def handle_poll_answer(update: Update, context: CallbackContext) -> None:
    poll_answer = update.poll_answer
    user_id = poll_answer.user.id
    poll_id = poll_answer.poll_id
    option_ids = poll_answer.option_ids

    # You can perform actions based on poll responses here
    print(f"User {user_id} voted in poll {poll_id} with options {option_ids}")




# Function to handle incoming messages and update stats
async def handle_message(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    update_user_stats(user.id, user.username)

# Function to handle /userstats command and display top users
async def user_stats(update: Update, context: CallbackContext) -> None:
    conn = sqlite3.connect('user_stats.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT username, message_count FROM user_messages ORDER BY message_count DESC LIMIT 10')
    top_users = cursor.fetchall()
    
    stats_text = "Top Users:\n"
    for username, count in top_users:
        stats_text += f"{username}: {count} messages\n"
    
    conn.close()
    
    await update.message.reply_text(stats_text)







logging.basicConfig(level=logging.INFO)  


async def harsha_fact(update: Update, context):
    if "Yuta" or 'Harsha' in update.message.text.lower():
        await update.message.reply_text("Uk what Yuta is a gay")


# Welcome message command handler
async def welcome(update: Update, context: CallbackContext) -> None:
    if update.message.new_chat_members:
        # GIF to be sent as the welcome message
        gif_file_id = 'https://c.tenor.com/rvYiscAk_kAAAAAC/anime-welcome.gif'

        # Create inline keyboard buttons for group rules and FAQ commands
        keyboard = [
            [InlineKeyboardButton("Group Rules", callback_data='group_rules')],
            [InlineKeyboardButton("FAQ", callback_data='faq')],
            [InlineKeyboardButton("Help", callback_data='help')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send the welcome message with the GIF and inline keyboard
        await update.message.reply_animation(animation=gif_file_id, caption="Welcome to the group! Please check the buttons below for group rules, FAQ, and help.", reply_markup=reply_markup)




async def rules(update: Update, context: CallbackContext) -> None:
    rules_text = (
        "Welcome to the group! Here are the rules:\n"
        "1. Be respectful to everyone.\n"
        "2. No spamming or flooding the chat.\n"
        "3. No offensive language or harassment.\n"
        "4. Follow the group's theme and guidelines.\n"
        "5. Have fun and be supportive!"
    )
    await update.message.reply_text(rules_text)

async def faq(update: Update, context: CallbackContext) -> None:
    faq_text = (
        "Frequently Asked Questions:\n"
        "Q: How do I change my profile picture?\n"
        "A: Go to your profile settings and choose a new picture.\n"
        "Q: How do I report an issue?\n"
        "A: Contact the group admin with a detailed description of the issue.\n"
        "Q: Can I invite friends to the group?\n"
        "A: Yes, but make sure they follow the group rules."
    )
    await update.message.reply_text(faq_text)




# Function to add a sticker to the bot's shared sticker pack
async def kang(update: Update, context: CallbackContext) -> None:
    if update.message.reply_to_message and update.message.reply_to_message.sticker:
        user = update.message.from_user
        sticker = update.message.reply_to_message.sticker
        sticker_file_id = sticker.file_id  # Get the sticker file ID

        # Define a shared sticker pack name for the bot (fixed pack)
        sticker_pack_name = f"SharedPack_by_{context.bot.username}"
        sticker_pack_title = f"{context.bot.username}'s Shared Sticker Pack"

        # Prepare the emojis for the sticker
        emojis = sticker.emoji or "😎"  # Default emoji if none

        file_name = None  # Initialize to None
        try:
            # Set a longer timeout for the download process
            new_sticker_file = await asyncio.wait_for(context.bot.get_file(sticker_file_id), timeout=30)

            # Download the sticker and save it locally
            file_name = f"sticker_{sticker_file_id}.webp"
            await new_sticker_file.download(file_name)

            # Try to add the sticker to the existing shared pack
            try:
                with open(file_name, 'rb') as sticker_file:
                    await context.bot.add_sticker_to_set(
                        user_id=user.id,  # Use the current user's ID for the action
                        name=sticker_pack_name,  # The shared sticker pack
                        png_sticker=sticker_file,
                        emojis=emojis
                    )
                await update.message.reply_text(
                    f"Sticker added to the shared pack [here](t.me/addstickers/{sticker_pack_name})", 
                    parse_mode="Markdown"
                )

            except Exception as e:
                # If the sticker pack doesn't exist, create a new shared one
                if "STICKERSET_INVALID" in str(e):
                    with open(file_name, 'rb') as sticker_file:
                        await context.bot.create_new_sticker_set(
                            user_id=user.id,  # Use the current user's ID for the action
                            name=sticker_pack_name,
                            title=sticker_pack_title,
                            png_sticker=sticker_file,
                            emojis=emojis
                        )
                    await update.message.reply_text(
                        f"Created a new shared pack [here](t.me/addstickers/{sticker_pack_name})", 
                        parse_mode="Markdown"
                    )
                else:
                    raise e

        except asyncio.TimeoutError:
            await update.message.reply_text("Failed to download the sticker. Operation timed out.")
        except Exception as e:
            await update.message.reply_text(f"Failed to process the sticker: {e}")
            print(f"Error: {e}")

        finally:
            # Clean up by removing the downloaded file only if it exists
            if file_name and os.path.exists(file_name):
                os.remove(file_name)

    else:
        await update.message.reply_text("Please reply to a sticker with the /kang command.")



# Expand the truth questions list with more questions
truth_questions = [
    "What’s the biggest lie you’ve ever told?",
    "What is your biggest fear?",
    "What is your most embarrassing memory?",
    "Have you ever cheated in a game or competition?",
    "Who was your first crush?",
    "What is the one thing you regret doing in life?",
    "Have you ever lied to get out of trouble?",
    "What’s a secret you’ve never told anyone?",
    "What’s your biggest insecurity?",
    "What is your worst habit?",
    "Have you ever pretended to like a gift you actually hated?",
    "What is something you’ve done that you’re not proud of?",
    "Have you ever been in love?",
    "What’s the most childish thing you still do?",
    "Who is the last person you stalked on social media?",
    "What is something you’re afraid of that no one knows about?",
    "If you could change one thing about yourself, what would it be?",
    "Have you ever broken the law?",
    "What’s the most embarrassing thing you’ve done in front of someone you like?",
    "What’s the most awkward date you’ve ever been on?",
    "Have you ever lied to a friend?",
    "What’s the worst rumor you’ve heard about yourself?",
    "If you could date any celebrity, who would it be?",
    "What is something you’ve never told your parents?",
    "What is the most embarrassing thing in your search history?",
    "What’s the weirdest dream you’ve ever had?",
    "What’s the most awkward text you’ve ever sent by accident?",
    "What’s the longest time you’ve gone without showering?",
    "If you had to delete one app from your phone, what would it be?",
    "Who do you secretly envy?",
    "If you could switch lives with someone for a day, who would it be?",
    "Have you ever let someone else take the blame for something you did?",
    "Have you ever had a crush on a friend’s significant other?",
    "What is the most awkward moment you’ve had with a crush?",
    "Have you ever eavesdropped on someone?",
    "If you could be invisible for a day, what would you do?",
    "What’s the most embarrassing thing you’ve ever worn?",
    "Have you ever pretended to be sick to get out of something?",
    "What’s the most expensive thing you’ve stolen?",
    "If you had to marry one person in this room, who would it be?",
    "What’s the weirdest thing you do when you’re alone?",
    "What’s something you’ve done that you would never want your parents to know?",
    "Have you ever been caught in a lie?",
    "What’s the meanest thing you’ve ever said to someone?",
    "What’s something silly that you’re still afraid of?",
    "Have you ever snuck out of the house?"
]

async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Add me to your group", url='https://t.me/Yuki4747_bot?startgroup=true')],
        [InlineKeyboardButton("Support", url='https://t.me/Yuta47474')],
        [InlineKeyboardButton("Help", callback_data='help')],
        [InlineKeyboardButton("Commands", callback_data='commands')]
    ]
    
       
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    start_text = (
        "Hello! I'm Yuki, your friendly bot. \n Effortlessly manage your group with our all-in-one bot—your personal assistant for moderation, organization, and more"
    )
    await update.message.reply_text(start_text, reply_markup=reply_markup)

async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query_data = query.data

    if query.data == 'group_rules':
        await query.message.reply_text("Welcome to the group! Here are the rules:\n"
        "1. Be respectful to everyone.\n"
        "2. No spamming or flooding the chat.\n"
        "3. No offensive language or harassment.\n"
        "4. Follow the group's theme and guidelines.\n"
        "5. Have fun and be supportive!")

    elif query.data == 'faq':
        await query.message.reply_text("Frequently Asked Questions:\n"
        "Q: How do I change my profile picture?\n"
        "A: Go to your profile settings and choose a new picture.\n"
        "Q: How do I report an issue?\n"
        "A: Contact the group admin with a detailed description of the issue.\n"
        "Q: Can I invite friends to the group?\n"
        "A: Yes, but make sure they follow the group rules.")


    
    if query_data == 'help':
        await query.answer()
        await query.message.reply_text("Here are the commands you can use:\n/help - Show this help message\n/start - Start the bot")
    elif query_data == 'commands':
        await query.answer()
        await query.message.reply_text("Here are the commands you can use:\n/start - Start the bot\n/help - Show help information")
    


async def help_command(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Start", callback_data='start')],
        [InlineKeyboardButton("Help", callback_data='help')],
        # Add more buttons if needed
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    help_text = (
        "Here are the commands you can use:\n"
        "\n/start - Greet the bot\n"
        "/help - Show this help message\n"
        "/afk - Set your status as AFK\n"
        "/truth - Get a truth question\n"
        "/dare - Get a dare challenge\n"
        "/brb - Let others know you're away for a bit\n"
        "/love - Find out who I love\n"
        "/quotes - Get a random inspirational quote\n"
        "/couples - Get a random couple\n"
        "/favorite_anime - know about yuki's favourite anime\n" 

        "\nHere are the management commands you can use:\n"
        "\n/promote <username> - Promote a member to admin\n"
        "/ban <username> - Ban a member from the group\n"
        "/mute <username> - Mute a member\n"
        "/unmute <username> - Unmute a member\n"
        "/announce <message> - Send an announcement to the group"
    )
    await update.message.reply_text(help_text, reply_markup=reply_markup)

async def afk(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Doggy's stay away from the group")

async def truth(update: Update, context: CallbackContext) -> None:
    # Randomly select a truth question from the list
    question = random.choice(truth_questions)
    await update.message.reply_text(f"Truth: {question}")

#administrative commands
# Promote a user to admin
async def promote(update: Update, context: CallbackContext) -> None:
    if not context.args:
        await update.message.reply_text("Please specify the username to promote.")
        return
    
    username = context.args[0]
    chat_id = update.effective_chat.id
    
    try:
        member = await context.bot.get_chat_member(chat_id, username)
        if member.status in ['administrator', 'creator']:
            await update.message.reply_text(f"{username} is already an admin.")
        else:
            await context.bot.promote_chat_member(
                chat_id, member.user.id,
                can_manage_chat=True,
                can_delete_messages=True,
                can_manage_video_chats=True,
                can_restrict_members=True,
                can_pin_messages=True,
                can_invite_users=True,
            )
            await update.message.reply_text(f"{username} has been promoted to admin.")
    except Exception as e:
        await update.message.reply_text(f"Error promoting {username}: {str(e)}")

# Ban a user from the group
async def ban(update: Update, context: CallbackContext) -> None:
    if not context.args:
        await update.message.reply_text("Please specify the username to ban.")
        return

    username = context.args[0]
    chat_id = update.effective_chat.id

    try:
        member = await context.bot.get_chat_member(chat_id, username)
        await context.bot.ban_chat_member(chat_id, member.user.id)
        await update.message.reply_text(f"{username} has been banned from the group.")
    except Exception as e:
        await update.message.reply_text(f"Error banning {username}: {str(e)}")

# Mute a user
async def mute(update: Update, context: CallbackContext) -> None:
    if not context.args:
        await update.message.reply_text("Please specify the username to mute.")
        return

    username = context.args[0]
    chat_id = update.effective_chat.id

    try:
        member = await context.bot.get_chat_member(chat_id, username)
        await context.bot.restrict_chat_member(
            chat_id, member.user.id,
            permissions=ChatPermissions(can_send_messages=False)
        )
        await update.message.reply_text(f"{username} has been muted.")
    except Exception as e:
        await update.message.reply_text(f"Error muting {username}: {str(e)}")

# Unmute a user
async def unmute(update: Update, context: CallbackContext) -> None:
    if not context.args:
        await update.message.reply_text("Please specify the username to unmute.")
        return

    username = context.args[0]
    chat_id = update.effective_chat.id

    try:
        member = await context.bot.get_chat_member(chat_id, username)
        await context.bot.restrict_chat_member(
            chat_id, member.user.id,
            permissions=ChatPermissions(can_send_messages=True)
        )
        await update.message.reply_text(f"{username} has been unmuted.")
    except Exception as e:
        await update.message.reply_text(f"Error unmuting {username}: {str(e)}")

# Announce a message to the group
async def announce(update: Update, context: CallbackContext) -> None:
    if not context.args:
        await update.message.reply_text("Please specify the announcement message.")
        return
    
    announcement = ' '.join(context.args)
    await update.message.reply_text(f"📢 Announcement: {announcement}")







async def dare(update: Update, context: CallbackContext) -> None:
    dare_challenges = [
        "Send a funny selfie to the group!",
        "Text someone random 'I have a crush on you!'",
        "Sing the chorus of your favorite song in a voice message.",
        "Do 10 push-ups and send a video as proof!",
        "Talk in a funny accent for the next 5 minutes.",
        "Let someone else send a message from your phone.",
        "Share an embarrassing childhood story.",
        "Send a voice message saying the alphabet backwards.",
        "Pretend to be a waiter and serve imaginary food to the group.",
        "Imitate a famous celebrity for the next 5 minutes.",
        "Send a screenshot of your phone's home screen.",
        "Wear your clothes inside out for the next 10 minutes.",
        "Send a picture of the last thing you ate.",
        "Call your crush and sing a song to them.",
        "Do 15 jumping jacks and record yourself doing it.",
        "Let someone write a status for your social media account.",
        "Send a voice message of you singing ‘Happy Birthday’ to a random friend.",
        "Type a message using only your elbows.",
        "Speak in a robot voice for the next 5 minutes.",
        "Text your last sent emoji to a random contact.",
        "Pretend to be a cat and meow for the next 2 minutes.",
        "Share the last photo you took on your phone.",
        "Send a voice message saying a tongue twister three times fast.",
        "Do a handstand against a wall and take a picture.",
        "Eat a spoonful of something weird (ketchup, mustard, etc.).",
        "Let someone give you a nickname for the rest of the game.",
        "Send a message using only emojis for the next 5 minutes.",
        "Draw a self-portrait and share a picture of it.",
        "Wear socks on your hands for the next 10 minutes.",
        "Send a voice message reading the last text message you received.",
        "Send a picture of your current outfit.",
        "Talk like a pirate for the next 5 minutes.",
        "Send a random text to a contact and screenshot their response.",
        "Do a silly dance for 30 seconds and send a video.",
        "Send a picture of the contents of your fridge.",
        "Do an impression of your favorite animal.",
        "Let someone pick a song, and you have to sing along in a voice message.",
        "Send a message in a language you don’t speak using Google Translate.",
        "Post an embarrassing story as your social media status for 10 minutes.",
        "Make up a random rap about an object near you.",
        "Record yourself telling a joke and send it to the group.",
        "Wear a hat for the next 10 minutes (improvise if you don’t have one).",
        "Send a video of you trying to juggle three items.",
        "Try to say something with your mouth full (but be safe!)."
    ]

    dare_challenge = random.choice(dare_challenges)
    await update.message.reply_text(f"Dare: {dare_challenge}")

async def couple(update: Update, context):
    chat_members = await context.bot.get_chat_administrators(update.effective_chat.id)  # Get the list of participants
    if len(chat_members) < 2:
        await update.message.reply_text("There are not enough participants to form a couple!")
        return

    members_list = [member.user.first_name for member in chat_members]
    couple = random.sample(members_list, 2)  # Randomly select two members

    await update.message.reply_text(f"Today's random couple is: {couple[0]} ❤️ {couple[1]}!")

async def brb(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("shu shu idiot no need of u in this group.")

async def love(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("I love only Yuta.")

async def scythe_fact(update: Update, context):
    if "Scythe" in update.message.text.lower():
        await update.message.reply_text("Ek fun fact !! Scythe is the greatest nub of all time.")

async def kkrh_fact(update: Update, context):
    if "kkrh" in update.message.text.lower():
        await update.message.reply_text("SECRET!!")

async def nishu_fact(update: Update, context):
    if "Nishu" in update.message.text.lower():
        await update.message.reply_text("Nishu is my best friend")

async def ryuk_fact(update: Update, context):
    if "Ryuk" in update.message.text.lower():
        await update.message.reply_text("are ryuk whi na jiski bohut saari gf hai ... par sabke sath kat gaya bichare ka")

async def favorite_anime(update: Update, context):
    await update.message.reply_text("Yuki's favorite anime is \n The Time I Got Reincarnated as a slime \n Sword Art Online \n Blue Spring Ride \n One Piece \n Aur bhi bohut saare aur woh sab SECRET!!")

async def couple(update: Update, context):
    chat_members = await context.bot.get_chat_administrators(update.effective_chat.id)  # Get the list of participants
    if len(chat_members) < 2:
        await update.message.reply_text("There are not enough participants to form a couple!")
        return

    members_list = [member.user.first_name for member in chat_members]
    couple = random.sample(members_list, 2)  # Randomly select two members

    await update.message.reply_text(f"Today's random couple is: {couple[0]} ❤️ {couple[1]}!")

async def quotes(update: Update, context: CallbackContext) -> None:
    quotes_list = [
         "“I'm not a hero because I want your approval. I do it because I want to!” – All Might, My Hero Academia",
    "“To know sorrow is not terrifying. What is terrifying is to know you can't go back to happiness you could have.” – Matsumoto Rangiku, Bleach",
    "“It's not the face that makes someone a monster; it's the choices they make with their lives.” – Naruto Uzumaki, Naruto",
    "“People’s lives don’t end when they die, it ends when they lose faith.” – Itachi Uchiha, Naruto",
    "“The world isn’t perfect. But it’s there for us, doing the best it can. That’s what makes it so damn beautiful.” – Roy Mustang, Fullmetal Alchemist",
    "“Forgetting is like a wound. The wound may heal, but it has already left a scar.” – Monkey D. Luffy, One Piece",
    "“If you don’t take risks, you can’t create a future.” – Monkey D. Luffy, One Piece",
    "“Power comes in response to a need, not a desire.” – Goku, Dragon Ball Z",
    "“A lesson without pain is meaningless. That’s because you cannot gain something without sacrificing something else in return.” – Edward Elric, Fullmetal Alchemist",
    "“Fear is not evil. It tells you what your weakness is. And once you know your weakness, you can become stronger as well as kinder.” – Gildarts Clive, Fairy Tail",
    "“You need to accept the fact that you’re not the best and have all the will to strive to be better than anyone you face.” – Roronoa Zoro, One Piece",
    "“We are all like fireworks: we climb, we shine and always go our separate ways and become further apart. But even if that time comes, let’s not disappear like a firework, and continue to shine forever.” – Hitsugaya Toshiro, Bleach",
    "“A person grows up when he’s able to overcome hardships. Protection is important, but there are some things that a person must learn on his own.” – Jiraiya, Naruto",
    "“I have no money, no resources, no hopes. I am the happiest man alive.” – Joji Itami, GATE",
    "“Even if I lose this feeling, I’m sure I’ll just fall in love with you all over again.” – Syaoran Li, Cardcaptor Sakura",
    "“It’s okay not to be okay as long as you’re not giving up.” – Karen Aijou, Revue Starlight",
    "“The world is cruel, but also very beautiful.” – Mikasa Ackerman, Attack on Titan",
    "“Life is not a game of luck. If you wanna win, work hard.” – Sora, No Game No Life",
    "“The ticket to the future is always open.” – Vash The Stampede, Trigun",
    "“I’ll leave tomorrow’s problems to tomorrow’s me.” – Saitama, One Punch Man",
    "“Don’t give up, there’s no shame in falling down! True shame is to not stand up again!” – Shintaro Midorima, Kuroko’s Basketball",
    "“The future belongs to those who believe in the beauty of their dreams.” – Hinata Shoyo, Haikyuu!",
    "“Whatever you lose, you’ll find it again. But what you throw away you’ll never get back.” – Kenshin Himura, Rurouni Kenshin",
    "“If you can’t find a reason to fight, then you shouldn’t be fighting.” – Akame, Akame Ga Kill",
    "“A strong person is not the one who never falls, but the one who gets up again after falling!” – Gintoki Sakata, Gintama",
    "“You should enjoy the little detours. To the fullest. Because that's where you'll find the things more important than what you want.” – Ging Freecss, Hunter x Hunter",
    "“If you don’t share someone’s pain, you can never understand them.” – Nagato, Naruto",
    "“There are times in life when you have to distance yourself from those you love because you love them.” – Holo, Spice and Wolf",
    "“In our society, letting others find out that you’re nice is extremely dangerous.” – Hitagi Senjougahara, Bakemonogatari",
    "“Everything has a beginning and an end. Life is just a cycle of starts and stops.” – Mugen, Samurai Champloo",
    "“We don't have to know what tomorrow holds! That's why we can live for everything we're worth today!” – Natsu Dragneel, Fairy Tail",
    "“If you don’t like your destiny, don’t accept it.” – Naruto Uzumaki, Naruto",
    "“You should never give up on life, no matter how you feel. No matter how badly you want to give up.” – Canaan",
    "“To act is not necessarily compassion. True compassion sometimes comes from inaction.” – Hinata Miyake, A Place Further than the Universe",
    "“Forgetting is like a wound. The wound may heal, but it has already left a scar.” – Monkey D. Luffy, One Piece",
    "“Sometimes, we have to look beyond what people want and look at what’s right for them.” – Piccolo, Dragon Ball Z",
    "“I’ll always be by your side, just like the wind that flows through your hair.” – Yuki Sohma, Fruits Basket",
    "“Even if things are painful and tough, people should appreciate what it means to be alive.” – Yato, Noragami",
    "“You should enjoy the little detours. To the fullest. Because that's where you'll find the things more important than what you want.” – Ging Freecss, Hunter x Hunter",
    "“It’s okay to live, even if there’s no greater point to living.” – Yuugo Hachiken, Silver Spoon",
    "“I don’t care if no one likes me. I wasn’t created in this world to entertain everyone.” – Oreki Houtarou, Hyouka",
    "“It doesn’t matter how strong you are. As long as you have a reason to fight, you are capable of changing the world.” – Shingeki no Kyojin",
    "“No matter how deep the night, it always turns to day, eventually.” – Brook, One Piece",
    "“A dropout will beat a genius through hard work.” – Rock Lee, Naruto"
    ]
    quote = random.choice(quotes_list)
    await update.message.reply_text(quote)

# Replace 'YOUR_TOKEN_HERE' with your bot's token
TOKEN = '7419788460:AAFyXg-ysiqTXg7BkNh769Rc-2mvr_ZJeK0'

# Create the Application and pass it your bot's token
application = Application.builder().token(TOKEN).build()

# Add command handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("afk", afk))
application.add_handler(CommandHandler("truth", truth))
application.add_handler(CommandHandler("dare", dare))
application.add_handler(CommandHandler("brb", brb))
application.add_handler(CommandHandler("love", love))
application.add_handler(CommandHandler("quotes", quotes))
application.add_handler(CommandHandler("couple", couple))
application.add_handler(CommandHandler("favorite_anime", favorite_anime))
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("promote", promote))
application.add_handler(CommandHandler("ban", ban))
application.add_handler(CommandHandler("mute", mute))
application.add_handler(CommandHandler("unmute", unmute))
application.add_handler(CommandHandler("announce", announce))
application.add_handler(CommandHandler("afk", afk))
application.add_handler(CommandHandler("brb", brb))
application.add_handler(CallbackQueryHandler(button))
application.add_handler(CommandHandler("kang", kang))
application.add_handler(CommandHandler("rules", rules))
application.add_handler(CommandHandler("faq", faq))
application.add_handler(CommandHandler("userstats", user_stats))
application.add_handler(CommandHandler("poll", create_poll))
application.add_handler(PollAnswerHandler(handle_poll_answer))
application.add_handler(CommandHandler('play', play))
app.add_handler(CommandHandler("play2", play_game))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(CommandHandler('info', info))
application.add_handler(CommandHandler('rankings', rankings))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, log_chat))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, scythe_fact))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, harsha_fact))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, kkrh_fact))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, nishu_fact))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ryuk_fact))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))



# Run the bot
application.run_polling()
logger.info("Bot is polling...")
