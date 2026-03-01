import os

from pydantic import Field
from pydantic_settings import BaseSettings
import dotenv

dotenv.load_dotenv()
class Settings(BaseSettings):

    # UI
    enable_repo_management: bool = Field(default=True)

    #数据库名称
    db_name:str = Field(default=os.getenv("DB_NAME"))
    #数据库连接字符串
    mongodb_url: str = Field(default=os.getenv("MONGODB_URL"))
    #repos数据表名
    repos_collection_name: str = Field(default=os.getenv("REPOS_COLLECTION_NAME"))
    rag_collection_name: str = Field(default=os.getenv("RAG_COLLECTION_NAME"))

settings = Settings()