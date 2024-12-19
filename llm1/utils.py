from langchain_community.document_loaders import CSVLoader,PyPDFLoader,WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
# This function is to convert the documents' temporary names to their original names.
def converting_to_org_name(string):
    name_list = list(string.split("\n"))
    return [name[16:] for name in name_list]
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# Returning the document names (not pages)
def format_sources(docs):
    return "\n".join(doc.metadata["source"] for doc in docs)
def load_docs_Web(url):
    loader = WebBaseLoader(url)
    return loader.load()
def load_docs_PDF(name):
    loader = PyPDFLoader(name)
    return loader.load()
def load_docs_CSV(name):
    loader = CSVLoader(file_path=name, encoding="utf-8", csv_args={
                'delimiter': ','})
    return loader.load()
    
def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    return text_splitter.split_documents(text)

def get_vector_store(text_chunks, config):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001",google_api_key='AIzaSyCCDH1LZgcluEGoXnJRyrEZ21aLTBXScK0')
    vectorstore = FAISS.from_documents(documents=text_chunks, embedding=embeddings)
    return vectorstore.as_retriever()

def load_faiss_index(config):
    embeddings = GoogleGenerativeAIEmbeddings(model=config.MODEL_EMBEDDING_NAME, cohere_api_key=config.cohere_api_key)
    return FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
