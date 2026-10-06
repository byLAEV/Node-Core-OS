# Development

## Supported development environment

Node Core OS is developed and tested **exclusively for GNU/Linux terminal environments**.

Development commands are terminal commands executed on GNU/Linux:

```bash
python3 main.py
```

The repository does not target graphical desktop environments, Windows, macOS, Android, or mobile application runtimes.

## Run

Python 3.10+ is recommended.

```bash
python3 main.py
```

## Test

```bash
python3 -m unittest discover -s tests
```

The official GitHub Actions workflow uses a fixed GNU/Linux runner and validates the same terminal-oriented Python test suite.

## Milestones

1. Runtime and configuration
2. Local storage
3. Kubo lifecycle and API adapter
4. Content/CID operations
5. Identity primitives
6. Evidence and reputation
7. Protocol runtime
8. Application lifecycle and permissions

The repository should keep the architectural target broad while only marking features as implemented when they are executable and tested.
