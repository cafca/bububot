import io
import config
import json
import requests
import datetime

from pydub import AudioSegment

VOICE_IDS = {
    'default': '21m00Tcm4TlvDq8ikWAM',
    'vincent': 'cM6V3RU0Sx9iDNoAg9Ou'
}

def log(message):
    print(f'{datetime.datetime.now().strftime("%H:%M:%S.%f")}: {message}')
    
# The eleven labs handler converts the text from the message to audio
# and sends it back to the user as a telegram message.):
async def eleventy_labs_handler(update, context, answer):
    await update.message.chat.send_action(action="typing")

    # get the default voice id
    voice_id = VOICE_IDS['default']

    # get the api key from the config
    api_key = config.eleven_labs_api_key

    # set the headers
    headers = {
        'Content-Type': 'application/json',
        'xi-api-key': api_key,
        'accept': 'audio/mpeg'
    }

    # set the payload
    payload = {
        'text': answer,
        'voice_settings': {
            'stability': 0,
            'similarity_boost': 0
        }
    }

    # make the request and print errors
    r = requests.post(f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}', headers=headers, json=payload)

    # handle the response
    if r.status_code == 200:
        # get the MPEG-A audio file
        mpega_data = io.BytesIO(r.content)

        # conversion to ogg
        try:
            mpega_audio = AudioSegment.from_file(mpega_data, format="mp3")
            ogg_data = io.BytesIO()
            mpega_audio.export(ogg_data, format="ogg", codec="libopus")
            ogg_data.seek(0)
        except Exception as e:
            log("Could not decode the MPEG-A audio file:" + str(e))
            return


        await update.message.chat.send_action(action="typing")
        await context.bot.send_voice(update.effective_chat.id, ogg_data)
        log(f'Sent audio file to user')

    # Handle validation error on status code 422
    elif r.status_code == 422:
        # get the error message
        error_message = r.json()['detail'][0]['msg']

        # send the error message to the user
        await context.bot.send_message(update.effective_chat.id, text=error_message)
        log(f'Sent message to user: {error_message}')
    # Handle other errors
    else:
        # send the error message from `r` to the user
        await context.bot.send_message(update.effective_chat.id, text=r.text)
        log(f'Sent message to user: {r.text}')