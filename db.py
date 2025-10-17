"""
Database wrapper with encryption support - COMPLETE FIXED
"""
import logging
from typing import Optional, List
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.pool import StaticPool

from models import Base, Subscription, Customer, Target, History, AuditLog, BenchmarkTarget
from utils.crypto import CryptoManager
from utils.privacy_logger import mask_chat_id, safe_target_log, safe_bench_log

logger = logging.getLogger("SysAlertBot.db")


class DB:
    """Database wrapper with encryption"""
    
    def __init__(self, db_url: str, master_key: str):
        self.db_url = db_url
        self.crypto = CryptoManager(master_key)
        
        connect_args = {}
        if db_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
            
            if ":memory:" in db_url:
                self.engine = create_engine(
                    db_url,
                    connect_args=connect_args,
                    poolclass=StaticPool,
                    future=True
                )
            else:
                self.engine = create_engine(
                    db_url,
                    connect_args=connect_args,
                    future=True
                )
            
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        else:
            self.engine = create_engine(db_url, future=True, pool_pre_ping=True)
        
        session_factory = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)
        self.Session = scoped_session(session_factory)
        
        Base.metadata.create_all(self.engine)
        logger.info(f"Database initialized: {db_url}")
    
    @contextmanager
    def session_scope(self):
        """Transactional scope"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def session(self) -> Session:
        """Get new session - caller must close"""
        return self.Session()
    
    # === Subscription methods ===
    
    def add_subscription(self, chat_id: int) -> None:
        with self.session_scope() as s:
            if not s.get(Subscription, chat_id):
                import time
                s.add(Subscription(chat_id=chat_id, created_at=int(time.time())))
                logger.info(f"Added subscription: {mask_chat_id(chat_id)}")
    
    def remove_subscription(self, chat_id: int) -> None:
        with self.session_scope() as s:
            obj = s.get(Subscription, chat_id)
            if obj:
                s.delete(obj)
                logger.info(f"Removed subscription: {mask_chat_id(chat_id)}")
    
    def list_subscriptions(self) -> List[int]:
        with self.session_scope() as s:
            rows = s.query(Subscription).all()
            return [r.chat_id for r in rows]
    
    def is_subscribed(self, chat_id: int) -> bool:
        with self.session_scope() as s:
            return s.get(Subscription, chat_id) is not None
    
    # === Customer methods ===
    
    def get_customer_by_chat(self, chat_id: int) -> Optional[Customer]:
        with self.session_scope() as s:
            cust = s.query(Customer).filter_by(chat_id=chat_id).first()
            if cust:
                _ = cust.targets
            return cust
    
    def create_customer(self, chat_id: int, **kwargs) -> Customer:
        with self.session_scope() as s:
            import time
            c = Customer(chat_id=chat_id, created_at=int(time.time()), **kwargs)
            s.add(c)
            s.flush()
            return c
    
    def update_customer(self, chat_id: int, **kwargs) -> None:
        with self.session_scope() as s:
            import time
            cust = s.query(Customer).filter_by(chat_id=chat_id).first()
            if cust:
                for key, value in kwargs.items():
                    setattr(cust, key, value)
                cust.updated_at = int(time.time())
    
    def set_customer_interval(self, chat_id: int, interval_seconds: int) -> bool:
        """Set custom check interval for customer"""
        with self.session_scope() as s:
            customer = s.query(Customer).filter_by(chat_id=chat_id).first()
            if customer:
                import time
                customer.interval_seconds = interval_seconds
                customer.updated_at = int(time.time())
                logger.info(f"Set interval to {interval_seconds}s for customer {mask_chat_id(chat_id)}")
                return True
            return False
    
    # === Target methods with encryption ===
    
    def upsert_target(self, customer_id: int, name: str, ip: str, port: int) -> Target:
        """Create or update encrypted target"""
        with self.session_scope() as s:
            target_spec = f"{ip}:{port}"
            encrypted_value = self.crypto.encrypt(target_spec)
            fingerprint = self.crypto.hash_value(target_spec)
            
            t = s.query(Target).filter_by(customer_id=customer_id, name=name).first()
            if t:
                t.encrypted_value = encrypted_value
                t.fingerprint = fingerprint
                t.enabled = True
                logger.info(f"Updated target: {safe_target_log(name, ip, port)}")
            else:
                t = Target(
                    customer_id=customer_id,
                    name=name,
                    encrypted_value=encrypted_value,
                    fingerprint=fingerprint
                )
                s.add(t)
                logger.info(f"Created target: {safe_target_log(name, ip, port)}")
            s.flush()
            return t
    
    def list_customer_targets(self, customer_id: int) -> List[Target]:
        with self.session_scope() as s:
            return s.query(Target).filter_by(customer_id=customer_id).all()
    
    def get_target_decrypted(self, target: Target) -> tuple:
        """Decrypt target to (ip, port)"""
        decrypted = self.crypto.decrypt(target.encrypted_value)
        ip, port = decrypted.rsplit(":", 1)
        return ip, int(port)
    
    def remove_target(self, customer_id: int, name: str) -> bool:
        """Remove a target by name. Returns True if removed."""
        with self.session_scope() as s:
            t = s.query(Target).filter_by(customer_id=customer_id, name=name).first()
            if t:
                s.delete(t)
                logger.info(f"Removed target: [encrypted] for customer {mask_chat_id(customer_id)}")
                return True
            return False
    
    def toggle_target_mode(self, customer_id: int, name: str, enable: bool) -> bool:
        """Toggle target enabled/disabled. Returns True if successful."""
        with self.session_scope() as s:
            t = s.query(Target).filter_by(customer_id=customer_id, name=name).first()
            if t:
                t.enabled = enable
                mode_str = "enabled" if enable else "disabled"
                logger.info(f"Target [encrypted] {mode_str} for customer {mask_chat_id(customer_id)}")
                return True
            return False
    
    def toggle_all_targets(self, customer_id: int, enable: bool) -> int:
        """Toggle all targets for a customer. Returns count of updated targets."""
        with self.session_scope() as s:
            targets = s.query(Target).filter_by(customer_id=customer_id).all()
            count = 0
            for t in targets:
                t.enabled = enable
                count += 1
            
            if count > 0:
                mode_str = "enabled" if enable else "disabled"
                logger.info(f"All {count} targets {mode_str} for customer {mask_chat_id(customer_id)}")
            
            return count
    
    def count_customer_targets(self, customer_id: int) -> int:
        """Count targets for a customer"""
        with self.session_scope() as s:
            return s.query(Target).filter_by(customer_id=customer_id).count()
    
    def update_target_checked(self, target_id: int, timestamp: int, failed: bool) -> None:
        with self.session_scope() as s:
            t = s.get(Target, target_id)
            if t:
                t.last_checked = timestamp
                if failed:
                    t.consecutive_failures += 1
                else:
                    t.consecutive_failures = 0
    
    # === Benchmark target methods ===
    # === Benchmark target methods ===
    
    def add_benchmark_target(self, chat_id: int, target_name: str, network: str = "mainnet") -> bool:
        """Add a benchmark target for user"""
        with self.session_scope() as s:
            # Check if already exists
            existing = s.query(BenchmarkTarget).filter_by(
                chat_id=chat_id,
                fingerprint=self.crypto.hash_value(target_name)
            ).first()
            
            if existing:
                # Update network if exists
                existing.network = network
                logger.info(f"Updated benchmark: {safe_bench_log(target_name, network)} for user {mask_chat_id(chat_id)}")
                return True

            # Create new
            encrypted = self.crypto.encrypt(target_name)
            fingerprint = self.crypto.hash_value(target_name)

            import time
            bt = BenchmarkTarget(
                chat_id=chat_id,
                encrypted_value=encrypted,
                fingerprint=fingerprint,
                network=network,
                created_at=int(time.time())
            )
            s.add(bt)
            logger.info(f"Added benchmark: {safe_bench_log(target_name, network)} for user {mask_chat_id(chat_id)}")
            return True
    
    def remove_benchmark_target(self, chat_id: int, target_name: str) -> bool:
        """Remove a benchmark target"""
        with self.session_scope() as s:
            fingerprint = self.crypto.hash_value(target_name)
            bt = s.query(BenchmarkTarget).filter_by(
                chat_id=chat_id,
                fingerprint=fingerprint
            ).first()
            
            if bt:
                s.delete(bt)
                logger.info(f"Removed benchmark: {safe_bench_log(target_name, 'unknown')} for user {mask_chat_id(chat_id)}")
                return True
            return False
    
    def list_benchmark_targets(self, chat_id: int) -> List[tuple]:
        """Get all benchmark targets for user. Returns list of (target_name, network) tuples"""
        with self.session_scope() as s:
            targets = s.query(BenchmarkTarget).filter_by(chat_id=chat_id).all()
            result = []
            for bt in targets:
                target_name = self.crypto.decrypt(bt.encrypted_value)
                network = bt.network or "mainnet"
                result.append((target_name, network))
            return result
    
    def count_benchmark_targets(self, chat_id: int) -> int:
        """Count benchmark targets for user"""
        with self.session_scope() as s:
            return s.query(BenchmarkTarget).filter_by(chat_id=chat_id).count()
    
    def get_benchmark_target(self, chat_id: int) -> Optional[tuple]:
        """Get first benchmark target (backwards compatibility)"""
        targets = self.list_benchmark_targets(chat_id)
        return targets[0] if targets else None
    
    def set_benchmark_target(self, chat_id: int, target_name: str, network: str = "mainnet") -> None:
        """Deprecated: use add_benchmark_target instead"""
        self.add_benchmark_target(chat_id, target_name, network)
    # === History methods ===
    
    def write_history(
        self,
        customer_chat_id: int,
        target_name: str,
        status: str,
        error: str,
        response_time: float
    ) -> None:
        with self.session_scope() as s:
            import time
            h = History(
                timestamp=int(time.time()),
                customer_chat_id=customer_chat_id,
                target_name=target_name,
                status=status,
                error=error or "",
                response_time=response_time
            )
            s.add(h)
    
    def get_recent_history(self, customer_chat_id: int, limit: int = 20) -> List[History]:
        with self.session_scope() as s:
            return (
                s.query(History)
                .filter_by(customer_chat_id=customer_chat_id)
                .order_by(History.timestamp.desc())
                .limit(limit)
                .all()
            )
    
    # === Audit methods ===
    
    def audit(self, actor_chat_id: int, action: str, details: str) -> None:
        with self.session_scope() as s:
            import time
            log = AuditLog(
                actor_chat_id=actor_chat_id,
                action=action,
                details=details,
                created_at=int(time.time())
            )
            s.add(log)
            logger.info(f"Audit: {mask_chat_id(actor_chat_id)} - {action}")
    
    # === Delete account ===
    
    def delete_user_data(self, chat_id: int) -> None:
        """Delete all user data (GDPR compliance)"""
        with self.session_scope() as s:
            # Delete customer and all targets (cascade)
            customer = s.query(Customer).filter_by(chat_id=chat_id).first()
            if customer:
                s.delete(customer)
            
            # Delete benchmark target
            bt = s.query(BenchmarkTarget).filter_by(chat_id=chat_id).first()
            if bt:
                s.delete(bt)
            
            # Delete history
            s.query(History).filter_by(customer_chat_id=chat_id).delete()
            
            # Delete subscription
            sub = s.get(Subscription, chat_id)
            if sub:
                s.delete(sub)
            
            # Audit log
            import time
            s.add(AuditLog(
                actor_chat_id=chat_id,
                action="delete_account",
                details="User deleted all data",
                created_at=int(time.time())
            ))
            
            logger.info(f"Deleted all data for user: {mask_chat_id(chat_id)}")