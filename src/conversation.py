import logging
from typing import Any
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConversationEnhancer:
    @staticmethod
    def get_conversation_chain(
        vectorstore: FAISS, 
        llm: Any, 
        model_type: str = 'google'
    ):
        """
        Sets up a conversational retrieval chain using the new LCEL patterns.
        This chain is "history-aware" and will reformulate questions based on history.
        
        Args:
            vectorstore (FAISS): The FAISS vector store with document embeddings.
            llm (Any): The initialized language model.
            model_type (str): 'google' or 'local', to determine which prompt to use.
        
        Returns:
            A new LangChain runnable (LCEL chain).
        """
        if not vectorstore:
            raise ValueError("Vector store is not initialized.")
        if not llm:
            raise ValueError("LLM is not initialized.")

        # 1. History-Aware Retriever
        # This chain reformulates the user's latest question to be a standalone
        # question, using the chat history for context.
        contextualize_q_system_prompt = (
            "Given a chat history and the latest user question "
            "which might reference context in the chat history, "
            "formulate a standalone question which can be understood "
            "without the chat history. Do NOT answer the question, "
            "just reformulate it if needed and otherwise return it as is."
        )
        contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        history_aware_retriever = create_history_aware_retriever(
            llm, vectorstore.as_retriever(), contextualize_q_prompt
        )
        logger.info("Created history-aware retriever.")

        # 2. Answer Generation Chain
        # This chain takes the user's question and the retrieved documents
        # and generates an answer.
        
        if model_type == 'local':
            # Use the strict custom prompt for the local Gemma model
            system_prompt_template = """
            Given the following conversation and a piece of retrieved context, answer the user's question.
            If you don't know the answer from the context, just say "I am sorry, I cannot find that information in the provided documents."
            Do not try to make up an answer.
            
            Context:
            {context}
            
            Helpful Answer:
            """
            logger.info("Using custom 'local' prompt for answer chain.")
        else:
            # Default prompt for Google models
            system_prompt_template = (
                "You are an assistant for question-answering tasks. "
                "Use the following pieces of retrieved context to answer the question. "
                "If you don't know the answer, just say that you don't know. "
                "Keep the answer concise.\n\n"
                "Context:\n{context}"
            )
            logger.info("Using default 'google' prompt for answer chain.")

        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt_template),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        
        # This sub-chain combines the retrieved documents into a single string
        question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
        logger.info("Created question-answer 'stuff' chain.")

        # 3. Full Retrieval Chain
        # This final chain combines the two previous chains:
        # 1. It calls the history_aware_retriever to get documents.
        # 2. It then calls the question_answer_chain with those documents.
        rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
        
        logger.info(f"Full RAG conversation chain created successfully for model type: {model_type}")
        return rag_chain