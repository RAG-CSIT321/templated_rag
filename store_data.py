from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.node_parser import TokenTextSplitter

class StoreData:
    def __init__(self, data_dir="data", storage_dir="data_storage"):
        self.data_dir = data_dir
        self.storage_dir = storage_dir
        self.index = None

    def process_data(self):
        """Process files in the data directory and update the index."""
        reader = SimpleDirectoryReader(input_dir=self.data_dir)
        documents = reader.load_data()

        splitter = TokenTextSplitter(chunk_size=512, chunk_overlap=10, separator=" ")
        nodes = splitter.get_nodes_from_documents(documents)

        self.index = VectorStoreIndex(nodes)
        self.index.storage_context.persist(persist_dir=self.storage_dir)
        return self.index

    def load_index(self):
        """Load the persisted index."""
        from llama_index.core import StorageContext, load_index_from_storage
        storage_context = StorageContext.from_defaults(persist_dir=self.storage_dir)
        self.index = load_index_from_storage(storage_context)
        return self.index