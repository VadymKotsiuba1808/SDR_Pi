---
name: comment-reviewer
description: Analyze source code documentation, optimize existing comments, and add meaningful "Why" explanations. Use when the user requests a code documentation audit, needs to clean up redundant comments, or wants to ensure compatibility with mkdocstrings and Google Style docstrings.
---

# Comment Reviewer

## Overview

This skill enables automated code quality assessment with a focus on documentation excellence. It identifies redundant "noise" comments, adds essential "Why" context for complex logic, and ensures all docstrings are compatible with `mkdocstrings` and modern documentation standards.

## Guidelines

### 1. Document the "Why", Not the "What"
- **Avoid Redundancy:** Do not add comments that merely repeat what the code is doing (e.g., skip `x = x + 1 # increment x`).
- **Explain Intent:** Focus on documenting the reasoning behind complex logic, business rules, mathematical formulas, and non-obvious workarounds.
- **Clarify Algorithms:** For multi-step procedures, provide high-level context on the goal of the algorithm.

### 2. Audit and Clean Existing Comments
- **Modify:** Update outdated, vague, or inaccurate comments.
- **Remove Noise:** Delete redundant comments, obvious explanations, and visual clutter like large blocks of commented-out code.
- **Professionalism:** Ensure all comments are concise, professional, and add value to the maintainer.

### 3. Language-Specific Standards
- **Python:**
  - Enforce **Google Style** docstrings for all public modules, classes, and functions.
  - Ensure compatibility with `mkdocstrings`.
  - Use `-> None` for empty returns and maintain strict PEP 484 typing.
- **TypeScript/JavaScript:**
  - Use valid **JSDoc/TSDoc** for exported symbols.
  - Document parameter types and return values clearly.

### 4. MkDocs Compatibility
- Use **Markdown** inside docstrings for lists, bold text, and code blocks.
- Utilize **Admonitions** for important notes:
  - `!!! note`: For general observations.
  - `!!! warning`: For critical side effects or constraints.
  - `!!! info`: For architectural context.

## Workflow

1. **Scan:** Analyze the target file to identify areas with high redundancy or missing context.
2. **Execute:** Apply modifications directly to the file using `replace` or `write_file`.
3. **Validate:** Ensure the code remains syntactically correct and the documentation is logically sound.
4. **Review:** Present the changes as a diff for the user to review in Git.

!!! warning
    Do NOT alter the functional execution logic of the code. This skill is strictly for documentation and maintainability improvements.
