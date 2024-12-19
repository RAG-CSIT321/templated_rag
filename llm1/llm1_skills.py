from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI

import redis
from langchain.vectorstores.redis import Redis

from langchain_core.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain_core.runnables import RunnableParallel
from langchain.schema.output_parser import StrOutputParser
from langchain import hub

from llm1.utils import *

def runllm1(file_name,config,query):
    # tools required
    llms = ChatGoogleGenerativeAI(model=config.MODEL_NAME,google_api_key=config.MODEL_API_KEY)
    embeddings = GoogleGenerativeAIEmbeddings(model=config.MODEL_EMBEDDING_NAME,google_api_key=config.MODEL_API_KEY)
    r = redis.Redis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        password=config.REDIS_PASSWORD)
    url=config.REDIS_URL
    print(r.ping())
    r.flushdb()
    #CSV processing 
    data = load_docs_CSV(file_name)

    # store in vector database
    vstore = Redis.from_texts(
        texts= [datas.page_content for datas in data],
        #metadatas= file_name,
        embedding=embeddings,
        redis_url=url,
    )
    
    # get relevant context using vector database
    retriever = vstore.as_retriever(distance_threshold=0.5)
    print(retriever.invoke(query))
    prompt = hub.pull("rlm/rag-prompt")
    print(prompt)
    rag_chain_from_docs = (
        RunnablePassthrough.assign(context=(lambda x: format_docs(x["context"])))
        | prompt
        | llms
        | StrOutputParser()
    )
    
    rag_chain_with_source = RunnableParallel(
        {"context": retriever, "question": RunnablePassthrough()}
    ).assign(answer=rag_chain_from_docs)
    
    answer = rag_chain_with_source.invoke(query)
    #sources = format_sources(answer["context"])
    #source_name_list = converting_to_org_name(sources)
    
    return {
        #"source_name_list": source_name_list,
        "answer": answer["answer"]
    }
