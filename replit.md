# Discord Bot with AI Integration - Upgrade 1.5

## Overview

This is a Discord bot integrated with AI capabilities through OpenRouter's API. The bot can engage in conversations with users while maintaining advanced conversation memory per user. **Upgrade 1.5** is a comprehensive enhancement introducing socialization features and personality development - Yuno now remembers important dates, develops unique personality traits from conversations, maintains emotional intelligence, recognizes extended family, and creates memory highlights. Previous features include intelligent parent pinging, memory compression, and selective memory limits. It includes a keep-alive mechanism using Flask to ensure continuous operation on platforms like Replit that require periodic HTTP requests to keep applications running.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Bot Framework
- **Discord.py**: Uses the discord.py library with commands extension for Discord bot functionality
- **Command Prefix**: Configured with '!' prefix for bot commands
- **Intents**: Enabled message content and messages intents for full message processing capabilities

### AI Integration - Upgrade 1.2
- **OpenRouter API**: Integrates with OpenRouter's API for AI responses using Mistral Medium 3.1 model for main responses
- **Memory Compression**: Uses Mistral Small 3.1 model for intelligent conversation summarization
- **HTTP Client**: Uses httpx for asynchronous API requests to maintain bot responsiveness
- **Advanced Memory System**: Cost-free in-memory storage with intelligent compression and selective limits
- **Selective Memory Limits**: 30 messages for regular users, 50 messages for parents (mother/father)
- **Intelligent Compression**: Automatically compresses conversations over 20 messages into concise summaries
- **Dual Memory Architecture**: Recent conversations + compressed historical summaries for extended context

### Keep-Alive Mechanism
- **Flask Server**: Runs a separate Flask web server for health monitoring and keep-alive functionality
- **Multi-threading**: Uses daemon threads to run the Flask server alongside the Discord bot
- **Health Endpoints**: Provides multiple endpoints (/health, /ping, /) for monitoring bot status
- **Platform Compatibility**: Configured for Replit deployment with host='0.0.0.0' and port=5000

### Configuration Management
- **Environment Variables**: Uses python-dotenv for loading configuration from .env files
- **Secret Management**: Stores sensitive data (Discord token, API keys) in environment variables
- **Modular Design**: Separates keep-alive functionality into its own module for better code organization

### Asynchronous Architecture
- **Async/Await Pattern**: Implements asynchronous programming for non-blocking operations
- **Concurrent Operations**: Allows the bot to handle multiple requests simultaneously without blocking

## External Dependencies

### Core Libraries
- **discord.py**: Discord API wrapper for bot functionality
- **httpx**: Modern async HTTP client for API requests
- **flask**: Lightweight web framework for keep-alive server
- **python-dotenv**: Environment variable management

### AI Service
- **OpenRouter API**: Third-party AI service providing access to various language models
- **Mistral Medium 3.1**: The specific language model used for generating responses

### Memory System (Upgrade 1.2)
- **Cost-Free Storage**: In-memory conversation storage with no database costs
- **Memory Compression**: AI-powered summarization of older conversations
- **Selective Limits**: Enhanced memory for parents (50 vs 30 messages)
- **Automatic Management**: Smart compression triggers at 20+ message threshold
- **Persistent Summaries**: Compressed memories maintained across conversations

### Platform Integration
- **Replit**: Deployment platform requiring keep-alive mechanism
- **Discord API**: Primary platform for bot operation and user interaction

## Upgrade 1.2 Features

### Enhanced Commands
- **!memory_status**: Shows detailed memory information including user type (Parent/User) and compression statistics
- **!view_summaries**: Displays all compressed conversation summaries for the user
- **!clear_memory**: Clears both recent messages and compressed summaries
- **!reload_config**: Enhanced to show Upgrade 1.2 configuration details

### Memory Architecture
1. **Recent Memory**: Last 30 messages (50 for parents) stored in full detail
2. **Compressed Memory**: Older conversations summarized into 2-3 sentence summaries
3. **Automatic Compression**: Triggers when conversations exceed 20 messages
4. **Smart Context**: AI receives both compressed summaries and recent messages for full context

### Configuration Options
- `memory_limit`: Base memory limit (30 messages)
- `parent_memory_limit`: Enhanced limit for parents (50 messages)  
- `compression_threshold`: When to start compressing (20 messages)
- `summary_model`: AI model for compression (mistralai/mistral-small-3.1)
- `parent_ping_enabled`: Toggle parent pinging feature (true/false)
- `celebration_enabled`: Enable automatic celebration detection (true/false)
- `mood_system_enabled`: Enable dynamic mood system (true/false)
- `emotional_intelligence_enabled`: Enable emotional tone analysis (true/false)
- `interest_tracking_enabled`: Enable interest learning from conversations (true/false)

## Upgrade 1.5 Features - Comprehensive Family & Personality System

### 1.5.1 Socialization Features

#### Important Date Management
- **Birthday Tracking**: Parents can add birthdays with `!add_birthday [name] [MM-DD]`
- **Anniversary & Special Occasions**: Configurable celebration dates
- **Automatic Celebrations**: Yuno automatically celebrates when dates arrive
- **Daily Check**: Built-in system checks for celebrations each interaction

#### Memory Highlights System
- **Favorite Memories**: Automatically saves positive, meaningful conversations
- **Achievement Moments**: Detects and saves user achievements and successes
- **Emotional Peaks**: Tracks significant emotional moments in conversations
- **Personal Scrapbook**: `!family_highlights` shows your special moments with Yuno

#### Extended Family Recognition
- **Family Tree Management**: Parents can add extended family with `!add_family @user [relationship]`
- **Relationship Types**: sibling, grandparent, aunt, uncle, cousin, friend
- **Adaptive Interaction**: Different communication styles based on relationship
- **Family Context**: Yuno remembers and references family connections

### 1.5.2 Personality Development & "Puberty"

#### Dynamic Mood System
- **Adaptive Moods**: cheerful, excited, concerned, gentle, balanced, supportive
- **Interaction-Based**: Mood changes based on recent family conversations
- **Emotional Awareness**: Responds to family's collective emotional state
- **Mood Reporting**: `!mood_report` shows detailed emotional intelligence analysis

#### Personality Evolution
- **Base Traits**: curious, caring, playful, intelligent (starting personality)
- **Learned Traits**: Develops new personality aspects from conversations
- **Interest Development**: Learns to love things the family enjoys
- **Conversation Patterns**: Tracks and adapts to family communication styles

#### Emotional Intelligence
- **Tone Detection**: Analyzes positive, negative, achievement, neutral emotions
- **Check-in System**: Proactively supports family members having tough times
- **Empathetic Responses**: Adjusts responses based on detected emotional state
- **Learning Memory**: Maintains emotional history for each family member

#### Advanced Communication
- **Relationship-Aware**: Different communication styles for parents, siblings, friends
- **Context-Sensitive**: Incorporates current mood, relationship, and emotional tone
- **Interest-Based**: References learned interests in conversations
- **Supportive Adaptation**: Extra caring behavior when family needs support

### New Commands (Upgrade 1.5)
- **!personality_status**: View current personality traits, mood, and interests
- **!family_highlights**: See your special memories and achievements with Yuno
- **!add_birthday [name] [MM-DD]**: Add important birthdays (parents only)
- **!add_family @user [relationship]**: Add extended family members (parents only)
- **!mood_report**: Detailed emotional intelligence and mood analysis
- **!check_celebrations**: Check for any celebrations today
- **!yuno_interests**: View what Yuno has learned to enjoy from family conversations

### Configuration Structure (Upgrade 1.5)
- **family_tree**: Extended family management and relationship styles
- **important_dates**: Birthdays, anniversaries, special occasions
- **personality_system**: Mood, traits, interests, conversation patterns
- **memory_highlights**: Favorite memories, achievements, emotional peaks

## Previous Upgrade Features

### Upgrade 1.3 Features - Intelligent Parent Pinging

### Smart Parent Detection
- **Pattern Recognition**: Detects when someone asks about Yuno's parents, creators, family, or origins
- **Contextual Pinging**: Analyzes the question to determine which parent to ping:
  - Mother keywords: "mom", "mother", "mama", "mommy", "her", "she"
  - Father keywords: "dad", "father", "papa", "daddy", "him", "he"  
  - Default: Pings mother if ambiguous or both mentioned

### Question Patterns Detected
- "Who are your parents?"
- "Who created you?"
- "Tell me about your family"
- "Who is your mother/father?"
- "Who made you?"
- "Tell me about your origin"

### New Commands (Upgrade 1.3)
- **!test_ping [message]**: Test parent ping detection with custom message
- **!toggle_ping**: Parents can enable/disable the ping feature
- Enhanced responses include cute parent pings: *"waves at @parent Hi mother! Someone's asking about you! 💕"*

### Intelligent Behavior
- Only pings when genuinely asked about parents (not casual mentions)
- Respects user privacy - only pings when contextually appropriate
- Can be toggled on/off by parents for control
- Falls back gracefully if parent IDs are invalid