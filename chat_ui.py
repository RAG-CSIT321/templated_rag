import webview
from chat_history import ChatHistory

class ChatUI:
    def __init__(self, chatApi):
        self.chatApi = chatApi
        self.chat_history = ChatHistory()  # Initialize ChatHistory class

    def launch(self):
        """
        Launch the chatbot app using Pywebview.
        """
        with open("chat_ui.html", "r") as html_file:
            html_content = html_file.read()

        # Create and launch the PyWebView window
        window = webview.create_window(
            title="Chatbot App with File Upload and History",
            html=html_content,
            js_api=self.chatApi,
            width=800,
            height=600
        )
        webview.start()


