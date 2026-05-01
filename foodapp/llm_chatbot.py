"""
LLM-powered chatbot using Ollama for database interactions.
Supports function-calling pattern for add_food, delete_food, check_availability.
"""
import json
import logging
import re
from typing import Optional, Dict, Any, List, Tuple
from django.db.models import Q
from foodapp.models import Donation

logger = logging.getLogger('foodapp.llm_chatbot')

# Category mapping for auto-detection
CATEGORY_KEYWORDS = {
    'dairy': ['milk', 'cheese', 'butter', 'yogurt', 'egg', 'eggs', 'dairy'],
    'bakery': ['bread', 'cake', 'cookie', 'cookies', 'pastry', 'bakery'],
    'produce': ['rice', 'potato', 'vegetable', 'fruit', 'produce', 'carrot', 'apple', 'banana', 'tomato', 'onion'],
    'prepared': ['cooked', 'meal', 'rice', 'curry', 'prepared', 'cooked rice'],
}

def detect_category(food_name: str) -> str:
    """Detect food category from name"""
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in food_name.lower() for kw in keywords):
            return cat
    return 'other'


class ChatbotState:
    """Manages conversation state for multi-turn interactions"""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.conversation_history: List[Dict[str, str]] = []
        self.pending_action: Optional[str] = None  # 'add_food', 'delete_food', 'check_availability'
        self.pending_data: Dict[str, Any] = {}  # Collected data for pending action
        
    def add_message(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({'role': role, 'content': content})
    
    def get_context(self) -> str:
        """Format conversation history for LLM context"""
        lines = []
        for msg in self.conversation_history[-10:]:  # Last 10 messages
            lines.append(f"{msg['role'].upper()}: {msg['content']}")
        return '\n'.join(lines)
    
    def set_pending_action(self, action: str, data: Dict[str, Any] = None):
        """Set an action waiting for user confirmation"""
        self.pending_action = action
        self.pending_data = data or {}


class LLMChatbot:
    """LLM-based chatbot with function calling"""
    
    def __init__(self, model_name: str = "mistral"):
        """Initialize chatbot with model name (must be installed in Ollama)"""
        self.model_name = model_name
        self.sessions: Dict[str, ChatbotState] = {}
        
    def _try_import_ollama(self):
        """Try to import ollama, with helpful error if not installed"""
        try:
            import ollama
            return ollama
        except ImportError:
            raise ImportError(
                "Ollama not installed. Download from https://ollama.ai\n"
                "Then run: ollama pull mistral\n"
                "And ensure ollama serve is running on localhost:11434"
            )
    
    def get_session(self, session_id: str) -> ChatbotState:
        """Get or create a conversation session"""
        if session_id not in self.sessions:
            self.sessions[session_id] = ChatbotState(session_id)
        return self.sessions[session_id]
    
    def _build_system_prompt(self) -> str:
        """Build system prompt instructing LLM on food donation operations"""
        return """You are a helpful Food Donation Assistant. You help users:
1. Add food donations (need: food_name, quantity, location)
2. Check food availability (search donations by name or location)
3. Delete old/expired donations

When a user wants to:
- ADD FOOD: Politely ask for missing fields (food name, quantity, location). Once you have all info, ask for confirmation before saving.
  Respond with JSON: {"action": "add_food_confirm", "food_name": "...", "quantity": "...", "location": "..."}
  
- CHECK AVAILABILITY: Search the database and list results. 
  Respond with JSON: {"action": "check_availability", "search_term": "..."}
  
- DELETE FOOD: Ask for confirmation, then respond with JSON: {"action": "delete_food", "donation_id": ...}

For other questions: respond naturally and helpfully.

IMPORTANT: Always be concise and clear. Ask ONE clarifying question at a time. Use JSON only when you're ready to execute an action."""

    def _extract_json_action(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON action from LLM response if present"""
        # Look for JSON pattern in response
        json_match = re.search(r'\{.*?"action".*?\}', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return None
    
    def process_message(self, user_message: str, session_id: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Process user message and return (reply, action_dict).
        action_dict contains action details if LLM decided to perform an action.
        """
        session = self.get_session(session_id)
        session.add_message('user', user_message)
        
        try:
            ollama = self._try_import_ollama()
            
            # Build context
            system_prompt = self._build_system_prompt()
            messages = [
                {'role': 'system', 'content': system_prompt},
                *session.conversation_history
            ]
            
            # Call LLM
            response = ollama.chat(
                model=self.model_name,
                messages=messages,
                stream=False,
            )
            
            llm_reply = response['message']['content']
            session.add_message('assistant', llm_reply)
            
            # Extract action if present
            action = self._extract_json_action(llm_reply)
            
            # Clean response (remove JSON if present)
            clean_reply = re.sub(r'\{.*?"action".*?\}', '', llm_reply, flags=re.DOTALL).strip()
            
            return clean_reply, action
            
        except ImportError as e:
            logger.error(f"LLM unavailable: {e}")
            return f"Sorry, the AI assistant is not available. {str(e)}", None
        except Exception as e:
            logger.exception("Error in LLM processing")
            return f"Sorry, something went wrong: {str(e)}", None
    
    def handle_action(self, action: Dict[str, Any], user_id: Optional[int] = None) -> str:
        """Execute database operation based on LLM action"""
        action_type = action.get('action')
        
        try:
            if action_type == 'add_food_confirm':
                food_name = action.get('food_name', '').strip()
                quantity = action.get('quantity', '').strip()
                location = action.get('location', '').strip()
                
                if not all([food_name, quantity, location]):
                    return "Missing required fields (food_name, quantity, location)"
                
                category = detect_category(food_name)
                donation = Donation.objects.create(
                    food_name=food_name.title(),
                    category=category,
                    quantity=quantity,
                    location=location.title(),
                    donor_name='LLM Entry',
                    is_mine=True,
                    status='confirmed',
                    user_id=user_id
                )
                logger.info(f'LLM-created donation: {donation.id} - {donation.food_name}')
                return f'✓ Added "{food_name}" ({quantity}) at {location} to available food.'
            
            elif action_type == 'check_availability':
                search_term = action.get('search_term', '').strip()
                if not search_term:
                    return "What food or location would you like to search for?"
                
                donations = Donation.objects.filter(is_mine=True).exclude(status='cancelled').filter(
                    Q(food_name__icontains=search_term) | 
                    Q(location__icontains=search_term) |
                    Q(category__icontains=search_term)
                ).order_by('-created_at')[:5]
                
                if not donations:
                    return f"No listings found for '{search_term}'. Try another search term."
                
                results = []
                for d in donations:
                    results.append(f'- {d.food_name} ({d.quantity}) at {d.location}')
                return f"Found {len(results)} listing(s):\n" + '\n'.join(results)
            
            elif action_type == 'delete_food':
                donation_id = action.get('donation_id')
                try:
                    donation = Donation.objects.get(id=donation_id, is_mine=True)
                    food_name = donation.food_name
                    donation.delete()
                    logger.info(f'LLM-deleted donation: {donation_id}')
                    return f"✓ Deleted '{food_name}' from available food."
                except Donation.DoesNotExist:
                    return "Donation not found or you don't have permission to delete it."
            
            else:
                return f"Unknown action: {action_type}"
                
        except Exception as e:
            logger.exception(f"Error handling action {action_type}")
            return f"Error: {str(e)}"


# Global chatbot instance
llm_chatbot = LLMChatbot(model_name="mistral")
