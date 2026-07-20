import os

from typing import List
from fastapi import UploadFile

from config.settings import GOOGLE_API_KEY, VECTORSTORE_DIRECTORY, MODEL_OPTIONS
from core.document_processor import save_uploaded_file, load_documents_from_paths, split_documents_to_chunks

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from utils.logger import logger


def vectorstore_exists(persist_path: str) -> bool:
  exists = os.path.exists(persist_path) and bool(os.listdir(persist_path))
  logger.debug(f"Vectorstore exists at {persist_path}: {exists}")
  return exists

def get_embeddings(model_provider: str):
  logger.debug(f"Getting embeddings for provider: {model_provider}")
  if model_provider == "groq":
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L12-v2")
  elif model_provider == "gemini":
    if not GOOGLE_API_KEY:
      raise ValueError("GOOGLE_API_KEY is required for gemini embeddings")
    return GoogleGenerativeAIEmbeddings(
      model="models/embedding-001",
      google_api_key=GOOGLE_API_KEY
    )
  else:
    logger.error(f"Unsupported LLM Provider: {model_provider}")
    raise ValueError(f"Unsupported LLM Provider: {model_provider}")

def initialize_empty_vectorstores():
  logger.info("Initializing empty vectorstores...")
  for provider in MODEL_OPTIONS.keys():
    persist_path = VECTORSTORE_DIRECTORY[provider]
    os.makedirs(persist_path, exist_ok=True)

    if not os.listdir(persist_path):
      try:
        embedding = get_embeddings(provider)
      except ValueError as exc:
        logger.warning(f"Skipping vectorstore initialization for {provider}: {exc}")
        continue

      Chroma(
        embedding_function=embedding,
        persist_directory=persist_path
      )
      logger.debug(f"Initialized vectorstore for {provider} at {persist_path}")

  logger.info("Vectorstore initialization complete.")

# upsert_vectorstore_from_pdfs()
#   ↓
# save_uploaded_file()
# 保存上传的 PDF
#   ↓
# load_documents_from_paths()
# 读取 PDF 内容，转成 Document
#   ↓
# split_documents_to_chunks()
# 切成 chunks
#   ↓
# get_embeddings()
# 选择 embedding 模型
#   ↓
# VECTORSTORE_DIRECTORY[model_provider]
# 确定 ChromaDB 保存路径
#   ↓
# vectorstore_exists(persist_path)?
#   ├── 是：Chroma(...) 加载已有库，然后 add_documents(chunks)
#   └── 否：Chroma.from_documents(...) 新建库
#   ↓
# return vectorstore

async def upsert_vectorstore_from_pdfs(uploaded_files: List[UploadFile], model_provider: str):
  logger.debug(f"Upserting vectorstore for {model_provider}")
  file_paths = await save_uploaded_file(uploaded_files)#把上传文件保存到本地。
  docs = load_documents_from_paths(file_paths)
  chunks = split_documents_to_chunks(docs)#把 PDF 文本切成适合检索的小块。
  embedding = get_embeddings(model_provider)#选择 embedding 模型，用于文本向量化。

  persist_path = VECTORSTORE_DIRECTORY[model_provider]

  if vectorstore_exists(persist_path):
    logger.debug("Appending to existing vectorstore...")
    vectorstore = Chroma(persist_directory=persist_path, embedding_function=embedding)
    vectorstore.add_documents(chunks)#把 chunks 写入 ChromaDB。
    logger.debug(f"Added {len(chunks)} chunks to existing vectorstore.")
  else:
    vectorstore = Chroma.from_documents(documents=chunks, embedding=embedding, persist_directory=persist_path)#把 chunks 写入 ChromaDB。
    logger.debug(f"Created new vectorstore with {len(chunks)} chunks.")

  return vectorstore

def load_vectorstore(model_provider: str):
  persist_path = VECTORSTORE_DIRECTORY[model_provider]
  logger.debug(f"Loading vectorstore from {persist_path}")

  if vectorstore_exists(persist_path):
    logger.debug(f"Loading existing vectorstore for provider: {model_provider}")
    return Chroma(persist_directory=persist_path, embedding_function=get_embeddings(model_provider))

  logger.debug(f"VectorStore not found for provider: {model_provider}")
  raise ValueError(f"VectorStore not found for provider: {model_provider}")

def get_collections_count(model_provider: str):
  logger.debug(f"Getting collection count for provider: {model_provider}")
  vectorstore = load_vectorstore(model_provider)
  return vectorstore._collection.count()

def find_similar_chunks(model_provider: str, query: str):
  logger.debug(f"Searching for similar chunks for provider: {model_provider}")
  vectorstore = load_vectorstore(model_provider)
  return vectorstore.similarity_search(query)
