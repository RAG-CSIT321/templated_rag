from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from langchain_core.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser

def runllm1(file_name,config):
    llms = ChatGoogleGenerativeAI(model=config.MODEL_NAME,google_api_key=config.MODEL_API_KEY)
    embeddings = GoogleGenerativeAIEmbeddings(model=config.MODEL_EMBEDDING_NAME,google_api_key=config.MODEL_API_KEY)
    r = redis.Redis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        password=config.REDIS_PASSWORD)
    url=config.REDIS_URL
    
    vstore = Redis.from_texts(
            texts= [datas.page_content for datas in data],
            metadatas=[datas.metadata for datas in data],
            embedding=embedding_model,
            index_name="Movieidx",
            redis_url=url,
        )
    prompt = PromptTemplate.from_template(template)
    
    rag_chain_from_docs = (
        RunnablePassthrough.assign(context=(lambda x: format_docs(x["context"])))
        | prompt
        | llm
        | StrOutputParser()
    )
    
    rag_chain_with_source = RunnableParallel(
        {"context": compression_retriever, "input": RunnablePassthrough(), "table": (lambda x: table_text)}
    ).assign(answer=rag_chain_from_docs)
    
    answer = rag_chain_with_source.invoke(query)
    sources = format_sources(answer["context"])
    source_name_list = converting_to_org_name(sources)
    
    return {
        "source_name_list": source_name_list,
        "answer": answer["answer"]
    }