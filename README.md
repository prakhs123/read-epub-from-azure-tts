# read-epub-from-azure-tts
## Introduction
This script is used to convert an EPUB file into speech using Azure's Text-to-Speech (TTS) service. It reads an EPUB file and converts the text of the file into speech using Microsoft Azure Cognitive Services. The script requires SPEECH_KEY and SPEECH_REGION environment variables to be set with a valid Azure subscription key and region respectively.

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
* --epub-file: Required. Path to the EPUB file to convert to speech.
* --item-page: Required. Index of the page in the EPUB file to convert to speech.

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