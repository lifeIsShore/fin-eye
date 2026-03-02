from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import joblib
from xgboost import XGBClassifier

from app.services.technical_models import Timeframe, ModelKind


@dataclass
class SavedArtifact:
    path: str


class ModelArtifactStore:
    """
    Minimal model artifact store on the local filesystem.

    - sklearn models are saved with joblib (.joblib)
    - XGBoost models are saved using XGBClassifier.save_model (.json)
    """

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def artifact_path(self, *, symbol: str, timeframe: Timeframe, model_kind: ModelKind) -> Path:
        safe_symbol = symbol.upper()
        return (
            self.base_dir
            / safe_symbol
            / timeframe.value
            / f"{model_kind.value}"
        )

    def save(
        self,
        *,
        symbol: str,
        timeframe: Timeframe,
        model_kind: ModelKind,
        model: Any,
    ) -> SavedArtifact:
        base = self.artifact_path(symbol=symbol, timeframe=timeframe, model_kind=model_kind)
        base.parent.mkdir(parents=True, exist_ok=True)

        if model_kind == ModelKind.XGBOOST:
            path = base.with_suffix(".json")
            model.save_model(str(path))
            return SavedArtifact(path=str(path))

        # Default to sklearn-style persistence for now
        path = base.with_suffix(".joblib")
        joblib.dump(model, str(path))
        return SavedArtifact(path=str(path))

    def load(self, *, artifact_path: str, model_kind: ModelKind) -> Any:
        """
        Load a persisted model artifact.
        """
        path = Path(artifact_path)
        if model_kind == ModelKind.XGBOOST:
            model = XGBClassifier()
            model.load_model(str(path))
            return model
        return joblib.load(str(path))

