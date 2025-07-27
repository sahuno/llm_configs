# [MUST BE USED] Main Claude Configuration
## About 
    --- 
    Project Type:
    Session (New or continuation)
    Author (default): Samuel Ahuno (ekwame001@gmail.com) 
    ---
- Note to Claude: if the user does not fill this out, interview them to do so and then remove this line.
- ASK USER: What type of work this session is and whether its new or conituation of current project? 
Bioinformatics Ananlysis, software developments, Writing (Blogs/Journal), Maths (Applied or pure) (Fresh/conituation)


# Directory Structure of llm_configs
cli_coding_agents_setups: Coding Agents Configs
├── .claude
│   ├── CLAUDE.md: MUST READ if claude code
│   ├── hooks.yaml
│   ├── PROMPTS.md
│   ├── README.md
│   └── scripts:    Scripts for hooks & other important operations
└── .GEMINI
    └── GEMINI.md




## Working Directories
Scripts: ~/code/claude-scripts - Custom scripts and automation
Memory: ~/memories - Important information to remember (markdown)
Journal: ~/journal - Personal journal entries (markdown)
Ideas: ~/ideas - Creative ideas and thoughts (markdown)
To dos: ~/todos - Things to do, reminders, etc (markdown)
Projects: ~/projects - Active projects I'm working on (markdown)

## General Instructions & Projects
- You should search memories to see if there's an relevant information for my query, especially if you feel like you're missing context.
- Always either start a new project or continue an old project by writing a markdown file to ~/projects with an appropriate title. 
- As I do work, append important information to that file that you need to remember for the project.
- Do not use the following as variable names to avoid clashes with system variable names; [conditions, counts, results, sum, median, mean]
- In Genomic pipelines, Do not items like contig/chromosome names and sizes to ensure things don't break when we change codebase. Get contig names and sizes from the user supplied genome sizes file in the workflow.



### Visualization & Figures 
- Create 3 types of figues; png,pdf,svg for analysis place them under `png,pdf,svg` sub-directories.
- Figures should be of largest size possible
- Font type should always be Arial if font is available and of at least size 10. Headers should be Bold.
- Figure Axis should be legible, at least size 10
#### Figures for Nature magazine only
Use this for final figures when making manuscripts
- https://www.nature.com/nature/for-authors/formatting-guide
- Nature’s standard figure sizes are 90 mm (single column) and 180 mm (double column) and the full depth of the page is 170 mm.
- Use Arial or Helvetica font for all figures, with a size of 5-7pt when the figure is at final size (90mm or 180mm wide). 
