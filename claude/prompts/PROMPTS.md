## Hypothesis generation

```
pls enable Ultrathink mode.
You are now operating as a world-class academic research assistant trained in deep reading, structured synthesis, and factual precision.

I study <user insertion>. these are recent papers that came from our lab
1. <paper 1>
<pubmed link>

2.<paper 2> 
<pubmed link> 

Your role: - Act as a scholarly collaborator for students, researchers, writers, and knowledge workers. - Provide clean, citation-rich summaries of academic papers. - Extract and compare key arguments across multiple sources. - Attribute quotes and ideas to authors and their institutions. - Write formal, cohesive research notes in academic tone and structure. Your rules: - Never hallucinate sources or facts. If something isn’t in the text, say “not available.” - Include author names, paper titles, and publication year when citing. - Use formal academic English — avoid casual tone. - Default citation format is APA unless user specifies otherwise. - Always structure your output with clear section headings: Abstract, Summary by Source, Comparative Analysis, and Synthesis & Takeaways. - End with a full bibliography. - Assume all inputs are from reputable academic sources unless told otherwise. When a user gives you a document, treat it like a scholarly text. When they give a topic, find structure and help them reason through it academically. You are not a chatbot. You are a rigorous academic co-author.

pls give me 5 high ambitious hypothesis that i can test with  alphagenome the google deepmind recent tool.  it should merit publication in nature or other high imapct  journals. 
preferably in human species. 
<user provides any gitbub links>

```


## working examples
```
“Lets think from First principles. Before providing a final answer, always ask yourself: "How would a person with great insight, wisdom, agency and capability answer?” 

“What's the most important question i should be asking, that I haven't yet?”
```
"
- "Give me a bulletproof breakdown."
- "What’s missing to make this bulletproof?"
- "Poke holes until there are no more to poke" is a favorite too.
It feels like a cheat code for maximum optimization before further breakdown
"

"I’ve found adding “Explain it like I’m wrong” forces the model to surface hidden edge cases—instant QA boost.

Have you seen certain phrasings perform differently on GPT vs Claude, or does the consultant-mode magic carry across models?"

"
“Return the script fully updated in verbatim”
"

```
i need to create a presentation to discuss with my supervior. pls create plan md file on how we can craft the story from all the analyis we did. The     │
│   goal is ti investigate if combination therapy with Quisinostat (QSTAT) and Mek inhibitor (CKi) induces suprisingly DNA methylation profile with          │
│   functional consequences. Pls properly label repeats and genic type of analysis to avoid confusion. 

```


## Fresh eyes review
---
Great, now I want you to carefully read over all of the new code you just wrote and other existing code you just modified with "fresh eyes," looking super carefully for any obvious bugs, errors, problems, issues, confusion, etc.
---


## Bioinformatics Code Review

```
Review all code written or modified in this session. Examine with fresh eyes,
checking each category below. For each issue found, state the file, line,
category, severity (critical/warning/note), and a fix.

### 1. Data Integrity
- Is raw data ever modified or overwritten?
- Are input/output paths distinct (no read-then-write to same file)?
- Are random seeds set for all stochastic operations?

### 2. Genome Build Safety
- Are contig names or sizes hardcoded anywhere?
- Does every genomic output file include the genome build in filename AND directory?
- If multiple builds are involved, is coordinate liftOver verified?
- Do reference paths come from databases_config.yaml (not hardcoded)?

### 3. Pipeline Correctness (Snakemake/Nextflow)
- Do rules with `singularity:` directives avoid `singularity exec` in the shell block?
- Are resource allocations (mem_mb, threads, GPU) reasonable for the task?
- Does a dry-run pass? Are all input/output declarations complete?
- Are sample names parsed safely (no whitespace, no special characters)?

### 4. Statistical Rigor
- Is multiple testing correction applied where needed (default: Bonferroni)?
- Are effect sizes reported alongside p-values?
- Are comparisons using the correct test for the data distribution?
- For genomic data: is the test appropriate for the coverage/sample size?

### 5. ONT-Specific (if applicable)
- Does the dorado model match the sequencing chemistry?
- Does modkit pileup --ref match the alignment reference?
- Are multi-run samples handled correctly (independent basecalling, merge after alignment)?

### 6. Reproducibility
- Are there hardcoded absolute paths?
- Are container/tool versions pinned or loaded from config?
- Would this code produce identical results if run tomorrow on a different node?

### 7. Forbidden Patterns
- Variable names: conditions, counts, results, sum, median, mean?
- Using --reason with snakemake?
- Missing author/date headers on scripts?

Report findings as a table:
| File | Line | Category | Severity | Issue | Fix |
|------|------|----------|----------|-------|-----|
```