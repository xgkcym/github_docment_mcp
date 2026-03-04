from typing import  Optional

from pymongo import MongoClient
from pymongo.synchronous.collection import Collection
from pymongo.synchronous.database import Database

from src.core.settings import settings
from src.utils.logger_handler import logger


class MongoDBClient:
    """带有连接管理的 MongoDB 客户端包装器。"""
    def __init__(self):
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None

    @property
    def client(self)->MongoClient:
        """获取 MongoDB 客户端，支持延迟初始化。"""
        if self._client is None:
            try:
                self._client = MongoClient(settings.mongodb_url)
                self._client.admin.command("ping")
                logger.info("MongoDB数据库连接成功")
            except Exception as e:
                logger.error(f"MongoDB数据库连接失败 ${str(e)}")
                raise Exception(f"连接 MongoDB 失败：{e}") from e
        return self._client


    @property
    def database(self)->Database:
        """获取数据库实例。"""
        if self._db is None:
            self._db = self.client[settings.db_name]
        return self._db

    def get_collection(self,collection_name:str) -> Collection:
        """按名称获取集合。"""
        return self.database[collection_name]

    def test_connection(self) -> bool:
        """测试 MongoDB 连接。"""
        try:
            self.client.admin.command("ping")
            return True
        except Exception as e:
            logger.error(f"MongoDB 连接测试失败：{e}")
            return False


mongodb_client = MongoDBClient()