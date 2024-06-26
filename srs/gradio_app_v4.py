
import gradio as gr
from gradio import themes
import os
from dotenv import find_dotenv, load_dotenv
import shutil
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.llms import OpenAI
from langchain.chains import RetrievalQA
from langchain_openai import OpenAIEmbeddings
# from langchain import PromptTemplate
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import DirectoryLoader
import textwrap
import google.generativeai as genai
import nest_asyncio
from llama_index.core import SimpleDirectoryReader
from langchain_community.document_loaders import UnstructuredFileLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_cohere import CohereEmbeddings
from langchain.document_loaders import PyPDFLoader
from langchain.memory import ConversationBufferMemory
from langchain_cohere import ChatCohere
import textwrap
nest_asyncio.apply()

from llama_parse import LlamaParse
# Load environment variables from .env file
load_dotenv(find_dotenv())

#Google Gemini Model
OPENAI_KEY = os.environ["OPENAI_API_KEY"]
GOOGLE_API_KEY = os.environ['GOOGLE_API_KEY']
genai.configure(api_key=GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-pro-latest')

# OpenAI
openai_embeddings_model = OpenAIEmbeddings(openai_api_key=OPENAI_KEY)
openai_llm = ChatOpenAI(openai_api_key=OPENAI_KEY, model_name="gpt-3.5-turbo-0125")
COHERE_API_KEY = os.environ['COHERE_API_KEY']

embd = CohereEmbeddings()
persist_directory = 'db_GDPR'
#LLAMA-INDEX
LLAMA_INDEX = os.environ['LLAMA_INDEX']
parser = LlamaParse(
    api_key=LLAMA_INDEX,  # can also be set in your env as LLAMA_CLOUD_API_KEY
    result_type="markdown",  # "markdown" and "text" are available
    num_workers=4,  # if multiple files passed, split in `num_workers` API calls
    verbose=True,
    language="en",  # Optionally you can define a language, default=en
)
req_file_name = ""
# list all the pdf files within requirements directory
def list_pdf_files(directory):
    pdf_files = []
    for filename in os.listdir(directory):
        if filename.endswith(".pdf"):
            pdf_files.append(os.path.join(directory, filename))
    return pdf_files

#saving the parsed pdf to MD file
def save_as_md(text, filename):
    with open(filename, "w") as file:
        file.write(text)


def wrap_text_preserve_newlines(text, width=110):
    # Split the input text into lines based on newline characters
    lines = text.split('\n')

    # Wrap each line individually
    wrapped_lines = [textwrap.fill(line, width=width) for line in lines]

    # Join the wrapped lines back together using newline characters
    wrapped_text = '\n'.join(wrapped_lines)
    wrapped_text_string = str(wrapped_text)

    return wrapped_text_string

def process_llm_response(llm_response):
    response = wrap_text_preserve_newlines(llm_response['result'])
    print(response)
    print('\n\nSources:')
    for source in llm_response["source_documents"]:
        print(source.metadata['source'])

    return response

def process_doc():
    global req_file_name
    re_path = "./requirements/"+ req_file_name
    print(re_path)
    loader = PyPDFLoader(re_path)
    req_pages = loader.load_and_split()
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=10000, chunk_overlap=0
    )
    doc_splits = text_splitter.split_documents(req_pages)
    

# Add to vectorstore
    req_vectorstore = Chroma.from_documents(
        documents=doc_splits,
        embedding=embd,
        persist_directory=persist_directory
    )
    
    # pdf_files_list = list_pdf_files("./requirements")
    # documents = parser.load_data(pdf_files_list)
    # print(len(documents))
    # print(documents)
    # text_to_save = documents[0].text
    # merged_text = "\n".join([doc.text for doc in documents])
    
    # # Save the concatenated text to a single file
    # save_as_md(merged_text, "./requirements/requirements_merged.txt")
    

    # loader = DirectoryLoader("./requirements",  glob="**/*.@(pdf)", show_progress=True, loader_cls=UnstructuredFileLoader)
    # data = loader.load()
    # print(data)
    return "Vector Databases have been created successfully"

   

def talk_to_model():
    req_vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embd)
    req_retriever = req_vectorstore.as_retriever(search_kwargs={"k": 5})
    gen_template = """
    You are an expert software requirements compliance checker against GDPR policy. Use the following context (delimited by <ctx></ctx>) and the chat history (delimited by <hs></hs>) to answer the question:
    ------
    <ctx>
    {context}
    </ctx>
    ------
    <hs>
    {history}
    </hs>
    ------
    {question}
    Answer:
    """
    prompt = PromptTemplate(
        input_variables=["history", "context", "question"],
        template=gen_template,
    )
    with open("prompt.txt", "r") as file:
        # Read the entire content of the file
        prompt_instruction = file.read()

    llm=ChatCohere(
        model = "command-r-plus",
        cohere_api_key=COHERE_API_KEY,
        MAX_TOKENS=120000)
    
    GDPR_qa_chain = RetrievalQA.from_chain_type(llm=llm,
                                  chain_type="stuff",
                                  retriever=req_retriever,
                                       chain_type_kwargs={
                                            "verbose": False,
                                            "prompt": prompt,
                                            "memory": ConversationBufferMemory(
                                                memory_key="history",
                                                input_key="question"),
                                        },
                                  return_source_documents=True)
    
    query = prompt_instruction
    llm_response = GDPR_qa_chain(query)
    response = process_llm_response(llm_response)
    save_response_to_file(response, './commandr_report.txt')
    return response

def save_response_to_file(response, filename):
    with open(filename, 'w') as file:
        file.write(response + '\n')

def process_summary():
    gemini_pro_model = genai.GenerativeModel('gemini-1.5-pro-latest')
    sample_file = genai.upload_file(path="./commandr_report.txt",
                                display_name="Compliance Report")
    response = gemini_pro_model.generate_content(["""Based on the generated compliance report, prepare the final report. Explicitly highlight those areas of the requirements that are non-compliant. Provide the summary and highlight key areas that require modifications with respect to GDPR compliance. Discard the 
repetitive information. Focus on adding more clarity in the final report. If you want to add something additionally to make enhance the quality of the report, you can add""", sample_file])
    return response.text

def save_files_policies(uploaded_files):
    current_directory = os.getcwd()
    upload_directory = os.path.join(current_directory, "policies")
    os.makedirs(upload_directory, exist_ok=True)  # Create the directory if it doesn't exist

    file_paths = []
    saved_files = [] # Keep track of saved files
    for file in uploaded_files:
        file_name = os.path.basename(file.name)
        
        file_path = os.path.join(upload_directory, file_name)
        shutil.copy(file.name, file_path)
        # file_paths.append(file_path)
        print(f"Copied file to: {file_path}")
        saved_files.append(file_name)

    return f"Saved files for Policies: {', '.join(saved_files)}" # Return success message


# Similar function for storing requirements files, returning a success message
# def save_files_req(uploaded_files):
#     current_directory = os.getcwd()
#     upload_directory = os.path.join(current_directory, "requirements")
#     os.makedirs(upload_directory, exist_ok=True)  # Create the directory if it doesn't exist
#     global req_file_name
#     file_paths = []
#     saved_files = [] # Keep track of saved files
#     for file in uploaded_files:
#         file_name = os.path.basename(file.name)
#         file_path = os.path.join(upload_directory, file_name)
#         req_file_name = file_name
#         shutil.copy(file.name, file_path)
#         file_paths.append(file_path)
#         print(f"Copied file to: {file_path}")
#         saved_files.append(file_name)

#     return f"Saved files for Policies: {', '.join(saved_files)}" # Return success message

def save_files_req(uploaded_file):
    current_directory = os.getcwd()
    upload_directory = os.path.join(current_directory, "requirements")
    os.makedirs(upload_directory, exist_ok=True)  # Create the directory if it doesn't exist
    global req_file_name

    file_name = os.path.basename(uploaded_file.name)
    file_path = os.path.join(upload_directory, file_name)
    req_file_name = file_name

    shutil.copy(uploaded_file.name, file_path)
    print(f"Copied file to: {file_path}")

    return f"Saved file for Requirement Specifications: {file_name}"

def run_models(model_1, api_key_1, model_2, api_key_2, uploaded_files_policies, uploaded_files_req):
    # Placeholder for running models
    return "Models are running with "+model_1+" "+api_key_1


# theme = gr.themes.Soft()

js_func = """
function refresh() {
    const url = new URL(window.location);

    if (url.searchParams.get('__theme') !== 'dark') {
        url.searchParams.set('__theme', 'dark');
        window.location.href = url.href;
    }
}
"""
with gr.Blocks(js=js_func) as demo:
    gr.Markdown(
        """
        ## Compliance Checking Using Multi-Agent RAG
       The application facilitates compliance checking of requirements specification documents against regulatory policies such as GDPR, Data Act, HIPAA, and other domain-specific policies. 
       Users need to upload their requirements specification documents. Popular regulatory policies are already listed and available in the 
       application for compliance assessment. Alternatively, users can upload their own intended regulatory policies.
       
        ## Steps
        - Upload the Policies and SRS document
        - Save the Policies and SRS document
        - Click on Process Document button to create the vector databases for both the documents.
        - Finally assess the SRS document for compliance checking
        """
    )
    
    with gr.Row():
        compliance_options = ["GDPR", "DataAct", "HIPPA", "Others"]
        selected_compliance = gr.Dropdown(compliance_options, label="Step 1: Select Regulatory Policy")
        
    with gr.Row():
        with gr.Column(visible=False) as policy_upload_column:
            uploaded_files_policies = gr.File(file_count="multiple", label="Upload Files for Policies")
            save_btn_policies = gr.Button("Step 1.A. Save Policies", variant="primary")
        
        with gr.Column():
            uploaded_files_req = gr.File(file_count="single", file_types=[".pdf"], label="Upload File for Requirement Specifications")
            save_btn_req = gr.Button("Step 2. Save SRS", variant="primary")
        
    selected_compliance.change(
        lambda compliance: gr.update(visible=compliance == "Others"), 
        selected_compliance, 
        policy_upload_column
    )

    with gr.Row():
        with gr.Column():
            model_options = ["OpenAI", "LLaMA3", "Mixtral 8x7B", "Command R+"]
            selected_model_1 = gr.Dropdown(model_options, label="Select Model for CC_Agent1")
            api_key_1 = gr.Textbox(label="Provide API Key for CC_Agent1", visible=False)
            selected_model_1.change(
                lambda model: gr.update(visible=model == "OpenAI", interactive=model == "OpenAI"),
                selected_model_1,
                api_key_1
            )

        with gr.Column():
            selected_model_2 = gr.Dropdown(model_options, label="Select Model for CC_Agent2")
            api_key_2 = gr.Textbox(label="Provide API Key for CC_Agent2", visible=False)
            selected_model_2.change(
                lambda model: gr.update(visible=model == "OpenAI", interactive=model == "OpenAI"),
                selected_model_2,
                api_key_2
            )

    with gr.Row():
        btn_process_doc = gr.Button("Step 3. Process Documents", variant="primary")
        run_btn = gr.Button("Step 4. Check for Compliance", variant="primary")
        summary_btn = gr.Button("Summary", variant="primary")

    # Add a Textbox for status messages
    status_message = gr.Textbox(label="Status", interactive=False)
    with gr.Row():
        output = gr.Textbox(label="Output Report")
        summary_output = gr.Textbox(label="Summary Report")

    
    # output = gr.Textbox(label="Output Report")
    # summary_output = gr.Textbox(label="Summary Report")

    save_btn_policies.click(
        save_files_policies,
        inputs=[uploaded_files_policies],
        outputs=[status_message],  # Update the status_message
    )
    save_btn_req.click(
        save_files_req,
        inputs=[uploaded_files_req],
        outputs=[status_message],  # Update the status_message
    )
    btn_process_doc.click(
        process_doc,
        outputs=[status_message],  # Update the status_message
    )
    run_btn.click(
        talk_to_model,
        outputs=output,
    )
    summary_btn.click(
        process_summary,
        outputs=summary_output,
    )

if __name__ == "__main__":
    demo.launch()





