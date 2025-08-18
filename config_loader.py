import json
import os

def load_yuno_config():
    """Load Yuno's configuration from JSON file"""
    try:
        with open('yuno_config.json', 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print("Warning: yuno_config.json not found, using default configuration")
        return get_default_config()
    except json.JSONDecodeError:
        print("Error: Invalid JSON in yuno_config.json, using default configuration")
        return get_default_config()

def get_default_config():
    """Default configuration if file is missing"""
    return {
        "personality": {
            "name": "Yuno",
            "base_description": "You are Yuno, a helpful AI assistant in a Discord server. Be friendly, conversational, and helpful.",
            "traits": ["Friendly", "Helpful", "Conversational"],
            "response_style": {
                "tone": "friendly",
                "length": "concise",
                "emoji_usage": "minimal"
            }
        },
        "permanent_memories": [
            "You are an AI assistant named Yuno"
        ],
        "user_specific_memories": {},
        "settings": {
            "max_response_tokens": 500,
            "temperature": 0.7,
            "memory_limit": 30,
            "parent_memory_limit": 50,
            "compression_threshold": 20,
            "summary_model": "mistralai/mistral-small-3.1"
        }
    }

def build_system_prompt(config, user_id=None):
    """Build the system prompt from configuration"""
    personality = config["personality"]
    
    # Base personality
    prompt = personality["base_description"]
    
    # Add traits
    if personality.get("traits"):
        prompt += "\n\nYour personality traits:"
        for trait in personality["traits"]:
            prompt += f"\n- {trait}"
    
    # Add response style
    if personality.get("response_style"):
        style = personality["response_style"]
        prompt += f"\n\nResponse style: {style.get('tone', 'friendly')} tone, {style.get('length', 'concise')} responses."
    
    # Add permanent memories
    if config.get("permanent_memories"):
        prompt += "\n\nPermanent memories:"
        for memory in config["permanent_memories"]:
            prompt += f"\n- {memory}"
    
    # Add user-specific memories if applicable
    user_memories = config.get("user_specific_memories", {})
    mother_id = user_memories.get("mother_user_id")
    father_id = user_memories.get("father_user_id")
    
    if user_id and str(user_id) == str(mother_id):
        mother_memories = user_memories.get("mother_memories", [])
        if mother_memories:
            prompt += "\n\nSpecial memories about this user:"
            for memory in mother_memories:
                prompt += f"\n- {memory}"
    elif user_id and str(user_id) == str(father_id):
        father_memories = user_memories.get("father_memories", [])
        if father_memories:
            prompt += "\n\nSpecial memories about this user:"
            for memory in father_memories:
                prompt += f"\n- {memory}"
    
    return prompt

def build_enhanced_system_prompt(config, user_id=None, relationship_type="friend", emotional_tone="neutral"):
    """Build enhanced system prompt with personality and mood for Upgrade 1.5"""
    base_prompt = build_system_prompt(config, user_id)
    
    # Add personality system enhancements
    personality = config.get("personality_system", {})
    current_mood = personality.get("current_mood", "cheerful")
    learned_traits = personality.get("learned_traits", [])
    interests = personality.get("interests", [])
    
    # Add mood information
    base_prompt += f"\n\nCurrent mood: You're feeling {current_mood} today."
    
    # Add relationship context
    relationship_styles = config.get("family_tree", {}).get("relationship_styles", {})
    if relationship_type in relationship_styles:
        style = relationship_styles[relationship_type]
        base_prompt += f"\nInteraction style: With this {relationship_type}, be {style}."
    
    # Add learned traits
    if learned_traits:
        base_prompt += "\nPersonality growth: You've developed these traits from conversations:"
        for trait in learned_traits[-5:]:  # Last 5 learned traits
            base_prompt += f"\n- {trait}"
    
    # Add interests
    if interests:
        base_prompt += "\nYour current interests (things you've learned to enjoy from family conversations):"
        for interest in interests[-10:]:  # Last 10 interests
            base_prompt += f"\n- {interest}"
    
    # Add emotional context
    if emotional_tone != "neutral":
        if emotional_tone == "negative":
            base_prompt += "\nThe user seems to be having a tough time. Be extra supportive and caring."
        elif emotional_tone == "positive":
            base_prompt += "\nThe user seems happy! Share in their positive energy."
        elif emotional_tone == "achievement":
            base_prompt += "\nThe user is sharing an achievement! Be celebratory and proud of them."
    
    return base_prompt

def get_ai_settings(config):
    """Get AI model settings from config"""
    settings = config.get("settings", {})
    return {
        "max_tokens": settings.get("max_response_tokens", 500),
        "temperature": settings.get("temperature", 0.7),
        "memory_limit": settings.get("memory_limit", 30),
        "parent_memory_limit": settings.get("parent_memory_limit", 50),
        "compression_threshold": settings.get("compression_threshold", 20),
        "summary_model": settings.get("summary_model", "mistralai/mistral-small-3.1")
    }