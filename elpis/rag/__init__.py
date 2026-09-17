"""RAG（检索增强生成）模块

让 Agent 能够检索私有知识库（文档、笔记、代码库等），基于检索到的内容回答问题。

典型 RAG 流程：
1. 文档加载（Load）：读取各种格式的文档
2. 文本分割（Split）：把长文档切成小块（chunks）
3. 向量化（Embed）：把文本块转成向量
4. 存储（Store）：存入向量数据库
5. 检索（Retrieve）：根据用户查询检索相关文档块
6. 增强生成（Generate）：把检索到的内容加入提示词，让 LLM 基于知识库回答

未来可以加：
- loaders/：文档加载器（PDF、Word、Markdown、网页、代码文件等）
- splitters.py：文本分割器（按字符、按语义、按递归等）
- embeddings.py：向量化封装（OpenAI Embeddings、本地模型等）
- vector_store.py：向量存储（Chroma、FAISS、Milvus 等）
- retriever.py：检索器（相似度检索、关键词检索、混合检索）
- reranker.py：重排序（对检索结果重新排序，提升相关性）
- rag_chain.py：RAG 链路组装（检索→拼接提示词→生成）

使用场景：
- 让 Agent 查你的项目文档、笔记、知识库
- 基于私有代码库回答问题
- 客服/问答机器人，基于产品文档回答
"""
