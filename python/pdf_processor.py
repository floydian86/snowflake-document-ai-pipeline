#!/usr/bin/env python3
"""
Snowflake Document AI PDF Processor

This script demonstrates how to load, process, and flatten PDF documents
using Snowflake's Document AI capabilities.

Author: floydian86
License: MIT
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

import pandas as pd
import snowflake.connector
from snowflake.connector import DictCursor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
SNOWFLAKE_CONFIG = {
    'user': os.getenv('SNOWFLAKE_USER', 'your_username'),
    'password': os.getenv('SNOWFLAKE_PASSWORD', 'your_password'),
    'account': os.getenv('SNOWFLAKE_ACCOUNT', 'your_account'),
    'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE', 'your_warehouse'),
    'database': os.getenv('SNOWFLAKE_DATABASE', 'DOCUMENT_AI_DB'),
    'schema': os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC')
}

class SnowflakeDocumentAI:
    """
    Main class for processing PDFs using Snowflake Document AI
    """
    
    def __init__(self, config: Dict[str, str]):
        """
        Initialize the Document AI processor
        
        Args:
            config: Snowflake connection configuration
        """
        self.config = config
        self.connection = None
        self.cursor = None
        
    def connect(self) -> bool:
        """
        Establish connection to Snowflake
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.connection = snowflake.connector.connect(**self.config)
            self.cursor = self.connection.cursor(DictCursor)
            logger.info("Successfully connected to Snowflake")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            return False
    
    def disconnect(self):
        """
        Close Snowflake connection
        """
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("Disconnected from Snowflake")
    
    def setup_database_objects(self) -> bool:
        """
        Create necessary database objects for Document AI processing
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        try:
            # Create database if not exists
            self.cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.config['database']}")
            
            # Use the database
            self.cursor.execute(f"USE DATABASE {self.config['database']}")
            self.cursor.execute(f"USE SCHEMA {self.config['schema']}")
            
            # Create file stage for PDFs
            stage_sql = """
            CREATE STAGE IF NOT EXISTS pdf_stage
            FILE_FORMAT = (TYPE = 'CSV' SKIP_HEADER = 1)
            COMMENT = 'Stage for PDF documents'
            """
            self.cursor.execute(stage_sql)
            
            # Create tables for extracted data
            tables_sql = [
                """
                CREATE TABLE IF NOT EXISTS document_text_data (
                    document_name VARCHAR(255),
                    page_number INTEGER,
                    extracted_text TEXT,
                    confidence_score FLOAT,
                    processing_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS document_table_data (
                    document_name VARCHAR(255),
                    page_number INTEGER,
                    table_id INTEGER,
                    table_data VARIANT,
                    processing_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS document_kv_data (
                    document_name VARCHAR(255),
                    page_number INTEGER,
                    key_name VARCHAR(255),
                    key_value TEXT,
                    confidence_score FLOAT,
                    processing_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            ]
            
            for sql in tables_sql:
                self.cursor.execute(sql)
            
            logger.info("Database objects created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup database objects: {e}")
            return False
    
    def upload_pdf(self, pdf_path: str) -> bool:
        """
        Upload PDF file to Snowflake stage
        
        Args:
            pdf_path: Local path to PDF file
            
        Returns:
            bool: True if upload successful, False otherwise
        """
        try:
            pdf_file = Path(pdf_path)
            if not pdf_file.exists():
                logger.error(f"PDF file not found: {pdf_path}")
                return False
            
            # Upload file to stage
            upload_sql = f"PUT file://{pdf_path} @pdf_stage AUTO_COMPRESS=FALSE"
            self.cursor.execute(upload_sql)
            
            logger.info(f"Successfully uploaded {pdf_file.name} to stage")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload PDF: {e}")
            return False
    
    def process_pdf(self, pdf_filename: str) -> bool:
        """
        Process PDF using Snowflake Document AI functions
        
        Args:
            pdf_filename: Name of PDF file in stage
            
        Returns:
            bool: True if processing successful, False otherwise
        """
        try:
            # Extract text using Document AI
            extract_sql = f"""
            INSERT INTO document_text_data (document_name, page_number, extracted_text, confidence_score)
            SELECT 
                '{pdf_filename}' as document_name,
                page_number,
                extracted_text,
                confidence_score
            FROM TABLE(
                EXTRACT_DOCUMENT_TEXT('@pdf_stage/{pdf_filename}')
            )
            """
            
            self.cursor.execute(extract_sql)
            
            # Extract tables if available
            table_sql = f"""
            INSERT INTO document_table_data (document_name, page_number, table_id, table_data)
            SELECT 
                '{pdf_filename}' as document_name,
                page_number,
                table_id,
                table_data
            FROM TABLE(
                EXTRACT_DOCUMENT_TABLES('@pdf_stage/{pdf_filename}')
            )
            """
            
            try:
                self.cursor.execute(table_sql)
            except Exception as table_error:
                logger.warning(f"Table extraction failed (may not be available): {table_error}")
            
            # Extract key-value pairs if available
            kv_sql = f"""
            INSERT INTO document_kv_data (document_name, page_number, key_name, key_value, confidence_score)
            SELECT 
                '{pdf_filename}' as document_name,
                page_number,
                key_name,
                key_value,
                confidence_score
            FROM TABLE(
                EXTRACT_DOCUMENT_KEY_VALUES('@pdf_stage/{pdf_filename}')
            )
            """
            
            try:
                self.cursor.execute(kv_sql)
            except Exception as kv_error:
                logger.warning(f"Key-value extraction failed (may not be available): {kv_error}")
            
            logger.info(f"Successfully processed {pdf_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process PDF: {e}")
            return False
    
    def get_extracted_data(self, pdf_filename: str) -> Dict[str, pd.DataFrame]:
        """
        Retrieve extracted data as pandas DataFrames
        
        Args:
            pdf_filename: Name of processed PDF file
            
        Returns:
            Dict containing DataFrames for text, tables, and key-value data
        """
        results = {}
        
        try:
            # Get text data
            text_sql = f"""
            SELECT * FROM document_text_data 
            WHERE document_name = '{pdf_filename}'
            ORDER BY page_number
            """
            self.cursor.execute(text_sql)
            results['text'] = pd.DataFrame(self.cursor.fetchall())
            
            # Get table data
            table_sql = f"""
            SELECT * FROM document_table_data 
            WHERE document_name = '{pdf_filename}'
            ORDER BY page_number, table_id
            """
            self.cursor.execute(table_sql)
            results['tables'] = pd.DataFrame(self.cursor.fetchall())
            
            # Get key-value data
            kv_sql = f"""
            SELECT * FROM document_kv_data 
            WHERE document_name = '{pdf_filename}'
            ORDER BY page_number
            """
            self.cursor.execute(kv_sql)
            results['key_values'] = pd.DataFrame(self.cursor.fetchall())
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to retrieve extracted data: {e}")
            return {}
    
    def process_directory(self, pdf_directory: str) -> bool:
        """
        Process all PDF files in a directory
        
        Args:
            pdf_directory: Path to directory containing PDFs
            
        Returns:
            bool: True if all files processed successfully
        """
        pdf_dir = Path(pdf_directory)
        if not pdf_dir.exists():
            logger.error(f"Directory not found: {pdf_directory}")
            return False
        
        pdf_files = list(pdf_dir.glob("*.pdf"))
        if not pdf_files:
            logger.warning(f"No PDF files found in {pdf_directory}")
            return False
        
        success_count = 0
        for pdf_file in pdf_files:
            logger.info(f"Processing {pdf_file.name}...")
            
            # Upload and process PDF
            if self.upload_pdf(str(pdf_file)) and self.process_pdf(pdf_file.name):
                success_count += 1
                logger.info(f"Successfully processed {pdf_file.name}")
            else:
                logger.error(f"Failed to process {pdf_file.name}")
        
        logger.info(f"Processed {success_count}/{len(pdf_files)} PDF files successfully")
        return success_count == len(pdf_files)


def main():
    """
    Main execution function
    """
    logger.info("Starting Snowflake Document AI PDF Processor")
    
    # Initialize processor
    processor = SnowflakeDocumentAI(SNOWFLAKE_CONFIG)
    
    try:
        # Connect to Snowflake
        if not processor.connect():
            sys.exit(1)
        
        # Setup database objects
        if not processor.setup_database_objects():
            sys.exit(1)
        
        # Process PDFs from sample_pdfs directory
        sample_dir = Path("sample_pdfs")
        if sample_dir.exists():
            processor.process_directory(str(sample_dir))
        else:
            logger.warning("sample_pdfs directory not found. Please create it and add PDF files.")
            
            # Example of processing a single file
            sample_file = "example.pdf"
            if Path(sample_file).exists():
                logger.info(f"Processing single file: {sample_file}")
                if processor.upload_pdf(sample_file):
                    processor.process_pdf(sample_file)
                    
                    # Display results
                    results = processor.get_extracted_data(sample_file)
                    for data_type, df in results.items():
                        if not df.empty:
                            logger.info(f"\n{data_type.upper()} DATA:")
                            logger.info(df.head().to_string())
        
        logger.info("Processing completed successfully")
        
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        processor.disconnect()


if __name__ == "__main__":
    main()
