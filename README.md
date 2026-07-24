

# Project Name

**ReflectAI – AI Digital Personality Twin**

## Project Overview

ReflectAI is an AI-powered digital personality twin that learns and replicates an individual's communication style through both **text** and **voice** interactions. The system first analyzes how a user communicates by observing their conversations and speech patterns by intereactig with user with having some meaningful conversation to identify user speaking pattern . It then builds a personalized communication profile that enables the AI to respond in the user's unique style, tone, vocabulary, and conversational behavior.

Unlike traditional chatbots that generate generic responses, ReflectAI creates a personalized AI model capable of interacting through both text and voice while maintaining the user's communication characteristics.

---

# System Workflow

```
                    REFLECT AI

               +----------------------+
               |    Landing Page      |
               +----------+-----------+
                          |
          +---------------+----------------+
          |                                |
          |                                |
          ▼                                ▼
  Chat Personality Analysis         Voice Personality Analysis
      (Ollama)                          (Vapi + Ollama)
          |                                |
          |                                |
          ▼                                ▼
      Chat Analyzer                 Voice Analyzer
          |                                |
          +---------------+----------------+
                          |
                          ▼
            Personality Profile Generator
                          |
                 MongoDB Personality Profile
                          |
          +---------------+----------------+
          |                                |
          ▼                                ▼
      Chat Mode                     Voice Mode
       (Ollama)                   (Vapi + Ollama)
```

---

# Module 1 — Chat Personality Analysis

This module is responsible for learning the user's communication style through text conversations.

### Workflow

```
User

↓

Chat Interface

↓

Ollama Chatbot

↓

Conversation History

↓

Ollama Personality Analyzer

↓

Personality Profile
```

### Ollama analyzes

* Writing style
* Vocabulary usage
* Frequently used words
* Sentence structure
* Formal or casual tone
* Humor style
* Emotional expression
* Response length
* Conversation habits
* Greeting style
* Question asking behavior
* Emoji usage
* Repeated phrases

The extracted information is stored as a structured personality profile in the database.

---

# Module 2 — Voice Personality Analysis

This module learns the user's personality through natural voice conversations.

Instead of manually recording audio samples, the user simply talks with an AI interviewer powered by Vapi.

### Workflow

```
User

↓

Vapi Voice Agent

↓

Speech to Text

↓

Conversation Transcript

↓

Ollama Personality Analyzer

↓

Updated Personality Profile
```

Vapi handles

* Voice conversation
* Speech recognition
* Real-time interaction

Ollama analyzes

* Speaking style
* Communication habits
* Tone of conversation
* Emotional behavior
* Vocabulary
* Confidence level
* Formality
* Humor
* Conversation flow

The transcript and extracted personality traits are merged into the existing personality profile.

---

# Personality Profile

Instead of saving only chat history, ReflectAI maintains a structured personality profile.

Example

```json
{
  "tone":"casual",
  "favorite_words":["bro","actually","literally"],
  "sentence_length":"medium",
  "emoji_usage":"high",
  "humor":"sarcastic",
  "confidence":"high",
  "communication_style":"friendly",
  "response_length":"short",
  "greeting":"informal"
}
```

This profile continuously evolves as the user interacts with the system.

---

# Chat Mode

Once personality analysis is complete, users can chat with their digital twin.

### Workflow

```
User Message

↓

React Frontend

↓

FastAPI

↓

Load Personality Profile

↓

Prompt Builder

↓

Ollama

↓

Generated Response

↓

User
```

The Prompt Builder converts the stored personality profile into a dynamic system prompt before sending it to Ollama.

Example

```
You are Tanmay.

Speak casually.

Use "bro" frequently.

Keep responses concise.

Avoid formal language.

Maintain a friendly tone.

Use light humor.

Never respond like a generic AI assistant.
```

---

# Voice Mode

Users can also interact with their AI twin through voice.

### Workflow

```
User Speaks

↓

Vapi

↓

Speech to Text

↓

FastAPI

↓

Load Personality Profile

↓

Prompt Builder

↓

Ollama

↓

Generate Response

↓

Vapi

↓

Natural Voice Response
```

In this mode:

* Vapi manages the real-time voice conversation.
* Ollama generates responses according to the learned personality.
* Vapi delivers the response using an expressive conversational voice.

---

# Complete System Architecture

```
                    ┌──────────────────────────┐
                    │      React Frontend      │
                    │      (Vite + Tailwind)   │
                    └─────────────┬────────────┘
                                  │
                         REST API / WebSocket
                                  │
                    ┌─────────────▼────────────┐
                    │     FastAPI Backend      │
                    └─────────────┬────────────┘
                                  │
                                  │
                                  │
                    ┌───────────────────────────┼
                    │                           │                           
                    ▼                           ▼     
                Chat Personality          Voice Personality          
                    Analyzer                Analyzer 
                    |
                    ↓
            1.Chat with Ollama         1.Talk with  Vapi AI it 
                                        save coversation and ollama will analyze
                                        2.upload the voice recording or 
                                        call recording with user
            2.Upload  screenshots of    3.Chat with Ollama
            previous chat with useR
                    │                           │                           
                    │                           │                           
                    │                           │                    
                    │                           │
                    └───────────────┬───────────┘
                                    ▼
                            Prompt Builder
                                    │
                                    ▼
                                Ollama LLM
                                    │
                        ┌───────────┴───────────┐
                        │                       │
                        ▼                       ▼
                    Chat Response          Voice Response
                                                │
                                                ▼
                                            Vapi AI
```

---

# Frontend

### Framework

* React (Vite)
* JavaScript
* Tailwind CSS
* React Router
* Framer Motion

### Pages

### 1. Landing Page

* Project introduction
* Animated AI visualization
* Get Started button
* Login / Register

---

### 2. Chat Personality Analysis

* Chat window
* Progress indicator
* Personality learning status
* Analysis completion percentage

---

### 3. Voice Personality Analysis

* Voice interview
* Animated microphone
* Live transcript
* Speaking status

---

### 4. Chat with Your AI Twin

* Messenger-like interface
* Conversation history
* Personality-based responses

---

### 5. Talk with Your AI Twin

* Voice call interface
* Microphone controls
* Speaking animation
* Live interaction

---

### 6. Personality Dashboard

Display:

* Communication Style
* Vocabulary Score
* Humor Style
* Confidence
* Emotional Tone
* Favorite Words
* Learning Progress
* Conversation Statistics

---

# Backend

### Framework

* FastAPI

### AI Components

* Ollama (LLM)
* Prompt Builder
* Personality Analyzer
* Conversation Manager
* Memory Manager

### Voice

* Vapi AI

reflect/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI server & route handlers
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── ollama_client.py # Communicates with local Ollama
│   │   │   ├── analyzer.py      # Personality analysis workflow
│   │   │   └── chat.py          # Digital Twin chat workflow
│   │   └── schemas.py           # API request/response structures (Pydantic)
│   ├── requirements.txt         # FastAPI, Uvicorn, etc.
│   └── run.py                   # Dev script to start backend
├── frontend/                    # Minimal structure for React setup later
│   ├── src/
│   │   ├── components/          # Reusable UI elements
│   │   ├── pages/               # Views (Landing, Analyze, Chat, Dashboard)
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
└── README.md
