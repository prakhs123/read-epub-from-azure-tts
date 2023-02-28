# read-epub-from-azure-tts
## Introduction
This script is used to convert an EPUB file into speech using Azure's Text-to-Speech (TTS) service. It reads an EPUB file and converts the text of the file into speech using Microsoft Azure Cognitive Services. The script requires SPEECH_KEY and SPEECH_REGION environment variables to be set with a valid Azure subscription key and region respectively.

This project involves converting epub to HTML pages that is divided into multiple ssml string (XML) (referred as `Index`). Each ssml string contains headings or paragraphs, which are referred to as `tokens`.
The HTML page is split into ssml strings either by headings or by specified number of tokens (default 1).

Open your epub in your favourite epub reader, and start reading pages by pages, accompanied by audio :).

## Prerequisites
1. Azure subscription - Create one for [free](https://azure.microsoft.com/free/cognitive-services)
2. [Create a Speech resource](https://portal.azure.com/#create/Microsoft.CognitiveServicesSpeechServices) in the Azure portal.
3. Get the Speech resource key and region. After your Speech resource is deployed, select Go to resource to view and manage keys. For more information about Cognitive Services resources, see [Get the keys for your resource](https://learn.microsoft.com/en-us/azure/cognitive-services/cognitive-services-apis-create-account#get-the-keys-for-your-resource).

## TODOs
Currently, the project uses `en-US-AriaNeural` voice and `narration-professional` style, which is good for reading books.
The prosody rate is set to +20%. (Speed)
All these constants should be converted to variables and used in argparse.
Remove ads and side contents from HTML pages

## Requirements
* Python 3.6 or above
* azure.cognitiveservices.speech
* ebooklib
* beautifulsoup4
* requests-html
* sshkeyboard

## Usage

```
python read-epub.py --epub-or-html-file EPUB_FILE_PATH --item-page ITEM_PAGE
```

## Arguments:
* epub-or-html-file: Optional. Path to the EPUB/HTML file to convert to speech.
* item-page: Optional. Index of the page in the file to convert to speech.

To process the ssml strings and tokens, two variables are used: next-index and next-sub-index.

* num-tokens: Optional. The number of tokens a SSML string should contain. Default 1.
* start-index: Optional. the index of the ssml string XML from which the speech should start.

Tokens are the smallest unit, and a single ssml string can contain one or more tokens. By properly utilizing num-token and start-index, the project can accurately generate speech output from the HTML page's multiple ssml string and their contained tokens.

## Environment variables
This script uses two environment variables `SPEECH_KEY` and `SPEECH_REGION` to access the Azure Cognitive Services. Please set these variables to valid Azure subscription key and region respectively.

```
export SPEECH_KEY=<your_subscription_key>
export SPEECH_REGION=<your_subscription_region>
```

## Getting Started
```
export SPEECH_KEY=<your_subscription_key>
export SPEECH_REGION=<your_subscription_region>
python3 -m venv .
source bin/activate
pip install -r requirements.txt
python3 read-epub.py --epub-or-html-file Alices\ Adventures\ in\ Wonderland.epub --item-page 0 --start-index 0
```

## Acknowledgements
This script uses Azure's Text-to-Speech service for converting text into speech.