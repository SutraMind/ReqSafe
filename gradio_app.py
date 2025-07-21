import gradio as gr
import os
import shutil
import textwrap
import nest_asyncio
from dotenv import load_dotenv, find_dotenv
from langchain_community.document_loaders import PyPDFLoader, UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_models import ChatOllama

nest_asyncio.apply()
load_dotenv(find_dotenv())

# Embedding using BGE-large-en
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-large-en")
persist_path = "./faiss_index"
req_file_name = ""

def wrap_text_preserve_newlines(text, width=110):
    lines = text.split('\n')
    return '\n'.join([textwrap.fill(line, width=width) for line in lines])

def process_llm_response(llm_response):
    if 'result' not in llm_response or 'source_documents' not in llm_response:
        return "Invalid LLM response format."

    response = wrap_text_preserve_newlines(llm_response['result'])
    sources = "\n\nSources:\n" + "\n".join(
        source.metadata.get('source', 'Unknown') for source in llm_response["source_documents"]
    )
    return response + sources

def save_response_to_file(response, filename):
    with open(filename, 'w') as f:
        f.write(response + '\n')

def save_files_req(uploaded_file):
    global req_file_name
    os.makedirs("./requirements", exist_ok=True)
    file_name = os.path.basename(uploaded_file.name)
    req_file_name = file_name
    file_path = os.path.join("./requirements", file_name)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(uploaded_file, f)
    return f"✅ Requirement File Saved: {file_name}"

def save_files_policies(uploaded_files):
    os.makedirs("./policies", exist_ok=True)
    saved = []
    for file in uploaded_files:
        name = os.path.basename(file.name)
        path = os.path.join("./policies", name)
        with open(path, "wb") as f:
            shutil.copyfileobj(file, f)
        saved.append(name)
    return f"✅ Policies Saved: {', '.join(saved)}"

def process_doc():
    global req_file_name
    loader = PyPDFLoader(f"./requirements/{req_file_name}")
    pages = loader.load_and_split()
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(chunk_size=1000, chunk_overlap=100)
    docs = splitter.split_documents(pages)

    db = FAISS.from_documents(documents=docs, embedding=embeddings)
    db.save_local(persist_path)
    return "✅ FAISS vectorstore created."

def talk_to_model(selected_model):
    db = FAISS.load_local(persist_path, embeddings, allow_dangerous_deserialization=True)
    retriever = db.as_retriever(search_kwargs={"k": 5})

    try:
        with open("prompt.txt", "r") as f:
            question = f.read()
    except FileNotFoundError:
        return "❌ prompt.txt not found."

    prompt = PromptTemplate(
        input_variables=["history", "context", "question"],
        template="""
You are a software compliance checker for GDPR.
Use the context below between <ctx></ctx> and chat history <hs></hs> to answer the question:
<ctx>
{context}
</ctx>
<hs>
{history}
</hs>
Question: {question}
Answer:
""")

    llm = ChatOllama(model=selected_model, temperature=0.3)

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={
            "verbose": False,
            "prompt": prompt,
            "memory": ConversationBufferMemory(memory_key="history", input_key="question")
        }
    )

    response = qa_chain(question)
    result = process_llm_response(response)
    save_response_to_file(result, "./ollama_report.txt")
    return result

# ----------------- UI -----------------

with gr.Blocks() as demo:
    gr.Markdown("## GDPR Compliance Checker using Ollama + BGE + FAISS")

    with gr.Row():
        uploaded_files_policies = gr.File(file_count="multiple", label="Upload Policy PDFs")
        uploaded_files_req = gr.File(file_count="single", file_types=[".pdf"], label="Upload Requirements PDF")

    with gr.Row():
        save_btn_policies = gr.Button("Save Policy Files")
        save_btn_req = gr.Button("Save Requirement File")
        process_btn = gr.Button("Step 3: Process Documents")
        run_btn = gr.Button("Step 4: Run Compliance Check")

    model_choice = gr.Dropdown(["qwq:32b", "gemma:27b"], label="Select Ollama Model")

    status = gr.Textbox(label="Status", interactive=False)
    output = gr.TextArea(label="Compliance Report", lines=20)

    save_btn_policies.click(save_files_policies, inputs=[uploaded_files_policies], outputs=[status])
    save_btn_req.click(save_files_req, inputs=[uploaded_files_req], outputs=[status])
    process_btn.click(process_doc, outputs=[status])
    run_btn.click(talk_to_model, inputs=[model_choice], outputs=[output])

if __name__ == "__main__":
    demo.launch()
