"""
QueryMode

This Streamlit app allows users to explore different types of LLM-powered search integrations.

Search Modes:
- Conversational: A Perplexity-style conversational LLM search that provides summarized results with cited sources.
- Overview: A Google-style search that includes both organic results and AI-generated overviews when deemed helpful by the search engine.
- Traditional (no integreation): A traditional Google search that excludes AI-generated overviews and provides only organic search results.

How it works:
- Conversational is powered by Google's Gemini model, grounded in Google Search results.
- Overview and Traditional are taken directly from Google Search results, collected with
    the SERP API (https://serpapi.com/).
    - What is shown in each is simply parsed from these results.

Author: Matthew R. DeVerna
"""

import os
import sys

# Add 'lib' directory to sys.path to load dependencies
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

# Internal
from helpers.google import grounded_generation
from helpers.serp import get_search_results
from helpers.gnews import get_recent_articles, sample_articles
from helpers.utils import update_response_text, organic_search_to_markdown

# External
from google import genai
from serpapi import GoogleSearch

import streamlit as st


def main():
    """
    Main function to run the Streamlit app.
    """
    st.title("Welcome to QueryMode.")

    # Add app description
    st.markdown(
        """
    This web app uses advanced large language models to let users explore different ways artificial intelligence can be integrated into everyday web searches.

    #### Required
    1. Google API key (see [Google API documentation](https://ai.google.dev/gemini-api/docs/))
    2. SERP API key (see [SERP API documentation](https://serpapi.com/))

    #### Note
    These keys are **not stored** and you will **not be charged** unless you initiate searches.
    """
    )
    st.divider()

    st.subheader("API Key Setup")

    # Placeholder for OpenAI API key input
    google_api_key_place_holder = st.empty()
    serp_api_key_place_holder = st.empty()
    google_api_key = google_api_key_place_holder.text_input(
        "Google API Key", type="password"
    )
    serp_api_key = serp_api_key_place_holder.text_input("SERP API Key", type="password")

    # Initialize Google client if API key is provided
    google_api_key_valid = False
    serp_api_key_valid = False

    if google_api_key:
        try:
            google_client = genai.Client(api_key=google_api_key)
            # Test the API key by making a simple request
            google_client.models.list()
            st.success(
                "**Google API successfully loaded and validated!**\n\n"
                "To enter a new key, refresh the page."
            )
            google_api_key_valid = True
            google_api_key_place_holder.empty()  # Clear the API key input box

        except Exception as e:
            st.warning(
                "**Whoops! It looks like there was a problem.**\n\n"
                "Please check the error message provided by Google below to troubleshoot."
            )
            st.error(f"{e}")

    else:
        st.warning(
            "**Please provide a Google API key to proceed.**\n\n"
            "**Note**: Your key will **not be stored** and you will **not be charged** "
            "unless you initiate searches."
        )

    # Initialize SERP API client if API key is provided
    if serp_api_key:
        try:
            GoogleSearch.SERP_API_KEY = serp_api_key
            # Test the API key by making a simple request
            search = GoogleSearch({})
            search.get_account()
            st.success(
                "**SERP API successfully loaded and validated!**\n\n"
                "To enter a new key, refresh the page."
            )
            serp_api_key_valid = True
            serp_api_key_place_holder.empty()  # Clear the API key input box

        except Exception as e:
            st.warning(
                "**Whoops! It looks like there was a problem.**\n\n"
                "Please check the error message provided by SERP API below to troubleshoot."
            )
            st.error(f"{e}")

    else:
        st.warning(
            "**Please provide a SERP API key to proceed.**\n\n"
            "**Note**: Your key will **not be stored** and you will **not be charged** "
            "unless you attempt to fact check an article."
        )

    if not google_api_key_valid or not serp_api_key_valid:
        st.stop()

    # Retrieve recent articles
    st.divider()
    st.subheader("Fetch Google News headlines for search inspiration")
    if st.button("Fetch"):
        with st.spinner("Fetching recent articles..."):
            articles = get_recent_articles()
            sampled_articles = sample_articles(articles)

            if sampled_articles:
                st.success(
                    "Recent articles retrieved successfully! Click the 'Fetch' button again to change the articles."
                )
                articles_container = st.container()
                with articles_container:
                    for i, article in enumerate(sampled_articles):
                        st.markdown(
                            f"**{i+1}. {article['title']}** "
                            f"({article['published_date']}; [source]({article['href']}))"
                        )
            else:
                st.warning("No articles found. Please try again in a few moments.")
        st.session_state.articles_retrieved = True

    input_container = st.container()
    with input_container:
        st.divider()
        st.subheader("Search")

        # Select the search mode
        search_mode = st.radio(
            "Select search mode",
            ["Conversational", "Overview", "Traditional"],
        )

        if search_mode in ["Overview", "Traditional"]:
            location = st.text_input(
                "Enter a location for the search",
                help="Enter a city to mimic real search behavior.",
            )

        query = st.text_input(
            "Enter a search query",
            help="Use this as you would a normal Goole search.",
        )

        st.divider()
        if query:
            st.subheader("Search Results")

        # TODO: Need to allow conversation to continue
        if query and search_mode == "Conversational":
            conversational_container = st.container()
            with st.spinner("Searching Google..."):

                # Conversational Search
                grounded_response = grounded_generation(
                    client=google_client, model="gemini-2.0-flash", prompt=query
                )
                response_data = grounded_response.candidates[0]
                updated_text = update_response_text(
                    response_data.content.parts[0].text,
                    response_data.grounding_metadata.grounding_supports,
                    response_data.grounding_metadata.grounding_chunks,
                )

                with conversational_container:
                    st.subheader("Conversational Search")
                    if updated_text:
                        st.write(updated_text)

        # TODO: Implement
        elif query and search_mode == "Overview":
            st.write("Nothing implemented here.")
            pass

        # TODO: Need to handle infinite scrolling via pagination
        elif query and search_mode == "Traditional":

            with st.spinner("Searching Google..."):
                search_results = get_search_results(query, location, serp_api_key)
                formatted_results = organic_search_to_markdown(
                    search_results["organic_results"]
                )
                if formatted_results:
                    st.write(formatted_results)
                else:
                    st.warning(
                        "No search results found. Please try again in a few moments."
                    )


if __name__ == "__main__":
    main()
