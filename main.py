import logging
from telegram import (
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    InlineQueryHandler
)
from telegram.constants import ParseMode

from html import escape #return string from html
from uuid import uuid4 #generate a unique id
from room_scraper import *

#TODO: create a lock for the file to prevent corruption
# Enable logging
logging.basicConfig(
    filename='telegram-bot.log',
    filemode='w',
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt='%H:%M:%S',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Stages of conversation
START_ROUTES, END_ROUTES = range(2)

#button keyboard (for command shortcuts)
reply_keyboard = [
    ["schedule","@shit.py show rooms"],
    ["cancel room"]
]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)
#holds a dictionary of days of the week and the corresponding schedule object
days_of_the_week={
    'sunday':schedule.sunday,
    'monday':schedule.monday,
    'tuesday':schedule.tuesday,
    'wednesday':schedule.wednesday,
    'thursday':schedule.thursday
    }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send message on `/start`."""
    # Get user that sent /start and log his name
    user = update.message.from_user
    logger.info("User %s, %s started the conversation.", user.id, user.name)

    await update.message.reply_text(    
        "Hello, welcome to RoomBot. \r\n your one stop shop for all room related services!!!",
        reply_markup=markup
    )
    # Tell ConversationHandler that we're in state `FIRST` now
    return START_ROUTES

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays info on how to use the bot."""
    await update.message.reply_text("Use /start to test this bot.")

async def show_schedule(update:Update,context: ContextTypes.DEFAULT_TYPE):
    """
    displays buttons for days of the week and the user can press to see schedule of a day
    """
    keyboard=[
        [
        InlineKeyboardButton("Sunday",callback_data="sunday"),
        InlineKeyboardButton("Monday",callback_data="monday"),
        InlineKeyboardButton("Tuesday",callback_data="tuesday"),
        InlineKeyboardButton("Wednesday",callback_data="wednesday"),
        InlineKeyboardButton("Thursday",callback_data="thursday")
        ],
        [InlineKeyboardButton("exit",callback_data="exit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        text="Please choose a day", reply_markup=reply_markup
    )
    return START_ROUTES

async def show_hours(update:Update,context: ContextTypes.DEFAULT_TYPE):
    """
    after a day is pressed, show the hours set for that day
    also has button to enter change mode for start/end hour
    in change mode can increase/decrease the time by 1 between 9:00 and 20:00
    """
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()
    print(query.data)
    #display the relevent days times
    if query.data in days_of_the_week.keys():
        day = query.data
        keyboard=[[
            InlineKeyboardButton(str(days_of_the_week[day].start)+":00",callback_data="."),
            InlineKeyboardButton("-",callback_data="."),
            InlineKeyboardButton(str(days_of_the_week[day].end)+":00",callback_data=".")],
            [
            InlineKeyboardButton("change start",callback_data="change start " + day),
            InlineKeyboardButton("change end",callback_data="change end "+ day),
            InlineKeyboardButton("exit",callback_data="exit")
            ]

        ]

    #exit to main chat
    elif query.data == "exit":
        await query.edit_message_text(text="saved schedule")
        return START_ROUTES
    
    #enter change mode
    elif "change" in query.data:
        #splits the string into list, [change,start/end,<day>,+/-]
        args = query.data.split(' ')
        if args[1]=='start':
            
            if len(args) ==4: #if and inc/dec arg exists perform the action
                if args[3]=='-':
                    if days_of_the_week[args[2]].start>9:
                        days_of_the_week[args[2]].start-=1     
                elif args[3]=='+':
                    if days_of_the_week[args[2]].end>days_of_the_week[args[2]].start:
                        days_of_the_week[args[2]].start+=1
            current_time = days_of_the_week[args[2]].start
        elif args[1]=='end':
            
            if len(args) ==4:#if and inc/dec arg exists perform the action
                if args[3]=='-':
                    if days_of_the_week[args[2]].end > days_of_the_week[args[2]].start:
                        days_of_the_week[args[2]].end-=1
                elif args[3]=='+' and days_of_the_week[args[2]].end<20:
                    days_of_the_week[args[2]].end+=1
            current_time=days_of_the_week[args[2]].end
        #add/set the correct argument for the buttons
        if(len(args)<4):
            args.append('+')
        else:
            args[3]='+'
        plus_args = ' '.join(args)
        args[3]='-'
        minus_args = ' '.join(args)

        keyboard=[
            [InlineKeyboardButton(args[2],callback_data='.')],
            [InlineKeyboardButton("-",callback_data=minus_args),
             InlineKeyboardButton(str(current_time)+":00",callback_data="."),
             InlineKeyboardButton("+",callback_data=plus_args)],
             [InlineKeyboardButton("back",callback_data=args[2])]
            ]
            
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Instead of sending a new message, edit the message that
    # originated the CallbackQuery. This gives the feeling of an
    # interactive menu.
    await query.edit_message_text(text="please select option", reply_markup=reply_markup)
    return START_ROUTES


async def get_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the inline query. This is run when you type: @botusername <query>
    shows the room number, size, and available time slot (max 2 hours)
    user can choose a room to be reserved
    """

    query = update.inline_query.query
    if(query==''):
        return START_ROUTES
    category=''
    if(query == "show rooms"):
        print("showing rooms")
        available_rooms = get_available_rooms()
        results=[]
        for room in available_rooms:
            print(len(room.available_times))
            for time in room.available_times:
                id=str(room.id)+"_"+str(time.id)
                title=str(room.number)
                description="size:"+str(room.size)+ " time: "+str(time.start) +":"+str(time.end)
                results.append(
                    InlineQueryResultArticle(
                        id=id,title=title,description=description,input_message_content=InputTextMessageContent(str(room.id)+"_"+str(time.id))
                    )
                )
        print(results)
        await update.inline_query.answer(results)
    return START_ROUTES

    




#TODO: change this
async def display_shopping_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    print (query.answer())
    await query.edit_message_text("shopping cart")
    return ConversationHandler.END

def main() -> None:
    """Run the bot."""
    
    # get token for text file
    with open('token.txt') as f:
        lines = f.readlines()
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(lines[0][0:-1]).build()

    """
    create conversation structure:
        - start conversation
        - choose action (done through message buttons)
    """
    conversation_handler= ConversationHandler(
        entry_points=[CommandHandler("start",start)],
        states={
            START_ROUTES: [
                MessageHandler(filters.Regex("^schedule$"),show_schedule),
                CallbackQueryHandler(show_hours)
            ],
            END_ROUTES: [
                CallbackQueryHandler(display_shopping_cart,pattern="^shopping cart$")
            ],
        },
        fallbacks=[CommandHandler("start",start)], per_chat=True, per_user=False
    )
    application.add_handler(InlineQueryHandler(get_rooms))
    application.add_handler(conversation_handler)
    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()