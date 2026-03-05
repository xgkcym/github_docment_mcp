import os
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings
import dotenv

from src.utils import config

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
    vector_index_name: str = Field(default=os.getenv("VECTOR_INDEX_NAME"))
    fts_index_name:str = Field(default=os.getenv("FTS_INDEX_NAME"))
    embedding_dimensions: int = Field(default=int(os.getenv("EMBEDDING_DIMENSIONS")))
    embed_batch_size:int = Field(default= 10 if int(os.getenv("EMBED_BATCH_SIZE")) >= 10 else int(os.getenv("EMBED_BATCH_SIZE")))
    similarity_top_k:int = Field(default=int(os.getenv("SIMILARITY_TOP_K")))

    chunk_size:int = Field(default=int(os.getenv("CHUNK_SIZE")))
    chunk_overlap:int = Field(default=int(os.getenv("CHUNK_OVERLAP")))
    separator:str = Field(default="\n\n")

    chroma_data_url:str = Field(default=str(config.chroma_data_dir))
    # github
    github_api_key: str = Field(default=os.getenv("GITHUB_API_KEY"))
    github_timeout: int = Field(default=int(os.getenv("GITHUB_TIMEOUT")))
    #查询的后缀文档
    file_extensions:List[str] = Field(default=['.md','.mdx'])
    github_concurrent_requests: int = Field(default=int(os.getenv("GITHUB_CONCURRENT_REQUESTS")))

    default_embedding_api_key:str = Field(default=os.getenv("DEFAULT_EMBEDDING_API_KEY"))
    default_embedding_model:str = Field(default=os.getenv("DEFAULT_EMBEDDING_MODEL"))

    default_llm_model:str = Field(default=os.getenv("DEFAULT_LLM_MODEL"))
    default_llm_base_url:str = Field(default=os.getenv("DEFAULT_LLM_BASE_URL"))
    default_llm_api_key:str = Field(default=os.getenv("DEFAULT_LLM_API_KEY"))

    cross_encoder_model:str = Field(default=os.getenv("CROSS_ENCODER_MODEL"))
    cross_encoder_top_k:int = Field(default=int(os.getenv("CROSS_ENCODER_TOP_K")))

    hf_token:str = Field(default=os.getenv("HF_TOKEN"))

    #翻译
    allow_trans:bool = Field(default=True if os.getenv("ALLOW_TRANS") == "true" else False)
    niu_trans_to:str = Field(default=os.getenv("NIU_TRANS_TO"))
    niu_trans_appId:str= Field(default=os.getenv("NIU_TRANS_APPID"))
    niu_trans_api_key:str = Field(default=os.getenv("NIU_TRANS_API_KEY"))
    niu_trans_url:str = Field(default=os.getenv("NIU_TRANS_URL"))

settings = Settings()