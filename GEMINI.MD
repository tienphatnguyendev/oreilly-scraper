---

## Superpowers Workflow (Agentic Protocol)

The AI agent **MUST** follow this strict sequence of skills for all coding tasks. Deviations are forbidden.

### Core Loop

1.  **brainstorming**
    *   **Trigger**: Before writing any code. Corrects assumptions, refines requirements, and validates design.
    *   **Action**: Socratic dialogue (one question at a time).
    *   **Output**: A validated Design Document (`docs/plans/...-design.md`).
    *   **HARD GATE**: You **MUST** have a valid Linear Issue ID before proceeding.
        *   **Skill**: Use the **Linear MCP** tools via `.gemini/Skills/task-manager` to manage the ticket lifecycle (Status: In Progress, Assignee: Self).

2.  **using-git-worktrees**
    *   **Trigger**: After design approval & Linear Issue confirmation.
    *   **Action**: Create an isolated workspace on a new branch (`type/issueID-slug`).
    *   **Output**: A clean, isolated environment for the task.

3.  **writing-plans**
    *   **Trigger**: With an approved design and active worktree.
    *   **Action**: Break work into bite-sized tasks (2-5 mins execution time).
    *   **Output**: `implementation_plan.md` with exact file paths, code snippets, and verification steps.

4.  **executing-plans** OR **subagent-driven-development**
    *   **Trigger**: With a detailed plan.
    *   **Action**:
        *   **Subagent**: Dispatches fresh agents per task (Spec Compliance -> Code Quality).
        *   **Execution**: Batched execution with human checkpoints.
    *   **Methodology**: **test-driven-development** (Strict RED-GREEN-REFACTOR).
        *   Write failing test -> Watch it fail -> Write minimal code -> Watch it pass -> Refactor.

5.  **requesting-code-review**
    *   **Trigger**: Between major tasks or milestone completion.
    *   **Action**: Review implementation against the plan. Critical issues block progress.

6.  **finishing-a-development-branch**
    *   **Trigger**: When all tasks are complete and verified.
    *   **Action**: Verify all tests pass, present options (Merge/PR), and clean up the worktree.

### Key Protocols
-   **Debugging**: Follow `systematic-debugging` (Investigate -> Analyze -> Hypothesize -> Fix).
-   **Verification Gate**: No claim of "fixed" without terminal evidence.

---
