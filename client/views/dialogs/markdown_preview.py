import markdown
from PyQt5.QtWidgets import QVBoxLayout, QDialog
from PyQt5.QtWebEngineWidgets import QWebEngineView
 
class MarkdownPreviewDialog(QDialog):
    def __init__(self, markdown_text: str, title="Markdown Preview", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(800, 600)

        html_content = markdown.markdown(markdown_text, extensions=["fenced_code", "tables"])

        full_html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/styles/github-dark.min.css">
            <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/highlight.min.js"></script>
            <script>hljs.highlightAll();</script>
            <style>
                body {{
                    font-family: sans-serif;
                    padding: 20px;
                    background-color: #1e1e1e;
                    color: #ddd;
                }}
                h1, h2, h3, h4 {{
                    color: #ffffff;
                }}
                pre {{
                    background: #2d2d2d;
                    padding: 10px;
                    border-radius: 6px;
                    overflow-x: auto;
                }}
            </style>
        </head>
        <body>{html_content}</body>
        </html>
        """

        view = QWebEngineView()
        view.setHtml(full_html)

        layout = QVBoxLayout(self)
        layout.addWidget(view)
