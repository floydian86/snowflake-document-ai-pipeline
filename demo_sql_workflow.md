# Snowflake Document AI Pipeline - SQL Demo Guide

## Overview

This guide provides a complete SQL-based proof-of-concept (POC) demonstration for the Snowflake Document AI Pipeline. Follow these step-by-step instructions to set up, test, and demonstrate the complete workflow for extracting data from PDF documents using Snowflake's Document AI capabilities.

## Prerequisites

- Access to a Snowflake account with Document AI features enabled
- ACCOUNTADMIN or equivalent privileges for initial setup
- Sample PDF documents for testing (available in the `pdf_documents/` directory)

## Demo Setup

### Step 1: Environment Preparation

First, set up your Snowflake environment by running the initial configuration:

```sql
-- Set context
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE COMPUTE_WH;

-- Create database and schema
CREATE DATABASE IF NOT EXISTS DOCUMENT_AI_DB;
USE DATABASE DOCUMENT_AI_DB;
CREATE SCHEMA IF NOT EXISTS PDF_PROCESSING;
USE SCHEMA PDF_PROCESSING;
```

### Step 2: Execute Database Objects Script

Run the complete database objects setup from `doc_ai_objects.sql`:

```sql
-- Execute the contents of doc_ai_objects.sql
-- This creates all necessary stages, tables, and functions

-- Key objects created:
-- 1. PDF_STAGE (internal stage for PDF files)
-- 2. RAW_PDF_DATA (table for raw document processing results)
-- 3. PROCESSED_DOCUMENTS (table for cleaned document data)
-- 4. DOCUMENT_PAGES (table for individual page content)
-- 5. DOCUMENT_TABLES (table for extracted table data)
```

### Step 3: Document Upload

Upload your sample PDF documents to the stage:

```sql
-- List available files in the stage
LIST @PDF_STAGE;

-- If files are not present, you can upload them via Snowflake UI or SnowSQL:
-- PUT file:///path/to/your/document.pdf @PDF_STAGE;
```

## SQL Workflow Demonstration

### Step 4: Process Documents Using Document AI

Execute the main processing workflow from `doc_ai_pipeline_processing.sql`:

```sql
-- 1. Process all PDF files in the stage
INSERT INTO RAW_PDF_DATA (file_name, processing_result, processed_timestamp)
SELECT 
    METADATA$FILENAME as file_name,
    PARSE_DOCUMENT(BUILD_SCOPED_FILE_URL(@PDF_STAGE, METADATA$FILENAME), {'mode': 'LAYOUT'}) as processing_result,
    CURRENT_TIMESTAMP as processed_timestamp
FROM @PDF_STAGE
WHERE METADATA$FILE_EXTENSION = 'pdf';

-- 2. Verify raw processing results
SELECT 
    file_name,
    processing_result:pages[0]:elements[0]:type as first_element_type,
    processing_result:pages[0]:elements[0]:content as first_element_content
FROM RAW_PDF_DATA
LIMIT 3;
```

### Step 5: Extract and Flatten Document Data

Transform the raw JSON into structured, queryable data:

```sql
-- Extract document-level metadata
INSERT INTO PROCESSED_DOCUMENTS (
    document_id, 
    file_name, 
    total_pages, 
    processing_status, 
    processed_timestamp
)
SELECT 
    ROW_NUMBER() OVER (ORDER BY file_name) as document_id,
    file_name,
    ARRAY_SIZE(processing_result:pages) as total_pages,
    'COMPLETED' as processing_status,
    processed_timestamp
FROM RAW_PDF_DATA;

-- Extract page-level content
INSERT INTO DOCUMENT_PAGES (
    document_id,
    page_number,
    page_text,
    element_count
)
SELECT 
    pd.document_id,
    (page_data.INDEX + 1) as page_number,
    ARRAY_TO_STRING(
        ARRAY_AGG(element.VALUE:content::STRING), 
        ' '
    ) as page_text,
    ARRAY_SIZE(page_data.VALUE:elements) as element_count
FROM PROCESSED_DOCUMENTS pd
JOIN RAW_PDF_DATA rd ON pd.file_name = rd.file_name,
LATERAL FLATTEN(rd.processing_result:pages) page_data,
LATERAL FLATTEN(page_data.VALUE:elements) element
WHERE element.VALUE:type = 'text'
GROUP BY pd.document_id, page_data.INDEX;
```

### Step 6: Extract Tables and Structured Data

Process any tables found in the documents:

```sql
-- Extract table data
INSERT INTO DOCUMENT_TABLES (
    document_id,
    page_number,
    table_index,
    table_data,
    row_count,
    column_count
)
SELECT 
    pd.document_id,
    (page_data.INDEX + 1) as page_number,
    (table_element.INDEX + 1) as table_index,
    table_element.VALUE as table_data,
    ARRAY_SIZE(table_element.VALUE:rows) as row_count,
    ARRAY_SIZE(table_element.VALUE:rows[0]:cells) as column_count
FROM PROCESSED_DOCUMENTS pd
JOIN RAW_PDF_DATA rd ON pd.file_name = rd.file_name,
LATERAL FLATTEN(rd.processing_result:pages) page_data,
LATERAL FLATTEN(page_data.VALUE:elements) table_element
WHERE table_element.VALUE:type = 'table';
```

## Demo Queries and Analysis

### Step 7: Demonstrate Query Capabilities

Show the power of the processed data with analytical queries:

```sql
-- 1. Document summary statistics
SELECT 
    COUNT(*) as total_documents,
    SUM(total_pages) as total_pages_processed,
    AVG(total_pages) as avg_pages_per_document,
    MIN(processed_timestamp) as first_processed,
    MAX(processed_timestamp) as last_processed
FROM PROCESSED_DOCUMENTS;

-- 2. Content analysis by document
SELECT 
    pd.file_name,
    pd.total_pages,
    COUNT(dp.page_number) as pages_with_text,
    COUNT(dt.table_index) as total_tables,
    SUM(LENGTH(dp.page_text)) as total_text_length
FROM PROCESSED_DOCUMENTS pd
LEFT JOIN DOCUMENT_PAGES dp ON pd.document_id = dp.document_id
LEFT JOIN DOCUMENT_TABLES dt ON pd.document_id = dt.document_id
GROUP BY pd.document_id, pd.file_name, pd.total_pages
ORDER BY pd.file_name;

-- 3. Text search across all documents
SELECT 
    pd.file_name,
    dp.page_number,
    SUBSTRING(dp.page_text, 1, 200) as text_preview
FROM PROCESSED_DOCUMENTS pd
JOIN DOCUMENT_PAGES dp ON pd.document_id = dp.document_id
WHERE UPPER(dp.page_text) LIKE '%YOUR_SEARCH_TERM%'
ORDER BY pd.file_name, dp.page_number;

-- 4. Table content analysis
SELECT 
    pd.file_name,
    dt.page_number,
    dt.table_index,
    dt.row_count,
    dt.column_count,
    dt.table_data:rows[0]:cells as first_row_sample
FROM PROCESSED_DOCUMENTS pd
JOIN DOCUMENT_TABLES dt ON pd.document_id = dt.document_id
ORDER BY pd.file_name, dt.page_number, dt.table_index;
```

## Advanced Features Demo

### Step 8: Document Classification and Tagging

Add intelligence to your document processing:

```sql
-- Add classification based on content patterns
ALTER TABLE PROCESSED_DOCUMENTS ADD COLUMN document_type VARCHAR(50);

UPDATE PROCESSED_DOCUMENTS 
SET document_type = 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM DOCUMENT_PAGES dp 
            WHERE dp.document_id = PROCESSED_DOCUMENTS.document_id 
            AND UPPER(dp.page_text) LIKE '%INVOICE%'
        ) THEN 'INVOICE'
        WHEN EXISTS (
            SELECT 1 FROM DOCUMENT_PAGES dp 
            WHERE dp.document_id = PROCESSED_DOCUMENTS.document_id 
            AND UPPER(dp.page_text) LIKE '%CONTRACT%'
        ) THEN 'CONTRACT'
        WHEN EXISTS (
            SELECT 1 FROM DOCUMENT_TABLES dt 
            WHERE dt.document_id = PROCESSED_DOCUMENTS.document_id
        ) THEN 'DATA_REPORT'
        ELSE 'GENERAL'
    END;

-- View document classification results
SELECT 
    document_type,
    COUNT(*) as document_count,
    AVG(total_pages) as avg_pages
FROM PROCESSED_DOCUMENTS
GROUP BY document_type;
```

### Step 9: Performance Monitoring

Monitor the pipeline performance:

```sql
-- Processing performance metrics
SELECT 
    DATE(processed_timestamp) as processing_date,
    COUNT(*) as documents_processed,
    SUM(total_pages) as pages_processed,
    AVG(total_pages) as avg_pages_per_doc,
    MIN(processed_timestamp) as first_processed,
    MAX(processed_timestamp) as last_processed
FROM PROCESSED_DOCUMENTS
GROUP BY DATE(processed_timestamp)
ORDER BY processing_date;

-- Storage usage analysis
SELECT 
    'RAW_PDF_DATA' as table_name,
    COUNT(*) as row_count
FROM RAW_PDF_DATA
UNION ALL
SELECT 
    'PROCESSED_DOCUMENTS' as table_name,
    COUNT(*) as row_count
FROM PROCESSED_DOCUMENTS
UNION ALL
SELECT 
    'DOCUMENT_PAGES' as table_name,
    COUNT(*) as row_count
FROM DOCUMENT_PAGES
UNION ALL
SELECT 
    'DOCUMENT_TABLES' as table_name,
    COUNT(*) as row_count
FROM DOCUMENT_TABLES;
```

## Demo Validation and Testing

### Step 10: Data Quality Checks

Validate the processing results:

```sql
-- 1. Check for processing errors
SELECT 
    file_name,
    CASE 
        WHEN processing_result IS NULL THEN 'NULL_RESULT'
        WHEN processing_result:error IS NOT NULL THEN 'PROCESSING_ERROR'
        ELSE 'SUCCESS'
    END as status
FROM RAW_PDF_DATA;

-- 2. Validate page extraction completeness
SELECT 
    pd.file_name,
    pd.total_pages as expected_pages,
    COUNT(DISTINCT dp.page_number) as extracted_pages,
    CASE 
        WHEN pd.total_pages = COUNT(DISTINCT dp.page_number) THEN 'COMPLETE'
        ELSE 'INCOMPLETE'
    END as extraction_status
FROM PROCESSED_DOCUMENTS pd
LEFT JOIN DOCUMENT_PAGES dp ON pd.document_id = dp.document_id
GROUP BY pd.document_id, pd.file_name, pd.total_pages;

-- 3. Content quality assessment
SELECT 
    pd.file_name,
    COUNT(dp.page_number) as pages_with_content,
    AVG(LENGTH(dp.page_text)) as avg_content_length,
    SUM(CASE WHEN LENGTH(dp.page_text) < 50 THEN 1 ELSE 0 END) as low_content_pages
FROM PROCESSED_DOCUMENTS pd
LEFT JOIN DOCUMENT_PAGES dp ON pd.document_id = dp.document_id
GROUP BY pd.document_id, pd.file_name;
```

## Troubleshooting Guide

### Common Issues and Solutions

1. **No Documents Processed**: Verify files are uploaded to the stage and have .pdf extension
2. **Empty Content**: Check Document AI permissions and file accessibility
3. **Performance Issues**: Consider using larger warehouse for processing multiple documents

### Debug Queries

```sql
-- Check stage contents
LIST @PDF_STAGE;

-- Examine raw processing results
SELECT 
    file_name,
    processing_result:pages[0]:pageInfo as page_info,
    ARRAY_SIZE(processing_result:pages) as page_count
FROM RAW_PDF_DATA;

-- Investigate processing errors
SELECT 
    file_name,
    processing_result:error as error_details
FROM RAW_PDF_DATA
WHERE processing_result:error IS NOT NULL;
```

## Demo Conclusion

This SQL-based POC demonstrates:

1. ✅ **Complete PDF Processing Pipeline**: From upload to structured data extraction
2. ✅ **Scalable Architecture**: Handles multiple documents efficiently
3. ✅ **Rich Data Analysis**: Text search, table extraction, and classification
4. ✅ **Quality Monitoring**: Built-in validation and performance metrics
5. ✅ **SQL-Native**: All processing done within Snowflake using standard SQL

### Next Steps

- **Production Deployment**: Scale the solution with automation and error handling
- **Integration**: Connect with BI tools and downstream applications  
- **Advanced AI**: Implement custom extraction patterns for specific document types
- **Monitoring**: Set up automated quality checks and alerting

### Resources

- [Snowflake Document AI Documentation](https://docs.snowflake.com/)
- [SQL Scripts in this Repository](./doc_ai_objects.sql)
- [Processing Workflow](./doc_ai_pipeline_processing.sql)

---

*This demo guide provides a complete end-to-end workflow for evaluating Snowflake's Document AI capabilities. Customize the queries and processing logic based on your specific document types and business requirements.*
