from config import conf, generation_config
from google import genai
import traceback
import sys
from telebot.types import Message
from md2tgmd import escape
from telebot import TeleBot
import io
from PIL import Image
import time


gemini_chat_dict = {}
gemini_pro_chat_dict = {}
default_model_dict = {}

model_1                 =       conf["model_1"]
model_2                 =       conf["model_2"]
error_info              =       conf["error_info"]
before_generate_info    =       conf["before_generate_info"]
download_pic_notify     =       conf["download_pic_notify"]

search_tool = {'google_search': {}}

client = genai.Client(api_key=sys.argv[2])

async def gemini_stream(bot, message, m, model_type):
    sent_message = None
    try:
        sent_message = await bot.reply_to(message, "🤖 Generating answers...")

        chat = None
        if model_type == model_1:
            chat_dict = gemini_chat_dict
        else:
            chat_dict = gemini_pro_chat_dict

        if str(message.from_user.id) not in chat_dict:
            chat = client.aio.chats.create(model=model_1, config={'tools': [search_tool]})
            chat_dict[str(message.from_user.id)] = chat
        else:
            chat = chat_dict[str(message.from_user.id)]

        response = await chat.send_message_stream(
            m,
            )

        full_response = ""
        last_update = time.time()
        update_interval = conf["streaming_update_interval"]

        async for chunk in response:
            if hasattr(chunk, 'text') and chunk.text:
                full_response += chunk.text
                current_time = time.time()

                if current_time - last_update >= update_interval:

                    try:
                        await bot.edit_message_text(
                            escape(full_response),
                            chat_id=sent_message.chat.id,
                            message_id=sent_message.message_id,
                            parse_mode="MarkdownV2"
                            )
                    except Exception as e:
                        if "parse markdown" in str(e).lower():
                            await bot.edit_message_text(
                                full_response,
                                chat_id=sent_message.chat.id,
                                message_id=sent_message.message_id
                                )
                        else:
                            if "message is not modified" not in str(e).lower():
                                print(f"Error updating message: {e}")
                    last_update = current_time

        try:
            await bot.edit_message_text(
                escape(full_response),
                chat_id=sent_message.chat.id,
                message_id=sent_message.message_id,
                parse_mode="MarkdownV2"
            )
        except Exception as e:
            try:
                if "parse markdown" in str(e).lower():
                    await bot.edit_message_text(
                        full_response,
                        chat_id=sent_message.chat.id,
                        message_id=sent_message.message_id
                    )
            except Exception:
                traceback.print_exc()


    except Exception as e:
        traceback.print_exc()
        if sent_message:
            await bot.edit_message_text(
                f"{error_info}\nError details: {str(e)}",
                chat_id=sent_message.chat.id,
                message_id=sent_message.message_id
            )
        else:
            await bot.reply_to(message, f"{error_info}\nError details: {str(e)}")

async def gemini_edit(bot: TeleBot, message: Message, m: str, photo_file: bytes):

    image = Image.open(io.BytesIO(photo_file))
    response = await client.aio.models.generate_content(
        model=model_1,
        contents=[m, image],
        config=generation_config
    )
    for part in response.candidates[0].content.parts:
        if part.text is not None:
            await bot.send_message(message.chat.id, escape(part.text), parse_mode="MarkdownV2")
        elif part.inline_data is not None:
            photo = part.inline_data.data
            await bot.send_photo(message.chat.id, photo)