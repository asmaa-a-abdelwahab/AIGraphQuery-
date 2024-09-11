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

# Streamlit App setup
st.title("WikiPathways Query Tool")
st.write("This app integrates OpenAI's API with WikiPathways SPARQL endpoint for querying biological pathways using natural language.")

# Input fields for OpenAI API Key and BioBricks Token
api_key = st.text_input("OpenAI API Key", type="password")
biobricks_token = st.text_input("BioBricks Token", type="password")

# Input for the natural language query
query_input = st.text_area('Natural Language Query', placeholder='Enter your SPARQL-like query here...')

# Button to trigger the query
if st.button("Generate and Execute Query"):
    if not api_key or not biobricks_token or not query_input:
        st.error("Please ensure all fields are filled out.")
    else:
        try:
            st.info("Configuring BioBricks...")

            # Use pexpect to run the biobricks configure command with token input

            child = pexpect.spawn('biobricks configure --overwrite y', timeout=120)
            child.logfile = sys.stdout.buffer  # Log the output for debugging

            # Step 1: Handle the token input
            child.expect(['Input a token from biobricks.ai/token:', pexpect.TIMEOUT, pexpect.EOF])
            child.sendline(biobricks_token)  # Send the BioBricks token
            time.sleep(1)
            child.sendline('.')  # Send the path (current directory)
            st.success("BioBricks configuration successful!")

            # pexpect.spawn('biobricks install wikipathways', timeout=120)
            biobricks.install('wikipathways')

            # Proceed with loading WikiPathways data and querying
            wikipathways = biobricks.assets('wikipathways')
            store = HDTStore(wikipathways.wikipathways_hdt)
            g = Graph(store=store)

            # Formulate the natural query for OpenAI
            natural_query = 'Use WikiPathways SPARQL Endpoint to retrieve the following information' \
                            ' and make sure to include the necessary prefix lines in the generated SPARQL query.\n' \
                            f'{query_input}'

            # Call OpenAI API to convert natural language to SPARQL
            st.info("Calling OpenAI API...")
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": natural_query}
                ],
                max_tokens=400
            )

            sparql_query = response['choices'][0]['message']['content']
            st.success("Response from OpenAI received...")

            # Validate if the SPARQL block is correctly extracted
            if '```sparql' in sparql_query and '```' in sparql_query:
                sparql_query = sparql_query.split('```sparql')[1].split('```')[0].strip()
                st.info(f"SPARQL Query extracted:\n{sparql_query}")

                # Execute the SPARQL query
                st.info("Executing SPARQL query...")
                results = g.query(sparql_query)
                df = pd.DataFrame(results, columns=[str(var) for var in results.vars])
                store.close()

                # Display the results
                if df.empty:
                    st.warning("No data retrieved from the query.")
                else:
                    st.write("Data retrieved from WikiPathways:")
                    st.dataframe(df)
            else:
                st.error("SPARQL block not found in the response.")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
