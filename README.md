# Local Gmail AI Assistant

A Python assistant that watches your Gmail inbox, reads important emails aloud, and helps you reply using voice input or AI-generated drafts.

## Features
- Watches selected senders or domains
- Summarizes incoming emails
- Reads email summaries using local text-to-speech
- Prompts for permission to send an AI-generated response or user voice reply
- Records voice replies using speech-to-text ot generate the response from local model
- Saves replies as Gmail drafts or sends them immediately
- Works with local and open-source tools to eliminate subscription costs


## Zero-Cost and Privacy Approach
- The project is designed to run with free/open-source components and does not require a paid API for the main workflow.
- Text-to-speech and speech-to-text are handled locally with models stored on your machine.
- The Gmail access token and Google credentials are stored locally in the project folder.
- Email content is processed by the app on your device, and local logs are written for troubleshooting.
- For stronger privacy, run the LLM locally (for example with a local Ollama setup) instead of sending your emails to a remote service.

## Required User Permissions
When you sign in, the app asks for permission to:
- Read your Gmail inbox and message details (to detect unread emails and summarize them)
- Create and send Gmail drafts/messages (when you choose to save or send a reply)
- Use your microphone (to record voice replies)
- Use your speaker/output device (to read emails aloud)

You should review the requested Google scopes before approving access. This project uses Gmail API permissions for reading and composing only.

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Download your Google OAuth credentials JSON file and save it as `credentials.json`.
3. Download the required local model files:
   - `kokoro-v0_19.onnx`
   - `voices.bin`
   Place them in the project root.
4. Make sure you have an LLM runtime available for AI replies (for example, a local Ollama setup).
5. Start the app:
   ```bash
   python main.py
   ```

## Important Notes
- The app expects `credentials.json` and `token.json` for Gmail authentication.
- The token file is created after you approve access and is stored locally.
- Sensitive files are ignored by Git via `.gitignore`.
- If you use a remote AI service, your email text may leave your device; for maximum privacy, prefer a local model setup.
