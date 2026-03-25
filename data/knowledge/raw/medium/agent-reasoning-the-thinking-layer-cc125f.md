# Agent Reasoning: The Thinking Layer

**Author:** Oracle Developers Team  
**Published:** 2026-03-25T17:11:42.534Z  
**URL:** https://medium.com/oracledevs/agent-reasoning-the-thinking-layer-14e977fdc649  
**Tags:** ai-agent, artificial-intelligence, agentic-ai, large-language-models, ai  

---

## Summary

Featured

# Agent Reasoning: The Thinking Layer

## An open-source reasoning layer technology for any Ollama-served LLM

--

Listen

Share

More

### Key Takeaways

Agent Reasoning is an open-source reasoning layer that adds planning, deduction, and self-correction to any Ollama-served LLM (e.g., gemma3, llama3), via plug-and-play Python or a proxy server.Multiple proven reasoning strategies built-in (CoT, Self-Consistency, ToT, ReAct, Self-Reflection, Decomposition, Refinement) with a guided “s

---

## Full Content

Featured

# Agent Reasoning: The Thinking Layer

## An open-source reasoning layer technology for any Ollama-served LLM

--

Listen

Share

More

### Key Takeaways

Agent Reasoning is an open-source reasoning layer that adds planning, deduction, and self-correction to any Ollama-served LLM (e.g., gemma3, llama3), via plug-and-play Python or a proxy server.Multiple proven reasoning strategies built-in (CoT, Self-Consistency, ToT, ReAct, Self-Reflection, Decomposition, Refinement) with a guided “start simple” path.Practical tooling for teams: interactive CLI/TUI, Python API, and an Ollama-compatible gateway so existing apps gain reasoning without code changes.Clear benchmark guidance: CoT delivers the best average accuracy; ToT shines for multi-step logic; ReAct leads when tools (search, calculator) matter.

- Agent Reasoning is an open-source reasoning layer that adds planning, deduction, and self-correction to any Ollama-served LLM (e.g., gemma3, llama3), via plug-and-play Python or a proxy server.

- Multiple proven reasoning strategies built-in (CoT, Self-Consistency, ToT, ReAct, Self-Reflection, Decomposition, Refinement) with a guided “start simple” path.

- Practical tooling for teams: interactive CLI/TUI, Python API, and an Ollama-compatible gateway so existing apps gain reasoning without code changes.

- Clear benchmark guidance: CoT delivers the best average accuracy; ToT shines for multi-step logic; ReAct leads when tools (search, calculator) matter.

## Implementing Cognitive Problem-Solving in Open Source Models

From Nacho Martinez, Data Scientist Advocate at Oracle (and author of theA2A-based Multi-Agent RAG system) comes an open-source reasoning layer that can enable any open-source Large Language Model (LLM) such as gemma3 or llama3 to perform complex planning, logical deduction and self-correction.

The layer wraps these models in a cognitive architecture built based on key research papers (CoT, ToT and ReAct).

We call this Agent Reasoning, and it is availableopen-source in this GitHub repository, alongside aJupyter notebook.

### Features of Agent Reasoning

Plug & Play: Use via Python Class or as a Network Proxy.Model Agnostic: Works with any model served by Ollama.Chain-of-Thought (CoT)&Self-Consistency: Implements Majority Voting (k samples) with temperature sampling.Tree of Thoughts (ToT): BFS strategy with robust heuristic scoring and pruning.ReAct (Reason + Act): Real-time tool usage (Web Searchvia scraping, Wikipedia API, Calculator) with fallback/mock capabilities. External grounding implemented.Self-Reflection: Dynamic multi-turn Refinement Loop (Draft -> Critique -> Improve).Decomposition & Least-to-Most: Planning and sub-task execution.Refinement Loop: Score-based iterative improvement (Generator → Critic → Refiner) until quality threshold met.Complex Refinement Pipeline: 5-stage optimization (Technical Accuracy → Structure → Depth → Examples → Polish).

- Plug & Play: Use via Python Class or as a Network Proxy.

- Model Agnostic: Works with any model served by Ollama.

- Chain-of-Thought (CoT)&Self-Consistency: Implements Majority Voting (k samples) with temperature sampling.

- Tree of Thoughts (ToT): BFS strategy with robust heuristic scoring and pruning.

- ReAct (Reason + Act): Real-time tool usage (Web Searchvia scraping, Wikipedia API, Calculator) with fallback/mock capabilities. External grounding implemented.

- Self-Reflection: Dynamic multi-turn Refinement Loop (Draft -> Critique -> Improve).

- Decomposition & Least-to-Most: Planning and sub-task execution.

- Refinement Loop: Score-based iterative improvement (Generator → Critic → Refiner) until quality threshold met.

- Complex Refinement Pipeline: 5-stage optimization (Technical Accuracy → Structure → Depth → Examples → Polish).

## Interactive Jupyter Notebook

We prepared aninteractive Jupyter notebookto demonstrate the capabilities of agent reasoning.

This is a comprehensive demo covering all reasoning strategies (CoT, ToT, ReAct, Self-Reflection) with benchmarks and comparisons.

## Architectures in Detail

For most users, start with Chain-of-Thought (CoT) — it has the best average accuracy and lowest latency cost. Use Self-Consistency when correctness is critical and you can afford 3–5× more inference time. Avoid ToT for knowledge-retrieval tasks (it underperforms baseline on MMLU) and reserve it for multi-step planning or logic puzzles.

## Accuracy Benchmarks

You can evaluate reasoning strategies against standard NLP datasets to measure accuracy improvements. The benchmark system includes embedded question sets from 4 standard datasets.

To run an accuracy benchmark:

Or using the Python API:

Charts are auto-generated after each run and are saved to`benchmarks/charts/`.

The following are the results of a full evaluation across 11 strategies:

### Key findings:

CoTachieves the highest average accuracy (87.0%), outperforming Standard on GSM8K (+6.6%) and MMLU (+6.7%)Self-Consistencyties CoT on MMLU (96.7%) and GSM8K (76.7%) through majority votingToTexcels on GSM8K math (76.7%, +10% over Standard) through branch explorationReActachieves the highest ARC-Challenge score (96.0%) via tool-augmented reasoning

- CoTachieves the highest average accuracy (87.0%), outperforming Standard on GSM8K (+6.6%) and MMLU (+6.7%)

- Self-Consistencyties CoT on MMLU (96.7%) and GSM8K (76.7%) through majority voting

- ToTexcels on GSM8K math (76.7%, +10% over Standard) through branch exploration

- ReActachieves the highest ARC-Challenge score (96.0%) via tool-augmented reasoning

### Accuracy Statistics

This is the accuracy heat map per-strategy:

This is the average accuracy by strategy:

### Benchmarks

Benchmarks charts are auto-generated after every benchmark run.

For a complete listing of sample output benchmarks (response latency, throughput etc.) please refer to theAgent Reasoning GitHub repository.

## Installation

You can install Agent Reasoning in a few different ways:

### Quick Start (3 commands)

```rust
uv sync && ollama pull gemma3:270m && uv run agent-reasoning
```

### One-command, single-step install

```rust
curl -fsSL https://raw.githubusercontent.com/jasperan/agent-reasoning/main/install.sh | bash
```

You can also install agent-reasoning using either PyPi or directly from source:

### Using PyPi

### From Source usinguv

### Development

## Configuring the large language model (LLM)

We useOllamaas an example for this procedure.

Ollama must be running locally, or you can connect to a remote Ollama instance.

```rust
ollama pull gemma3:270m    # Tiny model for quick testing
ollama pull gemma3:latest  # Full model for quality results
```

## Configuring the remote Ollama endpoint

If you don’t have Ollama installed locally, you can connect to a remote Ollama instance. Configuration is stored in`config.yaml`in the root directory of the repository.

### Option 1: Interactive CLI configuration

```rust
agent-reasoning
# Select "Configure Endpoint" from the menu
```

### Option 2: Server CLI Argument

```rust
agent-reasoning-server --ollama-host http://192.168.1.100:11434
```

### Option 3: Direct Config File

Copy the example config and edit it:

```rust
cp config.yaml.example config.yamlcp config.yaml.example config.yaml
```

Or create`config.yaml`in the project root:

```rust
ollama:
  host: http://192.168.1.100:11434
```

### Option 4: Python API

## Usage

### 1. Interactive CLI

Use the rich CLI to access all agents, comparisons and benchmarks.

Timing Metrics: Every response shows TTFT, total time, tokens/secSession History: All chats auto-saved to data/sessions/ with export to markdownHead-to-Head: Compare any two strategies side-by-side in parallelAgent Info: Built-in strategy guide with descriptions and use casesBenchmark Charts: Auto-generate PNG visualizations of benchmark results

- Timing Metrics: Every response shows TTFT, total time, tokens/sec

- Session History: All chats auto-saved to data/sessions/ with export to markdown

- Head-to-Head: Compare any two strategies side-by-side in parallel

- Agent Info: Built-in strategy guide with descriptions and use cases

- Benchmark Charts: Auto-generate PNG visualizations of benchmark results

Setup

```rust
# If installed via pip:
agent-reasoning
# Or from source:
python agent_cli.py
```

Shortcuts

The CLI also provides several useful shortcuts:

Interactive experience

### 2. Terminal UI (TUI)

You can also use a Go-based terminal interface with a split-panel layout and arena grid view.

Split layout: agent sidebar + chat panelArena mode: 3×3 grid showing all agents running in parallelReal-time streaming with cancellation support

- Split layout: agent sidebar + chat panel

- Arena mode: 3×3 grid showing all agents running in parallel

- Real-time streaming with cancellation support

The TUI automatically starts the reasoning server on launch. Requires Go 1.18+.

Keybindings for TUI

Chat View

The default chat view is a split-pane layout with a 16-agent sidebar, chat panel with live streaming, and a metrics bar showing TTFT, tokens/sec, and token count in real-time.

Press`v`to togglestructured visualization mode. Instead of raw text, you see the agent’s reasoning process rendered live: tree diagrams for ToT, swimlanes for ReAct, vote tallies for Consistency, score gauges for Refinement, and more.

Press`p`to open thehyperparameter tuner. Adjust ToT width/depth, Consistency samples, Refinement score thresholds, and other agent parameters before running a query.

Press`?`to invoke thestrategy advisor. The MetaReasoningAgent analyzes your query and recommends the best strategy.

Modes of interaction

Arena Modeprompts all 16 agents to race simultaneously on the same query displayed using a 4×4 grid; a leaderboard bar updates as each agent finishes:

- Arena Modeprompts all 16 agents to race simultaneously on the same query displayed using a 4×4 grid; a leaderboard bar updates as each agent finishes:

Head-to-Head Duelprompts two agents to compete 1–1 on the same query.

There are plenty of other features to try, such as:

theStep-Through Debuggerwhich enables pausing the agent between LLM calls and inspecting intermediate statetheBenchmark Dashboardwhich reads existing JSON benchmark filestheSession Browserwhich enables search and re-running of past conversations, with filtering optionstheAgent Guide, which contains reference cards for all 16 agents, covering best-for, parameters, trade-offs, and research reference. Pressing Enter on any card initiates a chat with the agent.

- theStep-Through Debuggerwhich enables pausing the agent between LLM calls and inspecting intermediate state

- theBenchmark Dashboardwhich reads existing JSON benchmark files

- theSession Browserwhich enables search and re-running of past conversations, with filtering options

- theAgent Guide, which contains reference cards for all 16 agents, covering best-for, parameters, trade-offs, and research reference. Pressing Enter on any card initiates a chat with the agent.

### 3. Python API (for developers)

Use the ReasoningInterceptor as a drop-in replacement for your LLM client:

Using agents directly:

Using refinement agents for quality control:

### 4. Reasoning Gateway Server

Run a proxy server that impersonates Ollama. This allows any Ollama-compatible app, such as LangChain or Web UIs, to gain reasoning capabilities without any code changes whatsoever.

Then configure your app:

Base URL:http://localhost:8080Model:gemma3:270m+cot(or+tot, +react,etc.)

- Base URL:http://localhost:8080

- Model:gemma3:270m+cot(or+tot, +react,etc.)

API Endpoints

## Troubleshooting

Model Not Found: Ensure you have pulled the base model (ollama pull gemma3:270m).Timeout / Slow: ToT and Self-Reflection make multiple calls to the LLM. With larger models (Llama3 70b), this can take time.Hallucinations: The default demo uses gemma3:270m which is extremely small and prone to logic errors. Switch to gemma2:9b or llama3 for robust results.

- Model Not Found: Ensure you have pulled the base model (ollama pull gemma3:270m).

- Timeout / Slow: ToT and Self-Reflection make multiple calls to the LLM. With larger models (Llama3 70b), this can take time.

- Hallucinations: The default demo uses gemma3:270m which is extremely small and prone to logic errors. Switch to gemma2:9b or llama3 for robust results.

## Extending the system further

You can add additional reasoning strategies.

Create a class insrc/agent_reasoning/agents/inheriting from BaseAgent.Implement thestream(self, query)method.Register it inAGENT_MAPinsrc/agent_reasoning/interceptor.py.

- Create a class insrc/agent_reasoning/agents/inheriting from BaseAgent.

- Implement thestream(self, query)method.

- Register it inAGENT_MAPinsrc/agent_reasoning/interceptor.py.

## Conclusion

Thank you for reading, and we look forward to seeing what you build using Agent Reasoning!

Agent Reasoning GitHub repositoryJupyter NotebookOracle AI Developer Hub

- Agent Reasoning GitHub repository

- Jupyter Notebook

- Oracle AI Developer Hub

## Frequently Asked Questions (FAQs)

### When should I use each strategy?

Start with Chain-of-Thought for best accuracy/latency trade-off; use Self-Consistency when correctness is critical; reserve Tree of Thoughts for complex multi-step reasoning; pick ReAct for fact-checks or calculations.

### Do I need a specific model?

No. It’s model-agnostic for any model served by Ollama. Quality improves with larger models (e.g., gemma2:9b, llama3 vs tiny 270m).

### How hard is setup?

Three-command quick start, one-line install script, and ready-to-run demos in a Jupyter notebook. A proxy lets existing Ollama apps adopt reasoning by just changing the base URL/model name.

### How do I evaluate results?

Built-in benchmarks (GSM8K, MMLU, ARC-Challenge, HellaSwag) auto-generate charts, with side-by-side strategy comparisons and session histories for review.
