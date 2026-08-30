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

Superseded by **`/review`**, which does this against a structured checklist.
The bare version, if you want it without the checklist:

> Read over all of the new code you just wrote and the existing code you just
> modified with fresh eyes, looking carefully for bugs, errors, and confusion.


## Bioinformatics Code Review

Now a slash command: **`/review`** (bio-skills plugin). The 7-category checklist
that used to be pasted from here lives in
`plugins/bio-skills/commands/review.md`, plus a category for silent-failure
verification. Kept as a command rather than a prompt so it is discoverable and
cannot drift from a copy in this file.

## literature review
"Retrieve De Cecco et al. Nature 2019 (PMID 30728521) on LINE-1 and senescence. I want to understand: (1) what causal claim they make, (2) what experiments they used to establish that causality — specifically necessity and sufficiency — and (3) what they could not prove. Present it as a structured breakdown."

General rule: lead with the intellectual question, not the tool. Tools are means; the question is the goal. The more precisely you define what you want to understand, the less I have to guess — and the less I pad the response with things you didn't need.