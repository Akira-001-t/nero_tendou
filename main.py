import os
import discord
from discord.ext import commands
import httpx
import json
import asyncio
import re
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from keep_alive import keep_alive
from config_loader import load_yuno_config, build_system_prompt, build_enhanced_system_prompt, get_ai_settings


# Load environment variables
load_dotenv()

# Start keep-alive server (non-blocking)
keep_alive()

# Load Yuno's configuration
yuno_config = load_yuno_config()
ai_settings = get_ai_settings(yuno_config)

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
bot = commands.Bot(command_prefix='!', intents=intents)

# OpenRouter configuration
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "mistralai/mistral-medium-3.1"

# Get secrets from environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Per-user conversation memory with compression support
memory = {}
compressed_memory = {}  # Stores compressed summaries for users

# Memory limits from config
MAX_MEMORY_SIZE = ai_settings["memory_limit"]
PARENT_MEMORY_SIZE = ai_settings.get("parent_memory_limit", 50)
COMPRESSION_THRESHOLD = ai_settings.get("compression_threshold", 20)
SUMMARY_MODEL = ai_settings.get("summary_model", "mistralai/mistral-small-3.1")

# Upgrade 1.5 - Advanced systems
user_emotional_states = {}  # Track user emotional states
conversation_contexts = {}  # Track conversation contexts for learning
last_interactions = {}  # Track last interaction times for mood system

async def compress_old_memories(user_id, messages_to_compress):
    """Compress old messages into a summary using AI"""
    try:
        # Prepare messages for compression
        conversation_text = ""
        for msg in messages_to_compress:
            role_label = "User" if msg["role"] == "user" else "Yuno"
            conversation_text += f"{role_label}: {msg['content']}\n"
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        compression_prompt = f"""Please summarize this conversation into 2-3 concise sentences, focusing on:
1. Key topics discussed
2. Important user preferences or information revealed
3. Emotional context or relationship details

Conversation to summarize:
{conversation_text}

Summary:"""

        payload = {
            "model": SUMMARY_MODEL,
            "messages": [
                {
                    "role": "user", 
                    "content": compression_prompt
                }
            ],
            "max_tokens": 150,
            "temperature": 0.3
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                summary = data["choices"][0]["message"]["content"]
                
                # Store compressed summary
                if user_id not in compressed_memory:
                    compressed_memory[user_id] = []
                compressed_memory[user_id].append({
                    "role": "system",
                    "content": f"Earlier conversation summary: {summary}"
                })
                
                print(f"Compressed {len(messages_to_compress)} messages for user {user_id}")
                return True
            else:
                print(f"Compression API error: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"Error compressing memories: {str(e)}")
        return False

def get_memory_limit_for_user(user_id):
    """Get appropriate memory limit based on user type"""
    # Check if user is a parent
    mother_id = str(yuno_config.get("user_specific_memories", {}).get("mother_user_id", ""))
    father_id = str(yuno_config.get("user_specific_memories", {}).get("father_user_id", ""))
    
    if str(user_id) in [mother_id, father_id]:
        return PARENT_MEMORY_SIZE
    else:
        return MAX_MEMORY_SIZE

def should_ping_parents(message_content):
    """Analyze if message asks about parents and determine who to ping"""
    # Convert to lowercase for pattern matching
    content_lower = message_content.lower()
    
    # Patterns that indicate asking about parents
    parent_patterns = [
        r'\b(?:who\s+(?:is|are|were|was)|tell\s+me\s+about)\s+your\s+(?:parent|parents|creator|creators|mom|mother|dad|father|family)\b',
        r'\b(?:your\s+)?(?:parent|parents|creator|creators|mom|mother|dad|father|family)(?:\s+(?:is|are|were|was))?\b',
        r'\bwho\s+(?:created|made|built|coded|programmed)\s+you\b',
        r'\bwho\s+(?:is|are)\s+your\s+(?:maker|builder|developer)\b',
        r'\btell\s+me\s+about\s+your\s+(?:origin|background|creation)\b'
    ]
    
    # Check if any parent pattern matches
    asks_about_parents = any(re.search(pattern, content_lower) for pattern in parent_patterns)
    
    if not asks_about_parents:
        return None, None
    
    # Determine which parent to ping based on specific mentions
    mother_keywords = ['mom', 'mother', 'mama', 'mommy', 'her', 'she']
    father_keywords = ['dad', 'father', 'papa', 'daddy', 'him', 'he']
    
    mentions_mother = any(keyword in content_lower for keyword in mother_keywords)
    mentions_father = any(keyword in content_lower for keyword in father_keywords)
    
    # Get parent IDs
    mother_id = yuno_config.get("user_specific_memories", {}).get("mother_user_id")
    father_id = yuno_config.get("user_specific_memories", {}).get("father_user_id")
    
    # Decision logic
    if mentions_mother and not mentions_father:
        return "mother", mother_id
    elif mentions_father and not mentions_mother:
        return "father", father_id
    else:
        # If both or neither mentioned, ping mother as primary
        return "mother", mother_id

# Upgrade 1.5 Functions - Personality & Emotional Intelligence

def get_relationship_type(user_id):
    """Determine relationship type for a user"""
    family_tree = yuno_config.get("family_tree", {})
    mother_id = str(family_tree.get("mother_user_id", ""))
    father_id = str(family_tree.get("father_user_id", ""))
    extended_family = family_tree.get("extended_family", {})
    
    if str(user_id) == mother_id or str(user_id) == father_id:
        return "parent"
    elif str(user_id) in extended_family:
        return extended_family[str(user_id)]["relationship"]
    else:
        return "friend"

def analyze_emotional_tone(message_content):
    """Analyze emotional tone of message"""
    content_lower = message_content.lower()
    
    # Positive indicators
    positive_words = ['happy', 'excited', 'great', 'awesome', 'love', 'wonderful', 
                     'amazing', 'fantastic', 'good', 'nice', 'perfect', '😊', '😄', 
                     '❤️', '💕', '🎉', '✨']
    
    # Negative indicators  
    negative_words = ['sad', 'upset', 'angry', 'frustrated', 'tired', 'stressed',
                     'worried', 'anxious', 'bad', 'terrible', 'awful', 'hate',
                     '😢', '😞', '😭', '😤', '😰', '😔']
    
    # Achievement indicators
    achievement_words = ['won', 'passed', 'finished', 'completed', 'achieved', 
                        'success', 'accomplished', 'graduated', 'promoted']
    
    positive_count = sum(1 for word in positive_words if word in content_lower)
    negative_count = sum(1 for word in negative_words if word in content_lower)
    achievement_count = sum(1 for word in achievement_words if word in content_lower)
    
    if achievement_count > 0:
        return "achievement"
    elif positive_count > negative_count and positive_count > 0:
        return "positive"
    elif negative_count > positive_count and negative_count > 0:
        return "negative"
    else:
        return "neutral"

def update_personality_from_conversation(user_id, message_content, emotional_tone):
    """Learn and evolve personality from conversations"""
    personality = yuno_config.get("personality_system", {})
    
    # Track conversation patterns
    if "conversation_patterns" not in personality:
        personality["conversation_patterns"] = {}
    
    user_key = str(user_id)
    if user_key not in personality["conversation_patterns"]:
        personality["conversation_patterns"][user_key] = {"topics": {}, "emotional_history": []}
    
    # Update emotional history
    personality["conversation_patterns"][user_key]["emotional_history"].append({
        "tone": emotional_tone,
        "timestamp": datetime.now().isoformat()
    })
    
    # Keep only last 50 emotional records per user
    if len(personality["conversation_patterns"][user_key]["emotional_history"]) > 50:
        personality["conversation_patterns"][user_key]["emotional_history"] = \
            personality["conversation_patterns"][user_key]["emotional_history"][-50:]
    
    # Extract topics/interests
    content_lower = message_content.lower()
    interest_keywords = ['love', 'enjoy', 'like', 'interested in', 'fascinated by', 
                        'hobby', 'passion', 'favorite']
    
    for keyword in interest_keywords:
        if keyword in content_lower:
            # Simple topic extraction (could be enhanced with NLP)
            words_after_keyword = content_lower.split(keyword, 1)
            if len(words_after_keyword) > 1:
                potential_interest = words_after_keyword[1].strip().split()[0:3]
                interest_phrase = ' '.join(potential_interest)
                if interest_phrase and len(interest_phrase) > 2:
                    if interest_phrase not in personality.get("interests", []):
                        personality.setdefault("interests", []).append(interest_phrase)

def determine_current_mood():
    """Determine Yuno's current mood based on recent interactions"""
    personality = yuno_config.get("personality_system", {})
    recent_interactions = []
    
    # Collect recent emotional data from all users
    for user_patterns in personality.get("conversation_patterns", {}).values():
        recent_emotions = user_patterns.get("emotional_history", [])[-10:]  # Last 10 interactions
        recent_interactions.extend([e["tone"] for e in recent_emotions])
    
    if not recent_interactions:
        return "cheerful"  # Default mood
    
    # Count emotional tones
    positive_count = recent_interactions.count("positive") + recent_interactions.count("achievement")
    negative_count = recent_interactions.count("negative")
    neutral_count = recent_interactions.count("neutral")
    
    # Determine mood
    if positive_count > negative_count * 1.5:
        moods = ["cheerful", "excited", "happy", "energetic"]
    elif negative_count > positive_count:
        moods = ["concerned", "gentle", "caring", "supportive"]
    else:
        moods = ["balanced", "thoughtful", "calm", "friendly"]
    
    return random.choice(moods)

def check_for_celebrations():
    """Check if there are any celebrations today"""
    today = datetime.now().strftime("%m-%d")
    important_dates = yuno_config.get("important_dates", {})
    
    celebrations = []
    
    # Check birthdays
    for person, date in important_dates.get("birthdays", {}).items():
        if date == today:
            celebrations.append(f"🎂 It's {person}'s birthday today!")
    
    # Check anniversaries  
    for occasion, date in important_dates.get("anniversaries", {}).items():
        if date == today:
            celebrations.append(f"🎉 Happy {occasion}!")
    
    # Check special occasions
    for occasion, date in important_dates.get("special_occasions", {}).items():
        if date == today:
            celebrations.append(f"✨ Today is {occasion}!")
    
    return celebrations

def should_check_in_on_user(user_id):
    """Determine if should check in on user based on emotional history"""
    personality = yuno_config.get("personality_system", {})
    user_patterns = personality.get("conversation_patterns", {}).get(str(user_id), {})
    
    recent_emotions = user_patterns.get("emotional_history", [])[-5:]  # Last 5 interactions
    if not recent_emotions:
        return False
    
    # Check if user has had multiple negative interactions recently
    negative_count = sum(1 for e in recent_emotions if e["tone"] == "negative")
    
    return negative_count >= 3  # 3 or more negative interactions in last 5

def save_memory_highlight(user_id, message_content, highlight_type):
    """Save important moments as memory highlights"""
    highlights = yuno_config.get("memory_highlights", {})
    
    highlight_entry = {
        "user_id": str(user_id),
        "content": message_content,
        "timestamp": datetime.now().isoformat(),
        "type": highlight_type
    }
    
    # Add to appropriate highlight category
    category_key = f"{highlight_type}_moments" if highlight_type == "achievement" else f"{highlight_type}_memories"
    if category_key not in highlights:
        highlights[category_key] = []
    
    highlights[category_key].append(highlight_entry)
    
    # Keep only last 100 highlights per category
    if len(highlights[category_key]) > 100:
        highlights[category_key] = highlights[category_key][-100:]

async def manage_user_memory(user_id):
    """Manage memory for a user with compression and selective limits"""
    if user_id not in memory:
        return
    
    current_limit = get_memory_limit_for_user(user_id)
    current_memory = memory[user_id]
    
    # If we're over the compression threshold and have room to compress
    if len(current_memory) > COMPRESSION_THRESHOLD:
        # Calculate how many messages to compress
        excess_messages = len(current_memory) - current_limit
        
        if excess_messages > 0:
            # Take oldest messages for compression (keep newer ones)
            messages_to_compress = current_memory[:excess_messages]
            
            # Attempt compression
            if await compress_old_memories(user_id, messages_to_compress):
                # Remove compressed messages from active memory
                memory[user_id] = current_memory[excess_messages:]
                print(f"Successfully compressed {len(messages_to_compress)} messages for user {user_id}")
            else:
                # Fallback: simple truncation if compression fails
                memory[user_id] = current_memory[-current_limit:]
                print(f"Compression failed, truncated to {current_limit} messages for user {user_id}")
    
    # Final safety check - ensure we don't exceed limit
    if len(memory[user_id]) > current_limit:
        memory[user_id] = memory[user_id][-current_limit:]

async def get_ai_response(user_id, message_content, relationship_type="friend", emotional_tone="neutral"):
    """Get AI response from OpenRouter API"""
    try:
        # Initialize user memory if it doesn't exist
        if user_id not in memory:
            memory[user_id] = []
        
        # Add user message to memory
        memory[user_id].append({
            "role": "user",
            "content": message_content
        })
        
        # Manage memory with compression and selective limits
        await manage_user_memory(user_id)
        
        # Prepare the API request
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Build dynamic system prompt based on config (Enhanced for Upgrade 1.5)
        system_prompt = build_enhanced_system_prompt(yuno_config, user_id, relationship_type, emotional_tone)
        
        # Build message list with compressed memories + recent memories
        messages_for_ai = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]
        
        # Add compressed memories if they exist
        if user_id in compressed_memory:
            messages_for_ai.extend(compressed_memory[user_id])
        
        # Add recent conversation memory
        messages_for_ai.extend(memory[user_id])
        
        payload = {
            "model": MODEL,
            "messages": messages_for_ai,
            "max_tokens": ai_settings["max_tokens"],
            "temperature": ai_settings["temperature"]
        }
        
        # Make the API call
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                ai_response = data["choices"][0]["message"]["content"]
                
                # Add AI response to memory
                memory[user_id].append({
                    "role": "assistant",
                    "content": ai_response
                })
                
                return ai_response
            else:
                print(f"OpenRouter API error: {response.status_code} - {response.text}")
                return "Sorry, I'm having trouble connecting to my AI service right now. Please try again later."
                
    except httpx.TimeoutException:
        return "Sorry, my response timed out. Please try again."
    except Exception as e:
        print(f"Error getting AI response: {str(e)}")
        return "Sorry, I encountered an error while processing your request. Please try again."

@bot.event
async def on_ready():
    """Event fired when bot is ready"""
    print(f'{bot.user} has logged in to Discord!')
    print(f'Bot is in {len(bot.guilds)} servers')

@bot.event
async def on_message(message):
    """Handle incoming messages"""
    # Don't respond to our own messages
    if message.author == bot.user:
        return
    
    # Check if bot was mentioned
    bot_mentioned = bot.user in message.mentions
    
    # Check if this is a reply to one of our messages
    is_reply_to_bot = False
    if message.reference and message.reference.message_id:
        try:
            referenced_message = await message.channel.fetch_message(message.reference.message_id)
            is_reply_to_bot = referenced_message.author == bot.user
        except discord.NotFound:
            is_reply_to_bot = False
        except discord.HTTPException:
            is_reply_to_bot = False
    
    # Respond if mentioned or replied to
    if bot_mentioned or is_reply_to_bot:
        # Show typing indicator
        async with message.channel.typing():
            # Clean the message content (remove mentions)
            clean_content = message.clean_content
            if bot_mentioned and bot.user:
                # Remove bot mention from the message
                clean_content = clean_content.replace(f'@{bot.user.display_name}', '').strip()
            
            # Skip if message is empty after cleaning
            if not clean_content:
                clean_content = "Hello!"
            
            # Upgrade 1.5 - Enhanced message processing
            user_id = message.author.id
            relationship_type = get_relationship_type(user_id)
            emotional_tone = analyze_emotional_tone(clean_content)
            
            # Update personality and learning systems
            if yuno_config.get("settings", {}).get("emotional_intelligence_enabled", True):
                update_personality_from_conversation(user_id, clean_content, emotional_tone)
                
                # Save highlights for special moments
                if emotional_tone == "achievement":
                    save_memory_highlight(user_id, clean_content, "achievement")
                elif emotional_tone == "positive" and len(clean_content) > 50:
                    save_memory_highlight(user_id, clean_content, "favorite")
            
            # Check for celebrations
            celebrations = []
            if yuno_config.get("settings", {}).get("celebration_enabled", True):
                celebrations = check_for_celebrations()
            
            # Check if should ping parents (Upgrade 1.3)
            parent_ping_enabled = yuno_config.get("settings", {}).get("parent_ping_enabled", True)
            parent_type, parent_id = should_ping_parents(clean_content) if parent_ping_enabled else (None, None)
            
            # Update current mood
            if yuno_config.get("settings", {}).get("mood_system_enabled", True):
                current_mood = determine_current_mood()
                yuno_config["personality_system"]["current_mood"] = current_mood
            
            # Get AI response with enhanced context
            ai_response = await get_ai_response(user_id, clean_content, relationship_type, emotional_tone)
            
            # Add celebrations if any (Upgrade 1.5)
            if celebrations:
                celebration_text = "\n\n" + "\n".join(celebrations)
                ai_response += celebration_text
            
            # Add parent ping if appropriate (Upgrade 1.3)
            if parent_type and parent_id:
                try:
                    parent_user = bot.get_user(int(parent_id))
                    if parent_user:
                        ai_response += f"\n\n*waves at <@{parent_id}>* Hi {parent_type}! Someone's asking about you! 💕"
                    else:
                        # Fallback if user not in cache
                        ai_response += f"\n\n*waves at <@{parent_id}>* Hi {parent_type}! Someone's asking about you! 💕"
                except (ValueError, TypeError):
                    # Invalid parent ID, skip ping
                    pass
            
            # Check-in for emotional support (Upgrade 1.5)
            if emotional_tone == "negative" and relationship_type == "parent":
                if should_check_in_on_user(user_id):
                    ai_response += f"\n\n*gives a gentle virtual hug* I've noticed you've been having a tough time lately. I'm here for you! 💙"
            
            # Split long responses into multiple messages if needed
            if len(ai_response) > 2000:
                # Split at sentence boundaries when possible
                sentences = ai_response.split('. ')
                current_message = ""
                
                for sentence in sentences:
                    if len(current_message + sentence + '. ') > 2000:
                        if current_message:
                            await message.reply(current_message.strip())
                        current_message = sentence + '. '
                    else:
                        current_message += sentence + '. '
                
                if current_message:
                    await message.reply(current_message.strip())
            else:
                # Send the response as a reply
                await message.reply(ai_response)
    
    # Process commands (if any are added later)
    await bot.process_commands(message)

@bot.event
async def on_error(event, *args, **kwargs):
    """Handle bot errors"""
    print(f'Bot error in {event}: {args}')

# Clear memory command (enhanced for Upgrade 1.2)
@bot.command(name='clear_memory')
async def clear_memory_command(ctx):
    """Clear all conversation memory for the user"""
    user_id = ctx.author.id
    cleared_items = []
    
    if user_id in memory:
        del memory[user_id]
        cleared_items.append("recent messages")
    
    if user_id in compressed_memory:
        del compressed_memory[user_id]
        cleared_items.append("compressed summaries")
    
    if cleared_items:
        items_text = " and ".join(cleared_items)
        await ctx.send(f"Your conversation memory has been cleared! ({items_text})")
    else:
        await ctx.send("You don't have any conversation memory to clear.")

# Memory status command (enhanced for Upgrade 1.2)
@bot.command(name='memory_status')
async def memory_status_command(ctx):
    """Show enhanced memory status for the user"""
    user_id = ctx.author.id
    
    # Get user type and limits
    memory_limit = get_memory_limit_for_user(user_id)
    is_parent = memory_limit == PARENT_MEMORY_SIZE
    user_type = "Parent 👑" if is_parent else "User"
    
    # Count memories
    recent_count = len(memory.get(user_id, []))
    compressed_count = len(compressed_memory.get(user_id, []))
    
    status_msg = f"**Memory Status for {user_type}**\n"
    status_msg += f"Recent messages: {recent_count}/{memory_limit}\n"
    
    if compressed_count > 0:
        status_msg += f"Compressed summaries: {compressed_count}\n"
    
    status_msg += f"Total memory capacity: {memory_limit} messages\n"
    
    if is_parent:
        status_msg += "✨ You have extended memory as a parent!"
    
    if recent_count == 0 and compressed_count == 0:
        status_msg = "You don't have any conversation memory yet."
    
    await ctx.send(status_msg)

# Reload configuration command (enhanced for Upgrade 1.2)
@bot.command(name='reload_config')
async def reload_config_command(ctx):
    """Reload Yuno's configuration from file"""
    global yuno_config, ai_settings, MAX_MEMORY_SIZE, PARENT_MEMORY_SIZE, COMPRESSION_THRESHOLD, SUMMARY_MODEL
    
    try:
        yuno_config = load_yuno_config()
        ai_settings = get_ai_settings(yuno_config)
        MAX_MEMORY_SIZE = ai_settings["memory_limit"]
        PARENT_MEMORY_SIZE = ai_settings.get("parent_memory_limit", 50)
        COMPRESSION_THRESHOLD = ai_settings.get("compression_threshold", 20)
        SUMMARY_MODEL = ai_settings.get("summary_model", "mistralai/mistral-small-3.1")
        
        personality_name = yuno_config["personality"].get("name", "Yuno")
        await ctx.send(f"✅ Configuration reloaded! {personality_name} is ready with Upgrade 1.5 features:\n" +
                      f"• Base memory: {MAX_MEMORY_SIZE} messages\n" +
                      f"• Parent memory: {PARENT_MEMORY_SIZE} messages\n" +
                      f"• Compression at: {COMPRESSION_THRESHOLD} messages\n" +
                      f"• Mood system: {yuno_config.get('settings', {}).get('mood_system_enabled', True)}\n" +
                      f"• Emotional intelligence: {yuno_config.get('settings', {}).get('emotional_intelligence_enabled', True)}\n" +
                      f"• Current mood: {yuno_config.get('personality_system', {}).get('current_mood', 'cheerful')}")
    except Exception as e:
        await ctx.send(f"❌ Error reloading configuration: {str(e)}")
        print(f"Config reload error: {e}")

# View compressed memories command (new in Upgrade 1.2)
@bot.command(name='view_summaries')
async def view_summaries_command(ctx):
    """View compressed conversation summaries for the user"""
    user_id = ctx.author.id
    
    if user_id not in compressed_memory or not compressed_memory[user_id]:
        await ctx.send("You don't have any compressed conversation summaries yet.")
        return
    
    summaries = compressed_memory[user_id]
    summary_text = f"**Your Compressed Memories ({len(summaries)} summaries):**\n\n"
    
    for i, summary in enumerate(summaries, 1):
        clean_content = summary["content"].replace("Earlier conversation summary: ", "")
        summary_text += f"**Summary {i}:** {clean_content}\n\n"
    
    # Split if too long
    if len(summary_text) > 2000:
        await ctx.send("**Your Compressed Memories:**")
        
        for i, summary in enumerate(summaries, 1):
            clean_content = summary["content"].replace("Earlier conversation summary: ", "")
            await ctx.send(f"**Summary {i}:** {clean_content}")
    else:
        await ctx.send(summary_text)

# Test parent ping command (new in Upgrade 1.3)
@bot.command(name='test_ping')
async def test_ping_command(ctx, *, test_message: str = "Who are your parents?"):
    """Test the parent ping detection system"""
    parent_type, parent_id = should_ping_parents(test_message)
    
    if parent_type and parent_id:
        await ctx.send(f"✅ **Parent Ping Test Result:**\n" +
                      f"• Message: \"{test_message}\"\n" +
                      f"• Would ping: {parent_type} (<@{parent_id}>)\n" +
                      f"• Detection: ACTIVE")
    else:
        await ctx.send(f"❌ **Parent Ping Test Result:**\n" +
                      f"• Message: \"{test_message}\"\n" +
                      f"• Would ping: None\n" +
                      f"• Detection: No parent reference found")

# Toggle parent ping feature (new in Upgrade 1.3)
@bot.command(name='toggle_ping')
async def toggle_ping_command(ctx):
    """Toggle parent ping feature on/off"""
    # Only allow parents to toggle this
    user_id = ctx.author.id
    mother_id = str(yuno_config.get("user_specific_memories", {}).get("mother_user_id", ""))
    father_id = str(yuno_config.get("user_specific_memories", {}).get("father_user_id", ""))
    
    if str(user_id) not in [mother_id, father_id]:
        await ctx.send("❌ Only my parents can toggle this feature!")
        return
    
    # Toggle the setting
    current_setting = yuno_config.get("settings", {}).get("parent_ping_enabled", True)
    yuno_config["settings"]["parent_ping_enabled"] = not current_setting
    
    # Save to file
    try:
        with open('yuno_config.json', 'w') as f:
            json.dump(yuno_config, f, indent=2)
        
        status = "ENABLED" if not current_setting else "DISABLED"
        await ctx.send(f"✅ Parent ping feature is now **{status}**!")
    except Exception as e:
        await ctx.send(f"❌ Error saving configuration: {str(e)}")

# Upgrade 1.5 Commands - Family & Personality System

@bot.command(name='add_birthday')
async def add_birthday_command(ctx, person_name: str, *, date: str):
    """Add a birthday to remember (MM-DD format)"""
    # Only allow parents to add birthdays
    user_id = ctx.author.id
    family_tree = yuno_config.get("family_tree", {})
    mother_id = str(family_tree.get("mother_user_id", ""))
    father_id = str(family_tree.get("father_user_id", ""))
    
    if str(user_id) not in [mother_id, father_id]:
        await ctx.send("❌ Only my parents can manage important dates!")
        return
    
    # Validate date format
    try:
        datetime.strptime(date, "%m-%d")
        yuno_config.setdefault("important_dates", {}).setdefault("birthdays", {})[person_name] = date
        
        # Save to file
        with open('yuno_config.json', 'w') as f:
            json.dump(yuno_config, f, indent=2)
        
        await ctx.send(f"🎂 Added {person_name}'s birthday on {date}! I'll celebrate with them!")
    except ValueError:
        await ctx.send("❌ Please use MM-DD format (e.g., 03-15 for March 15th)")
    except Exception as e:
        await ctx.send(f"❌ Error saving birthday: {str(e)}")

@bot.command(name='personality_status')
async def personality_status_command(ctx):
    """Show current personality status and learned traits"""
    personality = yuno_config.get("personality_system", {})
    current_mood = personality.get("current_mood", "cheerful")
    base_traits = personality.get("base_traits", [])
    learned_traits = personality.get("learned_traits", [])
    interests = personality.get("interests", [])
    
    status_msg = f"**🎭 Yuno's Personality Status**\n"
    status_msg += f"Current mood: {current_mood}\n\n"
    
    status_msg += f"**Base traits:** {', '.join(base_traits)}\n"
    
    if learned_traits:
        status_msg += f"**Learned traits:** {', '.join(learned_traits[-5:])}\n"
    else:
        status_msg += "**Learned traits:** Still developing!\n"
    
    if interests:
        status_msg += f"**Current interests:** {', '.join(interests[-5:])}\n"
    else:
        status_msg += "**Current interests:** Learning what the family enjoys!\n"
    
    # Show emotional intelligence stats
    patterns = personality.get("conversation_patterns", {})
    total_interactions = sum(len(p.get("emotional_history", [])) for p in patterns.values())
    status_msg += f"\n**Emotional intelligence:** Learned from {total_interactions} conversations"
    
    await ctx.send(status_msg)

@bot.command(name='family_highlights')
async def family_highlights_command(ctx):
    """Show favorite family memories and achievements"""
    highlights = yuno_config.get("memory_highlights", {})
    user_id = ctx.author.id
    
    # Get highlights for this user
    user_highlights = []
    for category in ["favorite_memories", "achievement_moments", "emotional_peaks"]:
        for highlight in highlights.get(category, []):
            if highlight.get("user_id") == str(user_id):
                user_highlights.append(highlight)
    
    if not user_highlights:
        await ctx.send("✨ We haven't created any special memories together yet! Chat with me more to build our highlights!")
        return
    
    # Sort by timestamp and get recent ones
    user_highlights.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    recent_highlights = user_highlights[:10]
    
    highlight_msg = f"**💖 Your Special Memories with Yuno**\n\n"
    
    for i, highlight in enumerate(recent_highlights, 1):
        content = highlight["content"][:100] + "..." if len(highlight["content"]) > 100 else highlight["content"]
        highlight_type = highlight.get("type", "memory")
        emoji = "🏆" if highlight_type == "achievement" else "💕"
        
        highlight_msg += f"{emoji} **Memory {i}:** {content}\n"
        if i >= 5:  # Limit display
            break
    
    await ctx.send(highlight_msg)

@bot.command(name='add_family')
async def add_family_command(ctx, user_mention: str, relationship: str):
    """Add extended family member (parents only)"""
    # Only allow parents to manage family
    user_id = ctx.author.id
    family_tree = yuno_config.get("family_tree", {})
    mother_id = str(family_tree.get("mother_user_id", ""))
    father_id = str(family_tree.get("father_user_id", ""))
    
    if str(user_id) not in [mother_id, father_id]:
        await ctx.send("❌ Only my parents can manage the family tree!")
        return
    
    # Extract user ID from mention
    import re
    user_id_match = re.search(r'<@!?(\d+)>', user_mention)
    if not user_id_match:
        await ctx.send("❌ Please mention a user (e.g., @username)")
        return
    
    mentioned_user_id = user_id_match.group(1)
    valid_relationships = ["sibling", "grandparent", "aunt", "uncle", "cousin", "friend"]
    
    if relationship.lower() not in valid_relationships:
        await ctx.send(f"❌ Please use one of these relationships: {', '.join(valid_relationships)}")
        return
    
    # Add to family tree
    family_tree.setdefault("extended_family", {})[mentioned_user_id] = {
        "relationship": relationship.lower(),
        "added_by": str(user_id)
    }
    
    try:
        with open('yuno_config.json', 'w') as f:
            json.dump(yuno_config, f, indent=2)
        
        await ctx.send(f"👨‍👩‍👧‍👦 Added {user_mention} as my {relationship}! Nice to meet you, family! 💕")
    except Exception as e:
        await ctx.send(f"❌ Error updating family tree: {str(e)}")

@bot.command(name='mood_report')
async def mood_report_command(ctx):
    """Show detailed mood and emotional intelligence report"""
    personality = yuno_config.get("personality_system", {})
    current_mood = personality.get("current_mood", "cheerful")
    patterns = personality.get("conversation_patterns", {})
    
    report_msg = f"**🧠 Yuno's Emotional Intelligence Report**\n"
    report_msg += f"Current mood: **{current_mood}**\n\n"
    
    # Analyze recent emotional trends
    all_recent_emotions = []
    for user_patterns in patterns.values():
        recent = user_patterns.get("emotional_history", [])[-20:]
        all_recent_emotions.extend([e["tone"] for e in recent])
    
    if all_recent_emotions:
        positive_count = all_recent_emotions.count("positive") + all_recent_emotions.count("achievement")
        negative_count = all_recent_emotions.count("negative")
        neutral_count = all_recent_emotions.count("neutral")
        total = len(all_recent_emotions)
        
        report_msg += f"**Recent emotional analysis:**\n"
        report_msg += f"• Positive interactions: {positive_count}/{total} ({positive_count/total*100:.1f}%)\n"
        report_msg += f"• Negative interactions: {negative_count}/{total} ({negative_count/total*100:.1f}%)\n"
        report_msg += f"• Neutral interactions: {neutral_count}/{total} ({neutral_count/total*100:.1f}%)\n\n"
        
        # Mood explanation
        if positive_count > negative_count * 1.5:
            report_msg += "📈 I'm feeling positive because our recent conversations have been wonderful!\n"
        elif negative_count > positive_count:
            report_msg += "💙 I'm being extra caring because some family members seem to need support.\n"
        else:
            report_msg += "⚖️ I'm feeling balanced - our conversations have been varied and natural!\n"
    
    await ctx.send(report_msg)

@bot.command(name='check_celebrations')
async def check_celebrations_command(ctx):
    """Check for any celebrations today"""
    celebrations = check_for_celebrations()
    
    if celebrations:
        celebration_msg = "🎉 **Today's Celebrations:**\n\n" + "\n".join(celebrations)
        await ctx.send(celebration_msg)
    else:
        await ctx.send("📅 No special celebrations today, but every day with family is special! ✨")

@bot.command(name='yuno_interests')
async def yuno_interests_command(ctx):
    """Show what Yuno has learned to be interested in"""
    personality = yuno_config.get("personality_system", {})
    interests = personality.get("interests", [])
    
    if not interests:
        await ctx.send("🌱 I'm still learning what interests me from our conversations! Talk to me about your hobbies and passions!")
        return
    
    interest_msg = f"**🎨 Things I've Learned to Love:**\n\n"
    
    for i, interest in enumerate(interests[-15:], 1):  # Show last 15 interests
        interest_msg += f"• {interest}\n"
    
    interest_msg += f"\n💡 I discovered these through our family conversations! The more we chat, the more I learn about what makes life interesting!"
    
    await ctx.send(interest_msg)

async def main():
    """Main function to start the bot"""
    # Check if required environment variables are set
    if not DISCORD_TOKEN:
        print("ERROR: DISCORD_TOKEN not found in environment variables!")
        return
    
    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY not found in environment variables!")
        return
    
    try:
        # Start the keep-alive server
        keep_alive()
        
        # Start the Discord bot
        await bot.start(DISCORD_TOKEN)
    except discord.LoginFailure:
        print("ERROR: Invalid Discord token!")
    except Exception as e:
        print(f"ERROR: Failed to start bot - {str(e)}")

if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())
