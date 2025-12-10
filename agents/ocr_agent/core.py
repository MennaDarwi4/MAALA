import base64
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

class OCRAgent:
    def __init__(self, groq_api_key):
        # ✅ استخدم نموذج Vision المتاح في Groq
        self.llm = ChatGroq(
            groq_api_key=groq_api_key, 
            model_name="llama-3.3-70b-versatile"
        )

    def extract_text(self, image_path: str) -> str:
        """
        Extracts text from an image specified by its file path.
        """
        try:
            # Read image and encode as base64
            with open(image_path, "rb") as image_file:
                image_bytes = image_file.read()

            image_base64 = base64.b64encode(image_bytes).decode("utf-8")

            # Prepare the message for the vision model
            message = [
                HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": (
                                "Extract all the text from this image. "
                                "Return only the extracted text, no explanations. "
                                "Preserve the formatting as much as possible."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                )
            ]

            # Call the vision-capable model
            response = self.llm.invoke(message)
            return response.content.strip()

        except Exception as e:
            return f"Error extracting text: {str(e)}"