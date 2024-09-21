"""
Developers:
- Spencer Presley | github.com/spencerpresley
- Dustin O'Brien | github.com/omniladder

Chatbot Module for Salt Cast Project

This module implements a sophisticated chatbot system for the Salt Cast research project,
focusing on salinity levels in the Chesapeake Bay. Key features include:

1. Integration with OpenAI's language models and FAISS vector database for contextual understanding and document retrieval.
2. Conversation memory using ConversationSummaryBufferMemory and ConversationEntityMemory to maintain context across sessions.
3. Web search capabilities using DuckDuckGo for up-to-date information, enhancing response accuracy.
4. Asynchronous processing of prompts with streaming responses to handle real-time user interactions efficiently.
5. Context-aware responses prioritizing project-specific knowledge to provide tailored information.
6. Entity extraction and management from conversations and relevant documents to enrich the chatbot's understanding.
7. Citation handling for web search results to maintain transparency and reliability.
8. Flexible initialization with customizable parameters (project name, database, model, etc.) to adapt to different project needs.
9. Error handling and extensive logging (printing) for debugging to ensure robustness and ease of maintenance.

The Chatbot class encapsulates all functionalities, providing methods for processing prompts,
managing conversation context, and handling post-response operations.

Chatbot uses a variety of helper modules to perform its tasks. These modules are located in the `src/scripts` and `scr/scripts/utils` directories.

The Chatbot's configuartion can be found in the `src/scripts/config.py` file.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Dict, List, Optional, AsyncGenerator

from fastapi import Request
from fastapi.responses import StreamingResponse

from langchain.cache import InMemoryCache
from langchain.chains import LLMChain
from langchain.globals import set_llm_cache
from langchain.prompts import PromptTemplate
from langchain.utilities import DuckDuckGoSearchAPIWrapper

from langchain_community.utilities import ArxivAPIWrapper

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain_core.output_parsers import JsonOutputParser

from langchain_openai import ChatOpenAI, OpenAIEmbeddings 

from .utils import *
from .utils.document_processing import extract_entities
from .config import ChatbotConfig
from .vectordb_manager import VectorDBManager
from .memory_manager import MemoryManager

from .markdown_buffer import MarkdownBuffer

class Chatbot:
    """
    Encapsulates the chatbot functionality for the Salt Cast Project.
    This class integrates various components such as language models, vector databases, and web search APIs to provide a responsive and intelligent chatbot.
    """

    def __init__(
        self,
        project_name: str = ChatbotConfig.DEFAULT_PROJECT_NAME,
        database_name: str = ChatbotConfig.DEFAULT_DATABASE_NAME,
        temperature: float = ChatbotConfig.DEFAULT_TEMPERATURE,
        model_type: str = ChatbotConfig.DEFAULT_MODEL_TYPE,
        system_messages: Optional[dict] = None,
    ):
        """
        Initializes the Chatbot with necessary components.

        Args:
            project_name (str): The name of the project.
            database_name (str): The name of the database.
            temperature (float): The temperature setting for the language model. Defaults to 0.65. Range is 0.0 (most deterministic) to 1.0 (most random).
            model_type (str): Model to be used, accepts any OpenAI models. Defaults to gpt-4o-mini. gpt-4o provides better results and is faster but also more expensive.
            system_messages (Optional[dict]): Predefined system messages loaded from a static file. Defaults to None.

        Initializes components like language models, vector databases, and web search APIs. Sets up in-memory caching to optimize API call efficiency.
        """
        self.project_name = project_name
        self.database_name = database_name
        self.api_key = get_openai_api_key()

        # Set up in-memory cache to prevent api calls for identical prompts
        set_llm_cache(InMemoryCache())

        self.llm = ChatOpenAI(
            api_key=self.api_key,
            temperature=temperature,
            model=model_type,
            streaming=True,
        )
        self.embeddings: OpenAIEmbeddings = OpenAIEmbeddings(api_key=self.api_key)
        self.vectordb_manager = VectorDBManager(self.project_name, self.database_name, self.embeddings)
        self.memory_manager = MemoryManager(self.llm)
        
        self.global_chat_history: List[str] = []
        
        self.search: DuckDuckGoSearchAPIWrapper = DuckDuckGoSearchAPIWrapper()
        self.web_search_parser: JsonOutputParser = JsonOutputParser(
            pydantic_object=WebSearchDecision
        )
        self.web_search_cache: Dict[str, str] = {}
        search_query_prompt = PromptTemplate(
            input_variables=["original_query"],
            template="Given teh user's query: '{original_query}', generate a search query to find the most relelvant and up-to-date information online. The search query should be short and focused.",
        )
        self.search_query_chain: LLMChain = LLMChain(
            llm=self.llm, prompt=search_query_prompt
        )

        # For frontend display
        self.chat_history: List[str] = []
        self.system_messages: dict = system_messages if system_messages else ChatbotConfig.SYSTEM_MESSAGES
                
    def load_system_messages(self) -> dict:
        """
        Loads the system message(s) from a static folder.

        Returns:
            dict: A dictionary containing system message(s).
        
        This method reads the system message(s) from a JSON file located in a predefined path.
        """
        system_messages: Dict[str, str] = {}

        script_dir: str = os.path.dirname(os.path.abspath(__file__))
        system_messages_path: str = os.path.join(
            script_dir, ChatbotConfig.SYSTEM_MESSAGES_PATH
        )
        with open(system_messages_path, "r") as f:
            system_messages: Dict[str, str] = json.load(f)

        return system_messages
    
    async def should_search_arxiv(self, query: str) -> bool:
        """
        Determines whether it is appropriate to search ArXiv based on the given query.

        Args:
            query (str): The user's query to evaluate.

        Returns:
            bool: True if searching ArXiv is deemed appropriate, False otherwise.

        This method uses the language model to predict whether the content of the query is relevant to the topics covered in the ArXiv database.
        """
        decision_prompt = f"Given the query: '{query}', determine if it is appropriate to search ArXiv for relevant information. Return 'yes' if it is appropriate, otherwise return 'no'."
        decision = await self.llm.apredict(decision_prompt)
        should_search_arxiv = True if decision.lower() == "yes" else False
        return should_search_arxiv

    async def generate_arxiv_query(self, original_query: str) -> str:
        """
        Generates a specific and relevant search query for ArXiv based on the user's input.

        Args:
            original_query (str): The user's original query.

        Returns:
            str: A refined query string tailored for searching the ArXiv database.

        This method formats the user's query into a more focused search string that is likely to yield relevant academic articles from ArXiv.
        """
        query_prompt = f"Generate a search query for ArXiv based on the following user query: '{original_query}'. Ensure the query is specific and relevant to the user's query."
        arxiv_query = await self.llm.apredict(query_prompt)
        return arxiv_query
    
    async def search_arxiv(self, query: str) -> str:
        """
        Performs a search on ArXiv using the specified query and returns formatted results.

        Args:
            query (str): The query string for ArXiv.

        Returns:
            str: Formatted string containing the search results or an error message.

        This method interfaces with the ArXiv API to fetch relevant articles based on the query. It handles exceptions by returning an appropriate error message.
        """
        try:
            arxiv = ArxivAPIWrapper()
            results = arxiv.run(query)
            if results:
                return f"ArXiv search results:\n\n{results}\n\n"
            else:
                return "No relevant ArXiv results found."
        except Exception as e:
            print(f"Error in search_arxiv: {str(e)}")
            return "An error occurred during ArXiv search."
    
    async def process_prompt(
        self, prompt: str, session_id: str, request: Request = None
    ):
        """
        Processes the given prompt, performs necessary searches, and generates a response.

        Args:
            prompt (str): The user's query.
            session_id (str): The session identifier for tracking conversation context and saving messages to sql database.
            request (Request, optional): The HTTP request context, used for handling disconnections in streaming responses.

        Returns:
            str: The final response generated by the chatbot, or an error message.

        This method orchestrates the entire response generation process, including web and ArXiv searches, document retrieval, and conversation context management. It handles streaming responses for UI display.
        """
        print("Entering process_prompt method")
        llm_response: str = ""
        web_search_results: str = ""
        citations: str = ""
        citation_guide: str = ""
        try:
            print(f"Processing Prompt: {prompt[:50]}... for session: {session_id}")

            arxiv_results = None
            if await self.should_search_arxiv(prompt):
                arxiv_query = await self.generate_arxiv_query(prompt)
                arxiv_results = await self.search_arxiv(arxiv_query)
                print(f"Performed ArXiv search with query: {arxiv_query}")
                print(f"ArXiv search results: {arxiv_results[:100]}")
            
            # Determine if a web search is necessary and perform it if needed.
            if simple_should_web_search(prompt):
                search_query: str = generate_search_query(self.search_query_chain, prompt)
                search_results: List[str] = web_search(self.search, search_query)
                print(f"Performed web search with query: {search_query}")

                if search_results:
                    # Format web search results and generate citations
                    web_search_results: str = (
                        "Web search results:\n\n" + "\n\n".join(search_results) + "\n\n"
                    )
                    citations, citation_guide = format_citations(search_results)
                    print("Generated citations:", citations)
                    print("Generated citation guide:", citation_guide)
                else:
                    print("No search results found")
                    web_search_results: str = "No web search results found."

            # Retrive and process relevant documents from the FAISS database
            try:
                relevant_docs: List[str] = self.vectordb_manager.get_relevant_docs(prompt=prompt)
                print("Retrieved relevant docs")
                print(relevant_docs)

                if relevant_docs:
                    # Extract entities from relelvant documents to provide additional context
                    relevant_docs_entities: Dict[str, List[str]] = extract_entities(
                        llm=self.llm, docs=relevant_docs
                    )
                    print("Extracted entities from docs")
                    print(relevant_docs_entities)
                else:
                    relevant_docs_summary: str = ""
                    relevant_docs_entities: Dict[str, List[str]] = ""
                    print("No relevant docs found")
            except Exception as e:
                print(f"Error processing relevant docs: {str(e)}")
                relevant_docs_summary: str = ""
                relevant_docs_entities: Dict[str, List[str]] = ""

            # Load conversation memory to maintain context across interactions
            try:
                # Retrieve conversation summary from buffer memory
                conversation_summary, conversation_entities = self.memory_manager.load_memory_variables(prompt=prompt)
                print("Conversation summary loaded")
                print(conversation_summary)
                print("Conversation entities loaded")
                print(conversation_entities)
            except Exception as e:
                print(f"Error loading memory variables: {str(e)}")
                raise

             # Prepare the context for the LLM
            context_params = {
                "relevant_docs": relevant_docs,
                "relevant_docs_entities": relevant_docs_entities,
                "conversation_summary": conversation_summary.get("history", "No previous conversation."),
                "conversation_entities": ", ".join(conversation_entities.get("entities", {}).keys()),
            }
            
            # Prepare the context for the LLM, including web results if necesarry
            context: str = ""
            if web_search_results:
                context_params.update({
                    "web_search_results": web_search_results,
                    "citations": citations,
                    "citation_guide": citation_guide,
                })
                context_template = ChatbotConfig.CONTEXT_TEMPLATE_WITH_SEARCH
            else:
                context_template = ChatbotConfig.CONTEXT_TEMPLATE_WITHOUT_SEARCH

            if arxiv_results:
                context_params["arxiv_results"] = arxiv_results

            context = context_template.format(**context_params)

            print("Context prepared for LLM")

            # Prepare messages for the LLM, including system message and user query with context
            messages: List[BaseMessage] = [
                SystemMessage(content=ChatbotConfig.SYSTEM_MESSAGES),
                HumanMessage(content=f"Context: {context}\n\nUser Query: {prompt}"),
            ]

            print("Prepared messages for LLM")

            # This asynchronous generator function streams the response from the LLM in chunks.
            # It formats each chunk for HTML display and checks for disconnection requests.
            # If a web search was performed, it appends a formatted citation guide at the end of the stream.
            # TODO: Add support for the other markdown formats e.g. bold, italic, etc.
            async def chunk_generator() -> AsyncGenerator[str, None]:
                nonlocal llm_response
                try:
                    # Stream the LLM's response chunk by chunk
                    async for chunk in self.llm.astream(messages):
                        if chunk.content:
                            if request and await request.is_disconnected():
                                break
                            # Format content for the HTML display
                            formatted_content: str = chunk.content.replace("\n", "<br>")
                            llm_response += chunk.content
                            yield f"data: {chunk.content}\n\n"
            # markdown_response: str = ""
            # async def chunk_generator() -> AsyncGenerator[str, None]:
            #     nonlocal llm_response
            #     nonlocal markdown_response
            #     markdown_buffer = MarkdownBuffer()                
            #     try:
            #         async for chunk in self.llm.astream(messages):
            #             if chunk.content:
            #                 if request and await request.is_disconnected():
            #                     break
            #                 llm_response += chunk.content
            #                 processed_chunks = markdown_buffer.add_chunk(chunk.content)
            #                 for element in processed_chunks:
            #                     markdown_response += element
            #                     # llm_response += element
            #                     yield f"data: {element}\n\n"
                    
            #         # Process any remaining content in the buffer
            #         # markdown_buffer.add_chunk("\n") # Add a newline to clone any open elements
            #         remaining_elements = markdown_buffer.flush()
            #         for element in remaining_elements:
            #             markdown_response += element
            #             # llm_response += element
            #             yield f"data: {element}\n\n"

                    # if markdown_buffer.buffer:
                    #     # Any remaining text that wasn't part of a Markdown element
                    #     formatted_content = markdown_buffer.buffer
                    #     llm_response += formatted_content
                    #     yield f"data: {formatted_content}\n\n"

                    # # Append citation guide if web search was performed
                    # if citation_guide:
                    #     citation_guide_formatted: str = citation_guide.replace(
                    #         "\n", "<br>"
                    #     )
                    #     llm_response += f"<br><br>{citation_guide_formatted}"
                    #     yield f"data: <br><br>{citation_guide_formatted}\n\n"
                    
            # async def chunk_generator() -> AsyncGenerator[str, None]:
            #     nonlocal llm_response
            #     nonlocal markdown_response
            #     markdown_buffer = MarkdownBuffer()
            #     queue = asyncio.Queue()
                
            #     async def llm_stream_handler():
            #         nonlocal llm_response
            #         try:
            #             async for chunk in self.llm.astream(messages):
            #                 if chunk.content:
            #                     llm_response += chunk.content
            #                     await queue.put(chunk.content)
            #                 if request and await request.is_disconnected():
            #                     break
            #             await queue.put(None) # Signal end of stream
            #         except Exception as e:
            #             print(f"Error in llm_stream_handler: {str(e)}")
            #             await queue.put(None)
                
            #     async def markdown_processor():
            #         nonlocal markdown_response
            #         while True:
            #             chunk = await queue.get()
            #             if chunk is None:
            #                 break
            #             processed_chunks = markdown_buffer.add_chunk(chunk)
            #             for element in processed_chunks:
            #                 markdown_response += element
            #                 yield element
                    
            #         remaining_chunks = markdown_buffer.flush()
            #         for element in remaining_chunks:
            #             markdown_response += element
            #             # yield f"data: {element}\n\n"
            #             yield element
                            
            #     llm_task = asyncio.create_task(llm_stream_handler())
                    
            #     try:
            #         async for chunk in markdown_processor():
            #             yield f"data: {chunk}\n\n"
                            
            #         print("Finished generating response")

            #         yield "event: end-of-stream\ndata: stream complete\n\n"

            #     except Exception as e:
            #         print(f"Error in markdown processor in chunk_generator: {str(e)}")
            #         yield f"event: stream-error\ndata: stream error occured: {str(e)}\n\n"
            #         raise
                    
            #     finally:
            #         # Ensure both tasks are completed 
            #         await llm_task
                    
            #         # Schedule post-response processing as an asynchronous task
            #         asyncio.create_task(
            #             self.post_response_processing(
            #                 prompt=prompt,
            #                 llm_response=llm_response,
            #                 session_id=session_id,
            #                 markdown_response=markdown_response,
            #             )
            #         )                   

                    yield "event: end-of-stream\ndata: stream complete\n\n"
                    # Schedule post-response processing as axn asynchronous task
                    asyncio.create_task(
                        self.post_response_processing(
                            prompt=prompt,
                            llm_response=llm_response,
                            session_id=session_id,
                            # markdown_response=markdown_response,
                        )
                    )

                 
                except Exception as e:
                    print(f"Error in chunk_generator: {str(e)}")
                    yield f"event: stream-error\ndata: stream error occured: {str(e)}\n\n"
                    

            if request:
                print("Returning StreamingResponse")
                return StreamingResponse(
                    chunk_generator(), media_type="text/event-stream"
                )
            else:
                print("Generating response without streaming")
                for chunk in self.llm.stream(messages):
                    if chunk.content:
                        print(chunk.content, end="", flush=True)
                        llm_response += chunk.content

                # Append citation guide if web search was performed
                if citation_guide:
                    llm_response += f"\n\n{citation_guide}"

                # Run post-processing synchronously for non-streaming requests
                await self.post_response_processing(
                    prompt=prompt,
                    llm_response=llm_response,
                    session_id=session_id,
                )

            print(f"Generated response: {llm_response[:50]}...")

        except Exception as e:
            print(f"An error occurred in process_prompt: {str(e)}")
            import traceback

            traceback.print_exc()

        return llm_response

    async def post_response_processing(
        self,
        *,
        prompt: str,
        llm_response: str,
        session_id: str,
        markdown_response: Optional[str] = None,
        conversation_summary: Optional[dict] = None,
        conversation_entities: Optional[dict] = None,
    ):
        """
        Handles post-response tasks such as updating conversation memories and saving messages to the database.

        Args:
            prompt (str): The original user prompt.
            llm_response (str): The response generated by the language model.
            session_id (str): The session identifier for tracking conversation context.
            conversation_summary (Optional[dict]): The current state of the conversation summary.
            conversation_entities (Optional[dict]): The current state of the conversation entities.

        This method ensures that the chatbot's state is updated with the latest interaction details. It saves the conversation history to the sql database and updates the langchain memories (summary and entitiy).
        """
        try:
            print(f"Starting post-response processing for session: {session_id}")
            print("-" * 50)
            print(f"Prompt: {prompt}")
            print("-" * 50)
            print(f"LLM Response: {llm_response}")
            print("-" * 50)
            print(f"Markdown Response: {markdown_response}")
            print("-" * 50)
            await self.memory_manager.update_memories(prompt=prompt, llm_response=llm_response)

            # Reload summary and entities after updating
            updated_summary, updated_entities = self.memory_manager.load_memory_variables(prompt=prompt)
            print("Updated entities:", self.memory_manager.entityMemory.entity_store)

            # Print updated ConversationSummaryBufferMemory contents
            print("\nConversation Summary:")
            print(pretty_print_json(obj=updated_summary))

            # Print updated ConversationEntityMemory contents
            print("\nConversation Entities:")
            print(pretty_print_json(obj=updated_entities))

            self.global_chat_history.append(AIMessage(content=llm_response))

            print("Finished post-response processing")
        except Exception as e:
            print(f"Error in post_response_processing: {str(e)}")
            import traceback
            traceback.print_exc()
