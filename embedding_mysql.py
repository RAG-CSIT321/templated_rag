import mysql.connector
from langchain.schema import Document  # or use your own Document class
def embedding_mysql():
    conn = mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="12345678",
        database="movie"
    )
    cursor = conn.cursor()
    # Query
    cursor.execute("SELECT * FROM test")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    # Convert each row into a Document
    documents = []
    for row in rows:
        contents = dict(zip(columns, row))
        # Add movies_database as the id
        content = "\n".join(f"{col}: {val}" for col, val in contents.items())
        content = "{" + content + "}"
        metadata = {'source': 'movies_database'}
        doc = Document(page_content=content, metadata=metadata)
        documents.append(doc)
    # Cleanup
    cursor.close()
    conn.close()
    return documents


