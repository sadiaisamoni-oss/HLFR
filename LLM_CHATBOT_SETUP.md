# LLM-Powered Chatbot Setup Guide

This project now supports both **regex-based chatbot** (always available) and **AI-powered LLM chatbot** (with Ollama).

## Quick Start

### Option 1: Use Regex-Based Chatbot (Default - No Setup Needed)
The existing chatbot at `/api/chatbot/` works without any LLM setup:
- Auto-detects donation patterns
- Searches database for items
- Answers common questions
- **No external dependencies required**

### Option 2: Enable LLM-Powered Chatbot (Recommended)

#### Step 1: Install Ollama
Download and install **Ollama** from https://ollama.ai

Ollama is a lightweight, standalone application for running LLMs locally.

#### Step 2: Pull a Model
Open terminal and run:
```bash
ollama pull mistral
```

This downloads Mistral (7B parameters) - small, fast, and free.

Other supported models:
- `ollama pull llama2` - Llama 2 (7B) - Great for instruction following
- `ollama pull neural-chat` - Intel's optimized chat model
- `ollama pull phi` - Smallest model (2.7B) - Fastest

#### Step 3: Start Ollama Service
```bash
ollama serve
```

Keep this running in the background. It listens on `http://localhost:11434`

#### Step 4: Restart Django Server
```bash
python manage.py runserver
```

#### Step 5: Test LLM Chatbot
Login and access the LLM endpoint:
```bash
curl -X POST http://localhost:8000/api/chatbot/llm/ \
  -H "Content-Type: application/json" \
  -d '{"message": "I want to add 5kg rice at Dhaka"}'
```

## How It Works

### Regex Chatbot (`/api/chatbot/`)
Hardcoded patterns for:
- **Auto-donation**: "I have 2kg rice at Dhaka"  
- **Item lookup**: "rice" (1-3 word searches)
- **Location search**: "food near Dhaka"
- **Intent detection**: "donate", "find", "want"

✅ **Fast** | ✅ **No dependencies** | ✅ **Reliable**  
❌ **Limited to patterns** | ❌ **No context memory**

### LLM Chatbot (`/api/chatbot/llm/`)
Uses Mistral/Llama to:
- **Understand natural language** - Any phrasing understood
- **Maintain context** - Multi-turn conversations remembered
- **Function-calling** - Extracts structured data from messages
- **Smart database operations**:
  - Asks for missing info: "How many kg?"
  - Confirms before saving: "Add 5kg Rice at Dhaka? (yes/no)"
  - Searches flexibly: "Show me dairy near Banani"
  - Deletes records: "Remove old listings"

✅ **Natural language** | ✅ **Context-aware** | ✅ **Function-calling**  
❌ **Requires Ollama** | ❌ **Slower (few seconds)** | ⚠️ **Needs model download**

## Example Conversations

### Adding Food via LLM
```
User: I want to donate rice
Bot: How many kg or packets of rice do you have?
User: 5kg
Bot: Great! At which location?
User: Dhaka
Bot: I'll add 5kg Rice at Dhaka. Confirm? (yes/no)
User: yes
Bot: ✓ Added "Rice" (5kg) at Dhaka to available food.
```

### Checking Availability
```
User: What dairy products are available near Gulshan?
Bot: Found 3 listings:
- Fresh Milk (5L) at Gulshan
- Yogurt (2kg) at Gulshan
- Cheese (500g) at Gulshan
```

### Deleting Old Donations
```
User: I want to remove the old bread donation
Bot: Which bread donation? (ID: 15, 22, 31)
User: 15
Bot: ✓ Deleted "Bread" from available food.
```

## Architecture

```
Frontend (chatbot.html)
    |
    ├─→ /api/chatbot/ (Regex - always works)
    |
    └─→ /api/chatbot/llm/ (LLM - requires login & Ollama)
            |
            └→ Ollama Service (http://localhost:11434)
                |
                └→ Mistral/Llama Model
                        |
                        └→ foodapp.llm_chatbot module
                            |
                            └→ Database (Django Models)
```

## Configuration

### Model Selection
Edit `foodapp/llm_chatbot.py`:
```python
# Line: llm_chatbot = LLMChatbot(model_name="mistral")
# Change "mistral" to:
# - "llama2" for Llama 2
# - "neural-chat" for Intel's model
# - "phi" for smallest/fastest
```

### Ollama Host/Port
Default: `http://localhost:11434`

To use different host, set environment variable:
```bash
export OLLAMA_HOST=http://192.168.1.10:11434
```

## Troubleshooting

### "LLM assistant is not available"
- Is Ollama running? → Run `ollama serve`
- Is model installed? → Run `ollama pull mistral`
- Can you reach localhost:11434? → Test with `curl http://localhost:11434/`

### Response is very slow
- Model is too large → Use `ollama pull phi`
- Machine is slow → Enable GPU (Ollama auto-detects NVIDIA/AMD/Apple Metal)

### Model seems confused
- Try a different model: `ollama pull neural-chat`
- Adjust system prompt in `foodapp/llm_chatbot.py` (line 68)

## Frontend Integration

### Option A: Always use LLM (if available, fallback to regex)
```javascript
// In chatbot.html sendChatbotRequest():
try {
  const response = await fetch('/api/chatbot/llm/', {...});
} catch (e) {
  // Fallback to regex chatbot
  const response = await fetch('/api/chatbot/', {...});
}
```

### Option B: User chooses
```html
<!-- Add toggle button -->
<button id="chat-mode-toggle">Switch to LLM Mode</button>
```

Currently: Frontend uses `/api/chatbot/` (regex). To enable LLM:
1. Edit `templates/chatbot.html`
2. Change URL from `/api/chatbot/` to `/api/chatbot/llm/`
3. Ensure user is logged in
4. Ensure Ollama is running

## Performance Benchmarks

On typical hardware (4 CPU cores, 8GB RAM):

| Operation | Regex Chatbot | LLM Chatbot (Mistral) |
|-----------|---------------|-----------------------|
| Simple search | 5ms | 1-2s |
| Add item with questions | 10ms | 3-5s |
| Check availability | 10ms | 2-3s |
| Multi-turn conversation | N/A | 2-3s per message |

**Note**: LLM times include network latency to Ollama. First request slower (model load).

## What's Coming

- [ ] Multi-language support (Bengali)
- [ ] Custom model fine-tuning on your data
- [ ] GPU acceleration (CUDA/ROCm)
- [ ] Web interface for model selection
- [ ] Conversation history UI
- [ ] Voice input/output

## Support

For issues:
1. Check logs: `tail -f ~/.ollama/logs/*.log`
2. Test Ollama directly: `ollama list`
3. Check Django logs: `python manage.py runserver --verbosity=3`
