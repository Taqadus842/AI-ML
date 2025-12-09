# 🚀 **AI-Powered Customer Support Email Automation**


## **Introduction**

Managing customer emails can be slow and tiring. Support teams often deal with many messages every day, and it takes a lot of time to sort them, understand the request, write replies, and double-check everything. This can cause delays and mistakes, which affects customer satisfaction.

I built this **Customer Support Email Automation System** to help solve that problem.
Using **Langgraph**, the system uses several **AI agents** that work together to read emails, categorize them, create replies, and check the quality of the messages before they are sent. It also uses **RAG (Retrieval-Augmented Generation)** to answer questions using information from your own documents.

The goal is simple: **faster, clearer, and more accurate customer support emails**.

---

## **Features**

### ⭐ Email Management with AI Agents

* Automatically watches your Gmail inbox
* Sorts emails into: **complaint**, **product inquiry**, **feedback**, or **unrelated**
* Ignores irrelevant emails to keep the workflow clean

### ⭐ AI Email Response Generation

* Creates quick replies for complaints and feedback
* Uses **RAG** to give accurate answers for product or service questions
* Generates **personalized** emails for each customer

### ⭐ AI Quality Check

* Reviews every draft email
* Checks formatting, clarity, and relevance
* Makes sure the final message looks professional before sending

---

## **How the System Works**

1. **Email Monitoring** – The system keeps checking your Gmail inbox for new emails using the Gmail API.
2. **Email Categorization** – AI agents sort each email into the correct category.
3. **Response Creation**

   * Complaints & feedback → AI writes a suitable reply.
   * Product/service questions → AI uses RAG to find the correct info from your documents and writes the answer.
4. **Quality Review** – Another AI agent checks the draft email for mistakes or missing details.
5. **Sending** – The approved email is sent to the customer automatically.

---

## **Tech Stack**

* **Langchain & Langgraph** – For AI agent workflows
* **Langserve** – For API deployment with FastAPI
* **Groq & Google Gemini APIs** – For LLMs and embeddings
* **Gmail API** – For reading and sending emails

---

## **How to Run the Project**

### ✅ Requirements

* Python 3.7+
* Groq API key
* Google Gemini API key
* Gmail API credentials
* Packages listed in `requirements.txt`

### ⚙️ Setup

1. **Clone the repo**

   ```sh
   git clone https://github.com/Taqadus842/AI-ML/langgraph-email-automation.git
   cd langgraph-email-automation
   ```

2. **Create and activate a virtual environment**

   ```sh
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```sh
   pip install -r requirements.txt
   ```

4. **Add environment variables**
   Create a `.env` file and add:

   ```env
   MY_EMAIL=your_email@gmail.com
   GROQ_API_KEY=your_groq_api_key
   GOOGLE_API_KEY=your_gemini_api_key
   ```

5. **Enable Gmail API**
   Follow the Google guide to enable Gmail API and download your credentials.

---

## **Running the Application**

### ▶️ Start the workflow

```sh
python main.py
```

This will start checking emails, categorizing them, generating replies, and verifying quality.

### ▶️ Run it as an API

```sh
python deploy_api.py
```

The API will run at **localhost:8000**, with documentation available at `/docs` and a playground at `/playground`.

---

## **Customization**

* You can edit how each agent works by modifying the methods inside the `Nodes` class.
* You can change the prompts inside the `prompts` folder.
* You can add new data for RAG inside the `data` folder and rebuild the vector store:

```sh
python create_index.py
```

---

✅ make it fun or casual
Just tell me!
