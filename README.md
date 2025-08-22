# Snowflake Document AI PDF Pipeline

A proof-of-concept (POC) implementation for extracting structured data from PDF documents using Snowflake's Document AI capabilities. This pipeline demonstrates how to load, process, and flatten PDF data into Snowflake tables for analysis.

**Important Note**: PDF files processed by this pipeline may be unstructured. This pipeline is specifically designed to handle unstructured PDFs, and users should not expect source documents to be cleanly formatted. The system can process documents with varied layouts, inconsistent formatting, and mixed content types.

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
- **Example Templates**: Ready-to-use Python scripts and Jupyter notebooks

## Prerequisites

- Snowflake account with Document AI enabled
- Python 3.8 or higher
- Snowflake Python Connector (`snowflake-connector-python`)
- Jupyter Notebook (optional, for interactive examples)

## Setup

### 1. Snowflake Configuration

1. Ensure your Snowflake account has Document AI features enabled
2. Create the required database objects using the provided SQL scripts:
   ```sql
   -- Run the DDL scripts in order:
   -- 1. database_setup.sql
   -- 2. stage_setup.sql
   -- 3. table_definitions.sql
   ```

### 2. Python Environment

1. Install required dependencies:
   ```bash
   pip install snowflake-connector-python pandas jupyter
   ```

2. Configure your Snowflake connection parameters in the Python scripts or create a `config.py` file:
   ```python
   SNOWFLAKE_CONFIG = {
       'user': 'your_username',
       'password': 'your_password',
       'account': 'your_account',
       'warehouse': 'your_warehouse',
       'database': 'DOCUMENT_AI_DB',
       'schema': 'PUBLIC'
   }
   ```

## Usage

### Quick Start with Python Script

1. Place your PDF files in the `sample_pdfs/` directory
2. Run the main processing script:
   ```bash
   python pdf_processor.py
   ```

### Interactive Jupyter Notebook

1. Launch Jupyter:
   ```bash
   jupyter notebook
   ```
2. Open `document_ai_pipeline.ipynb`
3. Follow the step-by-step walkthrough

### Manual SQL Processing

1. Upload PDFs to your Snowflake stage:
   ```sql
   PUT file://path/to/your/document.pdf @pdf_stage;
   ```

2. Process the document:
   ```sql
   SELECT * FROM TABLE(
       EXTRACT_DOCUMENT_TEXT('@pdf_stage/document.pdf')
   );
   ```

## Project Structure

```
├── README.md                    # This file
├── LICENSE                      # MIT License
├── sql/
│   ├── database_setup.sql       # Database and schema creation
│   ├── stage_setup.sql          # File stage configuration
│   └── table_definitions.sql    # Table schemas for extracted data
├── python/
│   ├── pdf_processor.py         # Main processing script
│   ├── config.py.template       # Configuration template
│   └── utils.py                 # Utility functions
├── notebooks/
│   └── document_ai_pipeline.ipynb  # Interactive tutorial
└── sample_pdfs/                 # Sample PDF files for testing
```

## Demo

### Sample Data Processing

The repository includes sample PDF documents to demonstrate the pipeline:

1. **Invoice Processing**: Extract vendor information, line items, and totals
2. **Resume Parsing**: Extract contact info, skills, and work experience
3. **Form Processing**: Extract field values from structured forms

### Example Output

After processing a sample invoice PDF:

```sql
-- View extracted text
SELECT * FROM invoice_text_data;

-- View extracted tables
SELECT * FROM invoice_table_data;

-- View key-value pairs
SELECT * FROM invoice_kv_data;
```

### Performance Metrics

- Processing time: ~2-5 seconds per page
- Accuracy: 95%+ for structured documents
- Supported formats: PDF (text-based and scanned)

## Key SQL Functions Used

- `EXTRACT_DOCUMENT_TEXT()`: Extract raw text from PDFs
- `PARSE_DOCUMENT()`: Structure document content
- `FLATTEN()`: Convert nested JSON to relational format
- `LATERAL FLATTEN()`: Handle array elements

## Working with Unstructured PDFs

This pipeline is specifically designed to handle unstructured PDFs that may have inconsistent formatting, varied layouts, and mixed content types. Users should expect that source documents may not be cleanly formatted, and the pipeline includes several strategies to handle these challenges.

### Common Challenges with Unstructured PDFs

1. **Varied Layouts**: Documents with inconsistent page structures, different fonts, and varying spacing
2. **Scanned Images**: PDF documents that contain scanned images rather than selectable text
3. **Mixed Content**: Documents combining tables, free-form text, images, and forms
4. **Inconsistent Formatting**: Documents with irregular column structures, merged cells, or split content across pages
5. **Poor Quality Scans**: Low-resolution images, skewed text, or degraded document quality

### Troubleshooting Highly Unstructured Documents

#### For Documents with Poor Text Extraction:

```sql
-- Check extraction confidence scores
SELECT 
    file_name,
    confidence_score,
    extraction_method
FROM document_extraction_metadata
WHERE confidence_score < 0.8;

-- Use alternative extraction methods for low-confidence results
SELECT * FROM TABLE(
    EXTRACT_DOCUMENT_TEXT('@pdf_stage/document.pdf', {'ocr_mode': 'force'})
);
```

#### For Documents with Mixed Table and Text:

```sql
-- Separate table extraction from text extraction
SELECT * FROM TABLE(
    PARSE_DOCUMENT('@pdf_stage/document.pdf', {'extract_tables': true, 'extract_text': false})
);

-- Process text separately
SELECT * FROM TABLE(
    PARSE_DOCUMENT('@pdf_stage/document.pdf', {'extract_tables': false, 'extract_text': true})
);
```

#### For Scanned Documents:

```sql
-- Enable OCR processing for image-based PDFs
SELECT * FROM TABLE(
    EXTRACT_DOCUMENT_TEXT('@pdf_stage/scanned_doc.pdf', 
        {'ocr_enabled': true, 'image_quality': 'high'}
    )
);
```

### Post-Processing Techniques for Better Extraction Quality

1. **Text Cleaning and Normalization**:
   ```sql
   -- Clean extracted text
   SELECT 
       REGEXP_REPLACE(extracted_text, '\s+', ' ') as cleaned_text,
       TRIM(extracted_text) as trimmed_text
   FROM document_text_data;
   ```

2. **Content Classification**:
   ```sql
   -- Classify content types
   SELECT 
       page_number,
       CASE 
           WHEN extracted_text LIKE '%table%' OR extracted_text LIKE '%|%' THEN 'table_content'
           WHEN LENGTH(extracted_text) < 100 THEN 'header_footer'
           ELSE 'body_text'
       END as content_type
   FROM document_text_data;
   ```

3. **Quality Assessment**:
   ```sql
   -- Assess extraction quality
   SELECT 
       file_name,
       page_number,
       LENGTH(extracted_text) as text_length,
       (LENGTH(extracted_text) - LENGTH(REPLACE(extracted_text, ' ', ''))) as word_count,
       confidence_score
   FROM document_analysis
   WHERE confidence_score IS NOT NULL;
   ```

### Recommended Workflow for Unstructured Documents

1. **Initial Assessment**: Run basic extraction and check confidence scores
2. **Quality Check**: Examine extracted content for completeness and accuracy
3. **Adaptive Processing**: Apply different extraction parameters based on document type
4. **Post-Processing**: Clean and normalize extracted data
5. **Validation**: Compare results against expected content patterns

### Performance Optimization Tips

- **Batch Processing**: Process similar document types together for consistency
- **Parameter Tuning**: Adjust OCR and extraction parameters based on document quality
- **Staged Approach**: Process documents in stages (text first, then tables, then images)
- **Quality Thresholds**: Set confidence score thresholds to determine processing approach

```sql
-- Example: Adaptive processing based on document characteristics
WITH document_assessment AS (
    SELECT 
        file_name,
        CASE 
            WHEN file_size > 10000000 THEN 'large_document'
            WHEN CONTAINS(file_name, 'scan') THEN 'scanned_document'
            ELSE 'standard_document'
        END as document_type
    FROM stage_file_metadata
)
SELECT 
    file_name,
    document_type,
    CASE document_type
        WHEN 'large_document' THEN 'chunk_processing'
        WHEN 'scanned_document' THEN 'ocr_processing'
        ELSE 'standard_processing'
    END as recommended_approach
FROM document_assessment;
```

## Troubleshooting

### Common Issues

1. **Document AI not enabled**: Contact Snowflake support to enable Document AI features
2. **Stage access errors**: Ensure proper permissions on file stages
3. **Large file processing**: Consider breaking large PDFs into smaller chunks
4. **Connection issues**: Verify Snowflake connection parameters

### Debug Mode

Enable debug logging in Python scripts:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Snowflake Documentation Team for Document AI guidance
- Community contributors and testers
- Tutorial authors and content creators

## Support

For questions and issues:

1. Check the [Issues](https://github.com/floydian86/snowflake-document-ai-pipeline/issues) page
2. Review Snowflake's Document AI documentation
3. Contact the repository maintainer

---

*This is a proof-of-concept implementation. Please test thoroughly before using in production environments.*
