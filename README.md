# PipeCat Chat Bot

This project is a simple chat bot connected to Llama Instant 8b. It uses a scraper to store data in a FAISS vector database. The bot retrieves content regarding the URLs from the vector database once you add the URL.

## Tech Stack

- **Python**: Programming language used for the backend.
- **Pipecat**: Framework for building the chat bot.
- **Daily**: Used for Text-to-Speech (TTS).
- **Deepgram**: Used for Speech-to-Text (STT).
- **FAISS**: Vector database for storing data.
- **Llama Index**: Used for storing data.
- **Bootstrap**: Frontend framework for styling.
- **jQuery**: JavaScript library for DOM manipulation.
- **Vite**: Build tool for Pipecat.

## Features

- Connects to Llama Instant 8b.
- Uses a scraper to store data in FAISS vector database.
- Retrieves content from the vector database based on added URLs.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   ```
2. Navigate to the project directory:
   ```bash
   cd pipecat-chatbot
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the chat bot:

   ```bash
   python server.py
   ```
2. To clean Daily rooms

   ```bash
   python clean_rooms.py
   ```
