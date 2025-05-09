import mysql.connector
from langchain.schema import Document  # or use your own Document class
# Connect to MySQL
# class mysql_connection:
#     def __init__(self):
#         pass
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
        metadata = dict(zip(columns, row))
        content = "\n".join(f"{col}: {val}" for col, val in metadata.items())
        doc = Document(page_content=content, metadata=metadata)
        documents.append(doc)
    # Cleanup
    cursor.close()
    conn.close()
    return documents


