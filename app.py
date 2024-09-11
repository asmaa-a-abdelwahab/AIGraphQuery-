import os
import openai
import textwrap
from SPARQLWrapper import SPARQLWrapper, JSON
import ipywidgets as widgets
import pandas as pd
from rdflib import Graph
from rdflib_hdt import HDTStore
import biobricks as bb
from IPython.display import display

class WikiPathwaysQueryTool:
    """A tool to generate and execute SPARQL queries on WikiPathways using natural language via OpenAI's API."""

    def __init__(self):
        """Initialize the user interface components and setup event handlers."""
        self.setup_widgets()
        self.setup_event_handlers()

    def setup_widgets(self):
        """Setup the interactive widgets for the Jupyter notebook interface."""
        self.api_key_input = widgets.Password(description="OpenAI API Key:",
                                              layout=self.input_layout(),
                                              style={'description_width': 'initial'})

        self.biobricks_token_input = widgets.Password(description="BioBricks Token:",
                                                      layout=self.input_layout(),
                                                      style={'description_width': 'initial'})

        self.query_input = widgets.Textarea(description='Natural Language Query:',
                                            placeholder='Enter your SPARQL-like query here...',
                                            layout=self.textarea_layout(),
                                            style={'description_width': 'initial'})

        self.execute_button = widgets.Button(description="Generate and Execute Query",
                                             button_style='success',
                                             layout=self.input_layout())
        self.output = widgets.Output()

        display(self.api_key_input, self.biobricks_token_input, self.query_input, self.execute_button, self.output)

    def input_layout(self):
        """Define a common layout for input widgets to maintain UI consistency."""
        return widgets.Layout(width='500px', height='auto', margin='10px 0 10px 0')

    def textarea_layout(self):
        """Specific layout for the textarea to accommodate more text."""
        return widgets.Layout(width='500px', height='100px', margin='10px 0 10px 0')

    def setup_event_handlers(self):
        """Connect button clicks to their event handlers."""
        self.execute_button.on_click(self.execute_query)

    def execute_query(self, b):
        """Handle the query generation and execution based on user input."""
        with self.output:
            self.output.clear_output()
            if not self.api_key_input.value or not self.biobricks_token_input.value or not self.query_input.value:
                print("Please ensure all fields are filled out.")
                return

            try:
                self.process_query()

            except Exception as e:
                print(f"An error occurred: {str(e)}")

    def process_query(self):
        """Process the natural language query to generate and execute a SPARQL query."""
        print("Execution started...")
        wikipathways = bb.assets('wikipathways')
        store = HDTStore(wikipathways.wikipathways_hdt)
        g = Graph(store=store)

        # Formulate the natural query
        natural_query = 'Use WikiPathways SPARQL Endpoint to retrieve the following information' \
                        ' and make sure to include the necessary prefix lines in the generated SPARQL query.\n' \
                        f'{self.query_input.value}'

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": natural_query}
            ],
            max_tokens=400
        )

        sparql_query = response['choices'][0]['message']['content']
        print("Response from OpenAI received...")

        # Validate if the SPARQL block is correctly extracted
        if '```sparql' in sparql_query and '```' in sparql_query:
            sparql_query = sparql_query.split('```sparql')[1].split('```')[0].strip()
            print("SPARQL Query extracted:\n", textwrap.dedent(sparql_query).strip())  # Debug print

            results = g.query(sparql_query)
            df = pd.DataFrame(results, columns=[str(var) for var in results.vars])
            store.close()

            if df.empty:
                print("No data retrieved from the query.")
            else:
                print("Data retrieved from WikiPathways...")
                display(df)
        else:
            print("SPARQL block not found in the response.")

# Usage example (uncomment the following line if running in a Jupyter notebook environment)
tool = WikiPathwaysQueryTool()