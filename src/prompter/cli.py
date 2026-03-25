"""CLI entry point for prompter — optimize, evaluate, history commands."""
from __future__ import annotations

import asyncio
import difflib
import logging
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from prompter.config.agent_config import AgentConfig
from prompter.eval.evaluator import EvalReport, Evaluator
from prompter.eval.test_suite import TestSuite
from prompter.history.store import HistoryStore
from prompter.optimizer import Optimizer, OptimizerConfig
from prompter.runner.agent_runner import AgentRunner

logger = logging.getLogger(__name__)
console = Console()

LOGO = r"""
                              _
  _ __  _ __ ___  _ __ ___  _ __ | |_ ___ _ __
 | '_ \| '__/ _ \| '_ ` _ \| '_ \| __/ _ \ '__|
 | |_) | | | (_) | | | | | | |_) | ||  __/ |
 | .__/|_|  \___/|_| |_| |_| .__/ \__\___|_|
 |_|                        |_|
"""


def _create_llm(model: str, base_url: str, api_key: str | None) -> Any:
    """Create an LLM adapter based on model/url."""
    from prompter.llm.openai_compat import OpenAICompatAdapter

    return OpenAICompatAdapter(
        model=model,
        base_url=base_url,
        api_key=api_key or "",
    )


def _parse_tiers(tiers_str: str | None) -> dict[str, dict[str, str]] | None:
    """Parse --tiers CLI option.

    Format: 'name:provider:model,name:provider:model'
    Example: 'local:ollama:llama3.2,cheap:openai:gpt-4o-mini'

    Returns:
        Dict mapping tier name to {provider, model}, or None if empty.

    Raises:
        ValueError: If format is invalid.
    """
    if not tiers_str:
        return None

    result: dict[str, dict[str, str]] = {}
    for entry in tiers_str.split(","):
        parts = entry.strip().split(":")
        if len(parts) != 3:
            raise ValueError(
                f"Invalid tier format: '{entry.strip()}'. "
                "Expected 'name:provider:model' (e.g., 'local:ollama:llama3.2')"
            )
        name, provider, model = parts
        result[name.strip()] = {
            "provider": provider.strip(),
            "model": model.strip(),
        }

    return result


def _sparkline(values: list[float]) -> str:
    """Generate a Unicode sparkline from a list of values."""
    if not values:
        return ""
    blocks = " \u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"
    mn, mx = min(values), max(values)
    spread = mx - mn if mx > mn else 1.0
    return "".join(
        blocks[min(len(blocks) - 1, int((v - mn) / spread * (len(blocks) - 1)))]
        for v in values
    )


def _prompt_diff(before: str, after: str) -> str:
    """Generate a colored diff of prompt changes."""
    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile="before",
        tofile="after",
    )
    lines = []
    for line in diff:
        if line.startswith("+") and not line.startswith("+++"):
            lines.append(f"[green]{line.rstrip()}[/green]")
        elif line.startswith("-") and not line.startswith("---"):
            lines.append(f"[red]{line.rstrip()}[/red]")
        else:
            lines.append(line.rstrip())
    return "\n".join(lines)


@click.group()
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
def main(verbose: bool = False) -> None:
    """prompter — Autoresearch-style optimizer for LLM agent systems."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )


@main.command()
@click.argument("agent_dir", type=click.Path(exists=True))
@click.argument("test_suite", type=click.Path(exists=True))
@click.option("--max-iters", default=20, help="Maximum optimization iterations")
@click.option("--target-score", default=1.0, type=float, help="Target score to reach")
@click.option("--model", default="gpt-4o-mini", help="LLM model to use")
@click.option("--base-url", default="https://api.openai.com/v1", help="LLM API base URL")
@click.option("--api-key", envvar="OPENAI_API_KEY", help="API key")
@click.option("--n-runs", default=3, type=int, help="Eval runs per iteration for variance")
@click.option("--output-dir", default=None, type=click.Path(), help="Save optimized config here")
@click.option("--verbose", is_flag=True, help="Show detailed mutation info")
@click.option(
    "--variance-modes",
    default=None,
    help="Comma-separated variance modes: run,order,paraphrase",
)
@click.option(
    "--tiers",
    default=None,
    help="Multi-tier escalation: name:provider:model,... "
    "(e.g., local:ollama:llama3.2,cheap:openai:gpt-4o-mini)",
)
@click.option(
    "--config",
    "config_file",
    default=None,
    type=click.Path(exists=True),
    help="Load configuration from a prompter.yaml file",
)
def optimize(
    agent_dir: str,
    test_suite: str,
    max_iters: int,
    target_score: float,
    model: str,
    base_url: str,
    api_key: str | None,
    n_runs: int,
    output_dir: str | None,
    verbose: bool,
    variance_modes: str | None,
    tiers: str | None,
    config_file: str | None,
) -> None:
    """Optimize an agent config against a test suite."""
    # Show logo
    console.print(f"[bold cyan]{LOGO}[/bold cyan]")

    # Parse variance modes
    parsed_variance_modes: list[str] | None = None
    if variance_modes:
        parsed_variance_modes = [m.strip() for m in variance_modes.split(",")]

    # Load config file if provided
    if config_file:
        from prompter.config.config_file import load_config, merge_cli_overrides

        file_config = load_config(config_file)
        file_config = merge_cli_overrides(
            file_config,
            max_iters=max_iters if max_iters != 20 else None,
            target_score=target_score if target_score != 1.0 else None,
            model=model if model != "gpt-4o-mini" else None,
            base_url=base_url if base_url != "https://api.openai.com/v1" else None,
            n_runs=n_runs if n_runs != 3 else None,
            variance_modes=parsed_variance_modes,
        )
        # Use config file values as defaults
        max_iters = file_config.optimizer.max_iterations
        target_score = file_config.optimizer.target_score
        n_runs = file_config.optimizer.n_eval_runs
        if file_config.llm:
            model = file_config.llm.model
            base_url = file_config.llm.base_url
        if parsed_variance_modes is None:
            parsed_variance_modes = file_config.optimizer.variance_modes

    config = AgentConfig.load(agent_dir)
    suite = TestSuite.load(test_suite)
    llm = _create_llm(model, base_url, api_key)

    output_path = Path(output_dir) if output_dir else Path(agent_dir) / "optimized"
    history_path = output_path / "history.jsonl"
    snapshots_dir = output_path / "snapshots"

    opt_config = OptimizerConfig(
        max_iterations=max_iters,
        target_score=target_score,
        n_eval_runs=n_runs,
        compute_ci=n_runs > 1,
        snapshots_dir=snapshots_dir,
        variance_modes=parsed_variance_modes or ["run"],
    )

    # Parse tier configuration
    parsed_tiers = _parse_tiers(tiers)

    optimizer = Optimizer(
        config=config,
        test_suite=suite,
        llm=llm,
        opt_config=opt_config,
        history_path=history_path,
    )

    console.print("[bold]Starting optimization...[/bold]")
    console.print(f"  Agent: {agent_dir}")
    console.print(f"  Tests: {test_suite} ({len(suite.tests)} cases)")
    console.print(f"  Model: {model}")
    console.print(f"  Max iterations: {max_iters}")
    console.print(f"  Target score: {target_score}")
    if parsed_variance_modes:
        console.print(f"  Variance modes: {', '.join(parsed_variance_modes)}")
    if parsed_tiers:
        console.print(f"  Escalation tiers: {', '.join(parsed_tiers.keys())}")
    console.print()

    result = asyncio.run(optimizer.run())

    # Display results
    _print_optimization_result(result, config, output_path)

    # Save optimized config
    output_path.mkdir(parents=True, exist_ok=True)
    result.best_config.save(output_path / "agent")
    console.print(f"\n[green]Optimized config saved to {output_path / 'agent'}[/green]")


@main.command()
@click.argument("agent_dir", type=click.Path(exists=True))
@click.argument("test_suite", type=click.Path(exists=True))
@click.option("--model", default="gpt-4o-mini", help="LLM model to use")
@click.option("--base-url", default="https://api.openai.com/v1", help="LLM API base URL")
@click.option("--api-key", envvar="OPENAI_API_KEY", help="API key")
@click.option("--n-runs", default=1, type=int, help="Number of eval runs")
@click.option("--verbose", is_flag=True, help="Show per-test details")
def evaluate(
    agent_dir: str,
    test_suite: str,
    model: str,
    base_url: str,
    api_key: str | None,
    n_runs: int,
    verbose: bool,
) -> None:
    """Evaluate an agent config against a test suite without optimizing."""
    config = AgentConfig.load(agent_dir)
    suite = TestSuite.load(test_suite)
    llm = _create_llm(model, base_url, api_key)

    evaluator = Evaluator(n_runs=n_runs, compute_variance=n_runs > 1)
    runner = AgentRunner(config=config, llm=llm)
    agent_fn = runner.as_agent_fn()

    console.print("[bold]Evaluating...[/bold]")
    report = asyncio.run(evaluator.evaluate(agent_fn, suite, config.config_hash()))

    _print_eval_report(report, verbose)


@main.command()
@click.argument("history_file", type=click.Path(exists=True))
def history(history_file: str) -> None:
    """Print optimization history summary."""
    store = HistoryStore(history_file)
    records = store.get_all()

    if not records:
        console.print("[yellow]No history records found.[/yellow]")
        return

    table = Table(title="Optimization History")
    table.add_column("Iter", justify="right", style="cyan")
    table.add_column("Mutation", style="magenta")
    table.add_column("Score Before", justify="right")
    table.add_column("Score After", justify="right")
    table.add_column("Delta", justify="right")
    table.add_column("Status", style="bold")

    for record in records:
        delta = record.delta
        delta_str = f"{delta:+.4f}" if record.mutation_type else "-"
        status = "[green]ACCEPTED[/green]" if record.accepted else "[red]REJECTED[/red]"
        mutation = record.mutation_type or "baseline"

        table.add_row(
            str(record.iteration),
            mutation,
            f"{record.score_before:.4f}",
            f"{record.score_after:.4f}",
            delta_str,
            status,
        )

    console.print(table)

    best = store.get_best()
    if best:
        console.print(
            f"\n[bold]Best score:[/bold] "
            f"{best.score_after:.4f} (iteration {best.iteration})"
        )


def _print_eval_report(report: EvalReport, verbose: bool = False) -> None:
    """Print evaluation report to console."""
    console.print(f"\n[bold]Score:[/bold] {report.aggregate_score:.4f}")
    console.print(f"[bold]Passed:[/bold] {len(report.passed)}/{len(report.results)}")

    if report.confidence_interval:
        ci = report.confidence_interval
        console.print(
            f"[bold]CI:[/bold] [{ci.ci_lower:.4f}, {ci.ci_upper:.4f}] "
            f"(std: {ci.std:.4f})"
        )

    if verbose:
        table = Table(title="Test Results")
        table.add_column("Test ID")
        table.add_column("Score", justify="right")
        table.add_column("Output")
        table.add_column("Error")

        for r in report.results:
            score_style = "green" if r.score >= 1.0 else "red"
            table.add_row(
                r.test_id,
                f"[{score_style}]{r.score:.2f}[/{score_style}]",
                r.actual_output[:80],
                r.error or "",
            )

        console.print(table)


def _print_optimization_result(
    result: Any, original_config: AgentConfig, output_path: Path
) -> None:
    """Print optimization result summary."""
    console.print("\n[bold]Optimization Complete[/bold]")
    console.print(f"  Baseline score: {result.baseline_report.aggregate_score:.4f}")
    console.print(f"  Final score:    {result.final_report.aggregate_score:.4f}")
    console.print(f"  Iterations:     {result.iterations_run}")

    improvement = result.final_report.aggregate_score - result.baseline_report.aggregate_score
    if improvement > 0:
        console.print(f"  [green]Improvement:  +{improvement:.4f}[/green]")
    elif improvement < 0:
        console.print(f"  [red]Regression:   {improvement:.4f}[/red]")
    else:
        console.print("  No change in score.")

    # Score trajectory sparkline from history
    if result.history_path and Path(result.history_path).exists():
        try:
            store = HistoryStore(result.history_path)
            records = store.get_all()
            scores = [r.score_after for r in records]
            if scores:
                console.print(f"\n  Score trajectory: {_sparkline(scores)}")
        except Exception:
            pass  # Non-critical display feature

    # Prompt diff
    if original_config.system_prompt != result.best_config.system_prompt:
        console.print("\n[bold]Prompt Changes:[/bold]")
        diff_output = _prompt_diff(
            original_config.system_prompt,
            result.best_config.system_prompt,
        )
        if diff_output:
            console.print(diff_output)
