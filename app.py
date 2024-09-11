import sys
import time
import openai
import pandas as pd
import streamlit as st
from rdflib import Graph
from rdflib_hdt import HDTStore
import biobricks
import pexpect
import subprocess

# Constants
OPENAI_ASSISTANT_MSG = "You are a helpful assistant."
CONFIGURE_TIMEOUT = 120
INSTALL_TIMEOUT = 120

# Custom CSS for style
st.markdown("""
    <style>
    .main {
        background-color: #f9f9f9;
        font-family: 'Arial', sans-serif;
    }
    .stTextInput, .stButton, .stTextArea {
        padding: 10px;
    }
    .stProgress {
        color: #4CAF50;
    }
    /* Code block style */
    .stCode {
        background-color: #0a0a0a;
        color: black;
        border-radius: 1px;
        padding: 3px;
    }
    .stDataframe {
        background-color: #0a0a0a;
        color: black;
        border-radius: 2px;
        padding: 5px;
    }
    /* Dark theme for sidebar */
    .sidebar sidebarcontent {
        background-color: #2c3e50;
        color: #403f3f;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar for input fields
st.sidebar.title("Configuration")
api_key = st.sidebar.text_input("OpenAI API Key", type="password")
biobricks_token = st.sidebar.text_input("BioBricks Token", type="password")
query_input = st.sidebar.text_area('Natural Language Query', placeholder='Enter your SPARQL-like query here...')

# Streamlit App setup
st.title("🧬 WikiPathways Query Tool\n\n")
st.markdown("""
This app integrates **OpenAI's API** with the **WikiPathways SPARQL endpoint** for querying biological pathways using natural language queries.
""")

# Progress feedback
progress_bar = st.progress(0)

def configure_biobricks(token):
    """Configure BioBricks with the provided token."""
    try:
        progress_bar.progress(10)
        st.subheader("🔧 Configuring BioBricks & OpenAI...")
        child = pexpect.spawn('biobricks configure --overwrite y', timeout=CONFIGURE_TIMEOUT)
        child.logfile = sys.stdout.buffer  # Log output for debugging

        # Handle token input
        child.expect(['Input a token from biobricks.ai/token:', pexpect.TIMEOUT, pexpect.EOF])
        child.sendline(token)  # Send the BioBricks token
        child.sendline('.')  # Set the path (current directory)

        progress_bar.progress(30)
        st.success("✔️ BioBricks configured successfully!")

    except pexpect.exceptions.TIMEOUT:
        st.error("⚠️ BioBricks configuration timed out. Please ensure the token is correct.")
        return False
    except Exception as e:
        st.error(f"⚠️ An error occurred during BioBricks configuration: {str(e)}")
        return False
    return True

def install_wikipathways():
    """Install WikiPathways asset using BioBricks."""
    try:
        progress_bar.progress(40)
        # st.subheader("📦 Installing WikiPathways...")
        subprocess.run(
            ['biobricks', 'install', 'wikipathways'],
            capture_output=True, text=True, timeout=INSTALL_TIMEOUT
        )
        progress_bar.progress(60)
        st.success("✔️ WikiPathways installed successfully!")
    except subprocess.TimeoutExpired:
        st.error("⚠️ WikiPathways installation timed out.")
    except Exception as e:
        st.error(f"⚠️ An error occurred during WikiPathways installation: {str(e)}")

def query_openai(api_key, query_input):
    """Send natural language query to OpenAI and get SPARQL query."""
    openai.api_key = api_key
    st.success("✔️ OpenAI Configured successfully!")
    natural_query = f'Use WikiPathways SPARQL Endpoint to retrieve the following information and include the necessary prefix lines.\n{query_input}'
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": OPENAI_ASSISTANT_MSG},
                {"role": "user", "content": natural_query}
            ],
            max_tokens=400
        )
        sparql_query = response['choices'][0]['message']['content']
        return sparql_query
    except Exception as e:
        st.error(f"⚠️ An error occurred while querying OpenAI: {str(e)}")
        return None

def run_sparql_query(graph, sparql_query):
    """Execute SPARQL query on the WikiPathways RDF graph."""
    try:
        progress_bar.progress(80)
        # st.subheader("📡 Executing SPARQL query...")
        results = graph.query(sparql_query)
        df = pd.DataFrame(results, columns=[str(var) for var in results.vars])
        if df.empty:
            st.warning("⚠️ No data retrieved from the query.")
        else:
            st.subheader("📊 Data Retrieved from WikiPathways:")
            st.dataframe(df)
    except Exception as e:
        st.error(f"⚠️ An error occurred while executing SPARQL query: {str(e)}")

# Button to trigger the query
if st.button("🚀 Generate and Execute Query"):
    if not api_key or not biobricks_token or not query_input:
        st.error("⚠️ Please ensure all fields are filled out.")
    else:
        # Step 1: Configure BioBricks
        if configure_biobricks(biobricks_token):
            # Step 2: Install WikiPathways asset
            install_wikipathways()

            # Step 3: Load WikiPathways data
            try:
                wikipathways = biobricks.assets('wikipathways')
                store = HDTStore(wikipathways.wikipathways_hdt)
                graph = Graph(store=store)
                progress_bar.progress(70)
            except AttributeError:
                st.error("⚠️ Error loading WikiPathways data.")
                sys.exit(1)

            # Step 4: Query OpenAI API
            sparql_query = query_openai(api_key, query_input)
            if sparql_query and '```sparql' in sparql_query:
                sparql_query = sparql_query.split('```sparql')[1].split('```')[0].strip()
                st.subheader("📝 SPARQL Query Generated:")
                st.code(f"{sparql_query}")

                # Step 5: Execute SPARQL query
                run_sparql_query(graph, sparql_query)
            else:
                st.error("⚠️ SPARQL block not found in the response.")

        progress_bar.progress(100)
