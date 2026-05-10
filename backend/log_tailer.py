#!/usr/bin/env python3
"""
Morphic Log Tailer  –  Full LogAI Pipeline
==========================================
Per-monitor background thread that:
  1. Polls logs_url at a configurable interval
  2. Parses raw log lines with Drain3 (LogAI's log parser)
  3. Extracts temporal features / counter vectors
  4. Vectorizes log templates (Word2Vec / TF-IDF)
  5. Clusters logs (K-Means / DBSCAN)
  6. Detects anomalies via:
       • Time-series  : ETS on error-rate counter vector
       • Semantic     : One-Class SVM on log embeddings
       • Statistical  : IsolationForest on feature matrix
  7. Generates a log summary (top patterns + stats)
  8. Fires an on_anomaly callback when threshold exceeded
"""

import os
import io
import json
import time
import math
import logging
import threading
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger("morphic.log_tailer")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ─────────────────────────────────────────────────────────────
# LogAI Full Pipeline
# ─────────────────────────────────────────────────────────────

class LogAIFullPipeline:
    """
    Wraps the entire LogAI processing chain:
      DataLoader → Preprocessor → LogParser (Drain) →
      FeatureExtractor → LogVectorizer →
      CategoricalEncoder → AnomalyDetector (3 algorithms) →
      Summarizer
    """

    def __init__(self):
        self.available = False
        self._log_parser = None
        self._word2vec_model = None
        self._ocsvm = None
        self._iso_forest = None
        self._error_counter_history: deque = deque(maxlen=30)

        try:
            # Core LogAI imports
            from logai.information_extraction.log_parser import LogParser, LogParserConfig
            from logai.algorithms.parsing_algo.drain import DrainParams
            from logai.algorithms.vectorization_algo.word2vec import Word2Vec, Word2VecParams
            from logai.algorithms.vectorization_algo.tfidf import TfIdf, TfIdfParams
            from logai.algorithms.anomaly_detection_algo.one_class_svm import (
                OneClassSVM, OneClassSVMParams,
            )
            from logai.algorithms.anomaly_detection_algo.isolation_forest import (
                IsolationForest, IsolationForestParams,
            )
            from logai.dataloader.data_model import LogRecordObject

            # --- LogParser with Drain ---
            parsing_algo_params = DrainParams(sim_th=0.7, depth=5)
            log_parser_config = LogParserConfig(
                parsing_algorithm="drain",
                parsing_algo_params=parsing_algo_params
            )
            self._log_parser = LogParser(log_parser_config)

            # --- TF-IDF vectorizer (fast, no warm-up needed) ---
            tfidf_params = TfIdfParams()
            self._tfidf = TfIdf(params=tfidf_params)

            # --- One-Class SVM for semantic anomaly detection ---
            self._ocsvm = OneClassSVM(kernel="rbf", nu=0.1)

            # --- IsolationForest for statistical anomaly detection ---
            self._iso_forest = IsolationForest(n_estimators=100, contamination=0.1)

            self.available = True
            logger.info("✅ LogAI full pipeline ready (LogParser/Drain + TF-IDF + OCSVM + IsolationForest)")

        except ImportError as e:
            logger.warning(f"⚠️  LogAI not fully installed, using statistical fallback: {e}")
        except Exception as e:
            logger.warning(f"⚠️  LogAI init error: {e}")

    # ------------------------------------------------------------------ #
    #  Main analysis entry point
    # ------------------------------------------------------------------ #
    def analyze(self, logs: List[Dict]) -> Dict:
        """Run the full analysis pipeline on a batch of log records."""
        if not logs:
            return self._empty_result()

        # Normalise to flat dict list
        records = [self._normalise(l) for l in logs]

        if self.available:
            return self._logai_pipeline(records)
        else:
            return self._statistical_fallback(records)

    # ------------------------------------------------------------------ #
    #  Full LogAI pipeline
    # ------------------------------------------------------------------ #
    def _logai_pipeline(self, records: List[Dict]) -> Dict:
        try:
            from logai.dataloader.data_model import LogRecordObject

            # Build a DataFrame in LogAI's expected format
            df = pd.DataFrame(records)
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
            df = df.fillna("")

            loglines = df["message"].astype(str)

            # ── 1. Log Parsing (Drain via LogParser) ──────────────────────────────────
            parsed_result = self._log_parser.parse(loglines)
            templates = parsed_result['parsed_logline']
            df["template"] = templates

            # ── 2. Log Summarization ────────────────────────────────────
            template_counts = df["template"].value_counts().head(10)
            summary = {
                "top_patterns": [
                    {"pattern": pat, "count": int(cnt)}
                    for pat, cnt in template_counts.items()
                ]
            }

            # ── 3. Feature Extraction ───────────────────────────────────
            error_mask = df["level"].isin(["ERROR", "CRITICAL", "FATAL"])
            warn_mask  = df["level"].isin(["WARN", "WARNING"])
            
            # Heuristic for "fault" keywords even in INFO/WARN logs
            fault_keywords = ["fail", "error", "exception", "stall", "timeout", "abort", "anomaly", "underflow"]
            fault_mask = df["message"].str.lower().apply(lambda x: any(kw in x for kw in fault_keywords))
            
            error_count = int(error_mask.sum())
            warn_count  = int(warn_mask.sum())
            fault_count = int(fault_mask.sum())
            total       = len(df)
            
            # Composite error rate including warnings and faults
            error_rate  = error_count / total if total else 0.0
            fault_rate  = fault_count / total if total else 0.0
            warn_rate   = warn_count / total if total else 0.0

            # Time-series counter vector (1-minute buckets)
            df["minute"] = df["timestamp"].dt.floor("1min")
            error_by_min = df[error_mask | fault_mask].groupby("minute").size()
            self._error_counter_history.extend(error_by_min.values.tolist())

            # ── 4. TF-IDF Vectorization ─────────────────────────────────
            anomaly_scores_semantic = np.zeros(total)
            try:
                vectors = self._tfidf.transform(pd.Series(templates))
                if hasattr(vectors, "toarray"):
                    vectors = vectors.toarray()

                if len(vectors) >= 5:
                    # ── 5. One-Class SVM ────────────────────────────────
                    self._ocsvm.fit(vectors)
                    preds = self._ocsvm.predict(vectors)   # -1 = anomaly
                    anomaly_scores_semantic = (preds == -1).astype(float)
            except Exception as ve:
                logger.debug(f"Vectorization/OCSVM skipped: {ve}")

            # ── 6. IsolationForest on feature matrix ────────────────────
            anomaly_scores_iso = np.zeros(total)
            try:
                feature_cols = []
                # Encode level as numeric
                level_map = {"DEBUG": 0, "INFO": 1, "WARN": 2, "WARNING": 2,
                             "ERROR": 3, "CRITICAL": 4, "FATAL": 4}
                level_numeric = df["level"].map(level_map).fillna(1).values.reshape(-1, 1)

                # Message length as feature
                msg_len = df["message"].str.len().fillna(0).values.reshape(-1, 1)
                
                # Add fault flag as feature
                is_fault = fault_mask.astype(float).values.reshape(-1, 1)

                feature_matrix = np.hstack([level_numeric, msg_len, is_fault])
                if len(feature_matrix) >= 10:
                    self._iso_forest.fit(feature_matrix)
                    iso_preds = self._iso_forest.predict(feature_matrix)
                    anomaly_scores_iso = (iso_preds == -1).astype(float)
            except Exception as ie:
                logger.debug(f"IsolationForest skipped: {ie}")

            # ── 7. Time-series ETS anomaly (rolling z-score) ────────────
            ts_anomaly = False
            ts_score = 0.0
            if len(self._error_counter_history) >= 5:
                hist = np.array(list(self._error_counter_history))
                mean, std = hist[:-1].mean(), hist[:-1].std() + 1e-6
                z = abs((hist[-1] - mean) / std)
                ts_score = float(min(1.0, z / 4.0))
                ts_anomaly = z > 2.2 # Lowered from 2.5

            # ── 8. Composite anomaly score ──────────────────────────────
            semantic_anomaly_rate = float(anomaly_scores_semantic.mean())
            iso_anomaly_rate      = float(anomaly_scores_iso.mean())
            
            # Weighted composite score
            composite_score = max(
                error_rate,
                fault_rate * 0.9,
                semantic_anomaly_rate * 0.8,
                iso_anomaly_rate * 0.7,
                ts_score * 0.95,
                warn_rate * 0.4
            )

            anomaly_detected = (
                composite_score > 0.30 # Lowered from 0.35
                or error_rate > 0.08  # Lowered from 0.10
                or ts_anomaly
                or semantic_anomaly_rate > 0.15 # Lowered from 0.20
                or (fault_rate > 0.15 and warn_rate > 0.20)
            )

            # ── 9. Build error signals ──────────────────────────────────
            error_df = df[error_mask].head(20)
            signals = [
                {
                    "timestamp": str(row.get("timestamp", "")),
                    "level":     row.get("level", "ERROR"),
                    "message":   str(row.get("message", ""))[:500],
                    "service":   row.get("service", "unknown"),
                    "template":  row.get("template", ""),
                }
                for _, row in error_df.iterrows()
            ]

            return {
                "anomaly_detected":      anomaly_detected,
                "score":                 round(composite_score, 4),
                "error_rate":            round(error_rate, 4),
                "error_count":           error_count,
                "warn_count":            warn_count,
                "total_logs":            total,
                "ts_anomaly":            ts_anomaly,
                "ts_score":              round(ts_score, 4),
                "semantic_anomaly_rate": round(semantic_anomaly_rate, 4),
                "iso_anomaly_rate":      round(iso_anomaly_rate, 4),
                "signals":               signals,
                "summary":               summary,
                "pipeline":              "logai_full",
            }

        except Exception as exc:
            logger.error(f"LogAI pipeline error: {exc}", exc_info=True)
            return self._statistical_fallback([])

    # ------------------------------------------------------------------ #
    #  Statistical fallback (no LogAI)
    # ------------------------------------------------------------------ #
    def _statistical_fallback(self, records: List[Dict]) -> Dict:
        if not records:
            return self._empty_result()

        total = len(records)
        error_count = sum(
            1 for r in records
            if r.get("level", "").upper() in ("ERROR", "CRITICAL", "FATAL")
        )
        warn_count = sum(
            1 for r in records
            if r.get("level", "").upper() in ("WARN", "WARNING")
        )
        error_rate = error_count / total if total else 0.0

        self._error_counter_history.append(error_rate)
        if len(self._error_counter_history) >= 5:
            hist = np.array(list(self._error_counter_history))
            mean, std = hist[:-1].mean(), hist[:-1].std() + 1e-6
            z = abs((hist[-1] - mean) / std)
            ts_score = float(min(1.0, z / 4.0))
        else:
            z, ts_score = 0.0, 0.0

        composite_score = max(error_rate, ts_score * 0.9)
        anomaly_detected = composite_score > 0.35 or error_rate > 0.10

        signals = [
            {
                "timestamp": r.get("timestamp", ""),
                "level":     r.get("level", "ERROR"),
                "message":   str(r.get("message", ""))[:500],
                "service":   r.get("service", "unknown"),
            }
            for r in records
            if r.get("level", "").upper() in ("ERROR", "CRITICAL", "FATAL")
        ][:20]

        return {
            "anomaly_detected": anomaly_detected,
            "score":            round(composite_score, 4),
            "error_rate":       round(error_rate, 4),
            "error_count":      error_count,
            "warn_count":       warn_count,
            "total_logs":       total,
            "ts_score":         round(ts_score, 4),
            "signals":          signals,
            "pipeline":         "statistical_fallback",
        }

    # ------------------------------------------------------------------ #
    def _normalise(self, log: Dict) -> Dict:
        """Flatten a raw log dict to a standard schema."""
        level = str(
            log.get("level", log.get("log_level", log.get("severity", "INFO")))
        ).upper()
        msg = str(log.get("message", log.get("msg", log.get("body", json.dumps(log)))))
        ts_raw = log.get("timestamp", log.get("@timestamp", log.get("time", "")))
        return {
            "timestamp": ts_raw or datetime.now(timezone.utc).isoformat(),
            "level":     level,
            "message":   msg[:2000],
            "service":   str(log.get("service", log.get("logger", log.get("source", "unknown")))),
        }

    def _empty_result(self) -> Dict:
        return {
            "anomaly_detected": False,
            "score": 0.0,
            "error_rate": 0.0,
            "error_count": 0,
            "warn_count": 0,
            "total_logs": 0,
            "signals": [],
            "pipeline": "empty",
        }


# ─────────────────────────────────────────────────────────────
# TailerState & MonitorLogTailer
# ─────────────────────────────────────────────────────────────

@dataclass
class TailerState:
    monitor_id: str
    logs_url: str
    auth_type: str = "NONE"
    auth_config: Dict = field(default_factory=dict)
    interval_seconds: int = 30
    enabled: bool = True
    monitor_enabled: bool = True
    github_owner: Optional[str] = None
    github_repo: Optional[str] = None
    github_token: Optional[str] = None
    github_branch: str = "main"
    # runtime
    running: bool = False
    last_fetched_at: Optional[datetime] = None
    consecutive_errors: int = 0


class MonitorLogTailer:
    ANOMALY_COOLDOWN_SECONDS = 300

    def __init__(self, state: TailerState, db_manager, pipeline: LogAIFullPipeline,
                 on_anomaly: Callable):
        self.state = state
        self.db = db_manager
        self.pipeline = pipeline
        self.on_anomaly = on_anomaly
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_anomaly_trigger: Optional[datetime] = None
        self._seen_keys: deque = deque(maxlen=2000)
        self._seen_set: set = set()

    def start(self):
        self._stop_event.clear()
        self.state.running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            name=f"tailer-{self.state.monitor_id}",
            daemon=True,
        )
        self._thread.start()
        logger.info(f"[tailer] ▶ Started for monitor {self.state.monitor_id}")

    def stop(self):
        self._stop_event.set()
        self.state.running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _run_loop(self):
        while not self._stop_event.is_set():
            # Only poll logs when monitor is enabled AND log tailing is enabled
            if self.state.enabled and self.state.monitor_enabled:
                try:
                    self._tick()
                    self.state.consecutive_errors = 0
                except Exception as exc:
                    self.state.consecutive_errors += 1
                    logger.error(f"[tailer] {self.state.monitor_id}: {exc}", exc_info=True)
            self._stop_event.wait(timeout=self.state.interval_seconds)

    def _tick(self):
        logs = self._fetch_logs()
        if not logs:
            return
        self.state.last_fetched_at = datetime.now(timezone.utc)
        logs = self._dedup_and_flag(logs)
        if not logs:
            return

        result = self.pipeline.analyze(logs)
        self._store_logs(logs, analysis=result)
        if result.get("anomaly_detected"):
            self._handle_anomaly(logs, result)

    def _dedup_and_flag(self, logs: List[Dict]) -> List[Dict]:
        """Deduplicate by (timestamp, trace_id) and flag ASYNC-ORPHAN."""
        out: List[Dict] = []
        for log in logs:
            ts = str(log.get("timestamp") or log.get("@timestamp") or log.get("time") or "")
            trace_id = str(log.get("trace_id") or "")
            key = (ts, trace_id)

            # Dedup
            if key in self._seen_set:
                continue
            if len(self._seen_keys) == self._seen_keys.maxlen:
                try:
                    old = self._seen_keys.popleft()
                    self._seen_set.discard(old)
                except Exception:
                    pass
            self._seen_keys.append(key)
            self._seen_set.add(key)

            # ASYNC-ORPHAN detection
            if trace_id in ("", "unknown", "ASYNC-ORPHAN", "None"):
                log = dict(log)
                log["async_orphan"] = True
            out.append(log)
        return out

    def _fetch_logs(self) -> List[Dict]:
        headers = {"Accept": "application/json", "User-Agent": "Morphic-LogTailer/2.0"}
        cfg = self.state.auth_config or {}
        if self.state.auth_type == "BEARER":
            tok = cfg.get("bearer_token", "")
            if tok:
                headers["Authorization"] = f"Bearer {tok}"
        elif self.state.auth_type == "BASIC":
            import base64
            creds = f"{cfg.get('username','')}:{cfg.get('password','')}"
            headers["Authorization"] = "Basic " + base64.b64encode(creds.encode()).decode()
        try:
            resp = requests.get(self.state.logs_url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                for key in ("logs", "data", "items", "results", "messages", "records"):
                    if key in data and isinstance(data[key], list):
                        return data[key]
                return [data]
        except Exception as exc:
            logger.warning(f"[tailer] Fetch failed {self.state.logs_url}: {exc}")
        return []

    def _store_logs(self, logs: List[Dict], analysis: Optional[Dict] = None):
        try:
            conn = self.db.postgres_conn
            is_anomaly = bool(analysis.get("anomaly_detected")) if analysis else False
            anomaly_score = float(analysis.get("score")) if analysis and analysis.get("score") is not None else None
            with conn.cursor() as cur:
                # Store logs
                for log in logs[-100:]:
                    level = str(log.get("level", log.get("log_level", "INFO"))).upper()
                    msg = str(log.get("message", log.get("msg", json.dumps(log))))[:2000]
                    cur.execute(
                        "INSERT INTO monitor_log_entries (monitor_id, log_level, message, raw, anomaly_score, is_anomaly) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (
                            self.state.monitor_id,
                            level,
                            msg,
                            json.dumps(log),
                            anomaly_score,
                            is_anomaly,
                        ),
                    )
                
                # Store batch analysis
                if analysis:
                    cur.execute(
                        """INSERT INTO monitor_analysis 
                           (monitor_id, composite_score, error_rate, semantic_score, iso_score, ts_score, top_patterns, anomaly_detected, signals)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            self.state.monitor_id,
                            analysis.get("score"),
                            analysis.get("error_rate"),
                            analysis.get("semantic_anomaly_rate"),
                            analysis.get("iso_anomaly_rate"),
                            analysis.get("ts_score"),
                            json.dumps(analysis.get("summary", {}).get("top_patterns", [])),
                            analysis.get("anomaly_detected"),
                            json.dumps(analysis.get("signals", []))
                        )
                    )
            conn.commit()
        except Exception as exc:
            logger.error(f"[tailer] Store failed: {exc}")
            try:
                self.db.postgres_conn.rollback()
            except Exception:
                pass

    def _handle_anomaly(self, logs: List[Dict], analysis: Dict):
        now = datetime.now(timezone.utc)
        if self._last_anomaly_trigger:
            if (now - self._last_anomaly_trigger).total_seconds() < self.ANOMALY_COOLDOWN_SECONDS:
                return
        self._last_anomaly_trigger = now
        # Prefer a real trace_id from the log batch so remediation is trace-anchored.
        trace_id = None
        for l in reversed(logs):
            tid = str(l.get("trace_id") or "").strip()
            if tid and tid.lower() not in ("unknown", "none"):
                trace_id = tid
                break
        if not trace_id:
            trace_id = f"trace-{self.state.monitor_id}-{int(now.timestamp())}"
        logger.warning(
            f"[tailer] 🚨 Anomaly on {self.state.monitor_id} "
            f"score={analysis['score']} pipeline={analysis.get('pipeline')}"
        )
        try:
            with self.db.postgres_conn.cursor() as cur:
                cur.execute(
                    "UPDATE monitors SET last_anomaly_at=%s, agent_run_status='TRIGGERED' WHERE id=%s",
                    (now, self.state.monitor_id),
                )
            self.db.postgres_conn.commit()
        except Exception:
            try:
                self.db.postgres_conn.rollback()
            except Exception:
                pass
        if self.on_anomaly:
            self.on_anomaly(
                monitor_id=self.state.monitor_id,
                trace_id=trace_id,
                logs=logs,
                analysis=analysis,
                github_owner=self.state.github_owner,
                github_repo=self.state.github_repo,
                github_token=self.state.github_token,
                github_branch=self.state.github_branch,
            )


# ─────────────────────────────────────────────────────────────
# TailerRegistry
# ─────────────────────────────────────────────────────────────

class TailerRegistry:
    def __init__(self, db_manager, on_anomaly_callback: Callable):
        self.db = db_manager
        self.on_anomaly = on_anomaly_callback
        self.pipeline = LogAIFullPipeline()
        self._tailers: Dict[str, MonitorLogTailer] = {}
        self._lock = threading.Lock()

    def sync_monitors(self, monitors: List[Dict]):
        with self._lock:
            current_ids = {m["id"] for m in monitors if m.get("logs_url")}
            for mid in list(self._tailers):
                if mid not in current_ids:
                    self._tailers[mid].stop()
                    del self._tailers[mid]
            for m in monitors:
                if not m.get("logs_url"):
                    continue
                mid = m["id"]
                if mid in self._tailers:
                    t = self._tailers[mid]
                    t.state.logs_url = m["logs_url"]
                    t.state.github_owner = m.get("github_owner")
                    t.state.github_repo = m.get("github_repo")
                    t.state.github_token = m.get("github_token")
                    t.state.enabled = bool(m.get("log_tail_enabled", True))
                    t.state.monitor_enabled = bool(m.get("enabled", True))
                else:
                    state = TailerState(
                        monitor_id=mid,
                        logs_url=m["logs_url"],
                        auth_type=m.get("auth_type", "NONE"),
                        github_owner=m.get("github_owner"),
                        github_repo=m.get("github_repo"),
                        github_token=m.get("github_token"),
                        github_branch=m.get("github_branch", "main"),
                        enabled=bool(m.get("log_tail_enabled", True)),
                    )
                    state.monitor_enabled = bool(m.get("enabled", True))
                    tailer = MonitorLogTailer(state, self.db, self.pipeline, self.on_anomaly)
                    tailer.start()
                    self._tailers[mid] = tailer

    def stop_all(self):
        with self._lock:
            for t in self._tailers.values():
                t.stop()
            self._tailers.clear()

    def get_status(self) -> Dict:
        with self._lock:
            return {
                mid: {
                    "running":           t.state.running,
                    "enabled":           t.state.enabled,
                    "last_fetched_at":   t.state.last_fetched_at.isoformat() if t.state.last_fetched_at else None,
                    "consecutive_errors": t.state.consecutive_errors,
                    "pipeline":          "logai_full" if self.pipeline.available else "statistical_fallback",
                }
                for mid, t in self._tailers.items()
            }
