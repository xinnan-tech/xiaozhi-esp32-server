"""数据库连接管理 - SQLAlchemy 2.0 同步引擎

两个数据库:
1. feedback_db - 反馈系统独立数据库
2. xiaozhi_esp32_server - xiaozhi 主数据库（仅用于注册设备到 ai_device 表）
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.shared.config import settings


class Base(DeclarativeBase):
    """ORM 基类"""
    pass


# ---- 反馈系统数据库 (feedback_db) ----
engine = create_engine(
    settings.database_url,
    pool_size=settings.database.get("pool_size", 10),
    max_overflow=settings.database.get("max_overflow", 20),
    pool_recycle=settings.database.get("pool_recycle", 3600),
    echo=settings.server.get("debug", False),
)

SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_session():
    """获取 feedback_db session（FastAPI 依赖注入）"""
    session = SessionFactory()
    try:
        yield session
    finally:
        session.close()


def init_database():
    """初始化 feedback_db 数据库表"""
    Base.metadata.create_all(bind=engine)
    _ensure_feedback_record_crm_columns()
    _ensure_feedback_record_identity_columns()
    _ensure_suggestion_columns()
    _ensure_member_product_columns()
    _ensure_product_columns()


def _ensure_product_columns():
    columns = {
        "duration_minutes": "ALTER TABLE crm_product ADD COLUMN duration_minutes INT NULL DEFAULT 60 COMMENT '默认服务时长'",
    }
    try:
        with engine.begin() as conn:
            existing_columns = {row[0] for row in conn.execute(text("SHOW COLUMNS FROM crm_product"))}
            for name, ddl in columns.items():
                if name not in existing_columns:
                    conn.execute(text(ddl))
    except Exception:
        pass


def _ensure_member_product_columns():
    """兼容已有库：为 crm_member_product 补齐购买计算字段。"""
    columns = {
        "unit_price": "ALTER TABLE crm_member_product ADD COLUMN unit_price DECIMAL(12,2) NULL DEFAULT 0 COMMENT '购买时单价'",
        "purchase_count": "ALTER TABLE crm_member_product ADD COLUMN purchase_count INT NULL DEFAULT 0 COMMENT '购买数量/次数'",
        "discount": "ALTER TABLE crm_member_product ADD COLUMN discount DECIMAL(5,2) NULL DEFAULT 1 COMMENT '折扣系数'",
    }
    try:
        with engine.begin() as conn:
            existing_columns = {row[0] for row in conn.execute(text("SHOW COLUMNS FROM crm_member_product"))}
            for name, ddl in columns.items():
                if name not in existing_columns:
                    conn.execute(text(ddl))
    except Exception:
        pass


def _ensure_suggestion_columns():
    """兼容已有库：为 crm_suggestion 补齐建议管理字段。"""
    columns = {
        "tags": "ALTER TABLE crm_suggestion ADD COLUMN tags JSON NULL COMMENT '标签'",
        "priority": "ALTER TABLE crm_suggestion ADD COLUMN priority VARCHAR(16) NULL DEFAULT 'medium' COMMENT '优先级'",
        "source": "ALTER TABLE crm_suggestion ADD COLUMN source VARCHAR(32) NULL DEFAULT 'manual' COMMENT '来源'",
        "submitter_name": "ALTER TABLE crm_suggestion ADD COLUMN submitter_name VARCHAR(64) NULL COMMENT '提出人'",
    }
    try:
        with engine.begin() as conn:
            existing_columns = {row[0] for row in conn.execute(text("SHOW COLUMNS FROM crm_suggestion"))}
            for name, ddl in columns.items():
                if name not in existing_columns:
                    conn.execute(text(ddl))
    except Exception:
        # 表不存在时 create_all 会负责创建；这里只做兼容补列
        pass


def _ensure_feedback_record_identity_columns():
    """兼容已有库：为 feedback_record 补齐客户身份辅助字段。"""
    columns = {
        "customer_name": "ALTER TABLE feedback_record ADD COLUMN customer_name VARCHAR(64) NULL COMMENT '客户称呼/自报姓名'",
        "phone_tail": "ALTER TABLE feedback_record ADD COLUMN phone_tail VARCHAR(4) NULL COMMENT '客户手机号后四位'",
        "member_match_status": "ALTER TABLE feedback_record ADD COLUMN member_match_status VARCHAR(32) NULL COMMENT '客户匹配状态'",
        "member_match_candidates": "ALTER TABLE feedback_record ADD COLUMN member_match_candidates JSON NULL COMMENT '手机号后四位匹配候选客户'",
    }
    indexes = {
        "idx_feedback_record_phone_tail": "ALTER TABLE feedback_record ADD INDEX idx_feedback_record_phone_tail (phone_tail)",
    }
    try:
        with engine.begin() as conn:
            existing_columns = {row[0] for row in conn.execute(text("SHOW COLUMNS FROM feedback_record"))}
            for name, ddl in columns.items():
                if name not in existing_columns:
                    conn.execute(text(ddl))
            existing_indexes = {row[2] for row in conn.execute(text("SHOW INDEX FROM feedback_record"))}
            for name, ddl in indexes.items():
                if name not in existing_indexes:
                    conn.execute(text(ddl))
    except Exception:
        pass


def _ensure_feedback_record_crm_columns():
    """兼容已有库：为 feedback_record 补齐 CRM 关联字段。"""
    columns = {
        "member_id": "ALTER TABLE feedback_record ADD COLUMN member_id VARCHAR(64) NULL COMMENT '关联客户ID'",
        "visit_id": "ALTER TABLE feedback_record ADD COLUMN visit_id VARCHAR(64) NULL COMMENT '关联到店记录ID'",
        "card_close_id": "ALTER TABLE feedback_record ADD COLUMN card_close_id VARCHAR(64) NULL COMMENT '关联销卡记录ID'",
    }
    indexes = {
        "idx_feedback_record_member_id": "ALTER TABLE feedback_record ADD INDEX idx_feedback_record_member_id (member_id)",
        "idx_feedback_record_visit_id": "ALTER TABLE feedback_record ADD INDEX idx_feedback_record_visit_id (visit_id)",
        "idx_feedback_record_card_close_id": "ALTER TABLE feedback_record ADD INDEX idx_feedback_record_card_close_id (card_close_id)",
    }
    with engine.begin() as conn:
        existing_columns = {row[0] for row in conn.execute(text("SHOW COLUMNS FROM feedback_record"))}
        for name, ddl in columns.items():
            if name not in existing_columns:
                conn.execute(text(ddl))
        existing_indexes = {row[2] for row in conn.execute(text("SHOW INDEX FROM feedback_record"))}
        for name, ddl in indexes.items():
            if name not in existing_indexes:
                conn.execute(text(ddl))


# ---- xiaozhi 主数据库 (xiaozhi_esp32_server) ----
def _build_xiaozhi_db_url():
    """构建 xiaozhi 主库连接 URL（同 MySQL 实例，不同 schema）"""
    db = settings.database
    return (
        f"mysql+pymysql://{db['username']}:{db['password']}"
        f"@{db['host']}:{db['port']}/xiaozhi_esp32_server"
        f"?charset={db.get('charset', 'utf8mb4')}"
    )


_xiaozhi_engine = None


def get_xiaozhi_engine():
    """懒加载 xiaozhi 主库引擎"""
    global _xiaozhi_engine
    if _xiaozhi_engine is None:
        _xiaozhi_engine = create_engine(
            _build_xiaozhi_db_url(),
            pool_size=3,
            max_overflow=5,
            pool_recycle=3600,
        )
    return _xiaozhi_engine


def register_device_in_xiaozhi(device_mac: str, agent_id: str, alias: str = "") -> bool:
    """在 xiaozhi 的 ai_device 表中注册/更新设备

    这样 H5 调用 OTA 时，xiaozhi-server 能识别设备并直接返回 WS URL，
    不需要激活码。
    """
    try:
        eng = get_xiaozhi_engine()
        with eng.connect() as conn:
            # 检查设备是否已存在
            result = conn.execute(
                text("SELECT id FROM ai_device WHERE mac_address = :mac"),
                {"mac": device_mac}
            )
            existing = result.fetchone()

            if existing:
                # 更新 agent_id
                conn.execute(
                    text("UPDATE ai_device SET agent_id = :agent_id, alias = :alias WHERE mac_address = :mac"),
                    {"agent_id": agent_id, "alias": alias or "反馈H5设备", "mac": device_mac}
                )
            else:
                # 插入新设备
                conn.execute(
                    text("""
                        INSERT INTO ai_device (id, mac_address, agent_id, alias, auto_update, sort, create_date)
                        VALUES (:id, :mac, :agent_id, :alias, 0, 0, NOW())
                    """),
                    {
                        "id": device_mac.replace(":", "")[:32],
                        "mac": device_mac,
                        "agent_id": agent_id,
                        "alias": alias or "反馈H5设备",
                    }
                )
            conn.commit()
        return True
    except Exception as e:
        from loguru import logger
        logger.warning(f"注册设备到 xiaozhi 主库失败: {e}")
        return False
