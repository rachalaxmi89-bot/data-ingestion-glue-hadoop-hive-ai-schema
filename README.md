# Data Ingestion & ETL: AWS Glue, Hadoop/Hive, and an AI Schema Designer

 **serverless ETL pipeline on AWS Glue**, a **distributed storage + SQL analytics workflow on Hadoop/Hive**, and a **Dockerized AI tool that generates database schemas from natural language** using a locally-hosted LLM.

---

## Project Structure

```
.
├── README.md
├── glue-etl/
│   └── ETL-AWS-Glue.md          # AWS Glue ETL pipeline — steps, transforms, output
├── hadoop-hive/
│   ├── steps.md                 # HDFS + Hive commands and queries
│   └── problem-1-data.csv       # Source employee dataset
└── ai-schema-designer/
    └── schema_designer.py       # AI-powered schema generator (Ollama + Docker)
```

---

## Part 1 — AWS Glue ETL Pipeline

**Goal:** Extract, transform, and load Employee and Department data using a fully serverless AWS pipeline.

### Architecture
```
S3 (Raw CSVs) → Glue Crawlers → Glue Data Catalog → Glue ETL Job → S3 (Processed)
```

### What Was Built
1. **S3 setup** — created a bucket with separate raw and processed folders; uploaded Employee and Department CSVs.
2. **Glue Crawlers** — configured crawlers to scan both CSVs and auto-generate table schemas in the Glue Data Catalog.
3. **Transformations** (Glue ETL Job):
   - Removed null values (`age IS NOT NULL`)
   - Added a processing timestamp column
   - Joined Employee and Department tables on `dept_id`
4. **Output** — wrote the cleaned, joined result to `/processed/` in S3 (Parquet/CSV).

### Sample Output
| emp_id | name | age | dept_name | processed_time |
|---|---|---|---|---|
| 1 | Alice | 25 | HR | `timestamp` |
| 2 | Bob | 30 | IT | `timestamp` |

### Challenges
Resolved **IAM permission issues** on the Glue job role and **crawler configuration errors** during initial setup.

### Why Glue
Glue's value here isn't the join itself — a small join could be done in pandas. The point is the **pattern**: managed, serverless Spark execution with no cluster to provision, and a **Data Catalog** that makes the resulting tables immediately queryable by other AWS tools (Athena, Redshift Spectrum) without extra setup. That pattern is what scales when the pipeline needs to run repeatedly, at larger volume, or be shared across teams.

---

## Part 2 — Hadoop HDFS + Hive Analytics

**Goal:** Analyze workforce cost-to-company and country-wise profitability for a multinational company using distributed storage and SQL-on-Hadoop.

### Architecture
```
Local CSV → HDFS (distributed storage) → Hive external table → HiveQL analytics
```

### What Was Built

**1. HDFS setup**
```bash
docker exec -it namenode bash
hdfs dfs -mkdir /PartBTest
docker cp problem-1-data.csv namenode:/tmp/
hdfs dfs -put /tmp/problem-1-data.csv /PartBTest
hdfs dfs -ls /PartBTest
```

**2. File replication across HDFS directories**
```bash
hdfs dfs -mkdir /PartBTest2
hdfs dfs -cp /PartBTest/problem-1-data.csv /PartBTest2
hdfs dfs -ls /PartBTest2
```

**3. Hive table creation**
```sql
CREATE TABLE IF NOT EXISTS employee_data (
    empId       INT,
    employeeAge INT,
    salary      INT,
    country     STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE;

LOAD DATA INPATH 'hdfs://namenode:8020/PartBTest/problem-1-data.csv' INTO TABLE employee_data;
```

**4. Country-wise workforce analysis**
```sql
SELECT country, COUNT(*) AS employee_count
FROM employee_data
GROUP BY country
ORDER BY employee_count DESC;
```

### Why Hadoop/Hive
The scenario is framed as a **Big Data** problem — Hive is built to query large files sitting in distributed storage (HDFS) that wouldn't fit or perform well in a single-node database. HiveQL gives SQL-like access to that data without writing MapReduce/Spark code directly, translating familiar SQL into distributed jobs under the hood.

---

## Part 3 — AI-Based Schema Designer (Docker + Ollama)

**Goal:** Build an AI-assisted tool that designs relational database schemas from plain-English requirements — automating a task normally requiring a human data architect.

### Architecture
```
User (plain English) → Python CLI → Ollama (Llama 3, in Docker) → SQL schema (DDL) → saved .sql file
```

### How It Works
- Runs entirely against a **local LLM** (Llama 3, served via Ollama in Docker) — no cloud API, no cost, no data leaving the machine.
- A **system prompt** instructs the model to act as a database architect: produce a normalized schema, output clean SQL `CREATE TABLE` statements with keys/constraints, and suggest sample `INSERT`/`SELECT` queries.
- Supports a **multi-turn conversation** — the schema can be iteratively refined (e.g., "add a Department table and link it by foreign key") since conversation history is preserved.
- Includes a **connection health check** before starting, with a clear error message pointing to `docker compose ps` if Ollama isn't reachable.
- Generated schemas are saved to timestamped `.sql` files for a durable, reviewable output.

### CLI Commands
| Command | Action |
|---|---|
| *(free text)* | Generate or refine a schema based on the requirement described |
| `save` | Save the current schema to a `.sql` file |
| `new` | Start a fresh conversation/session |
| `quit` | Exit |

### Running It
```bash
# Ensure Ollama is running in Docker with the llama3 model pulled
docker exec -it ollama ollama pull llama3

# Install dependencies
pip install requests

# Run the tool
python schema_designer.py
```

### Example Session
```
You: I need to track employees and their departments

AI Schema Designer:
-----------------------------------------------------------------
CREATE TABLE department (
    dept_id   INT PRIMARY KEY,
    dept_name VARCHAR(100) NOT NULL
);

CREATE TABLE employee (
    emp_id    INT PRIMARY KEY,
    name      VARCHAR(100) NOT NULL,
    age       INT,
    dept_id   INT,
    FOREIGN KEY (dept_id) REFERENCES department(dept_id)
);
-----------------------------------------------------------------
[Tip] Type 'save' to save this schema, or ask for modifications.
```

### Design Note: Generation vs. Execution
This tool **generates** SQL — it does not auto-execute it against a live database. That's a deliberate choice: reviewing AI-generated DDL before running it against real infrastructure is safer than blind execution. A natural next step would be adding a validated execution path (e.g., via `psycopg2`/`SQLAlchemy` against a Dockerized Postgres instance) behind an explicit confirmation step.

---

## How These Three Parts Connect

| Stage | Tool | Role |
|---|---|---|
| **Design** | AI Schema Designer (Ollama) | Proposes the schema/table structure from requirements |
| **Ingest & Transform** | AWS Glue | Moves and cleans real data at scale into a queryable table |
| **Store & Query** | Hadoop HDFS + Hive | Stores large files in distributed storage and queries them with SQL |

In a real pipeline these represent three layers of the same workflow: **design → ingest/transform → store/analyze**. The AI tool automates the design step that normally needs a human data architect; Glue and Hive are the execution engines that actually move and query data at scale once that design is approved.

---

## Tech Stack

| Category | Tools |
|---|---|
| Cloud ETL | AWS Glue, AWS S3, IAM |
| Distributed Storage | Hadoop HDFS |
| SQL-on-Hadoop | Apache Hive, HiveQL |
| AI / LLM | Ollama, Llama 3 |
| Containerization | Docker |
| Language | Python, SQL |

---

## Key Concepts Demonstrated

- Serverless ETL design with schema discovery via crawlers and a shared Data Catalog
- Distributed file system operations (HDFS) and SQL-on-Hadoop querying (Hive)
- Local LLM deployment (Ollama in Docker) for a design-time, agentic AI use case
- Understanding of where each tool fits in a layered data platform — design, ingestion, storage, and analytics are separate concerns solved by different tools, not interchangeable ones

## Future Improvements

- Add automated validation/linting of AI-generated SQL before saving
- Wire the schema designer to an execution path (create tables in a live Postgres instance) behind a confirmation step
- Add Hive table partitioning by country for larger-scale query performance
- Parameterize the Glue job (bucket names, join keys) instead of hardcoding
