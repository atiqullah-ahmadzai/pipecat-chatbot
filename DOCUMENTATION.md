# Simple Chat Bot Documentation

## Overview

This project is a simple chat bot connected to Llama Instant 8b. It uses a scraper to store data in a FAISS vector database. The bot retrieves content regarding the URLs from the vector database once you add the URL.

## Tech Stack

### Backend

- **Python**: The primary programming language used for the backend.
- **Pipecat**: A framework used to build the chat bot.
- **Daily**: Utilized for Text-to-Speech (TTS) functionalities.
- **Deepgram**: Utilized for Speech-to-Text (STT) functionalities.
- **FAISS**: A vector database used for storing and retrieving data.
- **Llama Index**: Used for storing data.

### Frontend

- **Bootstrap**: A frontend framework used for styling the user interface.
- **jQuery**: A JavaScript library used for DOM manipulation.
- **Vite**: A build tool used for building the Pipecat framework.

## Features

- **Llama Instant 8b Integration**: The chat bot is connected to Llama Instant 8b for enhanced conversational capabilities.
- **Data Scraping**: The bot uses a scraper to collect data and store it in the FAISS vector database.
- **URL Content Retrieval**: Once a URL is added, the bot retrieves relevant content from the vector database.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   ```
2. Navigate to the project directory:
   ```bash
   cd main
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
2. Interact with the bot through the provided user interface using http://localhost:8000
