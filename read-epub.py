import argparse
import logging
import os
import sys
import threading
import time
import xml.etree.ElementTree as ET
import xml.sax.saxutils
from _queue import Empty
from queue import Queue

import azure.cognitiveservices.speech as speechsdk
from bs4 import BeautifulSoup
from ebooklib import epub
from requests_html import HTMLSession

# configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

SPEECH_KEY = os.environ.get('SPEECH_KEY')
SPEECH_REGION = os.environ.get('SPEECH_REGION')

if not SPEECH_KEY:
    raise ValueError("SPEECH_KEY is not set.")

if not SPEECH_REGION:
    raise ValueError("SPEECH_REGION is not set.")


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
    logging.info("converting following text to speech")
    logging.info(text)


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


def create_ssml_strings(contents, next_sub_index, num_tokens):
    def reset_ssml_string():
        nonlocal curr_ssml_string, sub_index, next_sub_index
        curr_ssml_string += footer
        ssml_strings.append((curr_ssml_string, sub_index))
        curr_ssml_string = header
        next_sub_index += sub_index
        sub_index = 0

    ssml_strings = []
    header = """<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US">
        <voice name="en-US-AriaNeural">"""
    footer = """
        </voice>
    </speak>"""
    curr_ssml_string = header
    sub_index = 0

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

        if sub_index > num_tokens:
            reset_ssml_string()
        if text == '':
            reset_ssml_string()
            continue
        token_string = create_ssml_string(text, doc_tag, emphasis_level)
        curr_ssml_string += token_string
        sub_index += 1
        logging.debug(f"token_string:\n {token_string}\ntoken_index: {next_sub_index + sub_index}")

    if curr_ssml_string:
        curr_ssml_string += footer
        sub_index += 1
        ssml_strings.append((curr_ssml_string, sub_index))

    return ssml_strings


def skip_stop(q=None, stop_event=None, halt_event=None, synthesizer=None):
    while not stop_event.is_set():
        try:
            user_input = q.get_nowait()
            logging.info(f"User Entered `{user_input}`")
            if user_input == ' ':
                synthesizer.stop_speaking_async()
                return
            elif user_input == 'Q':
                synthesizer.stop_speaking_async()
                halt_event.set()
                return
        except Empty:
            pass
    logging.info(f"No User Input found, closing the skip stop thread for this iteration")


def get_user_input(q):
    while True:
        q.put(sys.stdin.read(1))
        time.sleep(0.1)


def main():
    args = parse_args()
    locale = args.get_available_voices
    if locale:
        speech_synthesis_get_available_voices(locale)
        return
    item_page = args.item_page
    next_index = args.next_index
    next_sub_index = args.next_sub_index
    num_tokens = args.num_tokens
    try:
        if args.epub_or_html_file.endswith('.epub'):
            book = epub.read_epub(args.epub_or_html_file)
            items = [item for item in book.get_items() if item.get_type() == 9]
            item = items[item_page]
            html = item.get_content()
        elif args.epub_or_html_file.endswith('.html'):
            with open(args.epub_or_html_file, 'r') as file:
                html = file.read()
        elif args.epub_or_html_file.startswith('http'):
            session = HTMLSession()
            r = session.get(args.epub_or_html_file)
            html = r.text
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
    ssml_strings = create_ssml_strings(contents[next_sub_index:], next_sub_index, num_tokens)
    synthesizer = get_speech_synthesizer()
    halt_event = threading.Event()
    q = Queue()
    get_user_input_thread = threading.Thread(target=get_user_input, args=(q, ), daemon=True)
    get_user_input_thread.start()
    for i, (ssml_string, total_tokens) in enumerate(ssml_strings[next_index:]):
        if halt_event.is_set():
            break
        logging.debug(f"ssml_string:\n{ssml_string}\nTotal tokens in ssml_string: {total_tokens - 1}")
        logging.info(f"Next Index: {next_index + i + 1}")
        if total_tokens < 1:
            continue
        text = extract_emphasis_text(ssml_string)
        display_text_that_will_be_converted_to_speech(text)
        # speech synthesis starts here
        stop_event = threading.Event()
        skip_stop_thread = threading.Thread(target=skip_stop, args=(q, stop_event, halt_event, synthesizer,))
        skip_stop_thread.start()
        speech_synthesis_result = synthesizer.speak_ssml_async(ssml_string).get()
        stop_event.set()
        skip_stop_thread.join()
        if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            logging.debug("Speech synthesized for text [{}]".format(ssml_string))
        elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_synthesis_result.cancellation_details
            logging.error("Speech synthesis canceled: {}".format(cancellation_details.reason))
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                if cancellation_details.error_details:
                    logging.error("Error details: {}".format(cancellation_details.error_details))


def parse_args():
    parser = argparse.ArgumentParser(description='Text to speech converter')
    parser.add_argument('--get-available-voices', type=str, default=None,
                        help="Enter a locale in BCP-47 format (e.g. en-US) that you want to get the voices of, "
                             "or enter empty to get voices in all locales.")
    parser.add_argument('--epub-or-html-file', type=str, required=False,
                        help='path to the EPUB/HTML file to convert to speech')
    parser.add_argument('--num-tokens', type=int, default=9,
                        help='number of tokens in one ssml string, default 9')
    parser.add_argument('--item-page', type=int, default=0,
                        help='index of the page in the EPUB file to convert to speech')
    parser.add_argument('--next-index', type=int, default=0,
                        help='index of ssml string to start speech')
    parser.add_argument('--next-sub-index', type=int, default=0,
                        help='index of ssml token to start processing')
    return parser.parse_args()


if __name__ == '__main__':
    main()
