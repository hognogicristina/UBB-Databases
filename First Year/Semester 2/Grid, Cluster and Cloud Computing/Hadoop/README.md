**README**

# Project Overview

This repository demonstrates a simple Hadoop-based WordCounter application using Docker containers to simulate a Hadoop cluster. It downloads large English texts from Project Gutenberg, stores them in HDFS, runs a MapReduce job to compute word occurrences per book, and retrieves the results.

## Directory Structure

```
/ (project root)
├── build.sh                # Main build script for building all Docker images and running the entire workflow
├── docker-compose.yml      # Defines the Hadoop cluster (NameNode, DataNodes, ResourceManager, NodeManagers) via Docker Compose
├── hadoop.env              # Configuration file for Hadoop environment variables
├── submit/                 # Contains Dockerfile and run.sh for submitting the WordCounter job
│   ├── Dockerfile          # Builds the "hadoop-wordcounter" image
│   ├── index.jar           # JAR containing compiled WordCounter classes and stopwords.txt
│   ├── all_books.txt       # Single large concatenated text of all books
│   └── run.sh              # Script to copy the concatenated file into HDFS, show block locations, run WordCounter, and retrieve results
├── wordcounter/            # Contains Java source, build scripts, and init script for the compile-and-test container
│   ├── build.sh            # Compiles WordCounter.java inside the "hadoop-compiler" container, producing index.jar
│   ├── init.sh             # Launches a live Hadoop environment inside the "hadoop-compiler" container for testing/debugging
│   ├── WordCounter.java    # Mapper, Combiner, Reducer, and driver code
│   └── stopwords.txt       # List of words to ignore (e.g., "the", "and", ...)
└── download-books.sh       # Downloads 6 large English Gutenberg books >512 KB each and saves them as book1.txt–book6.txt, printing each file’s size
```

*All scripts should be made executable (`chmod +x`).*

---

## Pre-requisites

* Docker (with at least Docker Engine 20.x)
* Docker Compose
* At least 4 GB RAM available for the Hadoop containers
* A Linux/macOS host (the scripts assume a Unix-like environment for `stat`, `ls -lh`, etc.)

---

## High-Level Build & Run Steps

> **Important:** Run these steps **in order**.
>
> 1. `build.sh` from the project root
> 2. `docker-compose up -d`
> 3. `init.sh` from the `wordcounter/` directory
> 4. If there are no errors:
     >
     >    * `build.sh` from the `wordcounter/` directory
>    * `run.sh` from the project root

### 1. `build.sh` (project root)

```bash
chmod +x build.sh   # only needed once to make it executable
./build.sh
```

This script will:

1. Build **all** Docker images for the mini Hadoop cluster:

    * `hadoop-base`: base image containing Hadoop 3.4.1 binaries and Java 11
    * `hadoop-namenode`: starts HDFS NameNode
    * `hadoop-datanode` (3 copies): each runs an HDFS DataNode
    * `hadoop-resourcemanager`: runs YARN ResourceManager
    * `hadoop-nodemanager`: runs YARN NodeManager
    * (HistoryServer is commented out)
    * `hadoop-wordcounter`: image that bundles `index.jar`, `all_books.txt`, and `run.sh` for job submission
2. After all images are built, it exits.

> **Note:** A successful `build.sh` will leave you with images named:
> `hadoop-base`, `hadoop-namenode`, `hadoop-datanode`, `hadoop-resourcemanager`, `hadoop-nodemanager`, `hadoop-wordcounter`.

### 2. `docker-compose up -d` (project root)

```bash
docker-compose up -d
```

This will:

* Launch a 4-node HDFS cluster (1 NameNode + 3 DataNodes)
* Launch a YARN cluster (1 ResourceManager + 1 NodeManager)
* All containers share the network `hadoop-bby_default` defined in `docker-compose.yml`.

**What is running now?**

* **HDFS NameNode** listens at `namenode:9000` (client RPC) and `namenode:9870` (Web UI)
* **DataNodes** each register with the NameNode, store data blocks
* **YARN ResourceManager** listens at `resourcemanager:8032` (YARN RPC) and `resourcemanager:8088` (Web UI)
* **YARN NodeManager** runs on a single NodeManager container

Give it \~20 seconds to ensure all containers are healthy and HDFS reports 3 DataNodes.

### 3. `init.sh` (inside `wordcounter/`)

```bash
cd wordcounter
chmod +x init.sh   # make sure it’s executable
bash init.sh
```

This will:

1. Build the `hadoop-compiler` image (a Debian container with Hadoop tools)
2. Launch an interactive shell in `hadoop-compiler` with HDFS ports mapped locally:

    * `-p 9871:9870`  (to view NameNode UI at `http://localhost:9871`)
    * `-p 8089:8088`  (to view YARN UI at `http://localhost:8089`)
3. Mount a host directory `$(pwd)/hadoop-data` into `/hadoop-data` (unused for this step, but ready if needed).

Inside that interactive shell, you can manually test HDFS commands, e.g.:

```bash
hdfs dfs -ls /
hdfs dfs -mkdir /test
hdfs dfs -put somefile /test
# etc.
```

When ready, type `exit` to leave that container.

> At this point, your Hadoop cluster is built, HDFS is running, and you can compile/test WordCounter inside the `hadoop-compiler` container.

### 4. (If no errors) `build.sh` (inside `wordcounter/`)

```bash
cd wordcounter
bash build.sh
```

This will:

1. Copy `WordCounter.java` and `stopwords.txt` into the running `hadoop-compiler` container’s `/tmp`
2. Run `javac -encoding UTF-8 -classpath $(hadoop classpath) WordCounter.java` to compile (so non-ASCII punctuation is allowed)
3. Package `WordCounter*.class` plus `stopwords.txt` into `index.jar`
4. Copy `index.jar` back out to the host and into `../submit/index.jar`

At the end, you should see:

```
index.jar built and copied to host.
```

### 5. `run.sh` (project root)

```bash
bash run.sh
```

What it does:

1. Rebuilds the `hadoop-wordcounter` image (`./submit` directory)
2. Formats the HDFS NameNode (`hdfs namenode -format -force`)
3. Deletes any existing `/output` in HDFS
4. Recreates `/books` directory in HDFS
5. Uploads each of the 10 book files (as `COPY`ed into `/opt/hadoop/`) into `/books` in HDFS
6. Runs `hdfs fsck /books/bookX.txt -files -blocks -locations` to verify split/chunk placement
7. Lists `/` to confirm `/books` and other dirs
8. Prints the size (`%o`) of each `/books/<book>.txt`
9. Runs `hadoop-wordcounter` (which launches the MapReduce WordCounter job: Mapper → Combiner → Reducer)
10. Retrieves `/output/*` from HDFS into `result.txt` on the host
11. Removes HDFS folders `/output` and `/books`

Once complete, you’ll see `result.txt` containing lines of the form:

```
<word>   (bookX.txt, line1,line2,...) (bookY.txt, line4,...) ...
```

---

## How Hadoop, MapReduce, and HDFS Splits Work

### HDFS & Block Storage

* **HDFS (Hadoop Distributed FileSystem)** breaks every large file into fixed‐size blocks (default 512 KB in our `hadoop.env`)
* Each block is replicated (default factor = 3) across different DataNodes to ensure fault tolerance
* In our cluster, uploading `bookX.txt` (≈25–30 MB) results in \~26 blocks of \~512 KB each
* The `fsck … -blocks -locations` command shows precisely which block IDs and on which DataNode instances each resides:

  ```text
  blk_1073741832_1008   len=524288   Live_repl=3   [datanode1, datanode2, datanode3]
  blk_1073741833_1009   len=524288   …
  … (all 26 blocks) …
  ```
* When you run a MapReduce job, **each block becomes one InputSplit**, handled by one Mapper task.

### MapReduce (WordCounter)

1. **Mapper** (`WordCounterMapper`):

    * **InputKey/InputValue**: receives `<LongWritable byteOffset, Text line>` for each line in its assigned block (via `FileInputFormat`)
    * **Task**: Tokenize each line into words (after stripping punctuation), ignore stopwords, and output `<“word;filename”, “lineNumberInThisSplit”>`
    * **Note**: `rowCount` is a counter local to that split; it resets on each new block. Therefore, line numbers are *split-relative*, not file-relative.

2. **Combiner** (`WordCounterCombiner`):

    * Receives all `<Text key = “word;filename”, Iterable<Text> values>` from the Mapper on that node
    * Aggregates all line‐number values into a single parenthesized string `(filename, line1,line2,…)`
    * Emits `<Text newKey = “word”, Text newValue = “(filename, line1,line2,…)”>`

3. **Reducer** (`WordCounterReducer`):

    * Receives `<Text key = “word”, Iterable<Text> values = (filenameA, …) (filenameB, …) …>`
    * Concatenates all file‐lists and writes out one final `<Text word, Text combinedValue>`
    * **Final output**:

      ```
      <word1>   (book2.txt, 123,456,789) (book5.txt, 10,50) ...
      <word2>   (book1.txt, 999) (book3.txt, 250,750) ...
      …  
      ```

### Why line numbers sometimes repeat

* Each Mapper sees only one split → it numbers lines starting at 1 for its split.
* If the same word appears at “line 3310” in split #1 (covering lines 1–3500 of book X) and also at “line 3310” in split #2 (covering lines 3501–7000 of book X), both Mappers emit `(bookX;3310)`.
* After combining, the Reducer shows both occurrences under the same “3310,” even though they refer to different absolute lines.
* **If you need absolute line numbers**, you must either (a) preprocess to prefix each line with its global line ID, or (b) omit line numbers altogether.

(Of course, you can still tell *which book* each word originated from via the Combiner’s `(filename, …)` grouping.)

---

## Docker & Cluster Architecture

1. **`hadoop-base` image**

    * Based on `debian:10` with OpenJDK 11 and Hadoop 3.4.1 installed under `/opt/hadoop-3.4.1`
    * Symlinks set up so that `$HADOOP_HOME=/opt/hadoop-3.4.1` and `$PATH` includes `$HADOOP_HOME/bin`
    * Contains no entrypoint; used as a base layer for all other Hadoop components.

2. **`hadoop-namenode`**

    * `FROM hadoop-base:latest`
    * Creates `/hadoop/dfs/name` (NameNode’s metadata directory)
    * Adds a small `run.sh` that starts `hdfs namenode` (via `hdfs --daemon start namenode`)
    * Exposes port 9870 (HTTP UI) and automatically registers with the same `$HADOOP_CONF_DIR` as the other containers.

3. **`hadoop-datanode`** (3 identical copies)

    * Also `FROM hadoop-base:latest`
    * Creates `/hadoop/dfs/data` (DataNode’s storage)
    * `run.sh` starts `hdfs datanode`
    * Each instance binds to a different Docker volume (`hadoop_datanode_1`, etc.) but shares the network so the NameNode can connect via DNS names (`datanode_1:9864`, etc.).

4. **`hadoop-resourcemanager`**

    * `FROM hadoop-base:latest`
    * Creates nothing special on disk, but `run.sh` starts `yarn resourcemanager`
    * Exposes port 8088 (YARN UI)
    * Depends on NameNode + DataNodes (via `SERVICE_PRECONDITION`).

5. **`hadoop-nodemanager`**

    * `FROM hadoop-base:latest`
    * `run.sh` starts `yarn nodemanager`
    * No exposed ports needed; it connects to ResourceManager on the shared network.

6. **`hadoop-wordcounter` / `submit`**

    * `FROM hadoop-base:latest`
    * Copies in:

        * `index.jar` (compiled WordCounter classes + stopwords.txt) → `/opt/hadoop/applications/app.jar`
        * `all_books.txt` → `/opt/hadoop/all_books.txt`
        * `run.sh` → `/run.sh` (chmod +x)
    * Environment variables:

      ```dockerfile
      ENV JAR_FILEPATH="/opt/hadoop/applications/app.jar"
      ENV CLASS_TO_RUN="WordCounter"
      ENV PARAMS="hdfs:///books /output"
      ```
    * `CMD ["/run.sh"]` ensures that, when run, it will:

        1. Format HDFS if needed
        2. (Re)create `/books`, upload the concatenated file, show splits
        3. Run the WordCounter job on `all_books.txt`
        4. Fetch `/output/*` to `result.txt` on the host
        5. Clean up HDFS

All containers communicate over the Docker network `hadoop-bby_default`. Topic ports:

* **HDFS NameNode**: 9000 (RPC), 9870 (UI)
* **DataNode**: 9864 (data + web)
* **YARN ResourceManager**: 8032 (RPC), 8088 (UI)
* **YARN NodeManager**: 8042 (UI), 8031 (RPC), etc. (internal only)

### How Containers Work Together

* **HDFS Components**:

    1. `hadoop-namenode` formats and starts the NameNode.
    2. Each of the 3 `hadoop-datanode` containers launches a DataNode which registers with the NameNode.
    3. NameNode’s web UI is reachable at `http://localhost:9870`.
    4. Once all DataNodes are up, `hdfs dfsadmin -report` inside any container will show 3 live DataNodes.

* **YARN Components**:

    1. `hadoop-resourcemanager` starts the ResourceManager, which allocates containers and tracks applications.
    2. `hadoop-nodemanager` starts a NodeManager, which actually launches and runs containerized map/reduce tasks.
    3. ResourceManager’s UI is at `http://localhost:8088`.

* **Job Submission**:

    * The `hadoop-wordcounter` image is run (via `docker run`) to submit a single MapReduce job.
    * Because `PARAMS="hdfs:///books /output"`, the driver in `WordCounter.java` uses:

      ```java
      FileInputFormat.addInputPath(job, new Path(args[0]));   // args[0] = hdfs:///books
      FileOutputFormat.setOutputPath(job, new Path(args[1])); // args[1] = /output
      ```
    * YARN allocates one mapper per HDFS block of `all_books.txt`. With a block size of 512 KB, \~25 MB / 512 KB ≈ 41 mappers.
    * Each mapper reads its split, tokenizes lines, emits `(word;filename, rowInSplit)`.
    * Combiners run locally on each node, then Reducers aggregate globally.

---

## Detailed Explanation: Hadoop Concepts

### HDFS (Hadoop Distributed FileSystem)

* Stores files in large, replicated blocks (512 KB each by default).
* One **NameNode** stores namespace metadata (file→block mappings, permissions, etc.).
* Multiple **DataNodes** store actual block data on local disks.
* A client writing a file:

    1. Contacts NameNode for block allocations
    2. Streams data to three different DataNodes (pipeline replication)
* A client reading a file:

    1. Contacts NameNode for block locations
    2. Reads directly from a local DataNode if nearby; else remote.

### MapReduce

* A distributed programming model for processing large datasets via two phases:

    * **Map phase**: Each mapper processes one input split (typically one HDFS block).
    * **Shuffle & Sort**: Hadoop automatically groups mapper outputs by key, sorts them, and sends them to reducers.
    * **Reduce phase**: Each reducer processes all values for a given key.

Our WordCounter example:

1. **Mapper**

    * Input: Key = byte offset, Value = one line of text
    * We override `map()` to:

        * Read the current filename via `((FileSplit) context.getInputSplit()).getPath().getName()`
        * Tokenize each line into clean words (lowercased, stopwords removed).
        * Output key = `word + ";" + filename`, value = `rowCountInThisSplit`
2. **Combiner**

    * Acts like a mini-reducer on each node, combining all `(word;filename, lineNumber)` pairs with the same key into `(word, "(filename, line1,line2,...)")`
    * Reduces network shuffle size.
3. **Reducer**

    * Input: `key = word`, values = a list of `(filename, lineList)` strings
    * Aggregates all file‐lists into one final record: `(word, "(bookA, …) (bookB, …) …")`

### Input Splits & Line Counting

* Each HDFS block becomes one **InputSplit**; `FileInputFormat` hands exactly one split to each Mapper.
* `TextInputFormat` ensures each mapper gets **whole lines**: it extends the split to the next newline boundary if needed.
* In `WordCounterMapper`, we track `rowCount++` for each line within the split, resetting `rowCount = 1` when the `filename` changes (i.e., new split).
* Because every split restarts `rowCount` at 1, the same “row number” may occur in multiple splits for the same file.

    * E.g. bookX’s absolute line 3500 might be `rowCount=3500` in split #1, and bookX’s absolute line 7000 might be `rowCount=3500` in split #2.
* If you need absolute line numbers, you must write a custom `InputFormat` or prepend a global line index first.

### YARN (Yet Another Resource Negotiator)

* Manages resources and job scheduling across the cluster.
* **ResourceManager**: Global authority that accepts job submissions, negotiates resources, and tracks application status.
* **NodeManager**: One per node—monitors container health, reports to RM, and launches map/reduce tasks inside containers.
* Each MapReduce job’s **ApplicationMaster** runs inside its own container; it negotiates with the RM for the needed containers (for mappers, reducers).
* In our small Docker cluster, there’s one NodeManager container, so all mappers/reducers run on that single NodeManager (suboptimal but works)

---

## Quick Troubleshooting

1. **Java compilation errors (unmappable character)**

    * Ensure `build.sh` in `wordcounter/` passes `-encoding UTF-8` to `javac`.
2. **HDFS formatting or permission issues**

    * If NameNode complains, try removing `hadoop_namenode:/hadoop/dfs/name` volume, then re-`docker-compose up --build`.
3. **Block count not matching expected**

    * Check `hdfs dfs -stat "%b" /books/all_books.txt` for blocksize (should be 512k).
    * Use `hdfs fsck /books/all_books.txt -files -blocks -locations` to verify block distribution.
4. **Job hangs in the map phase**

    * Look at YARN UI (`localhost:8088`), click on the application link, and check if mappers are all running or stuck.
    * Verify that DataNodes are healthy (`http://localhost:9870` → "Datanodes").

---

## Summary of Commands

```bash
# 1. Build all images
cd <project_root>
chmod +x build.sh
bash build.sh

# 2. Start Hadoop cluster
docker-compose up

# 3. Enter compiler container (optional debugging)
cd wordcounter
chmod +x init.sh
bash init.sh   # interactive shell; exit when done

# 4. Compile WordCounter
cd wordcounter
bash build.sh   # produces submit/index.jar

# 5. Run the WordCounter workflow
cd <project_root>
bash run.sh     # uploads books, shows splits, runs job, fetches result.txt

# 6. Inspect result
cat result.txt | less
```

At this point, `result.txt` holds your final WordCounter output.

**Enjoy exploring MapReduce on a miniature Docker‐based Hadoop cluster!**
