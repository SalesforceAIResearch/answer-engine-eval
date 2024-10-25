import json, argparse, csv, os, tqdm, requests, time, fcntl, itertools, threading, queue
from concurrent.futures import ThreadPoolExecutor
from utils_markdown import markdown_to_text
from utils_misc import extract_citations
from anyllm import generate_json
from bson import ObjectId

parser = argparse.ArgumentParser()
parser.add_argument('--fn', type=str, default="data/ans_eng_eval_0.1.json")
parser.add_argument('--num_workers', type=int, default=5)
args = parser.parse_args()

fn = args.fn

# 1. Scrape the sources
def scraper_jina_ai(url, bad_str="You've hit the rate limit"):
    text = bad_str
    while bad_str in text:
        response = requests.get("https://r.jina.ai/" + url)
        text = response.text
    if bad_str in text:
        print("Rate limit hit, waiting 10s")
        time.sleep(10)
    return text

with open(fn, 'r') as f:
    data = json.load(f)

todo_sourcing = []
for d in data:
    for s_idx in range(1,11):
        source_key = f"S{s_idx}"
        if len(d[source_key]) > 0 and (f"{source_key}_content" not in d or "You've hit the rate limit" in d[f"{source_key}_content"]):
            todo_sourcing.append((d, source_key))

if len(todo_sourcing) > 0:
    print(f"Need to source {len(todo_sourcing)} sources")
    for d, source_key in tqdm.tqdm(todo_sourcing):
        d[f"{source_key}_content"] = scraper_jina_ai(d[source_key])
        with open(fn, 'w') as f:
            json.dump(data, f, indent=2)

# 2. Extract the core/non-core statements
with open(fn, "r") as f:
    data = json.load(f)

with open("prompts/extract_core_statements.txt", "r") as f:
    prompt_core_statements = f.read()

statements_todos = []
for d in data:
    if "core_statements" not in d:
        statements_todos.append(d)

def process_statements_single_sample(d):
    prompt_core_statements_populated = prompt_core_statements.replace("[[QUESTION]]", d["Question"]).replace("[[ANSWER]]", d["Output"])
    
    response_core_statements = generate_json([{"role": "user", "content": prompt_core_statements_populated}], model="gpt-4o", max_tokens=2000, temperature=0.0, step="ansengineeval-core-statements")
    statements = response_core_statements["sentences"]
    final_statements = [state for state in statements if type(state) == dict and all(k in state for k in ["sentence", "core"])]
    for state in final_statements:
        state["id"] = str(ObjectId())
    d["core_statements"] = final_statements

if len(statements_todos) > 0:
    with ThreadPoolExecutor(max_workers=args.num_workers) as executor:
        list(tqdm.tqdm(executor.map(lambda d: process_statements_single_sample(d), statements_todos), total=len(statements_todos)))

# 2b. Extract, for each core statement, the citations
for d in data:
    for statement in d["core_statements"]:
        if "citations" not in statement:
            statement["citations"] = extract_citations(statement["sentence"])

with open(fn, "w") as f:
    json.dump(data, f, indent=2)

# 3. Populate the support score for all (core statements,source) pairs
with open("prompts/factual_support.txt", "r") as f:
    prompt_factual_support = f.read()

support_statement_fn = args.fn.replace(".json", "_support_results.jsonl")
done_ids = []
if os.path.exists(support_statement_fn):
    with open(support_statement_fn, "r") as f:
        for line in f:
            d = json.loads(line)
            if d["fn"] == fn:
                done_ids.append(d["verif_id"])

todos = []
for d in data:
    core_statements = [statement for statement in d["core_statements"] if statement["core"] == "1"]
    source_idxs = [i for i in range(1,11) if d[f"S{i}"] != "" and f"S{i}_content" in d]
    for source_idx, core_statement in itertools.product(source_idxs, core_statements):
        verif_id = f"{d['id']}_{source_idx}_{core_statement['id']}"
        if verif_id not in done_ids:
            todos.append((d, source_idx, core_statement))

# Create a queue to hold the support statements
support_queue = queue.Queue()

def worker_thread():
    while True:
        # Get the next support statement from the queue
        data = support_queue.get()

        # Write the support statement to the file
        with open(support_statement_fn, "a") as f:
            f.write(json.dumps(data) + "\n")

        # Indicate that the task is done
        support_queue.task_done()

# Start the worker threads
for _ in range(args.num_workers):
    t = threading.Thread(target=worker_thread)
    t.daemon = True
    t.start()

def process_single_support_sample(d, source_idx, core_statement):
    source_markdown = d[f"S{source_idx}_content"]
    source_text = markdown_to_text(source_markdown)
    prompt_factual_support_populated = prompt_factual_support.replace("[[DOCUMENT]]", source_text).replace("[[STATEMENT]]", core_statement["sentence"])
    response = generate_json([{"role": "user", "content": prompt_factual_support_populated}], model="gpt-4o", max_tokens=100, temperature=0.0, step="ansengineeval-support2")

    verif_id = f"{d['id']}_{source_idx}_{core_statement['id']}"

    # Add the support statement to the queue
    support_queue.put({"fn": fn, "verif_id": verif_id, "sample_id": d["id"], "source_idx": source_idx, "core_statement_id": core_statement["id"], "support": response["support"]})

if len(todos) > 0:
    with ThreadPoolExecutor(max_workers=args.num_workers) as executor:
        list(tqdm.tqdm(executor.map(lambda x: process_single_support_sample(*x), todos), total=len(todos)))

    # Wait for all tasks to be completed
    support_queue.join()

# 3b. Assign the supporting_sources to each core statement

with open(support_statement_fn, "r") as f:
    factual_support_entries = [json.loads(line) for line in f]

factual_support = {}
for entry in factual_support_entries:
    if entry["fn"] != fn:
        continue
    factual_support[(entry["sample_id"], entry["source_idx"], entry["core_statement_id"])] = entry["support"]

missing_verif_keys = 0

for d in data:
    statements = [statement for statement in d["core_statements"] if statement["core"] == "1"]
    source_idxs = [i for i in range(1,11) if d[f"S{i}"] != "" and f"S{i}_content" in d]
    for i, statement in enumerate(statements):
        statement["supporting_sources"] = []
        for j, source_idx in enumerate(source_idxs):
            verif_key = (d["id"], source_idx, statement["id"])
            if verif_key in factual_support:
                if factual_support[verif_key] in ["full"]:
                    statement["supporting_sources"].append(source_idx)
            else:
                missing_verif_keys += 1

with open(fn, "w") as f:
    json.dump(data, f, indent=2)
print(f"Missing {missing_verif_keys} verification keys")
