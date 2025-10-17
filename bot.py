"""
SysAlert Monitor Bot - Main entrypoint - FIXED
"""
import os
import sys
import asyncio
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from db import DB
from services.tele_queue import TeleQueue
from services.monitor import monitoring_worker
from services.benchmark import benchmark_monitor_loop
from commands.handlers import register_handlers

load_dotenv()


async def error_handler(update: object, context: ContextTypes) -> None:
    """Handle errors and log them without exposing sensitive info to users"""
    logger.error("Exception while handling an update:", exc_info=context.error)

    # Send generic error message to user (don't leak internal details)
    if update and hasattr(update, 'effective_message') and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ An error occurred while processing your request.\n"
                "Please try again later or contact an administrator if the issue persists."
            )
        except Exception:
            # Even error handling can fail (e.g., chat deleted)
            pass

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('bot.log')]
)
logger = logging.getLogger("SysAlertBot")

# Global state
db: DB = None
tele_queue: TeleQueue = None
application: Application = None
config: Dict[str, Any] = {}
background_tasks: List[asyncio.Task] = []

def load_config() -> Dict[str, Any]:
    """Load configuration from environment"""
    conf = {
        "telegram_token": os.getenv("TELEGRAM_TOKEN"),
        "master_key": os.getenv("MASTER_KEY"),
        "admin_user_ids": [int(x.strip()) for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x.strip().isdigit()],
        "db_url": os.getenv("DB_URL", "sqlite:///./data/bot.db"),
        "max_concurrent_checks": int(os.getenv("MAX_CONCURRENT_CHECKS", "50")),
        "min_interval_seconds": int(os.getenv("MIN_INTERVAL_SECONDS", "20")),
        "default_interval_seconds": int(os.getenv("DEFAULT_INTERVAL_SECONDS", "60")),
        "connection_timeout": int(os.getenv("CONNECTION_TIMEOUT", "10")),
        "failure_threshold": int(os.getenv("FAILURE_THRESHOLD", "3")),
        "max_targets_per_user": int(os.getenv("MAX_TARGETS_PER_USER", "10")),
        "max_bench_targets_per_user": int(os.getenv("MAX_BENCH_TARGETS_PER_USER", "5")),
        "tele_workers": int(os.getenv("TELE_WORKERS", "3")),
        "per_chat_rate_seconds": float(os.getenv("PER_CHAT_RATE_SECONDS", "1.0")),
        "max_failed_admin_attempts": int(os.getenv("MAX_FAILED_ADMIN_ATTEMPTS", "5")),
        "admin_ban_duration": int(os.getenv("ADMIN_BAN_DURATION", "3600")),
        "bot_name": os.getenv("BOT_NAME", "SysAlert"),
        "cpu_benchmark": {
            "enabled": os.getenv("CPU_BENCH_ENABLED", "true").lower() == "true",
            "mainnet_url": os.getenv("CPU_BENCH_MAINNET_URL", "https://proton.saltant.io/Services?handler=CpuBenchmark&dataRange=0&networkType=1"),
            "testnet_url": os.getenv("CPU_BENCH_TESTNET_URL", "https://proton.saltant.io/Services?handler=CpuBenchmark&dataRange=0&networkType=2"),
            "threshold_seconds": float(os.getenv("CPU_BENCH_THRESHOLD_SECONDS", "0.35")),
            "poll_interval_seconds": int(os.getenv("CPU_BENCH_INTERVAL", "300"))
        }
    }
    
    if not conf["telegram_token"]:
        logger.error("TELEGRAM_TOKEN is required")
        sys.exit(1)
    
    if not conf["master_key"]:
        logger.error("MASTER_KEY is required - run: python scripts/bootstrap.sh")
        sys.exit(1)
    
    return conf

async def post_init(app: Application) -> None:
    """Initialize services after application setup"""
    global tele_queue, background_tasks
    
    async def bot_send(chat_id: int, text: str):
        await app.bot.send_message(chat_id=chat_id, text=text)
    
    tele_queue = TeleQueue(
        bot_send,
        workers=config["tele_workers"],
        per_chat_rate_seconds=config["per_chat_rate_seconds"]
    )
    await tele_queue.start()
    
    # Store in bot_data for handlers to access
    app.bot_data['tele_queue'] = tele_queue
    app.bot_data['db'] = db
    app.bot_data['config'] = config
    
    # Start monitoring worker
    monitor_task = asyncio.create_task(monitoring_worker(db, tele_queue, config))
    background_tasks.append(monitor_task)
    
    # Start CPU benchmark if enabled
    if config["cpu_benchmark"]["enabled"]:
        benchmark_task = asyncio.create_task(
            benchmark_monitor_loop(db, tele_queue, config, config["admin_user_ids"])
        )
        background_tasks.append(benchmark_task)
    
    logger.info("Bot initialized successfully")


async def post_shutdown(app: Application) -> None:
    """Cleanup on shutdown"""
    global tele_queue, background_tasks
    
    logger.info("Shutting down gracefully...")
    
    if tele_queue:
        await tele_queue.stop()
    
    for task in background_tasks:
        task.cancel()
    
    if background_tasks:
        await asyncio.gather(*background_tasks, return_exceptions=True)
    
    background_tasks.clear()
    logger.info("Shutdown complete")


def main():
    """Main entrypoint"""
    global config, db, application, tele_queue
    
    logger.info("Starting SysAlert Monitor Bot v2.0")
    
    config = load_config()
    
    db = DB(config["db_url"], config["master_key"])
    
    application = Application.builder().token(config["telegram_token"]).build()
    
    # Register handlers - pass tele_queue after it's created in post_init
    register_handlers(application, db, config)

    # Register error handler
    application.add_error_handler(error_handler)

    application.post_init = post_init
    application.post_shutdown = post_shutdown
    
    logger.info("Bot polling started")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()