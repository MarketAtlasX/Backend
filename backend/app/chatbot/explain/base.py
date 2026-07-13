from abc import ABC, abstractmethod
from typing import Any

from .models import ExplanationResult


class BaseExplainer(ABC):
    @abstractmethod
    async def explain(self, prediction: str = "", context: dict[str, Any] | None = None) -> ExplanationResult:
        ...

    def format_explanation(self, result: ExplanationResult) -> str:
        if not result or (not result.shap and not result.attention and not result.graph):
            return ""
        lines = []
        if result.shap:
            lines.append("### SHAP Feature Attribution")
            lines.append("")
            lines.append(f"**Prediction:** {result.shap.prediction[:80]}")
            lines.append(f"**Expected Change:** {result.shap.predicted_change_pct:+.1f}%")
            lines.append("")
            lines.append("| Factor | Contribution |")
            lines.append("|--------|-------------|")
            for c in sorted(result.shap.contributions, key=lambda x: abs(x.impact_pct), reverse=True):
                sign = "+" if c.direction == "positive" else "-"
                lines.append(f"| {c.feature} | {sign}{abs(c.impact_pct):.1f}% |")
            lines.append("")

        if result.attention:
            lines.append("### Attention Weights")
            lines.append("")
            if result.attention.top_events:
                lines.append("**Most Influential Events:**")
                for i, ev in enumerate(result.attention.top_events, 1):
                    lines.append(f"   {i}. {ev.input_label} — weight: {ev.weight:.2%}")
                lines.append("")
            if result.attention.top_features:
                lines.append("**Key Features:**")
                for f in result.attention.top_features:
                    lines.append(f"   • {f.input_label}: {f.weight:.2%}")
                lines.append("")

        if result.graph:
            lines.append("### Reasoning Path")
            lines.append("")
            lines.append(f"**{result.graph.start_entity}**")
            for step in result.graph.path:
                lines.append(f"   ↓ **{step.relation}**")
                lines.append(f"   {step.target}")
            lines.append("")
            if result.graph.path_summary:
                lines.append(f"*{result.graph.path_summary}*")
                lines.append("")

        return "\n".join(lines)
