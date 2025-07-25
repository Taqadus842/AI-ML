import gradio as gr
import numpy as np
from PIL import Image
import joblib

# Load your trained model
model = joblib.load("model.joblib")

def predict_digit(image):
    try:
        if image is None:
            return "Please upload an image."
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)

        # Convert image to grayscale and resize to 28x28
        image = image.convert("L").resize((28, 28))

        # Convert image to numpy array
        img_array = np.array(image)

        # Flatten the image
        img_array = img_array.reshape(1, -1)

        # Make prediction
        prediction = model.predict(img_array)[0]
        return f"Predicted Digit: {prediction}"
    except Exception as e:
        return f"Error: {str(e)}"

# Create Gradio interface
interface = gr.Interface(
    fn=predict_digit,
    inputs=gr.Image(image_mode="L", sources=["upload", "webcam"], label="Upload a digit image"),
    outputs="text"
)

interface.launch()
