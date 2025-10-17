"""
TCP monitoring service - FIXED
"""
import asyncio
import time
import logging
from typing import Tuple, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger("SysAlertBot.monitor")


async def tcp_check(ip: str, port: int, timeout: float = 5.0) -> Tuple[bool, float, str]:
    """TCP connection check"""
    start = time.time()
    
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host=ip, port=port),
            timeout=timeout
        )
        
        writer.close()
        await writer.wait_closed()
        
        response_time = time.time() - start
        return True, response_time, ""
    except asyncio.TimeoutError:
        return False, 0.0, f"Connection timeout after {timeout}s"
    except ConnectionRefusedError:
        return False, 0.0, "Connection refused"
    except OSError as e:
        return False, 0.0, f"OS error: {e}"
    except Exception as e:
        return False, 0.0, str(e)


async def monitoring_worker(db, tele_queue, config: Dict[str, Any]):
    """Background monitoring worker"""
    logger.info("Starting monitoring worker")
    
    semaphore = asyncio.Semaphore(config["max_concurrent_checks"])
    
    while True:
        try:
            subscriptions = await asyncio.to_thread(db.list_subscriptions)
            
            for chat_id in subscriptions:
                # IMPORTANT: Reload customer data fresh each loop
                customer = await asyncio.to_thread(db.get_customer_by_chat, chat_id)
                if not customer:
                    continue
                
                if not customer.alerts_enabled:
                    continue
                
                # Reload targets list (this gets fresh enabled status)
                for target in customer.targets:
                    # Check enabled status (this is now fresh from DB)
                    if not target.enabled:
                        logger.debug(f"Skipping disabled target: {target.name}")
                        continue
                    
                    asyncio.create_task(
                        _check_target(db, tele_queue, customer, target, semaphore, config)
                    )
            
        except Exception:
            logger.exception("Error in monitoring worker")
        
        await asyncio.sleep(5)


async def _check_target(db, tele_queue, customer, target, semaphore, config):
    """Check single target"""
    async with semaphore:
        # Decrypt target
        ip, port = await asyncio.to_thread(db.get_target_decrypted, target)
        
        # Perform check
        timeout = config["connection_timeout"]
        success, response_time, error_msg = await tcp_check(ip, port, timeout)
        
        # Record history
        try:
            await asyncio.to_thread(
                db.write_history,
                customer.chat_id,
                target.name,
                "success" if success else "failure",
                error_msg,
                response_time
            )
        except Exception:
            logger.exception(f"Failed to write history for {target.name}")
        
        # Get current consecutive failures BEFORE updating
        current_failures = target.consecutive_failures
        
        # Update target
        try:
            import time as time_module
            await asyncio.to_thread(
                db.update_target_checked,
                target.id,
                int(time_module.time()),
                not success
            )
        except Exception:
            logger.exception(f"Failed to update target {target.name}")
        
        # Get bot branding and thresholds
        bot_name = config.get("bot_name", "SysAlert")
        failure_threshold = config.get("failure_threshold", 3)
        
        # Send alerts based on OLD consecutive_failures value
        if not success:
            consecutive = current_failures + 1
            
            if consecutive >= failure_threshold:
                alert_msg = (
                    f"⚠️ {bot_name} ⚠️\n"
                    f"🔴 ALERT: {target.name} is DOWN\n\n"
                    f"🎯 Target: {ip}:{port}\n"
                    f"💥 Consecutive failures: {consecutive}\n"
                    f"❌ Error: {error_msg}\n"
                    f"⏱️ Response time: {response_time:.3f}s"
                )
                try:
                    await tele_queue.enqueue(customer.chat_id, alert_msg)
                except Exception:
                    logger.exception(f"Failed to send alert for {target.name}")
        else:
            # Success - only send recovery if it WAS failing (current_failures > 0)
            if current_failures > 0:
                recovery_msg = (
                    f"⚠️ {bot_name} ⚠️\n"
                    f"✅ RECOVERED: {target.name} is UP\n\n"
                    f"🎯 Target: {ip}:{port}\n"
                    f"⏱️ Response time: {response_time:.3f}s"
                )
                try:
                    await tele_queue.enqueue(customer.chat_id, recovery_msg)
                    logger.info(f"Sent recovery message for {target.name}")
                except Exception:
                    logger.exception(f"Failed to send recovery message for {target.name}")