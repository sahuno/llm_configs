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
## Figure digest

Explain figure [0-9].[a-z]. what is the biomedical implication of this structure in health and research? how do we know this is correct? how did they generate this figure?

## Structured paper analysis

A longer companion to the `journal-club` skill's staged pipeline — use this when
you want one pass over a paper rather than the full stage sequence.

<PROMPT_BEGIN >
You are an rigorous [insert field] scientist with an eye and taste for rigorous scientific research procedures. 
Pls read and think clearly about this paper and present your findings with appropriate headings!
1.        What is the one thing this paper is solving? If you can fit it into one sentence, Yes, do it, otherwise be specific as possible. 
2.        What are the specific objectives that were met to solve this one thing? were there any opposing views, and were they addressed?
3.        Create a logical map of how the specific objectives interact, you can use ASCI figures. It’s fine if it’s not sequential and there multiple connections, show me all but indicate the best possible connection.
4.        What were the methods that were used to solve each objective? this could be an assay + statistical analysis, mathematical modeling with assay verification. Be concise and brief as much as possible. Identify the measurable outcome for each specific objective. it’s possible that in some cases a single specific objective could be multiple measurable outcomes. Please make sure to indicate such multi -outcomes.
5.        Were there any corrections or hard filtering decisions made in the methods? What’s the dynamic range hypothetically and where does that filtering cut-off falls and how does that affect the conclusions if I use a different cut-off based on percentile of dynamic range in 10% increment?
6.        For any mathematical or statistical modeling what are the variables used, what was the measurable outcome? What broader domain of the field does this approach fall? Indicate any multiple disciplinary approaches and how that impacted how the researchers concretely addressed the objectives.
7.        Which other methods could they have used based on previous and current trends in the field?
8.        What is missing in this paper? what questions does this conclusion open that could be tested ?
<PROMPT_END>



### crash course
"""
Before we do cell type annotation using the cluster markers, give me a crash course on concepts/methods (ie. scRNA-seq integrated with VDJ-seq). First principles, what are we     
tring to solve, why this tool is best option, understandig clones and metrics of clone analysis, how to think beyond the technology for biological          
  insights. and any other things you may think of. save this as a .md file so i can keep going back to it

"""
