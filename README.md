# read-epub-from-azure-tts
## Introduction
This script is used to convert an EPUB file into speech using Azure's Text-to-Speech (TTS) service. It reads an EPUB file and converts the text of the file into speech using Microsoft Azure Cognitive Services. The script requires SPEECH_KEY and SPEECH_REGION environment variables to be set with a valid Azure subscription key and region respectively.

This project involves converting epub to HTML pages that is divided into multiple ssml string (XML). Each ssml string contains headings or paragraphs, which are referred to as tokens.
The HTML page is split either by headings or by max 9 tokens. I have set max 9 tokens as Azure services can stream 10 minutes of audio in a single request for free-tier plan.

## TODOs
Currently, the project uses `en-US-AriaNeural` voice and `narration-professional` style, which is good for reading books.
The prosody rate is set to +20%. (Speed)
All these constants should be converted to variables and used in argparse.

## Requirements
* Python 3.6 or above
* azure.cognitiveservices.speech
* ebooklib
* beautifulsoup4

## Usage

```
python read-epub.py --epub-file EPUB_FILE_PATH --item-page ITEM_PAGE
```

## Arguments:
* epub-file: Required. Path to the EPUB file to convert to speech.
* item-page: Required. Index of the page in the EPUB file to convert to speech.

To process the ssml strings and tokens, two variables are used: next-index and next-sub-index.

* next-index: Optional. the index of the ssml string XML from which the speech should start.
* next-sub-index: Optional. the index of the selected token from which processing should begin.

It is important to note that next-sub-index is an independent entity that determines the starting point for processing tokens, and it does not relate to the processing of tokens inside the selected ssml string.

Tokens are the smallest unit, and a single ssml string can contain one or more tokens. By properly utilizing next-index and next-sub-index, the project can accurately generate speech output from the HTML page's multiple ssml string and their contained tokens.

To validate you are reading the correct page, I have added two options,

* confirm-before-reading: Optional. 1 if you want to confirm before reading, 0 otherwise
* prompt-only-once: Optional. 1 if you are ok that you want to read the page, and do not want prompt to come again and again. Default value is 1. If you want prompt again and again, you can set it to 0.


## Example
```
python read-epub.py --epub-file mybook.epub --item-page 2
```
This command converts the text of the 2nd page of mybook.epub into speech.

## Environment variables
This script uses two environment variables `SPEECH_KEY` and `SPEECH_REGION` to access the Azure Cognitive Services. Please set these variables to valid Azure subscription key and region respectively.

```
export SPEECH_KEY=<your_subscription_key>
export SPEECH_REGION=<your_subscription_region>
```

## Acknowledgements
This script uses Azure's Text-to-Speech service for converting text into speech.