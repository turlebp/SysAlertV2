"""
CPU benchmark monitoring - FIXED
"""
import asyncio
import logging
import aiohttp
from typing import Optional, Tuple, Any, List, Dict

logger = logging.getLogger("SysAlertBot.benchmark")


def _parse_possible_structures(data: Any, target_name: str) -> Optional[Tuple[int, float]]:
    """Parse various JSON response formats"""
    # CSV-like strings - find FIRST match
    if isinstance(data, list) and len(data) > 0:
        if isinstance(data[0], str):
            for line in data:
                parts = line.split(',')
                if len(parts) >= 3 and parts[0].strip() == target_name:
                    try:
                        ts = int(parts[1].strip())
                        val = float(parts[2].strip())
                        return (ts, val)  # Return first match
                    except (ValueError, IndexError):
                        continue
            return None
        
        # List of dicts - get last data point
        if isinstance(data[0], dict):
            for item in data:
                if item.get("name") == target_name:
                    series_data = item.get("data", [])
                    if series_data and len(series_data) > 0:
                        last_point = series_data[-1]
                        if len(last_point) >= 2:
                            return (int(last_point[0]), float(last_point[1]))
            return None
    
    # Dict of lists - get last data point
    if isinstance(data, dict):
        if target_name in data:
            series_data = data[target_name]
            if isinstance(series_data, list) and len(series_data) > 0:
                last_point = series_data[-1]
                if isinstance(last_point, (list, tuple)) and len(last_point) >= 2:
                    return (int(last_point[0]), float(last_point[1]))
    
    return None


async def check_cpu_benchmark(
    url: str,
    target_name: str,
    threshold: float,
    timeout: float = 10.0
) -> Tuple[bool, Optional[float], str]:
    """Check CPU benchmark"""
    try:
        # Create session with SSL verification enabled
        connector = aiohttp.TCPConnector(ssl=True)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status != 200:
                    return False, None, f"HTTP {resp.status}"
                
                data = await resp.json()
                result = _parse_possible_structures(data, target_name)
                
                if result is None:
                    return False, None, f"Target '{target_name}' not found"
                
                timestamp, value = result
                
                if value > threshold:
                    msg = f"⚠️ CPU Benchmark: {target_name} = {value:.3f}s (threshold: {threshold}s)"
                    return True, value, msg
                else:
                    return False, value, "OK"
    except asyncio.TimeoutError:
        return False, None, "Timeout"
    except Exception as e:
        return False, None, f"Error: {e}"

async def benchmark_monitor_loop(
    db,
    tele_queue,
    config: Dict[str, Any],
    admin_chat_ids: List[int]
):
    """Background benchmark monitoring"""
    bench_config = config.get("cpu_benchmark", {})
    
    if not bench_config.get("enabled", True):
        return
    
    threshold = float(bench_config.get("threshold_seconds", 0.35))
    interval = int(bench_config.get("poll_interval_seconds", 300))
    
    logger.info(f"Starting CPU benchmark monitor (interval: {interval}s)")
    
    while True:
        try:
            subscriptions = await asyncio.to_thread(db.list_subscriptions)
            
            for chat_id in subscriptions:
                targets = await asyncio.to_thread(db.list_benchmark_targets, chat_id)
                if not targets:
                    continue
                
                for target_name, network in targets:
                    url = bench_config.get(f"{network}_url")
                    if not url:
                        logger.warning(f"No URL configured for {network}")
                        continue
                    
                    alert_triggered, value, message = await check_cpu_benchmark(
                        url, target_name, threshold
                    )
                    
                    if alert_triggered:
                        network_icon = "🌐" if network == "mainnet" else "🧪"
                        alert_msg = (
                            f"⚠️ {config.get('bot_name', 'SysAlert')} ⚠️\n"
                            f"📊 CPU Benchmark Alert\n\n"
                            f"🎯 Target: {target_name}\n"
                            f"{network_icon} Network: {network.upper()}\n"
                            f"📊 Score: {value:.3f}s\n"
                            f"🚨 Threshold: {threshold}s\n"
                            f"❌ Status: SLOW"
                        )
                        await tele_queue.enqueue(chat_id, alert_msg)
        except Exception:
            logger.exception("Error in benchmark monitor loop")
        
        await asyncio.sleep(interval)