# Bash tool

# Bash tool

The bash tool enables Claude to execute shell commands in a persistent bash session, allowing system operations, script execution, and command-line automation. Shell access is a foundational agent capability. On Terminal-Bench 2.0, a benchmark that evaluates real-world terminal tasks using shell-only validation, Claude shows strong performance gains with access to a persistent bash session.

## Overview

The bash tool provides Claude with:
- Persistent bash session that maintains state
- Ability to run any shell command
- Access to environment variables and working directory
- Command chaining and scripting capabilities

## Model compatibility

| Model | Tool Version |
|-------|-------------|
| Claude 4 models and Sonnet 3.7 | bash_20250124 |

## Use cases

- Development workflows: Run build commands, tests, and development tools
- System automation: Execute scripts, manage files, automate tasks
- Data processing: Process files, run analysis scripts, manage datasets
- Environment setup: Install packages, configure environments

## Quick start

Python example:
```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=1024,
    tools=[{"type": "bash_20250124", "name": "bash"}],
    messages=[
        {"role": "user", "content": "List all Python files in the current directory."}
    ],
)
```

## How it works

The bash tool maintains a persistent session:
1. Claude determines what command to run
2. You execute the command in a bash shell
3. Return the output (stdout and stderr) to Claude
4. Session state persists between commands (environment variables, working directory)

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| command | Yes* | The bash command to run |
| restart | No | Set to true to restart the bash session |

*Required unless using restart

## Example: Multi-step automation

Claude can chain commands to complete complex tasks:
1. Install package: pip install requests
2. Create script with cat heredoc
3. Run script: python fetch_joke.py

The session maintains state between commands, so files created in step 2 are available in step 3.

## Implement the bash tool

The bash tool is implemented as a schema-less tool. When using this tool, you don't need to provide an input schema; the schema is built into Claude's model and can't be modified.

Steps:
1. Set up a bash environment with subprocess.Popen
2. Handle command execution with stdin/stdout
3. Process Claude's tool calls - extract and execute commands
4. Implement safety measures - validate commands, block dangerous patterns

## Security

The bash tool provides direct system access. Essential safety measures:
- Running in isolated environments (Docker/VM)
- Implementing command filtering and allowlists
- Setting resource limits (CPU, memory, disk)
- Logging all executed commands

Key recommendations:
- Use ulimit to set resource constraints
- Filter dangerous commands (sudo, rm -rf, etc.)
- Run with minimal user permissions
- Monitor and log all command execution

## Pricing

The bash tool adds 245 input tokens to API calls. Additional tokens consumed by command outputs, error messages, and large file contents.

## Common patterns

### Development workflows
- Running tests: pytest && coverage report
- Building projects: npm install && npm run build
- Git operations: git status && git add . && git commit

### Git-based checkpointing
Git serves as a structured recovery mechanism in long-running agent workflows:
- Capture a baseline before agent work begins
- Commit per feature as rollback points
- Reconstruct state at session start via git log
- Revert on failure with git checkout

### File operations
- Processing data: wc -l *.csv && ls -lh *.csv
- Searching files: find . -name "*.py" | xargs grep "pattern"
- Creating backups: tar -czf backup.tar.gz ./data

### System tasks
- Checking resources: df -h && free -m
- Process management: ps aux | grep python
- Environment setup: export PATH

## Limitations

- No interactive commands: Cannot handle vim, less, or password prompts
- No GUI applications: Command-line only
- Session scope: Persists within conversation, lost between API calls
- Output limits: Large outputs may be truncated
- No streaming: Results returned after completion

## Combining with other tools

The bash tool is most powerful when combined with the text editor and other tools.