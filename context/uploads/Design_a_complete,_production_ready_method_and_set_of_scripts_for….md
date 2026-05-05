Design a complete, production-ready method and set of scripts for a Telegram bot that enables secure file upload and download between a Telegram user and a Virtual Private Server (VPS). The solution must be implemented in Python 3.9+ using the python-telegram-bot library (v20.x) and run on a Linux VPS (Ubuntu 22.04 LTS recommended). Include the following specifications:  
  
1. **Authentication & Access Control**: Implement user whitelisting via Telegram user IDs. Only authorized users can upload or download files. Include a simple admin command to add/remove users.  
  
2. **Upload Functionality**:   
   - Users send a file (document, photo, video, audio) to the bot.  
   - The bot saves the file to a designated directory on the VPS (e.g., `/var/bot_uploads/`).  
   - Generate a unique filename using timestamp + original filename to avoid collisions.  
   - Confirm successful upload with a message containing the saved filename and file size.  
   - Handle files up to 50 MB (Telegram's limit for bots). For larger files, implement chunked upload using Telegram's file streaming if possible, or reject with a clear error.  
  
3. **Download Functionality**:  
   - Users send a command like `/download <filename>` to retrieve a file.  
   - The bot checks if the file exists in the upload directory.  
   - If found, send the file back to the user via Telegram's sendDocument method.  
   - If not found, respond with a clear error message listing available files (via a `/list` command).  
  
4. **File Management Commands**:  
   - `/list`: Display all files in the upload directory with sizes and upload dates.  
   - `/delete <filename>`: Remove a specific file (with confirmation prompt).  
   - `/help`: Show available commands and usage instructions.  
  
5. **Security & Error Handling**:  
   - Validate file extensions against a whitelist (e.g., .pdf, .jpg, .png, .docx, .txt, .zip) to prevent malicious uploads.  
   - Sanitize filenames to prevent path traversal attacks (remove "../", "..\\", etc.).  
   - Implement rate limiting (max 5 uploads per minute per user).  
   - Log all operations (uploads, downloads, errors) to a file with timestamps.  
   - Handle network errors, Telegram API exceptions, and disk space issues gracefully with user-friendly messages.  
  
6. **Deployment Instructions**:  
   - Provide step-by-step setup: create a Python virtual environment, install dependencies (python-telegram-bot, python-dotenv), set up environment variables (BOT_TOKEN, ALLOWED_USERS, UPLOAD_DIR), and configure systemd service for auto-restart.  
   - Include a sample `.env` file and a `requirements.txt`.  
   - Add a systemd service file example for production deployment.  
  
7. **Code Structure**:  
   - Organize into modules: `bot.py` (main bot logic), `file_handler.py` (upload/download operations), `auth.py` (user validation), `config.py` (settings from environment).  
   - Include comprehensive comments and docstrings.  
   - Use async/await for non-blocking operations.  
  
8. **Testing & Validation**:  
   - Provide a simple test script to verify bot functionality locally.  
   - Include instructions for testing with a real Telegram bot token.  
  
Output the final solution as a single document with clear sections: Overview, Prerequisites, Installation Steps, Configuration, Code (with all modules), Deployment, and Usage Examples. Ensure the code production ready and includes error handling for all edge cases.  
