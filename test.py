from controller_project import handle_request

def test_1():
    file_name='imdb_top_1000.csv'
    query = 'What are movies released in 1977 '
    print("testing result")
    result = handle_request(1,query,file_name)
    print(f"Testing result for {query}:\n {result}")
if __name__ == "__main__":
    test_1()
    print("\nAll tests completed.")
