"""
Telegram bot command handlers - COMPLETE WITH MULTIPLE BENCHMARKS
"""
import re
import secrets
import logging
import asyncio
import ipaddress
import time
from typing import Dict, Any
from collections import defaultdict
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from utils.security import (
    sanitize_target_name,
    sanitize_for_display,
    validate_domain,
    validate_port,
    is_safe_interval
)

logger = logging.getLogger("SysAlertBot.handlers")

delete_tokens = {}
_tele_queue = None

# Security: Track failed admin command attempts
failed_admin_attempts = defaultdict(list)

def set_tele_queue(queue):
    """Called by bot.py to set queue reference"""
    global _tele_queue
    _tele_queue = queue


def is_user_banned(user_id: int, config: Dict[str, Any]) -> bool:
    """Check if user is temporarily banned due to failed admin attempts"""
    max_attempts = config.get("max_failed_admin_attempts", 5)
    ban_duration = config.get("admin_ban_duration", 3600)

    attempts = failed_admin_attempts[user_id]
    current_time = time.time()

    # Clean old attempts
    attempts[:] = [ts for ts in attempts if current_time - ts < ban_duration]

    return len(attempts) >= max_attempts


def record_failed_attempt(user_id: int, config: Dict[str, Any], db):
    """Record failed admin command attempt"""
    failed_admin_attempts[user_id].append(time.time())

    # Audit log
    try:
        db.audit(
            user_id,
            "failed_admin_attempt",
            f"Unauthorized admin command attempt from {user_id}"
        )
    except Exception:
        logger.exception("Failed to write audit log")


def register_handlers(app: Application, db, config: Dict[str, Any]):
    """Register all command handlers"""
    
    def is_admin(user_id: int) -> bool:
        return user_id in config["admin_user_ids"]
    
    bot_name = config.get("bot_name", "SysAlert")
    
    async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = (
            f"🚀 Welcome to {bot_name} v2.0\n\n"
            f"🔐 Privacy-hardened monitoring with encrypted storage\n\n"
            f"📋 Use /whoami to get your chat ID\n"
            f"📚 Use /help to see all commands"
        )
        await update.message.reply_text(msg)
    
    async def whoami_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        is_subbed = await asyncio.to_thread(db.is_subscribed, chat_id)
        
        msg = f"👤 Your Information\n\n"
        msg += f"💬 Chat ID: {chat_id}\n"
        msg += f"👨‍💻 User ID: {user_id}\n"
        msg += f"📝 Subscribed: {'✅ Yes' if is_subbed else '❌ No'}\n"
        msg += f"🔧 Admin: {'✅ Yes' if is_admin(user_id) else '❌ No'}"
        
        await update.message.reply_text(msg)
    
    async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = f"📚 {bot_name} - Available Commands\n\n"
        msg += "👤 User Commands\n"
        msg += "• /start - Welcome message\n"
        msg += "• /whoami - Show your information\n"
        msg += "• /setbench - Add benchmark target\n"
        msg += "• /listbench - List benchmark targets\n"
        msg += "• /removebench - Remove benchmark target\n"
        msg += "• /setinterval - Set check interval\n"
        msg += "• /addtarget - Add monitoring target\n"
        msg += "• /removetarget - Remove a target\n"
        msg += "• /mode - Toggle monitoring mode\n"
        msg += "• /check - Manually check target now\n"
        msg += "• /get cpu - Show benchmark scores\n"
        msg += "• /status - View all targets\n"
        msg += "• /history - Recent check history\n"
        msg += "• /delete_account - Delete all your data\n\n"
        
        if is_admin(update.effective_user.id):
            msg += "🔧 Admin Commands\n"
            msg += "• /addsub - Add subscription\n"
            msg += "• /rmsub - Remove subscription\n"
            msg += "• /stats - Bot statistics\n"
        
        await update.message.reply_text(msg)
    
    async def setbench_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add benchmark target"""
        chat_id = update.effective_chat.id
        
        if not await asyncio.to_thread(db.is_subscribed, chat_id):
            await update.message.reply_text("❌ You're not subscribed to this bot")
            return
        
        if len(context.args) < 1 or len(context.args) > 2:
            await update.message.reply_text(
                "📊 Add Benchmark Target\n\n"
                "Usage: /setbench <target> [network]\n\n"
                "Networks:\n"
                "• mainnet (default)\n"
                "• testnet\n\n"
                "Examples:\n"
                "• /setbench turtlebp mainnet\n"
                "• /setbench chainblock testnet\n"
                "• /setbench bp21 (defaults to mainnet)\n\n"
                "Manage targets:\n"
                "• /listbench - Show all benchmark targets\n"
                "• /removebench <target> - Remove a target"
            )
            return
        
        # Check limit
        current_count = await asyncio.to_thread(db.count_benchmark_targets, chat_id)
        max_bench = config.get("max_bench_targets_per_user", 5)
        
        # Sanitize target name
        target_name = sanitize_target_name(context.args[0])
        if not target_name:
            await update.message.reply_text(
                "❌ Invalid target name\n\n"
                "Requirements:\n"
                "• 1-32 characters\n"
                "• Letters, numbers, dash, underscore only\n"
                "• No special characters"
            )
            return

        network = context.args[1].lower() if len(context.args) == 2 else "mainnet"

        # Check if updating existing
        targets = await asyncio.to_thread(db.list_benchmark_targets, chat_id)
        is_update = any(t[0] == target_name for t in targets)

        if not is_update and current_count >= max_bench:
            await update.message.reply_text(
                f"❌ Maximum benchmark targets reached ({max_bench})\n"
                f"Remove one first with: /removebench <target>"
            )
            return

        if network not in ["mainnet", "testnet"]:
            await update.message.reply_text("❌ Invalid network. Use: mainnet or testnet")
            return
        
        success = await asyncio.to_thread(db.add_benchmark_target, chat_id, target_name, network)
        
        if success:
            network_icon = "🌐" if network == "mainnet" else "🧪"
            action = "Updated" if is_update else "Added"
            await update.message.reply_text(
                f"✅ {action} benchmark target!\n\n"
                f"🎯 Target: {target_name}\n"
                f"{network_icon} Network: {network.upper()}\n"
                f"📊 Total: {current_count if is_update else current_count + 1}/{max_bench}"
            )
        else:
            await update.message.reply_text("❌ Failed to add benchmark target")
    
    async def listbench_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all benchmark targets"""
        chat_id = update.effective_chat.id
        
        if not await asyncio.to_thread(db.is_subscribed, chat_id):
            await update.message.reply_text("❌ You're not subscribed to this bot")
            return
        
        targets = await asyncio.to_thread(db.list_benchmark_targets, chat_id)
        
        if not targets:
            await update.message.reply_text(
                "📊 No Benchmark Targets\n\n"
                "Add one with:\n"
                "/setbench <target> [network]\n\n"
                "Example:\n"
                "/setbench turtlebp mainnet"
            )
            return
        
        max_bench = config.get("max_bench_targets_per_user", 5)
        msg = f"📊 Benchmark Targets ({len(targets)}/{max_bench})\n\n"
        
        for target_name, network in targets:
            network_icon = "🌐" if network == "mainnet" else "🧪"
            msg += f"{network_icon} {target_name} ({network.upper()})\n"
        
        msg += "\n💡 Tip: Use /get cpu to check all targets"
        
        await update.message.reply_text(msg)
    
    async def removebench_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove a benchmark target"""
        chat_id = update.effective_chat.id
        
        if not await asyncio.to_thread(db.is_subscribed, chat_id):
            await update.message.reply_text("❌ You're not subscribed to this bot")
            return
        
        if len(context.args) != 1:
            await update.message.reply_text(
                "🗑️ Remove Benchmark Target\n\n"
                "Usage: /removebench <target>\n"
                "Example: /removebench turtlebp"
            )
            return
        
        target_name = context.args[0].strip()
        
        removed = await asyncio.to_thread(db.remove_benchmark_target, chat_id, target_name)
        
        if removed:
            await update.message.reply_text(f"✅ Removed benchmark target: {target_name}")
        else:
            await update.message.reply_text(f"❌ Benchmark target not found: {target_name}")
    
    async def setinterval_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set custom check interval"""
        chat_id = update.effective_chat.id
        
        if not await asyncio.to_thread(db.is_subscribed, chat_id):
            await update.message.reply_text("❌ You're not subscribed to this bot")
            return
        
        if len(context.args) != 1:
            min_interval = config["min_interval_seconds"]
            await update.message.reply_text(
                f"⏱️ Set Check Interval\n\n"
                f"Usage: /setinterval <seconds>\n"
                f"Minimum: {min_interval}s\n"
                f"Example: /setinterval 30"
            )
            return
        
        try:
            interval = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid number")
            return

        min_interval = config["min_interval_seconds"]
        if not is_safe_interval(interval, min_interval):
            await update.message.reply_text(
                f"❌ Interval must be between {min_interval} and 86400 seconds (24 hours)"
            )
            return
        
        customer = await asyncio.to_thread(db.get_customer_by_chat, chat_id)
        if not customer:
            customer = await asyncio.to_thread(db.create_customer, chat_id)
        
        success = await asyncio.to_thread(db.set_customer_interval, chat_id, interval)
        
        if success:
            await update.message.reply_text(f"✅ Check interval set to {interval} seconds")
        else:
            await update.message.reply_text("❌ Failed to set interval")
    
    async def addtarget_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add monitoring target"""
        chat_id = update.effective_chat.id
        
        if not await asyncio.to_thread(db.is_subscribed, chat_id):
            await update.message.reply_text("❌ You're not subscribed to this bot")
            return
        
        if len(context.args) < 2:
            msg = (
                "🎯 Add Monitoring Target\n\n"
                "Usage:\n"
                "• /addtarget <name> <ip> <port>\n"
                "• /addtarget <name> <domain> <port>\n"
                "• /addtarget <name> <domain> (default port: 80)\n\n"
                "Examples:\n"
                "• /addtarget myserver 192.168.1.100 9876\n"
                "• /addtarget api example.com 8080\n"
                "• /addtarget website example.com"
            )
            await update.message.reply_text(msg)
            return
        
        customer = await asyncio.to_thread(db.get_customer_by_chat, chat_id)
        if customer:
            target_count = await asyncio.to_thread(db.count_customer_targets, customer.id)
            max_targets = config.get("max_targets_per_user", 10)
            
            if target_count >= max_targets:
                await update.message.reply_text(
                    f"❌ Maximum targets reached ({max_targets})\n"
                    f"Remove a target first with /removetarget"
                )
                return
        
        # Sanitize and validate inputs
        name = sanitize_target_name(context.args[0])
        if not name:
            await update.message.reply_text(
                "❌ Invalid target name\n\n"
                "Requirements:\n"
                "• 1-32 characters\n"
                "• Letters, numbers, dash, underscore only\n"
                "• No special characters"
            )
            return

        host = context.args[1].strip()
        port_str = context.args[2].strip() if len(context.args) >= 3 else "80"

        # Validate port
        try:
            port_int = int(port_str)
            if not validate_port(port_int):
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Invalid port number (must be 1-65535)")
            return

        # Validate host (IP or domain)
        is_ip = False
        try:
            ipaddress.ip_address(host)
            is_ip = True
        except ValueError:
            if not validate_domain(host):
                await update.message.reply_text("❌ Invalid IP address or domain name")
                return
        
        if not customer:
            customer = await asyncio.to_thread(db.create_customer, chat_id, 
                                               interval_seconds=config["default_interval_seconds"],
                                               failure_threshold=config["failure_threshold"])
        
        await asyncio.to_thread(db.upsert_target, customer.id, name, host, port_int)
        
        type_icon = "📡" if is_ip else "🌐"
        await update.message.reply_text(
            f"✅ Target added successfully!\n\n"
            f"{type_icon} {name}\n"
            f"🎯 Address: {host}:{port_int}\n"
            f"⏱️ Interval: {customer.interval_seconds}s"
        )
    
    async def removetarget_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove a target"""
        chat_id = update.effective_chat.id
        
        if not await asyncio.to_thread(db.is_subscribed, chat_id):
            await update.message.reply_text("❌ You're not subscribed to this bot")
            return
        
        if len(context.args) != 1:
            await update.message.reply_text(
                "🗑️ Remove Target\n\n"
                "Usage: /removetarget <name>\n"
                "Example: /removetarget myserver"
            )
            return
        
        name = context.args[0].strip()
        
        customer = await asyncio.to_thread(db.get_customer_by_chat, chat_id)
        if not customer:
            await update.message.reply_text("❌ No targets configured")
            return
        
        removed = await asyncio.to_thread(db.remove_target, customer.id, name)
        
        if removed:
            await update.message.reply_text(f"✅ Target {name} removed successfully")
        else:
            await update.message.reply_text(f"❌ Target {name} not found")
    
    async def mode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle monitoring mode"""
        chat_id = update.effective_chat.id
        
        if not await asyncio.to_thread(db.is_subscribed, chat_id):
            await update.message.reply_text("❌ You're not subscribed to this bot")
            return
        
        if len(context.args) < 2:
            msg = (
                "🔧 Toggle Monitoring Mode\n\n"
                "Usage:\n"
                "• /mode maintenance <target> - Disable monitoring\n"
                "• /mode active <target> - Enable monitoring\n"
                "• /mode maintenance all - Disable all\n"
                "• /mode active all - Enable all\n\n"
                "Examples:\n"
                "• /mode maintenance myserver\n"
                "• /mode active all"
            )
            await update.message.reply_text(msg)
            return
        
        mode = context.args[0].lower()
        target_name = context.args[1].strip()
        
        if mode not in ["maintenance", "active"]:
            await update.message.reply_text("❌ Invalid mode. Use: maintenance or active")
            return
        
        customer = await asyncio.to_thread(db.get_customer_by_chat, chat_id)
        if not customer:
            await update.message.reply_text("❌ No targets configured")
            return
        
        enable = (mode == "active")
        
        if target_name.lower() == "all":
            updated_count = await asyncio.to_thread(db.toggle_all_targets, customer.id, enable)
            
            if updated_count > 0:
                icon = "✅" if enable else "🔧"
                mode_str = "active" if enable else "maintenance"
                await update.message.reply_text(
                    f"{icon} {updated_count} target(s) set to {mode_str} mode"
                )
            else:
                await update.message.reply_text("❌ No targets to update")
        else:
            success = await asyncio.to_thread(db.toggle_target_mode, customer.id, target_name, enable)
            
            if success:
                icon = "✅" if enable else "🔧"
                mode_str = "active" if enable else "maintenance"
                await update.message.reply_text(
                    f"{icon} Target {target_name} set to {mode_str} mode"
                )
            else:
                await update.message.reply_text(f"❌ Target {target_name} not found")
    
    async def check_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manually check a target now"""
        chat_id = update.effective_chat.id
        
        if not await asyncio.to_thread(db.is_subscribed, chat_id):
            await update.message.reply_text("❌ You're not subscribed to this bot")
            return
        
        if len(context.args) != 1:
            await update.message.reply_text(
                "🔍 Manual Check\n\n"
                "Usage: /check <target>\n"
                "Example: /check myserver"
            )
            return
        
        target_name = context.args[0].strip()
        
        customer = await asyncio.to_thread(db.get_customer_by_chat, chat_id)
        if not customer:
            await update.message.reply_text("❌ No targets configured")
            return
        
        target = None
        for t in customer.targets:
            if t.name == target_name:
                target = t
                break
        
        if not target:
            await update.message.reply_text(f"❌ Target {target_name} not found")
            return
        
        checking_msg = await update.message.reply_text(f"🔍 Checking {target_name}...")
        
        from services.monitor import tcp_check
        ip, port = await asyncio.to_thread(db.get_target_decrypted, target)
        
        timeout = config["connection_timeout"]
        success, response_time, error_msg = await tcp_check(ip, port, timeout)
        
        if success:
            result_msg = (
                f"✅ {target_name} is UP\n\n"
                f"🎯 Target: {ip}:{port}\n"
                f"⏱️ Response time: {response_time:.3f}s\n"
                f"📊 Status: Healthy"
            )
        else:
            result_msg = (
                f"❌ {target_name} is DOWN\n\n"
                f"🎯 Target: {ip}:{port}\n"
                f"💥 Error: {error_msg}\n"
                f"⏱️ Response time: {response_time:.3f}s"
            )
        
        await checking_msg.edit_text(result_msg)
    
    async def get_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get CPU benchmark scores for all targets"""
        chat_id = update.effective_chat.id
        
        if not await asyncio.to_thread(db.is_subscribed, chat_id):
            await update.message.reply_text("❌ You're not subscribed to this bot")
            return
        
        if len(context.args) != 1 or context.args[0].lower() != "cpu":
            await update.message.reply_text(
                "📊 Get Benchmark Scores\n\n"
                "Usage: /get cpu"
            )
            return
        
        targets = await asyncio.to_thread(db.list_benchmark_targets, chat_id)
        if not targets:
            await update.message.reply_text(
                "❌ No benchmark targets set\n\n"
                "Add one with: /setbench <target> [network]\n"
                "Example: /setbench turtlebp mainnet"
            )
            return
        
        from services.benchmark import check_cpu_benchmark
        bench_config = config["cpu_benchmark"]
        
        checking_msg = await update.message.reply_text(
            f"📊 Fetching benchmarks for {len(targets)} target(s)..."
        )
        
        results = []
        for target_name, network in targets:
            url = bench_config.get(f"{network}_url")
            if not url:
                results.append((target_name, network, None, f"URL not configured for {network}"))
                continue
            
            alert_triggered, value, message = await check_cpu_benchmark(
                url,
                target_name,
                bench_config["threshold_seconds"]
            )
            results.append((target_name, network, value, message if value is None else None))
        
        # Build response
        threshold = bench_config["threshold_seconds"]
        msg = "📊 CPU Benchmark Results\n\n"
        
        for target_name, network, value, error in results:
            network_icon = "🌐" if network == "mainnet" else "🧪"
            
            if value is not None:
                if value > threshold:
                    status = "❌ SLOW"
                    icon = "⚠️"
                else:
                    status = "✅ OK"
                    icon = "✅"
                
                msg += f"{icon} {target_name}\n"
                msg += f"   {network_icon} {network.upper()} | Score: {value:.3f}s | {status}\n"
            else:
                msg += f"❌ {target_name}\n"
                msg += f"   {network_icon} {network.upper()} | Error: {error}\n"
        
        msg += f"\n🚨 Threshold: {threshold}s"
        
        await checking_msg.edit_text(msg)
    
    async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show all targets"""
        chat_id = update.effective_chat.id
        
        if not await asyncio.to_thread(db.is_subscribed, chat_id):
            await update.message.reply_text("❌ You're not subscribed to this bot")
            return
        
        customer = await asyncio.to_thread(db.get_customer_by_chat, chat_id)
        if not customer:
            await update.message.reply_text(
                "📊 No Monitoring Configured\n\n"
                "Add your first target with:\n"
                "/addtarget <name> <host> <port>"
            )
            return
        
        msg = f"📊 {bot_name} - Monitoring Status\n\n"
        msg += f"🔔 Alerts: {'✅ Enabled' if customer.alerts_enabled else '❌ Disabled'}\n"
        msg += f"⏱️ Check Interval: {customer.interval_seconds}s\n"
        msg += f"💥 Failure Threshold: {customer.failure_threshold}\n\n"
        
        if not customer.targets:
            msg += "📋 No Targets\n\n"
            msg += "Add targets with:\n/addtarget <name> <host> <port>"
        else:
            max_targets = config.get("max_targets_per_user", 10)
            msg += f"🎯 Targets ({len(customer.targets)}/{max_targets})\n"
            for t in customer.targets:
                if not t.enabled:
                    status = "🔧"
                    label = " (maintenance)"
                elif t.consecutive_failures > 0:
                    status = "❌"
                    label = f" ({t.consecutive_failures} failures)"
                else:
                    status = "✅"
                    label = ""
                
                msg += f"{status} {t.name}{label}\n"
        
        await update.message.reply_text(msg)
    
    async def delete_account_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Initiate account deletion"""
        chat_id = update.effective_chat.id
        
        token = secrets.token_urlsafe(16)
        delete_tokens[chat_id] = token
        
        async def expire_token():
            await asyncio.sleep(600)
            delete_tokens.pop(chat_id, None)
        
        asyncio.create_task(expire_token())
        
        msg = (
            "⚠️ ACCOUNT DELETION WARNING ⚠️\n\n"
            "This will permanently delete:\n"
            "🗑️ All monitoring targets (encrypted)\n"
            "🗑️ Benchmark preferences\n"
            "🗑️ Check history\n"
            "🗑️ Your subscription\n\n"
            "⏰ Token expires in 10 minutes\n\n"
            "To confirm, send:\n"
            f"/confirm_delete {token}"
        )
        await update.message.reply_text(msg)
    
    async def confirm_delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm account deletion"""
        chat_id = update.effective_chat.id
        
        if len(context.args) != 1:
            await update.message.reply_text(
                "🗑️ Confirm Deletion\n\n"
                "Usage: /confirm_delete <token>"
            )
            return
        
        provided_token = context.args[0]
        expected_token = delete_tokens.get(chat_id)
        
        if not expected_token or provided_token != expected_token:
            await update.message.reply_text("❌ Invalid or expired token")
            return
        
        await asyncio.to_thread(db.delete_user_data, chat_id)
        delete_tokens.pop(chat_id, None)
        
        await update.message.reply_text(
            "✅ Account Deleted Successfully\n\n"
            "🗑️ All your data has been permanently removed\n"
            "👋 Thank you for using our service"
        )
    
    async def history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show recent check history"""
        chat_id = update.effective_chat.id
        
        if not await asyncio.to_thread(db.is_subscribed, chat_id):
            await update.message.reply_text("❌ You're not subscribed to this bot")
            return
        
        from datetime import datetime
        history = await asyncio.to_thread(db.get_recent_history, chat_id, 10)
        
        if not history:
            await update.message.reply_text(
                "📜 No History Available\n\n"
                "History will appear once targets are checked"
            )
            return
        
        msg = f"📜 Recent Check History\n\n"
        for h in history:
            status = "✅" if h.status == "success" else "❌"
            dt = datetime.fromtimestamp(h.timestamp)
            msg += f"{status} {h.target_name} - {dt.strftime('%m/%d %H:%M')}\n"
            if h.error:
                msg += f"   Error: {h.error[:40]}\n"
        
        await update.message.reply_text(msg)
    
    # Admin commands
    async def addsub_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin: Add subscription"""
        user_id = update.effective_user.id

        # Check if user is banned
        if is_user_banned(user_id, config):
            await update.message.reply_text("❌ Access temporarily restricted")
            return

        if not is_admin(user_id):
            record_failed_attempt(user_id, config, db)
            await update.message.reply_text("❌ Unauthorized - Admin only")
            logger.warning(f"Unauthorized admin command attempt from {user_id}")
            return
        
        if len(context.args) != 1:
            await update.message.reply_text(
                "🔧 Add Subscription\n\n"
                "Usage: /addsub <chat_id>"
            )
            return
        
        try:
            target_chat_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid chat_id (must be a number)")
            return
        
        await asyncio.to_thread(db.add_subscription, target_chat_id)
        await asyncio.to_thread(db.audit, update.effective_user.id, "add_subscription", f"Added {target_chat_id}")
        await update.message.reply_text(f"✅ Subscription added for chat_id: {target_chat_id}")
    
    async def rmsub_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin: Remove subscription"""
        user_id = update.effective_user.id

        # Check if user is banned
        if is_user_banned(user_id, config):
            await update.message.reply_text("❌ Access temporarily restricted")
            return

        if not is_admin(user_id):
            record_failed_attempt(user_id, config, db)
            await update.message.reply_text("❌ Unauthorized - Admin only")
            logger.warning(f"Unauthorized admin command attempt from {user_id}")
            return
        
        if len(context.args) != 1:
            await update.message.reply_text(
                "🔧 Remove Subscription\n\n"
                "Usage: /rmsub <chat_id>"
            )
            return
        
        try:
            target_chat_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid chat_id (must be a number)")
            return
        
        await asyncio.to_thread(db.remove_subscription, target_chat_id)
        await asyncio.to_thread(db.audit, update.effective_user.id, "remove_subscription", f"Removed {target_chat_id}")
        await update.message.reply_text(f"✅ Subscription removed for chat_id: {target_chat_id}")
    
    async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin: Show statistics"""
        user_id = update.effective_user.id

        # Check if user is banned
        if is_user_banned(user_id, config):
            await update.message.reply_text("❌ Access temporarily restricted")
            return

        if not is_admin(user_id):
            record_failed_attempt(user_id, config, db)
            await update.message.reply_text("❌ Unauthorized - Admin only")
            logger.warning(f"Unauthorized admin command attempt from {user_id}")
            return
        
        queue_stats = _tele_queue.get_stats() if _tele_queue else {}
        subs = await asyncio.to_thread(db.list_subscriptions)
        
        msg = f"📊 {bot_name} - Bot Statistics\n\n"
        msg += f"👥 Subscriptions: {len(subs)}\n"
        msg += f"📤 Messages Sent: {queue_stats.get('sent', 0)}\n"
        msg += f"⚠️ Messages Failed: {queue_stats.get('failed', 0)}\n"
        msg += f"🗑️ Messages Dropped: {queue_stats.get('dropped', 0)}\n"
        msg += f"📬 Queue Size: {_tele_queue.queue_size() if _tele_queue else 0}"
        
        await update.message.reply_text(msg)
    
    # Register handlers
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("whoami", whoami_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("setbench", setbench_cmd))
    app.add_handler(CommandHandler("listbench", listbench_cmd))
    app.add_handler(CommandHandler("removebench", removebench_cmd))
    app.add_handler(CommandHandler("setinterval", setinterval_cmd))
    app.add_handler(CommandHandler("addtarget", addtarget_cmd))
    app.add_handler(CommandHandler("removetarget", removetarget_cmd))
    app.add_handler(CommandHandler("mode", mode_cmd))
    app.add_handler(CommandHandler("check", check_cmd))
    app.add_handler(CommandHandler("get", get_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("delete_account", delete_account_cmd))
    app.add_handler(CommandHandler("confirm_delete", confirm_delete_cmd))
    app.add_handler(CommandHandler("history", history_cmd))
    app.add_handler(CommandHandler("addsub", addsub_cmd))
    app.add_handler(CommandHandler("rmsub", rmsub_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    
    logger.info("Command handlers registered")