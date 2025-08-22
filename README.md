# Snowflake Document AI PDF Pipeline

A proof-of-concept (POC) implementation for extracting data from PDF documents using Snowflake's Document AI capabilities. This pipeline demonstrates how to load, process, and flatten PDF data into Snowflake tables for analysis.

## Overview

This project provides a complete end-to-end solution for:
- Uploading PDF documents to Snowflake stages
- Processing PDFs using Snowflake's Document AI functions
- Extracting and flattening structured data into relational tables
- Querying and analyzing the extracted document data

## Features

- **Automated PDF Processing**: Leverage Snowflake's native Document AI capabilities
- **Flexible Data Extraction**: Extract text, tables, and key-value pairs from PDFs
- **Scalable Architecture**: Handle multiple documents efficiently
- **SQL-Native**: All processing done within Snowflake using SQL

# Snowflake Document AI Pipeline -  Guide

Follow the step-by-step instructions to set up, test, and demonstrate the complete workflow for extracting data from PDF documents using Snowflake's Document AI capabilities.

## Prerequisites

- Access to a Snowflake account with Document AI features enabled
- ACCOUNTADMIN or equivalent privileges for initial setup
- Sample PDF documents for testing (available in the `pdf_documents/` directory)

## Demo Setup

### Step 1: Environment Preparation

First, set up your Snowflake environment by running the complete database objects and privileges setup from `doc_ai_objects.sql`:

            
            -- Set context
            USE ROLE ACCOUNTADMIN;
            USE WAREHOUSE DOC_AI_WH;
            
            -- Create database and schema
            CREATE DATABASE IF NOT EXISTS DOCUMENT_AI_DB;
            USE DATABASE DOCUMENT_AI_DB;
            CREATE SCHEMA IF NOT EXISTS DOC_AI_SCHEMA;
            USE SCHEMA DOC_AI_SCHEMA;
            

### Step 2: Prepare a Document AI model build

        1. Navigate to Document AI in Snowsight.  
        2. Open your model build (create `inspection_reviews`).  
        3. Click on `Define values` in the Build Details tab.
        4. For each document, add:
            - `inspection_date`: What is the inspection date?
            - `inspection_grade`: What is the grade?
            - `inspector`: Who performed the inspection?
            - `list_of_units`: What are all the units?
        5. Review suggested results; correct manually if needed.
        6. Once validated, publish the model build to finalize it for the downstream pipeline.



### Step 3: Create document processing pipeline
    
    
        
        -- Execute the contents of doc_ai_pipeline_processing.sql
        -- This creates all necessary stages, stream, tables, and task
        
        -- Key objects created:
        -- 1. MY_PDF_STAGE (internal stage for PDF files)
        -- 2. MY_PDF_STREAM (streams on stage)
        -- 3. PDF_REVIEWS (table to store information about the documents )
        -- 4. LOAD_NEW_FILE_DATE (task to process new documents in the stage)
        -- 5. PDF_REVIEWS_FLATTEN (table to analyze the extracted information in separate columns)
        

### Step 4: Document Upload to process documents

**Download** the sample documents from the pdf_documents folder to your computer.
**Upload** the extracted PDF files to the my_pdf_stage stage in Snowsight for processing.
**Review** the extracted information in the pdf_reviews_flatten table to see the final result.


### Resources

- [Snowflake Document AI Documentation](https://docs.snowflake.com/)
- [SQL Scripts in this Repository](./doc_ai_objects.sql)
- [Processing Workflow](./doc_ai_pipeline_processing.sql)

---


*This is a proof-of-concept implementation. Please test thoroughly before using in production environments.*
