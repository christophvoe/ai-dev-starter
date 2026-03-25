# Maximum-Efficiency Coding Setup

**Author:** Eivind Kjosbakken  
**Published:** 2026-02-18T00:01:01.685Z  
**URL:** https://medium.com/towards-artificial-intelligence/maximum-efficiency-coding-setup-c7fee8176e7e  
**Tags:**  

---

## Summary

Member-only story

# Maximum-Efficiency Coding Setup

## Learn how to be a more efficient programmer

--

Listen

Share

More

There are many different coding setups people use for programming. In this article, I’ll take you through my personal coding setup and the tools and applications that I use to achieve maximum efficiency when programming.

This is a setup that I’ve created through extensive testing and experimenting myself through trial and error. While testing, I’ve attempted to use seve

---

## Full Content

Member-only story

# Maximum-Efficiency Coding Setup

## Learn how to be a more efficient programmer

--

Listen

Share

More

There are many different coding setups people use for programming. In this article, I’ll take you through my personal coding setup and the tools and applications that I use to achieve maximum efficiency when programming.

This is a setup that I’ve created through extensive testing and experimenting myself through trial and error. While testing, I’ve attempted to use several different applications for programming, and each of them has advantages in different settings.

I’ll take you through the current coding setup I have, though it is, of course, subject to change soon in the future with the rapid advancement of LLM technology.

I’m not sponsored by any of the tooling mentioned in this video, and it’s simply the tooling I use on a day-to-day basis as a programmer.

## Why optimize your coding setup

As a programmer, your coding setup is one of the most important elements you can optimize. This is where you spend most of your time solving different problems. Because of all the time you spend with your coding setup, you should spend time making sure it’s optimized for your personal workflows.

Personally, I always look for opportunities to make my setup more efficient. For a long period of time, I used Cursor on a daily basis as the platform from which I did all my coding. A few weeks ago, I suddenly shifted to using purely Claude Code through Warp, which essentially makes up the majority of my coding setup.

The switch from using Cursor to using Claude Code through Warp was one of the most significant productivity increases I’ve experienced since I first noticed how efficient agents could program for me. Warp + Claude Code has helped me massively in my daily work as a data scientist in a startup working on document AI.

## Walking through my coding setup

In this section, I’ll walk you through the different tooling, techniques, and approaches I use to optimize my coding setup. I’ll cover the applications I use on a day-to-day basis, but also how I utilize and get the most out of these applications and other important tricks I use to make my coding as effective as possible.

All of the tips I’ll cover in this section have a significant impact on my productivity as an engineer.

## Tooling

First of all, I want to cover the tooling I use. I use Claude Code and Warp for almost all of my coding. If I want to check some production logs or if I want to fix a bug or implement a new feature, I’ll essentially always use Claude Code in Warp.

Within Warp, I have the following setup. I have each tab in Warp as a separate folder I’m working in. So if I’m working in folder A, that’s my first tab in Warp. And if I’m working in folder B, that’s my second tab. Now, I typically find myself having several agents running within the same folder. In this case, I make a split pane using CMD + D in Warp, so my tab is split into multiple panes. Depending on the task I’m working on, I could have up to five agents working within the same repository. And then I have different repositories in different Warp tabs.

I want to note one exception where I use Cursor instead of Claude Code: When I need full control of the code. For example, if the feature is of critical importance or a part of critical infrastructure. Also, typically when I run important migration scripts or backfilling scripts, I’ll also do it in Cursor because this gives me more control of the code. I can also run the code myself through interactive windows with Python.

## Git worktrees

As I mentioned in my previous section, I often find myself running multiple agents within the same repository. If you have multiple agents updating files at the same time in the same repository, you’ll run into problems with agents colliding with each other. To solve this problem, you can use Git Worktrees.

Git worktrees are essentially copies of Git repositories that you can make to have agents run completely separate from each other. So whenever I spin up a new agent, I tell it to start a new git worktree for what it’s working on. and that agent can now work completely separately from all other agents working in the same repository.

This is an essential feature if you want to work with parallel agents in Claude Code (which is one of the major benefits of working with Claude Code). Thus, you should definitely be utilizing Git Worktrees in your day-to-day programming with parallel agents.

## Slash commands

Slash commands are another very powerful feature. Slah commands are essentially stored prompts, so you can quickly access a prompt that you have stored on a previous occasion. For example, if you have a very repetitive prompt, you should store it as a slash command. Some examples of this are:

Create PR from feature branch to devCreate release PR (dev -> main)Simplify this code (for example, with the Claude Code simplify command)

- Create PR from feature branch to dev

- Create release PR (dev -> main)

- Simplify this code (for example, with the Claude Code simplify command)

Slash commands are incredibly powerful, and I’ve covered them in one of my previous articles. The benefit of slash commands is twofold. First of all, you save time by not having to write out the prompt every time. So instead of having to write out a long prompt, telling the model that it needs to:

Pull the latest dev branch and rebase on top of itRun precommit checksA good PR descriptionMake a pull request from a feature branch to dev

- Pull the latest dev branch and rebase on top of it

- Run precommit checks

- A good PR description

- Make a pull request from a feature branch to dev

Instead of having to write out all of this, you can simply store this prompt in a slash command and access the prompt instantly.

The second advantage is that you get to be more consistent when writing your prompts. For example, when creating pull requests to dev, as I mentioned, you would have to run a series of checks (pull latest dev branch, rebase, run precommit checks, …). If you write this out every time, you risk forgetting parts of the prompt. This is not a problem if you use slash commands, however, because you’ll always be utilizing the same prompt, and you’ll be more consistent.

> Slash commands make you both faster and more consistent

Slash commands make you both faster and more consistent

## Low threshold to fire off agents

Another topic I want to cover is that you should have a super low threshold to fire off agents to perform tasks for you. Whenever you can think of a new task or get a new problem you have to solve, you should just fire off an agent. For example, if I notice a button that is misaligned, some text in my application that has to be updated, or translations that have to be updated. I simply fire off a new agent, let it run fully autonomously, and create a pull request for me.

The main point is that you should have a low threshold to fire off agents because it’s so cheap to run and costs you so little time. The cost of firing a new agent is essentially spending time writing out a good prompt and, in many cases, answering a few questions the agents have for you to properly understand the task you gave them.

There are now many tools out there that offer a lot of token usage for a relatively low price. For example, I’m using the $200 Claude Code subscription, which is a set amount per month, and I’ve never run into rate limits. This means I can fire off as many agents as I can without additional cost.

## Utilize the best models

Another tip I have might sound very obvious, but I always recommend using the best models whenever you work with programming. The reason for this is that in the long term, this saves you both time and money.

Yes, the best models are typically the most expensive models per token and are also the slowest models. However, it turns out that if you use cheaper models, they will more often make mistakes, which takes additional time for you to fix and iterate on, which again makes the model utilize even more tokens. Thus, in the end, it often turns out that using a cheaper, smaller model actually turns out to be more expensive and time-consuming.

You should therefore be utilizing the frontier models such as Gemini 3 Pro, Claude 4.5 Opus, and GPT 5.2 Codex. There are also some up-and-coming open source models performing well on the coding benchmarks, though I haven’t achieved the same success with open source models as I’ve achieved with frontier closed source models.

## Conclusion

In this article, I’ve covered how to have a maximum efficiency coding setup. I’ve discussed the coding setup I use on a day-to-day basis, where I use the Warp terminal with Claude Code. Furthermore, I use specific techniques such as organizing Warp with split panes and tabs by the folder I’m working on. I’m also making sure to always use the latest and best coding models. I believe spending time optimizing your coding setup is a very good use of time. As a programmer, your coding setup is one of the things you spend the most time with, and if you can make that a few percentage points more efficient, it will likely pay off in the long run.

👉 My Free Resources

💌Substack

🚀10x Your Engineering with LLMs (Free 3-Day Email Course)

📚Get my free Vision Language Models ebook

💻My webinar on Vision Language Models

👉 Find me on socials:

🧑‍💻Get in touch

🔗LinkedIn

🐦X / Twitter

✍️Medium
