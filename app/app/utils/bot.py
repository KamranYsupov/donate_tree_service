from typing import Dict, Any

from aiogram import Bot
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from app.loader import bot


async def echo_message_with_media(
        chat_id: int,
        original_message: Message
):
    """Полностью копирует сообщение с медиа"""
    text = original_message.text or original_message.caption or ""
    reply_markup = original_message.reply_markup
    # Фото
    if original_message.photo:
        await bot.send_photo(
            chat_id=chat_id,
            photo=original_message.photo[-1].file_id,
            caption=text,
            reply_markup=reply_markup,
    )

    # Видео
    elif original_message.video:
        await bot.send_video(
            chat_id=chat_id,
            video=original_message.video.file_id,
            caption=text,
            reply_markup=reply_markup,
        )

    # Кружочки видео (Video Note)
    elif original_message.video_note:
        await bot.send_video_note(
            chat_id=chat_id,
            video_note=original_message.video_note.file_id,
            reply_markup=reply_markup,
        )

    # Голосовые сообщения (Voice)
    elif original_message.voice:
        await bot.send_voice(
            chat_id=chat_id,
            voice=original_message.voice.file_id,
            caption=text,
            reply_markup=reply_markup,
        )

    # Документ
    elif original_message.document:
        await bot.send_document(
            chat_id=chat_id,
            document=original_message.document.file_id,
            caption=text,
            reply_markup=reply_markup,
        )

    # Аудио (музыка)
    elif original_message.audio:
        await bot.send_audio(
            chat_id=chat_id,
            audio=original_message.audio.file_id,
            caption=text,
            reply_markup=reply_markup,
            title=original_message.audio.title,
        )

    # Стикеры
    elif original_message.sticker:
        await bot.send_sticker(
            chat_id=chat_id,
            sticker=original_message.sticker.file_id,
            reply_markup=reply_markup
        )

    # Анимации (GIF)
    elif original_message.animation:
        await bot.send_animation(
            chat_id=chat_id,
            animation=original_message.animation.file_id,
            caption=text,
            reply_markup=reply_markup
        )

    # Местоположение
    elif original_message.location:
        await bot.send_location(
            chat_id=chat_id,
            latitude=original_message.location.latitude,
            longitude=original_message.location.longitude,
            reply_markup=reply_markup
        )

    # Контакты
    elif original_message.contact:
        await bot.send_contact(
            chat_id=chat_id,
            phone_number=original_message.contact.phone_number,
            first_name=original_message.contact.first_name,
            last_name=original_message.contact.last_name,
            reply_markup=reply_markup
        )

    # Опросы
    elif original_message.poll:
        await bot.send_poll(
            chat_id=chat_id,
            question=original_message.poll.question,
            options=[option.text for option in original_message.poll.options],
            reply_markup=reply_markup,
            is_anonymous=original_message.poll.is_anonymous,
            type=original_message.poll.type
        )

    # Просто текст
    elif original_message.text:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
        )




async def send_assembled_message(
        bot: Bot,
        chat_id: int,
        text: str,
        photo_id: str | None = None,
        button_text: str | None = None,
        button_link: str | None = None,
) -> Message:
    """Отправляет собранное сообщение"""
    # Создаем клавиатуру если есть кнопка
    reply_markup = None
    if button_text and button_link:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=button_text, url=button_link)]
            ]
        )
        reply_markup = keyboard

    if photo_id and text:
        return await bot.send_photo(
            chat_id=chat_id,
            photo=photo_id,
            caption=text,
            reply_markup=reply_markup,
        )
    elif text:
        return await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup
        )
    else:
        return await bot.send_message(chat_id, "❌ Сообщение пустое")


def serialize_message(message: Message) -> Dict[str, Any]:
    """Сериализует объект Message в словарь"""
    serialized = {
        "message_id": message.message_id,
        "chat_id": message.chat.id,
        "date": message.date.isoformat() if message.date else None,
        "text": message.text,
        "caption": message.caption,
        "entities": [entity.to_dict() for entity in message.entities] if message.entities else None,
        "caption_entities": [entity.to_dict() for entity in
                             message.caption_entities] if message.caption_entities else None,
    }

    # Сериализация медиа
    if message.photo:
        serialized["photo"] = [{
            "file_id": photo.file_id,
            "file_unique_id": photo.file_unique_id,
            "width": photo.width,
            "height": photo.height,
            "file_size": photo.file_size
        } for photo in message.photo]
        serialized["media_type"] = "photo"

    elif message.video:
        serialized["video"] = {
            "file_id": message.video.file_id,
            "file_unique_id": message.video.file_unique_id,
            "width": message.video.width,
            "height": message.video.height,
            "duration": message.video.duration,
            "file_name": message.video.file_name,
            "file_size": message.video.file_size
        }
        serialized["media_type"] = "video"

    elif message.document:
        serialized["document"] = {
            "file_id": message.document.file_id,
            "file_unique_id": message.document.file_unique_id,
            "file_name": message.document.file_name,
            "file_size": message.document.file_size
        }
        serialized["media_type"] = "document"

    elif message.audio:
        serialized["audio"] = {
            "file_id": message.audio.file_id,
            "file_unique_id": message.audio.file_unique_id,
            "duration": message.audio.duration,
            "performer": message.audio.performer,
            "title": message.audio.title,
            "file_name": message.audio.file_name,
            "file_size": message.audio.file_size,
            "mime_type": message.audio.mime_type
        }
        serialized["media_type"] = "audio"

    # Сериализация кнопок
    if message.reply_markup:
        serialized["reply_markup"] = serialize_reply_markup(message.reply_markup)

    return serialized


def serialize_reply_markup(reply_markup) -> Dict[str, Any]:
    """Сериализует клавиатуру"""
    if hasattr(reply_markup, "inline_keyboard"):
        return {
            "type": "inline_keyboard",
            "inline_keyboard": [
                [
                    {
                        "text": button.text,
                        "url": button.url,
                        "callback_data": button.callback_data,
                        "web_app": button.web_app.to_dict() if button.web_app else None
                    } for button in row
                ] for row in reply_markup.inline_keyboard
            ]
        }
    return None
