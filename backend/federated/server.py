"""
Federated learning SIMULATION.

What this module really does (stated plainly so the UI never over-claims):
* The four "institutions" are SIMULATED partitions of SYNTHETIC data generated
  in federated/client.py. No real college or student data participates.
* Each round: every client starts from the current global model, trains
  locally (SGD logistic regression), and sends its model update.
* Server-side protection: each client UPDATE (delta from the global model) is
  L2-clipped to CLIP_NORM, the clipped updates are averaged with sample
  weights, and Gaussian noise with std = NOISE_MULTIPLIER x CLIP_NORM / n_clients
  is added - the DP-FedAvg mechanism.
* No privacy accountant is implemented, so NO (epsilon, delta) guarantee is
  claimed. `privacy_epsilon` is reported as None. With only 4 clients,
  client-level DP would in any case give a very weak guarantee.
* Global accuracy is MEASURED on a fixed, seeded held-out synthetic test set.
  No floors, offsets or per-round bonuses are applied.
"""
import os
from datetime import datetime, timezone

import numpy as np

from extensions import db
from models import FLTrainingRound
from federated.client import InstitutionClient

CLIP_NORM = float(os.getenv("FL_CLIP_NORM", "1.0"))
NOISE_MULTIPLIER = float(os.getenv("FL_NOISE_MULTIPLIER", "0.5"))
N_FEATURES = 10
GLOBAL_MODEL_PATH = os.getenv("FL_GLOBAL_MODEL_PATH") or os.path.join(
    os.path.dirname(__file__), "..", "ml", "models", "fl_global.npz")

INSTITUTIONS = [
    {"id": "Institution_Alpha", "name": "Simulated Partition A (synthetic data)", "samples": 180},
    {"id": "Institution_Beta", "name": "Simulated Partition B (synthetic data)", "samples": 140},
    {"id": "Institution_Gamma", "name": "Simulated Partition C (synthetic data)", "samples": 160},
    {"id": "Institution_Delta", "name": "Simulated Partition D (synthetic data)", "samples": 125},
]

PRIVACY_STATEMENT = (
    "Simulation on synthetic data. Client updates are clipped (L2 norm "
    f"{CLIP_NORM}) and Gaussian noise (multiplier {NOISE_MULTIPLIER}) is added before aggregation. "
    "No privacy accountant is implemented, so no formal differential-privacy (epsilon, delta) guarantee is claimed."
)


def _test_set():
    rng = np.random.RandomState(20261112)
    X = rng.uniform(0.2, 0.95, size=(400, N_FEATURES))
    y = (X.mean(axis=1) > 0.55).astype(int)
    return X, y


def _load_global():
    try:
        data = np.load(GLOBAL_MODEL_PATH)
        return [data["coef"], data["intercept"]]
    except Exception:
        return [np.zeros((1, N_FEATURES)), np.zeros((1,))]


def _save_global(params):
    os.makedirs(os.path.dirname(GLOBAL_MODEL_PATH), exist_ok=True)
    np.savez(GLOBAL_MODEL_PATH, coef=params[0], intercept=params[1])


def _accuracy(params, X, y) -> float:
    logits = X @ params[0].T + params[1]
    return float(((logits.ravel() > 0).astype(int) == y).mean())


def run_federated_round(app=None):
    last_round = FLTrainingRound.query.order_by(FLTrainingRound.round_number.desc()).first()
    round_number = (last_round.round_number + 1) if last_round else 1

    global_params = _load_global()
    clients = [InstitutionClient(str(inst['id']), int(inst['samples'])) for inst in INSTITUTIONS]

    updates, weights, client_metrics = [], [], []
    for client in clients:
        new_params, num_samples, metrics = client.fit([p.copy() for p in global_params], {})
        delta = [np.asarray(n) - g for n, g in zip(new_params, global_params)]
        norm = float(np.sqrt(sum(float((d ** 2).sum()) for d in delta)))
        scale = min(1.0, CLIP_NORM / (norm + 1e-12))
        updates.append([d * scale for d in delta])
        weights.append(num_samples)
        client_metrics.append({**metrics, "update_norm": round(norm, 4), "clipped": scale < 1.0})

    total = float(sum(weights))
    agg = [sum(u[i] * (w / total) for u, w in zip(updates, weights)) for i in range(len(global_params))]
    noise_std = NOISE_MULTIPLIER * CLIP_NORM / len(clients)
    rng = np.random.default_rng()
    agg = [a + rng.normal(0.0, noise_std, size=a.shape) for a in agg]
    new_global = [g + a for g, a in zip(global_params, agg)]
    _save_global(new_global)

    X_test, y_test = _test_set()
    global_accuracy = round(_accuracy(new_global, X_test, y_test), 4)

    round_records = []
    now = datetime.now(timezone.utc)
    for client, m in zip(clients, client_metrics):
        record = FLTrainingRound(round_number=round_number, partition_id=client.partition_id,
                                 local_accuracy=m.get('local_accuracy'),
                                 global_accuracy_after_round=global_accuracy, trained_on=now)
        db.session.add(record)
        round_records.append({**record.to_dict(), "update_norm": m["update_norm"], "clipped": m["clipped"]})
    db.session.commit()

    return {
        'round_number': round_number,
        'participating_nodes': len(INSTITUTIONS),
        'global_accuracy': global_accuracy,
        'evaluation': 'Measured on a fixed held-out synthetic test set (400 samples)',
        'privacy_mechanism': {'clip_norm': CLIP_NORM, 'noise_multiplier': NOISE_MULTIPLIER,
                              'noise_std': round(noise_std, 4)},
        'privacy_guarantee': None,
        'privacy_statement': PRIVACY_STATEMENT,
        'records': round_records
    }


def get_federated_history():
    rounds = FLTrainingRound.query.order_by(FLTrainingRound.round_number.asc()).all()
    grouped = {}
    inst_name_map = {inst['id']: inst['name'] for inst in INSTITUTIONS}
    inst_samples_map = {inst['id']: inst['samples'] for inst in INSTITUTIONS}

    for r in rounds:
        grouped.setdefault(r.round_number, {
            'round_number': r.round_number,
            'global_accuracy': r.global_accuracy_after_round,
            'global_loss': None,          # not measured / not stored
            'privacy_epsilon': None,      # no accountant -> no epsilon is claimed
            'privacy_delta': None,
            'trained_on': r.trained_on.isoformat() if r.trained_on else None,
            'aggregation_status': 'FedAvg with update clipping + Gaussian noise',
            'node_accuracies': []
        })
        grouped[r.round_number]['node_accuracies'].append({
            'partition_id': r.partition_id,
            'institution_name': inst_name_map.get(r.partition_id, r.partition_id),
            'samples': inst_samples_map.get(r.partition_id),
            'local_accuracy': r.local_accuracy,
            'status': 'Update aggregated'
        })
    return list(grouped.values())


def get_federated_round_details(round_number: int):
    rounds = FLTrainingRound.query.filter_by(round_number=round_number).all()
    if not rounds:
        return None
    inst_name_map = {inst['id']: inst['name'] for inst in INSTITUTIONS}
    inst_samples_map = {inst['id']: inst['samples'] for inst in INSTITUTIONS}
    return {
        'round_number': round_number,
        'global_accuracy': rounds[0].global_accuracy_after_round,
        'global_loss': None,
        'participating_clients_count': len(rounds),
        'aggregation_status': 'Completed',
        'aggregation_strategy': 'FedAvg (sample-weighted) with per-client update clipping and Gaussian noise',
        'privacy_guarantee': {
            'epsilon': None,
            'delta': None,
            'mechanism': f'Update clipping (C = {CLIP_NORM}) + Gaussian noise (multiplier {NOISE_MULTIPLIER}); '
                         f'no formal privacy accounting',
            'raw_data_transferred': False
        },
        'nodes': [{
            'partition_id': r.partition_id,
            'institution_name': inst_name_map.get(r.partition_id, r.partition_id),
            'local_samples': inst_samples_map.get(r.partition_id),
            'local_accuracy': r.local_accuracy,
            'training_status': 'Local SGD step completed',
            'transmission': 'Model update sent (simulated, in-process)',
            'raw_data_retention': 'Synthetic data generated locally per partition'
        } for r in rounds],
        'pipeline_steps': [
            {'step': 1, 'name': 'Local Model Training', 'desc': 'Each simulated partition trains on its own synthetic data.'},
            {'step': 2, 'name': 'Update Clipping', 'desc': f'Each client update is L2-clipped to norm {CLIP_NORM}.'},
            {'step': 3, 'name': 'FedAvg Aggregation', 'desc': 'Sample-weighted average of clipped updates.'},
            {'step': 4, 'name': 'Gaussian Noise', 'desc': 'Noise is added to the aggregate. No epsilon is computed.'},
            {'step': 5, 'name': 'Global Model Update', 'desc': 'The new global model is stored and evaluated on held-out synthetic data.'}
        ],
        'privacy_statement': PRIVACY_STATEMENT,
    }


def get_federated_status():
    latest_round = FLTrainingRound.query.order_by(FLTrainingRound.round_number.desc()).first()
    return {
        'total_rounds': latest_round.round_number if latest_round else 0,
        'current_global_accuracy': latest_round.global_accuracy_after_round if latest_round else None,
        'current_global_loss': None,
        'participating_institutions': len(INSTITUTIONS),
        'nodes': INSTITUTIONS,
        'is_simulation': True,
        'data': 'synthetic',
        'differential_privacy': {
            'epsilon': None,
            'delta': None,
            'mechanism': f'Update clipping (C = {CLIP_NORM}) + Gaussian noise; no formal privacy accounting',
            'formal_guarantee': False,
        },
        'status': 'Operational (simulation)',
        'privacy_statement': PRIVACY_STATEMENT,
    }
