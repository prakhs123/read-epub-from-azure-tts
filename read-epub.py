import argparse
import asyncio
import logging
import os
import xml.etree.ElementTree as ET
import xml.sax.saxutils

import azure.cognitiveservices.speech as speechsdk
from bs4 import BeautifulSoup
from ebooklib import epub
from requests_html import HTMLSession

# configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SPEECH_KEY = os.environ.get('SPEECH_KEY')
SPEECH_REGION = os.environ.get('SPEECH_REGION')

if not SPEECH_KEY:
    raise ValueError("SPEECH_KEY is not set.")

if not SPEECH_REGION:
    raise ValueError("SPEECH_REGION is not set.")

import contextlib
import sys
import termios

@contextlib.contextmanager
def raw_mode(file):
    old_attrs = termios.tcgetattr(file.fileno())
    new_attrs = old_attrs[:]
    new_attrs[3] = new_attrs[3] & ~(termios.ECHO | termios.ICANON)
    try:
        termios.tcsetattr(file.fileno(), termios.TCSADRAIN, new_attrs)
        yield
    finally:
        termios.tcsetattr(file.fileno(), termios.TCSADRAIN, old_attrs)


def speech_synthesis_get_available_voices(text):
    """gets the available voices list."""
    speech_synthesizer = get_speech_synthesizer()
    result = speech_synthesizer.get_voices_async(text).get()
    # Check result
    if result.reason == speechsdk.ResultReason.VoicesListRetrieved:
        logging.info('Voices successfully retrieved, they are:')
        for voice in result.voices:
            logging.info(voice.name)
    elif result.reason == speechsdk.ResultReason.Canceled:
        logging.error("Speech synthesis canceled; error details: {}".format(result.error_details))


def display_text_that_will_be_converted_to_speech(text):
    logging.debug("converting following text to speech")
    logging.debug(text)


def extract_emphasis_text(xml_string):
    # Parse the XML string into an ElementTree object
    root = ET.fromstring(xml_string)

    # Find all the emphasis tags and extract their text
    emphasis_texts = [emphasis.text.strip() for emphasis in root.findall('.//{*}emphasis')]

    # Join the texts together with newlines
    return '\n'.join(emphasis_texts)


def get_speech_synthesizer():
    # This example requires environment variables named "SPEECH_KEY" and "SPEECH_REGION"
    speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('SPEECH_KEY'),
                                           region=os.environ.get('SPEECH_REGION'))
    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
    return speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)


def create_ssml_string(text, doc_tag, emphasis_level):
    text = text.replace('\n', ' ')
    return f"""
        <{doc_tag}>
            <mstts:express-as style="narration-professional">
                <prosody rate="+20.00%">
                    <emphasis level="{emphasis_level}">
                        {text}
                    </emphasis>
                </prosody>
            </mstts:express-as>
        </{doc_tag}>"""


def create_ssml_strings(contents, token_number, num_tokens):
    def reset_ssml_string():
        nonlocal curr_ssml_string, current_token_number_inside_index, token_number
        if curr_ssml_string == header:
            return
        curr_ssml_string += footer
        ssml_strings.append((curr_ssml_string, current_token_number_inside_index, token_number,
                             token_number + current_token_number_inside_index))
        curr_ssml_string = header
        token_number += current_token_number_inside_index
        current_token_number_inside_index = 0

    ssml_strings = []
    header = """<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US">
        <voice name="en-US-AriaNeural">"""
    footer = """
        </voice>
    </speak>"""
    curr_ssml_string = header
    current_token_number_inside_index = 0

    for content in contents:
        text = xml.sax.saxutils.escape(content.get_text())

        if content.name.startswith('h1'):
            doc_tag = "s"
            emphasis_level = "strong"
            reset_ssml_string()
        elif content.name.startswith('h2') or content.name.startswith('h3'):
            doc_tag = "s"
            emphasis_level = "moderate"
            reset_ssml_string()
        else:
            doc_tag = "p"
            emphasis_level = "none"

        if current_token_number_inside_index >= num_tokens:
            reset_ssml_string()
        if text == '':
            reset_ssml_string()
            continue
        token_string = create_ssml_string(text, doc_tag, emphasis_level)
        curr_ssml_string += token_string
        current_token_number_inside_index += 1
        logging.debug(
            f"token_string:\n {token_string}\ntoken_index: {token_number + current_token_number_inside_index}")

    if curr_ssml_string:
        curr_ssml_string += footer
        ssml_strings.append((curr_ssml_string, current_token_number_inside_index, token_number,
                             token_number + current_token_number_inside_index))
        current_token_number_inside_index += 1

    return ssml_strings


async def user_input_fn(i, reader, stop_event=None, halt_event=None, synthesizer=None):
    while True:
        try:
            user_input = await asyncio.wait_for(reader.read(1), timeout=0.1)
            user_input = user_input.decode()
            logging.info(f"User Entered `{user_input}`")
            if user_input == ' ':
                synthesizer.stop_speaking_async()
                return i+1
            elif user_input == 'q':
                synthesizer.stop_speaking_async()
                halt_event.set()
                return i
            elif user_input == 'r':
                synthesizer.stop_speaking_async()
                return i
            elif user_input == 'b':
                synthesizer.stop_speaking_async()
                return i-1
            elif user_input == 'p':
                synthesizer.stop_speaking_async()
                user_input = await reader.read(1)
                logging.info(f"User Entered `{user_input}`")
                if user_input == 'p':
                    return i
                elif user_input == 'q':
                    halt_event.set()
                    return i
                else:
                    logging.error("Invalid Input after Play/Pause")
                    halt_event.set()
                    return i
        except asyncio.TimeoutError:
            if stop_event.is_set():
                return i+1


async def speak(synthesizer, ssml_string, stop_event):
    syn_completed = False

    def synthesis_completed(evt):
        nonlocal syn_completed
        logging.debug(f"Synthesis Completed")
        speech_synthesis_result = evt.result
        if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            logging.debug("Speech synthesized for text [{}]".format(ssml_string))
        syn_completed = True

    def synthesis_cancelled(evt):
        nonlocal syn_completed
        logging.error(f"Synthesis Cancelled")
        speech_synthesis_result = evt.result
        if speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_synthesis_result.cancellation_details
            logging.error("Speech synthesis canceled: {}".format(cancellation_details.reason))
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                if cancellation_details.error_details:
                    logging.error("Error details: {}".format(cancellation_details.error_details))
        syn_completed = True

    synthesizer.synthesis_completed.connect(synthesis_completed)
    synthesizer.synthesis_canceled.connect(synthesis_cancelled)
    await asyncio.to_thread(synthesizer.start_speaking_ssml_async, ssml_string)
    while syn_completed is False:
        await asyncio.sleep(0.1)
    synthesizer.synthesis_completed.disconnect_all()
    stop_event.set()


async def main():
    args = parse_args()
    locale = args.get_available_voices
    if locale:
        speech_synthesis_get_available_voices(locale)
        return
    item_page = args.item_page
    start_index = args.start_index
    num_tokens = args.num_tokens
    try:
        if args.epub_or_html_file.endswith('.epub'):
            book = epub.read_epub(args.epub_or_html_file)
            items = [item for item in book.get_items() if item.get_type() == 9]
            item = items[item_page]
            html = item.get_content()
        elif args.epub_or_html_file.startswith('http'):
            session = HTMLSession()
            r = session.get(args.epub_or_html_file)
            html = r.text
        elif args.epub_or_html_file.endswith('.html'):
            with open(args.epub_or_html_file, 'r') as file:
                html = file.read()
        else:
            raise Exception('File Not Supported')
    except FileNotFoundError:
        logging.error("The file is not found.")
        return
    soup = BeautifulSoup(html, 'html.parser')
    if args.epub_or_html_file.startswith('http'):
        if soup.article:
            contents = soup.article.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p'])
        elif soup.section:
            contents = soup.section.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p'])
    else:
        contents = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p'])
    ssml_strings = create_ssml_strings(contents, 0, num_tokens)
    for i, (ssml_string, total_tokens, start_token, end_token) in enumerate(ssml_strings):
        logging.info(f"Index: {i} total_tokens: {total_tokens}, start_token: {start_token}, end_token: {end_token}")
    synthesizer = get_speech_synthesizer()
    halt_event = asyncio.Event()
    i = 0
    with raw_mode(sys.stdin):
        reader = asyncio.StreamReader()
        loop = asyncio.get_event_loop()
        await loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), sys.stdin)
        while i < len(ssml_strings):
            ssml_string, total_tokens, start_token, end_token = ssml_strings[i]
            if i < start_index:
                logging.info(f"Skipping Index: {i}")
                i += 1
                continue
            if halt_event.is_set():
                break
            logging.debug(f"ssml_string:\n{ssml_string}\nTotal tokens in ssml_string: {total_tokens - 1}")
            logging.info(f"Current Index: {i}")
            logging.info(f"Reading from start_token: {start_token}, end_token {end_token}")
            text = extract_emphasis_text(ssml_string)
            display_text_that_will_be_converted_to_speech(text)
            logging.info(
                "Press space to skip the current audio anytime, Press q to stop program, Press b to play previous index, Press r to restart playing, Press p to play/pause")
            # speech synthesis starts here
            stop_event = asyncio.Event()
            speak_coroutine = asyncio.create_task(speak(synthesizer, ssml_string, stop_event))
            user_input_coroutine = asyncio.create_task(user_input_fn(i, reader, stop_event, halt_event, synthesizer))
            _, i_to_set = await asyncio.gather(
                speak_coroutine,
                user_input_coroutine,
            )
            logging.info(f'Index {i} completed')
            i = i_to_set


def parse_args():
    parser = argparse.ArgumentParser(description='Text to speech converter')
    parser.add_argument('--get-available-voices', type=str, default=None,
                        help="Enter a locale in BCP-47 format (e.g. en-US) that you want to get the voices of, "
                             "or enter empty to get voices in all locales.")
    parser.add_argument('--epub-or-html-file', type=str, required=False,
                        help='path to the EPUB/HTML file to convert to speech')
    parser.add_argument('--num-tokens', type=int, default=1,
                        help='number of tokens in one ssml string, default 1')
    parser.add_argument('--item-page', type=int, default=0,
                        help='index of the page in the EPUB file to convert to speech')
    parser.add_argument('--start-index', type=int, default=0,
                        help='index of ssml string to start speech')
    return parser.parse_args()


if __name__ == '__main__':
    asyncio.run(main())
