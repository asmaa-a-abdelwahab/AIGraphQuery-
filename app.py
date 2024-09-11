import os
import openai
import textwrap
from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd
from rdflib import Graph
from rdflib_hdt import HDTStore
import biobricks as bb
import streamlit as st


class WikiPathwaysQueryTool:
    """A tool to generate and execute SPARQL queries on WikiPathways using natural language via OpenAI's API."""

    def __init__(self):
        """Initialize the Streamlit interface."""
        self.setup_ui()

    def setup_ui(self):
        """Setup the Streamlit UI components."""
        st.title("WikiPathways Query Tool")

        # Input fields for OpenAI API and BioBricks token
        self.api_key = st.text_input("OpenAI API Key", type="password")
        self.biobricks_token = st.text_input("BioBricks Token", type="password")

        # Textarea for the natural language query
        self.query_input = st.text_area("Natural Language Query", "Enter your SPARQL-like query here...")

        # Button to trigger the query
        if st.button("Generate and Execute Query"):
            if self.api_key and self.biobricks_token and self.query_input:
                self.execute_query()
            else:
                st.error("Please ensure all fields are filled out.")

    def execute_query(self):
        """Process the natural language query to generate and execute a SPARQL query."""
        st.info("Execution started...")

        # Configure BioBricks using the token from the input field
        bb.configure(token=self.biobricks_token)

        wikipathways = bb.assets('wikipathways')
        store = HDTStore(wikipathways.wikipathways_hdt)
        g = Graph(store=store)

        # Formulate the natural query
        natural_query = 'Use WikiPathways SPARQL Endpoint to retrieve the following information' \
                        ' and make sure to include the necessary prefix lines in the generated SPARQL query.\n' \
                        f'{self.query_input}'

        # Communicate with OpenAI API
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": natural_query}
                ],
                max_tokens=400
            )

            sparql_query = response['choices'][0]['message']['content']
            st.success("Response from OpenAI received.")

            # Validate if the SPARQL block is correctly extracted
            if '```sparql' in sparql_query and '```' in sparql_query:
                sparql_query = sparql_query.split('```sparql')[1].split('```')[0].strip()
                st.text(f"SPARQL Query extracted:\n{sparql_query}")  # Debug print

                results = g.query(sparql_query)
                df = pd.DataFrame(results, columns=[str(var) for var in results.vars])
                store.close()

                if df.empty:
                    st.warning("No data retrieved from the query.")
                else:
                    st.success("Data retrieved from WikiPathways.")
                    st.dataframe(df)
            else:
                st.error("SPARQL block not found in the response.")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")


# Run the app
if __name__ == "__main__":
    tool = WikiPathwaysQueryTool()
