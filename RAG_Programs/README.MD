## embeddingBasic
25 words using python - convert to a vector embeddings and then we will print those
We will do similarity search aganist the user entered word against those 25 words
embedding model - fine tune the accuracy of similarity search using parameters - we will modify the python accordingly 
Integrate this with gemini LLM
Integration with vector database

## Prompting for step 2
"Generate a python code - input hard code 25 words related to AI and databases. Embed using sentence transformer model, print the embeddings for each word, Include necessary improts and print statements."

Install : python -m pip install sentence-transformers

## Prompting for step 3
can you enhance this program to acceot input text from user - post which has to be embedded with the same model and parameter setting and perform similarity search to return top three values

## embedding model - fine tune the accuracy Step 4
can you enhance this program to acceot input text from user - post which has to be embedded with the same model and parameter setting and perform similarity search to return top 3 values

## Itegrating with gemini
integrate this with gemini llm to pass the top 3 retrived words from similarity search. Use this prompt : "result returned from myrag systems post similarity search now give me the accurate synonym for "Context" in a AI domain". Output should also have the reasoning. my gemini ai key is .env file

python -m pip install google-generativeai python-dotenv

## To install Vector DB for the ChromaDB example: embeddingChroma.py
python -m pip install chromadb

Run the persistent ChromaDB inspector dashboard with:

streamlit run embeddingChroma.py

The Streamlit dashboard reads the local `chroma_db` directory and displays database
size, total collections, total records, vector dimensions, collection metadata,
stored documents, embedding previews, and similarity-search request/response details.
Use `Sync hospital seed embeddings` to add any missing hospital vectors, then use
the search form to query the selected collection.

## Prompt to install Chroma database
To this program - integrate chromadb to store the embeddings and print the stats of database whenever new data is gettuing stored. Create a new python file for this enhancement.

## Prompt to Command line
what are the command line parameters that I need to pass when executing this program?

## For debugging and printing at output
Enhance the code so that ouput will have proper debug/print statements to know what is the request query to chroma DB and what is the  response, can you add more debugging what is going in and what is coming as ouput

## Chunks 
1. Python should look into each chunk one by one 
2. Convert each chunk to a jsaon maintaining the proper meta data available in the chunks 
3. Once all chunks are converted into the json, print the json object in the console
4. Use collection name as - HR Help. If not available create the collection
5. Read each json object do the embedding and store the embeddings and meta data in the chromadb
6. Print the database stats after inserting.
7. Add proper debugging statements wherever necessary. defualt directory is .\chroma_db 
8. all chcunks are available in here .\hr_chunks\