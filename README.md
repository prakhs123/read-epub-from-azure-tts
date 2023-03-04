# read-epub-from-azure-tts
## Introduction
This script is used to convert an EPUB/HTML file or any web page with article/section into speech using Azure's Text-to-Speech (TTS) service. After taking input it converts the input to HTML and then turns the HTML's text into speech using Microsoft Azure Cognitive Services. The script requires SPEECH_KEY and SPEECH_REGION environment variables to be set with a valid Azure subscription key and region respectively.

After the input is converted into HTML, the HTML is divided into multiple ssml string (XML) (referred as `Index`). Each ssml string contains headings or paragraphs, which are referred to as `tokens`.
The HTML page is split into ssml strings either by headings or by specified number of tokens (default 1).

Open your epub/html in your favourite reader, and start reading pages by pages, accompanied by audio :).

## Prerequisites
1. Azure subscription - Create one for [free](https://azure.microsoft.com/free/cognitive-services)
2. [Create a Speech resource](https://portal.azure.com/#create/Microsoft.CognitiveServicesSpeechServices) in the Azure portal.
3. Get the Speech resource key and region. After your Speech resource is deployed, select Go to resource to view and manage keys. For more information about Cognitive Services resources, see [Get the keys for your resource](https://learn.microsoft.com/en-us/azure/cognitive-services/cognitive-services-apis-create-account#get-the-keys-for-your-resource).

## TODOs
Currently, the project uses `en-US-AriaNeural` voice and `narration-professional` style, which is good for reading books.
The prosody rate is set to +20%. (Speed). All these constants should be converted to variables and used in argparse.  
Remove ads and side contents from HTML pages

## Requirements
* Python 3.6 or above
* azure.cognitiveservices.speech
* ebooklib
* beautifulsoup4
* requests-html

## Usage
```
python read-epub.py EPUB_OR_HTML_FILE --item-page ITEM_PAGE
```
## Arguments:
* epub-or-html-file: Optional. Path to the EPUB/HTML file to convert to speech.  

The page of the epub file to read can be configured by item-page argument. Note, each epub files is divided into multiple pages, which includes Preface, Acknowledgements, Front Cover etc. So, If you want to read from Chapter 1 of the epub file, you need to find the appropriate page by trial and error.    

* item-page: Optional. Index of the page in the epub file to convert to speech. (not required in case of webpage/HTML)  

How the HTML is broken into SSML strings can be configured by num-tokens argument  
* num-tokens: Optional. The number of tokens each SSML string should contain. Default 1.  

The place from where the speech should start can be configured by start-index argument    
* start-index: Optional. the index of the SSML string from which the speech should start.  

Tokens are the smallest unit, and a single SSML string can contain one or more tokens. By properly utilizing num-token and start-index, the project can accurately generate speech output from the HTML page's multiple SSML string and their contained tokens.

## Features:
Press space to skip the current index audio anytime, Press q to stop program, Press b to play previous index, Press r to restart playing current index, Press p to play/pause

## Environment variables
This script uses two environment variables `SPEECH_KEY` and `SPEECH_REGION` to access the Azure Cognitive Services. Please set these variables to valid Azure subscription key and region respectively.

```
export SPEECH_KEY=<your_subscription_key>
export SPEECH_REGION=<your_subscription_region>
```

## Getting Started

### Initial Setup
```
export SPEECH_KEY=<your_subscription_key>
export SPEECH_REGION=<your_subscription_region>
python3 -m venv .
source bin/activate
pip install -r requirements.txt
```
### Reading epub file
```
python3 read-epub.py Alices\ Adventures\ in\ Wonderland.epub --item-page 0 --start-index 0
```
### Reading Web page
```
python3 read-epub.py "https://www.artofliving.org/in-en/meditation/meditation-for-you/meditation-and-insomnia"
```
## Acknowledgements
This script uses Azure's Text-to-Speech service for converting text into speech.