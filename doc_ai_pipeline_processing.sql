CREATE OR REPLACE STAGE my_pdf_stage
  DIRECTORY = (ENABLE = TRUE)
  ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE');

  CREATE STREAM my_pdf_stream ON STAGE my_pdf_stage;

  ALTER STAGE my_pdf_stage REFRESH;

  CREATE OR REPLACE TABLE pdf_reviews (
  file_name VARCHAR,
  file_size VARIANT,
  last_modified VARCHAR,
  snowflake_file_url VARCHAR,
  json_content VARCHAR
);


CREATE OR REPLACE TASK load_new_file_data
  WAREHOUSE = DOC_AI_WH
  SCHEDULE = '1 minutes'
  COMMENT = 'Process new files in the stage and insert data into the pdf_reviews table.'
WHEN SYSTEM$STREAM_HAS_DATA('my_pdf_stream')
AS
INSERT INTO pdf_reviews (
  SELECT
    RELATIVE_PATH AS file_name,
    size AS file_size,
    last_modified,
    file_url AS snowflake_file_url,
    inspection_reviews!PREDICT(GET_PRESIGNED_URL('@my_pdf_stage', RELATIVE_PATH), 1) AS json_content
  FROM my_pdf_stream
  WHERE METADATA$ACTION = 'INSERT'
);

ALTER TASK load_new_file_data RESUME;


select * FROM pdf_reviews;


-- FLATTEN the JSON CONTENT FROM PDF_REVIEWS TABLE

CREATE OR REPLACE TABLE doc_ai_db.doc_ai_schema.pdf_reviews_flatten AS (
 WITH temp AS (
   SELECT
     RELATIVE_PATH AS file_name,
     size AS file_size,
     last_modified,
     file_url AS snowflake_file_url,
     inspection_reviews!PREDICT(get_presigned_url('@my_pdf_stage', RELATIVE_PATH), 1) AS json_content
   FROM directory(@my_pdf_stage)
 )

 SELECT
   file_name,
   file_size,
   last_modified,
   snowflake_file_url,
   json_content:__documentMetadata.ocrScore::FLOAT AS ocrScore,
   f.value:score::FLOAT AS inspection_date_score,
   f.value:value::STRING AS inspection_date_value,
   g.value:score::FLOAT AS inspection_grade_score,
   g.value:value::STRING AS inspection_grade_value,
   i.value:score::FLOAT AS inspector_score,
   i.value:value::STRING AS inspector_value,
   ARRAY_TO_STRING(ARRAY_AGG(j.value:value::STRING), ', ') AS list_of_units
 FROM temp,
   LATERAL FLATTEN(INPUT => json_content:inspection_date) f,
   LATERAL FLATTEN(INPUT => json_content:inspection_grade) g,
   LATERAL FLATTEN(INPUT => json_content:inspector) i,
   LATERAL FLATTEN(INPUT => json_content:list_of_units) j
 GROUP BY ALL
);


SELECT FILE_NAME as FILE_PROCESSED,
inspector_value as inspector_name,
inspection_date_value as inspection_date,
--inspection_date_score,
inspection_grade_value as inspection_grade,
--inspection_grade_score,
--ocrscore,
list_of_units

FROM PDF_REVIEWS_FLATTEN;
